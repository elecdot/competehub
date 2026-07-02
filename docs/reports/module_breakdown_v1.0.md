# 大学生竞赛信息智能筛选与推荐系统模块划分与分工

## 一、模块划分说明

本系统采用 B/S 体系结构风格，并结合 分层体系结构 与 模块化单体架构 进行概要设计。系统整体可划分为表示层、应用处理层和数据管理层：浏览器端 Vue 3 SPA 承担表示层，Flask REST API 承担应用处理层，PostgreSQL 承担数据管理层；Redis 与 Celery worker 用于支持异步提醒、过期状态更新等非即时任务。

本系统围绕大学生竞赛信息获取与跟进的核心任务链路进行模块划分。学生端主要完成“注册登录与画像维护、赛事搜索筛选、赛事详情查看、收藏订阅、提醒跟进、个性化推荐”等操作；管理员端主要完成“赛事录入、审核发布、状态维护、配置管理、审计统计”等操作。

系统功能模块划分为七个部分：

模块 M1：用户与画像管理模块
模块 M2：赛事治理模块
模块 M3：赛事发现与展示模块
模块 M4：赛事跟进模块
模块 M5：规则推荐与推荐解释模块
模块 M6：后台运营、配置与审计统计模块
模块 M7：内容沉淀与交流扩展模块

其中，M1-M6 作为当前阶段的核心交付模块，M7 作为增强扩展模块，根据开发进度实现基础原型或预留接口。

---

## 二、成员分工总览

| 成员 | 主要负责模块            | 协作模块                  | 工作重点                     |
| -- | ----------------- | --------------------- | ------------------------ |
| a  | M1 用户与画像管理模块      | M4 提醒偏好、M5 画像输入       | 注册登录、个人中心、学生画像、推荐与提醒偏好   |
| b  | M2 赛事治理模块         | M6 审计日志、M4 状态变更联动     | 赛事录入、编辑、审核发布、状态流转        |
| c  | M3 赛事发现与展示模块      | M5 推荐排序、M6 统计数据       | 搜索筛选、列表展示、分页排序、详情页、官方跳转  |
| d  | M5 规则推荐与推荐解释模块    | M1 用户画像、M3 赛事标签展示     | 推荐规则、推荐排序、推荐理由、一致性校验    |
| e  | M4 赛事跟进模块         | M1 提醒偏好、M2 状态变更       | 收藏订阅、提醒生成、消息中心、个人赛事日历    |
| f  | M6 后台运营、配置与审计统计模块 | M2 审核、M5 推荐配置、M7 扩展原型 | 用户管理、基础配置、审计日志、统计分析、测试文档 |

---

# 三、模块详细设计

>本文中的接口包括三类：页面接口表示用户或管理员可直接访问的界面入口；API 接口表示前后端或外部调用的 HTTP 接口；数据接口表示模块依赖的核心数据表或持久化对象。部分涉及后台任务的模块补充内部服务接口或任务接口。

## 模块 M1：用户与画像管理模块

功能：
提供用户注册、登录、登出、账号状态管理、学生画像维护和个性化偏好维护能力。该模块为赛事筛选、规则推荐、订阅提醒和个人中心提供基础用户数据。

接口：
页面接口：注册页、登录页、个人中心页、学生画像编辑页、偏好设置页。
API 接口：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/me`、`GET /api/v1/me/profile`、`PATCH /api/v1/me/profile`、`PATCH /api/v1/me/preferences`。
数据接口：`users`、`student_profiles`、`reminder_settings`。

负责人：a
协作人：e、d

### 子模块 M1.1：注册与登录

功能：
支持学生通过学号、邮箱或手机号注册登录。系统在注册时校验账号唯一性，在登录时校验账号状态和认证信息，并在登录成功后维护用户会话状态。

接口：
页面接口：注册表单、登录表单、登录状态提示。
API 接口：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/me`。
数据接口：`users`。

负责人：a

### 子模块 M1.2：账号状态与角色管理

功能：
维护用户基础身份信息、账号启用或禁用状态、用户角色信息。普通学生只能访问学生端功能，管理员用户可进入后台管理功能。

