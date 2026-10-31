# AGENTS.md - 校园食光 (Campus Foodie) 项目开发指南

## 1. 项目上下文
这是一个校园美食点评与分享社区。
- **前端**：Vue 3 (Vite) + TypeScript + Vue Router + Pinia + Element Plus
- **后端**：Python 3.10+ + FastAPI + SQLAlchemy 2.0 (Async) + Pydantic V2 + Alembic
- **数据库**：MySQL 8.0
- **图片存储**：本地文件系统 (`./uploads/`)

## 2. 目录结构规范
请严格按照以下结构生成和组织代码：

### 前端 (frontend/)
```text
src/
├── api/          # 封装 Axios 请求，按模块划分 (如 post.ts, user.ts)
├── assets/       # 静态资源 (图片、全局 CSS)
├── components/   # 全局复用组件 (如 PostCard.vue, RatingStars.vue)
├── composables/  # 组合式函数 (如 useAuth.ts, useTitle.ts)
├── layouts/      # 页面布局 (如 DefaultLayout.vue, AdminLayout.vue)
├── router/       # 路由配置
├── stores/       # Pinia 状态管理
├── types/        # TypeScript 类型定义
└── views/        # 页面级组件 (如 HomeView.vue, LoginView.vue)
```

### 后端 (backend/)
```text
app/
├── api/v1/       # 路由端点 (endpoints)，按模块划分 (如 auth.py, posts.py)
├── core/         # 核心配置 (config.py, security.py/JWT)
├── db/           # 数据库连接与会话管理 (session.py)
├── models/       # SQLAlchemy ORM 模型 (与数据库表对应)
├── schemas/      # Pydantic 模型 (请求/响应数据校验)
├── services/     # 业务逻辑层 (处理复杂逻辑，避免路由层过于臃肿)
├── utils/        # 工具函数 (如 image_validator.py)
└── main.py       # FastAPI 应用入口
uploads/          # 本地图片存储目录 (需加入 .gitignore)
alembic/          # 数据库迁移脚本
```

## 3. 代码风格与技术约束

### 前端规范
- 必须使用 `<script setup lang="ts">` 和 Composition API。
- 组件命名使用 PascalCase (如 `PostCard.vue`)，文件名与组件名一致。
- 尽量使用 TailwindCSS 进行样式开发（如果引入），或 scoped CSS。
- API 请求必须封装在 `src/api/` 中，不要在 `views` 中直接写 `axios.get`。

### 后端规范
- 遵循 PEP8，使用 `ruff` 进行代码格式化。
- 数据库操作必须使用 SQLAlchemy 2.0 的异步语法 (`async with`, `await session.execute`)。
- 路由层 (api/) 只负责参数校验和调用 service 层，不写复杂 SQL 查询。
- 所有 API 必须有清晰的 Pydantic Schema 定义，并生成 OpenAPI 文档 (FastAPI 自带)。

## 4. AI 协作边界 (核心指令)

### 🟢 AI 可以自主完成的任务 (直接写代码)
- 根据 Schema 生成 CRUD 接口和 SQLAlchemy 模型。
- 编写前端页面的基础 UI 结构和 Element Plus 表单/表格组件。
- 编写单元测试和接口测试代码。
- 修复明确的 Bug 和报错信息。

### 🔴 AI 必须询问/确认的任务 (先沟通再动手)
- **修改数据库表结构**：任何对 `models/` 目录下文件的修改，必须先向我说明影响，并在我确认后再执行 `alembic` 迁移。
- **更改核心算法**：如热榜计算公式、称号升级逻辑，修改前需先提供伪代码或思路。
- **引入新依赖**：不要在未经我同意的情况下在 `requirements.txt` 或 `package.json` 中添加新的第三方库。

