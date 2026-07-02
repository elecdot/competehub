# 大学生竞赛信息智能筛选与推荐系统模块划分与分工

## 一、说明

本文档用于课程作业中的模块划分、接口说明和小组成员分工。小组成员暂以 `a`、`b`、`c`、`d`、`e`、`f` 作为占位姓名，后续可替换为真实姓名。

分工原则：

- 六位成员均覆盖核心业务或支撑模块，尽量保持工作量均衡。
- 每个模块设置一名主负责人，子模块可由同一负责人或协作成员承担。
- 接口包括前端页面入口、后端 REST API、后台管理入口和内部服务接口，具体实现可在后续开发任务中细化。

## 二、成员分工总览

| 成员 | 主要负责模块 | 协作模块 | 工作重点 |
|---|---|---|---|
| a | M1 用户与画像管理模块 | M5 提醒偏好 | 注册登录、用户画像、账号状态 |
| b | M2 赛事信息录入与审核模块 | M8 审计日志 | 赛事录入、审核、状态流转 |
| c | M3 搜索筛选与展示模块 | M6 推荐排序 | 列表查询、筛选、分页、排序 |
| d | M4 赛事详情与价值说明模块 | M2 赛事字段规范 | 详情页、适配标签、官方通道 |
| e | M5 收藏订阅、提醒与日历模块 | M1 用户偏好 | 收藏订阅、提醒生成、日历 |
| f | M6 推荐模块、M7 内容增强模块、M8 后台运营模块 | M3/M4 数据展示 | 规则推荐、资料沉淀、后台统计 |

## 三、模块详细划分

### 模块 M1：用户与画像管理模块

功能：提供用户注册登录、账号状态管理、学生画像维护和推荐偏好维护能力，为个性化筛选、推荐和订阅提醒提供基础数据。

接口：

- 页面接口：注册页、登录页、个人中心、学生画像编辑页。
- API 接口：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/me`、`PATCH /api/v1/me/profile`。
- 数据接口：`users`、`student_profiles`、`reminder_settings`。

负责人：a

#### 子模块 M1.1：注册与登录

功能：支持学生通过学号、邮箱或手机号注册登录，生成登录状态，并处理账号禁用、验证码错误、密码错误等异常。

接口：

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/me`

负责人：a

#### 子模块 M1.2：学生画像维护

功能：维护专业、年级、学院、兴趣方向、竞赛经历和目标偏好，用于筛选默认项和推荐规则计算。

接口：

- 页面接口：个人中心、画像编辑表单。
- API 接口：`GET /api/v1/me/profile`、`PATCH /api/v1/me/profile`。
- 数据接口：`student_profiles`。

负责人：a

#### 子模块 M1.3：推荐与提醒偏好

功能：维护关注类别、屏蔽类别、默认提前提醒天数、站内消息开关等偏好配置。

接口：

- API 接口：`GET /api/v1/me/preferences`、`PATCH /api/v1/me/preferences`。
- 数据接口：`student_profiles`、`reminder_settings`。

负责人：a；协作人：e

### 模块 M2：赛事信息录入、审核与状态管理模块

功能：支持管理员从可信来源人工录入赛事信息，完成审核发布、驳回、下架、归档、取消和过期状态维护。

接口：

- 页面接口：后台赛事列表、赛事录入页、赛事编辑页、待审核列表、审核详情页。
- API 接口：`POST /api/v1/admin/competitions`、`PATCH /api/v1/admin/competitions/{id}`、`POST /api/v1/admin/competitions/{id}/submit_review`、`POST /api/v1/admin/competitions/{id}/review`、`PATCH /api/v1/admin/competitions/{id}/status`。
- 数据接口：`competitions`、`competition_time_nodes`、`competition_tags`、`review_records`、`audit_logs`。

负责人：b

#### 子模块 M2.1：赛事人工录入

功能：录入赛事标题、来源、主办方、类别、时间节点、报名条件、官方链接、附件和适配信息。

接口：

- 页面接口：后台赛事创建表单。
- API 接口：`POST /api/v1/admin/competitions`。
- 数据接口：`competitions`、`competition_time_nodes`、`competition_tag_links`。

负责人：b

#### 子模块 M2.2：赛事审核发布

功能：审核待发布赛事，支持通过、驳回、退回修改，并记录审核意见。

接口：

- 页面接口：待审核列表、审核详情页。
- API 接口：`GET /api/v1/admin/reviews`、`POST /api/v1/admin/competitions/{id}/review`。
- 数据接口：`review_records`、`audit_logs`。

负责人：b

#### 子模块 M2.3：赛事状态管理

功能：维护赛事草稿、待审核、已发布、已驳回、已下架、已归档、已取消、已过期等状态。

接口：

- API 接口：`PATCH /api/v1/admin/competitions/{id}/status`。
- 内部服务接口：赛事状态变更服务、提醒取消/重算服务。
- 数据接口：`competitions`、`reminders`、`audit_logs`。

负责人：b；协作人：e

### 模块 M3：搜索筛选与列表展示模块

