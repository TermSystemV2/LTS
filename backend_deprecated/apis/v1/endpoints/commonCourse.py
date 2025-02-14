import json
import logging
import typing as t
import re

from fastapi import APIRouter, Request, Response, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from aioredis import Redis
import difflib

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config


async def get_lower_course_name_by_term(term, db: Session, redis_store: Redis):
    """
    获取 term 学期 每个grade 的课程数量
    然后将低于 阙值的课程返回
    :param db:
    :return:
    """
    key = "low_course_name_list_by_term" + str(term)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    ret_dict = {}
    if (not sqlState) or redisState == 0:
        if not sqlState:
            gradeList = await get_grade_list(db)
            for grade in gradeList:
                low_course_list = (
                    db.query(models.Course)
                    .join(
                        models.Score,
                        and_(
                            models.Course.courseName == models.Score.courseName,
                            models.Course.stuClass == models.Score.stuClass,
                        ),
                    )
                    .filter(
                        models.Course.term == term,
                        models.Course.stuClass[-4:-2] == grade,
                    )
                    .with_entities(
                        models.Course.courseName,
                        func.count(models.Course.courseName),
                    )
                    .group_by(models.Course.courseName)
                    .all()
                )
                res = sorted(low_course_list, key=lambda t: t[1])
                ret_dict[str(grade)] = []
                # 返回低于阙值的课程
                for course in res:
                    if course[1] < config.NUM_STUDENTS_IN_COURSE:
                        ret_dict[str(grade)].append(course[0])
                    else:
                        break
            ret = json.dumps(ret_dict, ensure_ascii=False)
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
            await redis_store.setex(key, config.REDIS_CACHE_EXPIRES, ret)
            ret_dict = json.loads(ret)
    else:
        ret_dict = json.loads(await redis_store.get(key))
    print("low_course_name_list_{}:{}".format(term, ret_dict))
    return ret_dict


async def get_lower_course_name_by_grade(grade, db: Session, redis_store: Redis):
    """
    获取 grade  每个term学期 的课程数量
    然后将低于 阙值的课程返回
    :param db:
    :return:
    """
    key = "low_course_name_list_by_grade" + str(grade)
    sqlState = (
        db.query(models.CalculateState)
        .filter(models.CalculateState.name == key)
        .first()
    )
    redisState = await redis_store.exists(key)
    ret = []
    if (not sqlState) or redisState == 0:
        if not sqlState:
            low_course_list = (
                db.query(models.Course)
                .join(
                    models.Score,
                    and_(
                        models.Course.courseName == models.Score.courseName,
                        models.Course.stuClass == models.Score.stuClass,
                    ),
                )
                .filter(models.Course.stuClass[-4:-2] == grade)
                .with_entities(
                    models.Course.courseName,
                    func.count(models.Course.courseName),
                )
                .group_by(models.Course.courseName)
                .all()
            )
            res = sorted(low_course_list, key=lambda t: t[1])
            # 返回低于阙值的课程
            for course in res:
                if course[1] < config.NUM_STUDENTS_IN_COURSE:
                    ret.append(course[0])
                else:
                    break
            ret = json.dumps(ret, ensure_ascii=False)
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
            await redis_store.setex(key, config.REDIS_CACHE_EXPIRES, ret)
            ret = json.loads(ret)
    else:
        ret = json.loads(await redis_store.get(key))
    return ret


async def get_class_list_all(db: Session):
    """
    获取所有班级信息
    :param db:
    :return:
    """
    res_class = (
        db.query(models.Student).with_entities(models.Student.stuClass).distinct().all()
    )
    class_list = []
    for res in res_class:
        class_list.append(res[0])
    ret = sorted(class_list)
    print("class_list:{}".format(ret))
    return ret


async def get_class_list_by_term(db: Session, term: str):
    """
    获取第term学期班级信息
    :param db:
    :return:
    """
    res_class = (
        db.query(models.Student)
        .filter(models.Student.term == term)
        .with_entities(models.Student.stuClass)
        .distinct()
        .all()
    )
    class_list = []
    for res in res_class:
        class_list.append(res[0])
    ret = sorted(class_list)
    print("class_list:{}".format(ret))
    return ret


async def get_major_list(db: Session):
    """
    获取所有专业信息
    :param db:
    :return:
    """
    res_major = (
        db.query(models.Student).with_entities(models.Student.stuClass).distinct().all()
    )
    major_list = []
    for res in res_major:
        major_list.append(re.search(r"[A-Z]+", res[0]).group())
    major_list.append("ALL")
    ret = sorted(set(major_list))
    print("major_list:{}".format(ret))
    return ret


