from tornado.web import Finish

from senguo_im.core.arguments import use_kwargs
from senguo_im.core.auth import AuthFunc
from senguo_im.core.db_configs import redis
from senguo_im.core.im_encrypt import SimpleEncrypt
from senguo_im.core.pub_web import UserLoginHandler
from senguo_im.user.apis.schemas import UserLoginDeserialize
from senguo_im.user.services import create_user, get_user_by_passport_id, update_user


class UserLoginApi(UserLoginHandler):
    """登录"""

    def on_finish(self):
        super().on_finish()
        if hasattr(self, "login_lock_key"):
            redis.delete(self.login_lock_key)

    @use_kwargs(UserLoginDeserialize)
    def post(self, passport_id: int, sign: str, shop_id: int):
        passport_info = self.is_verify(passport_id, sign)
        session = self.session
        user = get_user_by_passport_id(session, passport_id)
        if not user:
            user = create_user(session, passport_info)
        else:
            user = update_user(user, passport_info)
        session.commit()

        return self.send_success(token=self.get_token(passport_id, shop_id))

    def is_verify(self, passport_id, sign):
        """校验"""
        # 防并发
        self.login_lock_key = f"user_login:{passport_id}"
        if redis.get(self.login_lock_key):
            self.send_fail("防并发")
            raise Finish()
        redis.set(self.login_lock_key, 1, 60)
        calc_sign = SimpleEncrypt.encrypt(str(passport_id))
        if calc_sign != sign:
            print(f"sign:{sign}\npassport_id:{passport_id}")
            self.send_error(401, error_msg="Unauthorized")
            raise Finish()
        passport_info = AuthFunc.get_passport_info(passport_id)
        if not passport_info:
            # 中台没有返回无权限
            print(f"passport_id:{passport_id}")
            self.send_error(401, error_msg="Unauthorized")
            raise Finish()
        passport_info["passport_id"] = passport_id

        return passport_info
