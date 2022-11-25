import re


class Emoji:
    """ Emoji表情 """

    @staticmethod
    def filter_emoji(keyword):
        keyword = re.compile("[\U00010000-\U0010ffff]").sub("", keyword)
        return keyword

    @staticmethod
    def check_emoji(keyword):
        reg_emoji = re.compile("[\U00010000-\U0010ffff]")
        has_emoji = re.search(reg_emoji, keyword)
        if has_emoji:
            return True
        else:
            return False
