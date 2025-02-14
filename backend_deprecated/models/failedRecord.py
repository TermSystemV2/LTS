from sqlalchemy import Column, String

from .base import Base

class FailedRecord(Base):
    __tablename__ = "failedRecord"

    stuID = Column(String(10), primary_key=True, nullable=False)
    courseName = Column(String(30), primary_key=True, nullable=False)
    term = Column(String(2), primary_key=True, nullable=False)
    stuClass = Column(String(8), primary_key=True, nullable=False)