接口：
页面接口：个人中心基础信息区。
API 接口：`GET /api/v1/me`。
数据接口：`users`。

负责人：a
协作人：f

### 子模块 M1.3：学生画像维护

功能：
维护学生的学院、专业、年级、兴趣方向、竞赛经历和目标偏好。学生画像用于搜索默认条件、个性化推荐和统计分析。

接口：
页面接口：学生画像编辑表单、个人中心画像展示区。
API 接口：`GET /api/v1/me/profile`、`PATCH /api/v1/me/profile`。
数据接口：`student_profiles`。

负责人：a
协作人：d

### 子模块 M1.4：推荐与提醒偏好维护

功能：
维护用户关注类别、屏蔽类别、默认提前提醒天数、站内消息开关等偏好配置。该子模块为推荐模块和提醒模块提供用户侧配置。

接口：
页面接口：偏好设置页、消息提醒设置区。
API 接口：`PATCH /api/v1/me/preferences`。
数据接口：`student_profiles`、`reminder_settings`。

负责人：a
协作人：e、d

---

## 模块 M2：赛事治理模块

功能：
支持管理员从可信来源人工录入赛事信息，并完成赛事编辑、提交审核、审核发布、驳回、退回修改、下架、归档、取消和过期状态维护。该模块负责保证赛事信息来源明确、字段完整、状态可追踪。

接口：
页面接口：后台赛事列表页、赛事录入页、赛事编辑页、待审核赛事列表页、赛事审核详情页、赛事状态管理入口。
API 接口：`POST /api/v1/admin/competitions`、`PATCH /api/v1/admin/competitions/{id}`、`POST /api/v1/admin/competitions/{id}/submit_review`、`POST /api/v1/admin/competitions/{id}/review`、`PATCH /api/v1/admin/competitions/{id}/status`。
数据接口：`competitions`、`competition_time_nodes`、`competition_tags`、`competition_tag_links`、`review_records`、`audit_logs`。

负责人：b
协作人：f、e

### 子模块 M2.1：赛事人工录入

功能：
管理员录入赛事标题、简称、类别、主办方、承办方、来源名称、来源链接、官方报名链接、附件链接、赛事简介、报名条件、材料要求、参赛形式、适合专业、适合年级和关键时间节点。

接口：
页面接口：后台赛事创建表单、赛事字段填写区、时间节点编辑区。
API 接口：`POST /api/v1/admin/competitions`。
数据接口：`competitions`、`competition_time_nodes`、`competition_tag_links`。

负责人：b

### 子模块 M2.2：赛事编辑与字段维护

功能：
支持管理员对草稿、驳回或允许修改状态下的赛事进行编辑，维护赛事正文、时间节点、适配字段、标签和官方通道信息。

接口：
页面接口：后台赛事编辑页。
API 接口：`PATCH /api/v1/admin/competitions/{id}`。
数据接口：`competitions`、`competition_time_nodes`、`competition_tags`、`competition_tag_links`。

负责人：b
协作人：c、d

### 子模块 M2.3：赛事提交审核

功能：
管理员完成赛事信息录入后，可将赛事从草稿状态提交至待审核状态。系统应校验必填字段、来源链接、时间节点和基础标签完整性。

接口：
页面接口：赛事编辑页提交审核按钮、提交审核确认弹窗。
API 接口：`POST /api/v1/admin/competitions/{id}/submit_review`。
数据接口：`competitions`、`review_records`、`audit_logs`。

负责人：b

### 子模块 M2.4：赛事审核发布

功能：
审核人员查看待审核赛事，核对来源、时间节点、报名条件、官方链接和适配标签后，选择通过、驳回或退回修改，并记录审核意见。审核通过后赛事进入已发布状态并可在学生端展示。

接口：
页面接口：待审核赛事列表页、审核详情页、审核意见表单。
API 接口：`GET /api/v1/admin/reviews`、`POST /api/v1/admin/competitions/{id}/review`。
数据接口：`review_records`、`audit_logs`、`competitions`。

负责人：b
协作人：f

