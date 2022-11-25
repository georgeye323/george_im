from enum import Enum
from typing import List


class DescribedEnum(Enum):
    """
    可描述的枚举类基建
    mark: int
        唯一标识
    desc: str
        描述信息
    """
    def __init__(self, mark: int, desc: str):
        self._mark = mark
        self._desc = desc

    @property
    def mark(self) -> int:
        return self._mark

    @property
    def desc(self) -> str:
        return self._desc

    @classmethod
    def get_all_marks(cls) -> List[int]:
        return [described_enum.mark for described_enum in cls]

    @classmethod
    def get_choices(cls):
        return ((described_enum.mark, described_enum.desc) for described_enum in cls)
