import { defineStore } from 'pinia';
import { login as loginApi, type LoginPayload } from '@/api/auth';
import type { User } from '@/api/types';

interface AuthState {
  token: string;
  user: User | null;
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('access_token') || '',
    user: JSON.parse(localStorage.getItem('current_user') || 'null') as User | null,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    role: (state) => state.user?.role || 'guest',
  },
  actions: {
    async login(payload: LoginPayload) {
      const data = await loginApi(payload);
      this.token = data.access_token;
      this.user = data.user;
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('current_user', JSON.stringify(data.user));
    },
    logout() {
      this.token = '';
      this.user = null;
      localStorage.removeItem('access_token');
      localStorage.removeItem('current_user');
    },
  },
});

