# CompeteHub Tech Spec

## 一、目标与边界

本文档定义 CompeteHub 的长期技术结构、核心数据模型、服务边界和工程规范。它承接 `docs/PRD.zh.md` 中稳定的产品语义，但不把 PRD 当作逐项严格验收合同；后续开发任务和测试用例负责阶段性验收，本文档负责保持工程方向一致。

当前 P1 每个部署只属于一个配置确定的高校，不实现多租户隔离。学号、学院、管理员、字典和校级治理均在该部署边界内解释；外部赛事来源不改变用户所属边界。

阶段性架构选择、取舍原因和可被未来决策替换的内容记录在 `docs/adr/`。当前初始化技术决策见 `docs/adr/0001-initial-application-architecture.md`。

## 二、架构总览

系统采用前后端分离的单仓 monorepo：

```text
apps/
  web/                 # Vue 3 frontend
  api/                 # Flask backend API
docs/                  # Product and engineering documentation
  adr/                 # Architecture decision records
  reports/             # Course reports and generated analysis documents
infra/                 # Local infrastructure and deployment assets
scripts/               # Shared developer and agent helper scripts
```

运行时组件：

- Web：Vue 3 SPA，通过 REST API 访问后端。
- API：Flask 提供 `/api/v1` HTTP API，负责认证、业务规则和数据访问。
- Database：PostgreSQL 作为核心业务数据源。
- Redis：用于缓存、限流、Celery broker 和短期运行状态，不作为核心业务事实来源。
- Worker：Celery worker 执行提醒生成、赛事过期标记、后续半自动采集候选等异步任务。
- Identity Delivery Adapter：通过供应商无关接口发送账号验证消息。P1 可配置 SMTP 邮件发送方；它不是赛事提醒渠道，也不要求绑定特定邮件 SaaS。

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
- `docs/reports/README.md`：说明课程报告、调研材料和生成型文档的归档规则。
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

该脚本负责设置 workspace-safe 环境变量和缓存目录，例如 `XDG_CACHE_HOME`、
`TMPDIR`、`UV_CACHE_DIR`、`PRE_COMMIT_HOME`、`RUFF_CACHE_DIR` 和 npm cache。
它不接管用户配置目录，也不隐式选择 Python 项目；需要进入后端 uv 环境时必须
显式写出项目路径，例如：

```bash
./scripts/agent-env.sh uv run --project apps/api <command>
```

`justfile` 中的 Python 命令应优先通过该脚本封装，避免不同环境下出现全局缓存
或临时目录权限问题。

## 四、技术栈边界

### 4.1 Frontend

- Framework：Vue 3
- Build Tool：Vite
- Language：TypeScript
- Router：Vue Router
- State：Pinia
- HTTP Client：Axios，通过 `src/api/` 中的共享 client 和领域 API wrapper 统一 base URL、超时、凭据和错误处理。
- UI：Ant Design Vue，见 `docs/adr/0008-ant-design-vue-ui-library.md`；使用规范写入 `apps/web/README.md`，不得混用第二套通用 UI 组件库。
- Calendar：个人赛事日历使用 FullCalendar 的 Vue 3 开源标准能力实现月、周和列表视图；按锁定版本采用对应的标准 view 模块，不引入 premium resource/scheduler 功能，也不手写日期网格算法。

### 4.2 Backend

- Framework：Flask
- App Structure：application factory + Blueprints
- ORM：SQLAlchemy 2.x
- Migration：Flask-Migrate，底层使用 Alembic，见 `docs/adr/0002-initial-framework-supporting-choices.md`。
- Validation / Serialization：Marshmallow，见 `docs/adr/0002-initial-framework-supporting-choices.md` 和 `apps/api/README.md`。
- Auth：Flask Cookie Session，见 `docs/adr/0009-flask-cookie-session-auth.md`；避免将 token 存入 `localStorage`。
- Task Queue：Celery + Redis

### 4.3 Infrastructure

- PostgreSQL：核心关系型数据。
- Redis：缓存、限流、任务 broker。
- Docker Compose：本地启动 PostgreSQL、Redis 和可选 worker。
- Environment：`.env.example` 记录必需环境变量，真实 `.env` 不提交。

## 五、后端架构

### 5.1 包结构

