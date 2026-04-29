import request from './request';
import type { Competition, PageResult } from './types';

export function getStatistics() {
  return request.get('/admin/statistics') as Promise<Record<string, number>>;
}

export function getAdminCompetitions(params: Record<string, unknown>) {
  return request.get('/admin/competitions', { params }) as Promise<PageResult<Competition>>;
}
