import json
import logging
import typing as t
import requests
import json

from fastapi import APIRouter, Request, Response, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct, and_, func, create_engine

from database.session import get_db
import models
from schemas.basic import Response200, Response400
from core.config import config


synchronizedData_router = APIRouter()


@synchronizedData_router.get("/synchronizedData/")
async def synchronizedData(db: Session = Depends(get_db)):
    """
    同步数据
    返回四个年级第 term 学期的所有课程信息
    :param term:
    :return:
    """
    
    # 修改配置
    config.UPDATE_DATA = True
    # 同步班级维度的数据
    url_class_table = "http://127.0.0.1:8888/apis/v1/scores/class/table/<term>"
    await commonCode(url_class_table,"class table dim")
    url_class_chart = "http://127.0.0.1:8888/apis/v1/scores/class/chart/<term>"
    await commonCode(url_class_chart,"class chart dim")
    # 同步课程维度的数据
    url_course = "http://127.0.0.1:8888/apis/v1/scores/courses/<term>"
    await commonCode(url_course,"course dim")
    # 同步年级维度的数据
    url_grade = "http://127.0.0.1:8888/apis/v1/scores/grade/<term>"
    await commonCode(url_grade,"grade dim")
    # 同步学生信息数据
    url_studentInfo = "http://127.0.0.1:8888/apis/v1/studentInfo/grade/"
    await studentInfo(url_studentInfo)

    # 同步完毕之后关闭
    config.UPDATE_DATA = False
    return Response200(data="数据同步完毕")


async def commonCode(url,tips):
    """
    共性的代码请求部分
    """
    headers = {
    'Content-Type': 'application/json'
    }
    for term in config.Term_List:
        response_res = requests.request("POST", url, headers=headers, data=json.dumps({
            "term": term
        }))
        response_dict = json.loads(response_res)
        if response_dict['code'] != 200:
            print("%s term ".format(tips),term,": ",response_dict['msg'])
        else:
            print("term %s 表格 %s 请求成功！".format(term,tips))
            
async def studentInfo(url_studentInfo):
    payload={}
    headers = {}
    for grade in config.Grade_List:
        url_grade = url_studentInfo + "?grade=%s".format(grade)
        response_studentInfo = requests.request("GET", url_grade, headers=headers, data=payload)
        response_dict = json.loads(response_studentInfo)
        if response_dict['code'] != 200:
            print("grade_%s ".format(grade),": ",response_dict['msg'])
        else:
            print("grade_%s 请求成功".format(grade))