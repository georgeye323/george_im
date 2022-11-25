from typing import Iterable, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from senguo_im.chat.constant import PF_DB_NAME, RoomConstants, RoomMessageConstants
from senguo_im.chat.models import Room, RoomMember, RoomMessage, SMSRecord
from senguo_im.user.models import User


def create_room_single(session: Session, args: dict) -> Room:
    """创建会话-单聊"""
    members = args["members"]
    members.sort()
    if len(members) > 120:
        # 强制切片，成员数大于120的部分舍弃，暂时不会触发该场景，做预留
        members = members[0: 120]
    room_info = dict(
        members=str(members).replace(" ", ""),
        room_type=args["room_type"],
        accept_shop_id=args["accept_shop_id"],
        apply_passport_id=args["apply_passport_id"],
    )
    room = Room(**room_info)
    session.add(room)
    session.flush()

    return room


def create_room_member(session: Session, room_id: int, passport_id: int):
    """创建会话-成员"""

    room_member = RoomMember(room_id=room_id, passport_id=passport_id)
    session.add(room_member)
    session.flush()

    return room_member


def get_room_by_members_group(session: Session, args: dict) -> Room:
    """获取群聊会话"""

    result = (
        session.query(Room)
        .filter(
            Room.accept_shop_id == args["accept_shop_id"],
            Room.apply_passport_id == args["apply_passport_id"],
            Room.room_type == RoomConstants.RoomType.GROUP,
            Room.status == RoomConstants.Status.NORMAL,
        )
        .first()
    )

    return result


def list_room_by_passport_id(
    session: Session, passport_id: int, page: int, page_size: int, shop_id: int
) -> List[Room]:
    """
    获取正常会列表:
        shop_id存在，是批发易在查
        不存在，是采购在查
    """

    query_base = (
        session.query(Room)
        .join(RoomMember, Room.id == RoomMember.room_id)
        .filter(
            RoomMember.passport_id == passport_id,
            Room.status == RoomConstants.Status.NORMAL,
        )
    )
    if shop_id:
        query_base = query_base.filter(Room.accept_shop_id == shop_id,)
    else:
        query_base = query_base.filter(Room.apply_passport_id == passport_id,)
    if page != -1:
        query_base = query_base.offset(page * page_size).limit(page_size)
    result = query_base.all()

    return result


def get_room_by_id(session: Session, room_id: int,) -> Room:
    """获取正常会列表"""

    result = session.query(Room).filter(Room.id == room_id,).first()

    return result


def list_shop_by_ids(session: Session, shop_id_list: list):
    if not shop_id_list:
        return []
    query_sql = f"""
            SELECT
                shop.id,
                shop.shop_name,
                shop.shop_img,
                shop.market_id,
                sm.full_name,
                sm.shorter_name
            FROM
                {PF_DB_NAME}.shop shop
            JOIN {PF_DB_NAME}.shop_market sm ON sm.id = shop.market_id
            WHERE
                shop.id IN ({",".join(map(str, shop_id_list))})
        """
    shops = session.execute(query_sql).fetchall()

    return shops


def get_shop_by_id(session: Session, shop_id: int):
    query_sql = f"""
            SELECT
                shop.id,
                shop.shop_name,
                shop.shop_img,
                shop.market_id,
                shop.shop_phone,
                IFNULL(sm.full_name, ''),
                IFNULL(sm.shorter_name, ''),
                ai.passport_id
            FROM
                {PF_DB_NAME}.shop shop
            LEFT JOIN {PF_DB_NAME}.shop_market sm ON sm.id = shop.market_id
            LEFT JOIN {PF_DB_NAME}.account_info ai ON ai.id = shop.boss_id
            WHERE
                shop.id = {shop_id}
        """
    shop = session.execute(query_sql).fetchone()

    return shop


def list_account_by_passport_ids(session, apply_passport_id_list):
    if not apply_passport_id_list:
        return []
    sql = f"""
        SELECT 
            ai.id AS id,
            ai.nickname AS nickname,
            ai.realname AS realname,
            ai.sex AS sex,
            ai.headimgurl AS headimgurl,
            ai.passport_id AS passport_id
        FROM {PF_DB_NAME}.account_info ai
         WHERE ai.passport_id IN ({",".join(map(str, apply_passport_id_list))})
        """

    accounts = session.execute(sql).fetchall()

    return accounts


def get_customer_by_shop_id_and_user_id(session, shop_id, passport_id):

    sql = f"""
        SELECT 
            sc.id
        FROM
           {PF_DB_NAME}.shop_customer sc
           join {PF_DB_NAME}.account_info ai on ai.id = sc.account_id
        WHERE
            sc.shop_id = {shop_id} and ai.passport_id = {passport_id}
    """
    customer = session.execute(sql).first()
    return customer


def list_room_messsage_group_by_room_id(
    session: Session, room_id_list: list
) -> List[RoomMessage]:
    """通过聚合，取每个room最新一条消息"""
    rms = (
        session.query(func.max(RoomMessage.id).label("id"))
        .filter(RoomMessage.room_id.in_(room_id_list),)
        .group_by(RoomMessage.room_id)
        .all()
    )
    rm_ids = [rm.id for rm in rms]
    msg = session.query(RoomMessage).filter(RoomMessage.id.in_(rm_ids)).all()

    return msg