### 子模块 M2.5：赛事状态管理

功能：
维护赛事状态，包括草稿、待审核、已发布、已驳回、已下架、已归档、已取消和已过期。赛事状态变化后，应同步影响学生端展示、推荐结果和未发送提醒。

接口：
页面接口：后台赛事状态操作入口、状态变更原因填写区。
API 接口：`PATCH /api/v1/admin/competitions/{id}/status`。
内部服务接口：赛事状态变更服务、提醒取消或重算服务、审计日志写入服务。
数据接口：`competitions`、`reminders`、`audit_logs`。

负责人：b
协作人：e、f

---

## 模块 M3：赛事发现与展示模块

功能：
为学生和访客提供赛事搜索、筛选、排序、分页、列表展示、详情查看、适配标签展示和官方通道跳转能力。该模块整合原“搜索筛选与列表展示”和“赛事详情与官方通道”两类功能，统一负责学生端的赛事浏览与判断体验。

接口：
页面接口：赛事列表页、搜索框、筛选栏、排序控件、分页控件、赛事详情页、官方报名入口、附件入口、收藏订阅入口。
API 接口：`GET /api/v1/competitions`、`GET /api/v1/competitions/{id}`、`POST /api/v1/competitions/{id}/outbound_clicks`。
数据接口：`competitions`、`competition_time_nodes`、`competition_tags`、`competition_tag_links`、跳转统计记录。

负责人：c
协作人：b、d、f

### 子模块 M3.1：关键词搜索

功能：
支持按赛事名称、简称、主办方、类别和正文摘要检索赛事。搜索结果默认只展示已发布且未下架的赛事。

接口：
页面接口：赛事列表页搜索框、搜索结果展示区。
API 接口：`GET /api/v1/competitions?keyword=...`。
内部服务接口：赛事查询服务、搜索条件解析器。
数据接口：`competitions`。

负责人：c

### 子模块 M3.2：多维筛选

功能：
支持学生按专业、年级、赛事类别、参考标签、报名状态、截止日期和参赛形式组合筛选赛事。多条件筛选采用交集逻辑，筛选条件应在页面上清晰展示并支持清除。

接口：
页面接口：筛选栏、筛选标签、清除筛选按钮。
API 接口：`GET /api/v1/competitions?category=...&grade=...&major=...&tag=...`。
数据接口：`competitions`、`competition_tags`、`system_configs`。

负责人：c
协作人：f

### 子模块 M3.3：排序与分页

功能：
支持按截止时间、发布时间、推荐度和热度排序，并支持分页或加载更多。切换排序方式时应保留当前筛选条件。

接口：
页面接口：排序控件、分页控件、加载更多按钮。
API 接口：`GET /api/v1/competitions?sort=deadline&page=1&page_size=20`。
内部服务接口：排序规则服务、分页结果封装服务。

负责人：c
协作人：d

### 子模块 M3.4：赛事列表展示

功能：
在列表页展示赛事标题、类别、主办方、关键时间节点、参考标签、报名状态、收藏状态和订阅状态，帮助学生快速比较不同赛事。

接口：
页面接口：赛事列表卡片、赛事摘要信息区、收藏订阅快捷入口。
API 接口：`GET /api/v1/competitions`。
数据接口：`competitions`、`competition_time_nodes`、`competition_tags`、`favorites`、`subscriptions`。

负责人：c
协作人：e

### 子模块 M3.5：赛事详情展示

功能：
展示赛事简介、来源、主办方、报名条件、赛程安排、材料要求、参赛形式、适合专业、适合年级、附件、更新时间和状态提示。

接口：
页面接口：赛事详情页、详情信息区、时间节点区、状态提示区。
API 接口：`GET /api/v1/competitions/{id}`。
数据接口：`competitions`、`competition_time_nodes`、`competition_tags`。

负责人：c
协作人：b、d

### 子模块 M3.6：适配标签与价值依据展示

功能：
展示赛事参考标签、适合专业、适合年级、主办单位、认可信息和价值依据说明。相关说明只作为学生选赛参考，不替代学校或官方认定。

