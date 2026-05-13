根据现有文档和张子都分支里的代码基础，建议你们不要再重新设计成微服务，而是采用：

**前后端分离 + 模块化单体 + 分层架构 + RESTful API 接口风格**。

也就是：前端 Vue 3 负责页面和交互，后端 Flask 负责业务逻辑和数据处理，前后端通过 RESTful API 通信；后端不是拆成很多微服务，而是在一个 Flask 项目里按 auth、user、competition、recommendation、reminder、forum、admin 等业务模块拆分。这个判断和你们上传的架构说明一致：文档明确写到本项目采用“模块化单体架构 Modular Monolith”，并且采用前后端分离、单仓库多子项目、后端分层设计、PostgreSQL、Redis/Celery 增强层、Nginx + Gunicorn 部署方式。 GitHub 分支中也已经存在 `backend/`、`frontend/`、`infra/nginx`、`docs/`、`scripts/` 等目录，并且 README 写明前端是 Vue 3、后端是 Flask API、生产环境由 Nginx 代理到 Flask/Gunicorn。([GitHub][1])

---

## 一、选用的体系结构风格

### 1. 主体风格：前后端分离架构

前端负责页面展示、用户操作、表单校验、路由跳转；后端负责登录认证、权限控制、赛事查询、推荐计算、提醒、论坛和后台管理。你们的架构文档也说明前端和后端通过 HTTP API 通信，不共享页面渲染逻辑。

### 2. 后端风格：模块化单体架构

不拆微服务，而是在同一个 Flask 后端项目中按业务模块拆分。当前 GitHub 代码已经注册了 `health`、`auth`、`users`、`competitions`、`recommendations`、`reminders`、`forum`、`admin` 等 API 模块。([GitHub][2]) 这正好对应需求文档中的用户、赛事、搜索、详情评估、提醒、推荐、论坛资料、后台统计等模块。

### 3. 内部风格：分层架构

后端采用 Route / Service / Model / Common / Tasks 分层。GitHub 后端目录中已经有 `api`、`core`、`models`、`repositories`、`schemas`、`services`、`tasks`、`utils` 等目录，说明张子都已经把后端基础分层搭好了。([GitHub][3])

### 4. 前端风格：组件化 + MVVM 风格

前端采用 Vue 3，目录中已经有 `api`、`components`、`layouts`、`router`、`stores`、`utils`、`views` 等结构，适合按页面和组件继续分工开发。([GitHub][4])

---

## 二、6 人分工总表

由于需求文档里原本划分了 8 个功能模块，但你们小组只有 6 个人，所以建议把相近模块合并为 6 个开发责任模块。

| 成员  | 负责模块                   | 对应需求模块         | 主要职责                                    |
| --- | ---------------------- | -------------- | --------------------------------------- |
| 张子都 | M6 系统架构、接口联调、部署与演示集成模块 | 横向支撑所有模块       | 继续维护现有代码骨架、API 规范、数据库初始化、启动脚本、接口联调、演示流程 |
| 成员2 | M1 用户与画像管理模块           | 原 M1           | 登录注册、JWT、用户资料、个人画像、角色权限、收藏订阅记录          |
| 成员3 | M2 赛事信息、搜索筛选与详情评估模块    | 原 M2 + M3 + M4 | 赛事采集/录入、清洗去重、搜索筛选、详情页、价值评分、官方链接         |
| 成员4 | M3 个性化推荐与订阅提醒模块        | 原 M5 + M6      | 推荐规则、推荐理由、推荐偏好、订阅提醒、个人日历、站内通知           |
| 成员5 | M4 交流论坛、组队与资料沉淀模块      | 原 M7           | 发帖评论、组队交流、认证答疑、历届资料、经验分享、赛后复盘           |
| 成员6 | M5 后台运营、审核统计与测试文档模块    | 原 M8 + 测试文档    | 后台管理、用户管理、赛事审核、认证审核、评分规则、统计分析、测试用例、答辩材料 |

这样分工的好处是：张子都已经实现了一部分基础代码和演示闭环，所以他最适合做**架构负责人和联调负责人**；其余 5 人分别负责业务模块，避免 6 个人都去改同一批文件导致冲突。

---

## 三、按图片模板整理的模块描述

### 模块 M1：用户与画像管理模块

**功能：**
负责用户注册、登录、身份认证、角色选择、个人信息维护、画像标签维护，以及收藏和订阅基础记录管理。需求文档中 M1 明确包括注册登录、角色选择、个人信息维护、兴趣标签维护、收藏订阅。

**接口：**

