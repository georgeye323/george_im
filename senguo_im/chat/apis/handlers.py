import datetime
import json
import time
from operator import attrgetter
import traceback

from marshmallow import fields

from senguo_im.chat.apis.schemas import (
    ChatCreateDeserialize,
    ChatCreateSerializer,
    ChatDetailDeserialize,
    ChatDetailSerializer,
    ChatListDeserialize,
    ChatListSerializer,
    ChatMessageUpdateDeserialize,
    GetListRoomIdDeserialize,
    GetUnreadCountDeserialize,
    AllReadDeserialize,
    CMUCallbackDeserialize,
    SendMessageToCgDeserialize,
    GetUnreadListApiDeserialize,
)
from senguo_im.chat.constant import DefaultObject, RoomConstants, RoomMessageConstants
from senguo_im.chat.models import RoomMessage
from senguo_im.chat.services import (
    create_room_member,
    create_room_single,
    get_room_by_id,
    get_room_by_members_group,
    get_room_messsage_unread_by_room_ids,
    get_shop_by_id,
    list_account_by_passport_ids,
    list_room_by_passport_id,
    list_room_message_by_unread,
    list_room_message_unread_by_room_id,
    list_room_messsage_by_room_id,
    list_room_messsage_group_by_room_id,
    list_shop_by_ids,
    list_sms_record_by_phone_type,
    update_room_messsage_by_msg_room_id,
    update_all_read_message,
    create_room_message,
    get_member_list_by_room_id,
    update_room_member,
    get_customer_by_shop_id_and_user_id,
)
from senguo_im.core.arguments import use_args, use_kwargs
from senguo_im.core.auth import AuthFunc
from senguo_im.core.get_cg_data import GetData
from senguo_im.core.im_encrypt import PFSimpleEncrypt
from senguo_im.core.messages import WebSocketTool
from senguo_im.core.pub_web import UserBaseHandler, GlobalBaseHandler
from senguo_im.core.rabbitmq_kombu.config import KP
from senguo_im.user.services import get_user_by_passport_id, list_user_by_passport_ids, create_user


class ChatCreateApi(UserBaseHandler):
    """会话创建"""

    @use_args(ChatCreateDeserialize)
    def post(self, args: dict):
        session = self.session
        if not args["members"]:
            return self.send_fail("members is empty")
        if args["room_type"] == RoomConstants.RoomType.GROUP:
            room = self.create_chat_by_single(session, args)
            shop = get_shop_by_id(session, room.accept_shop_id)
            user = get_user_by_passport_id(session, room.apply_passport_id)
            # 批发易发起的聊天，可能用户未在IM系统注册
            if not user:
                passport_info = AuthFunc.get_passport_info(args["apply_passport_id"])
                if not passport_info:
                    return self.send_fail("用户未在森果旗下注册")
                passport_info["passport_id"] = args["apply_passport_id"]
                user = create_user(session, passport_info)
            member_list = list_account_by_passport_ids(session, args["members"])
        else:
            # 预留其他会话类型
            return self.send_fail("暂只支持多人聊天")
        session.commit()
        setattr(room, "shop_info", shop or {})
        setattr(room, "account_info", user)
        setattr(room, "member_list", member_list)
        data = ChatCreateSerializer().dump(room)

        return self.send_success(data=data)

    def create_chat_by_single(self, session, args):
        """创建单聊"""
        room = get_room_by_members_group(session, args)
        if not room:
            room = create_room_single(session, args)
            for passport_id in args["members"]:
                create_room_member(session, room.id, passport_id)
            # 推送websocket，更新监听的会话数量
            message = {
                "event": "create_room",
                "data": dict(member_list=args["members"], room_id=room.id),
            }
            # WebSocketTool.publish_create_room(room.id, "create_room", ws_data)
            KP.send_as_task(
                exchange_name="ChatExchange",
                payload=message,
                # routing_key="ChatExchange",
            )

        return room


class ChatListApi(UserBaseHandler):
    """会话获取-列表"""

    @use_kwargs(ChatListDeserialize)
    def get(self, page: int, page_size: int):
        shop_id = self.shop_id
        session = self.slave_session
        user = self.current_user
        rooms = list_room_by_passport_id(
            session, user.passport_id, page, page_size, shop_id
        )
        shop_id_list = [i.accept_shop_id for i in rooms]
        apply_passport_id_list = [i.apply_passport_id for i in rooms]
        room_id_list = [i.id for i in rooms]
        # 获取详细信息
        shops = list_shop_by_ids(session, shop_id_list)
        accounts = list_user_by_passport_ids(session, apply_passport_id_list)
        msgs = list_room_messsage_group_by_room_id(session, room_id_list)
        unread_dict = list_room_message_unread_by_room_id(
            session, room_id_list, user.passport_id
        )
        shop_dict = {shop.id: shop for shop in shops}
        account_dict = {account.passport_id: account for account in accounts}
        msg_dict = {msg.room_id: msg for msg in msgs}
        data_list = []
        for room in rooms:
            msg = msg_dict.get(room.id, "")
            if not msg:
                continue
            setattr(
                room,
                "shop_info",
                shop_dict.get(room.accept_shop_id, DefaultObject.SHOP_INFO),
            )
            setattr(room, "account_info", account_dict.get(room.apply_passport_id, {}))
            setattr(room, "msg", msg)
            setattr(room, "sort_key", msg.create_at)
            setattr(room, "unread_count", unread_dict.get(room.id, 0))
            data_list.append(room)
        data_list.sort(key=attrgetter("sort_key"), reverse=True)
        data = ChatListSerializer(many=True).dump(data_list)
        has_more = True if len(rooms) == page_size else False

        return self.send_success(data=data, has_more=has_more)


