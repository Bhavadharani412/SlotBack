import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { Appointment, Service } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import {
  Plus,
  Search,
  Filter,
  XCircle,
  CheckCircle2,
  Calendar as CalendarIcon,
  AlertCircle,
} from 'lucide-react';

export const AppointmentsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [services, setServices] = useState<Service[]>([]);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [serviceFilter, setServiceFilter] = useState<string>('all');

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [cancellationReason, setCancellationReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    service_id: '',
    date: '',
    time: '09:00',
  });

  const loadAppointments = async () => {
    try {
      setLoading(true);
      setError(null);
      const [appData, serviceData] = await Promise.all([
        api.getAppointments(),
        api.getServices(true),
      ]);
      setAppointments(appData);
      setServices(serviceData);
      if (serviceData.length > 0 && !formData.service_id) {
        setFormData((prev) => ({ ...prev, service_id: serviceData[0].id }));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load appointments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAppointments();
    if (searchParams.get('action') === 'new') {
      setCreateModalOpen(true);
    }
  }, []);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    if (!formData.customer_name || !formData.customer_email || !formData.customer_phone || !formData.date) {
      setActionError('Please fill in all required fields.');
      return;
    }
    try {
      setActionLoading(true);
      const startTime = new Date(`${formData.date}T${formData.time}:00`).toISOString();
      await api.createAppointment({
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        customer_phone: formData.customer_phone,
        service_id: formData.service_id,
        start_time: startTime,
      });
      setCreateModalOpen(false);
      setFormData({
        customer_name: '',
        customer_email: '',
        customer_phone: '',
        service_id: services[0]?.id || '',
        date: '',
        time: '09:00',
      });
      loadAppointments();
    } catch (err: any) {
      setActionError(err.message || 'Failed to create booking');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelConfirm = async () => {
    if (!selectedAppointment) return;
    try {
      setActionLoading(true);
      setActionError(null);
      await api.cancelAppointment(selectedAppointment.id, cancellationReason);
      setCancelModalOpen(false);
      setSelectedAppointment(null);
      setCancellationReason('');
      loadAppointments();
    } catch (err: any) {
      setActionError(err.message || 'Failed to cancel appointment');
    } finally {
      setActionLoading(false);
    }
  };

  const filteredAppointments = appointments.filter((app) => {
    const matchesSearch =
      app.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.customer_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.customer_phone.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || app.status === statusFilter;
    const matchesService = serviceFilter === 'all' || app.service_id === serviceFilter;
    return matchesSearch && matchesStatus && matchesService;
  });

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1>Appointments Directory</h1>
          <p>Schedule, manage, and cancel customer appointment bookings.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreateModalOpen(true)}>
          <Plus size={16} /> New Booking
        </button>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div style={{ display: 'flex', gap: '0.75rem', flex: 1, flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search by customer name, email, phone..."
              className="form-input search-input"
              style={{ paddingLeft: '32px' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <select
            className="form-select"
            style={{ width: '160px' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="scheduled">Scheduled</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </select>

          <select
            className="form-select"
            style={{ width: '180px' }}
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
          >
            <option value="all">All Services</option>
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <EmptyState title="Error Loading Appointments" description={error} isError action={<button className="btn btn-primary" onClick={loadAppointments}>Retry</button>} />
      ) : filteredAppointments.length === 0 ? (
        <EmptyState
          title="No Appointments Found"
          description={searchQuery || statusFilter !== 'all' ? 'No appointments match your search criteria.' : 'Create a booking to get started.'}
          action={<button className="btn btn-primary" onClick={() => setCreateModalOpen(true)}>Book Appointment</button>}
        />
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Service</th>
                <th>Date & Time</th>
                <th>Status</th>
                <th>Recovery</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAppointments.map((app) => (
                <tr key={app.id}>
                  <td>
                    <strong style={{ display: 'block' }}>{app.customer_name}</strong>
                    <span className="text-muted">{app.customer_email} • {app.customer_phone}</span>
                  </td>
                  <td>
                    <strong>{app.service?.name || 'N/A'}</strong>
                    <div className="text-muted">${app.service?.price} • {app.service?.duration_minutes} min</div>
                  </td>
                  <td>
                    {new Date(app.start_time).toLocaleString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
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
                  <td>
                    {app.status === 'scheduled' && (
                      <button
                        className="btn btn-sm btn-ghost"
                        style={{ color: 'var(--danger)' }}
                        onClick={() => {
                          setSelectedAppointment(app);
                          setCancelModalOpen(true);
                        }}
                      >
                        <XCircle size={14} /> Cancel
                      </button>
                    )}
                    {app.status === 'cancelled' && (
                      <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                        {app.cancellation_reason || 'Cancelled'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: Create Booking */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Schedule New Appointment"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleCreateSubmit} disabled={actionLoading}>
              {actionLoading ? 'Saving...' : 'Confirm Booking'}
            </button>
          </>
        }
      >
        {actionError && (
          <div className="alert alert-danger">
            <AlertCircle size={16} />
            <span>{actionError}</span>
          </div>
        )}
        <form onSubmit={handleCreateSubmit}>
          <div className="form-group">
            <label className="form-label">Customer Full Name *</label>
            <input
              type="text"
              className="form-input"
              required
              value={formData.customer_name}
              onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Customer Email *</label>
            <input
              type="email"
              className="form-input"
              required
              value={formData.customer_email}
              onChange={(e) => setFormData({ ...formData, customer_email: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Phone Number *</label>
            <input
              type="text"
              className="form-input"
              required
              value={formData.customer_phone}
              onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Service *</label>
            <select
              className="form-select"
              required
              value={formData.service_id}
              onChange={(e) => setFormData({ ...formData, service_id: e.target.value })}
            >
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} (${s.price} - {s.duration_minutes} min)
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Date *</label>
              <input
                type="date"
                className="form-input"
                required
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Time *</label>
              <input
                type="time"
                className="form-input"
                required
                value={formData.time}
                onChange={(e) => setFormData({ ...formData, time: e.target.value })}
              />
            </div>
          </div>
        </form>
      </Modal>

      {/* Modal: Cancel Appointment */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        title="Cancel Appointment"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCancelModalOpen(false)}>
              Keep Appointment
            </button>
            <button className="btn btn-danger" onClick={handleCancelConfirm} disabled={actionLoading}>
              {actionLoading ? 'Cancelling...' : 'Confirm Cancellation'}
            </button>
          </>
        }
      >
        {actionError && (
          <div className="alert alert-danger">
            <AlertCircle size={16} />
            <span>{actionError}</span>
          </div>
        )}
        <p style={{ marginBottom: '1rem' }}>
          Are you sure you want to cancel the booking for <strong>{selectedAppointment?.customer_name}</strong>?
          This will release the slot and automatically search eligible waitlisted customers for recovery.
        </p>
        <div className="form-group">
          <label className="form-label">Cancellation Reason (Optional)</label>
          <textarea
            className="form-textarea"
            rows={3}
            placeholder="e.g. Schedule conflict, Customer sickness..."
            value={cancellationReason}
            onChange={(e) => setCancellationReason(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  );
};
