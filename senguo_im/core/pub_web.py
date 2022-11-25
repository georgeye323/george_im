import datetime
import hashlib
import time
import traceback
import urllib.parse
from hashlib import md5

import requests
import tornado.websocket
from tornado.options import options
from tornado.web import Finish

from senguo_im.core.im_encrypt import LoginPassportIdCrypto, SimpleEncrypt
from senguo_im.user.models import User

from ..settings import (
    AUTH_COOKIE_DOMAIN,
    AUTH_COOKIE_EXPIRE_DAYS,
    AUTH_HOST_NAME,
    IM_LOGIN_SECRET_KEY,
)
from ..user import models
from ..user.services import get_user_by_passport_id
from .auth import AuthFunc
from .db_configs import DBSession, auth_redis, slave_DBSession


class GlobalBaseHandler(tornado.web.RequestHandler):
    """
    通用的请求处理基类，主要定义了一些API通信规范和常用的工具
    响应处理：
       一个请求在逻辑上分为三个结果：请求错误、请求失败和请求成功。请求错误会通常
       是由于请求不合法（如参数错误、请求不存在、token无效等），直接返回http状
       态码；请求失败通常是由于一些事物逻辑上的错误，比如库存不够、余额不足等；请
       求成功不解释

       错误请求: send_error(status_code, **kargs)[tornado自带，直接响应响应的HTTP错误头，如果你需要自定义错误Page的话，重写write_error(status_code, **kargs)]
       请求失败: send_fail(fail_code, fail_text)[返回JSON数据格式: {"success":False, "code":fail_code, "text":fail_text}]
       请求成功: send_success(**kwargs)[返回JSON数据格式:{"success":True, **kwargs}]
    """

    def send_success(self, **kwargs):
        obj = {"success": True}
        for k in kwargs:
            obj[k] = kwargs[k]
        self.write(obj)

    def send_fail(
        self,
        error_text=None,
        error_code=None,
        error_redirect=None,
        error_key=None,
        error_obj=None,
        extra_text=None,
    ):
        if error_obj:
            error_code = error_obj.error_code
            error_text = error_obj.error_text

        if type(error_code) == int:
            res = {
                "success": False,
                "error_code": error_code,
                "error_text": error_text,
                "error_redirect": error_redirect,
                "error_key": error_key,
                "extra_text": extra_text,
            }
        else:
            res = {"success": False, "error_text": error_text}
        self.set_header("Content-Type", "utf-8")
        self.write(res)

    def write_error(self, status_code, error_msg="", error_deal="", **kwargs):
        if status_code == 400:
            if kwargs.get("exc_info"):
                self.send_fail("参数错误: {}".format(kwargs["exc_info"][1]), 400)
            else:
                self.send_fail("参数错误: %s" % error_msg, 400)
        elif status_code == 404:
            self.send_fail("地址错误", 404)
        elif status_code == 500:
            self.send_fail("系统错误", 500)
        elif status_code == 401:
            self.send_fail(error_msg or "您的登录已经过期，请重新登录", 401)
        elif status_code == 403:
            self.send_fail("没有权限", 403)
        else:
            super().write_error(status_code, **kwargs)

    @property
    def session(self):
        if hasattr(self, "_session"):
            return getattr(self, "_session")
        self._session = DBSession()
        return self._session

    # 从库会话
    @property
    def slave_session(self):
        if hasattr(self, "_slave_session"):
            return getattr(self, "_slave_session")
        self._slave_session = slave_DBSession()
        return self._slave_session

    # 关闭数据库会话
    def on_finish(self):
        if hasattr(self, "_session"):
            self._session.close()
        if hasattr(self, "_slave_session"):
            self._slave_session.close()


class UserBaseHandler(GlobalBaseHandler):
    """ 用户的基类，用来处理认证 """

    expire = 7  # token有效期/天
    token_len = 5  # token参数数量

    # 获取当前用户（判断用户是否登录）
    def get_current_user(self) -> User:
        token = self.request.headers.get("Authentication", "")
        if not token:
            token = self.get_argument("token", "")
        token_list = token.split("|")
        if len(token_list) != self.token_len:
            return False
        sign = token_list[0]
        encrypt_pi = token_list[1]
        encrypt_time = token_list[2]
        passport_hash = token_list[3]
        self.shop_id = int(token_list[4])
        passport_id: str = LoginPassportIdCrypto.decrypt(encrypt_pi)
        timestamp: str = LoginPassportIdCrypto.decrypt(encrypt_time)
        # token过期
        if int(time.time()) > int(timestamp):
            return False
        # 签名错误
        s = IM_LOGIN_SECRET_KEY + passport_id
        if sign != SimpleEncrypt.encrypt(s):
            return False
        # 检查hash
        real_hash = (
            auth_redis.get("passport_hash:{}".format(passport_id)) or b""
        ).decode()
        if real_hash and real_hash != passport_hash:
            return None
        # 查询用户
        current_user = get_user_by_passport_id(self.session, int(passport_id))
        if not current_user:
            return False
        self._user = current_user

        return self._user

    def prepare(self):
        """登录限制"""
        if not self.current_user:
            self.send_error(401)
            raise Finish()

    def set_default_headers(self):
        """跨域问题"""

        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "*, Content-Type")
        self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.set_header("Content-Type", "application/json")
        self.set_header(
            "Access-Control-Max-Age", "3600"
        )  # 用来指定本次预检请求的有效期，单位为秒，在此期间不用发出另一条预检请求。

    def options(self):

        self.set_status(200)
        raise Finish()

    def get_token(self, passport_id: int, shop_id: int) -> str:
        """获取鉴权token"""
        passport_hash = self.calc_passport_hash(passport_id)
        passport_id = str(passport_id)
        s = IM_LOGIN_SECRET_KEY + passport_id
        encrypt_pi = LoginPassportIdCrypto.encrypt(passport_id)
        encrypt_time = LoginPassportIdCrypto.encrypt(str(self.get_timestamp()))

        return (
            SimpleEncrypt.encrypt(s)
            + f"|{encrypt_pi}"
            + f"|{encrypt_time}"
            + f"|{passport_hash}"
            + f"|{shop_id}"
        )

    def get_timestamp(self) -> int:
        end_time = datetime.datetime.now().date() + datetime.timedelta(days=self.expire)
        timestamp = int(time.mktime(end_time.timetuple()))

        return timestamp

    def calc_passport_hash(self, passport_id: int):
        """计算passport hash"""

        columns = ("id", "phone", "wx_unionid", "qq_account", "email", "can_login")
        try:
            data = AuthFunc.get_passport_info(passport_id)
        except:
            print(traceback.format_exc())
        else:
            data["id"] = passport_id
            hash_str = "".join([str(data[c] or "") for c in columns])
            return md5(hash_str.encode()).hexdigest()


class UserLoginHandler(UserBaseHandler):
    """用户登录基类"""

    # 覆盖超类的prepare，解除登录限制
    def prepare(self):
        pass


class OutwardAuthHandler(UserBaseHandler):
    def prepare(self):
        """授权校验"""
        token = self.request.headers.get("Authorization", "")
        if not token:
            return self.send_error(401, error_msg="Unauthorized")
        if not AuthFunc.verify_token(token):
            return self.send_error(403, error_msg="Invalid token")