接口：
页面接口：适配标签组件、价值依据说明区、参考说明提示。
API 接口：`GET /api/v1/competitions/{id}`。
数据接口：`competition_tags`、`competition_tag_links`、`competitions.value_notes`。
内部服务接口：标签展示服务、适配说明生成服务。

负责人：c
协作人：d

### 子模块 M3.7：官方通道跳转

功能：
提供官方报名、通知原文、附件下载等外部链接入口，并记录跳转行为，用于后台统计分析。

接口：
页面接口：官方报名按钮、通知原文按钮、附件下载入口。
API 接口：`POST /api/v1/competitions/{id}/outbound_clicks`。
数据接口：跳转统计记录、行为日志。

负责人：c
协作人：f

---

## 模块 M4：赛事跟进模块

功能：
支持学生对感兴趣的赛事进行收藏、订阅、提醒跟进和日历管理。该模块负责将赛事时间节点转化为用户可跟进的个人任务，降低错过报名截止、作品提交和比赛开始等关键节点的风险。

接口：
页面接口：收藏按钮、订阅按钮、我的收藏页、我的订阅页、消息中心、个人赛事日历页。
API 接口：`POST /api/v1/competitions/{id}/favorite`、`DELETE /api/v1/competitions/{id}/favorite`、`POST /api/v1/competitions/{id}/subscribe`、`DELETE /api/v1/competitions/{id}/subscribe`、`GET /api/v1/me/calendar`、`GET /api/v1/me/messages`、`POST /api/v1/me/messages/{id}/read`。
内部任务接口：`competehub.reminders.dispatch_due`。
数据接口：`favorites`、`subscriptions`、`reminder_settings`、`reminders`、`messages`、`competition_time_nodes`。

负责人：e
协作人：a、b

### 子模块 M4.1：收藏管理

功能：
支持学生收藏和取消收藏赛事，并在赛事列表、详情页和个人中心保持收藏状态一致。收藏用于后续查看，不必然触发提醒。

接口：
页面接口：列表页收藏按钮、详情页收藏按钮、我的收藏页。
API 接口：`POST /api/v1/competitions/{id}/favorite`、`DELETE /api/v1/competitions/{id}/favorite`。
数据接口：`favorites`。

负责人：e

### 子模块 M4.2：订阅管理

功能：
支持学生订阅和取消订阅赛事。订阅后系统根据赛事时间节点和提醒配置生成待发送提醒；取消订阅后应取消未来未发送提醒。

接口：
页面接口：列表页订阅按钮、详情页订阅按钮、我的订阅页。
API 接口：`POST /api/v1/competitions/{id}/subscribe`、`DELETE /api/v1/competitions/{id}/subscribe`。
数据接口：`subscriptions`、`reminders`。

负责人：e
协作人：a

### 子模块 M4.3：站内提醒生成

功能：
基于订阅记录、赛事时间节点和用户提醒偏好生成待发送提醒。提醒至少覆盖报名截止、作品提交截止和比赛开始等关键节点。

接口：
内部服务接口：提醒生成服务、提醒重算服务、提醒取消服务。
内部任务接口：`competehub.reminders.dispatch_due`。
数据接口：`reminders`、`competition_time_nodes`、`reminder_settings`。

负责人：e
协作人：b

### 子模块 M4.4：消息中心

功能：
展示系统生成的站内消息，支持用户查看提醒内容并标记已读。消息内容应包含赛事名称、节点类型、截止或开始时间和详情入口。

接口：
页面接口：消息中心页、未读消息提示、消息详情入口。
API 接口：`GET /api/v1/me/messages`、`POST /api/v1/me/messages/{id}/read`。
数据接口：`messages`、`reminders`。

负责人：e

### 子模块 M4.5：个人赛事日历

功能：
按月、周或列表形式展示已订阅赛事的关键时间节点。学生可以通过日历查看报名截止、作品提交、比赛开始等节点，并跳转到赛事详情页。

