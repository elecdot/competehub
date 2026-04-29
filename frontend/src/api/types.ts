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
  title: string;
  content: string;
  post_type: string;
  status: string;
  view_count: number;
  like_count: number;
  created_at: string;
}

