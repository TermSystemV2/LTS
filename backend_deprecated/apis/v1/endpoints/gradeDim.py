import json
import logging
import typing as t

from fastapi import APIRouter, Request, Response, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct, and_, func, create_engine
from aioredis import Redis

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config
from .commonCourse import (
    get_each_grade_class_number,
    get_lower_course_name_by_term,
    get_grade_list,
)
from utils.common import to_pinyin

gradeDim_router = APIRouter()


@gradeDim_router.post("/scores/grade/<term>")
async def get_grade_by_term(
    queryItem: schemas.GradeQuery,
    db: Session = Depends(get_db),
    redis_store: Redis = Depends(course_cache),
):
    """
    年级维度
    返回四个年级第 term 学期的所有课程信息
    :param term:
    :return:
    """
    term = str(queryItem.term)
    key = "grade_by_term_" + str(term)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    if (not sqlState) or redisState == 0:
        if not sqlState:  # 更新数据
            # 1. 得到一些基本信息（年级人数，班级人数）
            grade_class_info = await get_each_grade_class_number(db, redis_store)
            # 2. 四个grade
            gradeList = await get_grade_list(db)
            # 获取人数较少的（可能是转专业的课程）
            low_course_list = await get_lower_course_name_by_term(
                term, gradeList, db, redis_store
            )

            ret = []
            for grade in gradeList:
                if grade_class_info["total"]["ALL"][str(grade)][str(term)] == 0:
                    continue
                courseNameList = [
                    courseName[0]
                    for courseName in db.query(models.Course)
                    .filter(
                        models.Course.term == term,
                        models.Course.stuClass[-4:-2] == grade,
                    )
                    .with_entities(models.Course.courseName)
                    .distinct()
                    .all()
                ]
                low_course_list = await get_lower_course_name_by_term(
                    term, gradeList, db, redis_store
                )
                courseNameList = [
                    courseName
                    for courseName in courseNameList
                    if (courseName not in config.NOT_SHOW_COURSENAME)
                    and (courseName not in low_course_list)
                ]
                courseNameList = sorted(courseNameList, key=to_pinyin)
                # 将数据组织
                tmpDict = {
                    "term": str(term),
                    "grade": str(grade),
                    "courseName": [],
                    "failedNums": [],
                    "failedRates": [],
                }
                for courseName in courseNameList:
                    tmp_courseName = courseName
                    tmp_courseName = tmp_courseName.replace("（", "︵")
                    tmp_courseName = tmp_courseName.replace("）", "︶")
                    tmp_courseName = tmp_courseName.replace(")", "︶")
                    tmp_courseName = tmp_courseName.replace("(", "︵")
                    tmpDict["courseName"].append(tmp_courseName)

                    res = (
                        db.query(models.FailedRecord)
                        .filter(
                            models.FailedRecord.courseName == courseName,
                            models.FailedRecord.term == term,
                            models.FailedRecord.stuClass[-4:-2] == grade,
                        )
                        .all()
                    )
                    tmpDict["failedNums"].append(len(res))
                    tmpDict["failedRates"].append(
                        round(
                            len(res)
                            / grade_class_info["total"]["ALL"][str(grade)][str(term)]
                            * 100.0,
                            2,
                        )
                    )

                # 重新排序，具体思路：将数据重组为元组，然后排序，排序之后再打散
                tuple_tmpDict = []
                for i in range(len(tmpDict["courseName"])):
                    tuple_tmpDict.append(
                        (
                            tmpDict["courseName"][i],
                            tmpDict["failedNums"][i],
                            tmpDict["failedRates"][i],
                        )
                    )
                tuple_tmpDict = sorted(tuple_tmpDict, key=lambda t: t[1], reverse=True)
                tmpDict = {
                    "term": str(term),
                    "grade": str(grade),
                    "courseName": [],
                    "failedNums": [],
                    "failedRates": [],
                }
                for i in range(len(tuple_tmpDict)):
                    tmpDict["courseName"].append(tuple_tmpDict[i][0])
                    tmpDict["failedNums"].append(tuple_tmpDict[i][1])
                    tmpDict["failedRates"].append(tuple_tmpDict[i][2])

                # bug:???
                if 0 < len(tmpDict["courseName"]) < 8:
                    append_len = 8 - len(tmpDict["courseName"])
                    append_subjects_courseNames_new = [" "] * append_len
                    append_subjects_failed_rates_new = [" "] * append_len
                    append_subjects_failed_nums_new = [" "] * append_len
                    tmpDict["courseName"] += append_subjects_courseNames_new
                    tmpDict["failedRates"] += append_subjects_failed_rates_new
                    tmpDict["failedNums"] += append_subjects_failed_nums_new

                ret.append(tmpDict)
                if len(ret) != 0:
                    # 将计算好的数据写入数据库
                    print("将 年级维度的 计算结果保存到数据库...")
                    for gradeItem in ret:
                        gradeDimInsert = models.GradeByTermChart(
                            term=str(term),
                            grade=str(grade),
                            courseName=json.dumps(
                                gradeItem["courseName"], ensure_ascii=False
                            ),
                            failedNums=json.dumps(
                                gradeItem["failedNums"], ensure_ascii=False
                            ),
                            failedRates=json.dumps(
                                gradeItem["failedRates"], ensure_ascii=False
                            ),
                        )
                        db.add(gradeDimInsert)
                        db.commit()
                        db.refresh(gradeDimInsert)
                else:
                    return Response400(
                        msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空"
                    )
                db.add(models.CalculateState(name=key))
                db.commit()

                await redis_store.setex(
                    key, config.REDIS_CACHE_EXPIRES, json.dumps(ret, ensure_ascii=False)
                )
        else:
            # 直接读取计算好的数据
            retDb = (
                db.query(models.GradeByTermChart)
                .filter(models.GradeByTermChart.term == str(term))
                .all()
            )
            ret = []
            for dbItem in retDb:
                ret.append(
                    {
                        "term": dbItem.term,
                        "grade": dbItem.grade,
                        "courseName": json.loads(dbItem.courseName),
                        "failedNums": json.loads(dbItem.failedNums),
                        "failedRates": json.loads(dbItem.failedRates),
                    }
                )
        if len(ret) != 0:
            # 将数据写入缓存
            await redis_store.setex(
                key, config.REDIS_CACHE_EXPIRES, json.dumps(ret, ensure_ascii=False)
            )
        else:
            return Response400(
                data="中间结果数据库中暂时无数据，请在文件上传页面切换读取数据方式为从原始数据读取之后再请求"
            )
    else:
        ret = json.loads(await redis_store.get(key))

    return Response200(data=ret)
