import os
import re
import typing as t

from fastapi import APIRouter, File,UploadFile,Request, Response, Depends,status,HTTPException
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
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


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
        with open(save_file_name,"wb") as fw:
            fw.write(res)
        return Response200(msg="文件读取成功",data={"filename": file.filename,"file type":file.content_type})
    except Exception as e:
        return Response400(msg="保存文件出现错误："+str(e))


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
        return Response200(msg="文件读取成功",data={"filename": fileNameList})
    except Exception as e:
        return Response400(msg="保存文件出现错误："+str(e))




@file_router.put("/xlsxsqls")
async def read_xlsx_to_sql(db=Depends(get_db)):
    """
    目前有两类文件需要读取
    1. 以 S 结尾 ，则为成绩单
       以 A 结尾，则为学业分析
    2. 读入逻辑
        - 读入一条信息，
    :param db:
    :return:
    """
    print("read_xlsx")
    fileNames = os.listdir(config.SAVE_FILE_DIR)
    for name in fileNames:
        result = pd.read_excel(config.SAVE_FILE_DIR + "\\" + name)  # 不要加 header 默认都无列名
        term = name[-7:-5]
        if name[0] == 'C' or name[0] == 'Z' or name[0] == 'X':
            stuClass = name[:6]
            grade = name[2:4]
        else:
            stuClass = name[:7]
            grade = name[3:5]
        # print({
        #     "class": stuClass,
        #     "grade": grade,
        #     "term": term
        # })
        if name[-8] == 'S':
            await operation_student(db,result, stuClass)
            await operation_courses(db,result, term)
            await operation_scores(db,result, grade, term)
            pass
        elif name[-8] == 'A':
            await operation_stuAnalysis(result, stuClass, term)
            pass
    return Response200(msg="导入数据库成功")


async def operation_stuAnalysis(db:Session,result,stuClass,term):
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
            stuType = ''
            if newRow[2] == "班长":
                stuType = 1
            elif newRow[2] == '学委':
                stuType = 2
            content = newRow[3]
            # print("学委栏")
            # print(stuID,stuType,term,content)
            # stuAnalysis_sql = StuAnalysis.query.filter((StuAnalysis.stuID == stuID) & (StuAnalysis.stuType == stuType) & (StuAnalysis.term == term)).first()
            stuAnalysis_sql = db.query(models.StuAnalysis).filter(
                (models.StuAnalysis.stuID == stuID) & (models.StuAnalysis.stuType == stuType) & (models.StuAnalysis.term == term)).first()
            # print(stuAnalysis_sql)
            if stuAnalysis_sql:
                continue
            else:
                print("insert class commit")
                stuAnalysis_insert = models.StuAnalysis(stuID=stuID,stuName=stuName,stuType=stuType,term=term,stuClass=stuClass,content1=content)
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
            stuAnalysis_sql_stu = db.query(models.StuAnalysis).filter((models.StuAnalysis.stuID == stuID) & (models.StuAnalysis.stuType == stuType) & (models.StuAnalysis.term == term)).first()
            if stuAnalysis_sql_stu:
                continue
            else:
                stuAnalysis_stu = models.StuAnalysis(stuID=stuID,stuName=stuName,stuType=stuType,term=term,stuClass=stuClass,
                                              content1=selfContent,content2=monitorContent,content3=academicContent,failSubjectName=failSubjectName)
                db.add(stuAnalysis_stu)
                db.commit()
                db.refresh(stuAnalysis_stu)

    print("="*50)
    print("finish operation stuanalysis")
    print("=" * 50)



async def operation_scores(db:Session,result,grade,term):
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
    # print(creditsNew)
    len_courese = len(creditsNew)
    # print(len_courese)
    courseNames = coursersNew[:len_courese]
    # print(courseNames)
    shape = result.shape
    # print(result)
    for i in range(3,shape[0]):
        stuScore = result.iloc[i].tolist()
        if str(stuScore[0])[0] == 'U':
            stuID = stuScore[0]
            stuScoreNum = stuScore[2:2+len_courese]
            # print(stuScoreNum)
            for (courseName,score) in zip(courseNames,stuScoreNum):
                if pd.isna(score) == False:
                    # print(stuID, courseName, score, grade)
                    if type(score) == int:
                        score = str(score)
                    if '/' in (score):
                        score_sp = score.split('/')
                        if (score_sp[0].isdigit()):
                            score = score.split('/')[0]  # 切分 27/60
                        elif (score_sp[1].isdigit()):
                            score = score.split('/')[1]
                    if not re.search(r'\d',score):
                        # 不包含数字 如 缺交作业/
                        score = 0
                    # score_sql = Scores.query.filter((Scores.stuID == stuID) & (Scores.courseName == courseName)).first()
                    score_sql = db.query(models.Scores).filter((models.Scores.stuID == stuID) & (models.Scores.courseName == courseName)).first()
                    if score_sql:
                        # Scores.query().filter((Scores.stuID == stuID) & (Scores.courseName == courseName)).delete()
                        continue
                    else:
                        score_insert = models.Scores(stuID=stuID,courseName=courseName,score=score,grade=grade,term=term)
                        db.add(score_insert)
                        db.commit()
                        db.refresh(score_insert)

    print("=" * 50)
    print("finish operation_scores")
    print("=" * 50)



async def operation_courses(db:Session,result,term):
    """
    将课程信息写入数据库
    :param result:
    :param term:
    :return:
    """
    coursers = result.iloc[2].tolist()
    coursersNew = [x for x in coursers if pd.isna(x) == False]
    # print((coursersNew))
    credits = result.iloc[3].tolist()
    creditsNew = [x for x in credits if pd.isna(x) == False]
    # print(creditsNew)
    for (x,y) in zip(coursersNew,creditsNew):
        # print((x,y))
        # course_sql = Courses.query.filter((Courses.courseName == x) & (Courses.term == term)).first()
        course_sql = db.query(models.Courses).filter((models.Courses.courseName == x) & (models.Courses.term == term)).first()
        if course_sql:
            # Student.query().filter(Student.stuID == x).delete()
            continue
        else:
            course = models.Courses(courseName=x, credit=y, term=term)
            db.add(course)
            db.commit()
            db.refresh(course)

    print("=" * 50)
    print("finish commit course")
    print("=" * 50)


async def operation_student(db:Session,result,stuClass):
    """
    将学生信息写入数据库
    :param result: pandas读入的成绩单数据
    :return:
    """
    print("operation_scores")
    # 课程名称 & 学分
    # 学号
    stuIDList = result.iloc[:,[0]].values
    stuIDList = stuIDList.reshape(-1)
    stuNewIDList = [x for x in stuIDList if pd.isna(x) == False]
    stuNewIDList = stuNewIDList[2:]
    # 姓名
    stuNameList = result.iloc[:, [1]].values
    stuNameList = stuNameList.reshape(-1)
    stuNewNameList = [x for x in stuNameList if pd.isna(x) == False]
    for (x,y) in zip(stuNewIDList,stuNewNameList):
        student_sql = db.query(models.Student).filter(models.Student.stuID == x).first()

        if student_sql:
            # db.session.query(Note).filter(Note.title=='测试').delete()
            # db.session.query(Student).filter(Student.stuID == x).delete()
            # # db.session.add(student)
            # db.session.commit()
            continue
        else:
            student = models.Student(stuID=x, stuName=y, stuClass=stuClass)
            print(student.to_dic())
            db.add(student)
            db.commit()

    print("=" * 50)
    print("finish operation_scores")
    print("=" * 50)