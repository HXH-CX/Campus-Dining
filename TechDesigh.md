# 3. 技术设计文档 (Tech Design.md)

> 版本：v1.1（2026-10-30 修订，与 PRD v1.1 对齐）

## 3.1 技术架构概览
- **前端**：Vue 3 + Vite + Vue Router + Pinia + Element Plus
- **后端**：Python 3.10+ + FastAPI + SQLAlchemy 2.0 (Async) + Alembic (数据库迁移)
- **数据库**：MySQL 8.0
- **图片存储**：本地文件系统 (`./uploads/`)，通过 FastAPI 的 `StaticFiles` 提供静态资源访问
- **运行环境**：本地开发 (localhost)，前后端分离运行

> **UI 库已定稿为 Element Plus**（原文档"Element Plus / Naive UI"二选一已收口）。小程序迁移不在 MVP 范围内，本项目不引入 uni-app，迁移时另起工程。

## 3.2 系统架构图 (文字版)
```text
[浏览器 (Vue3)]
      │ HTTP/JSON (Authorization: Bearer <JWT>)
      ▼
[FastAPI 后端]
      │
      ├── /api/v1/auth      (JWT 认证)
      ├── /api/v1/uploads   (图片上传，先传后引用)
      ├── /api/v1/canteens  (食堂/商家/菜品 只读查询)
      ├── /api/v1/posts     (帖子发布/列表/热榜/点赞/评论)
      ├── /api/v1/users     (用户信息/关注/称号)
      ├── /api/v1/admin     (管理员 CRUD)
      └── /uploads          (静态图片服务)
      │
      ▼
[MySQL 数据库]       [本地磁盘 ./uploads/]
```

## 3.3 核心 API 设计 (RESTful)

统一前缀 `/api/v1`。标记 🔒 表示需要登录，标记 👑 表示需要管理员角色。

### 3.3.1 认证模块
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 学生注册（username/nickname/password） |
| POST | `/auth/login` | 登录，返回 JWT Token |
| GET | `/users/me` 🔒 | 当前用户信息（含称号、隐藏称号、计数） |

### 3.3.2 图片上传
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/uploads/images` 🔒 | `multipart/form-data` 单文件上传，返回 `{"url": "/uploads/2026/10/xxx.jpg"}`。服务端限制 5MB、仅 jpg/jpeg/png/webp，并校验文件头魔数；前端会先压缩（见 3.12.3）。发帖/改头像时引用该 URL |

> **形态定稿**：图片**先上传、后引用**。发帖接口走 JSON body 携带 `images: [url...]`，不使用 multipart 混合提交，避免前端 FormData 与 Pydantic 校验打架。

### 3.3.3 基础数据（公开只读）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/canteens` | 食堂列表 |
| GET | `/canteens/{id}/merchants` | 某食堂下的商家列表（含综合评分） |
| GET | `/merchants` | 商家搜索：`?keyword=` 按名字模糊匹配，留空返回全部；评分口径与食堂页一致（只算上架菜品），按综合评分倒序 |
| GET | `/merchants/{id}` | 商家详情（综合评分、菜品数） |
| GET | `/merchants/{id}/dishes` | 商家菜品列表（`?include_unavailable=false` 默认只返回上架） |
| GET | `/merchants/{id}/posts` | 该商家下所有帖子的分页流 |
| GET | `/dishes` | 菜品搜索：`?keyword=` 按菜名**或商家名**模糊匹配，只返回上架菜品；留空返回全部 |
| GET | `/dishes/top` | 高分榜：`?min_rating=4&min_count=2&limit=6`，只取上架菜品，按均分倒序、同分看评价数。**必须注册在 `/dishes/{id}` 之前**，否则会被路径参数吞掉（返回 422） |
| GET | `/dishes/random` | 随机抽一道菜（今天吃什么）：`?source=auto\|wants&exclude_id=`。`auto`（默认）先在高分池里抽、池空回退到全部上架菜品；`wants` 只在当前用户的想吃清单里抽（需登录，清单为空返回 404，**不回退**）。返回 `{dish, pool_size, source}`。同样**必须注册在 `/dishes/{id}` 之前** |
| GET | `/dishes/{id}` | 菜品详情（含所属商家、食堂，以及 `want_count` / `is_wanted`） |
| POST | `/dishes/{id}/want` 🔒 | 加入 / 移出想吃清单（幂等翻转），返回 `{wanted, want_count}`；已下架菜品拒绝加入（40001） |
| GET | `/users/{id}/wants` | 某人的想吃清单（分页，最近加的在前；已下架的菜仍返回，由前端标记） |
| GET | `/dishes/{id}/posts` | 该菜品的帖子分页流 |
| GET | `/dishes/{id}/ratings` | 该菜品的打分记录（分页，返回昵称/头像/星级/时间） |

