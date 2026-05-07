import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
});

export const ubidApi = {
  list: (
    page: number = 1,
    pageSize: number = 50,
    name: string = '',
    filters?: import('./api/types').FilterState
  ) => {
    const params: any = { page, page_size: pageSize };
    if (name) params.name = name;
    if (filters) {
      if (filters.activity_status.length > 0) params.activity_status = filters.activity_status.join(',');
      if (filters.departments.length > 0) params.departments = filters.departments.join(',');
      if (filters.pincode && filters.pincode.trim()) params.pincode = filters.pincode.trim();
    }
    return api.get(`/api/ubid/list`, { params });
  },
  lookup: (pan?: string, gstin?: string) =>
    api.get(`/api/ubid/lookup`, { params: { pan, gstin } }),
  getDetail: (ubid: string) =>
    api.get(`/api/ubid/${ubid}`),
  getFullDetail: (ubid: string) =>
    api.get(`/api/ubid/${ubid}/full-details`),
  getFilters: () =>
    api.get(`/api/ubid/filters`),
  getIntelligence: (ubid: string) =>
    api.get(`/api/ubid/${ubid}/intelligence`),
  revertLink: (data: import('./api/types').RevertLinkRequest) =>
    api.post(`/api/ubid/revert-link`, data),
  export: (ubid: string, format: 'json' | 'csv' = 'csv') =>
    api.get(`/api/ubid/${ubid}/export`, { params: { format }, responseType: 'blob' }),
};

export const activityApi = {
  getStats: () =>
    api.get(`/api/activity/stats`),
  query: (status?: string, pincode?: string, sector_nic?: string, no_inspection_days?: number) =>
    api.get(`/api/activity/query`, { params: { status, pincode, sector_nic, no_inspection_days } }),
  getTimeline: (ubid: string) =>
    api.get(`/api/activity/${ubid}/timeline`),
  getSectorBreakdown: (businesses: any[]) =>
    api.post(`/api/activity/sector-breakdown`, { businesses }),
};

export const reviewApi = {
  getQueue: (status: string = 'PENDING', page: number = 1, pageSize: number = 20) =>
    api.get(`/api/review/queue`, { params: { status, page, page_size: pageSize } }),
  getTask: (taskId: string) =>
    api.get(`/api/review/task/${taskId}`),
  submitDecision: (taskId: string, decision: string, reason: string = '') =>
    api.post(`/api/review/task/${taskId}/decision`, { decision, reason, reviewer_id: 'admin' }),
  getStats: () =>
    api.get(`/api/review/stats`),
};

export const adminApi = {
  getModelStats: () => api.get(`/api/admin/model-stats`),
  getAuditLog: (limit: number = 50) => api.get(`/api/admin/audit-log`, { params: { limit } }),
  triggerPipeline: () => api.post(`/api/admin/pipeline/run`),
  triggerReroute: () => api.post(`/api/admin/pipeline/reroute`),
  getPipelineStatus: (taskId: string) => api.get(`/api/admin/pipeline/status/${taskId}`),
};

export const nlApi = {
  query: (query: string) =>
    api.post(`/api/nl-query`, { query }),
};

export default api;
