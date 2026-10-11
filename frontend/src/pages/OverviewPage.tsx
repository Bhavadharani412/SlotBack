import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Appointment, Metrics, NotificationLog, RecoveryOffer } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import {
  Calendar,
  AlertTriangle,
  RefreshCw,
  Plus,
  ArrowRight,
  Send,
  CheckCircle2,
  Clock,
} from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [offers, setOffers] = useState<RecoveryOffer[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [metricsData, appData, offerData] = await Promise.all([
        api.getMetrics(),
        api.getAppointments(),
        api.getOffers(),
      ]);
      setMetrics(metricsData);
      setAppointments(appData);
      setOffers(offerData);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingSkeleton rows={6} />;

  if (error) {
    return (
      <EmptyState
        title="Failed to Load Dashboard"
        description={error}
        isError
        action={<button className="btn btn-primary" onClick={loadData}>Retry Loading</button>}
      />
    );
  }

  // Derived operational slices
  const urgentCancellations = appointments.filter(
    (a) => a.status === 'cancelled' && !offers.some((o) => o.appointment_id === a.id && o.status === 'accepted')
  );

  const activeOffers = offers.filter((o) => o.status === 'sent' || o.status === 'pending');

  const notificationFailures = offers
    .flatMap((o) => o.notification_logs.map((log) => ({ log, offer: o })))
    .filter(({ log }) => log.status === 'failed');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Staff Operational Dashboard</h1>
          <p>Track cancelled slots, waitlist members, and sent offers.</p>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-secondary" onClick={loadData}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/appointments?action=new')}>
            <Plus size={16} /> Book Appointment
          </button>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-title">Cancelled Slots</span>
          <span className="metric-value">{metrics?.eligible_cancellations ?? 0}</span>
          <span className="metric-subtitle">Open slots to refill</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">Filled Slots</span>
          <span className="metric-value" style={{ color: 'var(--success)' }}>
            {metrics?.recovered_appointments ?? 0}
          </span>
          <span className="metric-subtitle">Claimed from waitlist</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">Refill Rate</span>
          <span className="metric-value" style={{ color: 'var(--primary)' }}>
            {metrics?.recovery_rate ?? 0}%
          </span>
          <span className="metric-subtitle">Filled vs cancelled slots</span>
        </div>
        <div className="metric-card">
          <span className="metric-title">Time to Refill</span>
          <span className="metric-value">
            {metrics?.time_to_refill_median_minutes !== null ? `${metrics?.time_to_refill_median_minutes}m` : 'N/A'}
          </span>
          <span className="metric-subtitle">Average time to fill a slot</span>
        </div>
      </div>

      {/* Urgent Interventions Banner */}
      {notificationFailures.length > 0 && (
        <div className="alert alert-warning">
          <AlertTriangle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1 }}>
            <strong style={{ display: 'block', marginBottom: '0.25rem' }}>
              {notificationFailures.length} Notification Delivery Issue(s)
            </strong>
            <span>Offer messages could not be sent to waiting customers. Retry sending to avoid losing the slot.</span>
          </div>
          <Link to="/recovery" className="btn btn-sm btn-secondary">
            Fix Issues <ArrowRight size={14} />
          </Link>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
        {/* Urgent Cancellations Card */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertTriangle size={18} color="var(--danger)" />
              <h3>Cancelled Slots to Fill ({urgentCancellations.length})</h3>
            </div>
            <Link to="/recovery" className="btn btn-ghost btn-sm">View All</Link>
          </div>
          {urgentCancellations.length === 0 ? (
            <p className="text-muted" style={{ padding: '1rem 0' }}>All cancelled slots have been refilled or have offers sent.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {urgentCancellations.slice(0, 4).map((app) => (
                <div
                  key={app.id}
                  style={{
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--surface-hover)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <strong style={{ display: 'block', fontSize: '0.875rem' }}>
                      {app.service?.name || 'Service'} — {app.customer_name}
                    </strong>
                    <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      {new Date(app.start_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                    </span>
                  </div>
                  <Link to={`/recovery?appointment=${app.id}`} className="btn btn-sm btn-primary">
                    Find Waiting Customer
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Recovery Offers */}
        <div className="card">
          <div className="card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Send size={18} color="var(--primary)" />
              <h3>Sent Offers Pending Reply ({activeOffers.length})</h3>
            </div>
            <Link to="/recovery" className="btn btn-ghost btn-sm">Manage</Link>
          </div>
          {activeOffers.length === 0 ? (
            <p className="text-muted" style={{ padding: '1rem 0' }}>No active offers currently awaiting customer confirmation.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {activeOffers.slice(0, 4).map((offer) => (
                <div
                  key={offer.id}
                  style={{
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <strong style={{ display: 'block', fontSize: '0.875rem' }}>
                      Offer to {offer.waitlist_entry?.customer_name || 'Customer'}
                    </strong>
                    <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      Expires: {new Date(offer.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <StatusBadge status={offer.status} type="offer" />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Today's Appointments Table */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <div className="card-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Calendar size={18} color="var(--primary)" />
            <h3>Recent & Today's Appointments</h3>
          </div>
          <Link to="/appointments" className="btn btn-ghost btn-sm">
            View All Appointments <ArrowRight size={14} />
          </Link>
        </div>

        {appointments.length === 0 ? (
          <EmptyState title="No Appointments" description="No scheduled appointments found for today." />
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Customer</th>
                  <th>Service</th>
                  <th>Date & Time</th>
                  <th>Status</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {appointments.slice(0, 6).map((app) => (
                  <tr key={app.id}>
                    <td>
                      <strong style={{ display: 'block' }}>{app.customer_name}</strong>
                      <span className="text-muted">{app.customer_phone}</span>
                    </td>
                    <td>{app.service?.name || 'N/A'}</td>
                    <td>
                      {new Date(app.start_time).toLocaleString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                      })}
                    </td>
                    <td>
                      <StatusBadge status={app.status} type="appointment" />
                    </td>
                    <td>
                      {app.is_recovery ? (
                        <span className="badge badge-success">
                          <CheckCircle2 size={12} /> Recovered
                        </span>
                      ) : (
                        <span className="badge badge-neutral">Standard</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
