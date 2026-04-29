import request from './request';

export function getMe() {
  return request.get('/users/me') as Promise<unknown>;
}

export function updateProfile(payload: Record<string, unknown>) {
  return request.put('/users/me/profile', payload) as Promise<unknown>;
}
