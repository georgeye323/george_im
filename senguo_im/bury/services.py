import time
import typing
import json
from enum import Enum
from typing import Dict, Any, Callable

from senguo_im.bury.enums import SmsSceneEnum, SmsSendModeEnum
from senguo_im.chat.models import SMSRecord
from senguo_im.core.rabbitmq_kombu.config import BURY_KP


class MQMessageNameEnum(Enum):
    """自定义message_name"""
    TEST = "test"
    CMS_CLUE_USER_SYNC = "cms_clue_user_sync"
    SMS_SEND_RECORD = "sms_send_record"


class MessageBody:
    """基类 body  需要自己扩展。可继承扩展， con-sub 需要一致"""

    def __init__(
            self,
            message_name: MQMessageNameEnum,
            body: Dict[Any, Any],
            timestamp: int = 0,
            **kwargs  # 其他信息
    ):
        self.message_name = message_name.value if isinstance(message_name, MQMessageNameEnum) else message_name
        self.body = body
        if not timestamp:
            self.timestamp = int(time.time())
        else:
            self.timestamp = timestamp

        self.kw = kwargs

    def default_message(self):
        return {
            "message_name": self.message_name,
            "timestamp": self.timestamp,
            "body": self.body
        }

    def to_dict(self) -> dict:
        default_message = self.default_message()

        # 合并 message
        default_message.update(self.kw)
        return default_message

    @classmethod
    def parse_message_body(cls, body: bytes):
        json_body = json.loads(body.decode("utf-8"))
        return cls(**json_body)


def build_push_sms_msg_list(push_sms_record_list: typing.List[SMSRecord]):
    """
        构造mq推送列表，构造的对象会推送到数据中台，字段定义见数据中台。
    """
    res_list = []
    for sms_record in push_sms_record_list:
        res_list.append(
            {
                "sms_id": SmsSceneEnum.聊天消息未读提醒.mark,
                "sms_fk_id": sms_record.id,
                "phone": sms_record.phone,
                "passport_id": sms_record.passport_id,
                "fact_sms_count": sms_record.fact_sms_count,
                "yunpian_sid": sms_record.yunpian_sid,
                "record_status": sms_record.record_status,
                "send_mode": SmsSendModeEnum.SYSTEM_AUTO.mark,
                "customer_receive_status": sms_record.customer_receive_status,
                "remark": sms_record.remark,
                "create_at": sms_record.create_at.strftime("%Y-%m-%d %H:%S:%M"),
                "update_at": sms_record.update_at.strftime("%Y-%m-%d %H:%S:%M"),
            }
        )
    return res_list


def push_msg_to_bury(push_msg_list):
    """推送"""
    for msg in push_msg_list:
        body = MessageBody(MQMessageNameEnum.SMS_SEND_RECORD.value, msg).to_dict()
        BURY_KP.send_as_task(
            exchange_name="bury_topic_message",
            payload=body,
            routing_key="/message",
            exchange_type="topic",
            durable=False,
        )
