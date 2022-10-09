import json
import logging
import typing as t

from fastapi import APIRouter, Request, Response, Depends,status,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_,or_,func
from aioredis import Redis
import difflib

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config


async def get_lower_course_name(term,gradeList,db:Session,redis_store:Redis):
    """
    获取 term 学期 每个grade 的课程数量
    然后将低于 阙值的课程返回
    :param db:
    :return:
    """
    # engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    # sql = text(
    #     'select scores.courseName,term,COUNT(*) as cnNum from scores where scores.term = {} GROUP BY scores.courseName ORDER BY cnNum;'.format(
    #         term))
    redis_key = "low_coursename_list_" + str(term)
    state = await redis_store.exists(redis_key)
    if state == 0:
        ret_dict = {}
        for grade in gradeList:
            low_course_list = db.query(models.Scores).filter(
                and_(models.Scores.term == term, models.Scores.grade == grade)).with_entities(models.Scores.courseName,
                                                                                              models.Scores.term,
                                                                                              func.count(
                                                                                                  models.Scores.courseName)).group_by(
                models.Scores.courseName).all()
            res = sorted(low_course_list, key=lambda t: t[2])
            ret_dict[str(grade)] = []
            # 返回低于阙值的课程
            for course in res:
                if course[2] < config.NUM_STUDENTS_IN_COURSE:
                    ret_dict[str(grade)].append(course[0])
        print("low_coursename_list_{}:{}".format(term,ret_dict))
        await redis_store.setex(redis_key,config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,json.dumps(ret_dict,ensure_ascii=False))
    else:
        ret_dict = json.loads(await redis_store.get(redis_key))
    return ret_dict

async def get_lower_course_name_by_term_grade(term,gradeList,db:Session,redis_store:Redis):
    """
    获取 term 学期 每个grade 的课程数量
    然后将低于 阙值的课程返回
    :param db:
    :return:
    """
    # engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    # sql = text(
    #     'select scores.courseName,term,COUNT(*) as cnNum from scores where scores.term = {} GROUP BY scores.courseName ORDER BY cnNum;'.format(
    #         term))
    redis_key = "low_coursename_list_" + str(term)
    state = await redis_store.exists(redis_key)
    if state == 0:
        ret_dict = {}
        for grade in gradeList:
            low_course_list = db.query(models.Scores).filter(
                and_(models.Scores.term == term, models.Scores.grade == grade)).with_entities(models.Scores.courseName,
                                                                                              models.Scores.term,
                                                                                              func.count(
                                                                                                  models.Scores.courseName)).group_by(
                models.Scores.courseName).all()
            res = sorted(low_course_list, key=lambda t: t[2])
            ret_dict[str(grade)] = []
            # 返回低于阙值的课程
            for course in res:
                if course[2] < config.NUM_STUDENTS_IN_COURSE:
                    ret_dict[str(grade)].append(course[0])
        print("low_coursename_list_{}:{}".format(term,ret_dict))
        await redis_store.setex(redis_key,config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,json.dumps(ret_dict,ensure_ascii=False))
    else:
        ret_dict = json.loads(await redis_store.get(redis_key))
    return ret_dict

async def get_class_list(db:Session):
    """
    获取所有班级信息
    :param db:
    :return:
    """
    res_class = db.query(models.Student).with_entities(models.Student.stuClass).distinct().all()
    # print(res_class)
    class_list = []
    for res in res_class:
        class_list.append(res[0])
    ret = sorted(class_list)
    print("class_list:{}".format(ret))
    return ret


