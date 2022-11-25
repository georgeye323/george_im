from typing import Tuple, Iterable
import requests
from .auth import AuthFunc
from senguo_im.settings import CG_HOST_NAME


class GetData:
    """
    查询采购数据库
    """
    target_api = ""
    data = {}

    @classmethod
    def proxy_requests(cls,) -> Tuple[bool, list]:
        headers = {"Authorization": AuthFunc.gen_token()}
        try:
            response = requests.get(
                CG_HOST_NAME + cls.target_api, json=cls.data, headers=headers, timeout=3
            )
            if response.status_code != 200:
                raise Exception(f"错误状态码：{response.status_code}")
            resp = response.json()
            if not resp["success"]:
                raise Exception(resp.get("error_text"))
            # print(f"resp:{resp}")
            resp = resp["data"]
        except Exception as e:
            return False, "网络异常，请稍后再试"
        return True, resp

    @classmethod
    def get_payment_point_info_by_passport(cls, passport_id: int):
        cls.target_api = "/api/cg/payment-point/user-info/get"
        cls.data = dict(
            passport_id=passport_id,
        )
        return cls.proxy_requests()