def list_room_messsage_by_room_id(
    session: Session, room_id: int, page: int, page_size: int, msg_id: str = ""
) -> List[RoomMessage]:
    """若传msg_id，则按消息id向后偏移取{page_size}条数据"""
    if msg_id:
        rm_id = session.query(RoomMessage.id).filter_by(msg_id=msg_id).scalar() or 0
        msg = (
            session.query(RoomMessage)
            .filter(RoomMessage.room_id == room_id, RoomMessage.id < rm_id)
            .order_by(RoomMessage.id.desc())
            .offset(0)
            .limit(page_size)
            .all()
        )
    else:
        msg = (
            session.query(RoomMessage)
            .filter(RoomMessage.room_id == room_id)
            .order_by(RoomMessage.id.desc())
            .offset(page * page_size)
            .limit(page_size)
            .all()
        )

    return msg


def update_room_messsage_by_msg_room_id(
    session: Session, room_id: int, msg_id: str, passport_id: int
):
    (
        session.query(RoomMessage)
        .filter(
            RoomMessage.room_id == room_id,
            RoomMessage.msg_id == msg_id,
            RoomMessage.passport_id != passport_id,
        )
        .update(
            {RoomMessage.is_read: RoomMessageConstants.IsRead.YES},
            synchronize_session=False,
        )
    )


def create_room_message(session: Session, data):
    room_message_dict = dict(
        msg_id=data["msg_id"],
        passport_id=data["passport_id"],
        room_id=data["room_id"],
        type=data["type"],
        msg=data["msg"],
        template_message=data.get("template_message") if data.get("template_message") else None,
        source=data.get("source", 0)
    )
    room_message = RoomMessage(**room_message_dict)
    session.add(room_message)
    session.flush()


def list_room_message_unread_by_room_id(
    session: Session, room_id_list: list, passport_id: int
) -> dict:
    """通过聚合，取每个room未读消息数量"""
    rms = (
        session.query(RoomMessage.room_id, func.count(RoomMessage.id).label("count"))
        .filter(
            RoomMessage.room_id.in_(room_id_list),
            RoomMessage.is_read == RoomMessageConstants.IsRead.NO,
            RoomMessage.passport_id != passport_id,
        )
        .group_by(RoomMessage.room_id)
        .all()
    )

    return {i.room_id: i.count for i in rms}


def get_room_messsage_unread_by_room_ids(
    session: Session, room_id_list: list, passport_id: int
) -> int:
    """未读消息数"""
    count = (
        session.query(RoomMessage.room_id)
        .filter(
            RoomMessage.room_id.in_(room_id_list),
            RoomMessage.is_read == RoomMessageConstants.IsRead.NO,
            RoomMessage.passport_id != passport_id,
        )
        .count()
    )

    return count


def update_all_read_message(
    session: Session, passport_id: int, shop_id: int
):
    """一键已读"""
    room_messages = (
        session.query(RoomMessage)
        .join(Room, Room.id == RoomMessage.room_id)
        .join(RoomMember, RoomMember.room_id == Room.id)
        .filter(
            RoomMember.passport_id == passport_id,
            Room.status == 1,
            Room.accept_shop_id == shop_id,
            RoomMember.status == 1,
            RoomMessage.passport_id != passport_id,
        )
        .all()
    )
    room_message_ids = [rm.id for rm in room_messages]
    (
        session.query(RoomMessage)
        .filter(RoomMessage.id.in_(room_message_ids))
        .update(
            {RoomMessage.is_read: RoomMessageConstants.IsRead.YES},
            synchronize_session=False,
        )
    )

    session.flush()


def list_room_message_by_unread(session: Session, from_date, to_date) -> Iterable[Room]:
    """获取未读消息"""

    rooms = (
        session.query(
            Room,
            func.group_concat(RoomMessage.passport_id.distinct()).label("passport_ids"),
        )
        .join(Room, Room.id == RoomMessage.room_id)
        .filter(
            RoomMessage.create_at >= from_date,
            RoomMessage.create_at <= to_date,
            RoomMessage.is_read == RoomMessageConstants.IsRead.NO,
        )
        .group_by(RoomMessage.room_id)
        .all()
    )
    result = []
    for room, passport_ids in rooms:
        passport_ids = (
            list(map(int, passport_ids.split(",")))
            if passport_ids
            else []
        )
        # passport_ids = list(set(passport_ids))
        setattr(room, "passport_ids", passport_ids)
        result.append(room)

    return result


def list_sms_record_by_phone_type(
    session: Session, phones, from_date, to_date, send_type
) -> Iterable[SMSRecord]:
    """短信发送记录"""
    if not phones:
        return []

    result = (
        session.query(SMSRecord)
        .filter(
            SMSRecord.phone.in_(phones),
            SMSRecord.create_at >= from_date,
            SMSRecord.create_at < to_date,
            SMSRecord.send_type == send_type,
        )
        .all()
    )

    return result


def create_sms_record(session: Session, data) -> SMSRecord:

    sms_record = SMSRecord(**data)
    session.add(sms_record)
    session.flush()
    return sms_record


def get_member_list_by_room_id(session, room_id):
    result = (
        session.query(RoomMember).filter(
            RoomMember.room_id == room_id,
            RoomMember.status == 1,
        ).all()
    )
    return result


def update_room_member(session, room_id, del_members):
    (
        session.query(RoomMember)
        .filter(
            RoomMember.room_id == room_id,
            RoomMember.passport_id.in_(del_members)
        )
        .update(
            {RoomMember.status: 0},
            synchronize_session=False,
        )
    )
    session.flush()
