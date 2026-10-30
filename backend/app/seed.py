"""冷启动种子数据。

用法：
    python -m app.seed            # 幂等：已存在就跳过，可重复执行
    python -m app.seed --reset    # 先清空业务表再重建（不动表结构）

内容：2 个食堂 / 6 个商家 / 20 个菜品 / 9 个用户（1 管理员 + 8 学生）
     + 一批评分、帖子、点赞、评论、关注，让首页和热榜一打开就有梯度。
数据全部写死、不用随机数，方便对着截图复现问题。
"""

import argparse
import asyncio
import hashlib
import sys

from sqlalchemy import func, select, text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import session_scope
from app.models.catalog import Canteen, Dish, Merchant
from app.models.post import Comment, Like, Post
from app.models.rating import Rating
from app.models.social import Follow
from app.models.user import User

# ---------------------------------------------------------------- 封面图

# 菜品名关键词 -> 食物 emoji。没有真实照片时用它生成占位封面，
# 比空白方块或首字母更像个正经产品；接入真实图片后把 image_url 换掉即可。
EMOJI_RULES: list[tuple[str, str]] = [
    ("麻辣烫", "🌶️"),
    ("拉面", "🍜"),
    ("面片", "🍜"),
    ("拌面", "🍜"),
    ("卤肉饭", "🍚"),
    ("鸡腿饭", "🍗"),
    ("红烧肉饭", "🍖"),
    ("宫保鸡丁", "🍗"),
    ("辣子鸡", "🌶️"),
    ("鱼香肉丝", "🥘"),
    ("蒸饺", "🥟"),
    ("扁肉", "🥟"),
    ("炖罐", "🍲"),
    ("沙拉", "🥗"),
    ("三明治", "🥪"),
    ("溏心蛋", "🥚"),
    ("牛肉", "🥩"),
]

# 暖色系配对，按名字哈希轮换，保证同一道菜每次生成的颜色一致
COVER_COLORS: list[tuple[str, str]] = [
    ("#ffd9c2", "#ffb385"),
    ("#ffe7bd", "#ffc46b"),
    ("#ffd2d2", "#ff9a9a"),
    ("#e6f0d4", "#c0dc93"),
    ("#d9ecf7", "#a6d3ec"),
    ("#f0e0f7", "#d3b3e8"),
]


def emoji_of(name: str) -> str:
    for keyword, emoji in EMOJI_RULES:
        if keyword in name:
            return emoji
    return "🍽️"


def cover_svg(name: str) -> str:
    digest = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
    c1, c2 = COVER_COLORS[digest % len(COVER_COLORS)]
    emoji = emoji_of(name)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="100%" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#g)"/>
  <circle cx="336" cy="34" r="72" fill="#ffffff" opacity="0.22"/>
  <circle cx="52" cy="276" r="86" fill="#ffffff" opacity="0.16"/>
  <text x="200" y="182" font-size="120" text-anchor="middle"
        font-family="Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji, sans-serif">{emoji}</text>
