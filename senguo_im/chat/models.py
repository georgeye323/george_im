from sqlalchemy import BigInteger, Column, Index, Integer, String, JSON
from sqlalchemy.dialects.mssql import TINYINT

from ..core.db_configs import MapBase
from ..core.models import TimeBaseMixin


class Room(MapBase, TimeBaseMixin):
    """会话"""

    __tablename__ = "room"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    # 冗余字段，列表升序后转字符串
    members = Column(String(1024), nullable=False, comment="会员成员")
    room_type = Column(TINYINT, nullable=False, default=2, comment="会话类型，1：单聊，2：群聊")
    app_type = Column(TINYINT, nullable=False, default=1, comment="会话数据共享范围，1：批发")
    status = Column(TINYINT, nullable=False, default=1, comment="会话状态，1：正常 2：过期")
    # 会话信息
    accept_shop_id = Column(Integer, nullable=False, default=0, comment="会话接收者店铺ID")
    apply_passport_id = Column(Integer, nullable=False, default=0, comment="会话发起者")


class RoomMember(MapBase, TimeBaseMixin):
    """会话成员"""

    __tablename__ = "room_member"
    __table_args__ = (Index("ix_passport_id", "passport_id"),)

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    room_id = Column(Integer, nullable=False, comment="会话ID")
    passport_id = Column(Integer, nullable=False, comment="成员")
    status = Column(TINYINT, nullable=False, default=1, comment="成员状态，1：正常 2：删除")


class RoomMessage(MapBase, TimeBaseMixin):
    """会话消息存储"""

    __tablename__ = "room_message"
    __table_args__ = (
        Index("ix_msg_id", "msg_id", unique=True),
        Index("ix_room_passport_id_create_at", "room_id", "passport_id", "create_at"),
    )

    SOURCE_DEFAULT = 0  # 未知
    SOURCE_PF = 1  # 批发
    SOURCE_CG = 2  # 采购

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    msg_id = Column(String(50), nullable=False, comment="前端生成的消息ID")
    passport_id = Column(Integer, nullable=False, comment="消息发送者")
    room_id = Column(Integer, nullable=False, comment="会话ID")
    is_read = Column(TINYINT, nullable=False, default=0, comment="1：已读 0：未读")
    type = Column(String(20), nullable=False, default="text", comment="消息类型：img、text、template、system_quote_tip、system_payback_tip等")
    msg = Column(String(500), nullable=False, default="", comment="消息内容")
    template_message = Column(JSON, comment='模板消息 JSON 数据', nullable=False, default=dict)
    source = Column(TINYINT, nullable=False, default=SOURCE_DEFAULT, comment="0：未知 1：批发 2：采购")


class SMSRecord(MapBase, TimeBaseMixin):
    """短信发送记录"""

    __tablename__ = "sms_record"
    __table_args__ = (
        Index("ix_phone_create_at_send_type", "phone", "create_at", "send_type"),
    )

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    record_type = Column(
        Integer, nullable=False, default=1, comment="短信记录类型"
    )  # 1：聊天消息未读通知
    send_type = Column(
        Integer, nullable=False, default=1, comment="身份类型"
    )  # 1：批发商，2：采购商
    passport_id = Column(Integer, nullable=False, comment="接收方森果通行证号")
    phone = Column(String(32), nullable=False, comment="接收方手机号")
    # 记录实际发送记录条数(短信接口返回的实际消耗短信数量)(Re:余额变更短信直接设置成1-1条短信)
    fact_sms_count = Column(TINYINT, nullable=False, default=0)
    yunpian_sid = Column(BigInteger, nullable=False, default=0, comment="云片sid")
    record_status = Column(
        TINYINT, nullable=False, default=0, comment="发送状态"
    )  # 0:未发送 1:已发送  2: 发送中（群发过程中）3：发送失败
    customer_receive_status = Column(
        TINYINT, nullable=False, default=0, comment="客户接收状态"
    )  # 0 发送中 1发送成功 2发送失败
    remark = Column(String(100), nullable=False, default="", comment="备注")
