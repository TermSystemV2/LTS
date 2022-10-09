from sqlalchemy import Boolean, Column, Integer, String


from .base import Base

class Scores(Base):
    __tablename__ = 'scores'
    stuID = Column(String(10),primary_key=True)
    courseName = Column(String(30), primary_key=True)
    score = Column(Integer)
    grade = Column(String(10)) # 年级
    term = Column(Integer)

    def to_dic(self):
        return {
            "stuID":self.stuID,
            "courseName": self.courseName,
            "score": self.stuID,
            "grade": self.grade,
            "term": self.term
        }
