import json

import requests

from senguo_im.core.auth import AuthFunc
from senguo_im.settings import YUNPIAN_SYSTEM_APIKEY, ROOT_HOST_NAME, PF_HOST_NAME


class YunPainFunc:
    # 服务地址
    sms_host = "sms.yunpian.com"
    voice_host = "voice.yunpian.com"

    # 版本号
    version = "v2"

    # 模板短信接口的URI
    sms_tpl_send_uri = "/" + version + "/sms/tpl_single_send.json"
    sms_text_send_uri = "/" + version + "/sms/single_send.json"

    # 获取短信接口的URI
    sms_short_url_uri = "/" + version + "/short_url/shorten.json"

    # 营销短信群发URI
    sms_marketing_group_send_uri = "/" + version + "/sms/tpl_batch_send.json"

    # 新的群发地址
    sms_send_mass_uri = "/" + version + "/sms/batch_send.json"

    # 短信签名
    sms_sign_pfy = "【森果批发系统】"
    sms_sign_cgzs = "【森果批发系统】"

    # 短信文本
    sms_text_pfy = "您有一条新的采购商在线咨询信息未读，点击{} 立即回复TA"
    sms_text_cgzs = "您有一条新的批发商回复未读，点击{} 立即回复TA"

    # 短信回调
    sms_callback_pfy = ROOT_HOST_NAME + "/api/chat/msg-unread/callback/pfy"
    sms_callback_cgzs = ROOT_HOST_NAME + "/api/chat/msg-unread/callback/cgzs"

    # 跳转中间页面的服务器域名
    pf_open_host = "https://pf.senguo.cc"

    @classmethod
    def asyn_send_msg(cls, tpl_value, phones: list, sign_type, callback_url):
        """
        模板接口发短信（文本传入）群发，云片接口文档：
            https://www.yunpian.com/official/document/sms/zh_cn/domestic_batch_send
        """
        # 短信中不能包含'【'和'】'，发送前进行替换
        tpl_value = tpl_value.replace("【", "[")
        tpl_value = tpl_value.replace("】", "]")
        text = f"{sign_type}{tpl_value}"
        params = {
            "apikey": YUNPIAN_SYSTEM_APIKEY,
            "mobile": ",".join(map(str, phones)),
            "text": text,
            "callback_url": callback_url,
            # "uid": sms_marketing_activity_id,
        }
        headers = {
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8;",
            "Accept": "application/json;charset=utf-8;",
        }
        res = requests.post(
            "http://" + cls.sms_host + cls.sms_send_mass_uri,
            data=params,
            headers=headers,
        )
        response_str = res.text
        response = json.loads(response_str)
        return response

    @classmethod
    def tpl_short_url(cls, apikey, long_url):
        """云片-获取短链接"""
        params = {'apikey': apikey, 'long_url': long_url}
        res = requests.post("http://" + YunPainFunc.sms_host + YunPainFunc.sms_short_url_uri, data=params)
        response_str = res.text
        response = json.loads(response_str)
        code = response.get('code', 1)
        if code == 0:
            return response["short_url"]["short_url"]
        else:
            return long_url

    @classmethod
    def asyn_send_unread_msg(cls, tpl_value: str, phones: list, sign_type: str, callback_url: str, source: str):
        """短信通知-未读聊天消息"""
        if source == "app":
            long_link = f"{YunPainFunc.pf_open_host}/common/common_sms_to_app/get?app_name=pfy"
            short_link = cls.tpl_short_url(YUNPIAN_SYSTEM_APIKEY, long_link).split("//")[-1]
        elif source == "wx":
            # 避免直接操作access_token,直接从批发拿
            pf_url = PF_HOST_NAME + "/api/external/wx-url-scheme/get"
            data = cls.proxy_request(pf_url)
            wx_url_scheme = data.get("wx_url_scheme")
            qrcode_url = data.get("qrcode_url")
            if wx_url_scheme and wx_url_scheme["errcode"] == 0:
                link = wx_url_scheme.get("openlink", "")
                long_link = f"{YunPainFunc.pf_open_host}/common/common_sms_to_h5/get?link={link}&qrcode_url={qrcode_url}"
                short_link = cls.tpl_short_url(YUNPIAN_SYSTEM_APIKEY, long_link).split("//")[-1]
            else:
                short_link = ""
        else:
            short_link = ""
        tpl_value = tpl_value.format(f"#{short_link}#")

        return cls.asyn_send_msg(tpl_value, phones, sign_type, callback_url)

    @classmethod
    def proxy_request(cls, url: str):
        headers = {"Authorization": AuthFunc.gen_token()}
        response = requests.get(
            url, headers=headers, timeout=3
        )
        if response.status_code == 200:
            data = response.json().get("data", {})
        else:
            data = {}

        return data
