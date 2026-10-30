# 校园食光 (Campus Foodie)

校园美食点评社区 MVP。管理员维护「食堂 → 商家 → 菜品」基础库，学生发帖点评必绑一道菜并打星，
评分回写到菜品均分，再通过点赞/评论/24h 热榜和贡献度称号形成闭环。

定位是「小红书的信息流 + 大众点评的菜品评分」，**弱化交易**：不点单、不支付、不做举报与审核流程。

## 功能

**学生端**

- 食堂 / 商家 / 菜品三级导航，菜品与帖子支持关键词搜索（搜「兰州」能出该店下的菜品）
- 发帖：必须绑定菜品 + 1~5 星评分，文案 500 字，图片最多 4 张（上传前自动压缩）
- 信息流（最新 / 最热）、24h 热榜 Top10、帖子详情页（可分享直达）
- 点赞、评论、关注（单向关注，双向自动标记「互关」）
- 个人主页：称号、隐藏成就、帖子 / 评价 / 关注 / 粉丝
- 同一道菜重复打分**覆盖**原评分，不新增评价数——评分代表「我现在的看法」

**管理端**

- 食堂 / 商家 / 菜品增删改查，菜品上架 / 下架，菜品封面上传
- 帖子列表与应急删除（非审核流程）
- 删除保护：食堂下有商家、商家下有菜品、菜品被帖子或评分引用时返回 409 并提示处理方式

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Vue Router + Pinia + Element Plus（按需引入，首屏 JS 约 280KB / gzip 94KB） |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + Alembic + MySQL 8 |
| 认证 | JWT（HS256，7 天）+ bcrypt |
| 图片 | 本地 `uploads/`，前端压缩后上传，服务端校验扩展名与文件头魔数 |

## 目录结构

```
backend/
  app/
    api/v1/       # auth / users / catalog / posts / admin / uploads
    core/         # 配置、安全、统一响应、错误码、称号映射
    models/       # 10 张表，按域拆分
    schemas/      # Pydantic 请求/响应
    services/     # 业务逻辑（发帖、热度、称号、聚合）
    utils/        # 图片校验（MVP 为 Mock，预留 AI 接口）
  alembic/        # 迁移
  scripts/        # smoke_api.py（业务回归）、journey.py（前后端字段契约）
frontend/
  src/
    api/          # 按域拆分的请求封装，统一解包 {code,message,data}
    components/   # PostCard / HotBoard / ErrorState / AppSkeleton …
    views/        # 前台 12 页 + admin/ 4 页
    utils/        # 错误分类、图片压缩、格式化
Research.md  PDR.md  TechDesigh.md  AGENTS.md   # 需求、设计、协作约束
```

## 快速开始

前置：Python 3.11+、Node 18+、MySQL 8（本地 3306）。

### 1. 建库

```sql
CREATE DATABASE campus_foodie DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 后端

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate        # Windows；macOS/Linux 用 .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                 # 然后修改 DATABASE_URL 里的密码
alembic upgrade head                 # 建表
python -m app.seed                   # 灌演示数据（可加 --reset 重来）
uvicorn app.main:app --reload --port 8000
```

`.env` 里的 `DATABASE_URL` 形如：

```ini
DATABASE_URL=mysql+asyncmy://root:你的密码@127.0.0.1:3306/campus_foodie
```

> **密码含 `@` 时必须转义成 `%40`**，否则会被当成 host 分隔符，报出来的错看起来却像密码错误。

顺手把 `JWT_SECRET` 换掉：`python -c "import secrets; print(secrets.token_hex(32))"`。
`.env` 已在 `.gitignore` 里，不会进仓库。

接口文档：http://127.0.0.1:8000/docs

### 3. 前端

```bash
cd frontend
npm install
npm run dev                          # http://127.0.0.1:5173
```

Vite 已把 `/api` 与 `/uploads` 代理到 `127.0.0.1:8000`，前端代码里不出现跨域地址。

## 演示账号

`python -m app.seed` 会写入 9 个用户 / 2 个食堂 / 6 个商家 / 20 个菜品 / 8 条帖子 / 18 条评分。

| 账号 | 密码 | 说明 |
|---|---|---|
| `admin` | `admin123` | 管理员，可进「管理后台」 |
| `xiaoming` | `123456` | 学生，与 `lanzhou_only` 互为关注 |
| `lanzhou_only` | `123456` | 只给兰州拉面那 3 道菜打过分 —— 满足「纯爱战神」隐藏成就条件 |
| 其余 6 个学生 | `123456` | 见 `backend/app/seed.py` |

## 回归脚本

两套脚本都是**自建自清**，跑多少遍都不会污染演示数据（需先启动后端）：

```bash
cd backend
python scripts/smoke_api.py     # 64 项：权限、聚合、称号、删除保护等业务逻辑
python scripts/journey.py       # 58 项：按前端真实调用顺序验字段契约
```

分工：`smoke` 验「算得对不对」，`journey` 验「前端要的字段后端有没有」。接口一改先跑 `journey`。

## 设计文档

| 文件 | 内容 |
|---|---|
| `Research.md` | 竞品分析、需求取舍、已识别风险 |
| `PDR.md` | 功能范围、页面清单、业务规则、决策记录 |
| `TechDesigh.md` | 数据模型、API 契约、错误码、聚合策略、前端约定 |
| `AGENTS.md` | 协作边界与 13 条「实现时不得偏离」的技术契约 |

## 已知边界（MVP 有意不做）

- **不做举报与审核流程**：非美食图靠 Mock 校验（后缀 + 魔数）兜底，仅保留管理员应急删帖
- **不做 AI 视觉审核**：`utils/image_validator.py` 保留 `validate_food_image()` 接口，未来替换实现即可
- **不做交易**：无点单、支付、优惠
- **菜品被引用后不可物理删除**，只能下架（`is_available=0`），历史帖子与评分完整保留
- 图片存放在本地磁盘，未接对象存储
