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

**部署高校**:
The single university that owns one current P1 CompeteHub deployment. Student
numbers, colleges, administrators, dictionaries, and school-level governance
are interpreted inside this institution boundary. A deployment may still
publish赛事 from national organizers or other trustworthy external sources.
_Avoid_: 多租户平台, 用学院字段表示学校

**赛事**:
The canonical umbrella term for the competition domain. When dates, publication
status, 收藏, or 订阅 are involved, a current product 赛事 record means a 赛事届次
unless the text explicitly refers to a 赛事系列. Use 竞赛 only as a broad everyday
word or as part of the formal system name, not as the object name.
_Avoid_: 比赛, 竞赛

**赛事系列**:
The stable identity that groups one or more recurring 赛事届次, such as the
cross-year identity of a nationally organized competition. A one-off 赛事 still
has a series with one届次. Similar titles or organizers may suggest a match, but
an administrator must confirm series identity from source facts.
_Avoid_: 年度赛事记录, 同名赛事

**赛事届次**:
One concrete occurrence or participation cycle within a 赛事系列. Each届次 has
its own source facts, review and publication status, time nodes, and public
detail. A new annual cycle creates a new届次; a schedule correction within the
same cycle updates the existing届次.
_Avoid_: 赛事系列, 用新年度覆盖旧赛事

**赛事届次修订**:
A numbered content version of one赛事届次 containing its source-backed public
facts, stages, and time nodes. A published revision is immutable; later edits
create a new draft revision while the current approved revision remains public.
_Avoid_: 直接修改公开内容, 覆盖已发布版本

**公开修订**:
The approved赛事届次修订 currently selected for public list, detail, search, and
recommendation reads. Switching the public revision is an atomic result of
review approval.
_Avoid_: 待审核修订, 后台草稿

**进行中赛事修订**:
The single `draft` or `pending_review` revision currently moving through one
赛事届次 publication workflow. It records the public revision used as its
comparison baseline; P1 does not allow parallel active replacements.
_Avoid_: 采集候选记录, 并行修订, 终态审核记录

**紧急下架**:
An immediate, reasoned withdrawal of the current public赛事届次 when leaving it
visible creates a serious safety, fraud, link-hijacking, or misinformation risk.
It bypasses prior review only for withdrawal, writes audit evidence, and cannot
restore publication without a corrected revision and independent approval.
_Avoid_: 普通内容修改, 无原因隐藏

**公开赛事**:
A reviewed and currently published 赛事 that is eligible for the default public
list, search, recommendation, and detail surfaces. This term describes current
discoverability; it does not include every record whose historical detail
remains publicly readable.
_Avoid_: 未审核赛事, 草稿赛事, 历史可查看赛事

**历史可查看赛事**:
A previously published 赛事 whose current status is cancelled, expired, or
archived. It is excluded from default list, search, and recommendation results,
but its public detail remains readable with an explicit status warning so that
saved links and source history retain context.
_Avoid_: 公开赛事, 已下架赛事

**已下架赛事**:
A previously published 赛事 that an administrator has deliberately withdrawn
from public access. It is absent from public discovery and its detail is not
publicly readable. This is distinct from a cancelled, expired, or archived 赛事.
_Avoid_: 已取消赛事, 已过期赛事, 已归档赛事

**赛事时间节点**:
A milestone in a赛事届次 lifecycle with one semantic type and exactly one
`occurs_at` instant, such as registration opening, 报名截止日期, submission
deadline, competition start, review, or result announcement. A source period is
represented by separate start and end milestones rather than one node carrying
two times. The same milestone keeps one logical identity across corrected
赛事届次修订 while each approved correction creates a new immutable snapshot.
_Avoid_: 赛事日期, 时间段节点, 同时包含开始与截止的节点

**赛程语义变更**:
An approved change that alters a milestone occurrence, adds or removes a
student-selected milestone, or changes its controlled node type. Stage,
prominence, description, title, and other presentation-only corrections are
not赛程语义变更 even when they create a new content snapshot.
_Avoid_: 任意节点修订, 文案修改, 样式调整

**赛事阶段**:
A labeled and ordered group of related赛事时间节点 within one赛事届次, such as
"校赛报名", "初赛", or "全国总决赛". Related opening/deadline or start/end
milestones are paired through the stage while remaining separate single-instant
nodes.
_Avoid_: 时间段节点, 用描述文本猜测分组

