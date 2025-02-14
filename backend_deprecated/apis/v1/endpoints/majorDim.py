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
from .commonCourse import get_each_grade_class_number, get_major_list, get_grade_list
import re

majorDim_router = APIRouter()


@majorDim_router.post("/scores/major/chart/<term>")
async def get_major_chart_by_term(
    queryItem: schemas.ClassQuery,
    db: Session = Depends(get_db),
    redis_store: Redis = Depends(course_cache),
):
    """
    专业维度图标

    :param queryItem:
    :param db:
    :param redis_store:
    :return: [
         {
            "term": "11",
            "major": "ALL",
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
    term = str(queryItem.term)
    key = "major_by_term_chart_" + str(term)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    ret = []
    if (not sqlState) or redisState == 0:
        if not sqlState:  # 更新数据
            # 找到四个年级
            grade_class_info = await get_each_grade_class_number(db, redis_store)
            gradeList = await get_grade_list(db)
            majorList = await get_major_list(db)
            for major in majorList:
                if str(major) == "ALL":
                    continue
                tmpDict = {
                    "classNameList": [],
                    "failedNum": [],  # 挂科人数
                    "failedRate": [],
                    "totalNum": [],  # 各班总人数
                    "major": str(major),
                    "term": str(term),
                }
                count = 0
                lastGradeIndex = 0
                for grade in gradeList:
                    for className in grade_class_info["details"][str(grade)][
                        str(term)
                    ].keys():
                        if re.search(r"[A-Z]+", className).group() != major:
                            continue
                        if (
                            count == 0
                            or re.search(
                                r"[A-Z]+[0-9]{2}", tmpDict["classNameList"][count - 1]
                            ).group()
                            != re.search(r"[A-Z]+[0-9]{2}", className).group()
                        ):
                            tmpDict["classNameList"].append(
                                re.search(r"[A-Z]+[0-9]{2}", className).group()
                            )
                            tmpDict["failedNum"].append(0)
                            tmpDict["failedRate"].append(0)
                            tmpDict["totalNum"].append(0)
                            lastGradeIndex = count
                            count += 1
                        res = (
                            db.query(models.FailedRecord.stuID)
                            .filter(
                                models.FailedRecord.stuClass == className,
                                models.FailedRecord.term == term,
                            )
                            .distinct()
                            .all()
                        )
                        tmpDict["failedNum"][lastGradeIndex] += len(res)
                        tmpDict["totalNum"][lastGradeIndex] += grade_class_info[
                            "details"
                        ][str(grade)][str(term)][className]

                # 计算不及格率，修改班级名
                for i in range(len(tmpDict["classNameList"])):
                    tmpDict["failedRate"][i] = round(
                        tmpDict["failedNum"][i] / tmpDict["totalNum"][i] * 100, 2
                    )

                    tmp_className = tmpDict["classNameList"][i]
                    tmp_className = tmp_className + "\n级"
                    tmp_className = tmp_className.replace("CS", "计科")
                    tmp_className = tmp_className.replace("BD", "大数据")
                    tmp_className = tmp_className.replace("BSB", "本硕博")
                    tmp_className = tmp_className.replace("IOT", "物联网")
                    tmp_className = tmp_className.replace("ZY", "卓越")
                    tmp_className = tmp_className.replace("XJ", "校交")
                    tmpDict["classNameList"][i] = tmp_className
                ret.append(tmpDict)

            if len(ret) != 0:
                # 将计算好的数据写入数据库
                print("将 专业维度的表数据计算 结果存入数据库 ...")
                for majorItem in ret:
                    majorItemInsert = models.MajorByTermChart(
                        term=majorItem["term"],
                        major=str(majorItem["major"]),
                        classNameList=json.dumps(
                            majorItem["classNameList"], ensure_ascii=False
                        ),
                        failedNum=json.dumps(
                            majorItem["failedNum"], ensure_ascii=False
                        ),
                        failedRate=json.dumps(
                            majorItem["failedRate"], ensure_ascii=False
                        ),
                        totalNum=json.dumps(majorItem["totalNum"], ensure_ascii=False),
                    )
                    db.add(majorItemInsert)
                    db.commit()
                    db.refresh(majorItemInsert)

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
                db.query(models.MajorByTermChart)
                .filter(models.MajorByTermChart.term == str(term))
                .all()
            )
            ret = []
            for dbItem in retDb:
                ret.append(
                    {
                        "term": dbItem.term,
                        "major": dbItem.major,
                        "classNameList": json.loads(dbItem.classNameList),
                        "failedNum": json.loads(dbItem.failedNum),
                        "failedRate": json.loads(dbItem.failedRate),
                        "totalNum": json.loads(dbItem.totalNum),
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