`apps/api` 使用稳定 Flask 包结构：

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
- 个人赛事日历：桌面默认月视图、移动端默认列表视图，可切换月/周/列表并在当前设备保留选择；突出 `primary`、当前阶段和最近节点，保留成对标签和同日多节点的紧凑展开。
- 消息中心：全局消息图标与未读徽标，页面提供全部/未读标签、四类消息筛选、分页、单条已读和全部已读。使用紧凑列表而非卡片嵌套，目标不可访问时保留历史快照并禁用跳转。
- 个人画像。

管理端页面：

- 赛事管理：按系列、届次、生命周期和修订状态筛选，进入编辑、审核或状态维护。
- 赛事录入与编辑：结构化来源与发布字段、阶段、成对节点、重点级别、完整度反馈、草稿和提交操作。
- 待审核赛事：提交者和来源事实、公开/候选修订差异、提醒影响摘要，以及通过、驳回和退回意见。
- 状态维护：取消、归档、过期和紧急下架，操作前展示公开/订阅/提醒影响并收集必填原因。
- 基础配置。
- 用户与权限。
- 治理首页：只展示待办数量、推荐配置异常和少量关键摘要，详细证据进入对应标签页。
- 审核记录：按目标类型、状态、提交者和时间筛选赛事修订与推荐规则集的不可变决定，查看差异、影响、意见和决定时间。
- 操作审计：按操作者、受控动作、目标、结果和日期筛选不可变事件，只展示动作级允许字段。
- 基础统计：只读展示当前发布/待审、有效收藏/订阅、消息投递状态，以及 7/30 日外链和推荐曝光/点击计数；每项显示口径、`as_of`、时区和 best-effort 限制。

### 6.3 状态管理

Pinia stores：

- `auth_store`：登录状态、当前用户、角色和受控 capability 发现。
- `profile_store`：学生画像和推荐偏好。
- `competition_filter_store`：列表筛选条件、排序和分页。
- `dictionary_store`：赛事类别、标签、专业、年级等基础字典。
- `notification_store`：未读消息数、消息列表、已读状态。

前端不得以隐藏按钮替代后端权限控制；所有权限判断必须由后端兜底。

## 七、数据模型

### 7.1 核心表

首批核心表：

- `users`：账号、角色、状态和登录标识。
- `user_identities`：类型化学号、邮箱和手机号标识及其规范化、验证状态。
- `identity_verification_challenges`：账号标识的短期验证挑战，只保存验证码哈希、过期和消费状态。
- `verification_delivery_outbox`：与 challenge 同事务提交的邮箱验证投递任务；只保存可由应用密钥派生验证码的随机 nonce，并在投递或丢弃后清除。
- `student_profiles`：专业、年级、兴趣方向、竞赛经历和目标偏好。
- `competition_series`：赛事跨届稳定身份，由管理员根据来源事实确认。
- `competitions`：一次具体赛事届次的身份、生命周期状态和当前公开修订指针。
- `competition_revisions`：赛事届次的编号内容版本；已提交和已审核快照不可变。替换修订保存 `base_revision_id`，每届次通过 partial unique constraint 最多一个 `draft`/`pending_review` 进行中修订，审批锁定届次并拒绝 stale baseline。
- `competition_stages`：赛事届次中的有序阶段或轮次，用于分组和校验成对时间节点。
- `competition_time_nodes`：报名截止、作品提交、比赛开始等不可变节点快照；
  snapshot ID 精确引用一个赛事修订中的行，届次内稳定的
  `logical_node_key` 用于跨修订对齐，`node_revision` 随审核通过的改期递增。
