from sqlalchemy import Boolean, Column, Integer, String
from werkzeug.security import generate_password_hash,check_password_hash


from .base import Base

class User(Base):
    __tablename__ = 'user'

    cID = Column(String(10), primary_key=True,comment="工号")
    cName = Column(String(50), nullable=False, primary_key=True)
    hashed_password = Column(String(200), nullable=False) # 加密的。生成的会比较长
    is_active = Column(Boolean,default=True)
    is_superuser = Column(Boolean,default=True)
    # type = db.Column(db.String(200),nullable=False)

