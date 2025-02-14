from datetime import timedelta


from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.requests import Request

from models import User
from core import verify_password,create_access_token
from core.auth import authenticate_user
from core import deps
from schemas import UserCreate,Response400,Response200,ResponseToken
import schemas
from database.curd_ec import ec_get_by_grade
from database.session import get_db
from core import config,security

login_router = APIRouter()


@login_router.post("/login")
async def user_login(request:Request,form_data:OAuth2PasswordRequestForm = Depends(),db=Depends(get_db)):
    """
    没有权限认证和 token情形下的用户登陆
    :param form_data:
        - name: 用户名
        - password: 密码
    :param db:
    :return:
    """
    user = authenticate_user(db,form_data.username,form_data.password)
    print("login:{}".format(user))
    if not user:
        return Response400( msg='登陆失败')
    else:
        token = create_access_token({"sub": user.name})
        print("token:{}".format(token))
        return ResponseToken(data={"token": f"bearer {token}", "is_superuser": user.is_superuser}, access_token=token)

@login_router.put("/logout", summary="注销")
async def user_logout(request: Request, user: User = Depends(deps.get_current_user)):
    request.app.state.redis.delete(user.name)
    return Response200()














