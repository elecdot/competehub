import type { CompetitionTimeNode } from '@/types/competition'

const NODE_LABELS: Record<string, string> = {
  registration_start: '报名开始',
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

export function formatNodeLabel(nodeType: string) {
  return NODE_LABELS[nodeType] ?? nodeType
}

export function formatParticipantForm(participantForm?: string | null) {
  if (!participantForm) {
    return '未填写'
  }
  return PARTICIPANT_FORM_LABELS[participantForm] ?? participantForm
}

export function formatNodeDate(node: CompetitionTimeNode, includeTime = false) {
  const timestamp = node.due_at ?? node.starts_at
  if (!timestamp) {
    return '时间待确认'
  }

  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) {
    return '时间待确认'
  }

  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    ...(includeTime ? { timeStyle: 'short' as const } : {}),
  }).format(date)
}
