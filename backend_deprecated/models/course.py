from sqlalchemy import Boolean, Column, Integer, String, Float

from .base import Base

class Course(Base):
    __tablename__ = "course"

    courseName = Column(String(30), primary_key=True)
    credit = Column(Float, nullable=False)
    term = Column(Integer, primary_key=True)
    type = Column(Integer, default=0, nullable=False)  # todo#课程类型:0-必修,1-专选
    stuClass = Column(String(8), primary_key=True, nullable=False)
