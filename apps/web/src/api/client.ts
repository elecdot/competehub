import axios from 'axios'

import type {
  ApiEnvelope,
  CompetitionDetail,
  CompetitionListPayload,
} from '@/types/competition'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  withCredentials: true,
})

export interface CompetitionListParams {
  keyword?: string
  category?: string
  major?: string
  grade?: string
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
