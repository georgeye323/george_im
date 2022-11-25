from collections import namedtuple


class RoomConstants:
    class RoomType:
        SINGLE = 1
        GROUP = 2

    class Status:
        NORMAL = 1


class RoomMessageConstants:
    class IsRead:
        YES = 1
        NO = 0


PF_DB_NAME = "senguopf"


class DefaultObject:
    ACCOUNT_INFO = namedtuple(
        "account_info",
        [
            "id",
            "name",
            "headimgurl",
            "sex",
            "debt_rest",
            "remark",
            "nickname",
            "realname",
            "passport_id",
        ],
    )(0, "", "", 0, 0, "", "", "", 0)

    SHOP_INFO = namedtuple(
        "account_info",
        [
            "id",
            "boss_id",
            "shop_name",
            "shop_img",
            "shop_phone",
            "shop_address",
            "shop_province",
            "shop_city",
            "shop_county",
            "has_done",
            "merchant_name",
            "industry_type",
            "business_license",
            "realname",
            "nickname",
            "market_id",
        ],
    )(0, 0, "", "", "", "", "", "", "", -1, "", 0, "", "", "", 0)
