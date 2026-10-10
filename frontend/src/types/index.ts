export interface Service {
  id: string;
  name: string;
  description?: string;
  duration_minutes: number;
  price: number;
  is_active: boolean;
  created_at: string;
}

export interface Appointment {
  id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  service_id: string;
  start_time: string;
  end_time: string;
  status: 'scheduled' | 'completed' | 'cancelled' | 'no_show';
  cancellation_reason?: string;
  cancelled_at?: string;
  is_recovery: boolean;
  created_at: string;
  service?: Service;
}

export interface WaitlistEntry {
  id: string;
  customer_name: string;
  customer_email: string;
  customer_phone: string;
  service_id: string;
  preferred_start_date: string;
  preferred_end_date: string;
  notes?: string;
  status: 'active' | 'offered' | 'fulfilled' | 'cancelled';
  created_at: string;
  service?: Service;
}

export interface NotificationLog {
  id: string;
  offer_id: string;
  recipient_email: string;
  channel: string;
  status: 'delivered' | 'failed';
  retry_count: number;
  error_message?: string;
  sent_at: string;
}

export interface RecoveryOffer {
  id: string;
  appointment_id: string;
  waitlist_id: string;
  token: string;
  status: 'pending' | 'sent' | 'accepted' | 'expired' | 'withdrawn';
  expires_at: string;
  sent_at?: string;
  accepted_at?: string;
  created_at: string;
  appointment?: Appointment;
  waitlist_entry?: WaitlistEntry;
  notification_logs: NotificationLog[];
}

export interface BusinessSetting {
  business_name: string;
  default_offer_expiry_minutes: number;
  notification_email: string;
  auto_match_waitlist: boolean;
  updated_at: string;
}

export interface Metrics {
  eligible_cancellations: number;
  recovered_appointments: number;
  recovery_rate: number;
  time_to_refill_median_minutes: number | null;
  notification_failure_rate: number;
  total_active_waitlist: number;
  active_offers_count: number;
  period: string;
}

export interface OfferAcceptResponse {
  message: string;
  status: string;
  appointment: Appointment;
  offer: RecoveryOffer;
}
