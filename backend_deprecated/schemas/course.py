import typing as t

from pydantic import BaseModel,Field

class BaseQuery(BaseModel):
    term: str = Field(default='11', description="学期")

class CourseFailedDownload(BaseModel):
    courseName: str = Field(...,description="课程名称")
    
    
class GradeQuery(BaseQuery):
    pass

class ClassQuery(BaseQuery):
    pass

class CourseQuery(BaseQuery):
    pass

