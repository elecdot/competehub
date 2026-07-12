import type { CompetitionLifecycleStatus, CompetitionTimeNode, RegistrationStatus } from '@/types/competition'

const PRODUCT_TIME_ZONE = 'Asia/Shanghai'

const NODE_LABELS: Record<string, string> = {
  registration_start: '报名开始',
  registration_period: '报名期',
  registration_deadline: '报名截止',
  submission_deadline: '作品提交截止',
  competition_start: '比赛开始',
  competition_end: '比赛结束',
  result_announcement: '结果公布',
}

const PARTICIPANT_FORM_LABELS: Record<string, string> = {
  individual: '个人参赛',
  team: '团队参赛',
}

const REGISTRATION_STATUS_LABELS: Record<RegistrationStatus, string> = {
  open: '报名开放',
  upcoming: '即将报名',
  closed: '报名结束',
  unknown: '报名待确认',
  not_applicable: '无需报名',
}

const COMPETITION_STATUS_LABELS: Record<CompetitionLifecycleStatus, string> = {
  published: '公开中',
  cancelled: '已取消',
  archived: '已归档',
  expired: '已过期',
}

export function formatNodeLabel(nodeType: string) {
  return NODE_LABELS[nodeType] ?? nodeType
}

export function formatParticipantForm(participantForm?: string | null) {
  if (!participantForm) {
    return '未填写'
  }
  return PARTICIPANT_FORM_LABELS[participantForm] ?? participantForm
}

export function formatRegistrationStatus(status: RegistrationStatus) {
  return REGISTRATION_STATUS_LABELS[status]
}

export function formatCompetitionStatus(status: CompetitionLifecycleStatus) {
  return COMPETITION_STATUS_LABELS[status]
}

export function formatNodeDate(node: CompetitionTimeNode, includeTime = false) {
  const timestamps = [node.occurs_at, node.starts_at, node.due_at]
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value))
    .filter((value) => !Number.isNaN(value.getTime()))
    .sort((left, right) => left.getTime() - right.getTime())
  if (!timestamps.length) {
    return '时间待确认'
  }

  const now = Date.now()
  const date = timestamps.find((value) => value.getTime() >= now) ?? timestamps[0]

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeZone: PRODUCT_TIME_ZONE,
    ...(includeTime ? { timeStyle: 'short' as const } : {}),
  }).format(date)
}