### 3.3.4 社区模块（学生）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/posts` 🔒 | 发布帖子，body：`{dish_id, score(1-5), content?, images: [url]}`。事务内：写 post → **upsert rating** → 重算 dish 聚合。响应里的 `dish` 必须是**重算后**的值（前端结果面板直接用它展示"这道菜现在几分"），重算后要 `db.refresh(dish)` |
| GET | `/posts/feed` | 信息流 `?sort=latest\|hot\|following&page=&page_size=&keyword=`（keyword 匹配帖子文案）。`following` 需登录，未登录返回 40101；只返回我关注的人（**不含我自己**）的帖子，按时间倒序，`total` 用于前端区分"没人发帖"与"没关注人" |
| GET | `/posts/hot` | 24小时热榜 Top10（读缓存） |
| GET | `/posts/{id}` | 帖子详情（含菜品、商家、作者、我是否点过赞） |
| PUT | `/posts/{id}` 🔒 | 编辑自己的帖子：只接受 `content` / `images`，**不含评分与菜品**（改评分语义是重新表态，走发帖 upsert）。字段可省略，传 `null` 表示清空 |
| DELETE | `/posts/{id}` 🔒 | 删除自己的帖子（评论与点赞随帖级联，**评分保留**） |
| POST | `/posts/{id}/like` 🔒 | 点赞/取消点赞（幂等切换），同步维护 `like_count` |
| GET | `/posts/{id}/comments` | 评论列表（分页） |
| POST | `/posts/{id}/comments` 🔒 | 发表评论，同步维护 `comment_count` |
| DELETE | `/posts/{id}/comments/{cid}` 🔒 | 删除评论：本人或管理员；同步回减 `comment_count`，返回 `{comment_count}`。评论不属于该帖时按 404 处理 |

### 3.3.5 用户模块
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/users` | 用户搜索：`?keyword=` 按昵称模糊匹配，粉丝多的排前面；登录后 `followed_by_me` / `is_mutual` 相对当前用户 |
| GET | `/users/{id}` | 用户公开主页信息 |
| GET | `/users/{id}/liked-posts` 🔒 | 我赞过的帖子，按**点赞时间**倒序；仅本人可看，别人的 id 返回 40301 |
| PUT | `/users/me` 🔒 | 改昵称 / 头像（`avatar_url` 传 null 表示清空；用户名与称号不可改） |
| GET | `/users/{id}/posts` | 该用户的帖子列表 |
| GET | `/users/{id}/ratings` | 该用户的评价记录（公开） |
| GET | `/users/{id}/comments` | 该用户发过的评论，含所属帖子 `{id, dish_name, excerpt, image_url}`，用于回跳原帖（公开） |
| GET | `/users/{id}/followers` | 粉丝列表（带 `is_mutual` 互关标记） |
| GET | `/users/{id}/following` | 关注列表（带 `is_mutual`） |
| POST | `/users/{id}/follow` 🔒 | 关注/取消关注（幂等切换），维护两侧计数 |

### 3.3.5.1 通知模块（🔒 全部需登录）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/notifications?page=&page_size=&unread_only=` | 我的通知，按时间倒序；每项含 `{id, type, is_read, created_at, actor, post, comment_content}`，`post` 带 `{id, dish_name, content, image_url}` 供前端摘要展示 |
| GET | `/notifications/unread-count` | 未读数，铃铛角标专用（比拉列表便宜） |
| POST | `/notifications/read` | 全部标为已读，返回 `{updated, unread: 0}` |
| POST | `/notifications/{id}/read` | 单条标为已读；别人的通知按 404 处理（不暴露 id 是否存在） |

