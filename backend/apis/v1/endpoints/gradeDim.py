import json
import logging
import typing as t

from fastapi import APIRouter, Request, Response, Depends,status,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct,and_,func,create_engine
from aioredis import Redis

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config
from .commonCourse import get_each_grade_class_number, get_lower_course_name

gradeDim_router = APIRouter()

@gradeDim_router.post("/scores/grade/<term>")
async def get_grade_by_term(queryItem:schemas.GradeQuery,db:Session = Depends(get_db),redis_store:Redis= Depends(course_cache)):
    """
    年级维度
    返回四个年级第 term 学期的所有课程信息
    :param term:
    :return:
    """
    term = int(queryItem.term)
    redis_key = "grade_by_term_" + str(term)
    state = await redis_store.exists(redis_key)
    if state == 0:
        # print("get_grade_by_term term:{}".format(term))
        # 1. 得到一些基本信息（年级人数，班级人数）
        each_grade_class_number = await get_each_grade_class_number(db,redis_store)
        # print("each_grade_class_number:{}".format(each_grade_class_number))
        # print(type(each_grade_class_number))
        # 2. 四个grade
        gradeList = each_grade_class_number["grade"].keys()
        # 获取人数较少的（可能是转专业的课程）
        low_courseName_list_grade = await get_lower_course_name(term,gradeList,db,redis_store)

        ret = []
        for grade in gradeList:
            courseInfo = db.query(models.Scores).filter(and_(models.Scores.grade == grade,models.Scores.term == term)).with_entities(models.Scores.courseName,models.Scores.score).all()
            # 将数据组织成
            """
            {
                "courseName":[],
                "failed_nums":[],
                "failed_rates":[]
            }
            """
            tmpDict = {
                "courseName":[],
                "failed_nums":[],
                "failed_rates":[],
                "grade":str(grade)
            }
            for row in courseInfo:
                if row[0] not in low_courseName_list_grade[str(grade)] and row[1] < 60:
                    tmp_coureName = row[0]
                    tmp_coureName = tmp_coureName.replace('（', '︵')
                    tmp_coureName = tmp_coureName.replace('）', '︶')
                    tmp_coureName = tmp_coureName.replace(')', '︶')
                    tmp_coureName = tmp_coureName.replace('(', '︵')
                    if tmp_coureName not in tmpDict["courseName"]:
                        tmpDict["courseName"].append(tmp_coureName)
                        tmpDict["failed_nums"].append(1)
                    else:
                        tmpDict["failed_nums"][tmpDict["courseName"].index(tmp_coureName)] += 1
            gradeNum = each_grade_class_number["grade"][str(grade)]
            for i in range(len(tmpDict["courseName"])):
                tmpDict["failed_rates"].append("{:.2f}".format(float("{:.4f}".format(tmpDict["failed_nums"][i] / gradeNum))*100))

            # 重新排序，具体思路：将数据重组为元组，然后排序，排序之后再打散
            tuple_tmpDict = []
            for i in range(len(tmpDict["courseName"])):
                tuple_tmpDict.append((tmpDict["courseName"][i],tmpDict["failed_nums"][i],tmpDict["failed_rates"][i]))
            tuple_tmpDict = sorted(tuple_tmpDict,key=lambda t:t[1],reverse=True)
            tmpDict = {
                "courseName": [],
                "failed_nums": [],
                "failed_rates": [],
                "grade": str(grade)
            }
            for i in range(len(tuple_tmpDict)):
                tmpDict["courseName"].append(tuple_tmpDict[i][0])
                tmpDict["failed_nums"].append(tuple_tmpDict[i][1])
                tmpDict["failed_rates"].append(tuple_tmpDict[i][2])

            if  0 < len(tmpDict['courseName']) < 8:
                append_len = 8 - len(tmpDict['courseName'])
                append_subjects_courseNames_new = [' ']*append_len
                append_subjects_failed_rates_new = [' ']*append_len
                append_subjects_failed_nums_new = [' ']*append_len
                tmpDict['courseName'] += append_subjects_courseNames_new
                tmpDict['failed_rates'] += append_subjects_failed_rates_new
                tmpDict['failed_nums'] += append_subjects_failed_nums_new

            ret.append(tmpDict)
            if len(ret) !=0:
                await redis_store.setex(redis_key,config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,json.dumps(ret,ensure_ascii=False))
            else:
                return Response400(msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空")
    else:
        ret = json.loads(await redis_store.get(redis_key))

    return Response200(data=ret)




