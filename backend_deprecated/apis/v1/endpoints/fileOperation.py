import os
import re
import typing as t
import json

from fastapi import (
    APIRouter,
    File,
    UploadFile,
    Request,
    Response,
    Depends,
    status,
    HTTPException,
)
from sqlalchemy.orm import Session
from aioredis import Redis
import pandas as pd

from database.session import get_db
import models
import schemas
from schemas.basic import Response200, Response400
from core.config import config


file_router = APIRouter()


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


@file_router.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    """
    上传并保存文件
    :param files:
    :return:
    """
    try:
        res = await file.read()
        target_dir = "./documents/grade/"
        save_file_name = target_dir + file.filename
        with open(save_file_name, "wb") as fw:
            fw.write(res)
        return Response200(
            msg="文件读取成功",
            data={"filename": file.filename, "file type": file.content_type},
        )
    except Exception as e:
        return Response400(msg="保存文件出现错误：" + str(e))


@file_router.post("/uploadfiles/")
async def upload_file(files: t.List[UploadFile] = File(...)):
    """
    多文件上传
    :param files: 文件列表
    :return:
    """
    try:
        fileNameList = []
        for file in files:
            res = await file.read()
            target_dir = "./documents/grade/"
            save_file_name = target_dir + file.filename
            with open(save_file_name, "wb") as fw:
                fw.write(res)
            fileNameList.append(file.filename)
        return Response200(msg="文件读取成功", data={"filename": fileNameList})
    except Exception as e:
        return Response400(msg="保存文件出现错误：" + str(e))


@file_router.get("/xlsxsqls")
async def read_xlsx_to_sql(db: Session = Depends(get_db)):
    """
    目前有两类文件需要读取
    1. 以 S 结尾 ，则为成绩单
        以 A 结尾，则为学业分析
    2. 读入逻辑
        - 读入一条信息，
    :param db:
    :return:
    """
    await clearAllData(db)
    print("read_xlsx")
    fileNames = os.listdir(config.SAVE_FILE_DIR)
    gradeList = set()
    latestTerm = {}
    for name in fileNames:
        result = pd.read_excel(
            config.SAVE_FILE_DIR + "\\" + name
        )  # 不要加 header 默认都无列名
        term = name[-7:-5]
        stuClass = re.search(r"[A-Z]+[0-9]+", name).group()
        grade = re.search(r"[0-9]+", stuClass).group()[:2]
        gradeList.add(grade)
        if grade not in latestTerm.keys():
            latestTerm[grade] = term
        else:
            latestTerm[grade] = str(max(int(latestTerm[grade]), int(term)))
        if name[-8] == "S":
            await operation_student(db, result, stuClass, term)
            await operation_course(db, result, term, stuClass)
            await operation_scores(db, result, stuClass, term)
            pass
        elif name[-8] == "A":
            await operation_stuAnalysis(result, stuClass, term)
            pass
    ret = json.dumps(sorted(gradeList), ensure_ascii=False)
    db.add(models.ResultDict(key="grade_list", value=ret))
    db.add(
        models.ResultDict(
            key="latest_term", value=json.dumps(latestTerm, ensure_ascii=False)
        )
    )
    db.commit()
    return Response200(msg="导入数据库成功")


async def clearAllData(db: Session):
    db.query(models.Student).delete()
    # db.query(models.Course).delete()
    db.query(models.Score).delete()
    db.query(models.CalculateState).delete()
    db.query(models.ResultDict).delete()
    db.query(models.FailedRecord).delete()
    db.query(models.CourseByTermTable).delete()
    db.query(models.ClassByTermChart).delete()
    db.query(models.GradeByTermChart).delete()
    db.query(models.MajorByTermChart).delete()
    db.commit()

    pass


