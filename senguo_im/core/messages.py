import json

from .db_configs import redis, redis_msg


class MessageTool:
    """客户端获取消息或者服务器设置消息集"""

    def __init__(
        self,
        shop_id=None,
        redis_handler=redis_msg,
        user_id=None,
        key_prefix="universal",
    ):
        self._user_id = user_id  # 操作人/接收消息的人
        self._redis_handler = redis_handler  # 操作redis的句柄
        self._shop_id = shop_id
        if shop_id is None:
            # 不同的人接收的消息不同
            self._key = key_prefix + ":%d" % user_id
        else:
            # 同一个店铺消息相同
            self._key = key_prefix + ":%d" % shop_id  # 获取或设置消息的前缀

    def set_message(self, msg=None, receiver_ids=None, args=None, expire=86400):
        """设置消息"""
        map_content = dict()
        if msg:
            map_content["msg"] = msg
        if self._shop_id is not None and receiver_ids:
            map_content["receiver_ids"] = receiver_ids
        if args:
            map_content.update(args)
        try:
            self._redis_handler.hmset(self._key, map_content)
            self._redis_handler.expire(self._key, expire)
        except Exception as e:
            print(e)
            return False
        return True

    def get_message(self, get_dict=False):
        """获取消息"""
        msg = dict() if get_dict else ""
        try:
            all_content = self._redis_handler.hgetall(self._key)  # type: dict
            if all_content:
                result = dict()
                for key, value in all_content.items():
                    result[key.decode("utf-8")] = value.decode("utf-8")
                if get_dict:
                    msg = result
                if self._shop_id is not None:
                    receiver_ids = json.loads(result["receiver_ids"])
                    if self._user_id in receiver_ids:
                        msg = result.get("msg", "")
        except Exception:
            pass
        return msg

    def received_msg(self):
        """用户获取消息后的操作"""
        try:
            if self._shop_id:
                all_content = self._redis_handler.hgetall(self._key)  # type: dict
                if all_content:
                    result = dict()
                    for key, value in all_content.items():
                        result[key.decode("utf-8")] = value.decode("utf-8")
                    receiver_ids = json.loads(result.get("receiver_ids", "[]"))
                    if self._user_id in receiver_ids:
                        receiver_ids.remove(self._user_id)
                        # 因为设置后会重置过期时间，所以得设置剩余过期时间
                        result["receiver_ids"] = receiver_ids
                        self.set_message(
                            args=result, expire=self._redis_handler.ttl(self._key)
                        )
            else:
                self._redis_handler.delete(self._key)  # 单人消息接收即毁
        except Exception:
            pass


class WebSocketTool(object):
    @staticmethod
    def publish(room_id: int, event: str, data: dict):
        """ 通过redis利用websocket向客户端发布一条消息
        :param room_id: 会话id，在接收端控制
        :param event: str, 事件名
        :param data: 事件中需要发布的数据
        """
        message = json.dumps({"room_id": room_id, "event": event, "data": data})
        redis.publish(f"np_websocket:{room_id}", message)

    @staticmethod
    def publish_create_room(room_id: int, event: str, data: dict):
        """ 通过redis利用websocket向客户端发布一条消息
        :param room_id: 会话id，在接收端控制
        :param event: str, 事件名
        :param data: 事件中需要发布的数据
        """
        message = json.dumps({"room_id": room_id, "event": event, "data": data})
        redis.publish(f"np_websocket:create_room", message)
