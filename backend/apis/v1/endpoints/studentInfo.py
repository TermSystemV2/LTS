import json
import logging
from os import stat
from pyexpat import model
import re
from statistics import mode

from fastapi import APIRouter, Request, Response, Depends,status,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_,or_
from aioredis import Redis


from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import stuInfo_cache
from core.config import config
from database.curd_ec import (
    ec_getCurrentYear, ec_get_by_year, ec_getYearList, ec_get_by_grade,
    ec_gradeToYear, ec_getGradeList, ec_get_info_by_grade_year
)

stuInfo_router = APIRouter()

@stuInfo_router.get("/studentInfo/grade/")
async def getStudentInfoByGrade(grade:int,redis_store:Redis = Depends(stuInfo_cache),db:Session = Depends(get_db)):
    """
    请求某个年级的所有不及格学生的信息
    :param grade: 18 19 20 21
    :return:
    """
    print("[debug] grade {}".format(grade))
    state = await redis_store.exists("studentInfo_"+str(grade))
    print("[debug] state: ",state)
    if state == 0:
        course_credit_dic = await get_course_credit(db,redis_store)  # 课程:学分
        allFailedStudentInfos = []
        # 从score 中获取所有成绩有不及格情况的同学
        ## 格式为 json
        stuID_json = await get_failedStuID(db,redis_store)
        if stuID_json == -1:
            return Response400(msg="数据库异常")
        elif stuID_json == -2:
            return Response400(msg="写入redis异常")
        stuID_json = json.loads(stuID_json)
        print(type(stuID_json))
        # print("stuID_json:{}".format(stuID_json))

        stuID_list = []
        for stu in stuID_json:
            if stu["stuGrade"] == str(grade):
                stuID_list.append(stu["stuID"])
        # classNameList = []

        for stuID in stuID_list:
            dict_stuInfo = await get_stuInfo_by_grade(db,stuID, course_credit_dic, grade)
            allFailedStudentInfos.append(dict_stuInfo)
            # classNameList.append(dict_stuInfo["stuClass"])
        # print(classNameList)
        # 对结果进行排序
        allFailedStudentInfos.sort(key=lambda k: (k.get('sumFailedCredit')), reverse=True)
        index = 1
        for stuInfo in allFailedStudentInfos:
            stuInfo["index"] = index
            index += 1

        if len(allFailedStudentInfos) != 0:
            resp_json = json.dumps(allFailedStudentInfos,ensure_ascii=False)
            # resp_json = json.loads(resp_json)
            print("type(resp_json) ", type(resp_json))
            try:
                await redis_store.setex("studentInfo_"+str(grade),config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,resp_json)
            except Exception as E:
                logging.error("写入 redis 异常 %s" % E)

                return Response400(msg="写入 redis 异常 %s" % str(E))
            
            return Response200(data=allFailedStudentInfos)
        else:
            return Response400(msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空")
    else:
        resp_data = await redis_store.get("studentInfo_"+str(grade))
        # print("type(resp_data) ",type(json.loads(resp_data)))
        if isinstance(resp_data,str):
            resp_data = json.loads(resp_data)
        return Response200(data=resp_data)


@stuInfo_router.post("/studentInfo/query/")
async def queryStudentInfoByNameOrID(request:Request,queryItem:schemas.StudentInfoQuery,redis_store:Redis = Depends(stuInfo_cache),db:Session = Depends(get_db)):
    """
    通过学号或者 姓名查询学生信息
    :return:
    """
    query_stuID = queryItem.stuID # request.args.get("stuID")
    query_stuName = queryItem.stuName #request.args.get("stuName")
    course_credit_dic = await get_course_credit(db,redis_store)
    allFailedStudentInfos = []

    # 从score 中获取所有成绩有不及格情况的同学
    ## 格式为 json
    stuID_json = await get_failedStuID(db,redis_store)
    if stuID_json == -1:
        return Response400(code=status.HTTP_500_INTERNAL_SERVER_ERROR,msg="数据库查询异常")
    elif stuID_json == -2:
        return Response400(code=status.HTTP_500_INTERNAL_SERVER_ERROR,msg="写入redis异常")
    stuID_json = json.loads(stuID_json)
    # 将json转换为list
    # print("="*50)
    # print(type(stuID_json))
    # print("stuID_json:{}".format(stuID_json))
    # stuID_dict = json.loads(stuID_json)
    # print(type(stuID_dict))
    # print("stuID_dict:{}".format(stuID_dict))
    # stuID_json = list(stuID_json)
    stuID_list = []
    for stu in stuID_json:
        stuID_list.append(stu["stuID"])

    if query_stuID or query_stuName:
        if query_stuID:
            pattern = "U[0-9]{9,9}"  # 学号格式验证 U201718703
            if re.match(pattern, query_stuID) == None:
                return Response400(code=status.HTTP_400_BAD_REQUEST,msg="输入的学号格式不正确")
            if query_stuID not in stuID_list:
                return Response400(code=status.HTTP_400_BAD_REQUEST,msg="该学生在系统中无挂科记录")
        else:
            # 使用姓名查询
            query_res = db.query(models.Student).with_entities(models.Student.stuID).filter(models.Student.stuName == query_stuName).first()
            if query_res[0] not in stuID_list:
                return Response400(code=status.HTTP_400_BAD_REQUEST,msg="该学生在系统中无挂科记录")
            query_stuID = query_res[0]
        dict_stuInfo = await get_stuInfo(db,query_stuID, course_credit_dic)
        allFailedStudentInfos.append(dict_stuInfo)
        return Response200(data=allFailedStudentInfos)
        #  print("")
        # resp_json = json.dumps(allFailedStudentInfos,ensure_ascii=False)
        # return Response200(data=resp_json)

    return Response400(code=status.HTTP_400_BAD_REQUEST,msg="请输入正确的参数")


async def get_course_credit(db:Session,redis_store:Redis):
    """

    :return:
    {
        "courseName1":credit1,
        "courseName2":credit2,
    }
    """
    # 后序优化：将这些数据存在 redis中
    dict_course_credit = {}
    state = await redis_store.exists("dict_course_credit")
    if state == 0:
        couresList = db.query(models.Courses).all()
        for course in couresList:
            dict_course_credit[course.courseName] = course.credit
        await redis_store.setex("dict_course_credit",config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,json.dumps(dict_course_credit,ensure_ascii=False))
    else:
        dict_course_credit = await redis_store.get("dict_course_credit")
    # print("[debug] dict_course_credit :{}".format(dict_course_credit))
    # print("dict_course_credit: ", type(dict_course_credit))
    # print("dict_course_credit ",type())
    if isinstance(dict_course_credit,dict):
        return dict_course_credit
    else:
        return json.loads(dict_course_credit)

async def get_failedStuID(db:Session,redis_store:Redis):
    """
    获取考试有不及格情况同学的学号信息
    :return:
    {
        {
            "stuIndex": 1,
            "stuID": "U201514480"
        },
        {
            "stuIndex": 1,
            "stuID": "U201514480"
        }
    }
    """
    # 首先从redis中查
    state = await redis_store.exists("failedStuID")
    if state != 0:
        return await redis_store.get("failedStuID")
    # 没有读到
    try:
        # ## 查询学号 成绩 < 60, 对查询结果降序排序
        results = db.query(models.Scores).with_entities(models.Scores.stuID,models.Scores.grade).distinct().filter(models.Scores.score < '60').order_by(models.Scores.stuID.asc())
    except Exception as E:
        logging.error(msg="发生异常：{}".format(str(E)))
        return -1 #jsonify(errno=RET.DATAERR,errmsg="数据库异常")
    dic_stuID_list = []
    i = 1
    for res in results:
        d = {
            "stuIndex":i,
            "stuGrade":res[1],
            "stuID": res[0]
        }
        i += 1
        dic_stuID_list.append(d)
    # print("DEBUG get stuid list: ", dic_stuID_list)
    # 将不及格学生的学号信息存入 redis
    # dic_stuID_list = dict(errno=RET.OK,errmsg="OK",data=dic_stuID_list)
    resp_json = json.dumps(dic_stuID_list)
    try:
        await redis_store.setex("failedStuID", config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES, resp_json)
    except Exception as E:
        logging.error(msg="发生异常：{}".format(str(E)))
        return -2
    print("[debug]resp_json :{}".format(resp_json))
    return resp_json

async def get_stuInfo_by_grade(db:Session,stuID, course_credit_dic,grade):
    """

    :param stuID:
    :param course_credit_dic:
    :param grade:
    :return:
    """
    """
        根据学号，找到这个学生需要的所有信息
        :param stuID:
        :return:
        {
            "stuID": "stuID",
            "stuName": "stuName",
            "stuClass": "CS1707",
            "11":{
                "微积分": "67",
                "线性代数": "80"
            },
            “12”:{
                "微积分": "67",
                "线性代数": "80"
            },
            "failSubjects": {
                "微积分": "57",
                "计算机组成原理": "34"
            },
            "totalWeightedScore:totalWeightedScore,
            "totalWeightedScoreTerm1“:totalWeightedScoreTerm1,
            "totalWeightedScoreTerm3":totalWeightedScoreTerm3,
            "totalWeightedScoreTerm4":totalWeightedScoreTerm4
        }
        """
    # print(course_credit_dic)
    term1, term2, term3, term4 = {}, {}, {}, {}
    failedSubjectdict = {}
    failedSubjectdict["stuID"] = stuID
    stuClass = db.query(models.Student).filter(models.Student.stuID == stuID).with_entities(models.Student.stuClass, models.Student.stuName).first()
    # print("stuClass: ",stuClass,stuID)
    failedSubjectdict["stuName"] = stuClass[1]
    failedSubjectdict["stuClass"] = stuClass[0]
    # print("="*50)
    # print(stuID," ",grade)
    # print("="*50)
    scoreList = db.query(models.Scores).filter(and_(models.Scores.stuID == stuID,models.Scores.grade == grade)).with_entities(models.Scores.courseName,models.Scores.score,models.Scores.term).all()
    # print("="*50)
    # for sc in scoreList:
    #     print(sc)
    # print("="*50)
    credit1, credit2, credit3, credit4 = 0.0, 0.0, 0.0, 0.0
    sumScore1, sumScore2, sumScore3, sumScore4 = 0.0, 0.0, 0.0, 0.0
    failedSubjectNamesScores = {}
    sumFailedCredit = 0.0
    failedSubjectNumsTerm1, failedSubjectNumsTerm2, failedSubjectNumsTerm3, failedSubjectNumsTerm4 = 0, 0, 0, 0
    # courseName,score,term
    # print(course_credit_dic)
    for sc in scoreList:
        # print(sc.courseName,sc.score,sc.term)
        # if not isinstance(sc.score,int):
        #     continue
        # print("+"*20)
        # print(sc.to_dic())
        # print("+"*20)
        if sc[2] == 11 or sc[2] == 12:
            term1[sc[0]] = sc[1]
            sumScore1 += (sc[1] * course_credit_dic[sc[0]])
            credit1 += (course_credit_dic[sc[0]])
            if sc[1] < 60:
                failedSubjectNumsTerm1 += 1
        elif sc[2] == 21 or sc[2] == 22:
            # print("="*20)
            # print(sc)
            # print("couse_credict ",type(course_credit_dic))
            # print(type(sc[0]))
            # print(type(course_credit_dic[sc[0]]))
            # print(type(sc[1]))
            # print("="*20)
            term2[sc[0]] = sc[1]
            sumScore2 += (sc[1] * course_credit_dic[sc[0]])
            credit2 += (course_credit_dic[sc[0]])
            if sc[1] < 60:
                failedSubjectNumsTerm2 += 1
        elif sc[2] == 31 or sc[2] == 32:
            term3[sc[0]] = sc[1]
            sumScore3 += (sc[1] * course_credit_dic[sc[0]])
            credit3 += (course_credit_dic[sc[0]])
            if sc[1] < 60:
                failedSubjectNumsTerm3 += 1
            # print(sc.courseName,course_credit_dic[sc.courseName])
        elif sc[2] == 41 or sc[2] == 42:
            term4[sc[0]] = sc[1]
            sumScore4 += (sc[1] * course_credit_dic[sc[0]])
            credit4 += (course_credit_dic[sc[0]])
            if sc[1] < 60:
                failedSubjectNumsTerm4 += 1
        if sc[1] < 60:
            failedSubjectNamesScores[sc[0]] = sc[1]
            sumFailedCredit += course_credit_dic[sc[0]]

    totalScore = (sumScore1 + sumScore2 + sumScore3 + sumScore4)
    totalCredit = (credit1 + credit2 + credit3 + credit4)
    totalWeightedScore, totalWeightedScoreTerm1, totalWeightedScoreTerm2, totalWeightedScoreTerm3, totalWeightedScoreTerm4 = 0, 0, 0, 0, 0
    if totalCredit != 0.0:
        totalWeightedScore = (totalScore) / (totalCredit * 1.0)
    if credit1 != 0.0:
        totalWeightedScoreTerm1 = sumScore1 / (credit1 * 1.0)
    if credit2 != 0.0:
        totalWeightedScoreTerm2 = sumScore2 / (credit2 * 1.0)
    if credit3 != 0.0:
        totalWeightedScoreTerm3 = sumScore3 / (credit3 * 1.0)
    if credit4 != 0.0:
        totalWeightedScoreTerm4 = sumScore4 / (credit4 * 1.0)

    failedSubjectdict['grade'] = grade
    failedSubjectdict["term1"] = term1
    failedSubjectdict["term2"] = term2
    failedSubjectdict["term3"] = term3
    failedSubjectdict["term4"] = term4
    failedSubjectdict["totalWeightedScore"] = round(totalWeightedScore, 2)
    failedSubjectdict["totalWeightedScoreTerm1"] = round(totalWeightedScoreTerm1, 2)
    failedSubjectdict["totalWeightedScoreTerm2"] = round(totalWeightedScoreTerm2, 2)
    failedSubjectdict["totalWeightedScoreTerm3"] = round(totalWeightedScoreTerm3, 2)
    failedSubjectdict["totalWeightedScoreTerm4"] = round(totalWeightedScoreTerm4, 2)
    failedSubjectdict["failedSubjectNamesScores"] = failedSubjectNamesScores
    failedSubjectdict["failedSubjectNames"] = ",".join([key for key in failedSubjectNamesScores])
    failedSubjectdict["failedSubjectNums"] = len(failedSubjectNamesScores)
    failedSubjectdict["sumFailedCredit"] = sumFailedCredit
    failedSubjectdict["failedSubjectNumsTerm"] = [failedSubjectNumsTerm1, failedSubjectNumsTerm2,
                                                  failedSubjectNumsTerm3, failedSubjectNumsTerm4]
    failedSubjectdict["totalWeightedScoreTerm"] = [round(totalWeightedScoreTerm1, 2), round(totalWeightedScoreTerm2, 2),
                                                   round(totalWeightedScoreTerm3, 2), round(totalWeightedScoreTerm4, 2)]
    # 获取其个人评价
    stuAnalysisInfo = db.query(models.StuAnalysis).filter(models.StuAnalysis.stuID == stuID, models.StuAnalysis.stuType == 3).all()

    selfContent = {}
    if stuAnalysisInfo:
        for i in range(len(stuAnalysisInfo)):
            selfContent["term" + str(stuAnalysisInfo[i].term // 10) + "_selfcontent"] = stuAnalysisInfo[i].content1
    failedSubjectdict["selfContent"] = selfContent
    # print()
    # print(sumScore3, credit3)
    return failedSubjectdict
    # return jsonify(errno=RET.OK,errmsg="OK")


async def get_stuInfo(db:Session,stuID,course_credit_dic):
    """
    根据学号，找到这个学生需要的所有信息
    :param stuID:
    :return:
    {
        "stuID": "stuID",
        "stuName": "stuName",
        "stuClass": "CS1707",
        "11":{
            "微积分": "67",
            "线性代数": "80"
        },
        “12”:{
            "微积分": "67",
            "线性代数": "80"
        },
        "failSubjects": {
            "微积分": "57",
            "计算机组成原理": "34"
        },
        "totalWeightedScore:totalWeightedScore,
        "totalWeightedScoreTerm1“:totalWeightedScoreTerm1,
        "totalWeightedScoreTerm3":totalWeightedScoreTerm3,
        "totalWeightedScoreTerm4":totalWeightedScoreTerm4
    }
    """
    # print(course_credit_dic)
    term1,term2,term3,term4 = {},{},{},{}
    failedSubjectdict = {}
    failedSubjectdict["stuID"] = stuID
    stuClass = db.query(models.Student).filter(models.Student.stuID==stuID).with_entities(models.Student.stuClass,models.Student.stuName).first()
    # print("stuClass: ",stuClass,stuID)
    failedSubjectdict["stuName"] = stuClass[1]
    failedSubjectdict["stuClass"] = stuClass[0]
    scoreList = db.query(models.Scores).filter(models.Scores.stuID == stuID).all()
    credit1,credit2,credit3,credit4 = 0.0,0.0,0.0,0.0
    sumScore1,sumScore2,sumScore3,sumScore4 = 0.0,0.0,0.0,0.0
    failedSubjectNamesScores = {}
    sumFailedCredit = 0.0
    failedSubjectNumsTerm1,failedSubjectNumsTerm2,failedSubjectNumsTerm3,failedSubjectNumsTerm4 = 0,0,0,0
    print("="*50)
    print(type(course_credit_dic))
    print(course_credit_dic)
    if(not isinstance(course_credit_dic,dict)):
        course_credit_dic = json.loads(str(course_credit_dic))
    print(type(course_credit_dic))
    for sc in scoreList:
        # print(sc.courseName,sc.score,sc.term)
        if sc.term == 11 or sc.term == 12:
            term1[sc.courseName] = sc.score
            sumScore1 += (sc.score*course_credit_dic[sc.courseName])
            credit1 += (course_credit_dic[sc.courseName])
            if sc.score < 60:
                failedSubjectNumsTerm1 += 1
        elif sc.term == 21 or sc.term == 22:
            term2[sc.courseName] = sc.score
            sumScore2 += (sc.score*course_credit_dic[sc.courseName])
            credit2 += (course_credit_dic[sc.courseName])
            if sc.score < 60:
                failedSubjectNumsTerm2 += 1
        elif sc.term == 31 or sc.term == 32:
            term3[sc.courseName] = sc.score
            sumScore3 += (sc.score*course_credit_dic[sc.courseName])
            credit3 += (course_credit_dic[sc.courseName])
            if sc.score < 60:
                failedSubjectNumsTerm3 += 1
            # print(sc.courseName,course_credit_dic[sc.courseName])
        elif sc.term == 41 or sc.term == 42:
            term4[sc.courseName] = sc.score
            sumScore4 += (sc.score*course_credit_dic[sc.courseName])
            credit4 += (course_credit_dic[sc.courseName])
            if sc.score < 60:
                failedSubjectNumsTerm4 += 1
        if sc.score < 60:
            failedSubjectNamesScores[sc.courseName] = sc.score
            sumFailedCredit += course_credit_dic[sc.courseName]
        pass

    totalScore = (sumScore1+sumScore2+sumScore3+sumScore4)
    totalCredit = (credit1 + credit2 + credit3 + credit4)
    totalWeightedScore,totalWeightedScoreTerm1,totalWeightedScoreTerm2,totalWeightedScoreTerm3,totalWeightedScoreTerm4=0,0,0,0,0
    if totalCredit != 0.0:
        totalWeightedScore = (totalScore)/(totalCredit*1.0)
    if credit1 != 0.0:
        totalWeightedScoreTerm1 = sumScore1/(credit1*1.0)
    if credit2 != 0.0:
        totalWeightedScoreTerm2 = sumScore2/(credit2*1.0)
    if credit3 != 0.0:
        totalWeightedScoreTerm3 = sumScore3/(credit3*1.0)
    if credit4 != 0.0:
        totalWeightedScoreTerm4 = sumScore4/(credit4*1.0)

    failedSubjectdict["term1"] = term1
    failedSubjectdict["term2"] = term2
    failedSubjectdict["term3"] = term3
    failedSubjectdict["term4"] = term4
    failedSubjectdict["totalWeightedScore"] =round(totalWeightedScore,2)
    failedSubjectdict["totalWeightedScoreTerm1"] = round(totalWeightedScoreTerm1,2)
    failedSubjectdict["totalWeightedScoreTerm2"] = round(totalWeightedScoreTerm2,2)
    failedSubjectdict["totalWeightedScoreTerm3"] = round(totalWeightedScoreTerm3,2)
    failedSubjectdict["totalWeightedScoreTerm4"] = round(totalWeightedScoreTerm4,2)
    failedSubjectdict["failedSubjectNamesScores"] = failedSubjectNamesScores
    failedSubjectdict["failedSubjectNames"] = ",".join([key for key in failedSubjectNamesScores])
    failedSubjectdict["failedSubjectNums"] = len(failedSubjectNamesScores)
    failedSubjectdict["sumFailedCredit"] = sumFailedCredit
    failedSubjectdict["failedSubjectNumsTerm"]=[failedSubjectNumsTerm1,failedSubjectNumsTerm2,failedSubjectNumsTerm3,failedSubjectNumsTerm4]
    failedSubjectdict["totalWeightedScoreTerm"] = [round(totalWeightedScoreTerm1,2),round(totalWeightedScoreTerm2,2),round(totalWeightedScoreTerm3,2),round(totalWeightedScoreTerm4,2)]
    # 获取其个人评价
    stuAnalysisInfo = db.query(models.StuAnalysis).filter(models.StuAnalysis.stuID == stuID,models.StuAnalysis.stuType==3).all()

    selfContent = {}
    if stuAnalysisInfo:
        for i in range(len(stuAnalysisInfo)):
            selfContent["term"+str(stuAnalysisInfo[i].term//10)+"_selfcontent"] = stuAnalysisInfo[i].content1
    failedSubjectdict["selfContent"] = selfContent
    # print()
    # print(sumScore3, credit3)
    return failedSubjectdict
    # return jsonify(errno=RET.OK,errmsg="OK")




