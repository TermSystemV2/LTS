from fastapi import APIRouter
from sqlalchemy.orm import Session

import models

test_api = APIRouter()
def test_dict():
    d_dict = dict()
    d_dict['10'] = 0

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



if __name__ == '__main__':
    test_dict()