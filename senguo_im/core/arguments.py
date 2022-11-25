import typing

from webargs import ValidationError, fields
from webargs.tornadoparser import TornadoParser

from .utils import Emoji


class Parser(TornadoParser):
    DEFAULT_VALIDATION_STATUS = 400


parser = Parser()
use_args = parser.use_args
use_kwargs = parser.use_kwargs


class StrFilterEmoji(fields.String):
    """字符串-过滤emoji"""

    def _deserialize(self, value, attr, data, **kwargs):
        res = super(StrFilterEmoji, self)._deserialize(value, attr, data, **kwargs)

        return Emoji.filter_emoji(res)
