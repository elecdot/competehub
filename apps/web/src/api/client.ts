import axios from 'axios'

import type {
  ApiEnvelope,
  CompetitionDetail,
  CompetitionListPayload,
  ParticipantForm,
} from '@/types/competition'
import type {
  CompetitionRevision,
  CompetitionSeries,
  EditionDraftInput,
  EditionWorkspace,
} from '@/types/admin'

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
  participant_form?: ParticipantForm
  deadline_from?: string
  deadline_to?: string
  page?: number
  page_size?: number
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

export async function submitCompetitionRevision(revisionId: number) {
  const response = await apiClient.post<ApiEnvelope<CompetitionRevision>>(
    `/admin/competition_revisions/${revisionId}/submit_review`,
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
  const response = await apiClient.get<
    ApiEnvelope<{ id: number; role: string; capabilities: string[] }>
  >('/me')
  return response.data.data
}