- `competition_tags`：参考标签和适配标签。
- `competition_tag_links`：不可变赛事修订与受控标签关系；公开读取只解析当前 `published_revision_id` 的标签快照。
- `outbound_click_events`：隐私最小化的外链原始点击事件，保留 90 天。
- `outbound_click_daily_stats`：按上海产品日历日期和受控维度聚合的外链点击次数。
- `favorites`：收藏记录。
- `subscriptions`：订阅记录和订阅状态。
- `reminder_settings`：用户提醒偏好。
- `reminders`：待发送和已发送提醒。
- `messages`：站内消息。
- `review_records`：赛事修订、推荐规则集、资料和认证的不可变审核决定、差异与影响快照。
- `audit_logs`：使用动作级字段白名单的不可变后台和系统操作事件。
- `recommendation_rule_sets`：版本化推荐规则集及草稿、审核、激活和退役事实。
- `recommendation_rules`：从属于一个规则集版本的受控规则、结构化条件、内部权重和理由模板。
- `recommendation_request_items`：推荐响应中每个返回项及其可选曝光/点击时间的隐私最小化 90 天快照。
- `recommendation_daily_stats`：按事件发生的上海产品日历日期、规则版本、模式、位置、登录状态类别和赛事聚合的 item-level 曝光/点击总量，每个 request item 对每类事件最多计一次。
- `recommendation_reason_daily_stats`：在相同维度上增加理由代码的非加总归因计数；多理由 item 可进入多个理由行，理由行不得相加为总体。
- `system_configs`：消息模板、权重等通用配置。

### 7.2 状态枚举

赛事届次生命周期状态：

- `unpublished`
- `published`
- `offline`
- `archived`
- `cancelled`
- `expired`

赛事修订状态：

- `draft`
- `pending_review`
- `approved`
- `rejected`
- `returned`

提醒状态：

- `pending`
- `sent`
- `cancelled`
- `failed`

消息阅读状态：

- `unread`
- `read`

审核决定状态：

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
2. Celery beat 周期扫描 `status = pending` 且 `due_at <= now` 的提醒；独立重试任务把已到 `next_attempt_at` 的可重试 `failed` 记录先转回 `pending`。
3. Worker 幂等创建 `messages`。
4. 成功后将提醒状态更新为 `sent`；每次实际投递递增 `attempt_count`。瞬时失败写入受控 `last_error_code`、`failed_at` 和下一次重试时间，永久失败或耗尽重试后保持 `failed` 且不再安排时间。
5. 赛事取消、下架或节点删除时，service 取消未发送提醒。归档/过期仅在不存在未来节点时允许，并在状态事务中取消任何异常残留的未发送提醒；它们保留历史订阅和过去日历节点，不产生消息。
6. 同届节点事实变化时保留 `logical_node_key`、创建新的不可变 snapshot ID；在提交时由服务端相对基线冻结 `node_revision`。新节点修订取消旧修订的未发送提醒并重建未来计划；未变节点保持修订号并原地刷新 pending plan 的 snapshot FK 和文案，已发送提醒不可变。
7. 每个批准修订按“订阅者 + 批准修订事件”最多幂等生成一条赛事时间变更汇总消息，仅覆盖发生时刻、所选节点增删或所选节点类型变化。阶段、重点级别、描述、标题等展示修正只刷新当前内容；已过去的普通触发时间不补发伪准时提醒。
8. 首次订阅请求必须显式携带 `reminder_enabled`；开启时同时携带 `0–30` 的单一提前天数和非空受控节点类型。全局默认只用于前端确认面板预填，后端不得在字段缺失时推断同意。
9. 关闭单项提醒只取消该订阅的未发送计划，关闭全局提醒取消用户全部未发送计划；两者均保留订阅和日历节点。重新开启时只重建未来有效计划。
10. `reminder_settings` 是全局开关、默认提前天数和默认节点类型的唯一事实来源；`student_profiles` 不重复存储提醒字段。
11. `reminder_due`、`competition_time_changed`、`competition_cancelled` 和 `competition_offline` 使用“用户 + 领域事件”幂等键创建不可变消息快照。用户主动取消或关闭提醒不创建消息。
12. 周期清理任务删除创建满 365 天的消息，不区分已读状态；账号删除使用统一账号数据清理流程。提醒的 `sent` 状态与消息的已读状态分别维护。

### 8.3 推荐任务

规则推荐可同步计算并缓存短时间结果。个性化计算只读取单一 `active` 推荐规则集，缓存键必须包含规则集版本；响应返回版本和可追溯理由，不返回内部得分。无激活版本时降级为通用可行动结果并暴露管理配置异常，不使用 service 常量。候选预览仅使用合成画像和选定公开赛事，不读取任意真实学生画像，也不持久化结果。

