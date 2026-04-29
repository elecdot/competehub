export function getToken() {
  return localStorage.getItem('access_token') || '';
}

export function getStoredRole() {
  const user = JSON.parse(localStorage.getItem('current_user') || 'null') as { role?: string } | null;
  return user?.role || 'guest';
}