**时间节点重点级别**:
The controlled `primary` or `secondary` prominence of a赛事时间节点. Primary
nodes receive stronger display treatment and drive the default下一个关键时间节点.
Type-based defaults may be changed by an administrator only with a recorded
reason.
_Avoid_: 任意视觉权重, 无依据置顶

**赛事时间节点修订**:
An auditable version of one赛事时间节点 after an official schedule correction.
The node keeps its identity across revisions so reminders and calendar entries
can distinguish the current time from a superseded plan.
_Avoid_: 新建重复节点, 覆盖历史时间

**赛事时间变更通知**:
An idempotent 站内消息 telling active subscribers that a published赛事届次 time
node changed. It is distinct from an ordinary reminder scheduled before a
deadline or event time.
_Avoid_: 补发到期提醒, 静默改期

**产品日历时区**:
The `Asia/Shanghai` calendar used to interpret and display user-facing赛事 dates consistently. It is independent of a browser, server, or developer machine's local time zone.
_Avoid_: 浏览器本地时区, 服务器本地时区, UTC 日历日

**报名截止日期**:
The due date of a registration-deadline赛事时间节点. In public赛事 discovery, a deadline date filter means报名截止日期; submission and later milestones do not satisfy that filter.
_Avoid_: 任一节点截止日期, 作品提交截止日期

**报名状态**:
The dynamic, non-persisted state of registration for one赛事届次, derived from
its current registration stages and time nodes: `open`, `upcoming`, `closed`,
`unknown`, or `not_applicable`. `not_applicable` requires an explicit admin fact;
it is never inferred from missing registration nodes. For multiple rounds,
`open` takes precedence, then `upcoming`, then `closed`, with `unknown` used when
no higher-confidence result is available.
_Avoid_: 赛事发布状态, 固定存储的过期报名状态

**可行动排序**:
The default public discovery order that prioritizes赛事届次 by current student
actionability: open registration, upcoming registration, unknown registration,
not-applicable registration, then closed registration. Within each group it uses
the relevant next time fact and stable publication/id tie-breakers.
_Avoid_: 任意最近节点排序, 默认推荐度排序, 不稳定分页排序

**下一个关键时间节点**:
The nearest future `primary`赛事时间节点 shown to help students understand what
happens next. If no future primary node exists, the nearest future secondary
node is used as a fallback. It is not synonymous with报名截止日期 and does not
define the报名截止日期 filter.
_Avoid_: 下一个报名截止日期

**参赛形式**:
The set of supported ways a student may enter a赛事届次: `individual`, `team`,
or both. It is not a mutually exclusive single value. Team-size constraints are
separate赛事 information and are required whenever team entry is allowed.
_Avoid_: 团队人数, 报名条件, 个人与团队二选一字段

**适配范围**:
The explicit applicability of a赛事届次 to majors or grades: `all`, `selected`,
or `unknown`. `selected` requires a non-empty controlled-value list; `all` and
`unknown` must not be inferred from an empty list.
_Avoid_: 用空数组同时表示全部适用和资料缺失

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

**账号标识**:
A typed identity bound to one user: `student_no`, `email`, or `phone`. Login
selects the type explicitly and compares its normalized value only within that
type; it never searches unrelated identity fields and uses a password to guess
which user was intended.
_Avoid_: 无类型 account 字段, 跨字段密码消歧

**账号激活**:
The controlled transition from `pending_activation` to `active` after an
account identity has been verified through an enabled channel or an
institution-managed provisioning path. Creating an account does not itself
create an authenticated session.
_Avoid_: 注册即登录, 未验证账号

**密码凭据**:
The full user-chosen passphrase used as the current P1 single authentication
factor. It favors length and a local weak-password blocklist over character
composition rules, and is stored only through an explicitly configured adaptive
password hash.
_Avoid_: 密码明文, 一位密码, 强制字符组合

**会话版本**:
A server-authoritative counter on a user account that is copied into each
signed cookie session. A session is valid only while its version matches the
account; incrementing it terminates all existing sessions on their next request.
_Avoid_: 仅删除浏览器 Cookie, 禁用后仍有效的 session

