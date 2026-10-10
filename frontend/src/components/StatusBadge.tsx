import React from 'react';
import { CheckCircle2, Clock, XCircle, AlertTriangle, RefreshCw, Send } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  type?: 'appointment' | 'waitlist' | 'offer' | 'notification';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, type = 'appointment' }) => {
  const normalized = status.toLowerCase();

  let badgeClass = 'badge-neutral';
  let icon = <Clock size={12} />;
  let label = status;

  if (normalized === 'scheduled' || normalized === 'active' || normalized === 'delivered') {
    badgeClass = 'badge-success';
    icon = <CheckCircle2 size={12} />;
  } else if (normalized === 'completed' || normalized === 'fulfilled' || normalized === 'accepted') {
    badgeClass = 'badge-info';
    icon = <CheckCircle2 size={12} />;
  } else if (normalized === 'cancelled' || normalized === 'failed' || normalized === 'withdrawn') {
    badgeClass = 'badge-danger';
    icon = <XCircle size={12} />;
  } else if (normalized === 'offered' || normalized === 'pending' || normalized === 'sent') {
    badgeClass = 'badge-warning';
    icon = normalized === 'sent' ? <Send size={12} /> : <Clock size={12} />;
  } else if (normalized === 'expired') {
    badgeClass = 'badge-neutral';
    icon = <AlertTriangle size={12} />;
  }

  return (
    <span className={`badge ${badgeClass}`}>
      {icon}
      <span>{label.replace('_', ' ')}</span>
    </span>
  );
};
