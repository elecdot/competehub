# CompeteHub Tech Spec

## 一、目标与边界

本文档定义 CompeteHub 的技术架构、仓库结构、核心数据模型、服务边界和初始化规范。它承接 `docs/PRD.md` 中稳定的产品语义，但不把 PRD 当作逐项严格验收合同；后续开发任务和测试用例负责阶段性验收，本文档负责保持工程方向一致。

当前基础技术栈要求为 Vue、Flask 和 Redis。由于仓库仍处于初始化阶段，现有 `apps/api` 仅视为占位，可在不破坏项目约定的前提下重整为更清晰的工程结构。

## 二、架构总览

系统采用前后端分离的单仓 monorepo：

```text
apps/
  web/                 # Vue 3 frontend
  api/                 # Flask backend API
docs/                  # Product and engineering documentation
infra/                 # Local infrastructure and deployment assets
reports/               # Course reports and generated analysis documents
scripts/               # Shared developer and agent helper scripts
```

运行时组件：

- Web：Vue 3 SPA，通过 REST API 访问后端。
- API：Flask 提供 `/api/v1` HTTP API，负责认证、业务规则和数据访问。
- Database：PostgreSQL 作为核心业务数据源。
- Redis：用于缓存、限流、Celery broker 和短期运行状态，不作为核心业务事实来源。
- Worker：Celery worker 执行提醒生成、赛事过期标记、后续半自动采集候选等异步任务。

## 三、仓库初始化规范

### 3.1 语义目录 README

每个有独立语义的目录在创建时必须同时创建 `README.md`，作为该目录的入口和局部约定所在地。README 至少说明：

- 该目录负责什么，不负责什么。
- 关键子目录和入口文件。
- 本地开发、测试或生成命令。
- 仅适用于该目录的约定。

初始目录要求：

- `apps/README.md`：说明应用分层、前后端边界和新增 app 的规则。
- `apps/web/README.md`：说明 Vue 应用结构、开发命令、路由和状态管理约定。
- `apps/api/README.md`：说明 Flask API 结构、uv 使用方式、迁移和测试命令。
- `docs/README.md`：说明产品、技术和工程文档的放置规则。
- `infra/README.md`：说明本地基础设施、Docker Compose 和环境变量约定。
- `reports/README.md`：说明课程报告、调研材料和生成型文档的归档规则。
- `scripts/README.md`：说明脚本命名、幂等性和 agent-safe 命令约定。

### 3.2 命名与路径

- 文件名遵守 `docs/CONVENTIONS.md`，使用小写英文和下划线。
- `README.md` 作为标准入口文件允许使用大写。
- 文档中的路径使用仓库相对路径，避免机器相关绝对路径。
- 后续新增语义目录时，必须在同一变更中补充对应 README。

### 3.3 uv 与 agent 环境

后端继续使用 `uv` 管理依赖，但所有 agent 可执行命令必须避免写入只读全局缓存。初始化时应新增：

```text
scripts/agent-env.sh
```

该脚本负责设置 workspace-safe cache，例如：

```bash
UV_CACHE_DIR=.cache/uv uv run --project apps/api "$@"
```

`justfile` 中的 Python 命令应优先通过该脚本封装，避免不同环境下出现 uv cache 权限问题。

## 四、技术选型

### 4.1 Frontend

- Framework：Vue 3
- Build Tool：Vite
- Language：TypeScript
- Router：Vue Router
- State：Pinia
- HTTP Client：Axios 或基于 `fetch` 的薄封装，需统一错误处理。
- UI：初始化阶段可先使用轻量组件库或自建基础组件；若后续引入组件库，应在 `apps/web/README.md` 固化使用规范。

### 4.2 Backend

- Framework：Flask
- App Structure：application factory + Blueprints
- ORM：SQLAlchemy 2.x
- Migration：Alembic 或 Flask-Migrate
- Validation / Serialization：Marshmallow 或 Pydantic，初始化时选择一种并保持一致。
- Auth：HttpOnly Cookie session 或 Cookie-based JWT，避免将 token 存入 `localStorage`。
- Task Queue：Celery + Redis

### 4.3 Infrastructure

- PostgreSQL：核心关系型数据。
- Redis：缓存、限流、任务 broker。
- Docker Compose：本地启动 PostgreSQL、Redis 和可选 worker。
- Environment：`.env.example` 记录必需环境变量，真实 `.env` 不提交。

## 五、后端架构

### 5.1 包结构