功能：为学生和访客提供赛事关键词搜索、多维筛选、排序、分页和列表展示能力。

接口：

- 页面接口：赛事列表页、搜索框、筛选栏、排序控件、分页控件。
- API 接口：`GET /api/v1/competitions`。
- 数据接口：`competitions`、`competition_time_nodes`、`competition_tags`。

负责人：c

#### 子模块 M3.1：关键词搜索

功能：支持按赛事名称、简称、主办方、类别和正文摘要检索赛事。

接口：

- API 接口：`GET /api/v1/competitions?keyword=...`。
- 内部服务接口：赛事查询服务、搜索条件解析器。

负责人：c

#### 子模块 M3.2：多维筛选

功能：支持按专业、年级、赛事类别、参考标签、报名状态、截止日期、参赛形式组合筛选。

接口：

- API 接口：`GET /api/v1/competitions?category=...&grade=...&major=...`。
- 数据接口：基础字典配置、赛事适配字段。

负责人：c

#### 子模块 M3.3：排序与分页

功能：支持按截止时间、发布时间、推荐度和热度排序，支持分页或加载更多。

接口：

- API 接口：`GET /api/v1/competitions?sort=deadline&page=1&page_size=20`。
- 内部服务接口：排序规则服务、分页结果封装。

负责人：c；协作人：f

### 模块 M4：赛事详情、适配标签与官方通道模块

功能：展示赛事详情、来源标识、时间节点、报名条件、适配标签、价值依据和官方链接跳转。

接口：

- 页面接口：赛事详情页、官方报名入口、附件入口、收藏订阅入口。
- API 接口：`GET /api/v1/competitions/{id}`、`POST /api/v1/competitions/{id}/outbound_clicks`。
- 数据接口：`competitions`、`competition_time_nodes`、`competition_tags`、跳转统计记录。

负责人：d

#### 子模块 M4.1：详情展示

功能：展示赛事简介、报名条件、赛程安排、材料要求、来源、更新时间和状态提示。

接口：

- API 接口：`GET /api/v1/competitions/{id}`。
- 页面接口：详情信息区、时间节点区、状态提示区。

负责人：d

#### 子模块 M4.2：适配标签与价值依据说明

功能：展示参考标签、适合专业、适合年级、主办单位、认可信息和“仅作参考”说明。

接口：

- 数据接口：`competition_tags`、`competition_tag_links`、`competitions.value_notes`。
- 内部服务接口：标签展示服务、适配说明生成服务。

负责人：d；协作人：c

#### 子模块 M4.3：官方通道跳转

功能：提供官方报名、通知原文和附件下载入口，并记录跳转行为用于统计。

接口：

- API 接口：`POST /api/v1/competitions/{id}/outbound_clicks`。
- 页面接口：官方通道按钮组。

负责人：d；协作人：f

### 模块 M5：收藏订阅、站内提醒与个人赛事日历模块

功能：支持学生收藏、订阅赛事，按关键时间节点生成站内提醒，并在个人日历中集中展示。

接口：

- 页面接口：收藏按钮、订阅按钮、我的收藏、我的订阅、消息中心、个人赛事日历。
- API 接口：`POST /api/v1/competitions/{id}/favorite`、`POST /api/v1/competitions/{id}/subscribe`、`GET /api/v1/me/calendar`、`GET /api/v1/me/messages`、`POST /api/v1/me/messages/{id}/read`。
- 数据接口：`favorites`、`subscriptions`、`reminder_settings`、`reminders`、`messages`。

负责人：e

#### 子模块 M5.1：收藏与订阅

功能：创建、取消和查询收藏订阅记录，并保证列表页、详情页和个人中心状态一致。

接口：

- API 接口：`POST /api/v1/competitions/{id}/favorite`、`DELETE /api/v1/competitions/{id}/favorite`、`POST /api/v1/competitions/{id}/subscribe`、`DELETE /api/v1/competitions/{id}/subscribe`。
- 数据接口：`favorites`、`subscriptions`。

负责人：e

#### 子模块 M5.2：站内提醒

功能：基于订阅记录、时间节点和提醒配置生成待发送提醒，并在触发后创建站内消息。

接口：

- API 接口：`GET /api/v1/me/messages`、`POST /api/v1/me/messages/{id}/read`。
- 内部任务接口：`competehub.reminders.dispatch_due`。
- 数据接口：`reminders`、`messages`。

负责人：e

#### 子模块 M5.3：个人赛事日历

功能：按月、周或列表展示已订阅赛事的报名、提交、比赛等关键节点。

接口：

- API 接口：`GET /api/v1/me/calendar`。
- 页面接口：日历视图、节点详情入口。

负责人：e；协作人：a

### 模块 M6：规则推荐与推荐理由模块

功能：基于学生画像、赛事标签、适配专业、适配年级、截止时间和配置权重生成规则推荐，并展示推荐理由。

接口：

- 页面接口：推荐赛事页、列表推荐区、推荐理由标签。
- API 接口：`GET /api/v1/recommendations`。
- 数据接口：`student_profiles`、`competitions`、`competition_tags`、`recommendation_rules`。