### 3.3.6 管理后台 CRUD（👑）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/overview` | 数据概览：总量 / 今日新增 / 近 7 天发帖趋势（缺数据的天补 0）/ 上架但 0 人评的菜 / 无在售菜品的商家 / 已下架菜品数。全部查询时现算，不建统计表 |
| GET | `/admin/canteens?page=&page_size=` | 食堂列表 |
| POST | `/admin/canteens` | 创建食堂 |
| PUT | `/admin/canteens/{id}` | 改名 |
| DELETE | `/admin/canteens/{id}` | 删除（有商家时 40901） |
| GET/POST | `/admin/merchants` | 商家列表 / 创建（需 canteen_id） |
| PUT | `/admin/merchants/{id}` | 改名 / 换属食堂 |
| DELETE | `/admin/merchants/{id}` | 删除（有菜品时 40901） |
| GET/POST | `/admin/dishes` | 菜品列表（可含下架）/ 创建（需 merchant_id、image_url） |
| PUT | `/admin/dishes/{id}` | 改名 / 换属商家 / 替换图片 |
| PATCH | `/admin/dishes/{id}/availability` | 上架/下架 `{is_available: bool}` |
| DELETE | `/admin/dishes/{id}` | 删除（被帖子/评分引用时 40901，改为下架） |
| GET | `/admin/posts` | 帖子列表 `?keyword=&page=&page_size=`（后台定位违规内容用） |
| DELETE | `/admin/posts/{id}` | 应急删除违规帖子（非审核流程） |

## 3.4 数据库表结构设计 (MySQL)

```sql
-- 用户表
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL,
    avatar_url VARCHAR(255) DEFAULT NULL,
    title_level TINYINT NOT NULL DEFAULT 1 COMMENT '称号等级1-5，名称由后端映射，不存中文',
    is_admin TINYINT(1) NOT NULL DEFAULT 0 COMMENT '管理员标记',
    follower_count INT NOT NULL DEFAULT 0,
    following_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 用户成就/隐藏称号表（可与等级称号并存）
CREATE TABLE user_achievements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    code VARCHAR(50) NOT NULL COMMENT '如 pure_love_warrior',
    unlocked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_code (user_id, code),
    CONSTRAINT fk_ach_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 食堂表
CREATE TABLE canteens (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 商家表（不存综合评分，查询时聚合）
CREATE TABLE merchants (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    canteen_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_canteen (canteen_id),
    CONSTRAINT fk_merchant_canteen FOREIGN KEY (canteen_id) REFERENCES canteens(id)
);

-- 菜品表
CREATE TABLE dishes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    image_url VARCHAR(255) DEFAULT NULL,
    merchant_id BIGINT NOT NULL,
    avg_rating DECIMAL(3,2) NOT NULL DEFAULT 0.00 COMMENT '冗余聚合，由 ratings 重算',
    rating_count INT NOT NULL DEFAULT 0,
    is_available TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1上架 0下架；下架不可被新帖关联',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_merchant (merchant_id),
    CONSTRAINT fk_dish_merchant FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- 帖子表
CREATE TABLE posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    dish_id BIGINT NOT NULL,
    content TEXT,
    images JSON COMMENT '["/uploads/xxx.jpg"]',
    like_count INT NOT NULL DEFAULT 0,
    comment_count INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_created (created_at),
    KEY idx_dish (dish_id),
    KEY idx_user (user_id),
    CONSTRAINT fk_post_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_post_dish FOREIGN KEY (dish_id) REFERENCES dishes(id)
);

-- 打分表（一人一菜一条，重复打分覆盖更新 updated_at）
CREATE TABLE ratings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    dish_id BIGINT NOT NULL,
    score TINYINT NOT NULL CHECK (score BETWEEN 1 AND 5),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_dish (user_id, dish_id),
    KEY idx_user_recent (user_id, updated_at),
    KEY idx_dish (dish_id),
    CONSTRAINT fk_rating_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_rating_dish FOREIGN KEY (dish_id) REFERENCES dishes(id)
);

-- 评论表
CREATE TABLE comments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    post_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_post (post_id, created_at),
    CONSTRAINT fk_comment_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT fk_comment_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 点赞表
CREATE TABLE likes (
    user_id BIGINT NOT NULL,
    post_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, post_id),
    KEY idx_post (post_id),
    CONSTRAINT fk_like_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_like_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- 关注表（单向；互关由查询两侧推导）
CREATE TABLE follows (
    follower_id BIGINT NOT NULL,
    following_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, following_id),
    KEY idx_following (following_id),
    CONSTRAINT fk_follow_follower FOREIGN KEY (follower_id) REFERENCES users(id),
    CONSTRAINT fk_follow_following FOREIGN KEY (following_id) REFERENCES users(id)
);

-- 想吃清单（一人一菜一条；纯标记，不影响评分）
CREATE TABLE wants (
    user_id BIGINT NOT NULL,
    dish_id BIGINT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, dish_id),
    KEY idx_wants_dish (dish_id),
    CONSTRAINT fk_want_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_want_dish FOREIGN KEY (dish_id) REFERENCES dishes(id)
);

-- 站内通知（被赞 / 被评论 / 被关注）
CREATE TABLE notifications (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL COMMENT '接收者',
    actor_id BIGINT NOT NULL COMMENT '触发者',
    type VARCHAR(20) NOT NULL COMMENT 'like / comment / follow',
    post_id BIGINT NULL,
    comment_id BIGINT NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- 覆盖"某人的铃铛按时间倒序 + 未读筛选"这一个主要查询
    KEY idx_notifications_user (user_id, is_read, created_at),
    KEY idx_notifications_actor (actor_id),
    CONSTRAINT fk_notify_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notify_actor FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_notify_post FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    CONSTRAINT fk_notify_comment FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
);
```

