from senguo_im.chat.apis.handlers import (
    ChatCreateApi,
    ChatDetailApi,
    ChatListApi,
    ChatMessageUnreadCallbackApi,
    ChatMessageUnreadGetApi,
    ChatMessageUpdateApi,
    GetListRoomIdApi,
    GetUnreadCountApi,
    AllReadApi,
    SendMessageToCg,
    CGChatCreateApi,
    GetUnreadListAPi,
)

urlpatterns = [
    (r"/api/chat/create", ChatCreateApi),  # 会话创建
    (r"/api/chat/list", ChatListApi),  # 会话列表获取
    (r"/api/chat/detail", ChatDetailApi),  # 会话详情获取
    (r"/api/chat/msg/update", ChatMessageUpdateApi),  # 消息标记已读
    (r"/api/chat/msg-unread/get", ChatMessageUnreadGetApi),  # 消息标记未读-获取总数量
    (r"/api/chat/room-ids/get", GetListRoomIdApi),  # 批发获取店铺会话列表ids
    (r"/api/chat/unread-count/get", GetUnreadCountApi),  # 批发获取未读数量
    (r"/api/chat/unread-count/list", GetUnreadListAPi),  # 批发获取每个room的未读数量
    (r"/api/chat/all-read/update", AllReadApi),  # 批发一键已读
    (
        r"/api/chat/msg-unread/callback/pfy",
        ChatMessageUnreadCallbackApi,
        {"send_type": 1},
    ),  # 消息标记未读-短信通知回调
    (
        r"/api/chat/msg-unread/callback/cgzs",
        ChatMessageUnreadCallbackApi,
        {"send_type": 2},
    ),  # 消息标记未读-短信通知回调

    (r"/api/chat/send_message_to_cg", SendMessageToCg),  # 给采购发送通知消息
    (r"/api/chat/send/online_payback/open/message", CGChatCreateApi),  # 给采购发送通知消息
]
