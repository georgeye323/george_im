from typing import Iterable, List

from sqlalchemy.orm import Session

from senguo_im.user.models import User


def list_user_by_passport_ids(
    session: Session, apply_passport_id_list: Iterable
) -> List[User]:
    if not apply_passport_id_list:
        return []
    users = (
        session.query(User).filter(User.passport_id.in_(apply_passport_id_list)).all()
    )

    return users


def get_user_by_passport_id(session: Session, passport_id: int) -> User:

    result = session.query(User).filter_by(passport_id=passport_id).first()

    return result


def create_user(session: Session, passport_info: dict):

    user_info = dict(
        passport_id=passport_info["passport_id"],
        wx_unionid=passport_info["wx_unionid"],
        headimgurl=passport_info["headimgurl"],
        realname=passport_info["realname"],
        nickname=passport_info["nickname"],
        phone=passport_info["phone"],
    )
    user = User(**user_info)
    session.add(user)
    session.flush()

    return user


def update_user(user: User, passport_info: dict):

    user.headimgurl = passport_info["headimgurl"]
    user.realname = passport_info["realname"]
    user.nickname = passport_info["nickname"]
    user.phone = passport_info["phone"]

    return user
