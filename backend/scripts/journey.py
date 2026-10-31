"""用户旅程脚本：按前端的真实调用顺序走一遍，校验"前端要的字段后端都有"。

与 smoke_api.py 的区别：
- smoke 关注"业务逻辑对不对"（权限、聚合、称号）；
- journey 关注"契约对不对"（字段名、类型、嵌套结构），因为前端是照着它渲染的。

设计：只用种子数据里已有的帖子/评分，跑完把自己造的帖子删掉，不改任何聚合值。
"""

import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = "http://127.0.0.1:8000"

PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

passed = 0
failed = 0


def call(method, path, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE}/api/v1{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body)
        except json.JSONDecodeError:
            return exc.code, {"raw": body.decode("utf-8", "ignore")}


def upload(token, filename, content):
    boundary = f"----journey{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE}/api/v1/uploads/images",
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


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}  {str(detail)[:400]}")


def need(name, obj, keys):
    """断言对象具备前端渲染需要的字段。"""
    if not isinstance(obj, dict):
        check(name, False, obj)
        return
    missing = [k for k in keys if k not in obj]
    check(name, not missing, f"缺少字段 {missing}；实际 {list(obj)}" if missing else "")


def main():
    print("== 1. 首页：食堂 -> 商家 -> 菜品 三级导航")
    status, body = call("GET", "/canteens")
    check("食堂列表", status == 200 and body["data"], body)
    need("食堂字段", body["data"][0], ["id", "name", "merchant_count"])
    canteen_id = body["data"][0]["id"]

    status, body = call("GET", f"/canteens/{canteen_id}/merchants")
    check("商家列表", status == 200 and body["data"], body)
    need("商家字段", body["data"][0], ["id", "name", "canteen_id", "canteen_name", "overall_rating", "dish_count"])
    merchant_id = body["data"][0]["id"]

    status, body = call("GET", f"/merchants/{merchant_id}/dishes")
    check("菜品列表", status == 200 and body["data"], body)
    need(
        "菜品字段",
        body["data"][0],
        ["id", "name", "image_url", "merchant_id", "merchant_name", "canteen_name", "avg_rating", "rating_count", "is_available"],
    )
    dish = body["data"][0]
    dish_id = dish["id"]
    avg_before = dish["avg_rating"]
    count_before = dish["rating_count"]

    print("== 1.1 高分榜")
    status, body = call("GET", "/dishes/top?min_rating=4&min_count=2&limit=6")
    check("高分榜 200", status == 200, body)
    board = body["data"]
    check("榜单非空", len(board) > 0, board)
    if board:
        need(
            "榜单项字段（卡片要用）",
            board[0],
            ["id", "name", "image_url", "merchant_name", "canteen_name", "avg_rating", "rating_count"],
        )
        check(
            "每一项都过双重门槛",
            all(item["rating_count"] >= 2 and item["avg_rating"] >= 4 for item in board),
            [(i["name"], i["avg_rating"], i["rating_count"]) for i in board],
        )
        check(
            "按均分倒序",
            all(board[i]["avg_rating"] >= board[i + 1]["avg_rating"] for i in range(len(board) - 1)),
            [i["avg_rating"] for i in board],
        )
    status, body = call("GET", "/dishes/top?min_count=99")
    check("门槛过高返回空数组而不是报错", status == 200 and body["data"] == [], body)

    print("== 1.2 随机一顿（今天吃什么）")
    status, body = call("GET", "/dishes/random")
    check("随机抽取 200", status == 200, body)
    need("随机结果字段", body["data"], ["dish", "pool_size", "from_top"])
    pick = body["data"]
    need(
        "随机菜品字段（弹窗要用）",
        pick["dish"],
        ["id", "name", "image_url", "merchant_name", "canteen_name", "avg_rating", "rating_count"],
    )
    check(
        "默认从高分池里抽",
        pick["from_top"] is True and pick["pool_size"] >= 1 and pick["dish"]["rating_count"] >= 2,
        pick,
    )

    status, body = call("GET", f"/dishes/random?exclude_id={pick['dish']['id']}")
    check(
        "「换一个」不会原地重复",
        status == 200 and body["data"]["dish"]["id"] != pick["dish"]["id"],
        body["data"],
    )

    status, body = call("GET", "/dishes/random?min_count=99")
    check(
        "高分池空时回退到全部在售菜品",
        status == 200 and body["data"]["from_top"] is False and body["data"]["pool_size"] >= 2,
        body,
    )

    status, body = call("GET", "/dishes/random?exclude_id=0")
    check("非法 exclude_id 被拒", status == 400, body)

    print("== 2. 登录")
    status, body = call("POST", "/auth/login", {"username": "xiaoming", "password": "123456"})
    check("学生登录", status == 200, body)
    token = body["data"]["access_token"]
    need("登录返回用户", body["data"]["user"], ["id", "nickname", "title_level", "title_name", "title_emoji", "achievements"])

    print("== 3. 发帖（带图片上传）")
    status, body = upload(token, "journey.png", PNG_1PX)
    check("上传图片", status == 200 and body["data"]["url"], body)
    image_url = body["data"]["url"]

    # 用作者已有评分（5 星）覆盖，保证菜品聚合不变，跑完不留痕迹
    detail = call("GET", f"/dishes/{dish_id}")[1]["data"]
    status, body = call(
        "POST",
        "/posts",
        {"dish_id": dish_id, "score": 5, "content": "旅程脚本发的帖子，稍后会删掉", "images": [image_url]},
        token=token,
    )
    check("发帖", status == 200, body)
    post = body["data"]
    post_id = post["id"]
    need(
        "帖子字段（PostCard 需要）",
        post,
        ["id", "content", "images", "like_count", "comment_count", "created_at", "author", "dish", "merchant", "author_score", "is_liked"],
    )
    need("帖子作者字段", post["author"], ["id", "nickname", "avatar_url", "title_level", "title_name", "title_emoji"])
    need("帖子菜品字段", post["dish"], ["id", "name", "image_url", "avg_rating", "rating_count"])
    need("帖子商家字段", post["merchant"], ["id", "name", "canteen_name"])
    check("图片回显", post["images"] == [image_url], post["images"])

    status, body = call("GET", f"/dishes/{dish_id}")
    check(
        "聚合未被污染（评分覆盖）",
        body["data"]["avg_rating"] == avg_before and body["data"]["rating_count"] == count_before,
        body["data"],
    )

    print("== 4. 信息流 / 热榜")
    status, body = call("GET", "/posts/feed?sort=latest&page=1&page_size=3", token=token)
    check("feed 分页字段", status == 200 and {"items", "total", "page", "page_size"} <= set(body["data"]), body)
    first = body["data"]["items"][0]
    need("feed 项字段", first, ["id", "author", "dish", "merchant", "like_count", "comment_count", "is_liked"])

    status, body = call("GET", "/posts/hot")
    check("热榜", status == 200 and isinstance(body["data"], list), body)
    if body["data"]:
        need("热榜项字段", body["data"][0], ["id", "dish", "author", "like_count"])

    print("== 5. 点赞 / 评论")
    status, body = call("POST", f"/posts/{post_id}/like", token=token)
    check("点赞返回结构", status == 200 and set(body["data"]) == {"liked", "like_count"}, body)
    call("POST", f"/posts/{post_id}/like", token=token)  # 取消，回到初始状态

    status, body = call("POST", f"/posts/{post_id}/comments", {"content": "旅程脚本的评论"}, token=token)
    check("发评论", status == 200, body)
    need("评论字段", body["data"], ["id", "content", "created_at", "author"])

    status, body = call("GET", f"/posts/{post_id}/comments?page=1&page_size=20")
    check("评论列表分页", status == 200 and body["data"]["total"] >= 1, body)
    need("评论项字段", body["data"]["items"][0], ["id", "content", "created_at", "author"])

    print("== 5.1 编辑帖子（只改文案与配图）")
    new_text = "改过的文案：还行，就是有点咸"
    status, body = call("PUT", f"/posts/{post_id}", {"content": new_text}, token=token)
    check("编辑自己的帖子", status == 200, body)
    edited = body["data"]
    check("文案已更新", edited["content"] == new_text, edited.get("content"))
    check("只传 content 时配图不被清空", edited["images"] == post["images"], edited.get("images"))
    check("评分不受编辑影响", edited["author_score"] == post["author_score"], edited.get("author_score"))

    status, body = call("GET", f"/posts/{post_id}")
    check("详情读到新文案", status == 200 and body["data"]["content"] == new_text, body)

    # 只传 images：content 应保持原样（靠 model_fields_set 区分"没传"和"传 null"）
    status, body = call("PUT", f"/posts/{post_id}", {"images": []}, token=token)
    check("仅传 images 不动文案", status == 200 and body["data"]["content"] == new_text, body.get("data"))
    check("配图已清空", body["data"]["images"] == [], body.get("data"))

    status, body = call("POST", "/auth/login", {"username": "xiaohong", "password": "123456"})
    other_token = body["data"]["access_token"]
    status, body = call("PUT", f"/posts/{post_id}", {"content": "我是别人，改你的帖"}, token=other_token)
    check("改别人的帖子 403", status == 403, body)

    status, body = call("PUT", f"/posts/{post_id}", {"images": ["javascript:alert(1)"]}, token=token)
    check("非法图片地址 400", status == 400, body)

    status, body = call("PUT", "/posts/999999", {"content": "x"}, token=token)
    check("编辑不存在的帖子 404", status == 404, body)

    print("== 6. 个人中心")
    status, body = call("GET", f"/users/{post['author']['id']}")
    check("用户主页", status == 200, body)
    need(
        "用户字段",
        body["data"],
        ["id", "nickname", "avatar_url", "is_admin", "title_level", "title_name", "title_emoji", "follower_count", "following_count", "achievements", "created_at"],
    )

    status, body = call("GET", f"/users/{post['author']['id']}/posts?page=1&page_size=20")
    check("用户帖子", status == 200 and body["data"]["total"] >= 1, body)

    status, body = call("GET", f"/users/{post['author']['id']}/ratings?page=1&page_size=20")
    check("用户评价", status == 200 and body["data"]["total"] >= 1, body)
    need("评价项字段", body["data"]["items"][0], ["dish", "score", "updated_at"])
    need("评价里的菜品字段", body["data"]["items"][0]["dish"], ["id", "name", "image_url", "avg_rating", "rating_count"])

    status, body = call("GET", f"/users/{post['author']['id']}/comments?page=1&page_size=20")
    check("用户评论（刚发过 1 条）", status == 200 and body["data"]["total"] >= 1, body)
    comment_row = body["data"]["items"][0]
    need("评论项字段", comment_row, ["id", "content", "created_at", "post"])
    need("评论所属帖子字段", comment_row["post"], ["id", "dish_name", "excerpt", "image_url"])
    check("评论能定位回原帖", comment_row["post"]["id"] == post_id, comment_row["post"])

    status, body = call("GET", f"/users/{post['author']['id']}/followers?page=1&page_size=30")
    check("粉丝列表", status == 200, body)
    if body["data"]["items"]:
        need("粉丝项字段", body["data"]["items"][0], ["id", "nickname", "title_name", "title_emoji", "is_mutual", "followed_by_me"])

    status, body = call("GET", f"/users/{post['author']['id']}/following?page=1&page_size=30")
    check("关注列表", status == 200, body)

    print("== 7. 菜品详情")
    status, body = call("GET", f"/dishes/{dish_id}/ratings?page=1&page_size=50")
    check("打分记录", status == 200 and body["data"]["total"] >= 1, body)
    need("打分项字段", body["data"]["items"][0], ["user_id", "nickname", "avatar_url", "score", "updated_at"])

    status, body = call("GET", f"/dishes/{dish_id}/posts?page=1&page_size=10")
    check("菜品帖子流", status == 200, body)

    print("== 8. 管理后台")
    status, body = call("POST", "/auth/login", {"username": "admin", "password": "admin123"})
    admin = body["data"]["access_token"]
    check("管理员登录", status == 200, body)
    need("管理员标记", body["data"]["user"], ["is_admin"])
    check("is_admin 为真", body["data"]["user"]["is_admin"] is True, body["data"]["user"])

    status, body = call("GET", "/admin/canteens?page=1&page_size=20", token=admin)
    check("后台食堂表", status == 200 and {"items", "total"} <= set(body["data"]), body)

    status, body = call("GET", "/admin/merchants?page=1&page_size=20", token=admin)
    check("后台商家表", status == 200, body)
    need("后台商家字段", body["data"]["items"][0], ["id", "name", "canteen_name", "overall_rating", "dish_count"])

    status, body = call("GET", "/admin/dishes?page=1&page_size=20&include_unavailable=true", token=admin)
    check("后台菜品表", status == 200, body)

    print("== 9. 上架/下架联动")
    status, body = call("PATCH", f"/admin/dishes/{dish_id}/availability", {"is_available": False}, token=admin)
    check("下架", status == 200 and body["data"]["is_available"] is False, body)
    status, body = call("GET", f"/merchants/{merchant_id}/dishes")
    check("公开列表隐藏已下架", all(item["id"] != dish_id for item in body["data"]), body)
    status, body = call("POST", "/posts", {"dish_id": dish_id, "score": 5}, token=token)
    check("下架后禁止发帖", status == 400, body)
    call("PATCH", f"/admin/dishes/{dish_id}/availability", {"is_available": True}, token=admin)

    print("== 10. 收尾：管理员应急删帖（前端后台走的就是这条）")
    status, body = call("DELETE", f"/admin/posts/{post_id}", token=admin)
    check("管理员删帖", status == 200, body)
    status, body = call("GET", f"/posts/{post_id}")
    check("删后 404", status == 404, body)
    status, body = call("GET", f"/dishes/{dish_id}")
    check(
        "聚合仍未被污染",
        body["data"]["avg_rating"] == avg_before and body["data"]["rating_count"] == count_before,
        body["data"],
    )

    print("== 11. 搜索")
    status, body = call("GET", "/dishes?keyword=" + urllib.parse.quote("拉面"))
    check("搜菜名", status == 200 and body["data"]["total"] >= 1, body)
    check(
        "搜商家名也能命中（兰州拉面）",
        any("拉面" not in d["name"] for d in body["data"]["items"]),
        [d["name"] for d in body["data"]["items"]],
    )
    status, body = call("GET", "/dishes?keyword=" + urllib.parse.quote("绝无此菜"))
    check("空结果不报错", status == 200 and body["data"]["total"] == 0, body)
    status, body = call("GET", "/posts/feed?keyword=" + urllib.parse.quote("辣"))
    check("帖子文案搜索", status == 200, body)

    print("== 12. 修改资料")
    _, me = call("GET", "/users/me", token=token)
    original_nick = me["data"]["nickname"]
    status, body = call("PUT", "/users/me", {"nickname": "旅程改名测试"}, token=token)
    check("改昵称", status == 200 and body["data"]["nickname"] == "旅程改名测试", body)
    status, body = call("PUT", "/users/me", {"nickname": "   "}, token=token)
    check("空昵称被拒", status == 400, body)
    status, body = call("PUT", "/users/me", {"avatar_url": "javascript:alert(1)"}, token=token)
    check("非法头像地址被拒", status == 400, body)
    status, body = call("PUT", "/users/me", {"nickname": original_nick}, token=token)
    check("还原昵称", status == 200 and body["data"]["nickname"] == original_nick, body)

    print(f"\n通过 {passed} / {passed + failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