| 接口                                     | 说明         |
| -------------------------------------- | ---------- |
| `POST /api/v1/auth/register`           | 用户注册       |
| `POST /api/v1/auth/login`              | 用户登录       |
| `GET /api/v1/users/me`                 | 获取当前登录用户信息 |
| `PUT /api/v1/users/me/profile`         | 修改个人画像     |
| `GET /api/v1/users/me/certifications`  | 查看个人认证记录   |
| `POST /api/v1/users/me/certifications` | 提交竞赛经历认证   |

**负责人：成员2**

**子模块 M1.1：注册登录子模块**
功能：实现账号注册、账号密码登录、JWT Token 保存与登录状态判断。
接口：`POST /api/v1/auth/register`、`POST /api/v1/auth/login`。
负责人：成员2。

**子模块 M1.2：个人画像子模块**
功能：维护专业、年级、兴趣方向、竞赛经历、目标导向等信息，为推荐模块提供数据。
接口：`GET /api/v1/users/me`、`PUT /api/v1/users/me/profile`。
负责人：成员2。

**子模块 M1.3：角色权限子模块**
功能：区分访客、学生、教师、组织者、管理员等角色；未登录用户点击收藏/订阅时跳转登录。
接口：前端路由守卫 + 后端 JWT 鉴权。
负责人：成员2，张子都协助联调。

---

### 模块 M2：赛事信息、搜索筛选与详情评估模块

**功能：**
负责竞赛信息的录入、采集、清洗、去重、审核、上架、搜索、筛选、排序、详情展示、价值评分和官方链接跳转。这个模块合并了原需求中的 M2、M3、M4，因为三者都围绕“赛事数据”展开。需求文档中 M2 是赛事采集管理，M3 是搜索筛选展示，M4 是赛事详情与价值评估。

**接口：**

| 接口                                    | 说明               |
| ------------------------------------- | ---------------- |
| `GET /api/v1/competitions`            | 赛事列表、搜索、筛选、排序、分页 |
| `GET /api/v1/competitions/{id}`       | 赛事详情             |
| `GET /api/v1/competitions/options`    | 获取筛选项、分类、标签      |
| `POST /api/v1/competitions`           | 普通用户或组织者提交赛事     |
| `PUT /api/v1/competitions/{id}`       | 修改赛事信息           |
| `GET /api/v1/admin/competitions`      | 管理员查看全部赛事        |
| `POST /api/v1/admin/competitions`     | 管理员新增赛事          |
| `PUT /api/v1/admin/competitions/{id}` | 管理员修改赛事          |

**负责人：成员3**

**子模块 M2.1：赛事数据管理子模块**
功能：维护赛事名称、主办方、类别、级别、报名时间、比赛时间、标签、适合专业、官方链接等字段。
接口：`POST /api/v1/admin/competitions`、`PUT /api/v1/admin/competitions/{id}`。
负责人：成员3。

**子模块 M2.2：搜索筛选子模块**
功能：支持关键词、类别、级别、报名状态、截止日期、热度、评分等筛选和排序。
接口：`GET /api/v1/competitions?keyword=&category=&level=&sort=&page=`。
负责人：成员3。

**子模块 M2.3：赛事详情与价值评估子模块**
功能：展示赛事简介、报名条件、时间节点、适配人群、评分、评分依据、官方链接。
接口：`GET /api/v1/competitions/{id}`。
负责人：成员3。

**子模块 M2.4：采集与清洗子模块**
功能：根据官方通知或学校/学院网站整理赛事信息；当前阶段可以先手工录入和种子数据，后续再补自动爬取。
接口：后续扩展 `crawler` 或导入脚本。
负责人：成员3，张子都协助脚本接入。

---

### 模块 M3：个性化推荐与订阅提醒模块

**功能：**
负责基于用户画像、兴趣标签、收藏订阅行为、浏览记录等信息生成推荐结果，并展示推荐理由；同时负责收藏、订阅、站内通知、个人赛事日历和提醒设置。需求文档中 M5 是订阅提醒与日历，M6 是个性化推荐。 当前演示流程中也已经要求学生能进入推荐页看到推荐理由，并在订阅日历中看到已订阅赛事。

**接口：**

| 接口                                         | 说明        |
| ------------------------------------------ | --------- |
| `POST /api/v1/competitions/{id}/favorite`  | 收藏赛事      |
| `POST /api/v1/competitions/{id}/subscribe` | 订阅赛事      |
| `GET /api/v1/recommendations`              | 获取个性化推荐列表 |
| `PUT /api/v1/recommendations/preferences`  | 修改推荐偏好    |
| `GET /api/v1/reminders/calendar`           | 获取个人赛事日历  |
| `GET /api/v1/reminders/notifications`      | 获取站内通知    |
| `PUT /api/v1/reminders/settings`           | 修改提醒设置    |

