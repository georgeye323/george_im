from marshmallow import Schema, fields, validate


class UserLoginDeserialize(Schema):
    """登录-入参"""

    sign = fields.String(required=True, description="加密森果通行证")
    passport_id = fields.Integer(required=True, description="森果通行证")
    shop_id = fields.Integer(required=False, missing=0)
