from sqlalchemy import Boolean, Column, String

from .base import Base

class User(Base):
    """用户"""
    __tablename__ = 'user'

    name = Column(String(50), nullable=False, primary_key=True)
    hashed_password = Column(String(200), nullable=False) # 加密的。生成的会比较长
    is_active = Column(Boolean,default=True)
    is_superuser = Column(Boolean,default=True)

