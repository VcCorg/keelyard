// Utility functions for the dashboard

export function cn(...classes: (string | undefined | false)[]): string {
  return classes
    .filter((c): c is string => typeof c === 'string' && c.length > 0)
    .join(' ');
}

export function formatBytes(bytes: number): string {
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  if (bytes === 0) return '0 B';
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${(ms / 60000).toFixed(1)}m`;
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'running':
    case 'healthy':
    case 'success':
      return 'text-emerald-600 dark:text-emerald-400';
    case 'stopped':
    case 'unhealthy':
    case 'warning':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'failed':
    case 'error':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

export function getStatusBgColor(status: string): string {
  switch (status) {
    case 'running':
    case 'healthy':
    case 'success':
      return 'bg-emerald-50 dark:bg-emerald-900/20';
    case 'stopped':
    case 'unhealthy':
    case 'warning':
      return 'bg-yellow-50 dark:bg-yellow-900/20';
    case 'failed':
    case 'error':
      return 'bg-red-50 dark:bg-red-900/20';
    default:
      return 'bg-gray-50 dark:bg-gray-900/20';
  }
}
