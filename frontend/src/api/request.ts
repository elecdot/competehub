import axios from 'axios';
import { ElMessage } from 'element-plus';
import type { ApiResponse } from './types';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15000,
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response): any => {
    const payload = response.data as ApiResponse<unknown>;
    if (payload.code !== 0) {
      ElMessage.error(payload.message || '请求失败');
      return Promise.reject(payload);
    }
    return payload.data;
  },
  (error) => {
    const message = error.response?.data?.message || error.message || '网络异常';
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('current_user');
    }
    ElMessage.error(message);
    return Promise.reject(error);
  },
);

export default request;
