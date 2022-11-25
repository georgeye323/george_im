import datetime
import hashlib
import urllib

import requests

from ..settings import AUTH_API_SECRETKEY, AUTH_HOST_NAME
from .db_configs import auth_redis


class AuthFunc:
    """用于跟中台交换passport信息"""

    source = "caigou"

    @classmethod
    def _calc_token(cls, timestr):
        """token计算方式"""
        s = AUTH_API_SECRETKEY + timestr
        return hashlib.md5(s.encode("utf-8")).hexdigest()

    @classmethod
    def gen_token(cls):
        """生成token"""
        timestr = datetime.datetime.now().strftime("%Y%m%d%H")
        return cls._calc_token(timestr)

    @classmethod
    def verify_token(cls, token):
        """验证token"""
        # 上一小时的token在这一小时的前5分钟内仍然有效
        token_expire_delay = 5
        now = datetime.datetime.now()
        tokens = {now}
        if now.minute <= token_expire_delay:
            tokens.add(now - datetime.timedelta(hours=1))
        tokens = map(lambda x: x.strftime("%Y%m%d%H"), tokens)
        tokens = map(lambda x: cls._calc_token(x), tokens)
        return token in tokens

    @classmethod
    def verify_passport_info(cls, type_: str, value: str, force_create: bool = False):
        """根据phone或者wx_unionid在中台验证该账号是否存在,
        :param type_ phone or wx_unionid
        :param value phone or wx_unionid的值
        :param force_create 不存在时是否创建
        :return 查询到的用户信息或者创建的用户的信息,
             {'success': True,
              'data': {'id': 16, 'wx_unionid': 'oxkR_jqFyIUF3zeYMkTSmPa4JBjo', 'qq_account': None,
                      'email': '1522398832@qq.com', 'phone': '18071720503'}
             }
        """
        assert type_ in ("phone", "wx_unionid")
        url = urllib.parse.urljoin(AUTH_HOST_NAME, "/passport/verify?s=im")
        headers = {"Authorization": cls.gen_token()}
        data = dict(
            source=cls.source, type=type_, value=value, force_create=force_create
        )
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        if resp.status_code != 200:
            raise Exception(resp.text)
        resp = resp.json()
        return resp["success"], resp.get("data") or resp.get("error_text")

    @classmethod
    def get_passport_info(cls, passport_id: int):
        """
        根据passport_id 去中台查询一个人的信息
        :param passport_id:
        :return: 查询到的用户信息
            {'wx_unionid': 'oIWUauHbaXLvx5qdHu5iurTRc-go',
            'sex': 2,
            'qq_account': None,
            'headimgurl': 'o_1discv26j1lvj1fdv13t81kb32m27.jpg',
            'can_login': 1,
            'realname': '测试需要一个很长很长的很长的昵',
            'email': '1234@qq.com',
            'nickname': '阿树方塘',
            'password': '8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92',
            'phone': '18162664593'
            }
        """
        url = urllib.parse.urljoin(AUTH_HOST_NAME, "/passport/get?s=im")
        headers = {"Authorization": cls.gen_token()}
        data = dict(id=passport_id)
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        if resp.status_code != 200:
            raise Exception(resp.text)

        resp = resp.json()
        return resp.get("data")

    @classmethod
    def update_passport_info(cls, passport_id: int, type_: str, value: str):
        """更新passport表信息"""
        assert type_ in ("phone", "wx_unionid")

        url = urllib.parse.urljoin(AUTH_HOST_NAME, "/passport/update?s=im")
        headers = {"Authorization": cls.gen_token()}
        data = dict(id=passport_id, type=type_, value=value)
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        if resp.status_code != 200:
            raise Exception(resp.text)
        resp = resp.json()

        return resp["success"], resp.get("data") or resp.get("error_text")

    @classmethod
    def update_passport_info_extend(
        cls, passport_id: int, user_info: dict, update_type: str = "update"
    ):
        """
        通过passport_id更新中台的对应的用户的信息
        :param passport_id:
        :param user_info: { "password": PASSWORD,
                            "nickname": NICKNAME,
                            "realname": REALNAME,
                            "headimgurl": HEAD_IMG_URL,
                            "sex": SEX:0,1,2
                            "birthday": BIRTHDAY }
        :param update_type: update
        :return:
        """
        url = urllib.parse.urljoin(AUTH_HOST_NAME, "/passport/update/extend?s=im")
        headers = {"Authorization": cls.gen_token()}
        data = dict(id=passport_id, data=user_info, source=cls.source, type=update_type)
        resp = requests.post(url, json=data, headers=headers, timeout=5)
        if resp.status_code != 200:
            raise Exception(resp.text)
        resp = resp.json()

        return resp["success"], resp.get("data") or resp.get("error_text")