</svg>
"""


def ensure_cover(name: str) -> str:
    """把封面写到 uploads/seed/ 下并返回可访问 URL。已存在就复用，保证幂等。"""
    slug = hashlib.md5(name.encode("utf-8")).hexdigest()[:12]
    target = settings.upload_path / "seed" / f"{slug}.svg"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(cover_svg(name), encoding="utf-8")
    return f"/uploads/seed/{slug}.svg"


# ---------------------------------------------------------------- 静态数据

USERS = [
    # username, nickname, password, is_admin
    ("admin", "食堂管理员", "admin123", True),
    ("xiaoming", "小明爱吃肉", "123456", False),
    ("xiaohong", "红红不吃香菜", "123456", False),
    ("lanzhou_only", "拉面忠粉", "123456", False),
    ("wangshuai", "王子不吃早饭", "123456", False),
    ("lili", "莉莉周", "123456", False),
    ("laozhang", "老张的胃", "123456", False),
    ("ada", "阿达", "123456", False),
    ("kiki", "Kiki", "123456", False),
]

STUDENTS = [u[0] for u in USERS if not u[3]]

# 食堂 -> 商家 -> 菜品
CATALOG: dict[str, list[tuple[str, list[str]]]] = {
    "一食堂": [
        ("王记麻辣烫", ["麻辣烫（微辣）", "番茄麻辣烫", "麻酱麻辣烫"]),
        ("兰州拉面", ["牛肉拉面", "炒面片", "凉拌牛肉"]),
        ("阿姨卤肉饭", ["招牌卤肉饭", "鸡腿饭", "红烧肉饭", "溏心蛋"]),
    ],
    "二食堂": [
        ("川湘小炒", ["宫保鸡丁", "鱼香肉丝", "辣子鸡"]),
        ("沙县小吃", ["蒸饺", "拌面", "炖罐", "扁肉"]),
        ("轻食沙拉", ["鸡胸沙拉", "牛油果沙拉", "三明治"]),
    ],
}

# 评分：谁 -> 哪道菜 -> 几分
RATINGS = [
    ("xiaoming", "麻辣烫（微辣）", 5),
    ("xiaoming", "牛肉拉面", 4),
    ("xiaoming", "招牌卤肉饭", 5),
    ("xiaoming", "宫保鸡丁", 4),
    ("xiaohong", "麻辣烫（微辣）", 4),
    ("xiaohong", "蒸饺", 3),
    ("xiaohong", "鸡胸沙拉", 5),
    ("xiaohong", "番茄麻辣烫", 4),
    ("lanzhou_only", "牛肉拉面", 5),
    ("lanzhou_only", "炒面片", 5),
    ("lanzhou_only", "凉拌牛肉", 4),
    ("wangshuai", "牛肉拉面", 5),
    ("wangshuai", "鸡腿饭", 4),
    ("lili", "鸡胸沙拉", 4),
    ("lili", "三明治", 3),
    ("laozhang", "招牌卤肉饭", 4),
    ("ada", "麻辣烫（微辣）", 5),
    ("kiki", "炖罐", 4),
]

# 帖子：(作者, 菜品, 文案, 目标点赞数)
# 点赞数受用户总数限制（不能自己赞自己），最多 8；数值都落在可达范围内
POSTS = [
    ("xiaoming", "麻辣烫（微辣）", "阿姨手一抖，牛百叶给得比肉还多，这波血赚。就是微辣对湖南人来说真的只是微辣。", 8),
    ("xiaoming", "招牌卤肉饭", "肥瘦比例刚好，卤汁拌饭能干三碗。缺点是十一点半之后要排队十分钟。", 6),
    ("xiaoming", "宫保鸡丁", "花生是脆的！很多地方的花生都是软的，这家居然现炸。", 5),
    ("xiaohong", "鸡胸沙拉", "减脂期救命餐，酱料记得单独要，不然热量白算。", 7),
    ("xiaohong", "蒸饺", "皮有点厚，馅还行，八块钱一笼不亏。", 2),
    ("xiaohong", "麻辣烫（微辣）", "和小明说的完全不一致……我觉得微辣已经很辣了，慎重。", 4),
    ("lanzhou_only", "牛肉拉面", "汤头是清的，萝卜片给得实在。加个蛋人生圆满。", 7),
    ("lanzhou_only", "炒面片", "面片厚薄不太均匀，但锅气足，锅边那圈焦的最香。", 3),
]

# (评论者, 被评帖子的作者, 菜品, 内容)
COMMENTS = [
    ("xiaohong", "xiaoming", "麻辣烫（微辣）", "湖南人不要说微辣，谢谢。"),
    ("wangshuai", "xiaoming", "麻辣烫（微辣）", "上周去也是这个味，出品挺稳。"),
    ("xiaoming", "xiaohong", "麻辣烫（微辣）", "广东室友已经阵亡了。"),
    ("xiaoming", "lanzhou_only", "牛肉拉面", "加蛋 +1，再来勺辣油。"),
]

# 关注关系：(关注人, 被关注人)。xiaoming <-> lanzhou_only 构成互关
FOLLOWS = [
    ("xiaoming", "lanzhou_only"),
    ("xiaohong", "lanzhou_only"),
    ("wangshuai", "lanzhou_only"),
    ("lanzhou_only", "xiaoming"),
    ("lili", "xiaoming"),
    ("laozhang", "xiaohong"),
]


async def reset_tables() -> None:
    """按外键倒序清空业务表。TRUNCATE 会被外键挡住，这里用 DELETE。"""
    async with session_scope() as session:
        for table in (
            "likes",
            "comments",
            "posts",
            "ratings",
            "follows",
            "user_achievements",
            "dishes",
            "merchants",
            "canteens",
            "users",
        ):
            await session.execute(text(f"DELETE FROM {table}"))
        print("已清空业务表")


async def seed() -> None:
    async with session_scope() as session:
        # ---- 用户 ----
        users: dict[str, User] = {}
        for username, nickname, password, is_admin in USERS:
            user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if user is None:
                user = User(
                    username=username,
                    nickname=nickname,
                    password_hash=hash_password(password),
                    is_admin=is_admin,
                )
                session.add(user)
                await session.flush()
            users[username] = user

        # ---- 食堂 / 商家 / 菜品 ----
        dish_by_name: dict[str, Dish] = {}
        for canteen_name, merchants in CATALOG.items():
            canteen = (
                await session.execute(select(Canteen).where(Canteen.name == canteen_name))
            ).scalar_one_or_none()
            if canteen is None:
                canteen = Canteen(name=canteen_name)
                session.add(canteen)
                await session.flush()

            for merchant_name, dish_names in merchants:
                merchant = (
                    await session.execute(
                        select(Merchant).where(Merchant.name == merchant_name, Merchant.canteen_id == canteen.id)
                    )
                ).scalar_one_or_none()
                if merchant is None:
                    merchant = Merchant(name=merchant_name, canteen_id=canteen.id)
                    session.add(merchant)
                    await session.flush()

                for dish_name in dish_names:
                    dish = (
                        await session.execute(
                            select(Dish).where(Dish.name == dish_name, Dish.merchant_id == merchant.id)
                        )
                    ).scalar_one_or_none()
                    if dish is None:
                        dish = Dish(name=dish_name, merchant_id=merchant.id)
                        session.add(dish)
                        await session.flush()
                    if not dish.image_url:
                        dish.image_url = ensure_cover(dish_name)
                    dish_by_name[dish_name] = dish

        # ---- 评分（一人一菜一条）----
        for username, dish_name, score in RATINGS:
            user, dish = users[username], dish_by_name[dish_name]
            exists = (
                await session.execute(select(Rating).where(Rating.user_id == user.id, Rating.dish_id == dish.id))
            ).scalar_one_or_none()
            if exists is None:
                session.add(Rating(user_id=user.id, dish_id=dish.id, score=score))
        await session.flush()

        # ---- 关注 ----
        for follower, following in FOLLOWS:
            pair_exists = (
                await session.execute(
                    select(Follow).where(
                        Follow.follower_id == users[follower].id,
                        Follow.following_id == users[following].id,
                    )
                )
            ).scalar_one_or_none()
            if pair_exists is None:
                session.add(Follow(follower_id=users[follower].id, following_id=users[following].id))
        await session.flush()

        # ---- 帖子 / 评论 / 点赞 ----
        post_count = await session.scalar(select(func.count()).select_from(Post))
        if not post_count:
            created_posts: dict[tuple[str, str], Post] = {}
            for username, dish_name, content, _target in POSTS:
                user, dish = users[username], dish_by_name[dish_name]
                # 没有真实照片时，帖子引用菜品封面，首页信息流才不是一片空白
                images = [dish.image_url] if dish.image_url else []
                post = Post(user_id=user.id, dish_id=dish.id, content=content, images=images)
                session.add(post)
                await session.flush()
                created_posts[(username, dish_name)] = post

            # 点赞明细决定 like_count，避免出现"数字 20、列表 3 条"的假数据
            for (author, dish_name), post in created_posts.items():
                target = next(t for a, d, _c, t in POSTS if (a, d) == (author, dish_name))
                candidates = [u for u in STUDENTS if u != author][:target]
                for liker in candidates:
                    session.add(Like(user_id=users[liker].id, post_id=post.id))
                post.like_count = len(candidates)

            for commenter, post_author, dish_name, content in COMMENTS:
                target_post = created_posts.get((post_author, dish_name))
                if target_post is None:
                    continue
                session.add(Comment(post_id=target_post.id, user_id=users[commenter].id, content=content))
                target_post.comment_count += 1

        await session.flush()

        # ---- 重算聚合（与 service 层同一口径）----
        await session.execute(
            text(
                """
                UPDATE dishes d SET
                    avg_rating = COALESCE((SELECT ROUND(AVG(r.score), 2) FROM ratings r WHERE r.dish_id = d.id), 0),
                    rating_count = (SELECT COUNT(*) FROM ratings r WHERE r.dish_id = d.id)
                """
            )
        )
        await session.execute(
            text(
                """
                UPDATE users u SET
                    follower_count  = (SELECT COUNT(*) FROM follows f WHERE f.following_id = u.id),
                    following_count = (SELECT COUNT(*) FROM follows f WHERE f.follower_id  = u.id)
                """
            )
        )

    # ---- 汇总 ----
    async with session_scope() as session:
        counts = {}
        for label, model in (
            ("用户", User),
            ("食堂", Canteen),
            ("商家", Merchant),
            ("菜品", Dish),
            ("评分", Rating),
            ("帖子", Post),
        ):
            counts[label] = await session.scalar(select(func.count()).select_from(model))
    print("种子数据完成：" + " / ".join(f"{k} {v}" for k, v in counts.items()))
    print("管理员 admin / admin123；学生 xiaoming、xiaohong、lanzhou_only 等 8 人 / 123456")
    print(f"数据库：{settings.DATABASE_URL.split('@')[-1]}")


async def main(reset: bool) -> None:
    if reset:
        await reset_tables()
    await seed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="校园食光种子数据")
    parser.add_argument("--reset", action="store_true", help="先清空业务表再写入")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.reset))
    except Exception as exc:  # noqa: BLE001
        print(f"种子数据失败: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
