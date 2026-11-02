"""菜品的口味 / 形态标签。

为什么要有白名单而不是让用户自由打标签：
MVP 不做审核，开放标签立刻会出现「辣」「微辣」「中辣」「有点辣」四种写法，
最终搜「辣」搜不全。这里定一套固定词表，管理端只能选不能填。

存的是**中文名本身**（不是 key）：标签就是短中文词，没有改名需求，
直接存省掉一层映射；搜索时按数组元素精确匹配，不会像 LIKE '%辣%' 那样
把「不辣」也算进去。

新增标签只改这个文件 + 前端的多选，不用动表结构。
"""

from __future__ import annotations

from typing import Final

# 顺序即前端多选的展示顺序：先口味（用户最常按这个挑），再形态，最后时段
DISH_TAGS: Final[list[dict[str, str]]] = [
    {"name": "辣", "emoji": "🌶️", "group": "口味"},
    {"name": "清淡", "emoji": "🥗", "group": "口味"},
    {"name": "重口", "emoji": "🧄", "group": "口味"},
    {"name": "甜", "emoji": "🍬", "group": "口味"},
    {"name": "米饭", "emoji": "🍚", "group": "形态"},
    {"name": "面食", "emoji": "🍜", "group": "形态"},
    {"name": "粉", "emoji": "🍲", "group": "形态"},
    {"name": "汤", "emoji": "🥣", "group": "形态"},
    {"name": "饺子", "emoji": "🥟", "group": "形态"},
    {"name": "烧烤", "emoji": "🍢", "group": "形态"},
    {"name": "小吃", "emoji": "🍡", "group": "形态"},
    {"name": "早饭", "emoji": "🌅", "group": "时段"},
]

TAG_NAMES: Final[frozenset[str]] = frozenset(item["name"] for item in DISH_TAGS)
# 一道菜最多挂几个：多了筛选就失去区分度（全是标签等于没有标签）
MAX_TAGS_PER_DISH: Final[int] = 4


def clean_tags(tags: list[str] | None) -> list[str]:
    """去空白、去重、保序，校验全部在白名单内且不超上限。

    非法时抛 ValueError，由 pydantic 转成 400（项目统一走这套，不在这里造 HTTP 异常）。
    """
    if not tags:
        return []
    result: list[str] = []
    for raw in tags:
        name = (raw or "").strip()
        if not name:
            continue
        if name not in TAG_NAMES:
            raise ValueError(f"不支持的标签：{name}")
        if name not in result:
            result.append(name)
    if len(result) > MAX_TAGS_PER_DISH:
        raise ValueError(f"一道菜最多 {MAX_TAGS_PER_DISH} 个标签")
    return result
