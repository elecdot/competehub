import type { SubscriptionNodeType } from './competition'

export type Role = 'student' | 'admin' | 'teacher' | 'organizer'

export type ProfileStatus = 'incomplete' | 'recommendation_ready'

export type IdentityType = 'email' | 'phone' | 'student_no'

export interface CurrentUserResponse {
  id: number
  display_name: string | null
  role: Role
  capabilities: string[]
}

export interface CurrentUser {
  id: number
  displayName: string | null
  role: Role
  capabilities: string[]
}

export interface StudentProfile {
  id: number
  user_id: number
  college: string | null
  major: string | null
  grade: string | null
  interest_tags: string[]
  competition_experience: string | null
  goal_preferences: string[]
  blocked_tags: string[]
  default_remind_days: number
  message_enabled: boolean
  default_reminder_node_types: SubscriptionNodeType[]
  profile_status: ProfileStatus
  missing_fields: string[]
}

export interface LoginPayload {
  identity_type: IdentityType
  identifier: string
  password: string
}

export interface StudentProfileUpdate {
  college?: string | null
  major?: string | null
  grade?: string | null
  interest_tags?: string[]
}

export interface ProfileOptions {
  colleges: string[]
  majors_by_college: Record<string, string[]>
  grades: string[]
  interest_tags: string[]
}