`apps/api` 应重整为稳定 Flask 包：

```text
apps/api/
  README.md
  pyproject.toml
  src/competehub_api/
    __init__.py
    app.py
    config.py
    extensions.py
    blueprints/
    models/
    repositories/
    schemas/
    services/
    tasks/
  migrations/
  tests/
```

后端包名使用 `competehub_api`，避免继续使用泛化的 `api`。

### 5.2 分层约定

请求处理遵循：

```text
routes -> schemas -> services -> repositories -> models
```

- routes：只处理 HTTP 参数、认证上下文和响应。
- schemas：负责输入校验和输出序列化。
- services：承载业务规则、状态流转和跨表操作。
- repositories：封装数据库查询，避免在路由层散落 SQLAlchemy 查询。
- models：定义数据库表、枚举和关系。
- tasks：异步任务入口，调用 services，不直接复制业务规则。

### 5.3 Blueprints

首批 Blueprints：

- `auth`：注册、登录、登出、当前用户。
- `users`：学生画像、偏好。
- `competitions`：学生端赛事列表、筛选、详情、跳转记录。
- `admin`：赛事录入、审核、状态管理、配置管理。
- `subscriptions`：收藏、订阅、个人赛事日历。
- `notifications`：站内消息、提醒设置、已读状态。
- `recommendations`：规则推荐和推荐理由。
- `audit`：操作日志查询。

所有 API 使用 `/api/v1` 前缀。

## 六、前端架构

### 6.1 应用结构

`apps/web` 建议结构：

```text
apps/web/
  README.md
  package.json
  src/
    api/
    assets/
    components/
    layouts/
    pages/
    router/
    stores/
    types/
    utils/
```

### 6.2 页面分组

学生端页面：

- 赛事列表与搜索筛选。
- 赛事详情。
- 推荐赛事。
- 我的收藏与订阅。
- 个人赛事日历。
- 消息中心。
- 个人画像。

管理端页面：

- 赛事管理。
- 赛事录入与编辑。
- 待审核赛事。
- 基础配置。
- 用户与权限。
- 审核和操作日志。
- 简单统计。

### 6.3 状态管理

Pinia stores：

- `auth_store`：登录状态、当前用户、角色。
- `profile_store`：学生画像和推荐偏好。
- `competition_filter_store`：列表筛选条件、排序和分页。
- `dictionary_store`：赛事类别、标签、专业、年级等基础字典。
- `notification_store`：未读消息数、消息列表、已读状态。

前端不得以隐藏按钮替代后端权限控制；所有权限判断必须由后端兜底。

## 七、数据模型

### 7.1 核心表

首批核心表：

- `users`：账号、角色、状态和登录标识。
- `student_profiles`：专业、年级、兴趣方向、竞赛经历和目标偏好。
- `competitions`：赛事主体信息、来源、展示状态和适配说明。
- `competition_time_nodes`：报名截止、作品提交、比赛开始等关键节点。
- `competition_tags`：参考标签和适配标签。
- `competition_tag_links`：赛事与标签关系。
- `favorites`：收藏记录。
- `subscriptions`：订阅记录和订阅状态。
- `reminder_settings`：用户提醒偏好。
- `reminders`：待发送和已发送提醒。
- `messages`：站内消息。
- `review_records`：赛事、资料和认证审核记录。
- `audit_logs`：后台操作日志。
- `recommendation_rules`：规则推荐配置。
- `system_configs`：消息模板、权重等通用配置。

### 7.2 状态枚举

赛事状态：

- `draft`
- `pending_review`
- `published`
- `rejected`
- `offline`
- `archived`
- `cancelled`
- `expired`

提醒状态：

- `pending`
- `sent`
- `read`
- `cancelled`
- `failed`

审核状态：

- `pending`
- `approved`
- `rejected`
- `returned`

状态应使用枚举或受控常量，不使用自由字符串。

## 八、Redis 与异步任务

### 8.1 Redis 使用边界

Redis 用于：

- Celery broker / result backend。
- 高频字典或赛事列表短缓存。
- 登录或接口限流计数。
- 幂等锁和短期任务状态。

Redis 不用于：

- 保存用户画像、赛事、订阅、提醒、审核记录等核心事实数据。
- 作为唯一的延迟提醒队列。

### 8.2 站内提醒任务

站内提醒以数据库为事实来源：

