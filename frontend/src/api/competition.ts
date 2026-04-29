import request from './request';
import type { Competition, CompetitionOptions, PageResult } from './types';

export function getCompetitions(params: Record<string, unknown>) {
  return request.get('/competitions', { params }) as Promise<PageResult<Competition>>;
}

export function getCompetition(id: number) {
  return request.get(`/competitions/${id}`) as Promise<Competition>;
}

export function getCompetitionOptions() {
  return request.get('/competitions/options') as Promise<CompetitionOptions>;
}

export function favoriteCompetition(id: number) {
  return request.post(`/competitions/${id}/favorite`) as Promise<unknown>;
}

export function subscribeCompetition(id: number, remindDaysBefore = 3) {
  return request.post(`/competitions/${id}/subscribe`, { remind_days_before: remindDaysBefore }) as Promise<unknown>;
}
