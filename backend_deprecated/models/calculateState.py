from sqlalchemy import Boolean, Column, String

from .base import Base

class CalculateState(Base):
    __tablename__ = "calculateState"

    name = Column(String(50), primary_key=True, nullable=False)