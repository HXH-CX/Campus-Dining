"""称号与隐藏成就的展示映射。

数据库只存 level / code，中文名与 emoji 全部在这里，改文案不用改数据。
"""

from typing import TypedDict


class TitleInfo(TypedDict):
    level: int
    name: str
    emoji: str


TITLE_MAP: dict[int, TitleInfo] = {
    1: {"level": 1, "name": "干饭练习生", "emoji": "🍚"},
    2: {"level": 2, "name": "碳水狂魔", "emoji": "🍜"},
    3: {"level": 3, "name": "食堂扫地僧", "emoji": "🍗"},
    4: {"level": 4, "name": "绝地干饭王", "emoji": "🍱"},
    5: {"level": 5, "name": "食堂话事人", "emoji": "👑"},
}

MAX_TITLE_LEVEL = max(TITLE_MAP)

# 隐藏成就：code -> 展示信息
ACHIEVEMENT_MAP: dict[str, dict[str, str]] = {
    "pure_love_warrior": {
        "name": "纯爱战神",
        "emoji": "🥦",
        "description": "近 30 天只给同一个商家的菜打分",
    },
}


def title_of(level: int) -> TitleInfo:
    """越界或脏数据统一兜底到 Lv.1，避免接口报错。"""
    return TITLE_MAP.get(level, TITLE_MAP[1])


def achievement_of(code: str) -> dict[str, str]:
    return ACHIEVEMENT_MAP.get(code, {"name": code, "emoji": "🏅", "description": ""})


def level_by_contribution(post_count: int, like_count: int) -> int:
    """从 Lv.MAX 向下匹配，命中即停。只返回算出来的等级，是否降级由调用方决定。

    条件与 PRD 2.4 一一对应：
        Lv.5 发帖>=100 且 获赞>=2000   （唯一"且"）
        Lv.4 发帖>=50  或 获赞>=500
        Lv.3 发帖>=20  或 获赞>=100
        Lv.2 发帖>=5   或 获赞>=20
    """
    if post_count >= 100 and like_count >= 2000:
        return 5
    if post_count >= 50 or like_count >= 500:
        return 4
    if post_count >= 20 or like_count >= 100:
        return 3
    if post_count >= 5 or like_count >= 20:
        return 2
    return 1
