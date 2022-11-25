from sqlalchemy import Column, Index, Integer, String
from sqlalchemy.dialects.mssql import TINYINT

from ..core.db_configs import MapBase
from ..core.models import TimeBaseMixin


class User(MapBase, TimeBaseMixin):
    """ 用户 """

    __tablename__ = "user"
    __table_args__ = (Index("ux_passport_id", "passport_id", unique=True),)

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    passport_id = Column(Integer, nullable=False, comment="森果通行证ID")
    sex = Column(TINYINT, nullable=False, default=0, comment="用户性别 0:未知 1:男 2:女")
    headimgurl = Column(String(1024), comment="用户头像")
    realname = Column(String(128), comment="用户真实姓名")
    nickname = Column(String(64), default="", comment="用户昵称")
    phone = Column(String(32), default=None, comment="手机号")
    wx_unionid = Column(String(64), comment="微信unionid")