async def operation_stuAnalysis(db: Session, result, stuClass, term):
    """
    将学业分析写入数据库
    :param result:
    :param garde:
    :param term:
    :return:
    """

    shape = result.shape
    # print(result.shape)
    for i in range(shape[0]):
        tmpRow = result.iloc[i].tolist()
        newRow = [x for x in tmpRow if pd.isna(x) == False]
        # print(len(newRow))
        # print(newRow)
        if len(newRow) == 4:
            # 班长 or 学委
            stuID = newRow[1]
            stuName = newRow[0]
            stuType = ""
            if newRow[2] == "班长":
                stuType = 1
            elif newRow[2] == "学委":
                stuType = 2
            content = newRow[3]
            # print("学委栏")
            # print(stuID,stuType,term,content)
            # stuAnalysis_sql = StuAnalysis.query.filter((StuAnalysis.stuID == stuID) & (StuAnalysis.stuType == stuType) & (StuAnalysis.term == term)).first()
            stuAnalysis_sql = (
                db.query(models.StuAnalysis)
                .filter(
                    (models.StuAnalysis.stuID == stuID)
                    & (models.StuAnalysis.stuType == stuType)
                    & (models.StuAnalysis.term == term)
                )
                .first()
            )
            # print(stuAnalysis_sql)
            if stuAnalysis_sql:
                continue
            else:
                print("insert class commit")
                stuAnalysis_insert = models.StuAnalysis(
                    stuID=stuID,
                    stuName=stuName,
                    stuType=stuType,
                    term=term,
                    stuClass=stuClass,
                    content1=content,
                )
                db.add(stuAnalysis_insert)
                db.commit()
                db.refresh(stuAnalysis_insert)

        elif len(newRow) == 7:
            # 自己
            stuName = newRow[0]
            stuID = newRow[1]
            stuType = 3
            selfContent = newRow[3]
            monitorContent = newRow[4]
            academicContent = newRow[5]
            failSubjectName = newRow[6]
            print("学生栏")
            # print(stuID,stuType,term,grade,selfContent)
            # print(stuID,monitorType,term,grade,monitorContent)
            # print(stuID,academicType,term,grade,academicContent)

            # stuAnalysis_sql_stu = StuAnalysis.query.filter((StuAnalysis.stuID == stuID) & (StuAnalysis.stuType == stuType) & (StuAnalysis.term == term)).first()
            stuAnalysis_sql_stu = (
                db.query(models.StuAnalysis)
                .filter(
                    (models.StuAnalysis.stuID == stuID)
                    & (models.StuAnalysis.stuType == stuType)
                    & (models.StuAnalysis.term == term)
                )
                .first()
            )
            if stuAnalysis_sql_stu:
                continue
            else:
                stuAnalysis_stu = models.StuAnalysis(
                    stuID=stuID,
                    stuName=stuName,
                    stuType=stuType,
                    term=term,
                    stuClass=stuClass,
                    content1=selfContent,
                    content2=monitorContent,
                    content3=academicContent,
                    failSubjectName=failSubjectName,
                )
                db.add(stuAnalysis_stu)
                db.commit()
                db.refresh(stuAnalysis_stu)

    print("=" * 50)
    print("finish operation stuanalysis")
    print("=" * 50)