每次推荐响应为返回项创建随机 request ID 下的 90 天服务端快照。前端实际渲染后批量尽力记录曝光，从推荐页导航详情时尽力记录点击；统计失败不影响展示或导航。事件 API 只接受 request ID、事件类型和赛事 ID，从服务端快照读取位置、模式、规则版本、理由代码和登录状态类别。曝光和点击分别按 request item 幂等，点击要求已有曝光。原始行不保存用户、账号、画像、IP、User-Agent 或跨 request 标识，也不用于自动个性化。

周期任务在删除超过 90 天的原始行前写入两类幂等聚合：曝光使用 `impressed_at` 的 `Asia/Shanghai` 日期，点击使用 `clicked_at` 的日期，因此同一 request item 可在不同日期贡献两类事件。item-level 总量按事件日期、规则版本、模式、位置、登录状态类别和赛事计数，每个 request item 对每类事件最多一次；reason-level 归因在相同维度增加去重后的理由代码，一个多理由 item 可进入多个归因行。管理端 7/30 日总体曝光、点击及比值只读取 item-level 总量；该比值是窗口内点击事件除以窗口内曝光事件的 event-period interaction ratio，不是按曝光日期分 cohort 的转化率。理由行明确标注为不可加总的归因而非因果。若后续数据量增长，可预计算推荐结果，但版本和理由仍必须可追溯。

### 8.4 外链点击统计

- 外链使用真实 HTTP(S) `href` 直接打开，设置 `noopener/noreferrer`；前端通过 `sendBeacon` 或 keepalive 请求尽力记录，失败不得阻断跳转。
- API 只接受受控目标类型和来源页面，从当前可查看公开修订解析实际链接，不接受任意客户端 URL，也不做代理或重定向。
- 原始事件只保存赛事届次、公开修订、目标类型、来源页面、登录状态类别和服务端时间；用户 ID、账号标识、IP、User-Agent 和跨日访客标识不得进入分析表。
- Redis 可使用短期请求来源键做接口限速，但不得作为点击事实来源或持久访客标识。
- 周期任务按 `Asia/Shanghai` 日期幂等生成日聚合，并删除超过 90 天的原始事件。管理端指标明确标为记录点击次数，不展示独立人数或报名转化。

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

### 9.2 日期与时间约定

- 数据库时间字段保存带时区的时间点，并统一归一为 UTC。
- API 时间戳响应使用 UTC；带偏移输入转换为对应 UTC 时间点。
- 不带偏移的管理员时间输入按 `Asia/Shanghai` 解释。
- 学生端日期展示和日期型筛选按 `Asia/Shanghai` 产品日历日解释，查询时将上海午夜边界转换为 UTC。
- 具体决策与替代方案见 `docs/adr/0012-utc-instants-shanghai-calendar.md`。

### 9.3 关键接口组

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
- `POST /api/v1/recommendation_events`
- `GET /api/v1/admin/recommendation_rule_sets`
- `POST /api/v1/admin/recommendation_rule_sets`
- `POST /api/v1/admin/recommendation_rule_sets/{id}/preview`
- `POST /api/v1/admin/recommendation_rule_sets/{id}/submit_review`
- `POST /api/v1/admin/recommendation_rule_sets/{id}/review`
- `POST /api/v1/admin/competitions`
- `GET /api/v1/admin/competition_series`
- `POST /api/v1/admin/competition_series`
- `GET /api/v1/admin/competitions`
- `GET /api/v1/admin/competitions/{id}`
- `GET /api/v1/admin/competition_revisions`
- `GET /api/v1/admin/competition_revisions/{revision_id}`
- `POST /api/v1/admin/competitions/{id}/revisions`
- `PATCH /api/v1/admin/competition_revisions/{revision_id}`
- `POST /api/v1/admin/competition_revisions/{revision_id}/submit_review`
- `POST /api/v1/admin/competition_revisions/{revision_id}/review`
- `PATCH /api/v1/admin/competitions/{id}/status`
- `GET /api/v1/admin/reviews`
- `GET /api/v1/admin/audit_logs`
- `GET /api/v1/admin/stats`

Issue #35 implements the first-revision publication path in
`models/competition.py`, `services/competition_revisions.py`, the admin
blueprint/schemas/repositories, and `apps/web/src/pages/AdminHomePage.vue`.
The browser acceptance path in
`apps/web/e2e/competition-publication.spec.ts` uses real Cookie sessions to
move from editor submission through independent reviewer approval to student
visibility. Replacement-revision and lifecycle-maintenance expansion remains
owned by #37.

