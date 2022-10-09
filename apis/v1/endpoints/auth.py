from datetime import timedelta


from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.requests import Request

from models import User
from core import verify_password,create_access_token
from core.auth import authenticate_user,sign_up_new_user,authenticate_user_cID
from schemas import UserCreate,Response400,Response200
import schemas
from database.curd_ec import ec_get_by_grade
from database.session import get_db
from core import config,security

login_router = APIRouter(tags=["认证相关"])

# @login_router.post("/token")
# # async def login(db=Depends(get_db),form_data:OAuth2PasswordRequestForm = Depends()):
# async def login(db=Depends(get_db)):
#     user = authenticate_user(db,form_data.username,form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"}
#         )
#     access_token_expires = timedelta(
#         minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
#     )
#     if user.is_superuser == 'admin':
#         permissions = "admin"
#     else:
#         permissions = "user"
#     access_token = security.create_access_token(
#         data={"sub":user.cName,"permissions":"bearer"},
#         expires_delta=access_token_expires
#     )
#
#     return {"access_token":access_token,"token_type":"bearer"}

@login_router.post("/login")
async def login_without_auth(form_data:schemas.UserLogin,db=Depends(get_db)):
    """
    没有权限认证和 token情形下的用户登陆
    :param form_data:
    :param db:
    :return:
    """
    user = authenticate_user_cID(db,form_data.cID,form_data.password)
    print("login:{}".format(user))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return Response200(msg="登陆认证成功")


@login_router.post("/signup")
async def signup(db=Depends(get_db),form_data:OAuth2PasswordRequestForm= Depends()):
    """
    注册
    :param db:
    :param form_data:
    :return:
    """
    user = sign_up_new_user(db,form_data.username,form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account already exists",
            headers={"WWW-Authenticate": "Bearer"}
        )
    access_token_expires = timedelta(
        minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    if user.is_superuser:
        permissions = "admin"
    else:
        permissions = "user"

    access_token = security.create_access_token(
        data={"sub": user.cName, "permissions": "bearer"},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}














