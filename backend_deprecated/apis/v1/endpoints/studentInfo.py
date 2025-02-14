import json
import logging
from os import stat
from pyexpat import model
import re
from statistics import mode

from fastapi import APIRouter, Request, Response, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from aioredis import Redis


from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import stuInfo_cache
from core.config import config
from database.curd_ec import (
    ec_getCurrentYear,
    ec_get_by_year,
    ec_getYearList,
    ec_get_by_grade,
    ec_gradeToYear,
    ec_getGradeList,
    ec_get_info_by_grade_year,
)
from .commonCourse import (
    get_latest_student_by_stuID,
    get_lower_course_name_by_grade,
    get_latest_term_by_grade,
)
from utils.common import to_pinyin

stuInfo_router = APIRouter()


@stuInfo_router.get("/studentInfo/grade/<grade>")  # test
async def getStudentInfoByGrade(
    grade: int,
    redis_store: Redis = Depends(stuInfo_cache),
    db: Session = Depends(get_db),
):
    """
    请求某个年级的所有不及格学生的信息
    :param grade: 18 19 20 21
    :return:
    """
    key = "studentInfo_" + str(grade)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    if (not sqlState) or redisState == 0:
        if not sqlState:  # 更新数据
            course_credit_list = await get_course_and_credit_list(
                db, redis_store, grade
            )  # 课程:学分
            allFailedStudentInfos = []
            # 从score 中获取所有成绩有不及格情况的同学
            stuIDList = await get_failedStuID_by_grade(db, redis_store, grade)

            for stuID in stuIDList:
                dict_stuInfo = await get_stuInfo_by_grade(db, stuID, course_credit_list)
                allFailedStudentInfos.append(dict_stuInfo)
                # classNameList.append(dict_stuInfo["stuClass"])
            # print(classNameList)
            # 对结果进行排序
            allFailedStudentInfos.sort(
                key=lambda k: (k.get("sumFailedCredit")), reverse=True
            )
            index = 1
            for stuInfo in allFailedStudentInfos:
                stuInfo["index"] = index
                index += 1

            if len(allFailedStudentInfos) != 0:
                # 将计算好的数据写入到数据库
                for studentInfoItem in allFailedStudentInfos:
                    studentInfoQuery = (
                        db.query(models.StudentInfo)
                        .filter(
                            and_(
                                models.StudentInfo.grade
                                == str(studentInfoItem["grade"]),
                                models.StudentInfo.stuID == studentInfoItem["stuID"],
                            )
                        )
                        .first()
                    )
                    if studentInfoQuery:
                        db.query(models.StudentInfo).filter(
                            and_(
                                models.StudentInfo.grade
                                == str(studentInfoItem["grade"]),
                                models.StudentInfo.stuID == studentInfoItem["stuID"],
                            )
                        ).delete()
                        # db.delete(isInTable)
                        db.commit()
                    print("将 学生信息 计算结果保存到数据库...")
                    gradeDimInsert = models.StudentInfo(
                        index=str(studentInfoItem["index"]),
                        grade=str(grade),
                        stuID=studentInfoItem["stuID"],
                        stuName=studentInfoItem["stuName"],
                        stuClass=studentInfoItem["stuClass"],
                        term1=str(studentInfoItem["term1"]),
                        term2=str(studentInfoItem["term2"]),
                        term3=str(studentInfoItem["term3"]),
                        term4=str(studentInfoItem["term4"]),
                        totalWeightedScore=studentInfoItem["totalWeightedScore"],
                        totalWeightedScoreTerm1=studentInfoItem[
                            "totalWeightedScoreTerm1"
                        ],
                        totalWeightedScoreTerm2=studentInfoItem[
                            "totalWeightedScoreTerm2"
                        ],
                        totalWeightedScoreTerm3=studentInfoItem[
                            "totalWeightedScoreTerm3"
                        ],
                        totalWeightedScoreTerm4=studentInfoItem[
                            "totalWeightedScoreTerm4"
                        ],
                        failedSubjectNamesScores=str(
                            studentInfoItem["failedSubjectNamesScores"]
                        ),
                        failedSubjectNames=str(studentInfoItem["failedSubjectNames"]),
                        failedSubjectNums=studentInfoItem["failedSubjectNums"],
                        sumFailedCredit=studentInfoItem["sumFailedCredit"],
                        totalCredit=studentInfoItem["totalCredit"],
                        totalFailedCreditTerm=str(
                            studentInfoItem["totalFailedCreditTerm"]
                        ),
                        failedSubjectNumsTerm=str(
                            studentInfoItem["failedSubjectNumsTerm"]
                        ),
                        totalWeightedScoreTerm=str(
                            studentInfoItem["totalWeightedScoreTerm"]
                        ),
                        selfContent=str(studentInfoItem["selfContent"]),
                    )
                    db.add(gradeDimInsert)
                    db.commit()
                    db.refresh(gradeDimInsert)
                # resp_json = json.loads(resp_json)

                # return Response200(data=allFailedStudentInfos)
            else:
                return Response400(
                    msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空"
                )

        else:
            # 直接读取已经计算好的数据
            retDb = (
                db.query(models.StudentInfo)
                .filter(models.StudentInfo.grade == str(grade))
                .all()
            )
            allFailedStudentInfos = []
            # print("="*50)
            for dbItem in retDb:
                allFailedStudentInfos.append(
                    {
                        "index": dbItem.index,
                        "grade": dbItem.grade,
                        "stuID": dbItem.stuID,
                        "stuName": dbItem.stuName,
                        "stuClass": dbItem.stuClass,
                        "term1": eval(dbItem.term1) if dbItem.term1 != "" else [],
                        "term2": eval(dbItem.term2) if dbItem.term2 != "" else [],
                        "term3": eval(dbItem.term3) if dbItem.term3 != "" else [],
                        "term4": eval(dbItem.term4) if dbItem.term4 != "" else [],
                        "totalWeightedScore": dbItem.totalWeightedScore,
                        "totalWeightedScoreTerm1": dbItem.totalWeightedScoreTerm1,
                        "totalWeightedScoreTerm2": dbItem.totalWeightedScoreTerm2,
                        "totalWeightedScoreTerm3": dbItem.totalWeightedScoreTerm3,
                        "totalWeightedScoreTerm4": dbItem.totalWeightedScoreTerm4,
                        "failedSubjectNamesScores": (
                            eval(dbItem.failedSubjectNamesScores)
                            if dbItem.failedSubjectNamesScores != ""
                            else []
                        ),
                        "failedSubjectNames": dbItem.failedSubjectNames,
                        "failedSubjectNums": dbItem.failedSubjectNums,
                        "sumFailedCredit": dbItem.sumFailedCredit,
                        "totalCredit": dbItem.totalCredit,
                        "failedSubjectNumsTerm": eval(dbItem.failedSubjectNumsTerm),
                        "totalWeightedScoreTerm": eval(dbItem.totalWeightedScoreTerm),
                        "totalFailedCreditTerm": eval(dbItem.totalFailedCreditTerm),
                        "selfContent": (
                            eval(dbItem.selfContent) if dbItem.selfContent != "" else {}
                        ),
                    }
                )
        # 将数据写入 redis
        if len(allFailedStudentInfos) != 0:
            try:

                resp_json = json.dumps(allFailedStudentInfos, ensure_ascii=False)
                await redis_store.setex(
                    "studentInfo_" + str(grade),
                    config.REDIS_CACHE_EXPIRES,
                    resp_json,
                )
            except Exception as E:
                logging.error("写入 redis 异常 %s" % E)

                return Response400(msg="写入 redis 异常 %s" % str(E))
        else:
            return Response400(
                data="中间结果数据库中暂时无数据，请在文件上传页面切换读取数据方式为从原始数据读取之后再请求"
            )
        return Response200(data=allFailedStudentInfos)
    else:
        resp_data = await redis_store.get("studentInfo_" + str(grade))
        # print("type(resp_data) ",type(json.loads(resp_data)))
        if isinstance(resp_data, str):
            resp_data = json.loads(resp_data)
        return Response200(data=resp_data)