## 十、认证、权限与审计

### 10.1 角色

初始角色：

- `student`
- `admin`

未来候选角色，当前不作为正式产品角色：

- `teacher`
- `organizer`

### 10.2 权限原则

- 认证使用 Flask Cookie Session；session 只保存最小身份事实，不保存敏感业务数据。
- 账号状态使用 `pending_activation`、`active` 和 `disabled`；只有 `active` 账号可以建立 session 和写入个人业务数据。
- P1 公开注册只在 `PUBLIC_EMAIL_REGISTRATION_ENABLED=true` 且 SMTP 或等价真实邮件发送方已配置时开放邮箱入口；手机号短信注册延后，学号通过高校名册或管理员受控路径配置。
- SMTP 适配器由 `EMAIL_VERIFICATION_SENDER_DSN` 配置，支持 STARTTLS 的 `smtp://` 和隐式 TLS 的 `smtps://`；生产环境启用邮箱注册但缺少或错误配置发送方时必须启动失败。关闭公开注册时前端隐藏入口、后端返回明确的能力不可用错误。
- 测试可以注入内存发送器断言验证码流程；生产发送器不得在日志或响应中暴露验证码。注册、重发只在 HTTP 事务中写入 challenge 与 delivery outbox，SMTP 由 Celery worker 异步执行；worker 对暂时失败执行有界退避重试，并丢弃已消费或过期 challenge 的投递。
- 注册和重发的无效分支仍执行与有效分支同等级的密码/challenge hash 工作；verify 的 missing/ineligible challenge 使用固定 dummy challenge hash。登录对 unknown、pending、disabled 和 active 账号始终执行一次自适应密码验证，unknown 使用固定 dummy Argon2id hash，并在验证后统一判断账号和 identity 状态。
- 注册与验证不自动创建 session；身份验证完成后用户通过常规登录建立 session。
- 单因素密码在 NFC 规范化后必须为 15 至 128 个 Unicode 字符，允许空格、粘贴、自动填充和密码管理器，不设置字符种类组合规则，不静默截断，也不做周期性强制更换。
- 新密码必须通过仓库管理的本地常见、已泄露及上下文弱密码阻止列表；阻止列表校验不得依赖运行时在线服务。
- 新密码使用显式 Argon2id 参数 `m=19456 KiB, t=2, p=1`；登录继续验证历史 scrypt hash，并在验证成功后使用规范化密码于同一登录事务中升级到当前 Argon2id 参数。已有 Argon2id hash 通过 `check_needs_rehash()` 判定参数升级，登录失败不得修改 hash。参数必须至少达到当前 OWASP 基线，禁止依赖 Werkzeug 或其他库可能变化的默认算法参数。
- 登录失败按规范化类型化标识键和请求来源分别使用 Redis 渐进限速，所有账号状态使用一致失败响应；计数递增与首次 TTL 设置必须原子完成，不得因远程失败或运行中断永久锁定账号。
- Cookie session 只保存 `user_id`、`session_version`、`issued_at` 和 `last_activity_at`；登录前清理旧 session，所有受保护请求统一经过认证守卫并从数据库重读账号状态和版本。
- 学生 session 的空闲/绝对超时为 24 小时/7 天，管理员为 30 分钟/8 小时；活动只能延后空闲截止，不能延后绝对截止。服务端在路由执行前校验，失效后清除 Cookie 并返回统一 `401`。为避免同一页面并发请求反复重签 Cookie 和覆盖较新的活动时间，`last_activity_at` 的 Cookie 写入按一分钟窗口合并；超时、账号状态和版本仍逐请求校验。
- 修改账号角色或 capability、禁用账号、确认凭据泄露或终止全部会话时原子递增 `users.session_version`；既有设备下一请求即失效。普通退出只清理当前浏览器，P1 允许多设备并发且不建设设备会话列表或“记住我”选项。
- Cookie 应设置 `HttpOnly`、`SameSite=Lax`，生产环境设置 `Secure`。
- 所有修改接口必须使用 POST、PATCH 或 DELETE，不能用 GET 修改状态。
- 后台写操作应检查 `Origin` 或 `Referer`；若后续写操作范围扩大，可引入 CSRF token。
- 学生只能维护自己的画像、收藏、订阅和提醒设置。
- 画像服务统一校验部署高校的学院、专业、年级和兴趣标签字典，以及专业所属学院关系；兴趣标签去重后最多 10 个。
- `profile_status` 与 `missing_fields` 在读取时根据学院、专业、年级和至少一个兴趣标签动态计算，不在数据库保存完成布尔值。画像不完整不得阻断搜索、详情、收藏、订阅或提醒，只令推荐降级为带明确原因的通用可行动结果。
- 未登录访客只能访问公开赛事列表和详情。
- 管理员才能访问赛事录入、审核、配置、用户管理，以及审核、审计和统计治理证据；学生访问这些接口统一返回 `403`。
- `GET /me` 返回角色和受控 capability 列表供前端发现工作台入口；学生列表为空，后端不得把该响应或前端隐藏当成授权检查。
- 用户列表及角色、状态、capability 变更要求 `user_administrator`；禁止自我变更，并以事务约束保留至少一个 active 用户治理管理员。成功变更目标账号时递增其 `session_version`，记录原因和受控新旧值。
- 赛事录入、赛事审核和发布后状态维护分别使用 `competition_editor`、`competition_reviewer` 和 `competition_maintainer` 管理员权限，不新增正式用户角色；当前修订的提交者不得审核该修订，维护权限不允许编辑、审核或直接恢复公开修订。
- 推荐规则使用 `recommendation_editor` 和 `recommendation_reviewer` 管理员权限，不新增正式角色；候选规则集提交者不得审核该版本，激活必须原子退役旧版本。
- 后端必须对每个后台接口做权限检查。

