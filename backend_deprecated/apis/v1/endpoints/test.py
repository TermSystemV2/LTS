import json
import logging
import typing as t
import os

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
)

from apis.v1.endpoints.studentInfo import getStudentInfoByGrade

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from database.redis import course_cache
from core.config import config
from utils.common import to_pinyin, create_form, add_info_to_form


test_api = APIRouter()


@test_api.get("/test/major")
async def test_major(
    db: Session = Depends(get_db), redis_store: Redis = Depends(course_cache)
):
    ret = await get_each_grade_class_number(db, redis_store)
    return Response200(data=ret)


@test_api.get("/test/studentInfo/<grade>")
async def test_student(grade: int):
    result = await getStudentInfoByGrade(grade)
    return Response200(data=result)


class TestClass:

    config = 1


if __name__ == "__main__":

    a = TestClass()
    print(a.config)
    a.config = 2
    print(a.config)
