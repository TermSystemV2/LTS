from sqlalchemy import Boolean, Column, Integer, String

from .base import Base
#todo:fix
class ExcellentStudyClass(Base):
    __tablename__ = 'excellentStudyClass'
    grade = Column(Integer,primary_key=True)
    year = Column(Integer,primary_key=True)
    totalClassNum = Column(Integer)
    excellentClassNum = Column(Integer)

    def to_dict(self):
        return {
            "grade":self.grade,
            "year":self.year,
            "totalClassNum":self.totalClassNum,
            "excellentClassNum":self.excellentClassNum
        }

    def __str__(self):
        return str(
            {
                "grade": self.grade,
                "year": self.year,
                "totalClassNum": self.totalClassNum,
                "excellentClassNum": self.excellentClassNum
            }
        )
