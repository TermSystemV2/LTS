import json
import logging
import typing as t

from fastapi import APIRouter, Request, Response, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy import distinct, and_, func, create_engine
from aioredis import Redis

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config
from .commonCourse import get_each_grade_class_number

classDim_router = APIRouter()


@classDim_router.post("/scores/class/table/<term>")
async def get_class_table_by_term(queryItem: schemas.ClassQuery, db: Session = Depends(get_db),
                                  redis_store: Redis = Depends(course_cache)):
    """
    {
        [
            {
            "className": "CS2006",
            "failedNum": 1, # 挂科人数
            "failedNum2": 1, # 挂科人次
            "failedRange": "100.00", # 挂科幅度
            "failedRate": "3.00",
            "failedThreeNum": 0,
            "grade": "20",
            "id": "term11_CS2006",
            "totalNum": 30
          }
        ]
    }
    :param queryItem:
    :param db:
    :param redis_store:
    :return:
    """
    term = int(queryItem.term)
    redis_key = "class_by_term_table_" + str(term)
    state = await redis_store.exists(redis_key)
    if state == 0:
        if config.UPDATE_DATA:  # 更新数据模型
            ret = []
            # 找到四个年级
            grade_class_info = await get_each_grade_class_number(db, redis_store)
            for grade in grade_class_info["class_nums_student"].keys():
                for className in grade_class_info["class_nums_student"][grade]:
                    tmpDict = {
                        "term": str(term),
                        "className": className,
                        "totalNum": grade_class_info["class_nums_student"][grade][className],
                        "failedNum": 0,  # 挂科人数
                        "failedThreeNum": 0,  # 3门及以上的人
                        "failedNum2": 0,  # 挂科人次 重复计算
                        "failedRate": 0,  # 挂科率
                        "failedRange": 0  # 挂科幅度
                    }
                    res_class = db.query(models.Scores).join(models.Student, models.Scores.stuID == models.Student.stuID,
                                                             isouter=True). \
                        filter(
                        and_(models.Student.stuClass == className, models.Scores.term == term, models.Scores.score < 60)). \
                        with_entities(models.Scores.stuID, models.Scores.courseName, models.Scores.score,
                                      models.Student.stuClass).all()
                    print("res_class" + " =" * 50)
                    tmpDict["failedNum2"] = len(res_class)  # 人次
                    failedNum = []  # 人数
                    failedThreeNum = {}
                    for row in res_class:
                        if row[0] not in failedNum:
                            failedNum.append(row[0])
                        if row[0] not in failedThreeNum:
                            failedThreeNum[row[0]] = 1
                        else:
                            failedThreeNum[row[0]] += 1
                    for stuID in failedThreeNum.keys():
                        if failedThreeNum[stuID] >= 3:
                            tmpDict["failedThreeNum"] += 1

                    tmpDict["failedNum"] = len(failedNum)
                    if tmpDict["totalNum"] != 0:
                        tmpDict["failedRate"] = round(
                            tmpDict["failedNum"] / (tmpDict["totalNum"] * 1.0), 4) * 100
                        tmpDict["failedRate"] = float(
                            "{:.2f}".format(tmpDict["failedRate"]))

                    if tmpDict["failedNum"] != 0:
                        tmpDict["failedRange"] = round(
                            tmpDict["failedNum2"] / (tmpDict["failedNum"] * 1.0), 4) * 100
                        tmpDict["failedRange"] = float(
                            "{:.2f}".format(tmpDict["failedRange"]))
                    ret.append(tmpDict)
            if len(ret) != 0:
                # 将计算好的数据写入数据库
                for classItem in ret:
                    classItemQuery = db.query(models.ClassByTermTable).filter(and_(
                            models.ClassByTermTable.term == classItem['term'], models.ClassByTermTable.className == str(classItem['className'])
                    )).first()
                    # print("="*50)
                    # print(classItemQuery)
                    if classItemQuery:
                        continue
                    print("将 班级维度的表数据计算 结果存入数据库 ...")
                    classItemInsert = models.ClassByTermTable(
                        term = classItem['term'],
                        className = classItem['className'],
                        totalNum = classItem['totalNum'],
                        failedNum = classItem['failedNum'],
                        failedThreeNum = classItem['failedThreeNum'],
                        failedNum2 = classItem['failedNum2'],
                        failedRate = classItem['failedRate'],
                        failedRange = classItem['failedRange']
                    )
                    db.add(classItemInsert)
                    db.commit()
                    db.refresh(classItemInsert)
                
            else:
                return Response400(msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空")
        else:
            # 直接读取计算好的数据
            retDb = db.query(models.ClassByTermTable).filter(models.ClassByTermTable.term == str(term)).all()
            ret = []
            # print("="*50)
            for dbItem in retDb:
                ret.append(
                    {
                        "term": dbItem.term,
                        "className": dbItem.className,
                        "totalNum" : dbItem.totalNum,
                        "failedNum" : dbItem.failedNum,
                        "failedThreeNum" : dbItem.failedThreeNum,
                        "failedNum2" : dbItem.failedNum2,
                        "failedRate" : dbItem.failedRate,
                        "failedRange" : dbItem.failedRange
                    }
                )
        # 写入 redis
        await redis_store.setex(redis_key, config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,json.dumps(ret, ensure_ascii=False))
    else:
        ret = json.loads(await redis_store.get(redis_key))

    return Response200(data=ret)


@classDim_router.post("/scores/class/chart/<term>")
async def get_class_chart_by_term(queryItem: schemas.ClassQuery, db: Session = Depends(get_db),
                                  redis_store: Redis = Depends(course_cache)):
    """
    班级维度图标

    :param queryItem:
    :param db:
    :param redis_store:
    :return: [
         {
            "term": "11",
            "grade": "18",
            "classNameList": [
                "卓越\n1801",
                "ACM1801",
                "计科\n1801",
            ],
            "failedNum": [
                0,
                0,
                3
            ],
            "failedRate": [
                0.0,
                0.0,
                11.0
            ]
         }
    ]
    """
    print(queryItem.term)
    term = int(queryItem.term)
    print("term:{}".format(term))
    redis_key = "class_by_term_chart_" + str(term)
    state = await redis_store.exists(redis_key)
    if state == 0:
        if config.UPDATE_DATA:  # 更新数据
            ret = []
            # 找到四个年级
            grade_class_info = await get_each_grade_class_number(db, redis_store)
            print("get_class_chart_by_term:{}".format(grade_class_info))
            for grade in grade_class_info["grade"].keys():
                tmpDict = {
                    "classNameList": [],
                    "failedNum": [],
                    "failedRate": [],  # 挂科人数
                    "grade": str(grade),
                    "id": "term_" + str(term) + "_" + str(grade)
                }
                for className in grade_class_info["class_nums_student"][grade]:
                    res_class = db.query(models.Scores).join(models.Student, models.Scores.stuID == models.Student.stuID,
                                                             isouter=True). \
                        filter(
                        and_(models.Student.stuClass == className, models.Scores.term == term, models.Scores.score < 60)). \
                        with_entities(models.Scores.stuID, models.Scores.courseName, models.Scores.score,
                                      models.Student.stuClass).all()

                    tmpDict["classNameList"].append(className)
                    tmpDict["failedNum"].append(len(res_class))
                    tmpDict["failedRate"].append(
                        float("{:.2f}".format(round(len(res_class) / (grade_class_info["class_nums_student"][str(grade)][className] * 1.0), 4) * 100)))
                    # 修改班级名
                    for i in range(len(tmpDict["classNameList"])):
                        tmp_className = tmpDict["classNameList"][i]
                        tmp_className = tmp_className.replace('CS', '计科\n')
                        tmp_className = tmp_className.replace('BSB', '本硕博\n')
                        tmp_className = tmp_className.replace('IOT', '物联网\n')
                        tmp_className = tmp_className.replace('ZY', '卓越\n')
                        tmp_className = tmp_className.replace('XJ', '校交\n')
                        tmpDict["classNameList"][i] = tmp_className

                ret.append(tmpDict)
                
                if  len(ret) != 0:
                    # 将计算好的数据写入数据库
                    for classItem in ret:
                        classItemQuery = db.query(models.ClassByTermChart).filter(and_(
                            models.ClassByTermChart.id == classItem['id'], models.ClassByTermChart.grade == str(classItem['grade'])
                        )).first()
                        print("="*50)
                        print(classItemQuery)
                        if classItemQuery:
                            continue
                        print("将 班级维度的表数据计算 结果存入数据库 ...")
                        classItemInsert = models.ClassByTermChart(
                            id=classItem['id'],
                            grade=str(classItem['grade']),
                            classNameList=str(classItem['classNameList']),
                            failedNum=str(classItem['failedNum']),
                            failedRate=str(classItem['failedRate'])
                        )
                        db.add(classItemInsert)
                        db.commit()
                        db.refresh(classItemInsert)
                    
                else:
                    return Response400(msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空")
        
        else:  # 直接读取已经计算好的数据
            retDb = db.query(models.ClassByTermChart).filter(models.ClassByTermChart.term == str(term)).all()
            ret = []
            for dbItem in retDb:
                ret.append(
                    {
                        "term": dbItem.term,
                        "grade": dbItem.grade,
                        "classNameList": eval(dbItem.classNameList) if dbItem.classNameList != '' else [],
                        "failedNum": eval(dbItem.failedNum) if dbItem.classNameList != '' else [],
                        "failedRate": eval(dbItem.failedRate)  if dbItem.classNameList != '' else [],
                    }
                )
        
        # 将数据写入 redis
        await redis_store.setex(redis_key, config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES, json.dumps(ret, ensure_ascii=False))
    else:
        ret = json.loads(await redis_store.get(redis_key))

    return Response200(data=ret)