async def operation_scores(db: Session, result, stuClass, term):
    """
    将学生成绩写入数据库
    :param result:
    :param term:
    :return:
    """
    coursers = result.iloc[2].tolist()
    coursersNew = [x for x in coursers if pd.isna(x) == False]
    credits = result.iloc[3].tolist()
    creditsNew = [x for x in credits if pd.isna(x) == False]
    len_course = len(creditsNew)
    courseNames = coursersNew[:len_course]
    shape = result.shape
    for i in range(3, shape[0]):
        stuScore = result.iloc[i].tolist()
        if str(stuScore[0])[0] == "U":
            stuID = stuScore[0]
            stuScoreNum = stuScore[2 : 2 + len_course]
            for courseName, score in zip(courseNames, stuScoreNum):
                if pd.isna(score) == False:
                    score = str(score)
                    scoreList = []
                    for sub in score.split("/"):
                        sub = str(sub)
                        if sub:
                            if sub.isdigit():
                                scoreList.append(int(sub))
                            elif sub == "优":
                                scoreList.append(90)
                            elif sub == "良":
                                scoreList.append(80)
                            elif sub == "中":
                                scoreList.append(70)
                            elif sub == "差":
                                scoreList.append(59)
                            elif sub == "通过":
                                scoreList.append(80)
                            elif sub == "不通过":
                                scoreList.append(59)
                            elif sub == "缓考":
                                continue
                            else:
                                scoreList.append(0)
                    if scoreList == []:
                        continue
                    scoreList.sort()
                    if scoreList[0] < 60:
                        ret = (
                            db.query(models.FailedRecord)
                            .filter(
                                models.FailedRecord.stuID == stuID,
                                models.FailedRecord.courseName == courseName,
                                models.FailedRecord.term == term,
                                models.FailedRecord.stuClass == stuClass,
                            )
                            .first()
                        )
                        if not ret:
                            failed_insert = models.FailedRecord(
                                stuID=stuID,
                                courseName=courseName,
                                term=term,
                                stuClass=stuClass,
                            )
                            db.add(failed_insert)
                            db.commit()
                            db.refresh(failed_insert)
                    ret = (
                        db.query(models.Score)
                        .filter(
                            models.Score.stuID == stuID,
                            models.Score.courseName == courseName,
                            models.Score.stuClass == stuClass,
                        )
                        .first()
                    )
                    if ret:
                        ret.score = max(ret.score, scoreList[-1])
                        db.commit()
                        db.refresh(ret)
                        continue
                    score_insert = models.Score(
                        stuID=stuID,
                        courseName=courseName,
                        score=scoreList[-1],
                        stuClass=stuClass,
                    )
                    db.add(score_insert)
                    db.commit()
                    db.refresh(score_insert)

    print("=" * 50)
    print("finish operation_scores")
    print("=" * 50)


async def operation_course(db: Session, result, term, stuClass):
    """
    将课程信息写入数据库
    :param result:
    :param term:
    :return:
    """
    coursers = result.iloc[2].tolist()
    coursersNew = [x for x in coursers if pd.isna(x) == False]
    credits = result.iloc[3].tolist()
    creditsNew = [x for x in credits if pd.isna(x) == False]
    for x, y in zip(coursersNew, creditsNew):
        ret = (
            db.query(models.Course)
            .filter(
                models.Course.courseName == x,
                models.Course.term == term,
                models.Course.stuClass == stuClass,
            )
            .first()
        )
        if ret:
            continue
        course = models.Course(courseName=x, credit=y, term=term, stuClass=stuClass)
        db.add(course)
        db.commit()
        db.refresh(course)

    print("=" * 50)
    print("finish operation_course")
    print("=" * 50)


async def operation_student(db: Session, result, stuClass, term):
    """
    将学生信息写入数据库
    :param result: pandas读入的成绩单数据
    :return:
    """
    print("operation_scores")
    # 课程名称 & 学分
    # 学号
    stuIDList = result.iloc[:, [0]].values
    stuIDList = stuIDList.reshape(-1)
    stuNewIDList = [x for x in stuIDList if pd.isna(x) == False]
    stuNewIDList = stuNewIDList[2:]
    # 姓名
    stuNameList = result.iloc[:, [1]].values
    stuNameList = stuNameList.reshape(-1)
    stuNewNameList = [x for x in stuNameList if pd.isna(x) == False]
    for x, y in zip(stuNewIDList, stuNewNameList):
        ret = (
            db.query(models.Student)
            .filter(
                models.Student.stuID == x,
                models.Student.stuName == y,
                models.Student.stuClass == stuClass,
                models.Student.term == term,
            )
            .first()
        )
        if ret:
            continue
        student = models.Student(stuID=x, stuName=y, stuClass=stuClass, term=term)
        db.add(student)
        db.commit()
        db.refresh(student)

    print("=" * 50)
    print("finish operation_student")
    print("=" * 50)
