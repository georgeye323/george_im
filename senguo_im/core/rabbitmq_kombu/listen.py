import asyncio
import json
import traceback

from tornado.options import options
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from senguo_im.connect.apis.handlers import MessageHandler
from senguo_im.core.rabbitmq_kombu.config import KR, KP
from senguo_im.core.rabbitmq_kombu.room_handler import room_handler

try:
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
except:
    print(traceback.format_exc())


@KR.route(
    exchange_name="ChatExchange",
    queue_name_list=[f"ws:chat:{options.port}"],
    # routing_key="ChatExchange",
)
def rabbitmq_callback(body, message):
    """
    监听rabbitmq的消息处理逻辑
        create_room: 新建会员
        chat: 常规聊天消息
    """
    room_id = body.get("data", {}).get("room_id", 0)
    event = body.get("event", "")
    if event == "create_room":
        room_handler.new_room(room_id, body["data"]["member_list"])
    elif event == "chat":
        # 批发易推送消息存储
        if body.get("source") and body["source"] == "pfeasy":
            MessageHandler.save_data(body["data"])
            ret_msg = dict(
                event="receive_msg",
                data={"msg_id": body["data"]["msg_id"]},
                passport_id=body["data"]["passport_id"],
            )
            KP.send_as_task(
                exchange_name="ChatExchange",
                payload=ret_msg,
                # routing_key="ChatExchange",
            )
        # 获取room中需要推送消息的成员
        client_ids = room_handler.rooms_info.get(room_id, [])
        client_ids = list(set(client_ids))
        for client_id in client_ids:
            # 兼容多端登录
            ws_conns = room_handler.clients_info.get(client_id, [])
            ws_conns = list(set(ws_conns))
            passport_id = body.get("data", {}).get("passport_id", 0)
            if ws_conns and passport_id != client_id:
                for ws_conn in ws_conns:
                    ws_conn.write_message(
                        json.dumps({"event": body["event"], "data": body["data"]})
                    )
    else:
        # 后续添加日志
        pass
    message.ack()
