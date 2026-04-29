export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface User {
  id: number;
  username: string;
  role: string;
  email?: string;
  phone?: string;
  status?: string;
  created_at?: string;
}

export interface AwardExperience {
  competition?: string;
  category?: string;
  level?: string;
  award?: string;
  year?: string;
  evidence_url?: string;
}

export interface TeamPreference {
  looking_for_teammates?: boolean;
  target_competitions?: string[];
  required_awards?: string[];
  required_skills?: string[];
  contact_preference?: string;
}

export interface UserProfile {
  real_name?: string;
  school?: string;
  college?: string;
  major?: string;
  grade?: string;
  interests?: string[];
  competition_experiences?: AwardExperience[];
  goals?: string[];
  ability_level?: string;
  avatar_url?: string;
}

export interface CertificationRequest {
  id: number;
  user_id: number;
  competition_id?: number;
  certification_type: string;
  evidence_url?: string;
  description?: string;
  status: string;
  review_comment?: string;
  created_at: string;
  user?: User;
}

export interface Competition {
  id: number;
  title: string;
  summary?: string;
  description?: string;
  category: string;
  level: string;
  organizer?: string;
  tags: string[];
  status: string;
  registration_deadline_at?: string;
  official_url?: string;
  heat: number;
  score: number;
  recommend_score?: number;
  recommend_reasons?: string[];
}

export interface ForumPost {
  id: number;
  author_id: number;
  title: string;
  content: string;
  post_type: string;
  tags: string[];
  status: string;
  view_count: number;
  like_count: number;
  interest_count?: number;
  interested?: boolean;
  author?: User & { premium?: boolean; certifications?: CertificationRequest[] };
  created_at: string;
}

export interface ForumComment {
  id: number;
  post_id: number;
  author_id: number;
  parent_id?: number;
  content: string;
  status: string;
  created_at: string;
  author?: User & { premium?: boolean; certifications?: CertificationRequest[] };
}

export interface MatchmakingUser {
  user: User;
  profile: UserProfile;
  team_preference: TeamPreference;
  certifications: CertificationRequest[];
  shared_tags: string[];
  match_score: number;
}
