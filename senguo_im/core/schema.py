from marshmallow import Schema, fields, validate


class PageBaseDeserialize(Schema):
    """分页-入参"""

    page = fields.Integer(required=False, missing=0, description="页码")
    page_size = fields.Integer(required=False, missing=20, description="页容量")


class ShopBaseSerializer(Schema):
    """店铺-出参"""

    id = fields.Integer(data_key="shop_id", description="会话id")
    shop_name = fields.String(description="店铺名称")
    shop_img = fields.Function(
        lambda obj: obj.shop_img.split(",") if obj else "", description="店铺LOGO",
    )
    market_id = fields.Integer(data_key="shop_market_id", description="市场id")
    full_name = fields.String(description="市场全称")
    shorter_name = fields.String(description="市场简称")
    shop_phone = fields.String(description="店铺联系方式")
    wx_authorization_status = fields.Integer(comment="微信支付分授权状态 0：未授权 1：授权成功 2：取消授权")
    wx_authorization_code = fields.String(comment="预授权成功时的授权协议号")
    wx_openid = fields.String(comment="供货商超管微信openid")


class AccountBaseSerializer(Schema):
    """用户信息-出参"""

    id = fields.Integer(data_key="account_id", description="用户id")
    realname = fields.String(description="用户realname")
    nickname = fields.String(description="用户nickname")
    sex = fields.Integer(description="用户sex")
    headimgurl = fields.String(description="用户头像")
    passport_id = fields.Integer(description="森果通行证")
    wx_authorization_status = fields.Integer(comment="微信支付分授权状态 0：未授权 1：授权成功 2：取消授权")
    wx_authorization_code = fields.String(comment="预授权成功时的授权协议号")
    wx_openid = fields.String(comment="供货商超管微信openid")
    customer_id = fields.Integer(description="用户会员信息")


class MessageInfoSerializer(Schema):
    pf_url = fields.String(description="批发跳转URL")
    title = fields.String(description="消息头")
    msg = fields.String(missing="", description="消息body")
    cg_url = fields.String(description="采购跳转URL")


class RoomMessageBaseSerializer(Schema):
    """消息-出参"""

    id = fields.Integer(description="消息ID")
    msg_id = fields.String(description="前端生成的消息ID")
    passport_id = fields.Integer(description="消息发送者")
    room_id = fields.Integer(description="会话id")
    create_at = fields.DateTime(format="%Y-%m-%d %H:%M:%S", description="时间戳")
    is_read = fields.Integer(description="是否已读")
    msg = fields.String(description="消息内容")
    type = fields.String(description="消息类型:text、img、template等")
    account_info = fields.Nested(AccountBaseSerializer, description="发送者信息")
    template_message = fields.Nested(MessageInfoSerializer, description="模板消息内容")
