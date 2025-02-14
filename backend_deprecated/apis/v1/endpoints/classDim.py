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
from .commonCourse import get_each_grade_class_number, get_grade_list
import re

classDim_router = APIRouter()


@classDim_router.post("/scores/class/chart")
async def get_class_chart_by_term(
    queryItem: schemas.ClassQuery,
    db: Session = Depends(get_db),
    redis_store: Redis = Depends(course_cache),
):
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
    term = str(queryItem.term)
    print("term:{}".format(term))
    key = "class_by_term_chart_" + str(term)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    ret = []
    if (not sqlState) or redisState == 0:
        # 获取状态
        if not sqlState:  # 更新数据
            # 找到四个年级
            gradeList = json.loads(
                db.query(models.ResultDict.value)
                .filter(models.ResultDict.key == "grade_list")
                .scalar()
            )
            grade_class_info = await get_each_grade_class_number(db, redis_store)
            print("get_class_chart_by_term:{}".format(grade_class_info))
            for grade in gradeList:
                tmpDict = {
                    "classNameList": [],
                    "failedNum": [],  # 挂科人数
                    "failedRate": [],
                    "totalNum": [],  # 各班总人数
                }
                tmpDictMajor = {
                    "classNameList": [],
                    "failedNum": [],  # 挂科人数
                    "failedRate": [],
                    "totalNum": [],  # 各班总人数
                }
                count = 0
                lastMajorIndex = 0
                for className in grade_class_info["details"][str(grade)][str(term)]:
                    if (
                        count == 0
                        or re.search(
                            r"[A-Z]+", tmpDict["classNameList"][count - 1]
                        ).group()
                        != re.search(r"[A-Z]+", className).group()
                    ):
                        tmpDictMajor["classNameList"].append(
                            re.search(r"[A-Z]+", className).group()
                        )
                        tmpDictMajor["failedNum"].append(0)
                        tmpDictMajor["failedRate"].append(0)
                        tmpDictMajor["totalNum"].append(0)
                        lastMajorIndex += 1
                    res = (
                        db.query(models.FailedRecord.stuID)
                        .filter(
                            models.FailedRecord.stuClass == className,
                            models.FailedRecord.term == term,
                        )
                        .distinct()
                        .all()
                    )
                    tmpDict["classNameList"].append(className)
                    tmpDict["failedNum"].append(len(res))
                    tmpDictMajor["failedNum"][lastMajorIndex - 1] += len(res)
                    tmpDict["failedRate"].append(0)
                    tmpDict["totalNum"].append(
                        grade_class_info["details"][str(grade)][str(term)][
                            str(className)
                        ]
                    )
                    tmpDictMajor["totalNum"][lastMajorIndex - 1] += grade_class_info[
                        "details"
                    ][str(grade)][str(term)][str(className)]
                    count += 1

                # 计算不及格率，修改班级名
                for i in range(len(tmpDict["classNameList"])):
                    if tmpDict["totalNum"][i] != 0:
                        tmpDict["failedRate"][i] = round(
                            tmpDict["failedNum"][i] / tmpDict["totalNum"][i] * 100, 2
                        )

                    tmp_className = tmpDict["classNameList"][i]
                    if tmp_className == "":
                        continue
                    tmp_className = (
                        re.search(r"[A-Z]+", tmp_className).group()
                        + "\n"
                        + (
                            re.search(r"[0-9]+", tmp_className).group()
                            if re.search(r"[0-9]+", tmp_className) != None
                            else ""
                        )
                    )
                    tmp_className = tmp_className.replace("CS", "计科")
                    tmp_className = tmp_className.replace("BD", "大数据")
                    tmp_className = tmp_className.replace("BSB", "本硕博")
                    tmp_className = tmp_className.replace("IOT", "物联网")
                    tmp_className = tmp_className.replace("ZY", "卓越")
                    tmp_className = tmp_className.replace("XJ", "校交")
                    tmpDict["classNameList"][i] = tmp_className

                for i in range(len(tmpDictMajor["classNameList"])):
                    if tmpDictMajor["totalNum"][i] != 0:
                        tmpDictMajor["failedRate"][i] = round(
                            tmpDictMajor["failedNum"][i]
                            / tmpDictMajor["totalNum"][i]
                            * 100,
                            2,
                        )

                    tmp_className = tmpDictMajor["classNameList"][i]
                    if tmp_className == "":
                        continue
                    tmp_className = (
                        re.search(r"[A-Z]+", tmp_className).group()
                        + "\n"
                        + (
                            re.search(r"[0-9]+", tmp_className).group()
                            if re.search(r"[0-9]+", tmp_className) != None
                            else ""
                        )
                    )
                    tmp_className = tmp_className.replace("CS", "计科")
                    tmp_className = tmp_className.replace("BD", "大数据")
                    tmp_className = tmp_className.replace("BSB", "本硕博")
                    tmp_className = tmp_className.replace("IOT", "物联网")
                    tmp_className = tmp_className.replace("ZY", "卓越")
                    tmp_className = tmp_className.replace("XJ", "校交")
                    tmpDictMajor["classNameList"][i] = tmp_className

                ret.append(
                    {
                        "grade": str(grade),
                        "term": str(term),
                        "major": tmpDictMajor,
                        "cls": tmpDict,
                    }
                )

            if len(ret) != 0:
                # 将计算好的数据写入数据库
                for classItem in ret:
                    print("将 班级维度的表数据计算 结果存入数据库 ...")
                    classItemInsert = models.ClassByTermChart(
                        term=classItem["term"],
                        grade=classItem["grade"],
                        major=json.dumps(classItem["major"], ensure_ascii=False),
                        cls=json.dumps(classItem["cls"], ensure_ascii=False),
                    )
                    db.add(classItemInsert)
                    db.commit()
                    db.refresh(classItemInsert)
            else:
                return Response400(
                    msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空"
                )

            db.add(models.CalculateState(name=key))
            db.commit()

            await redis_store.setex(
                key, config.REDIS_CACHE_EXPIRES, json.dumps(ret, ensure_ascii=False)
            )

        else:  # 直接读取已经计算好的数据
            retDb = (
                db.query(models.ClassByTermChart)
                .filter(models.ClassByTermChart.term == str(term))
                .all()
            )
            ret = []
            for dbItem in retDb:
                ret.append(
                    {
                        "term": dbItem.term,
                        "grade": dbItem.grade,
                        "major": json.loads(dbItem.major),
                        "cls": json.loads(dbItem.cls),
                    }
                )
        if len(ret) != 0:
            # 将数据写入 redis
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
