from pydantic import BaseModel,Field
import typing as t

class UserBase(BaseModel):
    name: str = Field(...,description="用户名")
    is_active: bool = True
    is_superuser: bool = False

class UserLogin(BaseModel):
    name: str = Field(...,description="用户名")
    password: str = Field(...,description="登陆密码")



class UserOut(UserBase):
    pass

class UserCreate(UserBase):
    password: str

    class Config:
        from_attributes = True

class UserEdit(UserBase):
    password: t.Optional[str] = None

    class Config:
        from_attributes = True

class User(UserBase):

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    name: str = None
    permissions: str = "user"