## 3.5 图片审核接口预留设计
在后端创建独立的 `image_validator.py` 模块：
```python
# app/utils/image_validator.py
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIZE = 5 * 1024 * 1024

async def validate_food_image(image_path: str) -> bool:
    """
    MVP阶段：仅校验文件类型和大小，默认通过
    未来迭代：替换为调用大模型VL API判断是否为美食
    """
    # TODO: 接入 AI 视觉模型
    return True
```
上传接口在落盘前调用此函数，确保未来升级时无需修改业务代码。

## 3.6 聚合与计算策略

### 3.6.1 菜品评分（写时重算）
发帖时在同一事务内 upsert 评分，然后重算该菜品的冗余聚合字段：
```sql
INSERT INTO ratings (user_id, dish_id, score) VALUES (:uid, :did, :score)
ON DUPLICATE KEY UPDATE score = VALUES(score), updated_at = NOW();

UPDATE dishes d SET
    avg_rating = COALESCE((SELECT ROUND(AVG(r.score), 2) FROM ratings r WHERE r.dish_id = d.id), 0),
    rating_count = (SELECT COUNT(*) FROM ratings r WHERE r.dish_id = d.id)
WHERE d.id = :did;
```

### 3.6.2 商家综合评分（读时聚合，不落库）
```sql
SELECT m.*,
       COALESCE(ROUND(SUM(d.avg_rating * d.rating_count) / NULLIF(SUM(d.rating_count), 0), 2), 0) AS overall_rating,
       COUNT(d.id) AS dish_count
FROM merchants m
LEFT JOIN dishes d ON d.merchant_id = m.id AND d.is_available = 1
WHERE m.id = :mid
GROUP BY m.id;
```

### 3.6.3 热榜（定时缓存）
进程内缓存（MVP 不上 Redis）+ APScheduler 每小时预热，启动时先热一次：

```sql
SELECT p.*, (p.like_count + p.comment_count * 2) AS hot_score
FROM posts p
WHERE p.created_at >= NOW() - INTERVAL 24 HOUR
ORDER BY hot_score DESC
LIMIT 10;
```
- 缓存 TTL = `HOT_CACHE_TTL_SECONDS`（默认 3600），定时任务与 TTL 同一个值，靠 TTL 兜底：即使调度器没起来，接口也会按需重算，不会报错。
- 发帖 / 删帖 / 点赞 / 评论后主动 `invalidate()`，让榜单尽快反映变化，而不是死等一小时。
- `is_liked` 是"按人"的字段，不能进缓存：缓存只存公共部分，返回前按访问者补一次。
> 说明：帖子本身≤24h，其 `like_count`/`comment_count` 的全量值与窗口内值等价，无需另建窗口计数表。
> Feed 的 `sort=hot` 用同一公式但不加 24h 限制，即全时段热度排序。

### 3.6.4 称号（懒更新，只升不降）
触发点：访问 `/users/me`、发帖/打分成功后。**不建冗余计数列**，直接按索引 COUNT（校园站量级足够，避免计数漂移）：