async def get_each_grade_class_number(db: Session, redis_store: Redis):
    """
    获取每个年级的总人数
    :return:
    {
        "total":{
            "ALL":{
                "20":{
                    "11": 400,
                    "12": 420,
                    "21": 430,
                    ...
                },
                "21":{
                    ...
                },
            "CS": ...
            ...
            }
        },
        "details":{
            "20":{
                "11":{
                    "CS2001": 30,
                    "CS2002": 31,
                    ...
                },
                "12":...
            },
            "21":...
        }
    """
    sqlState = db.query(models.CalculateState).filter(
        models.CalculateState.name == "grade_class_info"
    )
    redisState = await redis_store.exists("grade_class_info")
    dict_grade_list = {}
    if (not sqlState) or redisState == 0:
        if not sqlState:
            termList = ["11", "12", "21", "22", "31", "32", "41", "42"]
            dict_grade_list["total"] = {}
            dict_grade_list["details"] = {}
            gradeList = json.loads(
                db.query(models.ResultDict.value)
                .filter(models.ResultDict.key == "grade_list")
                .scalar()
            )
            majorList = get_major_list(db)
            for major in majorList:
                dict_grade_list["total"][str(major)] = {}
                for grade in gradeList:
                    dict_grade_list["total"][str(major)][str(grade)] = {}
                    for term in termList:
                        dict_grade_list["total"][str(major)][str(grade)][str(term)] = 0
            for grade in gradeList:
                dict_grade_list["details"][str(grade)] = {}
                for term in termList:
                    dict_grade_list["details"][str(grade)][str(term)] = {}
                    classList = get_class_list_by_term(db, term)
                    for cls in classList:
                        ret = (
                            db.query(models.Student)
                            .filter(
                                models.Student.term == term,
                                models.Student.stuClass == cls,
                            )
                            .all()
                        )
                        dict_grade_list["details"][str(grade)][str(term)][str(cls)] = (
                            len(ret)
                        )
                        major = re.search(r"[A-Z]+", cls).group()
                        dict_grade_list["total"]["ALL"][str(grade)][str(term)] += len(
                            ret
                        )
                        dict_grade_list["total"][str(major)][str(grade)][
                            str(term)
                        ] += len(ret)
            res = json.dumps(dict_grade_list, ensure_ascii=False)
            db.add(models.CalculateState(name="grade_class_info"))
            db.add(models.ResultDict(key="grade_class_info", value=res))
            db.commit()

            await redis_store.setex("grade_class_info", config.REDIS_CACHE_EXPIRES, res)
        else:
            res = (
                db.query(models.ResultDict.value)
                .filter(models.ResultDict.key == "grade_class_info")
                .scalar()
            )
            await redis_store.setex("grade_class_info", config.REDIS_CACHE_EXPIRES, res)
            dict_grade_list = json.loads(res)
    else:
        dict_grade_list = json.loads(await redis_store.get("grade_class_info"))
    print("dict_grade_list:{}".format(dict_grade_list))
    return dict_grade_list


async def get_latest_student_by_stuID(db: Session, stuID: str):
    studentList: list[models.Student] = (
        db.query(models.Student).filter(models.Student.stuID == stuID).all()
    )
    if not studentList:
        raise Exception("Wrong stuID!")
    studentList.sort(
        key=lambda x: int(x.stuClass[-4:-2]) * 100 + int(x.term), reverse=True
    )
    return studentList[0]


async def get_grade(className):
    """
    获取年级信息
    :param className:
    :return:
    """
    return className[-4:-2]


async def get_grade_list(db: Session):
    """
    获取年级信息
    :param className:
    :return:
    """
    return json.loads(
        db.query(models.ResultDict.value)
        .filter(models.ResultDict.key == "grade_list")
        .scalar()
    )


async def get_latest_term(db: Session):
    return json.loads(
        db.query(models.ResultDict.value)
        .filter(models.ResultDict.key == "latestTerm")
        .scalar()
    )


async def get_latest_term_by_grade(db: Session, grade):
    ret = json.loads(
        db.query(models.ResultDict.value)
        .filter(models.ResultDict.key == "latestTerm")
        .scalar()
    )
    return ret[str(grade)]


# bug
async def get_each_term_courseName(db: Session, term):
    """
    获取指定学期的课程名称
    :param term: 1 代表第一学期
    :param db:
    :return: ['软件工程', '足球（二）', '足球（一）', '计算机通信与网络实验']
    """
    term = str(term) + "_"
    try:
        term_courseName = (
            await db.query(models.Course).filter(models.Course.term.like(term)).all()
        )
        score_courseName = (
            await db.query(models.Score).filter(models.Score.term.like(term)).all()
        )
    except Exception as E:
        logging.error("访问数据库发生错误：" + str(E))
        return -1
    # 找到上课人数少于 10人的
    student_in_course = {}
    for sc in score_courseName:
        if sc.courseName not in student_in_course:
            student_in_course[sc.courseName] = 1
        else:
            student_in_course[sc.courseName] += 1

    term_courseName_list = []
    for className in term_courseName:
        # if className.courseName not in NOT_SHOW_COURSENAME and className.courseName not in lower_num_course:
        if (
            className.courseName not in config.NOT_SHOW_COURSENAME
            and className.courseName
        ):
            term_courseName_list.append(className.courseName)

    term_courseName_list = set(term_courseName_list)

    return term_courseName_list
