import json
import logging
import typing as t

from fastapi import APIRouter, Request, Response, Depends,status,HTTPException



from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config
from database.curd_ec import (
    ec_get_by_year, ec_getYearList, ec_get_by_grade, ec_get_info_by_grade_year
)


ec_router = APIRouter()

# todo:增加前端接口

@ec_router.post("/excellent/info")
async def add_excellent_class_info(ec_info: schemas.ExcellentStudyClassSchemas, db=Depends(get_db)):
    """
    保存当年的优良学分班信息
    {
        "grade":self.grade,
        "year":self.year,
        "totalClassNum":self.totalClassNum,
        "excellentClassNum":self.excellentClassNum
    }
    :return:
    """
    try:
        ec_info_old = await ec_get_info_by_grade_year(db,ec_info.grade,ec_info.year)
        if not ec_info_old:
            db_ec_info = models.ExcellentStudyClass(
                grade=ec_info.grade,
                year=ec_info.year,
                totalClassNum=ec_info.totalClassNum,
                excellentClassNum=ec_info.excellentClassNum
            )
            db.add(db_ec_info)
            db.commit()
            db.refresh(db_ec_info)
            return Response200(msg="优良学风班数据插入成功")
        else:
            return Response400(code=status.HTTP_207_MULTI_STATUS,msg="该数据已经在数据库中存在")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="服务器内部发生异常")


@ec_router.get("/excellentInfoHist")
async def get_excellentStudyClass_info_histogram(db=Depends(get_db),redis_store=Depends(course_cache)):
    """
        获取优良学风班的柱状图信息

        :return:
        {
            "2018":{
                "excellentStudyClassNum":12,
                "excellentRate":26%,
            }
        }
        """
    # 先从缓存中读取
    state = await redis_store.exists("excellentStudyClassHist")
    if state != 0:
        try:
            resp_dict = await redis_store.get("excellentStudyClassHist")
            resp_dict = json.loads(resp_dict)
            return Response200(data=resp_dict)
        except Exception as E:
            logging.error("从 redis 读 excellentStudyClassHist 异常 %s" % E)

            return Response400(msg="从 redis 读 异常 %s" % str(E))
    else:
        yearList = await ec_getYearList(db)
        # 从 2018年开始
        resp_data = {}
        # 初始化
        for year in yearList:
            res = await ec_get_by_year(db,year)
            # ("%.2f" % class_table['failedRate'])
            res['excellentRate'] = '{:.2f}'.format((round(res["excellentStudyClassNum"] * 1.0 / res["totalClassNum"], 2) * 100))
            # tmp[""] = res
            resp_data[str(year)] = res

        if len(resp_data) != 0:
            # 写入 redis
            try:
                await redis_store.setex("excellentStudyClassHist", config.REDIS_CACHE_EXPIRES,
                                json.dumps(resp_data))
            except Exception as E:
                return -1, E
        else:
            return Response400(msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空")


    return Response200(msg="请求成功",data=resp_data)



@ec_router.get("/excellentInfoLine")
async def get_excellentStudyClass_info_line(db=Depends(get_db),redis_store=Depends(course_cache)):
    """
    获取优良学分班的折线图信息
    :return:
    {
        "16":{
            "grade2":28.57%,
            "grade3":42.86%,
            "grade4":57.14%
        }
    }
    """
    # 先从缓存中读取
    state = await redis_store.exists("excellentStudyClassLine")
    if state != 0:
        try:
            resp_dict = await redis_store.get("excellentStudyClassLine")
            resp_dict = json.loads(resp_dict)
            return Response200(data=resp_dict)
        except Exception as E:
            logging.error("从 redis 读 excellentStudyClassHist 异常 %s" % E)
            Response400(msg="从 redis 读 异常 %s" % str(E))
    else:
        yearList = await ec_getYearList(db)
        resp_data = {}
        for year in yearList:
            grade = year % 2000
            resp_data[str(year)] = await (ec_get_by_grade(db,grade))

        if len(resp_data) != 0:
            # 写入 redis
            try:
                await redis_store.setex("excellentStudyClassLine", config.REDIS_CACHE_EXPIRES,
                                json.dumps(resp_data))
            except Exception as E:
                print("将 excellentStudyClassHist 写入 redis 异常 ", str(E))
                return -1, E
        else:
            return Response400(msg="没有查询到相关数据，请检查查询关键字 or 数据库数据是否为空")
    return Response200(msg="请求成功",data=resp_data)