async def get_each_grade_class_number(db:Session,redis_store:Redis):
    """

    获取每个年级的总人数
    :return:
    {
      "grade":{
          "17":123,
          "18":134,
          "20":43,
      },
      "class_nums_student":{
            "17":{
                'CS1701': 32,
                'CS1707': 30
            },
            "18":{

            }
      }
    }
    """
    state = await redis_store.exists("grade_class_info")
    # print("state:{}".format(state))
    if state == 0:
        class_list = await get_class_list(db)
        # print("class_list:{}".format(class_list))
        # 先获取各个年级的名称
        dict_grade_list = dict()
        dict_grade_list["grade"] = {}
        dict_grade_list["class_nums_student"] = {}
        dict_nums_student = {}
        dict_nums_student_global = {} # 存放所有班级的学生数量
        for className in class_list:
            tmpRes = db.query(models.Student).filter(models.Student.stuClass == className).all()
            dict_nums_student_global[className] = len(tmpRes)

        grade_set = set()
        for key in dict_nums_student_global.keys():
            tmpStr = (key[2:4])
            if tmpStr.isdigit():
                grade_set.add(tmpStr)

        # 初始化 grade
        tmp_grade = sorted(grade_set)
        for grade in tmp_grade:
            dict_grade_list["grade"][grade] = 0
            dict_grade_list["class_nums_student"][str(grade)] = {}
        # 初始化每个班级人数为 0

        for grade in grade_set:
            dict_grade_list["class_nums_student"][str(grade)] = {}

        # # 初始化班级信息
        for className in class_list:
            grade = await get_grade(className)
            dict_grade_list["class_nums_student"][str(grade)][className] = 0

        # 调整班级顺序
        for grade in grade_set:
            tmp_class_nums_student_list = dict_grade_list["class_nums_student"][grade].keys()
            tmp_class_nums_student_list = sorted(tmp_class_nums_student_list)
            # iot = difflib.get_close_matches('IOT', tmp_class_nums_student, 1, cutoff=0.7)
            # 将卓越移到最前面
            print("="*50)
            tmp_class_nums_student_list.insert(0,tmp_class_nums_student_list[-1])
            print(tmp_class_nums_student_list)
            tmp_class_nums_student_list = tmp_class_nums_student_list[:-2]
            print(tmp_class_nums_student_list)
            # 计算班级人数
            class_nums_student = {}
            for className in tmp_class_nums_student_list:
                # tmpRes = db.query(models.Student).filter(models.Student.stuClass == className).all()
                class_nums_student[className] = dict_nums_student_global[className]
            dict_grade_list["class_nums_student"][grade] = class_nums_student

        for grade in grade_set:
            dict_grade_list["grade"][str(grade)] = sum(dict_grade_list["class_nums_student"][str(grade)].values())

        await redis_store.setex("grade_class_info",config.FAILED_STUID_INFO_REDIS_CACHE_EXPIRES,json.dumps(dict_grade_list,ensure_ascii=False))
    else:
        dict_grade_list = await redis_store.get("grade_class_info")
        dict_grade_list = json.loads(dict_grade_list)
    print("dict_grade_list:{}".format(dict_grade_list))
    # print(dict_grade_list["each_class_nums_student"]["CS1701"])
    return dict_grade_list

async def get_grade(className):
    """
    获取年级信息
    :param className:
    :return:
    """
    if className[0] == 'A' or className[0] == 'B' or className[0] == 'I':
        return className[3:5]
    else:
        return className[2:4]

async def get_each_term_courseName(db:Session,term):
    """
    获取指定学期的课程名称
    :param term: 1 代表第一学期
    :param db:
    :return: ['软件工程', '足球（二）', '足球（一）', '计算机通信与网络实验']
    """
    term = str(term) + "_"
    try:
        term_courseName = await db.query(models.Courses).filter(models.Courses.term.like(term)).all()
        socre_courseName = await db.query(models.Scores).filter(models.Scores.term.like(term)).all()
    except Exception as E:
        logging.error("访问数据库发生错误：" + str(E))
        return -1
    # 找到上课人数少于 10人的
    student_in_course = {}
    for sc in socre_courseName:
        if sc.courseName not in student_in_course:
            student_in_course[sc.courseName] = 1
        else:
            student_in_course[sc.courseName] += 1

    term_courseName_list = []
    for className in term_courseName:
        # if className.courseName not in NOT_SHOW_COURSENAME and className.courseName not in lower_num_course:
        if className.courseName not in config.NOT_SHOW_COURSENAME and className.courseName:
            term_courseName_list.append(className.courseName)

    term_courseName_list = set(term_courseName_list)

    return term_courseName_list