接口：
页面接口：个人赛事日历页、节点详情弹窗、详情跳转入口。
API 接口：`GET /api/v1/me/calendar?from=...&to=...&view=month`。
数据接口：`subscriptions`、`competition_time_nodes`、`competitions`。

负责人：e
协作人：a、c

---

## 模块 M5：规则推荐与推荐解释模块

功能：
基于学生画像、赛事标签、适合专业、适合年级、截止时间和系统配置权重生成个性化推荐结果，并生成可解释的推荐理由。该模块负责推荐计算、推荐排序、推荐理由生成和推荐解释一致性校验；赛事详情页中的适配标签和价值依据展示归属于 M3 赛事发现与展示模块。推荐结果应保持可追溯，不使用不可解释的绝对价值评分作为赛事价值判断。

接口：
页面接口：推荐赛事页、首页推荐区、列表推荐排序入口、推荐理由标签组件。
API 接口：`GET /api/v1/recommendations`、`PATCH /api/v1/me/preferences`、`GET /api/v1/admin/configs`、`PATCH /api/v1/admin/configs/{key}`。
数据接口：`student_profiles`、`competitions`、`competition_tags`、`competition_tag_links`、`recommendation_rules`、`system_configs`。

负责人：d
协作人：a、c、f

### 子模块 M5.1：规则推荐计算

功能：
读取学生画像和赛事字段，根据专业匹配、年级匹配、兴趣标签、赛事类别、截止时间、参考标签等规则生成推荐列表。

接口：
API 接口：`GET /api/v1/recommendations`。
内部服务接口：推荐规则计算服务、推荐排序服务。
数据接口：`student_profiles`、`competitions`、`competition_tags`、`recommendation_rules`。

负责人：d
协作人：a

### 子模块 M5.2：推荐排序

功能：
根据规则权重对候选赛事进行排序。推荐排序可用于推荐页，也可作为赛事列表页的一种排序方式。未登录或画像不足时，系统应降级为通用推荐或近期赛事排序。

接口：
API 接口：`GET /api/v1/recommendations`、`GET /api/v1/competitions?sort=recommendation`。
内部服务接口：推荐排序服务、通用推荐降级服务。
数据接口：`recommendation_rules`、`competitions`。

负责人：d
协作人：c

### 子模块 M5.3：推荐理由生成

功能：
为每条推荐结果生成可解释理由，例如“与你的专业匹配”“适合当前年级”“与你关注的人工智能方向相关”“报名截止较近”。推荐理由必须来源于明确规则或赛事字段。

接口：
页面接口：推荐理由标签组件。
API 接口：`GET /api/v1/recommendations`。
数据接口：`recommendation_rules.reason_template`、`student_profiles`、`competition_tags`。

负责人：d

### 子模块 M5.4：推荐解释一致性校验

功能：
校验推荐页中的推荐理由与 M3 详情页展示的适配标签、价值依据说明保持一致，避免出现推荐理由和赛事详情信息互相矛盾的情况。本子模块只负责一致性规则和解释生成约束，不负责详情页展示组件。

接口：
页面接口：推荐理由标签、详情页适配标签、价值依据说明区。
内部服务接口：推荐解释校验服务、推荐理由生成服务。
数据接口：`competition_tags`、`competition_tag_links`、`competitions.value_notes`。

负责人：d
协作人：c

### 子模块 M5.5：推荐规则配置协作

功能：
配合后台配置模块维护推荐规则权重、推荐理由模板、启用状态和基础字典，使推荐逻辑可以通过后台配置进行调整。

接口：
后台页面接口：推荐规则配置页、权重配置表单。
API 接口：`GET /api/v1/admin/configs`、`PATCH /api/v1/admin/configs/{key}`。
数据接口：`recommendation_rules`、`system_configs`。

负责人：d
协作人：f

---

## 模块 M6：后台运营、配置与审计统计模块

功能：
为管理员提供用户管理、基础配置管理、内容审核入口、审计日志查询和运营统计能力。该模块作为系统治理和运营支撑模块，不直接替代具体业务模块，而是为赛事治理、推荐规则、消息模板和数据统计提供统一后台能力。

