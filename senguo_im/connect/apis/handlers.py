import datetime
import json
import traceback

import tornado
from tornado.websocket import WebSocketHandler

from senguo_im.chat.models import RoomMessage
from senguo_im.chat.services import create_room_message, list_room_by_passport_id
from senguo_im.core.db_configs import DBSession, slave_DBSession
from senguo_im.core.pub_web import UserBaseHandler
from senguo_im.core.rabbitmq_kombu.config import KP


class MessageHandler(UserBaseHandler, tornado.websocket.WebSocketHandler):
    def prepare(self):
        super().prepare()
        self.on_finish()

    def set_default_headers(self):
        pass

    def get_room_ids(self, passport_id):
        """当前连接用户-所有会话"""
        slave_session = slave_DBSession()
        try:
            rooms = list_room_by_passport_id(
                slave_session, passport_id, -1, 0, self.shop_id
            )
        except:
            rooms = []
        finally:
            slave_session.close()

        return [room.id for room in rooms]

    @classmethod
    def save_data(cls, data):
        """保存消息"""
        session = DBSession()
        try:
            create_room_message(session, data)
            session.commit()
        except:
            print(traceback.format_exc())
        finally:
            session.close()


class IMSocketHandler(MessageHandler):
    """即时通讯"""

    def initialize(self, room_handler):
        self.room_handler = room_handler

    def open(self):
        self.passport_id = self.current_user.passport_id
        self.room_ids = self.get_room_ids(self.passport_id)
        self.room_handler.add_room(self.passport_id, self.room_ids)
        self.room_handler.add_client(self.passport_id, self)

    def on_close(self):
        self.room_handler.remove_room(self.passport_id, self.room_ids)
        self.room_handler.remove_client(self.passport_id, self)

    def on_message(self, message):
        """
        message数据结构:
            {
                "event": "chat",
                "data": {
                    "type": "img/text", # 消息类型
                    "msg_id": "passport_id|timestamp", # 消息ID
                    "msg": "你好啊！", # 消息内容
                    "room_id": 123, # 会话ID
                    "passport_id": 1234, # 发送者ID
                    "timestamp": 123123, # 发送时间
                }
            }
        """
        try:
            if isinstance(message, str):
                message = eval(message)
            if message["event"] == "chat":
                # 这个链接应该是采购端直连的, 可以直接判断来源为采购
                if message.get("data"):
                    if message["data"].get("source", 0) != RoomMessage.SOURCE_PF:
                        message["data"].update({"source": RoomMessage.SOURCE_CG})
                self.save_data(message["data"])
                self.write_message(
                    json.dumps(
                        {
                            "event": "receive_msg",
                            "data": {"msg_id": message["data"]["msg_id"]},
                        }
                    )
                )
                KP.send_as_task(
                    exchange_name="ChatExchange",
                    payload=message,
                    # routing_key="ChatExchange",
                )
            elif message["event"] == "ping":
                self.write_message(json.dumps({"event": "pong", "data": "pong"}))
        except:
            print(traceback.format_exc())
            self.write_message(json.dumps(dict(event="error_format", data="消息格式错误")))

    # 跨域检查
    def check_origin(self, origin):
        """暂时不做跨域限制"""
        # print(origin)
        # parsed_origin = urllib.parse.urlparse(origin)
        # try:
        #     return parsed_origin.netloc.index(".senguo.cc")!=-1
        # except BaseException:
        #     return False
        return True

    # @tornado.gen.coroutine
    # def add_listen(self, message):
    #     yield tornado.gen.Task(
    #         self.client.subscribe, f"np_websocket:{message.get('room_id', 0)}"
    #     )