```sql
-- 发帖数
SELECT COUNT(*) FROM posts WHERE user_id = :uid;
-- 获赞数
SELECT COUNT(*) FROM likes l JOIN posts p ON l.post_id = p.id WHERE p.user_id = :uid;
-- 纯爱战神：近30天打分全部来自同一商家且次数≥3
SELECT COUNT(*) AS cnt, COUNT(DISTINCT d.merchant_id) AS merchants
FROM ratings r JOIN dishes d ON r.dish_id = d.id
WHERE r.user_id = :uid AND r.updated_at >= NOW() - INTERVAL 30 DAY;
```
- 等级判定从 Lv.5 向下匹配，命中即停：`5 → (posts≥100 AND likes≥2000)`；`4 → (posts≥50 OR likes≥500)`；`3 → (posts≥20 OR likes≥100)`；`2 → (posts≥5 OR likes≥20)`；否则 1。
- 仅当新等级 > `users.title_level` 时更新，**不降级**。
- 纯爱战神：`cnt >= 3 AND merchants = 1` → 先 `SELECT` 判断是否已解锁，再插入 `user_achievements`，一次性永久保留。
  （不用 `INSERT IGNORE`：虽然也能去重，但 MySQL 会把重复键当警告抛给驱动，日志会被刷屏。）
- 称号名称映射放在 `app/core/titles.py` 常量字典，随用户信息一起返回。

## 3.7 接口契约

### 3.7.1 统一响应体
```json
{ "code": 0, "message": "ok", "data": { } }
```
分页数据固定结构：
```json
{ "code": 0, "message": "ok", "data": { "items": [], "total": 0, "page": 1, "page_size": 20 } }
```
由全局异常处理器保证：`HTTPException` 与业务异常都转换为该结构，前端只需判 `code`。

### 3.7.2 错误码
| code | HTTP | 含义 |
|---|---|---|
| 0 | 200 | 成功 |
| 40001 | 400 | 参数校验失败 |
| 40101 | 401 | 未登录 / Token 失效 |
| 40301 | 403 | 无权限（非本人 / 非管理员） |
| 40401 | 404 | 资源不存在 |
| 40901 | 409 | 资源冲突（唯一键冲突 / 存在下级数据不可删） |
| 42901 | 429 | 请求过于频繁（评论/发帖限流） |
| 50000 | 500 | 服务器内部错误 |

### 3.7.3 分页参数
统一 `page`（从1开始，默认1）、`page_size`（默认20，上限50）。

## 3.8 认证与安全
- 密码哈希：直接用官方 `bcrypt` 库（**不用 passlib**——passlib 1.7.4 依赖 Python 3.13 已移除的标准库 `crypt`，导入期就会炸）。bcrypt 只处理前 72 字节，注册接口把密码长度限制在 6~32 字符，从源头规避截断。
- JWT：`HS256`，payload `{sub: user_id, exp}`，**有效期 7 天**，MVP 不做 refresh token，过期即重新登录。
- 传递方式：`Authorization: Bearer <token>`。
- 角色：`users.is_admin` 字段区分（MVP 单角色表即可，不建 permission/role 多表）。管理员账号由种子脚本创建。
- CORS：开发期放开 `http://localhost:5173`，从 `.env` 读取 `CORS_ORIGINS`。
- 上传文件校验：扩展名白名单 + 文件头魔数校验 + 大小限制 + 随机文件名（不使用用户原始文件名）。

## 3.9 本地开发环境
- **数据库**：本机已装 MySQL 8.0.46（3306 端口在监听），**不需要 Docker**，直接建库 `campus_foodie` 即可。
  如需在新机器复现，再补 `docker-compose.yml` 起 MySQL 8.0 单实例。
- 驱动用 `asyncmy`，**必须同时装 `cryptography`**：MySQL 8 默认 `caching_sha2_password`，缺它会在握手阶段报
  `'cryptography' package is required for sha256_password or caching_sha2_password auth methods`。
- `.env`（从 `backend/.env.example` 复制，不入库）：
  ```ini
  DEBUG=true
  DATABASE_URL=mysql+asyncmy://root:<你的密码>@127.0.0.1:3306/campus_foodie
  DB_ECHO=false
  JWT_SECRET=<随机 32 字节>
  JWT_EXPIRE_DAYS=7
  UPLOAD_DIR=./uploads
  UPLOAD_MAX_MB=5
  CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
  ```
