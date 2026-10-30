"""接口冒烟脚本（开发自测用，不属于业务代码）。

用法：
    # 终端 1：启动服务
    python -m uvicorn app.main:app --port 8000
    # 终端 2（在 backend 目录下，用同一个 venv）
    python scripts/smoke_api.py

设计要点：
- 只用标准库做 HTTP，不引额外依赖。
- 测试数据自建自清：临时用户/食堂/商家/菜品/帖子在结束时由 DB 兜底删除，
  所以可以反复跑，不会污染种子数据。
"""

import asyncio
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

# 允许直接 `python scripts/smoke_api.py` 运行（脚本目录不在包路径里）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, or_  # noqa: E402

from app.db.session import session_scope
from app.models.catalog import Canteen, Dish, Merchant
from app.models.post import Comment, Like, Post
from app.models.rating import Rating
from app.models.social import Follow, UserAchievement
from app.models.user import User

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"

# 1x1 透明 PNG
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

passed = 0
failed = 0

# 需要清理的临时数据
temp = {
    "users": set(),
    "canteens": set(),
    "merchants": set(),
    "dishes": set(),
    "posts": set(),
}


def call(method, path, payload=None, token=None, base=API):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{base}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body.decode("utf-8", "ignore")}


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  {detail}")


def login(username, password):
    status, body = call("POST", "/auth/login", {"username": username, "password": password})
    assert status == 200, body
    return body["data"]["access_token"]


def upload(token, filename, content):
    boundary = f"----smoke{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{API}/uploads/images",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


async def cleanup() -> None:
    """DB 兜底清理。外键顺序：likes/comments -> posts -> ratings -> 关联表 -> 主表。"""
    async with session_scope() as s:
        user_ids = temp["users"]
        post_ids = temp["posts"]
        dish_ids = temp["dishes"]

        await s.execute(delete(Like).where(or_(Like.user_id.in_(user_ids), Like.post_id.in_(post_ids))))
        await s.execute(
            delete(Comment).where(or_(Comment.user_id.in_(user_ids), Comment.post_id.in_(post_ids)))
        )
        await s.execute(delete(Post).where(or_(Post.user_id.in_(user_ids), Post.id.in_(post_ids))))
        await s.execute(delete(Rating).where(or_(Rating.user_id.in_(user_ids), Rating.dish_id.in_(dish_ids))))
        await s.execute(
            delete(Follow).where(or_(Follow.follower_id.in_(user_ids), Follow.following_id.in_(user_ids)))
        )
        await s.execute(delete(UserAchievement).where(UserAchievement.user_id.in_(user_ids)))
        await s.execute(delete(User).where(User.id.in_(user_ids)))
        await s.execute(delete(Dish).where(Dish.id.in_(dish_ids)))
        await s.execute(delete(Merchant).where(Merchant.id.in_(temp["merchants"])))
        await s.execute(delete(Canteen).where(Canteen.id.in_(temp["canteens"])))


