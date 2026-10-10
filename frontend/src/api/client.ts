import {
  Appointment,
  BusinessSetting,
  Metrics,
  NotificationLog,
  OfferAcceptResponse,
  RecoveryOffer,
  Service,
  User,
  WaitlistEntry,
} from '../types';

const API_BASE = '/api/v1';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('slotback_token') : null;
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};

  const response = await fetch(`${API_BASE}${url}`, {
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let errorMsg = `API request failed with status ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
      }
    } catch {
      // fallback
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export const api = {
  // Services
  getServices: (activeOnly = false): Promise<Service[]> =>
    fetchJson(`/services${activeOnly ? '?active_only=true' : ''}`),
  createService: (data: Partial<Service>): Promise<Service> =>
    fetchJson('/services', { method: 'POST', body: JSON.stringify(data) }),
  updateService: (id: string, data: Partial<Service>): Promise<Service> =>
    fetchJson(`/services/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Appointments
  getAppointments: (params?: { date?: string; service_id?: string; status?: string }): Promise<Appointment[]> => {
    const query = new URLSearchParams();
    if (params?.date) query.append('date', params.date);
    if (params?.service_id) query.append('service_id', params.service_id);
    if (params?.status) query.append('status', params.status);
    const qStr = query.toString();
    return fetchJson(`/appointments${qStr ? `?${qStr}` : ''}`);
  },
  createAppointment: (data: {
    customer_name: string;
    customer_email: string;
    customer_phone: string;
    service_id: string;
    start_time: string;
  }): Promise<Appointment> =>
    fetchJson('/appointments', { method: 'POST', body: JSON.stringify(data) }),
  cancelAppointment: (id: string, reason?: string): Promise<Appointment> =>
    fetchJson(`/appointments/${id}/cancel`, { method: 'POST', body: JSON.stringify({ reason }) }),

  // Waitlist
  getWaitlist: (status?: string): Promise<WaitlistEntry[]> =>
    fetchJson(`/waitlist${status ? `?status=${status}` : ''}`),
  createWaitlistEntry: (data: {
    customer_name: string;
    customer_email: string;
    customer_phone: string;
    service_id: string;
    preferred_start_date: string;
    preferred_end_date: string;
    notes?: string;
  }): Promise<WaitlistEntry> =>
    fetchJson('/waitlist', { method: 'POST', body: JSON.stringify(data) }),
  cancelWaitlistEntry: (id: string): Promise<WaitlistEntry> =>
    fetchJson(`/waitlist/${id}`, { method: 'DELETE' }),

  // Recovery & Offers
  getOffers: (): Promise<RecoveryOffer[]> => fetchJson('/recovery/offers'),
  createOffer: (data: {
    appointment_id: string;
    waitlist_id: string;
    expiry_minutes?: number;
    simulate_notification_failure?: boolean;
  }): Promise<RecoveryOffer> =>
    fetchJson('/recovery/offers', { method: 'POST', body: JSON.stringify(data) }),
  getOfferByToken: (tokenOrId: string): Promise<RecoveryOffer> =>
    fetchJson(`/recovery/offers/${tokenOrId}`),
  acceptOffer: (tokenOrId: string): Promise<OfferAcceptResponse> =>
    fetchJson(`/recovery/offers/${tokenOrId}/accept`, { method: 'POST' }),
  withdrawOffer: (id: string): Promise<RecoveryOffer> =>
    fetchJson(`/recovery/offers/${id}/withdraw`, { method: 'POST' }),
  retryNotification: (notificationId: string): Promise<NotificationLog> =>
    fetchJson(`/recovery/notifications/${notificationId}/retry`, { method: 'POST' }),

  // Reports
  getMetrics: (): Promise<Metrics> => fetchJson('/reports/metrics'),

  // Settings
  getSettings: (): Promise<BusinessSetting> => fetchJson('/settings'),
  updateSettings: (data: BusinessSetting): Promise<BusinessSetting> =>
    fetchJson('/settings', { method: 'PUT', body: JSON.stringify(data) }),

  // Auth
  login: async (email: string, password: string): Promise<{ access_token: string; user: User }> => {
    const res = await fetchJson<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (res.access_token && typeof window !== 'undefined') {
      localStorage.setItem('slotback_token', res.access_token);
    }
    return res;
  },
  getMe: (): Promise<User> => fetchJson('/auth/me'),
  createStaffUser: (data: {
    email: string;
    password: string;
    full_name: string;
    role: 'admin' | 'staff';
  }): Promise<User> =>
    fetchJson('/auth/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  logout: () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('slotback_token');
    }
  },
};
