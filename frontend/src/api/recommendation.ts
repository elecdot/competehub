import request from './request';
import type { Competition } from './types';

export function getRecommendations(limit = 20) {
  return request.get('/recommendations', { params: { limit } }) as Promise<Competition[]>;
}

export function updateRecommendationPreferences(payload: Record<string, unknown>) {
  return request.put('/recommendations/preferences', payload) as Promise<unknown>;
}
