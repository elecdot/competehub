import axios from 'axios'

import type {
  ApiEnvelope,
  CompetitionDetail,
  CompetitionListPayload,
  DiscoverySort,
  RegistrationStatus,
  FavoriteState,
  ParticipantForm,
  SubscriptionConsent,
  SubscriptionCancellation,
  SubscriptionSummary,
} from '@/types/competition'
import type {
  CompetitionRevision,
  CompetitionSeries,
  EditionDraftInput,
  EditionWorkspace,
  RevisionDraftUpdate,
} from '@/types/admin'
import type {
  CurrentUserResponse,
  LoginPayload,
  ProfileOptions,
  StudentProfile,
  StudentProfileUpdate,
} from '@/types/auth'
import type { CalendarPayload, CalendarQuery } from '@/types/calendar'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  withCredentials: true,
})

export interface CompetitionListParams {
  keyword?: string
  category?: string
  major?: string
  grade?: string
  tag?: string
  registration_status?: RegistrationStatus
  participant_form?: ParticipantForm
  deadline_from?: string
  deadline_to?: string
  page?: number
  page_size?: number
  sort?: DiscoverySort
}

export async function fetchCompetitions(params: CompetitionListParams = {}) {
  const response = await apiClient.get<ApiEnvelope<CompetitionListPayload>>('/competitions', {
    params,
  })
  return response.data.data
}

export async function fetchCompetitionDetail(id: number) {
  const response = await apiClient.get<ApiEnvelope<CompetitionDetail>>(`/competitions/${id}`)
  return response.data.data
}

export function recordCompetitionOutboundClick(
  id: number,
  targetType: 'source_url' | 'official_url' | 'attachment_url',
  sourceSurface: 'competition_list' | 'competition_detail' | 'recommendation',
) {
  const baseURL = apiClient.defaults.baseURL ?? '/api/v1'
  const url = `${baseURL.replace(/\/$/, '')}/competitions/${id}/outbound_clicks`
  const payload = JSON.stringify({
    target_type: targetType,
    source_surface: sourceSurface,
  })

  try {
    const beacon = new Blob([payload], { type: 'application/json' })
    if (navigator.sendBeacon(url, beacon)) {
      return Promise.resolve()
    }
  } catch {
    // A keepalive request remains available when Beacon is unavailable or rejected.
  }

  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: payload,
    credentials: 'include',
    keepalive: true,
  }).then(() => undefined, () => undefined)
}

export async function favoriteCompetition(id: number) {
  const response = await apiClient.post<ApiEnvelope<FavoriteState>>(`/competitions/${id}/favorite`)
  return response.data.data
}

export async function unfavoriteCompetition(id: number) {
  const response = await apiClient.delete<ApiEnvelope<FavoriteState>>(`/competitions/${id}/favorite`)
  return response.data.data
}

export async function createCompetitionSubscription(id: number, payload: SubscriptionConsent) {
  const response = await apiClient.post<ApiEnvelope<SubscriptionSummary>>(
    `/competitions/${id}/subscription`,
    payload,
  )
  return response.data.data
}

export async function updateCompetitionSubscription(id: number, payload: SubscriptionConsent) {
  const response = await apiClient.patch<ApiEnvelope<SubscriptionSummary>>(
    `/competitions/${id}/subscription`,
    payload,
  )
  return response.data.data
}

export async function cancelCompetitionSubscription(id: number) {
  const response = await apiClient.delete<ApiEnvelope<SubscriptionCancellation>>(
    `/competitions/${id}/subscription`,
  )
  return response.data.data
}

export async function fetchCalendar(params: CalendarQuery) {
  const response = await apiClient.get<ApiEnvelope<CalendarPayload>>('/me/calendar', { params })
  return response.data.data
}

export async function fetchCompetitionSeries() {
  const response = await apiClient.get<ApiEnvelope<{ items: CompetitionSeries[] }>>(
    '/admin/competition_series',
  )
  return response.data.data.items
}

export async function createCompetitionSeries(canonicalName: string) {
  const response = await apiClient.post<ApiEnvelope<CompetitionSeries>>(
    '/admin/competition_series',
    { canonical_name: canonicalName },
  )
  return response.data.data
}

export async function createCompetitionEdition(payload: EditionDraftInput) {
  const response = await apiClient.post<ApiEnvelope<EditionWorkspace>>(
    '/admin/competitions',
    payload,
  )
  return response.data.data
}

export async function createCompetitionSuccessorRevision(
  competitionId: number,
  reason: string,
) {
  const response = await apiClient.post<ApiEnvelope<CompetitionRevision>>(
    `/admin/competitions/${competitionId}/revisions`,
    { reason },
  )
  return response.data.data
}

export async function maintainCompetitionLifecycle(
  competitionId: number,
  status: 'offline' | 'archived' | 'cancelled' | 'expired',
  reason: string,
) {
  const response = await apiClient.patch<ApiEnvelope<{ status: string }>>(
    `/admin/competitions/${competitionId}/status`,
    { status, reason },
  )
  return response.data.data
}

export async function fetchCompetitionEditions() {
  const response = await apiClient.get<ApiEnvelope<{ items: EditionWorkspace[] }>>(
    '/admin/competitions',
  )
  return response.data.data.items
}

export async function updateCompetitionRevision(
  revisionId: number,
  payload: RevisionDraftUpdate,
) {
  const response = await apiClient.patch<ApiEnvelope<CompetitionRevision>>(
    `/admin/competition_revisions/${revisionId}`,
    payload,
  )
  return response.data.data
}

export async function submitCompetitionRevision(revisionId: number) {
  const response = await apiClient.post<ApiEnvelope<CompetitionRevision>>(
    `/admin/competition_revisions/${revisionId}/submit_review`,
  )
  return response.data.data
}

export async function withdrawCompetitionRevision(revisionId: number) {
  const response = await apiClient.post<ApiEnvelope<CompetitionRevision>>(
    `/admin/competition_revisions/${revisionId}/withdraw`,
  )
  return response.data.data
}

export async function fetchPendingCompetitionRevisions() {
  const response = await apiClient.get<ApiEnvelope<{ items: CompetitionRevision[] }>>(
    '/admin/competition_revisions',
    { params: { status: 'pending_review' } },
  )
  return response.data.data.items
}

export async function reviewCompetitionRevision(
  revisionId: number,
  action: 'approve' | 'reject' | 'return',
  comment: string,
) {
  const response = await apiClient.post<ApiEnvelope<CompetitionRevision>>(
    `/admin/competition_revisions/${revisionId}/review`,
    { action, comment },
  )
  return response.data.data
}

export async function fetchCurrentUser() {
  const response = await apiClient.get<ApiEnvelope<CurrentUserResponse>>('/me')
  return response.data.data
}

export async function fetchCurrentProfile() {
  const response = await apiClient.get<ApiEnvelope<StudentProfile>>('/me/profile')
  return response.data.data
}

export async function fetchProfileOptions() {
  const response = await apiClient.get<ApiEnvelope<ProfileOptions>>('/me/profile/options')
  return response.data.data
}

export async function loginCurrentUser(payload: LoginPayload) {
  const response = await apiClient.post<ApiEnvelope<CurrentUserResponse>>('/auth/login', payload)
  return response.data.data
}

export async function updateCurrentProfile(payload: StudentProfileUpdate) {
  const response = await apiClient.patch<ApiEnvelope<StudentProfile>>('/me/profile', payload)
  return response.data.data
}