async def get_course_and_credit_list(db: Session, redis_store: Redis, grade):
    """

    :return:
    {
        "courseName1":credit1,
        "courseName2":credit2,
    }
    """
    key = "dict_course_and_credit_list"
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    course_credit_list = []
    if (not sqlState) or redisState == 0:
        if not sqlState:
            courseList: list[models.Course] = (
                db.query(models.Course)
                .filter(models.Course.stuClass[-4:-2] == str(grade))
                .distinct()
                .all()
            )
            lower_course = await get_lower_course_name_by_grade(grade, db, redis_store)
            for course in courseList:
                if course.courseName not in lower_course:
                    course_credit_list.append(course.courseName)
            course_credit_list.sort(key=to_pinyin)
            ret = json.dumps(course_credit_list, ensure_ascii=False)
            db.add(models.CalculateState(name=key))
            db.add(models.ResultDict(key=key, value=ret))
            db.commit()

            await redis_store.setex(key, config.REDIS_CACHE_EXPIRES, ret)
        else:
            ret = (
                db.query(models.ResultDict.value)
                .filter(models.ResultDict.key == key)
                .scalar()
            )
            course_credit_list = json.loads(ret)
            await redis_store.setex(key, config.REDIS_CACHE_EXPIRES, ret)
    else:
        course_credit_list = json.loads(await redis_store.get(key))
    return course_credit_list