def main():
    print("== 登录")
    admin = login("admin", "admin123")
    student = login("xiaoming", "123456")
    check("管理员登录", bool(admin))
    check("学生登录", bool(student))

    # 用户 id 不写死：种子表可能因重置而自增偏移，统一从 /users/me 取
    _, me = call("GET", "/users/me", token=student)
    student_id = me["data"]["id"]
    other = login("xiaohong", "123456")
    _, other_me = call("GET", "/users/me", token=other)
    other_id = other_me["data"]["id"]

    print("== 目录只读")
    status, body = call("GET", "/canteens")
    check("食堂列表 200", status == 200 and len(body["data"]) >= 2, body)
    canteen_id = body["data"][0]["id"]

    status, body = call("GET", f"/canteens/{canteen_id}/merchants")
    check("食堂下商家带综合评分", status == 200 and body["data"][0]["overall_rating"] > 0, body)
    merchant_id = body["data"][0]["id"]

    status, body = call("GET", f"/merchants/{merchant_id}")
    check("商家详情", status == 200 and "overall_rating" in body["data"], body)

    status, body = call("GET", f"/merchants/{merchant_id}/dishes")
    check("商家菜品列表", status == 200 and len(body["data"]) >= 1, body)
    dish_id = body["data"][0]["id"]

    status, body = call("GET", f"/dishes/{dish_id}/ratings?page=1&page_size=5")
    check("菜品打分分页", status == 200 and body["data"]["page_size"] == 5, body)

    status, _ = call("GET", "/canteens/99999/merchants")
    check("不存在的食堂 404", status == 404, status)

    print("== 权限隔离")
    status, body = call("GET", "/admin/canteens", token=student)
    check("学生访问管理端 403", status == 403 and body["code"] == 40301, body)
    status, _ = call("GET", "/admin/canteens")
    check("未登录访问管理端 401", status == 401, status)

    print("== 图片上传")
    status, body = call("POST", "/uploads/images", token=student)
    check("无文件 -> 40001", status == 400 and body["code"] == 40001, body)

    status, body = upload(student, "pic.png", PNG_1PX)
    check("上传 PNG 成功", status == 200 and body["data"]["url"].endswith(".png"), body)
    url = body["data"]["url"]
    with urllib.request.urlopen(f"{BASE}{url}") as resp:
        check("静态资源可访问", resp.status == 200 and resp.headers["Content-Type"] == "image/png")

    status, body = upload(student, "fake.jpg", b"this is not an image")
    check("伪造扩展名被拒", status == 400 and body["code"] == 40001, body)

    status, _ = upload(student, "note.txt", PNG_1PX)
    check("非白名单扩展名被拒", status == 400, status)

    print("== 管理端 CRUD（无帖子的链路，走 API 自删）")
    status, body = call("POST", "/admin/canteens", {"name": "冒烟测试食堂"}, token=admin)
    check("创建食堂", status == 200, body)
    tmp_canteen = body["data"]["id"]

    status, body = call("POST", "/admin/canteens", {"name": "冒烟测试食堂"}, token=admin)
    check("重名食堂 409", status == 409 and body["code"] == 40901, body)

    status, body = call("PUT", f"/admin/canteens/{tmp_canteen}", {"name": "冒烟测试食堂2"}, token=admin)
    check("改食堂名", status == 200 and body["data"]["name"] == "冒烟测试食堂2", body)

    status, body = call("POST", "/admin/merchants", {"name": "冒烟商家", "canteen_id": tmp_canteen}, token=admin)
    check("创建商家", status == 200, body)
    tmp_merchant = body["data"]["id"]

    status, _ = call("POST", "/admin/merchants", {"name": "孤儿商家", "canteen_id": 99999}, token=admin)
    check("商家挂不存在食堂 404", status == 404, status)

    status, body = call("DELETE", f"/admin/canteens/{tmp_canteen}", token=admin)
    check("有商家的食堂禁删 409", status == 409 and body["code"] == 40901, body)

    status, body = call(
        "POST", "/admin/dishes", {"name": "冒烟菜品", "merchant_id": tmp_merchant, "image_url": url}, token=admin
    )
    check("创建菜品", status == 200, body)
    tmp_dish = body["data"]["id"]

    status, _ = call("DELETE", f"/admin/merchants/{tmp_merchant}", token=admin)
    check("有菜品的商家禁删 409", status == 409, status)

    status, body = call("GET", f"/admin/dishes?merchant_id={tmp_merchant}", token=admin)
    check("管理端菜品列表分页", status == 200 and body["data"]["total"] == 1, body)

    status, body = call("PATCH", f"/admin/dishes/{tmp_dish}/availability", {"is_available": False}, token=admin)
    check("下架菜品", status == 200 and body["data"]["is_available"] is False, body)

    status, body = call("GET", f"/merchants/{tmp_merchant}/dishes")
    check("下架后公开列表不可见", status == 200 and body["data"] == [], body)

    status, _ = call("DELETE", f"/admin/dishes/{tmp_dish}", token=admin)
    check("未被引用菜品可删", status == 200, status)
    call("DELETE", f"/admin/merchants/{tmp_merchant}", token=admin)
    call("DELETE", f"/admin/canteens/{tmp_canteen}", token=admin)

    print("== 发帖链路（upsert 评分 / 聚合联动）")
    status, body = call("POST", "/admin/canteens", {"name": "冒烟帖子食堂"}, token=admin)
    p_canteen = body["data"]["id"]
    temp["canteens"].add(p_canteen)
    status, body = call("POST", "/admin/merchants", {"name": "冒烟帖子商家", "canteen_id": p_canteen}, token=admin)
    p_merchant = body["data"]["id"]
    temp["merchants"].add(p_merchant)

    p_dishes = []
    for name in ("冒烟菜A", "冒烟菜B", "冒烟菜C"):
        status, body = call("POST", "/admin/dishes", {"name": name, "merchant_id": p_merchant}, token=admin)
        p_dishes.append(body["data"]["id"])
        temp["dishes"].add(body["data"]["id"])

    # 新用户，专门用来验证称号解锁，不污染种子用户
    new_username = f"smoke_{uuid.uuid4().hex[:6]}"
    status, body = call(
        "POST", "/auth/register", {"username": new_username, "nickname": "冒烟用户", "password": "123456"}
    )
    check("注册新用户", status == 200, body)
    smoke_token = body["data"]["access_token"]
    smoke_uid = body["data"]["user"]["id"]
    temp["users"].add(smoke_uid)

    status, body = call(
        "POST", "/posts", {"dish_id": p_dishes[0], "score": 5, "content": "第一帖", "images": []}, token=smoke_token
    )
    check("发帖成功", status == 200 and body["data"]["author_score"] == 5, body)
    post_id = body["data"]["id"]
    temp["posts"].add(post_id)
    check("帖子带出商家与食堂", body["data"]["merchant"]["canteen_name"] == "冒烟帖子食堂", body)

    status, body = call("GET", f"/dishes/{p_dishes[0]}")
    check("发帖后菜品聚合=5/1", body["data"]["avg_rating"] == 5.0 and body["data"]["rating_count"] == 1, body)

    # 同一道菜再发一帖，评分改 3 —— 应该覆盖，而不是多一条评分
    status, body = call(
        "POST", "/posts", {"dish_id": p_dishes[0], "score": 3, "content": "第二帖", "images": []}, token=smoke_token
    )
    check("同菜二帖成功", status == 200, body)
    temp["posts"].add(body["data"]["id"])
    post2_id = body["data"]["id"]

    status, body = call("GET", f"/dishes/{p_dishes[0]}")
    check(
        "重复打分是覆盖不是新增",
        body["data"]["rating_count"] == 1 and body["data"]["avg_rating"] == 3.0,
        body,
    )

    status, body = call("GET", f"/posts/{post_id}")
    check("旧帖展示的是当前评分 3", body["data"]["author_score"] == 3, body)

    status, body = call("POST", "/posts", {"dish_id": 999999, "score": 5}, token=smoke_token)
    check("发帖到不存在菜品 404", status == 404, body)
    status, body = call("POST", "/posts", {"dish_id": p_dishes[0], "score": 6}, token=smoke_token)
    check("评分越界 40001", status == 400 and body["code"] == 40001, body)
    status, body = call(
        "POST", "/posts", {"dish_id": p_dishes[0], "score": 5, "images": ["javascript:alert(1)"]}, token=smoke_token
    )
    check("非法图片地址被拒", status == 400, body)

    status, body = call("PATCH", f"/admin/dishes/{p_dishes[2]}/availability", {"is_available": False}, token=admin)
    status, body = call("POST", "/posts", {"dish_id": p_dishes[2], "score": 5}, token=smoke_token)
    check("下架菜品不可发帖", status == 400 and "下架" in body["message"], body)
    call("PATCH", f"/admin/dishes/{p_dishes[2]}/availability", {"is_available": True}, token=admin)

    print("== 点赞 / 评论 / 信息流")
    status, body = call("POST", f"/posts/{post_id}/like", token=student)
    check("点赞", status == 200 and body["data"] == {"liked": True, "like_count": 1}, body)
    status, body = call("POST", f"/posts/{post_id}/like", token=student)
    check("再点取消", status == 200 and body["data"] == {"liked": False, "like_count": 0}, body)
    call("POST", f"/posts/{post_id}/like", token=student)

    status, body = call("POST", f"/posts/{post_id}/comments", {"content": "看起来不错"}, token=student)
    check("发评论", status == 200, body)
    status, body = call("GET", f"/posts/{post_id}/comments")
    check("评论列表", status == 200 and body["data"]["total"] == 1, body)
    status, body = call("POST", f"/posts/{post_id}/comments", {"content": "   "}, token=student)
    check("空评论被拒", status == 400, body)

    status, body = call("GET", f"/posts/{post_id}")
    check("评论数已累加", body["data"]["comment_count"] == 1, body)

    status, body = call("GET", "/posts/feed?sort=latest&page=1&page_size=3")
    check("feed latest 分页", status == 200 and body["data"]["page_size"] == 3, body)
    status, body = call("GET", "/posts/feed?sort=hot")
    check("feed hot 200", status == 200, body)
    status, body = call("GET", "/posts/hot")
    check("热榜返回 ≤10 条", status == 200 and len(body["data"]) <= 10, body)

    status, body = call("GET", f"/posts/feed?sort=latest&page=1&page_size=50", token=student)
    mine = [p for p in body["data"]["items"] if p["id"] == post_id]
    check("带 token 时返回 is_liked", bool(mine) and mine[0]["is_liked"] is True, mine[:1])

    status, body = call("GET", f"/merchants/{p_merchant}/posts")
    check("商家帖子流", status == 200 and body["data"]["total"] >= 2, body)
    status, body = call("GET", f"/dishes/{p_dishes[0]}/posts")
    check("菜品帖子流", status == 200 and body["data"]["total"] == 2, body)

    print("== 关注 / 互关")
    status, body = call("POST", f"/users/{other_id}/follow", token=smoke_token)
    check("关注成功", status == 200 and body["data"]["following"] is True, body)
    status, body = call("POST", f"/users/{other_id}/follow", token=smoke_token)
    check("再点取消关注", status == 200 and body["data"]["following"] is False, body)
    status, body = call("POST", f"/users/{smoke_uid}/follow", token=smoke_token)
    check("不能关注自己 400", status == 400, body)

    status, body = call("GET", f"/users/{student_id}/followers?page=1&page_size=5")
    first = body["data"]["items"][0] if status == 200 and body["data"]["items"] else {}
    check(
        "粉丝列表带 is_mutual / followed_by_me",
        status == 200 and "is_mutual" in first and "followed_by_me" in first,
        first,
    )
    status, body = call("GET", f"/users/{student_id}/following")
    check("关注列表可读", status == 200, body)

    print("== 称号与隐藏成就")
    # 三帖分别打三个同商家的菜 -> 满足纯爱战神（3 次 / 1 个商家）
    for dish in p_dishes[1:]:
        status, body = call("POST", "/posts", {"dish_id": dish, "score": 4}, token=smoke_token)
        temp["posts"].add(body["data"]["id"])
    status, body = call("POST", "/posts", {"dish_id": p_dishes[0], "score": 5, "content": "凑到 5 帖"}, token=smoke_token)
    temp["posts"].add(body["data"]["id"])

    status, body = call("GET", "/users/me", token=smoke_token)
    user = body["data"]
    check("发帖达 5 条升到 Lv.2", user["title_level"] == 2 and user["title_name"] == "碳水狂魔", user)
    codes = [a["code"] for a in user["achievements"]]
    check("解锁纯爱战神", "pure_love_warrior" in codes, user["achievements"])

    status, body = call("GET", f"/users/{smoke_uid}/ratings")
    check("我的评价列表", status == 200 and body["data"]["total"] == 3, body)

    print("== 管理端帖子列表")
    status, body = call("GET", "/admin/posts", token=student)
    check("学生访问管理端帖子列表 403", status == 403, body)
    status, body = call("GET", "/admin/posts?page=1&page_size=3", token=admin)
    check(
        "管理端帖子列表分页生效",
        status == 200 and body["data"]["page_size"] == 3 and len(body["data"]["items"]) <= 3,
        body["data"],
    )
    status, body = call("GET", "/admin/posts?keyword=" + urllib.parse.quote("凑到"), token=admin)
    hit = body["data"]["items"] if status == 200 else []
    check(
        "管理端列表可按内容搜",
        status == 200 and hit and all("凑到" in (p["content"] or "") for p in hit),
        hit[:1],
    )

    print("== 删帖权限")
    status, body = call("DELETE", f"/posts/{post_id}", token=student)
    check("删别人的帖子 403", status == 403, body)
    status, body = call("DELETE", f"/posts/{post_id}", token=smoke_token)
    check("删自己的帖子 200", status == 200, body)
    temp["posts"].discard(post_id)
    status, body = call("DELETE", f"/posts/{post2_id}", token=smoke_token)
    temp["posts"].discard(post2_id)

    status, body = call("GET", f"/admin/dishes?merchant_id={p_merchant}", token=admin)
    dish_a = next(d for d in body["data"]["items"] if d["id"] == p_dishes[0])
    check("删帖不影响评分（评分独立于帖子）", dish_a["rating_count"] == 1 and dish_a["avg_rating"] == 5.0, dish_a)

    print("== 清理临时数据")
    asyncio.run(cleanup())
    print("  done")

    print(f"\n通过 {passed} / {passed + failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
