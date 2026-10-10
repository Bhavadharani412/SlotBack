import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Appointment, RecoveryOffer, WaitlistEntry } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import {
  RefreshCw,
  Send,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ExternalLink,
  RotateCw,
  Clock,
} from 'lucide-react';

export const RecoveryPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offers, setOffers] = useState<RecoveryOffer[]>([]);
  const [cancelledAppointments, setCancelledAppointments] = useState<Appointment[]>([]);
  const [activeWaitlist, setActiveWaitlist] = useState<WaitlistEntry[]>([]);

  // Modal: Issue Recovery Offer
  const [issueModalOpen, setIssueModalOpen] = useState(false);
  const [selectedAppointmentId, setSelectedAppointmentId] = useState('');
  const [selectedWaitlistId, setSelectedWaitlistId] = useState('');
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [offerData, appData, wlData] = await Promise.all([
        api.getOffers(),
        api.getAppointments({ status: 'cancelled' }),
        api.getWaitlist('active'),
      ]);
      setOffers(offerData);
      setCancelledAppointments(appData);
      setActiveWaitlist(wlData);

      if (appData.length > 0 && !selectedAppointmentId) {
        setSelectedAppointmentId(appData[0].id);
      }
      if (wlData.length > 0 && !selectedWaitlistId) {
        setSelectedWaitlistId(wlData[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load recovery data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleIssueSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppointmentId || !selectedWaitlistId) {
      setActionError('Please select both a cancelled slot and an eligible waitlisted customer.');
      return;
    }
    try {
      setActionLoading(true);
      setActionError(null);
      await api.createOffer({
        appointment_id: selectedAppointmentId,
        waitlist_id: selectedWaitlistId,
        expiry_minutes: 60,
      });
      setIssueModalOpen(false);
      loadData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to issue offer');
    } finally {
      setActionLoading(false);
    }
  };

  const handleWithdrawOffer = async (id: string) => {
    if (!window.confirm('Withdraw this recovery offer? The customer will no longer be able to accept it.')) return;
    try {
      await api.withdrawOffer(id);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to withdraw offer');
    }
  };

  const handleRetryNotification = async (logId: string) => {
    try {
      await api.retryNotification(logId);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to retry notification delivery');
    }
  };

  // Find unoffered released slots
  const unofferedSlots = cancelledAppointments.filter(
    (app) => !offers.some((o) => o.appointment_id === app.id && o.status !== 'withdrawn' && o.status !== 'expired')
  );

  // Determine eligible waitlist for selected appointment
  const selectedAppointment = cancelledAppointments.find(a => a.id === selectedAppointmentId);
  const eligibleWaitlist = activeWaitlist.filter(w => {
    if (!selectedAppointment) return false;
    if (w.service_id !== selectedAppointment.service_id) return false;
    const prefStart = new Date(w.preferred_start_date).getTime();
    const prefEnd = new Date(w.preferred_end_date).getTime();
    const apptStart = new Date(selectedAppointment.start_time).getTime();
    return prefStart <= apptStart && prefEnd >= apptStart;
  });

  // Keep selected waitlist ID in sync when selected appointment changes
  useEffect(() => {
    if (eligibleWaitlist.length > 0) {
      if (!eligibleWaitlist.some(w => w.id === selectedWaitlistId)) {
        setSelectedWaitlistId(eligibleWaitlist[0].id);
      }
    } else {
      setSelectedWaitlistId('');
    }
  }, [selectedAppointmentId, eligibleWaitlist, selectedWaitlistId]);


  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Slot Recovery & Offer Management</h1>
          <p>Match released cancelled slots to waitlisted customers and monitor real-time offer states.</p>
        </div>
        <div className="page-header-actions">
          <button className="btn btn-secondary" onClick={loadData}>
            <RefreshCw size={16} /> Refresh
          </button>
          <button className="btn btn-primary" onClick={() => setIssueModalOpen(true)}>
            <Send size={16} /> Issue Recovery Offer
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <EmptyState title="Error Loading Recovery Data" description={error} isError action={<button className="btn btn-primary" onClick={loadData}>Retry</button>} />
      ) : (
        <>
          {/* Released Slots Pending Offer */}
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={18} color="var(--warning)" />
                <h3>Released Slots Available for Recovery ({unofferedSlots.length})</h3>
              </div>
            </div>
            {unofferedSlots.length === 0 ? (
              <p className="text-muted" style={{ padding: '0.5rem 0' }}>All cancelled slots have active or completed recovery workflows.</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
                {unofferedSlots.map((slot) => (
                  <div
                    key={slot.id}
                    style={{
                      padding: '1rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      backgroundColor: 'var(--surface-hover)',
                    }}
                  >
                    <strong style={{ display: 'block', marginBottom: '0.25rem' }}>
                      {slot.service?.name || 'Service'} (${slot.service?.price})
                    </strong>
                    <div className="text-muted" style={{ fontSize: '0.8125rem', marginBottom: '0.75rem' }}>
                      Released: {new Date(slot.start_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                    </div>
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => {
                        setSelectedAppointmentId(slot.id);
                        setIssueModalOpen(true);
                      }}
                    >
                      <Send size={14} /> Match & Offer Slot
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recovery Offers Table */}
          <div className="card">
            <div className="card-header">
              <h3>Persisted Recovery Offers ({offers.length})</h3>
            </div>
            {offers.length === 0 ? (
              <EmptyState title="No Recovery Offers Issued" description="Issued recovery offers will appear here with delivery and acceptance tracking." />
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Offered Slot</th>
                      <th>Waitlisted Customer</th>
                      <th>Offer Expiry</th>
                      <th>Status</th>
                      <th>Notification Delivery</th>
                      <th style={{ minWidth: '150px', whiteSpace: 'nowrap' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {offers.map((offer) => {
                      const notif = offer.notification_logs[0];
                      const isExpired = new Date(offer.expires_at) < new Date();
                      return (
                        <tr key={offer.id}>
                          <td>
                            <strong>{offer.appointment?.service?.name || 'Service'}</strong>
                            <div className="text-muted">
                              {new Date(offer.appointment?.start_time || offer.created_at).toLocaleString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit',
                              })}
                            </div>
                          </td>
                          <td>
                            <strong>{offer.waitlist_entry?.customer_name || 'Customer'}</strong>
                            <div className="text-muted">{offer.waitlist_entry?.customer_email}</div>
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                              <Clock size={14} color={isExpired ? 'var(--danger)' : 'var(--text-muted)'} />
                              <span>{new Date(offer.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                            </div>
                          </td>
                          <td>
                            <StatusBadge status={offer.status} type="offer" />
                          </td>
                          <td>
                            {notif ? (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <StatusBadge status={notif.status} type="notification" />
                                {notif.status === 'failed' && (
                                  <button
                                    className="btn btn-sm btn-secondary"
                                    title={notif.error_message || 'Retry delivery'}
                                    onClick={() => handleRetryNotification(notif.id)}
                                  >
                                    <RotateCw size={12} /> Retry
                                  </button>
                                )}
                              </div>
                            ) : (
                              <span className="text-muted">Pending Log</span>
                            )}
                          </td>
                          <td style={{ minWidth: '150px', whiteSpace: 'nowrap' }}>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'nowrap' }}>
                              <a
                                href={`/offer/${offer.token}`}
                                target="_blank"
                                rel="noreferrer"
                                className="btn btn-sm btn-ghost"
                                title="Open customer offer link"
                              >
                                <ExternalLink size={14} /> Link
                              </a>
                              {(offer.status === 'sent' || offer.status === 'pending') && !isExpired && (
                                <button
                                  className="btn btn-sm btn-ghost"
                                  style={{ color: 'var(--danger)' }}
                                  onClick={() => handleWithdrawOffer(offer.id)}
                                >
                                  Withdraw
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Modal: Issue Recovery Offer */}
      <Modal
        isOpen={issueModalOpen}
        onClose={() => setIssueModalOpen(false)}
        title="Issue Waitlist Recovery Offer"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setIssueModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleIssueSubmit} disabled={actionLoading}>
              {actionLoading ? 'Issuing...' : 'Send Recovery Offer'}
            </button>
          </>
        }
      >
        {actionError && (
          <div className="alert alert-danger">
            <AlertTriangle size={16} />
            <span>{actionError}</span>
          </div>
        )}
        <form onSubmit={handleIssueSubmit}>
          <div className="form-group">
            <label className="form-label">Select Released Cancelled Slot *</label>
            <select
              className="form-select"
              required
              value={selectedAppointmentId}
              onChange={(e) => setSelectedAppointmentId(e.target.value)}
            >
              {cancelledAppointments.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.service?.name} — {new Date(app.start_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} (Originally: {app.customer_name})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Select Eligible Waitlisted Customer *</label>
            {eligibleWaitlist.length > 0 ? (
              <select
                className="form-select"
                required
                value={selectedWaitlistId}
                onChange={(e) => setSelectedWaitlistId(e.target.value)}
              >
                {eligibleWaitlist.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.customer_name} ({w.customer_email}) — Requested: {w.service?.name || 'Any'}
                  </option>
                ))}
              </select>
            ) : (
              <div className="alert alert-warning" style={{ marginTop: '0.5rem' }}>
                <AlertTriangle size={16} />
                <span>No eligible customers found for this service and time window. They may be booked or none match.</span>
              </div>
            )}
          </div>
        </form>
      </Modal>
    </div>
  );
};