async def get_failedStuID_by_grade(db: Session, redis_store: Redis, grade):
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
    key = "failedStuID_" + str(grade)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    ret = []
    if (not sqlState) or redisState == 0:
        if not sqlState:
            stuIDList = db.query(models.FailedRecord.stuID).distinct().all()
            for stuID in stuIDList:
                student: models.Student = await get_latest_student_by_stuID(db, stuID)
                if student.stuClass[-4:-2] == str(grade):
                    ret.append(stuID)
            ret.sort()
            ret = json.dumps(ret, ensure_ascii=False)
            db.add(models.CalculateState(name=key))
            db.add(models.ResultDict(key=key, value=ret))
            db.commit()

            await redis_store.setex(key, config.REDIS_CACHE_EXPIRES, ret)
            ret = json.loads(ret)
        else:
            ret = (
                db.query(models.ResultDict.value)
                .filter(models.ResultDict.key == key)
                .scalar()
            )
            await redis_store.setex(key, config.REDIS_CACHE_EXPIRES, ret)
            ret = json.loads(ret)
    else:
        ret = json.loads(await redis_store.get(key))
    return ret


# todo
async def get_stuInfo_by_grade(db: Session, stuID, course_credit_list):
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
            "totalWeightedScoreTerm4":totalWeightedScoreTerm4.
            "totalFailedCreditTerm":totalFailedCreditTerm
        }
        """
    termList = ["11", "12", "21", "22", "31", "32", "41", "42"]
    term1, term2, term3, term4 = {}, {}, {}, {}
    totalFailedCreditTerm = [0, 0, 0, 0]
    failedDict = {}
    failedDict["stuID"] = stuID
    student: models.Student = await get_latest_student_by_stuID(db, stuID)
    failedDict["stuName"] = student.stuName
    failedDict["stuClass"] = student.stuClass
    grade = student.stuClass[-4:-2]
    latestTerm = get_latest_term_by_grade(db, grade)
    scoreList = (
        db.query(models.Score)
        .filter(models.Score.stuID == stuID)
        .with_entities(models.Score.courseName, models.Score.score)
        .distinct()
        .all()
    )
    credit1, credit2, credit3, credit4 = 0.0, 0.0, 0.0, 0.0  # 每学年所有课程的学分
    failedCredit1, failedCredit2, failedCredit3, failedCredit4 = (
        0.0,
        0.0,
        0.0,
        0.0,
    )  # 每学年所有课程的学分
    sumScore1, sumScore2, sumScore3, sumScore4 = 0.0, 0.0, 0.0, 0.0
    failedSubjectNamesScores = {}
    sumFailedCredit = 0.0
    (
        failedSubjectNumsTerm1,
        failedSubjectNumsTerm2,
        failedSubjectNumsTerm3,
        failedSubjectNumsTerm4,
    ) = (0, 0, 0, 0)
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
            sumScore1 += sc[1] * course_credit_list[sc[0]]
            credit1 += course_credit_list[sc[0]]
            if sc[1] < 60:
                failedSubjectNumsTerm1 += 1
                failedCredit1 += course_credit_list[sc[0]]
        elif sc[2] == 21 or sc[2] == 22:
            # print("="*20)
            # print(sc)
            # print("couse_credict ",type(course_credit_dic))
            # print(type(sc[0]))
            # print(type(course_credit_dic[sc[0]]))
            # print(type(sc[1]))
            # print("="*20)
            term2[sc[0]] = sc[1]
            sumScore2 += sc[1] * course_credit_list[sc[0]]
            credit2 += course_credit_list[sc[0]]
            if sc[1] < 60:
                failedSubjectNumsTerm2 += 1
                failedCredit2 += course_credit_list[sc[0]]
        elif sc[2] == 31 or sc[2] == 32:
            term3[sc[0]] = sc[1]
            sumScore3 += sc[1] * course_credit_list[sc[0]]
            credit3 += course_credit_list[sc[0]]
            if sc[1] < 60:
                failedSubjectNumsTerm3 += 1
                failedCredit3 += course_credit_list[sc[0]]
            # print(sc.courseName,course_credit_dic[sc.courseName])
        elif sc[2] == 41 or sc[2] == 42:
            term4[sc[0]] = sc[1]
            sumScore4 += sc[1] * course_credit_list[sc[0]]
            credit4 += course_credit_list[sc[0]]
            if sc[1] < 60:
                failedSubjectNumsTerm4 += 1
                failedCredit4 += course_credit_list[sc[0]]
        if sc[1] < 60:
            failedSubjectNamesScores[sc[0]] = sc[1]
            sumFailedCredit += course_credit_list[sc[0]]

    totalScore = sumScore1 + sumScore2 + sumScore3 + sumScore4
    totalCredit = credit1 + credit2 + credit3 + credit4

    (
        totalWeightedScore,
        totalWeightedScoreTerm1,
        totalWeightedScoreTerm2,
        totalWeightedScoreTerm3,
        totalWeightedScoreTerm4,
    ) = (0, 0, 0, 0, 0)
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

    failedDict["grade"] = grade
    failedDict["term1"] = term1
    failedDict["term2"] = term2
    failedDict["term3"] = term3
    failedDict["term4"] = term4
    failedDict["totalWeightedScore"] = round(totalWeightedScore, 2)
    failedDict["totalWeightedScoreTerm1"] = round(totalWeightedScoreTerm1, 2)
    failedDict["totalWeightedScoreTerm2"] = round(totalWeightedScoreTerm2, 2)
    failedDict["totalWeightedScoreTerm3"] = round(totalWeightedScoreTerm3, 2)
    failedDict["totalWeightedScoreTerm4"] = round(totalWeightedScoreTerm4, 2)
    failedDict["failedSubjectNamesScores"] = failedSubjectNamesScores
    failedDict["failedSubjectNames"] = ",".join(
        [key for key in failedSubjectNamesScores]
    )
    failedDict["failedSubjectNums"] = len(failedSubjectNamesScores)
    failedDict["sumFailedCredit"] = sumFailedCredit
    failedDict["totalCredit"] = totalCredit
    failedDict["failedSubjectNumsTerm"] = [
        failedSubjectNumsTerm1,
        failedSubjectNumsTerm2,
        failedSubjectNumsTerm3,
        failedSubjectNumsTerm4,
    ]
    failedDict["totalWeightedScoreTerm"] = [
        round(totalWeightedScoreTerm1, 2),
        round(totalWeightedScoreTerm2, 2),
        round(totalWeightedScoreTerm3, 2),
        round(totalWeightedScoreTerm4, 2),
    ]
    failedDict["totalFailedCreditTerm"] = [
        failedCredit1,
        failedCredit2,
        failedCredit3,
        failedCredit4,
    ]
    # 获取其个人评价
    stuAnalysisInfo = (
        db.query(models.StuAnalysis)
        .filter(models.StuAnalysis.stuID == stuID, models.StuAnalysis.stuType == 3)
        .all()
    )

    selfContent = {}
    if stuAnalysisInfo:
        for i in range(len(stuAnalysisInfo)):
            selfContent[
                "term" + str(stuAnalysisInfo[i].term // 10) + "_selfcontent"
            ] = stuAnalysisInfo[i].content1
    failedDict["selfContent"] = selfContent
    # print()
    # print(sumScore3, credit3)
    return failedDict
    # return jsonify(errno=RET.OK,errmsg="OK")


# todo
async def get_stuInfo(db: Session, stuID, course_credit_dic):
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
    stuClass = (
        db.query(models.Student)
        .filter(models.Student.stuID == stuID)
        .with_entities(models.Student.stuClass, models.Student.stuName)
        .first()
    )
    # print("stuClass: ",stuClass,stuID)
    failedSubjectdict["stuName"] = stuClass[1]
    failedSubjectdict["stuClass"] = stuClass[0]
    scoreList = db.query(models.Score).filter(models.Score.stuID == stuID).all()
    credit1, credit2, credit3, credit4 = 0.0, 0.0, 0.0, 0.0
    sumScore1, sumScore2, sumScore3, sumScore4 = 0.0, 0.0, 0.0, 0.0
    failedSubjectNamesScores = {}
    sumFailedCredit = 0.0
    (
        failedSubjectNumsTerm1,
        failedSubjectNumsTerm2,
        failedSubjectNumsTerm3,
        failedSubjectNumsTerm4,
    ) = (0, 0, 0, 0)
    print("=" * 50)
    print(type(course_credit_dic))
    print(course_credit_dic)
    if not isinstance(course_credit_dic, dict):
        course_credit_dic = json.loads(str(course_credit_dic))
    print(type(course_credit_dic))
    for sc in scoreList:
        # print(sc.courseName,sc.score,sc.term)
        if sc.term == 11 or sc.term == 12:
            term1[sc.courseName] = sc.score
            sumScore1 += sc.score * course_credit_dic[sc.courseName]
            credit1 += course_credit_dic[sc.courseName]
            if sc.score < 60:
                failedSubjectNumsTerm1 += 1
        elif sc.term == 21 or sc.term == 22:
            term2[sc.courseName] = sc.score
            sumScore2 += sc.score * course_credit_dic[sc.courseName]
            credit2 += course_credit_dic[sc.courseName]
            if sc.score < 60:
                failedSubjectNumsTerm2 += 1
        elif sc.term == 31 or sc.term == 32:
            term3[sc.courseName] = sc.score
            sumScore3 += sc.score * course_credit_dic[sc.courseName]
            credit3 += course_credit_dic[sc.courseName]
            if sc.score < 60:
                failedSubjectNumsTerm3 += 1
            # print(sc.courseName,course_credit_dic[sc.courseName])
        elif sc.term == 41 or sc.term == 42:
            term4[sc.courseName] = sc.score
            sumScore4 += sc.score * course_credit_dic[sc.courseName]
            credit4 += course_credit_dic[sc.courseName]
            if sc.score < 60:
                failedSubjectNumsTerm4 += 1
        if sc.score < 60:
            failedSubjectNamesScores[sc.courseName] = sc.score
            sumFailedCredit += course_credit_dic[sc.courseName]
        pass

    totalScore = sumScore1 + sumScore2 + sumScore3 + sumScore4
    totalCredit = credit1 + credit2 + credit3 + credit4
    (
        totalWeightedScore,
        totalWeightedScoreTerm1,
        totalWeightedScoreTerm2,
        totalWeightedScoreTerm3,
        totalWeightedScoreTerm4,
    ) = (0, 0, 0, 0, 0)
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
    failedSubjectdict["failedSubjectNames"] = ",".join(
        [key for key in failedSubjectNamesScores]
    )
    failedSubjectdict["failedSubjectNums"] = len(failedSubjectNamesScores)
    failedSubjectdict["sumFailedCredit"] = sumFailedCredit
    failedSubjectdict["totalCredit"] = totalCredit
    failedSubjectdict["failedSubjectNumsTerm"] = [
        failedSubjectNumsTerm1,
        failedSubjectNumsTerm2,
        failedSubjectNumsTerm3,
        failedSubjectNumsTerm4,
    ]
    failedSubjectdict["totalWeightedScoreTerm"] = [
        round(totalWeightedScoreTerm1, 2),
        round(totalWeightedScoreTerm2, 2),
        round(totalWeightedScoreTerm3, 2),
        round(totalWeightedScoreTerm4, 2),
    ]
    # 获取其个人评价
    stuAnalysisInfo = (
        db.query(models.StuAnalysis)
        .filter(models.StuAnalysis.stuID == stuID, models.StuAnalysis.stuType == 3)
        .all()
    )

    selfContent = {}
    if stuAnalysisInfo:
        for i in range(len(stuAnalysisInfo)):
            selfContent[
                "term" + str(stuAnalysisInfo[i].term // 10) + "_selfcontent"
            ] = stuAnalysisInfo[i].content1
    failedSubjectdict["selfContent"] = selfContent
    # print()
    # print(sumScore3, credit3)
    return failedSubjectdict
    # return jsonify(errno=RET.OK,errmsg="OK")