**推荐就绪画像**:
A student profile whose current `college`, `major`, `grade`, and at least one
interest tag pass the deployment dictionaries and cross-field validation. It is
a dynamically derived state used to select personalized or general
recommendations, not a stored approval flag.
_Avoid_: 空画像个性化, 持久化完成布尔值

**提醒确认**:
The explicit student confirmation of whether one赛事届次 subscription should
create in-app reminder plans, for which controlled node types, and with what
single advance-day offset. Displayed defaults prefill the choice but do not
replace confirmation.
_Avoid_: 收藏触发提醒, 静默默认同意

**站内消息**:
A durable, user-visible snapshot created when a reminder or subscribed赛事 event
is delivered. It has an independent read state and 365-day retention; it is not
the future reminder plan itself.
_Avoid_: 待发送提醒, 可重写历史消息

**外链点击事件**:
A privacy-minimized, best-effort record that an official, source, or attachment
link was activated from a controlled product surface. It counts clicks rather
than people or completed registrations and never blocks external navigation.
_Avoid_: 报名转化, 用户行为画像, 跳转前置埋点

**赛事治理工作台**:
The required administrator UI for editing, submitting, independently reviewing,
publishing, and maintaining赛事 revisions. API, CLI, and seed paths support it
but do not substitute for product acceptance.
_Avoid_: API-only 后台, 单账号自审演示

**推荐规则集**:
An immutable, versioned set of controlled recommendation rules and internal
weights. One independently reviewed version is active at a time; public results
expose its version and reasons, never its internal score.
_Avoid_: service 常量, 原地改权重, 可执行规则脚本

**推荐曝光**:
A best-effort record that one item from a specific recommendation response was
actually rendered. It can be paired with at most one recorded click for
aggregate click-through statistics without identifying the student.
_Avoid_: API 返回即曝光, 用户级推荐追踪

**治理证据**:
The read-only combination of review decisions, immutable audit events, and
defined operational statistics used to explain product state and activity. None
of the three substitutes for the others.
_Avoid_: 可编辑审计记录, 无口径统计大屏

**管理员**:
The current management role responsible for赛事录入, 审核发布, status maintenance, configuration, user management, and audit-oriented operations.
_Avoid_: 运营人员, 后台用户

**赛事编辑权限**:
An administrator capability to create and revise赛事届次 and submit a specific
revision for review. It is a permission within the管理员 role, not a separate
formal user role.
_Avoid_: 赛事审核权限, 新用户角色

**赛事审核权限**:
An administrator capability to approve, reject, or return a submitted赛事届次
revision. A person may hold both editor and reviewer permissions but cannot
review a revision they submitted.
_Avoid_: 自审权限, 新用户角色

**赛事维护权限**:
An administrator capability to cancel, expire, archive, or urgently offline a
published赛事届次 with required impact context and audit reason. It does not
authorize editing or approving a revision, and restoration still requires an
independently reviewed corrected revision.
_Avoid_: 赛事编辑权限, 赛事审核权限, 直接恢复发布

**用户治理权限**:
An administrator capability to list governed accounts and change another
account's role, status, or controlled capabilities. It cannot target its own
holder, and the system always retains at least one active holder.
_Avoid_: 普通管理员权限, 自我授权, 唯一管理员锁死

**辅助干系人**:
Teachers, teaching secretaries, competition organizers, and student organizations whose needs inform the system without being current formal product roles.
_Avoid_: 正式用户角色

**收藏**:
A student's lightweight saved reference to one赛事届次 for later viewing. 收藏
does not generate reminders or calendar nodes by itself and does not
automatically carry to a future届次 in the same赛事系列.
_Avoid_: 订阅, 关注

**订阅**:
A student's active decision to follow one赛事届次 and its time nodes. 订阅 can
generate站内提醒 and personal calendar nodes according to reminder settings,
but it does not automatically subscribe the student to a future届次 in the same
赛事系列.
_Avoid_: 收藏, 关注

**关注赛事系列**:
A separate, future opt-in to learn that a new赛事届次 has been published in a
赛事系列. It may announce the new届次, but it must not create a届次订阅 or deadline
reminders without a new student action.
_Avoid_: 订阅赛事届次, 自动续订

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
