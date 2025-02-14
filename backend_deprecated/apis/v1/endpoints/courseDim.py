import json
import logging
import typing as t
import os
import re

from fastapi import APIRouter, Request, Response, Depends, status, HTTPException
from aioredis import Redis
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from sqlalchemy import distinct, and_, func, create_engine
import pandas as pd
from starlette.responses import FileResponse

from apis.v1.endpoints.commonCourse import (
    get_each_grade_class_number,
    get_lower_course_name_by_term,
    get_major_list,
    get_latest_student_by_stuID,
    get_grade_list,
)
from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config
from utils.common import to_pinyin, create_form, add_info_to_form

courseDim_router = APIRouter()


@courseDim_router.post("/scores/courses/<term>")
async def get_coursers_by_term_pass(
    queryItem: schemas.ClassQuery,
    db: Session = Depends(get_db),
    redis_store: Redis = Depends(course_cache),
):
    """
    通过学期获得该学期课程的考试通过情况
    :param queryItem:
    :param db:
    :param redis_store:
    :return:
    [
        {
            "term": "11",
            "courseName": "大学物理（二）",
            "major": "ALL" | "CS"
            "failed_nums": {
                "18":29,
                "19":12
            },
            "gradeDistribute": {
                "18": {
                "0-59": 12,
                "60-69": 71,
                "70-79": 118,
                "80-89": 157,
                "90-100": 48
                },
                "19": {
                },
            },
            "pass_rate": [
                97.0,
                96.0,
                97.0,
                100.0
            ],
            "failStudentsList":[
                ["年级","班级","姓名"]
            ],
            "sumFailedNums": 100
        }
    ]
    """
    term = str(queryItem.term)
    key = "course_by_term_" + str(term)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    if (not sqlState) or redisState == 0:
        if not sqlState:  # 更新数据
            ret = []
            grade_class_info = await get_each_grade_class_number(db, redis_store)
            # 找到四个年级
            gradeList = await get_grade_list(db)
            # 找到所有专业
            majorList = await get_major_list(db)
            # 1.获取第 term 学期的所有课程
            courseNameList = [
                courseName[0]
                for courseName in db.query(models.Course)
                .filter(models.Course.term == term)
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
            print("=" * 50)
            print(courseNameList)
            for courseName in courseNameList:
                for major in majorList:
                    tmpDict = {
                        "term": str(term),
                        "courseName": courseName,
                        "major": str(major),
                        "failed_nums": {},
                        "gradeDistribute": {},
                        "pass_rate": {},
                        "failStudentsList": [],
                        "sumFailedNums": 0,
                    }
                    # 将term 学期各个年级的数据初始化
                    for grade in gradeList:
                        tmpDict["failed_nums"][str(grade)] = 0
                        tmpDict["gradeDistribute"][str(grade)] = {
                            "0-59": 0,
                            "60-69": 0,
                            "70-79": 0,
                            "80-89": 0,
                            "90-100": 0,
                        }
                        tmpDict["pass_rate"][str(grade)] = 0

                    res = (
                        db.query(models.Score)
                        .join(
                            models.Course,
                            and_(
                                models.Score.courseName == models.Course.courseName,
                                models.Score.stuClass == models.Course.stuClass,
                            ),
                        )
                        .filter(
                            models.Course.term == term,
                            models.Score.courseName == courseName,
                        )
                        .with_entities(
                            models.Score.score,
                            models.Score.stuID,
                            models.Score.stuClass,
                        )
                        .all()
                    )
                    for row in res:
                        if str(major) == "ALL" or re.search(r"[A-Z]+", row[2]) == str(
                            major
                        ):
                            if row[0] < 60:
                                tmpDict["sumFailedNums"] += 1
                                tmpDict["gradeDistribute"][str(row[2])[-4:-2]][
                                    "0-59"
                                ] += 1
                                tmpDict["failed_nums"][str(row[2])[-4:-2]] += 1
                                # 不及格学生信息
                                tmpStuInfo = await get_latest_student_by_stuID(
                                    db, row[1]
                                )
                                tmpDict["failStudentsList"].append(
                                    [
                                        tmpStuInfo.stuClass,
                                        tmpStuInfo.stuID,
                                        tmpStuInfo.stuName,
                                    ]
                                )
                            elif 60 <= row[1] <= 69:
                                tmpDict["gradeDistribute"][str(row[0])]["60-69"] += 1
                            elif 70 <= row[1] <= 79:
                                tmpDict["gradeDistribute"][str(row[0])]["70-79"] += 1
                            elif 80 <= row[1] <= 89:
                                tmpDict["gradeDistribute"][str(row[0])]["80-89"] += 1
                            elif 90 <= row[1] <= 100:
                                tmpDict["gradeDistribute"][str(row[0])]["90-100"] += 1
                    # 学生去重 并对结果按照班级排序
                    tmpDict["failStudentsList"] = list(
                        set([tuple(t) for t in tmpDict["failStudentsList"]])
                    )
                    tmpDict["failStudentsList"] = [
                        list(v) for v in tmpDict["failStudentsList"]
                    ]
                    tmpDict["failStudentsList"].sort(key=lambda x: x[0])
                    for grade in gradeList:
                        if (
                            grade_class_info["total"][str(major)][str(grade)][str(term)]
                            != 0
                        ):
                            tmpDict["pass_rate"][str(grade)] = round(
                                (
                                    grade_class_info["total"][str(major)][str(grade)][
                                        str(term)
                                    ]
                                    - tmpDict["failed_nums"][str(grade)]
                                )
                                / grade_class_info["total"][str(major)][str(grade)][
                                    str(term)
                                ]
                                * 100,
                                2,
                            )
                    sum_students = 0
                    for grade in gradeList:
                        sum_students += sum(
                            tmpDict["gradeDistribute"][str(grade)].values()
                        )
                    if sum_students > config.NUM_STUDENTS_IN_COURSE_COURSE_DIM:
                        # 该课程在 term 学期上的人数要大于 30，才认为该课程在学院的第 term 学期开设
                        ret.append(tmpDict)

            if len(ret) != 0:
                # 将计算好的数据写入数据库
                print("将 课程维度的表数据计算 结果存入数据库 ...")
                for courseItem in ret:
                    courseItemInsert = models.CourseByTermTable(
                        term=courseItem["term"],
                        courseName=courseItem["courseName"],
                        major=courseItem["major"],
                        failed_nums=json.dumps(
                            courseItem["failed_nums"], ensure_ascii=False
                        ),
                        gradeDistribute=json.dumps(
                            courseItem["gradeDistribute"], ensure_ascii=False
                        ),
                        pass_rate=json.dumps(
                            courseItem["pass_rate"], ensure_ascii=False
                        ),
                        failStudentsList=json.dumps(
                            courseItem["failStudentsList"], ensure_ascii=False
                        ),
                        sumFailedNums=courseItem["sumFailedNums"],
                    )
                    db.add(courseItemInsert)
                    db.commit()
                    db.refresh(courseItemInsert)
            else:
                return Response400(
                    msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空"
                )
            print(courseNameList)
            db.add(models.CalculateState(name=key))
            db.commit()

            await redis_store.setex(
                key,
                config.REDIS_CACHE_EXPIRES,
                json.dumps(ret, ensure_ascii=False),
            )
        else:
            # 直接读取已经计算好的数据
            ret = []
            retDb = (
                db.query(models.CourseByTermTable)
                .filter(models.CourseByTermTable.term == str(term))
                .all()
            )
            for dbItem in retDb:
                ret.append(
                    {
                        "term": dbItem.term,
                        "courseName": dbItem.courseName,
                        "major": dbItem.major,
                        "failedNums": json.loads(dbItem.failedNums),
                        "gradeDistribute": json.loads(dbItem.gradeDistribute),
                        "passRate": json.loads(dbItem.passRate),
                        "failStudentsList": json.loads(dbItem.failStudentsList),
                        "sumFailedNums": dbItem.sumFailedNums,
                    }
                )
        if len(ret) != 0:
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


# bug
@courseDim_router.post("/scores/courses/download/<courseName>")
async def downFailedStudet(
    courseItem: schemas.CourseFailedDownload,
    db: Session = Depends(get_db),
    redis_store: Redis = Depends(course_cache),
):
    """
    通过学期获得该学期课程的考试通过情况
    :param queryItem:
    :param db:
    :param redis_store:
    :return:
    返回如下字段的 excel文件
    ['序号','课程名', '班级', '学号', '姓名']

    """

    try:
        # 参数1：文件的路径 filename：自定义导出的文件名（需要带上格式后缀）
        courseName = str(courseItem.courseName)
        source_dir = "./documents/failedStudentExcel/"
        failed_student_excel_name = "failed_students_" + str(courseName) + ".xlsx"
        # os.path.exists(source_dir+faileed_student_excel_name)

        ret = []
        retDb = (
            db.query(models.CourseByTermTable)
            .filter(models.CourseByTermTable.courseName == courseName)
            .all()
        )
        if os.path.exists(source_dir + failed_student_excel_name):
            os.remove(source_dir + failed_student_excel_name)
        # print("create form")
        print(source_dir + failed_student_excel_name)
        FORM_HEADER = ["序号", "课程名", "班级", "学号", "姓名"]
        create_form(source_dir + failed_student_excel_name, FORM_HEADER)
        index = 0
        for dbItem in retDb:
            ret.append(
                {
                    "id": dbItem.id,
                    "term": dbItem.term,
                    "courseName": dbItem.courseName,
                    "failed_nums": (
                        eval(dbItem.failed_nums) if len(dbItem.failed_nums) != 0 else {}
                    ),
                    "gradeDistribute": (
                        eval(dbItem.gradeDistribute)
                        if len(dbItem.gradeDistribute) != 0
                        else {}
                    ),
                    "pass_rate": (
                        eval(dbItem.pass_rate) if dbItem.pass_rate != [] else {}
                    ),
                    "failStudentsList": (
                        eval(dbItem.failStudentsList)
                        if dbItem.failStudentsList != []
                        else []
                    ),
                    "sumFailedNums": dbItem.sumFailedNums,
                }
            )
            # ['序号','课程名', '班级', '学号',"姓名"]
            for stuInfo in ret[-1]["failStudentsList"]:
                tmpList = [
                    index,
                    ret[-1]["courseName"],
                    stuInfo[0],
                    stuInfo[1],
                    stuInfo[2],
                ]
                print(tmpList)
                add_info_to_form(source_dir + failed_student_excel_name, tmpList)
                index += 1

        if len(ret) == 0:
            # 中间计算表还没计算出来
            return Response400(
                msg="中间结果数据库中暂时无数据，请在文件上传页面切换读取数据方式为从原始数据读取之后再请求"
            )

        return FileResponse(
            path=source_dir + failed_student_excel_name,
            filename=failed_student_excel_name,
        )
    except Exception as e:
        return Response400(msg=str(e))
