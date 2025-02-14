from sqlalchemy import Column, String
from sqlalchemy.dialects.mysql import LONGTEXT

from .base import Base

class ResultDict(Base):
    __tablename__ = "resultDict"

    key = Column(String(255), primary_key=True, nullable=False)
    value = Column(LONGTEXT)
