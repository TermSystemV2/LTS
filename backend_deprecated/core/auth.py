import models
from database.curd import get_user_by_name
from core import security


def authenticate_user(db, name: str, password: str):
    print("authenticate_user:{}".format(name))
    user: models.User = get_user_by_name(db, name)
    if not user:
        return False
    if not security.verify_password(password, user.hashed_password):
        return False
    return user