接口：
页面接口：后台首页、用户管理页、基础配置页、内容审核页、操作日志页、统计概览页。
API 接口：`GET /api/v1/admin/users`、`PATCH /api/v1/admin/users/{id}`、`GET /api/v1/admin/configs`、`PATCH /api/v1/admin/configs/{key}`、`GET /api/v1/admin/reviews`、`GET /api/v1/admin/audit_logs`、`GET /api/v1/admin/stats`。
数据接口：`users`、`system_configs`、`recommendation_rules`、`review_records`、`audit_logs`、行为日志、收藏订阅记录、跳转记录。

负责人：f
协作人：b、c、d

### 子模块 M6.1：后台首页与统计概览

功能：
展示系统运营概况，包括赛事数量、待审核赛事数量、用户数量、搜索量、收藏量、订阅量、官方通道跳转量和推荐点击量。

接口：
页面接口：后台首页、统计卡片、趋势概览区。
API 接口：`GET /api/v1/admin/stats`。
数据接口：行为日志、收藏订阅记录、跳转记录、推荐点击记录。

负责人：f
协作人：c

### 子模块 M6.2：用户与权限管理

功能：
管理员查看用户列表，启用或禁用账号，调整用户角色和账号状态，并记录相关操作日志。

接口：
页面接口：用户管理页、用户详情弹窗、角色和状态编辑入口。
API 接口：`GET /api/v1/admin/users`、`PATCH /api/v1/admin/users/{id}`。
数据接口：`users`、`audit_logs`。

负责人：f
协作人：a

### 子模块 M6.3：基础配置管理

功能：
维护赛事类别、参考标签、适合专业、适合年级、消息模板、推荐权重等基础配置，为赛事录入、筛选、详情展示、推荐和提醒模块提供统一配置来源。

接口：
页面接口：基础配置页、标签配置表、推荐权重配置表、消息模板配置表。
API 接口：`GET /api/v1/admin/configs`、`PATCH /api/v1/admin/configs/{key}`。
数据接口：`system_configs`、`competition_tags`、`recommendation_rules`。

负责人：f
协作人：b、d

### 子模块 M6.4：审核记录管理

功能：
展示赛事、资料、认证申请等审核记录，支持管理员查看审核对象、审核状态、审核意见、提交人、审核人和审核时间。

接口：
页面接口：审核记录列表、审核详情页。
API 接口：`GET /api/v1/admin/reviews`。
数据接口：`review_records`。

负责人：f
协作人：b

### 子模块 M6.5：审计日志查询

功能：
查询后台关键操作记录，包括赛事创建、修改、提交审核、审核、下架、归档、取消、配置修改、用户角色变更和账号状态变更。

接口：
页面接口：操作日志页、日志筛选栏、日志详情弹窗。
API 接口：`GET /api/v1/admin/audit_logs`。
数据接口：`audit_logs`。

负责人：f
协作人：b

### 子模块 M6.6：测试文档与演示支撑

功能：
整理系统核心流程测试用例、接口测试记录、演示数据和答辩材料，保证系统在课程展示时能够完整演示主链路。

接口：
文档接口：测试用例文档、接口联调记录、演示流程文档。
内部协作接口：前后端联调清单、演示账号、演示数据初始化脚本。

负责人：f
协作人：全体成员

---

## 模块 M7：内容沉淀与交流扩展模块

功能：
作为增强扩展模块，支持往届资料归档、常见问题、组队交流、认证答疑和赛后复盘等能力，用于形成竞赛经验沉淀。该模块不作为第一阶段主链路的必要前提，可根据开发进度实现基础原型或预留接口。

接口：
页面接口：资料库页、资料详情页、组队帖列表页、组队帖详情页、认证答疑页、复盘记录页。
API 接口：后续可扩展为 `GET /api/v1/materials`、`POST /api/v1/admin/materials`、`GET /api/v1/team_posts`、`POST /api/v1/team_posts`、`POST /api/v1/certifications`、`POST /api/v1/admin/certifications/{id}/review`、`GET /api/v1/competition_reviews`、`POST /api/v1/competition_reviews`。
数据接口：复用 `users`、`competitions`、`review_records`、`audit_logs`，后续新增资料表、帖子表、认证申请表和复盘记录表。