- 启动顺序：
  1. `CREATE DATABASE campus_foodie DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;`
  2. `python -m alembic upgrade head`
  3. `python -m app.seed`（2 个食堂 / 6 个商家 / 20 个菜品 + 打底帖，解决冷启动）
  4. `uvicorn app.main:app --reload --port 8000`
- 探针：`GET /health` 看服务、`GET /health/db` 看库连不连得上——排查 .env 先看后者。
- **`alembic.ini` 必须保持纯 ASCII**：Windows 下 configparser 用系统 GBK 解码该文件，写中文注释会直接 `UnicodeDecodeError`。连接串也不写在这里，由 `alembic/env.py` 从 `app.core.config` 读，避免两处维护。
- 前端：`npm run dev`（Vite 代理 `/api` 与 `/uploads` 到 `127.0.0.1:8000`，避免跨域调试成本）。

## 3.10 前端接口层约定
- 所有请求封装在 `src/api/`，按域拆分：`auth.ts`、`post.ts`、`catalog.ts`（食堂/商家/菜品）、`user.ts`、`admin.ts`、`upload.ts`。
- Axios 实例统一：注入 Token、响应拦截器解包 `data`、`code !== 0` 抛业务异常、40101 自动登出跳登录页。
- 类型定义放 `src/types/`，与后端 Pydantic Schema 保持一一对应。

## 3.11 前端错误兜底约定

目标：任何一层出问题都不能白屏，且错误文案要说清楚"是没连上、超时、还是服务器出错"。

| 层次 | 机制 | 位置 |
|---|---|---|
| 请求失败 | `describeError()` 把 axios 错误分类为 `network / timeout / server / notfound / forbidden / unauthorized / unknown`，返回标题+说明+是否可重试 | `src/utils/error.ts` |
| 页面主数据 | 每个页面持有 `error` 状态，加载失败渲染 `<ErrorState>`（图标+说明+重试/刷新），**不再只弹一条 3 秒消失的 toast** | `src/components/ErrorState.vue` |
| 局部区域 | 热榜等"锦上添花"的区块失败时只降级自己（`compact` 模式），不拖垮整页 | `HotBoard.vue` |
| 渲染异常 | `<ErrorBoundary>` 用 `onErrorCaptured` 接住子树抛错，换页（`reset-key=route.fullPath`）自动清除 | `src/components/ErrorBoundary.vue`、`App.vue` |
| 全局兜底 | `app.config.errorHandler` 接根组件异常；`unhandledrejection` 只记日志（axios 错误已由拦截器提示，避免二次弹窗） | `src/main.ts` |
| 发版后 chunk 失效 | `router.onError` 识别动态 import 失败 → 自动整页刷新一次（`sessionStorage` 防死循环） | `src/router/index.ts` |
| 开发期后端未启动 | Vite 代理的 `error` 事件返回 502 + `{"code":50200,"message":"后端服务未启动..."}`，错误卡片直接说明原因 | `vite.config.ts` |

约定：**错误提示只负责"告知"，错误状态负责"可恢复"**。Toast 用于用户主动操作失败（点赞、提交表单），ErrorState 用于页面级加载失败。

## 3.12 加载态与前端构建

### 3.12.1 骨架屏统一用 `AppSkeleton`
不用 `el-skeleton`：它的 `rows` 是等宽文字条，和卡片/表格/头像完全不是一个形状，数据到位会明显跳一下。
`components/AppSkeleton.vue` 按内容形态提供 7 种骨架，尺寸对齐真实内容，加载完成不位移：

| variant | 用在哪 |
|---|---|
| `post` | 信息流、搜索的帖子 Tab、商家页帖子 Tab |
| `card` | 食堂/商家/菜品宫格 |
| `row` | 热榜、评论列表 |
| `detail` | 商家/菜品详情（头图 + 宫格） |
| `profile` | 个人主页 |
| `form` | 发帖页、登录注册 |
| `table` | 管理后台表格 |

新增列表页时**必须**有骨架分支，顺序固定为：`loading → skeleton` / `error → ErrorState` / `empty → 空态文案` / `else 内容`。
四条分支缺一条就会出现"闪一下空态"或"白屏"。

### 3.12.2 Element Plus 按需引入（自定义 resolver）
`unplugin-vue-components` + 自定义 resolver（见 `vite.config.ts` 的 `elementPlusComponentResolver`）。

