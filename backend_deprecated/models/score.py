from sqlalchemy import Boolean, Column, Integer, String

from .base import Base

class Score(Base):
    __tablename__ = "score"

    stuID = Column(String(10), primary_key=True)
    courseName = Column(String(30), primary_key=True)
    score = Column(Integer)
    stuClass = Column(String(8), primary_key=True, nullable=False)

    def to_dic(self):
        return {
            "stuID": self.stuID,
            "courseName": self.courseName,
            "score": self.score,
            "stuClass": self.stuClass,
        }
