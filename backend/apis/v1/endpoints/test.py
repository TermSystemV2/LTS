# from fastapi import APIRouter,Depends
# from sqlalchemy import within_group
# from sqlalchemy.orm import Session

# import models
# from schemas import Response200
# from database.session import get_db_async,async_engine

# test_api = APIRouter()

# def test_dict():
#     d_dict = dict()
#     d_dict['10'] = 0

# async def get_class_list():
#     """
#     获取所有班级信息
#     :param db:
#     :return:
#     """
#     async with async_engine.connect() as conn:
#         ret_class = conn.execute(select(models.Student).with_entities(models.Student.stuClass).distinct().all())
#         # res_class = db.query(models.Student).with_entities(models.Student.stuClass).distinct().all()
#         # ret_class = res
#     # print(res_class)
#     class_list = []
#     for res in res_class:
#         class_list.append(res[0])
#     ret = sorted(class_list)
#     print("class_list:{}".format(ret))

#     await async_engine.dispose()

#     return ret

# @test_api.get("/test_async_db")
# async def test_db_async(db:Session= Depends(get_db_async)):

#     ret = await get_class_list()
#     return Response200(data=ret)


