import request from './request';
import type { ForumComment, ForumPost, PageResult } from './types';

export function getPosts(params: Record<string, unknown>) {
  return request.get('/forum/posts', { params }) as Promise<PageResult<ForumPost>>;
}

export function createPost(payload: Record<string, unknown>) {
  return request.post('/forum/posts', payload) as Promise<ForumPost>;
}

export function getPost(id: number) {
  return request.get(`/forum/posts/${id}`) as Promise<ForumPost>;
}

export function getComments(id: number) {
  return request.get(`/forum/posts/${id}/comments`) as Promise<ForumComment[]>;
}

export function createComment(id: number, payload: Record<string, unknown>) {
  return request.post(`/forum/posts/${id}/comments`, payload) as Promise<ForumComment>;
}

export function markInterest(id: number, payload: Record<string, unknown>) {
  return request.post(`/forum/posts/${id}/interest`, payload) as Promise<Record<string, unknown>>;
}