**负责人：成员4**

**子模块 M3.1：推荐算法子模块**
功能：根据专业、兴趣、年级、收藏订阅历史、截止时间、热度计算推荐分。
接口：`GET /api/v1/recommendations`。
负责人：成员4。

**子模块 M3.2：推荐理由子模块**
功能：给出“与你的专业匹配”“与你的兴趣标签匹配”“距离截止时间较近”等解释，方便答辩时说明“智能推荐”的依据。
接口：`GET /api/v1/recommendations` 返回 `recommend_reasons` 字段。
负责人：成员4。

**子模块 M3.3：订阅提醒子模块**
功能：用户订阅赛事后，系统按报名截止、比赛开始、作品提交等节点生成提醒。
接口：`POST /api/v1/competitions/{id}/subscribe`、`GET /api/v1/reminders/notifications`。
负责人：成员4。

**子模块 M3.4：个人日历子模块**
功能：把用户订阅的赛事节点集中展示到个人日历或时间列表。
接口：`GET /api/v1/reminders/calendar`。
负责人：成员4。

---

### 模块 M4：交流论坛、组队与资料沉淀模块

**功能：**
负责论坛发帖、评论、点赞、组队交流、认证答疑、历届资料归档、经验分享和赛后复盘。需求文档中 M7 包括发帖评论、组队交流、认证答疑、历届资料归档和赛后复盘。

**接口：**

| 接口                                       | 说明       |
| ---------------------------------------- | -------- |
| `GET /api/v1/forum/posts`                | 查看帖子列表   |
| `POST /api/v1/forum/posts`               | 发布帖子     |
| `GET /api/v1/forum/posts/{id}`           | 查看帖子详情   |
| `GET /api/v1/forum/posts/{id}/comments`  | 查看评论     |
| `POST /api/v1/forum/posts/{id}/comments` | 发布评论     |
| `POST /api/v1/forum/posts/{id}/like`     | 点赞       |
| `POST /api/v1/forum/posts/{id}/interest` | 表达组队意向   |
| `POST /api/v1/users/me/certifications`   | 提交认证答疑申请 |

**负责人：成员5**

**子模块 M4.1：论坛发帖评论子模块**
功能：用户发布提问帖、经验帖、资料帖，并支持评论互动。
接口：`GET /api/v1/forum/posts`、`POST /api/v1/forum/posts`、`POST /api/v1/forum/posts/{id}/comments`。
负责人：成员5。

**子模块 M4.2：组队交流子模块**
功能：围绕某个竞赛发布组队需求，说明技能要求、人数和联系方式。
接口：`POST /api/v1/forum/posts/{id}/interest`、`GET /api/v1/users/matchmaking`。
负责人：成员5。

**子模块 M4.3：认证答疑子模块**
功能：获得奖项或参加过竞赛的用户提交认证，通过后可作为“认证用户”答疑。
接口：`POST /api/v1/users/me/certifications`。
负责人：成员5，成员6负责后台审核接口。

**子模块 M4.4：资料沉淀与复盘子模块**
功能：整理往届通知、获奖作品、备赛经验、复盘记录，形成可持续查询的资料库。
接口：可以先复用论坛帖子类型，后续扩展独立资料接口。
负责人：成员5。

---

### 模块 M5：后台运营、审核统计与测试文档模块

**功能：**
负责后台管理、用户管理、赛事管理、帖子管理、认证审核、评分规则配置、统计分析、日志留痕、测试用例和答辩材料整理。需求文档中 M8 包括用户权限管理、评分规则配置、内容审核、数据统计和反馈处理。 当前演示流程也要求管理员登录后进入后台管理页，确认用户数、赛事数、收藏数、订阅数、论坛帖子数等统计能加载。

**接口：**

| 接口                                      | 说明      |
| --------------------------------------- | ------- |
| `GET /api/v1/admin/statistics`          | 后台统计    |
| `GET /api/v1/admin/users`               | 用户管理    |
| `GET /api/v1/admin/competitions`        | 后台赛事管理  |
| `POST /api/v1/admin/competitions`       | 管理员新增赛事 |
| `PUT /api/v1/admin/competitions/{id}`   | 管理员修改赛事 |
| `GET /api/v1/admin/posts`               | 后台帖子管理  |
| `DELETE /api/v1/admin/posts/{id}`       | 删除或下架帖子 |
| `GET /api/v1/admin/certifications`      | 查看认证申请  |
| `PUT /api/v1/admin/certifications/{id}` | 审核认证申请  |

**负责人：成员6**