class ChatDetailApi(UserBaseHandler):
    """会话获取-详情"""

    @use_kwargs(ChatDetailDeserialize)
    def get(self, page: int, page_size: int, room_id: int, msg_id: str):
        session = self.slave_session
        _session = self.session
        room = get_room_by_id(session, room_id)
        if not room:
            return self.send_fail("会话不存在")
        members = eval(room.members)
        shop = get_shop_by_id(session, room.accept_shop_id)
        user = get_user_by_passport_id(session, room.apply_passport_id)
        if not user:
            data = AuthFunc.get_passport_info(room.apply_passport_id)
            if not data:
                return self.send_fail("用户未在森果旗下注册")
            data["passport_id"] = room.apply_passport_id
            user = create_user(_session, data)
        member_list = list_account_by_passport_ids(session, members)
        # 获取批发店铺的支付分信息
        _shop = shop
        if shop:
            # 获取店铺该用户的会员信息
            success, shop_payment_point_info = GetData.get_payment_point_info_by_passport(shop.passport_id)
            _shop = self.handle_shop_info(shop, success, shop_payment_point_info)
        # 获取用户的支付分信息
        customer = get_customer_by_shop_id_and_user_id(session, shop.id, user.passport_id)
        _success, user_payment_point_info = GetData.get_payment_point_info_by_passport(room.apply_passport_id)
        _user = self.handle_user_info(user, _success, user_payment_point_info, customer)
        # 消息列表
        msg_list = list_room_messsage_by_room_id(
            self.session, room_id, page, page_size, msg_id=msg_id
        )
        passport_id_list = [msg.passport_id for msg in msg_list]
        msg_user_list = list_user_by_passport_ids(session, passport_id_list)
        msg_user_dict = {msg_user.passport_id: msg_user for msg_user in msg_user_list}
        for msg in msg_list:
            setattr(msg, "account_info", msg_user_dict.get(msg.passport_id, {}))
            # 消息标记已读
            if msg.is_read == RoomMessageConstants.IsRead.NO:
                msg.is_read = RoomMessageConstants.IsRead.YES
        self.session.commit()

        setattr(room, "shop_info", _shop or {})
        setattr(room, "account_info", _user)
        setattr(room, "member_list", member_list)
        setattr(room, "msg_list", msg_list)
        data = ChatDetailSerializer().dump(room)
        has_more = True if len(msg_list) == page_size else False

        return self.send_success(data=data, has_more=has_more)

    def handle_shop_info(self, shop, flag, shop_payment_point_info):
        class Shop:
            pass
        result = Shop()

        result.id = shop.id
        result.shop_name = shop.shop_name
        result.shop_img = shop.shop_img
        result.market_id = shop.market_id
        result.shop_phone = shop.shop_phone
        result.full_name = shop.full_name if hasattr(shop, "full_name") else ""
        result.shorter_name = shop.full_name if hasattr(shop, "shorter_name") else ""
        result.wx_authorization_status = shop_payment_point_info.get("wx_authorization_status", 0) if flag else 0
        result.wx_authorization_code = shop_payment_point_info.get("wx_authorization_code", "") if flag else ""
        result.wx_openid = shop_payment_point_info.get("wx_openid", "") if flag else ""

        return result

    def handle_user_info(self, user, flag, user_payment_point_info, customer):
        result = dict(
            id=user.id,
            realname=user.realname,
            nickname=user.nickname,
            sex=user.sex,
            headimgurl=user.headimgurl,
            passport_id=user.passport_id,
            wx_authorization_status=user_payment_point_info.get("wx_authorization_status", 0) if flag else 0,
            wx_authorization_code=user_payment_point_info.get("wx_authorization_code", 0) if flag else "",
            wx_openid=user_payment_point_info.get("wx_openid", 0) if flag else "",
            customer_id=customer.id if customer else 0
        )
        return result


