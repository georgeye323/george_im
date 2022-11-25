from marshmallow import Schema, fields, validate

from senguo_im.chat.models import RoomMessage
from senguo_im.core.schema import (
    AccountBaseSerializer,
    PageBaseDeserialize,
    RoomMessageBaseSerializer,
    ShopBaseSerializer,
)


class ChatCreateDeserialize(Schema):
    """创建会话-入参"""

    members = fields.List(
        fields.Integer(required=True), required=True, description="会话成员列表"
    )
    accept_shop_id = fields.Integer(required=True, description="会话接收者店铺ID")
    apply_passport_id = fields.Integer(required=False, missing="", description="会话发起者-仅支持采购商")
    room_type = fields.Integer(
        required=False, validate=validate.OneOf([1, 2, 3]), missing=2, description="聊天类型"
    )
    shop_name = fields.String(required=False, missing="", description="店铺名称")
    customer_name = fields.String(required=False, missing="", description="会员名称")


class ChatCreateSerializer(Schema):
    """创建会话-出参"""

    id = fields.Integer(data_key="room_id", description="会话id")
    room_type = fields.Integer(description="会话类型")
    shop_info = fields.Nested(ShopBaseSerializer, description="店铺信息")
    account_info = fields.Nested(AccountBaseSerializer, description="用户信息")
    member_list = fields.Nested(AccountBaseSerializer, many=True, description="会话成员信息")


class ChatListDeserialize(PageBaseDeserialize):
    """会话列表-入参"""

    pass


class ChatListSerializer(ChatCreateSerializer):
    """会话列表-出参"""

    msg = fields.Nested(RoomMessageBaseSerializer, description="最新一条消息")
    unread_count = fields.Integer(description="未读消息数量")


class ChatDetailDeserialize(PageBaseDeserialize):
    """会话详情-入参"""

    room_id = fields.Integer(required=True, description="会话id")
    msg_id = fields.String(required=False, missing="", description="消息")


class ChatDetailSerializer(ChatCreateSerializer):
    """会话详情-入参"""

    msg_list = fields.Nested(RoomMessageBaseSerializer, many=True, description="消息列表")


class ChatMessageUpdateDeserialize(Schema):
    """消息已读-入参"""

    room_id = fields.Integer(description="会话id")
    msg_id = fields.String(description="消息id")


class GetListRoomIdDeserialize(Schema):
    """批发获取店铺会话id列表-入参"""

    passport_id = fields.Integer(required=False, missing=0, description="森果通行证")
    shop_id = fields.Integer(required=False, missing=0, description="店铺ID")
    sign = fields.String(required=False, missing=0, description="验证签名")


class GetUnreadCountDeserialize(Schema):
    """批发获取未读数量-入参"""

    room_id_list = fields.List(
        fields.Integer(description="会话id"), required=False, missing=[], description="会话id列表"
    )
    passport_id = fields.Integer(required=False, missing=0, description="森果通行证")
    sign = fields.String(required=False, missing=0, description="验证签名")
    timestamp = fields.Integer(required=False, missing=0, description="时间戳")


class AllReadDeserialize(Schema):
    """批发一键已读"""

    passport_id = fields.Integer(required=False, missing=0, description="森果通行证")
    shop_id = fields.Integer(required=False, missing=0, description="店铺ID")
    sign = fields.String(required=False, missing=0, description="验证签名")


class CMUCallbackDeserialize(Schema):
    """短信发送-回调"""

    error_msg = fields.String(description="运营商返回的代码")
    mobile = fields.String(description="接收手机号")
    report_status = fields.String(description="接收状态")


class SendMessageToCgDeserialize(ChatCreateDeserialize):
    """给采购助手发消息"""
    sign = fields.String(required=False, missing=0, description="验证签名")
    message_data = fields.String(required=False, missing="", description="发送的消息")
    passport_id = fields.Integer(required=False, missing="", description="会话发起者")
    timestamp = fields.Integer(required=False, description="时间戳")
    source = fields.Integer(required=False, missing=RoomMessage.SOURCE_PF, description="消息类型")
    message_type = fields.String(required=False, missing="template", description="消息类型")


class GetUnreadListApiDeserialize(Schema):
    """批发获取未读数量-入参"""

    room_id_list = fields.List(
        fields.Integer(description="会话id"), required=False, missing=[], description="会话id列表"
    )
    passport_id = fields.Integer(required=False, missing=0, description="森果通行证")
    sign = fields.String(required=False, missing=0, description="验证签名")
    timestamp = fields.Integer(required=False, missing=0, description="时间戳")
