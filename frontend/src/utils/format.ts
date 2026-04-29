export function formatDateTime(value?: string, fallback = '-') {
  if (!value) return fallback;
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}
