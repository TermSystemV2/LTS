from sqlalchemy import Boolean, Column, Integer, String,Float


from .base import Base

class Courses(Base):
    __tablename__ = 'courses'
    courseName = Column(String(30), primary_key=True)
    credit = Column(Float, nullable=False)
    term = Column(Integer, primary_key=True)