1. 用户订阅赛事后，API 根据赛事时间节点和提醒配置生成 `reminders`。
2. Celery beat 周期扫描 `status = pending` 且 `due_at <= now` 的提醒。
3. Worker 幂等创建 `messages`。
4. 成功后将提醒状态更新为 `sent`。
5. 赛事取消、下架或节点修改时，service 取消或重算未发送提醒。

### 8.3 推荐任务

规则推荐可同步计算并缓存短时间结果。若后续数据量增长，可将用户推荐结果异步预计算到数据库或缓存，但推荐理由仍必须可追溯到规则。

## 九、API 设计原则

### 9.1 REST 约定

- API 前缀：`/api/v1`
- 列表接口使用分页参数：`page`、`page_size`
- 筛选参数使用 query string
- 创建和更新接口使用 JSON body
- 响应统一包含数据和错误结构

示例：

```json
{
  "data": {},
  "error": null
}
```

错误示例：

```json
{
  "data": null,
  "error": {
    "code": "validation_error",
    "message": "请求参数不合法",
    "details": {}
  }
}
```

### 9.2 关键接口组

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`
- `GET /api/v1/competitions`
- `GET /api/v1/competitions/{id}`
- `POST /api/v1/competitions/{id}/favorite`
- `POST /api/v1/competitions/{id}/subscribe`
- `GET /api/v1/me/calendar`
- `GET /api/v1/me/messages`
- `POST /api/v1/me/messages/{id}/read`
- `GET /api/v1/recommendations`
- `POST /api/v1/admin/competitions`
- `POST /api/v1/admin/competitions/{id}/submit_review`
- `POST /api/v1/admin/competitions/{id}/review`
- `PATCH /api/v1/admin/competitions/{id}/status`

## 十、认证、权限与审计

### 10.1 角色

初始角色：

- `student`
- `admin`

预留角色：

- `teacher`
- `organizer`

### 10.2 权限原则

- 学生只能维护自己的画像、收藏、订阅和提醒设置。
- 未登录访客只能访问公开赛事列表和详情。
- 管理员才能访问赛事录入、审核、配置、用户管理和审计日志。
- 后端必须对每个后台接口做权限检查。

### 10.3 审计

以下操作必须写入 `audit_logs`：

- 赛事创建、修改、提交审核、审核、下架、归档、取消。
- 基础配置修改。
- 用户角色或账号状态修改。
- 内容审核和认证审核。

## 十一、测试与质量门禁

### 11.1 Backend

- Unit tests：services、repositories、规则推荐、状态流转。
- API tests：认证、赛事搜索、订阅提醒、后台审核。
- Migration tests：关键迁移可在临时数据库上执行。
- Lint / Format：Ruff。

### 11.2 Frontend

- Unit tests：工具函数、stores、关键组件。
- Component tests：赛事筛选、详情状态、消息状态。
- E2E tests：核心查赛链路、订阅提醒链路、后台审核链路。
- Lint / Format：ESLint + Prettier。

### 11.3 justfile

初始化后建议提供：

```text
api-dev
api-test
api-lint
web-dev
web-test
web-lint
db-upgrade
db-downgrade
infra-up
infra-down
pre-commit
```

Python 相关命令通过 `scripts/agent-env.sh` 封装 `uv`。

## 十二、初始化实施顺序

建议按以下顺序初始化：

1. 建立语义目录和各目录 README。
2. 新增 `scripts/agent-env.sh`，修正 `justfile` 的 uv cache 使用方式。
3. 重整 `apps/api` 为 Flask package，补齐 app factory、config、extensions 和健康检查。
4. 新增 `infra/docker-compose.yml`，启动 PostgreSQL 和 Redis。
5. 建立数据库模型、迁移和基础 seed 数据。
6. 初始化 `apps/web` Vue 3 + Vite + TypeScript。
7. 打通认证、赛事列表、赛事详情和后台赛事录入的最小闭环。
8. 增加订阅、提醒、消息中心和规则推荐。
9. 补充增强能力和统计能力。

## 十三、主要技术风险

- 中文搜索：PostgreSQL 基础查询可以支撑初期筛选，但复杂中文全文检索可能需要后续引入专用搜索服务。
- 提醒可靠性：必须以数据库为事实来源，并保证 worker 幂等，避免重复提醒或漏提醒。
- 权限扩展：教师和组织者暂不作为首批独立工作台，但角色模型必须预留扩展空间。
- PRD 漂移：新增语义和流程变更应同步 PRD 与 Tech Spec；局部实现细节只需同步到对应目录 README 或任务文档。