class ChatMessageUpdateApi(UserBaseHandler):
    """消息标记已读"""

    @use_kwargs(ChatMessageUpdateDeserialize)
    def post(self, room_id: int, msg_id: str):
        update_room_messsage_by_msg_room_id(
            self.session, room_id, msg_id, self.current_user.passport_id
        )
        self.session.commit()

        return self.send_success()


class ChatMessageUnreadGetApi(UserBaseHandler):
    """未读消息"""

    def get(self):
        session = self.slave_session
        user = self.current_user
        rooms = list_room_by_passport_id(session, user.passport_id, -1, 0, self.shop_id)
        room_id_list = [i.id for i in rooms]
        unread_count = get_room_messsage_unread_by_room_ids(
            session, room_id_list, user.passport_id
        )

        return self.send_success(unread_count=unread_count)


class GetListRoomIdApi(GlobalBaseHandler):
    """批发获取店铺会话id列表"""

    @use_kwargs(GetListRoomIdDeserialize)
    def get(self, passport_id: int, shop_id: int, sign: str):
        session = self.slave_session
        sign_str = "{}@{}".format(passport_id, shop_id)
        sign_temp = PFSimpleEncrypt.encrypt(sign_str)
        if sign != sign_temp:
            return self.send_fail("非法请求！")
        rooms = list_room_by_passport_id(session, passport_id, -1, 0, shop_id)
        data = [room.id for room in rooms]
        return self.send_success(data=data)


class GetUnreadListAPi(GlobalBaseHandler):
    """批发获取每个room的未读数量"""
    @use_kwargs(GetUnreadListApiDeserialize)
    def get(self, room_id_list, passport_id, sign, timestamp):
        session = self.slave_session
        sign_str = "{}@{}".format(passport_id, timestamp)
        sign_temp = PFSimpleEncrypt.encrypt(sign_str)
        if sign != sign_temp:
            return self.send_fail("非法请求！")
        unread_count_map = list_room_message_unread_by_room_id(
            session, room_id_list, passport_id
        )
        return self.send_success(unread_count=unread_count_map)


class GetUnreadCountApi(GlobalBaseHandler):
    """批发获取未读数量"""

    @use_kwargs(GetUnreadCountDeserialize)
    def get(self, room_id_list, passport_id, sign, timestamp):
        session = self.slave_session
        sign_str = "{}@{}".format(passport_id, timestamp)
        sign_temp = PFSimpleEncrypt.encrypt(sign_str)
        if sign != sign_temp:
            return self.send_fail("非法请求！")
        unread_count = get_room_messsage_unread_by_room_ids(
            session, room_id_list, passport_id
        )
        return self.send_success(unread_count=unread_count)


class AllReadApi(GlobalBaseHandler):
    """批发访问一键已读"""

    @use_kwargs(AllReadDeserialize)
    def post(self, passport_id: int, shop_id: int, sign: str):
        session = self.session
        sign_str = "{}@{}".format(passport_id, shop_id)
        sign_temp = PFSimpleEncrypt.encrypt(sign_str)
        if sign != sign_temp:
            return self.send_fail("非法请求！")
        update_all_read_message(session, passport_id, shop_id)
        session.commit()
        return self.send_success()


class ChatMessageUnreadCallbackApi(GlobalBaseHandler):
    def initialize(self, send_type):
        self.send_type = send_type

    @use_args(CMUCallbackDeserialize(many=True))
    def post(self, args: dict):
        phone_list = [i["mobile"] for i in args if i.get("mobile")]
        resp_dict = {i["mobile"]: i for i in args}
        # 查询
        now_hour = datetime.datetime.now().strftime("%Y-%m-%d %H") + ":00:00"
        now_hour = datetime.datetime.strptime(now_hour, "%Y-%m-%d %H:%M:%S")
        _from_date = now_hour + datetime.timedelta(hours=-1)
        _to_date = datetime.datetime.now()
        sms_record = list_sms_record_by_phone_type(
            self.session, phone_list, _from_date, _to_date, self.send_type
        )
        for record in sms_record:
            rep = resp_dict.get(record.phone)
            if rep:
                if rep.get("report_status") == "SUCCESS":
                    record.customer_receive_status = 1
                else:
                    record.customer_receive_status = 2
                    record.remark = rep.get("error_msg", "")
                self.session.add(record)
        if sms_record:
            self.session.commit()

        return self.write("SUCCESS")