**不要换回官方 `ElementPlusResolver`**：它对 Element Plus ≥1.1 统一从 `element-plus/es`（包根 barrel）导入，
而根入口里有 `makeInstaller([...全部组件])`，摇树摇不掉 —— 实测打出来 944KB，和全量引入没区别。
自定义 resolver 按组件目录逐个导入后降到 448KB。

配套约束：
- **禁止** `import { ElMessage } from 'element-plus'`，统一从 `@/utils/feedback` 拿（内部走 `element-plus/es/components/message/index`），否则根 barrel 又会被拉进来。
- **子组件的样式要单独引**：`ElTableColumn`、`ElFormItem`、`ElTabPane`、`ElBreadcrumbItem`、`ElDropdownMenu/Item`、`ElOption` 这类子组件**没有独立 JS 入口**（要从父目录 `index` 导入），但**样式是独立文件**（`theme-chalk/el-form-item.css`），父组件的 `style/css` 并不会带上。
  resolver 里 `sideEffects` 必须同时写父目录和自己目录，否则会出现"结构正常但样式缺一块"——典型症状是面包屑末尾多出一个斜杠、表单项之间没有间距。
- 函数式组件（Message / MessageBox）和指令（v-loading）不会自动带样式，样式在 `main.ts` 显式 `import 'element-plus/es/components/xxx/style/css'`。
- 语言包改用 `<el-config-provider :locale="zhCn">` 下发（不再 `app.use(ElementPlus)`）。
- `src/components.d.ts` 是插件生成的组件类型声明，**需要入库**，否则新克隆的仓库 `vue-tsc` 会报未知组件。
- `manualChunks` 用函数写法；对象写法 `{ 'element-plus': ['element-plus'] }` 会把整包拉进 chunk，等于废掉按需引入。

实测产物（vite build）：

| | 改造前 | 改造后 |
|---|---|---|
| 首屏 JS | 634 KB（其中 element-plus 448 KB 全量） | 286 KB |
| 首屏 CSS | 363 KB | 53 KB |
| 按需 EP 组件总量 | 944 KB | 448 KB |

### 3.12.3 图片上传前压缩（`utils/image.ts`）
手机拍的食物照通常 3-5MB / 4000px 宽，而卡片里最宽只显示到 600px 左右，原样上传既慢又占磁盘。
`uploadImage(file, options)` 内部先用 `compressImage()` 压缩再发 multipart，**所有上传入口自动生效**（发帖、头像、菜品封面）。

| 场景 | maxEdge | 说明 |
|---|---|---|
| 帖子配图 | 1600（默认） | 详情页大图要清晰 |
| 菜品封面 | 1200 | 列表 200px / 详情 600px |
| 用户头像 | 400 | 最大显示 72px，够 3x 屏 |

实现要点：
- 用 `createImageBitmap(file, { imageOrientation: 'from-image' })` 解码，让竖拍照片按 EXIF 摆正；老浏览器退回 `<img>` + objectURL。
- canvas 缩放时先铺白底：PNG 透明区转 JPEG 会变黑。
- 优先编码 WebP，浏览器不支持 WebP 编码时 `toBlob` 会回落成 PNG/JPEG，按 `blob.type` 换后缀 —— **后端会校验扩展名与文件头魔数一致，名字对不上会被拒**。
- 三条放弃条件：类型不是 jpg/png/webp、体积 ≤300KB 且尺寸不超标、压缩结果反而更大 —— 都退回原图。
- **任何异常都退回原图**：压缩是优化不是前置条件，不能因为它导致传不上去。
- 但"压缩没生效 + 文件超过 5MB"会在 `uploadImage()` 里提前拦下（抛"图片压缩失败且超过 5MB"），
  避免发一个注定被服务端 400 拒掉的请求。

实测（Chrome 无头，带噪点 4000×3000 JPEG）：5.8MB → 360KB WebP，长边 1600，前端上传接口返回 `code=0`，静态访问 `Content-Type: image/webp`。

配套调整：前端 `beforeUpload` 的体积上限从 5MB 放宽到 20MB（压缩在后，5MB 只会误伤手机原图），
服务端 `UPLOAD_MAX_MB` 保持 5 —— 压缩后的文件远低于它，留作兜底。
