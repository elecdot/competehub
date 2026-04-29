import request from './request';
import type { CertificationRequest, MatchmakingUser } from './types';

export function getMe() {
  return request.get('/users/me') as Promise<unknown>;
}

export function updateProfile(payload: Record<string, unknown>) {
  return request.put('/users/me/profile', payload) as Promise<unknown>;
}

export function getCertifications() {
  return request.get('/users/me/certifications') as Promise<CertificationRequest[]>;
}

export function createCertification(payload: Record<string, unknown>) {
  return request.post('/users/me/certifications', payload) as Promise<CertificationRequest>;
}

export function getMatchmakingUsers(params: Record<string, unknown>) {
  return request.get('/users/matchmaking', { params }) as Promise<MatchmakingUser[]>;
}