class SendMessageToCg(GlobalBaseHandler):
    """批发向采购发送消息"""

    @use_args(SendMessageToCgDeserialize)
    def post(self, args: dict):
        session = self.session
        # 记录一下这里的apply_passport_id实际指的是需要发送的采购商id，accept_shop_id指的是发消息的店铺id
        apply_passport_id = args.get("apply_passport_id")
        passport_id = args.get("passport_id")
        shop_id = args.get("accept_shop_id")
        sign = args.get("sign")
        timestamp = args.get("timestamp", int(time.time()))
        source = args["source"]
        message_type = args.get("message_type", "template")
        # 验签
        sign_str = "{}@{}".format(apply_passport_id, shop_id)
        sign_temp = PFSimpleEncrypt.encrypt(sign_str)
        if sign != sign_temp:
            return self.send_fail("非法请求！")
        # 创建会话
        if args["room_type"] == RoomConstants.RoomType.GROUP:
            # 这里会话要由接受者创建。
            room = self.create_chat_by_single(session, args)
            user = get_user_by_passport_id(session, room.apply_passport_id)
            # 批发易发起的聊天，可能用户未在IM系统注册
            if not user:
                passport_info = AuthFunc.get_passport_info(args["apply_passport_id"])
                if not passport_info:
                    return self.send_fail("用户未在森果旗下注册")
                passport_info["passport_id"] = args["apply_passport_id"]
                user = create_user(session, passport_info)
        else:
            # 预留其他会话类型
            return self.send_fail("暂只支持多人聊天")

        # 发送消息
        message_data = args.get("message_data")
        message = {
            "event": "chat",
            "data": {
                "type": message_type,  # 消息类型
                "msg_id": str(passport_id) + "|" + str(timestamp),  # 消息ID
                "msg": json.loads(message_data)['title'],  # 消息内容
                "room_id": room.id,  # 会话ID
                "passport_id": passport_id,  # 发送者ID
                "timestamp": timestamp,  # 发送时间
                "template_message": json.loads(message_data),
                "source": source
            }
        }
        self.save_data(session, message["data"])
        KP.send_as_task(
            exchange_name="ChatExchange",
            payload=message,
        )
        session.commit()
        return self.send_success()

    def create_chat_by_single(self, session, args):
        """创建单聊"""
        room = get_room_by_members_group(session, args)
        if not room:
            room = create_room_single(session, args)
            for passport_id in args["members"]:
                create_room_member(session, room.id, passport_id)
            # 推送websocket，更新监听的会话数量
            message = {
                "event": "create_room",
                "data": dict(member_list=args["members"], room_id=room.id),
            }
            KP.send_as_task(
                exchange_name="ChatExchange",
                payload=message,
            )
        else:
            # 发送消息的人是变化的  需要动态更新
            old_member_list = get_member_list_by_room_id(session, room.id)
            old_members = [i.passport_id for i in old_member_list]
            # 需要删除的
            del_members = list(set(old_members) - set(args['members']))
            # 需要新增的
            add_members = list(set(args['members']) - set(old_members))
            room.members = str(args['members'])
            for passport_id in add_members:
                create_room_member(session, room.id, passport_id)
            update_room_member(session, room.id, del_members)

        return room

    def save_data(self, session, data):
        """保存消息"""
        try:
            create_room_message(session, data)
        except:
            print(traceback.format_exc())


class CGChatCreateApi(SendMessageToCg):
    """小程序在线还款通知会话创建"""

    @use_args(ChatCreateDeserialize)
    def post(self, args: dict):
        session = self.session
        if not args["members"]:
            return self.send_fail("members is empty")
        if args["room_type"] == RoomConstants.RoomType.GROUP:
            room = self.create_chat_by_single(session, args)
            shop = get_shop_by_id(session, room.accept_shop_id)
            user = get_user_by_passport_id(session, room.apply_passport_id)
            # 批发易发起的聊天，可能用户未在IM系统注册
            if not user:
                passport_info = AuthFunc.get_passport_info(args["apply_passport_id"])
                if not passport_info:
                    return self.send_fail("用户未在森果旗下注册")
                passport_info["passport_id"] = args["apply_passport_id"]
                user = create_user(session, passport_info)
        else:
            # 预留其他会话类型
            return self.send_fail("暂只支持多人聊天")
        message_data = "您好，我想使用小程序在线还款功能，麻烦开启一下"
        timestamp = int(time.time())
        message = {
            "event": "chat",
            "data": {
                "type": "system_payback_tip",  # 消息类型
                "msg_id": str(args["apply_passport_id"]) + ":" + str(timestamp),  # 消息ID
                "msg": message_data,  # 消息内容
                "room_id": room.id,  # 会话ID
                "passport_id": args["apply_passport_id"],  # 发送者ID
                "timestamp": timestamp,  # 发送时间
                "source": RoomMessage.SOURCE_CG
            }
        }
        # 极光推送需要这些信息
        if args["shop_name"] and args["customer_name"]:
            message["data"]["shop_name"] = args["shop_name"]
            message["data"]["customer_name"] = args["customer_name"]
            message["data"]["shop_id"] = args["accept_shop_id"]
        self.save_data(session, message["data"])
        KP.send_as_task(
            exchange_name="ChatExchange",
            payload=message,
        )
        session.commit()

        return self.send_success()