### 10.3 审计

以下操作必须写入 `audit_logs`：

- 赛事创建、修改、提交审核、审核、下架、归档、取消。
- 基础配置修改。
- 用户角色、账号状态或 capability 修改。
- 内容审核和认证审核。

审核决定和审计事件写入后不可通过产品接口更新或删除。审计详情按动作使用字段白名单，不得包含密码、验证码、session、完整账号标识、用户画像内容或原始分析标识。治理统计只读并带口径、数据截至时间和时区，不提供用户级钻取。

## 十一、测试与质量门禁

项目测试模型以 `docs/testing.md` 为准。本文档只保留技术实现摘要，避免在
多个文档中重复维护同一套测试规则。

### 11.1 分层测试模型

| 层级 | 技术范围 | 当前策略 |
|---|---|---|
| Backend unit tests | services、repositories、规则推荐、状态流转、幂等规则。 | 使用 `pytest`，业务规则和回归风险较高的状态变化优先 TDD。 |
| API tests | 认证、赛事搜索、订阅提醒、后台审核、消息和权限。 | 使用 Flask test client 覆盖请求校验、响应结构、状态码和权限边界。 |
| Database / migration checks | SQLAlchemy models、迁移脚本、seed 数据、状态枚举变更。 | 涉及 schema 变化时在临时或本地数据库执行迁移；seed 数据应可复现。 |
| Integration tests | 管理员发布赛事、学生搜索订阅、提醒生成消息和日历节点。 | P1 主闭环稳定后补服务/API 集成测试；自动化前使用手工验收脚本。 |
| Frontend static checks | Vue routes、TypeScript 类型、构建产物。 | `just web-lint` 执行 `vue-tsc --noEmit`，`just web-build` 执行生产构建。 |
| Frontend component tests | 筛选、详情状态、订阅状态、消息状态。 | P1 UI 稳定后再引入 Vitest 或等价框架，并同步 `apps/web/package.json`、`justfile` 和本文档。 |
| E2E / manual acceptance | 中期和答辩演示主流程。 | `just web-e2e` 运行共享 Playwright Chromium 门禁；基础层提供确定性学生/编辑者/审核者 Cookie 会话和非空页面 smoke。后续 P1/P2 issue 增量覆盖发布、日历、推荐及治理路径；手工验收补充探索性与视觉检查。 |

### 11.2 Frontend quality gates

