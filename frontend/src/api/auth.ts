import request from './request';
import type { User } from './types';

export interface LoginPayload {
  account: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email?: string;
  phone?: string;
  student_no?: string;
  role?: string;
}

export function login(payload: LoginPayload) {
  return request.post('/auth/login', payload) as Promise<{ access_token: string; user: User }>;
}

export function register(payload: RegisterPayload) {
  return request.post('/auth/register', payload) as Promise<User>;
}