负责人：f
协作人：a、b、e

### 子模块 M7.1：资料归档

功能：
归档往届通知、优秀作品、经验材料、常见问题和复盘资料，并支持资料与赛事或赛事类别关联。

接口：
页面接口：资料库页、资料详情页、后台资料上传入口。
API 接口：`GET /api/v1/materials`、`POST /api/v1/admin/materials`。
数据接口：资料记录表、附件元数据、赛事关联关系。

负责人：f
协作人：b

### 子模块 M7.2：组队交流

功能：
支持学生围绕指定赛事发布组队需求，说明技能要求、人数需求、联系方式和截止时间。第一阶段可仅保留基础展示或接口预留。

接口：
页面接口：组队列表页、组队详情页、组队发布表单。
API 接口：`GET /api/v1/team_posts`、`POST /api/v1/team_posts`。
数据接口：组队帖子表、用户表、赛事表。

负责人：e
协作人：f

### 子模块 M7.3：认证答疑

功能：
参加过竞赛或获奖的用户可提交认证申请，管理员审核通过后，用户可在答疑内容中展示认证身份。该功能复用审核记录和审计日志机制。

接口：
页面接口：认证申请页、认证答疑页、后台认证审核页。
API 接口：`POST /api/v1/certifications`、`POST /api/v1/admin/certifications/{id}/review`。
数据接口：认证申请记录、`review_records`、`audit_logs`、`users`。

负责人：b
协作人：f

### 子模块 M7.4：赛后复盘

功能：
支持学生或教师提交赛后复盘记录，总结参赛过程、准备经验、问题和建议，为后续参赛者提供参考。

接口：
页面接口：复盘编辑页、复盘详情页、复盘列表页。
API 接口：`GET /api/v1/competition_reviews`、`POST /api/v1/competition_reviews`。
数据接口：复盘记录表、用户表、赛事表。

负责人：a
协作人：f

---

# 四、模块间关系说明

M1 用户与画像管理模块为 M5 规则推荐模块提供学生画像数据，为 M4 赛事跟进模块提供提醒偏好数据。

M2 赛事治理模块负责产生可信、结构化、状态明确的赛事数据，是 M3 赛事发现与展示模块、M4 赛事跟进模块和 M5 规则推荐模块的数据基础。

M3 赛事发现与展示模块负责学生端赛事浏览体验，向 M4 提供收藏订阅入口，向 M5 提供推荐结果展示入口，并向 M6 提供搜索和跳转统计数据。

M4 赛事跟进模块基于 M3 展示的赛事和 M2 维护的时间节点，生成收藏、订阅、提醒、消息和个人日历数据。

M5 规则推荐与推荐解释模块基于 M1 用户画像、M2/M3 赛事标签和 M6 推荐规则配置生成推荐结果和推荐理由，并保证推荐解释不与 M3 展示的适配标签和价值依据说明冲突。

M6 后台运营、配置与审计统计模块为 M2 赛事治理、M3 标签筛选、M4 消息模板和 M5 推荐规则提供配置支撑，并统一展示审计日志和运营统计。

M7 内容沉淀与交流扩展模块复用 M1 用户、M2 赛事、M6 审核与审计能力，用于后续扩展资料归档、组队交流、认证答疑和赛后复盘。

---

# 五、阶段性实现说明

第一阶段优先实现 M1-M6 的核心闭环，保证系统能够完成以下演示流程：

学生注册登录并维护画像；管理员录入赛事并审核发布；学生搜索筛选赛事并查看详情；学生收藏或订阅赛事；系统生成站内提醒并展示个人赛事日历；系统根据画像和赛事标签生成规则推荐；管理员在后台查看基础统计、配置和审计记录。

第二阶段根据开发进度补充 M7 内容沉淀与交流扩展模块，包括资料归档、组队交流、认证答疑和赛后复盘等功能。该模块应复用已有用户、赛事、审核和审计体系，避免形成独立内容孤岛。
