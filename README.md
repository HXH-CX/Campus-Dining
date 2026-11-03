# 校园食光 (Campus Foodie)

[![CI](https://github.com/HXH-CX/Campus-Dining/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/HXH-CX/Campus-Dining/actions/workflows/ci.yml)

校园美食点评社区 MVP。管理员维护「食堂 → 商家 → 菜品」基础库，学生发帖点评必绑一道菜并打星，
评分回写到菜品均分，再通过点赞/评论/24h 热榜和贡献度称号形成闭环。

定位是「小红书的信息流 + 大众点评的菜品评分」，**弱化交易**：不点单、不支付、不做举报与审核流程。

## 界面

<p align="center">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/home.png" alt="首页" width="580">
</p>
<p align="center"><sub>首页：高分榜、今日热榜、图文流（最新 / 最热 / 关注）</sub></p>

<p align="center">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/dish.png" alt="菜品详情" width="285">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/random.png" alt="今天吃什么" width="285">
</p>
<p align="center"><sub>左：菜品详情（口味标签、想吃、这家还有）　右：一键随机抽一道菜，可换、可直接去吃</sub></p>

<p align="center">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/search.png" alt="搜索" width="285">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/create.png" alt="发帖" width="285">
</p>
<p align="center"><sub>左：四页签搜索 + 口味标签筛选（还没菜的标签置灰）　右：发帖必须绑菜品并打分</sub></p>

<p align="center">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/notifications.png" alt="通知中心" width="285">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/profile-liked.png" alt="我赞过的" width="285">
</p>
<p align="center"><sub>左：通知中心（被赞 / 被评论 / 被关注）　右：个人主页「我赞过的」，仅本人可见</sub></p>

<p align="center">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/admin.png" alt="管理后台" width="580">
</p>
<p align="center"><sub>管理后台：今日新增、近 7 天发帖趋势、待关注项（上架没人评 / 没有在售菜的商家）</sub></p>

<p align="center">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/mobile-home.png" alt="移动端首页" width="188">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/mobile-dish.png" alt="移动端菜品页" width="188">
  <img src="https://gcore.jsdelivr.net/gh/HXH-CX/Campus-Dining@main/docs/screenshots/mobile-notifications.png" alt="移动端通知" width="188">
</p>
<p align="center"><sub>移动端：底部导航 + 中间抬起的发帖键，≤900px 顶栏搜索收成图标</sub></p>

> 截图由 `frontend/scripts/shots.mjs` 用真浏览器生成（同一套 CDP 驱动，不依赖 puppeteer），
> 改了样式跑一遍即可全套重截，不用手工一张张换。
>
> **图片走 jsDelivr 镜像而不是仓库相对路径**：GitHub 会把相对路径改写成
> `raw.githubusercontent.com`，该域名在部分网络环境下不可达，README 就会整片破图
> （页面能开、图片全挂）。`gcore.jsdelivr.net` 是同一份内容、可正常访问的副本。
> 重截后如果发现图没更新，把地址里的 `@main` 换成新的 commit sha，或在末尾加 `?v=2` 破缓存。

## 功能

**学生端**

- 食堂 / 商家 / 菜品三级导航；搜索分四个页签：**菜品 / 帖子 / 商家 / 用户**（搜「兰州」能出该店下的菜，搜「红红」能找到人并直接关注）
- **口味标签**：菜品挂「辣 / 清淡 / 面食 / 汤 / 早饭…」12 个标签（管理员维护，最多 4 个），搜索页一排 chips 可筛，菜品页的标签点一下就去看同类菜
- 发帖：必须绑定菜品 + 1~5 星评分，文案 500 字，图片最多 4 张（上传前自动压缩）；发完给一张「收据」——你打了几分、这道菜现在几分、离高分榜还差什么
- 信息流（最新 / 最热 / **关注**）、24h 热榜 Top10、**高分榜**（均分≥4 且至少 2 人评过）、帖子详情页（可分享直达，图片点开看大图、支持左右翻页）
- **今天吃什么**：一键随机抽一道菜，不满意「换一个」，满意直接进菜品详情；也可以只在「想吃」清单里抽
- **想吃清单**：菜品页「想吃」攒一份候选池，个人中心可查看和移除；发帖打分后自动划掉（吃过就不算想吃）
- 菜品页底部「**这家还有**」：横滑看同店其他在售菜（均分高的在前，没人评过的沉底），点一下换一道，右上角「看全部」进商家页
- 点赞、评论、关注（单向关注，双向自动标记「互关」）
- **回复某条评论**：评论支持一层回复，列表里显示「回复 @某某」，点一下滚到被回复的那条；被回复者收到「回复了你的评论」通知——帖主不会因为别人在楼下互相接话被刷屏
- **通知中心**：被赞 / 被评论 / 被关注都会落一条通知，顶栏铃铛显示未读数（60s 轮询，切到后台不轮）；点一条就标已读并跳到原帖或对方主页；取消点赞、取关、删评论、删帖都会把对应通知一起收回
- 个人主页：称号、隐藏成就、帖子 / 评价 / 想吃 / 我赞过的 / 评论 / 关注 / 粉丝（「我赞过的」仅本人可见，取消点赞会立刻从列表消失）
- 同一道菜重复打分**覆盖**原评分，不新增评价数——评分代表「我现在的看法」
- **手机上好用**：≤560px 顶栏收回成「品牌 + 搜索 + 账号」，导航挪到底部固定栏（首页 / 食堂 / 发帖 / 通知 / 我的），发帖在正中间抬起；≤900px 顶栏搜索框换成图标，保证手机上也有搜索入口

**管理端**

- 数据概览：总量与今日新增、近 7 天发帖趋势、以及「上架但没人评」「没有在售菜品的商家」等待关注项
- 食堂 / 商家 / 菜品增删改查，菜品上架 / 下架，菜品封面上传
- 帖子列表与应急删除（非审核流程）
- 删除保护：食堂下有商家、商家下有菜品、菜品被帖子或评分引用时返回 409 并提示处理方式

## 技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vue 3 + Vite + TypeScript + Vue Router + Pinia + Element Plus（按需引入，首屏 JS 131.8KB / gzip 50KB） |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + Alembic + MySQL 8 |
| 认证 | JWT（HS256，7 天）+ bcrypt；登录失败限流，登出后按令牌版本吊销旧 token |
| 图片 | 本地 `uploads/`，前端压缩后上传，服务端校验扩展名与文件头魔数 |

## 目录结构

```
backend/
  app/
    api/v1/       # auth / users / catalog / posts / notifications / admin / uploads
    core/         # 配置、安全、统一响应、错误码、称号映射
    models/       # 12 张表，按域拆分
    schemas/      # Pydantic 请求/响应
    services/     # 业务逻辑（发帖、热度、称号、聚合）
    utils/        # 图片校验（MVP 为 Mock，预留 AI 接口）
  alembic/        # 迁移
  scripts/        # smoke_api.py（业务回归）、journey.py（前后端字段契约）
  Dockerfile      # 容器：迁移 → 补种子 → 起 uvicorn
  docker-entrypoint.sh
frontend/
  src/
    api/          # 按域拆分的请求封装，统一解包 {code,message,data}
    components/   # PostCard / HotBoard / ErrorState / AppSkeleton …
    views/        # 前台 13 页 + admin/ 5 页
    utils/        # 错误分类、图片压缩、格式化
  scripts/        # e2e.mjs（真浏览器关键交互）、shots.mjs（生成 README 截图）
  Dockerfile      # 构建 dist 后交给 nginx
  nginx.conf      # 提供静态文件，并把 /api、/uploads 反代到后端
docker-compose.yml # 仓库根：mysql + backend + frontend 一条命令起全栈
dev.py            # 仓库根：一键启动（建 venv / 装依赖 / 等 MySQL / 迁移 / 灌种子 / 拉起前后端）
start.bat         # 仓库根：Windows 入口（双击即可）
start.sh          # 仓库根：macOS / Linux 入口
docs/screenshots/ # 仓库根：README 用的界面截图，由 shots.mjs 生成
Research.md  PDR.md  TechDesigh.md  AGENTS.md   # 需求、设计、协作约束
LEARNING.md       # 仓库根：怎么吃透这个项目（六个阶段 + 通关标准）
```

## 快速开始

前置：Python 3.10+、Node 18+（**跑 e2e / 截图脚本要 Node 22+**，它们用全局 `WebSocket` 连 CDP）、MySQL 8（本地 3306）。

### 1. 建库

```sql
CREATE DATABASE campus_foodie DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. 一键启动

在仓库根目录执行：

```bash
python dev.py                # Windows 也可双击 start.bat；macOS / Linux 用 ./start.sh
```

它会按需补齐环境：缺 venv 就建、缺依赖就装、缺 `.env` 就从模板复制、等 MySQL 起来、跑迁移、
补种子数据（已有的不重复写），最后同时拉起前后端并打开浏览器。**重复执行是安全的**，
可以直接当日常启动入口。

| 参数 | 作用 |
|---|---|
| `--reset` | 清空业务表后重灌种子（会丢数据） |
| `--reload` | 后端开热重载 |
| `--no-browser` | 不自动打开浏览器 |

首次启动前确认 `backend/.env` 里的 `DATABASE_URL`（写法见下节）。

启动后：前端 http://127.0.0.1:5173 ，接口文档 http://127.0.0.1:8000/docs ，后台 `/admin`。

### 3. 手动启动（想自己控制每一步）

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

另开一个终端：

```bash
cd frontend
npm install
npm run dev                          # http://127.0.0.1:5173
```

Vite 已把 `/api` 与 `/uploads` 代理到 `127.0.0.1:8000`，前端代码里不出现跨域地址。

### 4. 用 Docker 起（机器上没有 Python / Node 时）

```bash
docker compose up --build
```

- 前端 http://localhost:8080 ，接口文档 http://localhost:8000/docs
- MySQL 数据与 `uploads` 都在命名卷里：`docker compose down` 不丢数据，加 `-v` 才会清空
- 端口用 8080 而不是 5173，是为了不和本地 `npm run dev` 抢

容器里由 nginx 提供前端静态文件，并把 `/api`、`/uploads` 反代给后端，所以浏览器侧是同源请求；
`client_max_body_size` 设成 12m，比后端的 10MB 上限略高——否则手机直拍的照片会先被 nginx 用 413 挡掉，
用户看到的是"服务器错误"而不是"图片超过 10MB"。

## 演示账号

`python -m app.seed` 会写入 9 个用户 / 2 个食堂 / 6 个商家 / 20 个菜品 / 8 条帖子 / 18 条评分。

| 账号 | 密码 | 说明 |
|---|---|---|
| `admin` | `admin123` | 管理员，可进「管理后台」 |
| `xiaoming` | `123456` | 学生，与 `lanzhou_only` 互为关注 |
| `lanzhou_only` | `123456` | 只给兰州拉面那 3 道菜打过分 —— 满足「纯爱战神」隐藏成就条件 |
| 其余 6 个学生 | `123456` | 见 `backend/app/seed.py` |

## 回归脚本

三套脚本都是**自建自清**，跑多少遍都不会污染演示数据。

```bash
cd backend
python scripts/smoke_api.py     # 102 项：权限、聚合、称号、删除保护、登录限流、令牌吊销、评论回复、热榜一致性
python scripts/journey.py       # 167 项：按前端真实调用顺序验字段契约

cd ../frontend
npm run e2e                     # 41 项：真浏览器走一遍关键交互
```

分工：
- `smoke` 验「算得对不对」，`journey` 验「前端要的字段后端有没有」——接口一改先跑 `journey`；
- `e2e` 验「点得对不对」：首页 / 关注流 / 搜索四页签 / 口味标签筛选 / 发帖结果面板 / 大图预览 / 评论回复 / 同店其他菜 / 通知 / 个人中心 / 后台标签勾选 / 375px 不溢出。它用 CDP 驱动本机 Chrome，**不需要装 puppeteer**，失败会截图到 `frontend/.e2e-shots/`。

三套也跑在 CI 上（`.github/workflows/ci.yml`）：push 与 PR 会自动起一个 MySQL 服务、建表灌种子、跑完接口与浏览器回归——不用靠人记得在本地手跑。

`e2e` 会真的发一条帖子再删掉；为保证菜品均分不被测试数据带偏，它挑的是「当前账号已评过、且分数相同」的菜，覆盖后聚合值不变。

## 设计文档

| 文件 | 内容 |
|---|---|
| `Research.md` | 竞品分析、需求取舍、已识别风险 |
| `PDR.md` | 功能范围、页面清单、业务规则、决策记录 |
| `TechDesigh.md` | 数据模型、API 契约、错误码、聚合策略、前端约定 |
| `AGENTS.md` | 协作边界与 42 条「实现时不得偏离」的技术契约 |
| `LEARNING.md` | **怎么吃透这个项目**：六个阶段、三种练法、12 个必读文件、5 个改造挑战。适合「代码是别人写的、想真正搞懂」的人 |

## 已知边界（MVP 有意不做）

- **不做举报与审核流程**：非美食图靠 Mock 校验（后缀 + 魔数）兜底，仅保留管理员应急删帖
- **不做 AI 视觉审核**：`utils/image_validator.py` 保留 `validate_food_image()` 接口，未来替换实现即可
- **不做交易**：无点单、支付、优惠
- **菜品被引用后不可物理删除**，只能下架（`is_available=0`），历史帖子与评分完整保留
- 图片存放在本地磁盘，未接对象存储
- **登录限流是进程内计数**（同一用户名 5 次 / 同一 IP 20 次，15 分钟窗口）：单进程够用，
  多 worker 部署时各算各的，实际阈值会被放大；真上多实例要换成 Redis 的 `INCR + EXPIRE`
- **不做找回密码流程**：密码规则（≥8 位、含字母数字）已经提上去了，但没有邮箱/短信找回，
  忘了只能找管理员改库