## 5. 特殊业务逻辑备忘
- **图片审核 (`app/utils/image_validator.py`)**：当前阶段为 MVP，**不要**去调用真实的 AI 视觉 API。只需实现一个 Mock 函数，校验文件后缀和大小即可，并默认返回 `True`。请保留好接口，以便未来替换为真实 API。
- **热榜与称号**：采用“懒更新”或定时任务，不要在每次用户请求时实时计算全量数据。

## 6. 已定稿的技术契约（实现时不得偏离）

> 以下条目已由 PRD v1.1 / Tech Design v1.1 定稿，解决的是原文档互相矛盾之处。改动需先讨论。

1. **评分写入用 upsert**：`ratings` 上 `(user_id, dish_id)` 唯一。发帖带评分时用 `ON DUPLICATE KEY UPDATE` 覆盖，**不要**抛唯一键错误，也不要改成"一帖一评"。帖子与评分是两件事：一条评分 = 我当前的看法，多条帖子 = 多次就餐体验。
2. **称号不存中文名**：`users.title_level TINYINT`（1-5），名称映射放 `app/core/titles.py`。隐藏称号（如 `pure_love_warrior`）写 `user_achievements` 表，可与等级称号并存。**禁止**再往 `users` 加 `title VARCHAR`。
3. **商家综合评分不落库**：查询时按 `SUM(avg_rating*rating_count)/SUM(rating_count)` 聚合，只统计上架菜品。
4. **管理端是完整 CRUD**：带下级数据时删除返回 40901；菜品被帖子/评分引用后只能下架（`is_available=0`），不物理删除。
5. **MVP 不做举报与审核**：唯一兜底是 `DELETE /api/v1/admin/posts/{id}` 应急删除，不要自行加举报表、审核状态机、封禁字段。
6. **图片先传后引用**：`POST /uploads/images` 返回 URL，发帖走 JSON body 的 `images: [url]`，不用 multipart 混合提交。
7. **统一响应体** `{code, message, data}` + 分页 `{items, total, page, page_size}`，错误码见 Tech Design 3.7.2；由全局异常处理器统一包装，路由层不要自己拼 dict。
8. **前端 UI 库固定 Element Plus**；不引入 uni-app，不做小程序适配层。
9. **认证**：JWT HS256，7 天有效期，`Authorization: Bearer`，不做 refresh token；密码用 bcrypt；管理员用 `users.is_admin` 区分。
10. **页面级请求失败必须渲染错误态**：使用 `<ErrorState :error="e" @retry="load">`，**不要**只弹 toast 留白屏，也不要把失败表现成"暂无数据"（那会让用户以为真的没内容）。错误分类统一走 `src/utils/error.ts`，不要在各处自己判断 `error.response.status`。
11. **Element Plus 只能按需引入**：模板组件由自定义 resolver 自动引入；`ElMessage` / `ElMessageBox` 必须从 `@/utils/feedback` 导入，**禁止** `import ... from 'element-plus'`（根 barrel 会把整包 944KB 拖进产物）。新增用到的函数式组件时，记得在 `main.ts` 补它的 `style/css`。
12. **列表页四条状态分支缺一不可**：`loading`（用 `AppSkeleton`）/ `error`（`ErrorState`）/ `empty`（文案）/ `content`。骨架不要用 `el-skeleton` 的文字条，形状对不上会跳版。
13. **图片必须走 `uploadImage()` 上传**（内部先 `compressImage()` 再发 multipart）：它会按 `maxEdge` 缩放并转 WebP，异常时自动退回原图。**不要**直接 `xhr`/`fetch` 传原始 `File`。压缩后文件名后缀会跟着实际编码变（`.webp`），因为后端校验扩展名与文件头魔数一致。
14. **帖子编辑只改 `content` / `images`**：`PUT /posts/{id}` 不接受 `score` / `dish_id`。改评分会连带影响菜品均分，那是"重新表态"，必须走发帖的 upsert。请求体用 `model_fields_set` 区分"没传"与"传 null"——没传就保持原样，传 null 才清空。
15. **删评论要回减 `comment_count`**：权限是"本人或管理员"，评论不属于该帖按 404（不暴露别处的评论 id）。回减用 `CASE WHEN comment_count > 0`——该列是 unsigned，直接 `-1` 在计数为 0 时会报 out of range。删完要 `hot_service.invalidate()`，因为热榜权重是评论×2。
16. **高分榜必须带"最少评价人数"门槛**：只按均分排会让"一个人打 5 星"的菜霸榜（种子数据里就有 5.0 分但只有 1 人评的菜）。默认 `min_rating=4` + `min_count=2`，两个条件同时生效。另：`/dishes/top` 这类静态路径必须注册在 `/dishes/{id}` **之前**，否则会被路径参数匹配成 422。
17. **随机抽菜（`/dishes/random`）由后端抽，不是前端从榜单里随机**：候选池、回退、去重都在服务端，前端只负责演出。规则固定为"高分池优先，池空退回全部上架菜品"，`exclude_id` 保证「换一个」不原地重复；返回 `pool_size`，前端据此在只剩一道时禁用「换一个」。**不要**改成前端拿 `/dishes/top` 再 `Math.random()`：高分池为空时前端抽不出东西（它拿不到"回退到全部在售"那份池子），也拿不到候选池大小。
18. **关注流 `sort=following` 的三个硬约定**：① 必须登录，匿名返回 40101（不要返回空列表，否则前端分不清"没登录"和"没关注人"）；② 只含我关注的人，**不含我自己**；③ 过滤用 `Post.user_id.in_(select(Follow.following_id)...)`，不要 join `follows`（帖子对关注没有多对多，join 还得 distinct）。前端未登录时**不发请求**，直接渲染登录引导；空态按 `following_count` 分"没关注人"和"关注的人没发帖"两套文案。
19. **想吃清单（`wants`）只是标记，别把它当收藏夹或评分**：不影响 `avg_rating` / `rating_count`；下架菜品拒绝加入，但清单里已有的下架菜**保留并标「已下架」**，抽签时排除。三条联动必须保留：① `/dishes/random?source=wants` 只在清单里抽，**池子空就 404，不回退到全站**（用户自己挑的池子要尊重）；② `POST /posts` 成功后自动 `delete wants where user_id, dish_id`（吃过就不算想吃）；③ 管理员删菜品时先清 `wants`，**不要**让想吃记录变成 409 的删除阻碍。菜品详情的 `want_count` / `is_wanted` 只在 `with_want=True` 时计算，后台列表不要跟着逐条 COUNT。
20. **后台概览（`/admin/overview`）只读、现算，不建统计表**：所有数字都是查询时聚合，"今日"按**服务器本地时间** 0 点切（不要用 UTC，管理员看的是自己的今天），近 7 天趋势在 Python 里补零（SQL 只分组，别写递归日期表）。新增指标时优先复用 `admin_service._count()`，别为了一两个数字引入缓存层或定时任务。前端柱子高度用 `max(4%, 实际比例)`，全为 0 时也要有底座。
21. **破坏性操作必须二次确认**：删帖（本人或管理员）、删食堂/商家/菜品都要走 `ElMessageBox.confirm`（`type: 'warning'`），文案要点明「不可恢复」和「会连带删掉什么」。新增任何删除入口沿用同一写法，别做"点一下就删"的按钮——前台帖子卡片曾经就是这样。
22. **看图用自写的 `ImageViewer`，不要引 `el-image-viewer`**：那个组件要额外带样式和 popper 依赖，而帖子列表每张卡片都会挂预览。**列表里点图 = 进帖子详情，详情页点图 = 大图**（`PostCard` 用 `detail` 区分），别把列表的主点击区域改成看图。SVG 占位图允许放大到 `min(88vw, 860px)`，位图保持原尺寸（放大只会糊）。