**子模块 M5.1：后台首页统计子模块**
功能：展示用户数、赛事数、收藏数、订阅数、帖子数、待审核认证数。
接口：`GET /api/v1/admin/statistics`。
负责人：成员6。

**子模块 M5.2：内容审核子模块**
功能：审核赛事、帖子、认证申请和用户反馈。
接口：`GET /api/v1/admin/certifications`、`PUT /api/v1/admin/certifications/{id}`。
负责人：成员6。

**子模块 M5.3：权限与安全子模块**
功能：保证普通用户不能访问后台，管理员才能进行管理操作。
接口：JWT + `role_required("admin")`。
负责人：成员6，成员2协助。

**子模块 M5.4：测试与答辩文档子模块**
功能：整理测试用例、演示流程、功能截图、接口说明、系统结构图、答辩 PPT 素材。
接口：不直接提供业务接口，但要覆盖所有模块的测试。
负责人：成员6。

---

### 模块 M6：系统架构、接口联调、部署与演示集成模块

**功能：**
负责维护张子都已经实现的项目基础结构，统一前后端接口规范，处理数据库初始化、种子数据、启动脚本、Docker/Nginx 配置、局域网访问、演示流程和最终集成。当前 GitHub 分支已经包含后端、前端、基础设施、脚本和文档目录，适合由张子都继续作为架构与集成负责人。([GitHub][1])

**接口：**

| 接口或交付物               | 说明                                                       |
| -------------------- | -------------------------------------------------------- |
| `GET /api/v1/health` | 后端健康检查                                                   |
| 统一响应格式               | `{ code, message, data }`                                |
| API 前缀               | `/api/v1`                                                |
| 启动脚本                 | `scripts/start_backend.ps1`、`scripts/start_frontend.ps1` |
| 部署配置                 | `infra/nginx`、`docker-compose.yml`                       |
| 演示环境                 | 学生账号、管理员账号、SQLite / PostgreSQL 切换                        |

**负责人：张子都**

**子模块 M6.1：项目骨架维护子模块**
功能：维护 `frontend/`、`backend/`、`infra/`、`docs/`、`scripts/` 目录结构。
接口：统一代码规范和目录规范。
负责人：张子都。

**子模块 M6.2：接口联调子模块**
功能：保证前端 `api/` 调用后端 `/api/v1` 接口，处理跨域、Token、错误响应、分页格式。
接口：所有业务接口。
负责人：张子都，各模块负责人配合。

**子模块 M6.3：数据库与种子数据子模块**
功能：维护开发数据库、初始化命令、演示账号、演示赛事数据。
接口：`flask --app run.py init-db` 或启动脚本中的 `-Seed` 参数。
负责人：张子都。

**子模块 M6.4：部署与演示子模块**
功能：保证能本地启动、局域网访问、Docker 部署或 Nginx 部署；整理最终演示路径。上传的演示清单已经给出后端和前端启动脚本，以及学生账号、管理员账号和演示主链路。
接口：启动脚本、健康检查接口、局域网访问地址。
负责人：张子都。

---

## 四、最终建议的任务安排顺序

第一阶段先保证能演示：

1. 张子都负责把现有项目拉通，确保后端、前端、数据库、演示账号、健康检查接口都正常。
2. 成员2完成登录注册、用户画像和权限守卫。
3. 成员3完成赛事列表、筛选、详情、评分展示。
4. 成员4完成收藏、订阅、推荐、日历。
5. 成员5完成论坛列表、帖子详情、评论、组队。
6. 成员6完成后台统计、审核、测试用例和答辩材料。

第二阶段再补增强功能：

1. 成员3补赛事采集、去重、过期归档。
2. 成员4补提醒任务、推荐偏好调整。
3. 成员5补资料库、认证答疑、赛后复盘。
4. 成员6补评分规则配置、日志留痕、统计报表。
5. 张子都统一处理接口冲突、部署问题和最终演示环境。

这样写到课程设计报告里比较合理：既符合需求文档中的八大功能模块，又符合张子都当前代码中已经形成的前后端分离、模块化单体和分层架构。

[1]: https://github.com/elecdot/competehub/tree/ZiduZhang "GitHub - elecdot/competehub at ZiduZhang · GitHub"
[2]: https://github.com/elecdot/competehub/raw/refs/heads/ZiduZhang/backend/app/api/v1/__init__.py "raw.githubusercontent.com"
[3]: https://github.com/elecdot/competehub/tree/ZiduZhang/backend/app "competehub/backend/app at ZiduZhang · elecdot/competehub · GitHub"
[4]: https://github.com/elecdot/competehub/tree/ZiduZhang/frontend/src "competehub/frontend/src at ZiduZhang · elecdot/competehub · GitHub"