负责人：f

#### 子模块 M6.1：规则推荐计算

功能：读取用户画像和赛事配置，根据专业匹配、兴趣匹配、时间紧迫度、参考标签等规则生成推荐列表。

接口：

- API 接口：`GET /api/v1/recommendations`。
- 内部服务接口：推荐规则计算服务、推荐排序服务。

负责人：f；协作人：c

#### 子模块 M6.2：推荐理由展示

功能：为推荐结果生成可解释理由，例如“与你的专业匹配”“适合当前年级”“报名截止较近”。

接口：

- 数据接口：`recommendation_rules.reason_template`。
- 页面接口：推荐理由标签组件。

负责人：f

#### 子模块 M6.3：推荐偏好调整

功能：支持用户调整关注方向、屏蔽不感兴趣类别，并影响后续推荐结果。

接口：

- API 接口：`PATCH /api/v1/me/preferences`。
- 数据接口：`student_profiles.interest_tags`、`student_profiles.blocked_tags`。

负责人：f；协作人：a

### 模块 M7：交流论坛、资料沉淀与复盘模块

功能：作为增强能力保留，支持历届资料归档、组队交流、认证答疑和赛后复盘，形成赛事经验沉淀。

接口：

- 页面接口：资料库、资料详情、组队帖、认证答疑、复盘记录。
- API 接口：后续可扩展为 `/api/v1/materials`、`/api/v1/team_posts`、`/api/v1/certifications`、`/api/v1/reviews`。
- 数据接口：复用 `users`、`competitions`、`review_records`、`audit_logs`，后续新增资料和帖子表。

负责人：f

#### 子模块 M7.1：资料归档

功能：归档往届通知、优秀作品、经验材料、常见问题和复盘资料，并关联赛事或类别。

接口：

- API 接口：`POST /api/v1/admin/materials`、`GET /api/v1/materials`。
- 数据接口：资料记录表、附件元数据、赛事关联关系。

负责人：f

#### 子模块 M7.2：组队交流

功能：支持围绕指定赛事发布组队需求，说明技能要求、人数、联系方式和截止时间。

接口：

- API 接口：`POST /api/v1/team_posts`、`GET /api/v1/team_posts`。
- 页面接口：组队列表、组队详情、发布表单。

负责人：f；协作人：e

#### 子模块 M7.3：认证答疑

功能：参加过竞赛或获奖用户可提交认证申请，认证通过后以认证身份答疑。

接口：

- API 接口：`POST /api/v1/certifications`、`POST /api/v1/admin/certifications/{id}/review`。
- 数据接口：认证申请记录、审核记录。

负责人：f；协作人：b

#### 子模块 M7.4：赛后复盘

功能：学生或教师赛后提交复盘记录，总结参赛过程、问题和经验。

接口：

- API 接口：`POST /api/v1/competition_reviews`、`GET /api/v1/competition_reviews`。
- 页面接口：复盘编辑页、复盘详情页。

负责人：a；协作人：f

### 模块 M8：后台运营、配置与统计模块

功能：支持管理员进行用户权限管理、基础配置维护、内容审核、操作日志查询和运营统计。

接口：

- 页面接口：后台首页、用户管理、基础配置、内容审核、操作日志、统计概览。
- API 接口：`GET /api/v1/admin/users`、`PATCH /api/v1/admin/users/{id}`、`GET /api/v1/admin/configs`、`PATCH /api/v1/admin/configs/{key}`、`GET /api/v1/admin/audit_logs`、`GET /api/v1/admin/stats`。
- 数据接口：`users`、`system_configs`、`recommendation_rules`、`review_records`、`audit_logs`。

负责人：f；协作人：b

#### 子模块 M8.1：用户与权限管理

功能：管理员查看用户列表，启用或禁用账号，调整角色权限。

接口：

- API 接口：`GET /api/v1/admin/users`、`PATCH /api/v1/admin/users/{id}`。
- 数据接口：`users`、`audit_logs`。

负责人：f

#### 子模块 M8.2：基础配置管理

功能：维护赛事类别、参考标签、适合专业、适合年级、推荐权重和站内消息模板。

接口：

- API 接口：`GET /api/v1/admin/configs`、`PATCH /api/v1/admin/configs/{key}`。
- 数据接口：`system_configs`、`competition_tags`、`recommendation_rules`。

负责人：f；协作人：d

#### 子模块 M8.3：内容审核与审计日志

功能：审核赛事、资料、认证申请和用户反馈，并记录关键后台操作。

接口：

- API 接口：`GET /api/v1/admin/reviews`、`POST /api/v1/admin/reviews/{id}/handle`、`GET /api/v1/admin/audit_logs`。
- 数据接口：`review_records`、`audit_logs`。

负责人：b；协作人：f

#### 子模块 M8.4：统计分析

功能：统计访问量、搜索量、收藏量、订阅量、官方通道跳转量和推荐点击量。

接口：

- API 接口：`GET /api/v1/admin/stats`。
- 数据接口：行为日志、收藏订阅记录、跳转记录、推荐点击记录。

负责人：f；协作人：c
