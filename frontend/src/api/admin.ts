import request from './request';
import type { CertificationRequest, Competition, ForumPost, PageResult, User } from './types';

export function getStatistics() {
  return request.get('/admin/statistics') as Promise<Record<string, number>>;
}

export function getAdminCompetitions(params: Record<string, unknown>) {
  return request.get('/admin/competitions', { params }) as Promise<PageResult<Competition>>;
}

export function getAdminUsers() {
  return request.get('/admin/users') as Promise<Array<User & Record<string, unknown>>>;
}

export function getAdminPosts(params: Record<string, unknown>) {
  return request.get('/admin/posts', { params }) as Promise<ForumPost[]>;
}

export function deleteAdminPost(id: number) {
  return request.delete(`/admin/posts/${id}`) as Promise<ForumPost>;
}

export function getAdminCertifications() {
  return request.get('/admin/certifications') as Promise<CertificationRequest[]>;
}

export function reviewCertification(id: number, payload: Record<string, unknown>) {
  return request.put(`/admin/certifications/${id}`, payload) as Promise<CertificationRequest>;
}