- Current static checks：`vue-tsc --noEmit`，通过 `just web-lint` 执行；`just web-build` 同时执行类型检查和 Vite build。
- Stage 1 lint / format：P1 页面和 stores 稳定后，引入 ESLint、`eslint-plugin-vue` 和 Prettier。
- Stage 2 unit / component tests：核心组件和 stores 稳定后，引入 Vitest 和 Vue Test Utils，覆盖工具函数、stores、赛事筛选、详情状态和消息状态。
- Stage 3 E2E tests：共享 Playwright Chromium 门禁已通过 `just web-e2e` 建立，使用隔离可重建数据库、真实登录 Cookie、确定性学生/编辑者/审核者 actor，并将未捕获页面或 console 错误视为失败。P1 赛事治理工作台增量覆盖独立管理员编辑提交、审核发布和学生端可见；日历交付时覆盖月/周/列表切换、移动端列表、同日多节点、提醒关闭但节点保留和改期刷新；P2 再覆盖推荐结果以及审核、审计、统计三个治理标签页的导航、筛选、详情和权限边界。
- 每个前端质量门禁阶段必须在同一变更中同步 `apps/web/package.json`、lockfile、`justfile` 和本文档；分阶段决策见 `docs/adr/0010-staged-frontend-quality-gates.md`。

### 11.3 TDD 与非功能验证

`docs/agents/tdd.md` 是 bug 修复和可测试行为变更的工作流；`docs/testing.md`
是项目测试层级、验收脚本和非功能验证口径的来源。实现任务应先在
`docs/testing.md` 中选择相关测试层级，再在适合自动化的行为变更中按
`docs/agents/tdd.md` 执行 red-green-refactor。

非功能验证以可落地证据为主：

- 权限安全：学生不能访问后台 API，用户不能读取或修改他人画像、订阅、提醒和消息。
- 数据一致性：赛事状态变化影响列表、详情、推荐和提醒；取消订阅会取消未来未发送提醒。
- 幂等可靠性：提醒派发重复执行不产生重复站内消息。
- 响应时间 smoke：记录种子数据规模和本地环境，验证列表、搜索和详情满足 PRD 的 3 秒目标。
- 易用性：按手工验收脚本完成学生和管理员主流程。
- 可维护性：PR 明确验证证据，文档与公开契约同步更新。

### 11.4 justfile

根 `justfile` 作为开发入口，应提供分层 recipe：顶层入口用于日常操作，组件级 recipe 用于局部开发和 CI 对齐。

```text
default
setup
doctor
check
agent
agent-uv
fmt
lint
test
build
api-dev
api-sync
api-test
api-lint
api-format
web-install
web-dev
web-e2e-install
web-e2e
web-lint
web-build
docs-build
docs-serve
infra-up
infra-down
infra-config
pre-commit
```

Python 相关命令通过 `scripts/agent-env.sh` 设置 agent-safe 环境，并显式调用
`uv run --project apps/api ...`。

## 十二、初始化实施顺序

建议按以下顺序初始化。若顺序或关键选型发生变化，应新增或更新 `docs/adr/` 中的对应 ADR，而不是把阶段性说明写入本文档：

1. 建立语义目录和各目录 README。
2. 新增或维护 `scripts/agent-env.sh`，为 `justfile` 中的工具命令提供 workspace-safe 环境。
3. 重整 `apps/api` 为 Flask package，补齐 app factory、config、extensions 和健康检查。
4. 新增 `infra/docker-compose.yml`，启动 PostgreSQL 和 Redis。
5. 建立数据库模型、迁移和基础 seed 数据。
6. 初始化 `apps/web` Vue 3 + Vite + TypeScript。
7. 打通认证、赛事列表、赛事详情和后台赛事录入的最小闭环。
8. 增加订阅、提醒、消息中心和规则推荐。
9. 补充增强能力和统计能力。

## 十三、主要技术风险

- 中文搜索：PostgreSQL 基础查询和简单关键词匹配支撑初期筛选；专用搜索服务的重新决策条件见 `docs/adr/0011-postgresql-search-first.md`。
- 提醒可靠性：必须以数据库为事实来源，并保证 worker 幂等，避免重复提醒或漏提醒。
- 权限扩展：教师和组织者不作为当前基础角色，但角色模型必须预留扩展空间。
- PRD 漂移：新增语义和流程变更应同步 PRD 与 Tech Spec；局部实现细节只需同步到对应目录 README 或任务文档。
