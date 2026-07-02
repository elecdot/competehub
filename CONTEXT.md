# CompeteHub

This glossary records the project-specific language for the student competition discovery and recommendation domain.
It defines canonical terms and avoided wording only; decision rationale and
tradeoffs belong in `docs/adr/`.

## Language

**大学生竞赛信息智能筛选与推荐系统**:
The formal Chinese name of the system. Use this name in course reports, Chinese product documents, and formal report metadata.
_Avoid_: XX系统

**CompeteHub**:
The English short name of 大学生竞赛信息智能筛选与推荐系统. Use this name where a concise product or project name is needed.
_Avoid_: CompetitionHub, ContestHub

**赛事**:
The canonical business object that students search, view, favorite, subscribe to, and that administrators review and publish. Use 竞赛 only as a broad everyday word or as part of the formal system name, not as the object name.
_Avoid_: 比赛, 竞赛

**规则推荐**:
A recommendation approach that ranks赛事 by explicit profile, tag, time, and configuration rules and expresses output through推荐理由 instead of a public赛事价值分数.
_Avoid_: 智能评分, 含金量评分, 机器学习推荐

**推荐理由**:
Short user-facing explanations for why a赛事 appears in a recommendation result, derived from explicit rules or赛事 fields.
_Avoid_: 推荐分数, 算法结论

**价值依据说明**:
Reference information that helps students judge whether a赛事 is worth attention, such as organizer, recognition notes, tags, source facts, and fit notes. It does not replace official school or organizer recognition.
_Avoid_: 赛事价值评分, 含金量评分

**可信来源**:
An official or institutionally reliable source for赛事 information, such as school websites, college announcements, official competition sites, or official notices. Source identity and source link are part of the source fact.
_Avoid_: 非来源化信息, 群聊传闻

**人工录入**:
A management action where administrators create赛事 records from可信来源, with structured fields and retained source facts before review and publication.
_Avoid_: 自动采集, 爬虫采集

**采集候选赛事**:
A prospective赛事 record produced by semi-automated collection for administrator review. It is a candidate record, not a published赛事.
_Avoid_: 自动发布赛事, 自动采集发布

**学生**:
The current core user role that searches赛事, maintains a profile, receives recommendations, favorites or subscribes to赛事, and follows reminders.
_Avoid_: 普通用户, 客户

**管理员**:
The current management role responsible for赛事录入, 审核发布, status maintenance, configuration, user management, and audit-oriented operations.
_Avoid_: 运营人员, 后台用户

**辅助干系人**:
Teachers, teaching secretaries, competition organizers, and student organizations whose needs inform the system without being current formal product roles.
_Avoid_: 正式用户角色

**收藏**:
A student's lightweight saved reference to a赛事 for later viewing. 收藏 does not generate reminders or calendar nodes by itself.
_Avoid_: 订阅, 关注

**订阅**:
A student's active decision to follow a赛事 and its time nodes. 订阅 can generate站内提醒 and personal calendar nodes according to reminder settings.
_Avoid_: 收藏, 关注

**站内提醒**:
A reminder delivered inside CompeteHub as a system message instead of through external notification channels.
_Avoid_: 邮件提醒, 短信提醒, 微信提醒, 外部推送

**个人赛事日历**:
A student-facing calendar or list view of time nodes from subscribed赛事. It is derived from订阅 and赛事时间节点.
_Avoid_: 外部日历同步

**核心闭环**:
The current-version delivery scope made of M1-M6: student profile,赛事治理,赛事发现与展示,赛事跟进,规则推荐, and backend operation/configuration/audit support.
_Avoid_: 全量平台, 一期包含所有模块

**内容沉淀与交流扩展**:
The M7 future extension area for materials, team posts, certified Q&A, and post-competition reviews. It may be reserved in design, but it is not part of the current验收主线.
_Avoid_: 当前核心模块
