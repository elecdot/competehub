import axios from 'axios'

import type {
  ApiEnvelope,
  CompetitionDetail,
  CompetitionListPayload,
  ParticipantForm,
} from '@/types/competition'
import type {
  CurrentUserResponse,
  LoginPayload,
  ProfileOptions,
  StudentProfile,
  StudentProfileUpdate,
} from '@/types/auth'

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
