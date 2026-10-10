import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Service, WaitlistEntry } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { Modal } from '../components/Modal';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { Plus, Search, Users, AlertCircle, Trash2 } from 'lucide-react';

export const WaitlistPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [waitlist, setWaitlist] = useState<WaitlistEntry[]>([]);
  const [services, setServices] = useState<Service[]>([]);

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('active');

  // Add modal state
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    service_id: '',
    preferred_start_date: '',
    preferred_end_date: '',
    notes: '',
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [wlData, svcData] = await Promise.all([
        api.getWaitlist(),
        api.getServices(true),
      ]);
      setWaitlist(wlData);
      setServices(svcData);
      if (svcData.length > 0 && !formData.service_id) {
        setFormData((prev) => ({ ...prev, service_id: svcData[0].id }));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load waitlist');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setActionError(null);
    if (!formData.customer_name || !formData.customer_email || !formData.customer_phone || !formData.preferred_start_date || !formData.preferred_end_date) {
      setActionError('Please fill in all required fields.');
      return;
    }
    try {
      setActionLoading(true);
      await api.createWaitlistEntry({
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        customer_phone: formData.customer_phone,
        service_id: formData.service_id,
        preferred_start_date: new Date(formData.preferred_start_date).toISOString(),
        preferred_end_date: new Date(formData.preferred_end_date).toISOString(),
        notes: formData.notes,
      });
      setAddModalOpen(false);
      setFormData({
        customer_name: '',
        customer_email: '',
        customer_phone: '',
        service_id: services[0]?.id || '',
        preferred_start_date: '',
        preferred_end_date: '',
        notes: '',
      });
      loadData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to add waitlist entry');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEntry = async (id: string) => {
    if (!window.confirm('Are you sure you want to remove this customer from the waitlist?')) return;
    try {
      await api.cancelWaitlistEntry(id);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel waitlist entry');
    }
  };

  const filtered = waitlist.filter((w) => {
    const matchesSearch =
      w.customer_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.customer_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.customer_phone.includes(searchQuery);
    const matchesStatus = statusFilter === 'all' || w.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1>Customer Waitlist</h1>
          <p>Register and manage customer slot requests for automated recovery matching.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setAddModalOpen(true)}>
          <Plus size={16} /> Add Waitlist Entry
        </button>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div style={{ display: 'flex', gap: '0.75rem', flex: 1 }}>
          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search waitlist customer..."
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
            <option value="active">Active</option>
            <option value="offered">Offered</option>
            <option value="fulfilled">Fulfilled</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <EmptyState title="Error Loading Waitlist" description={error} isError action={<button className="btn btn-primary" onClick={loadData}>Retry</button>} />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No Waitlist Entries"
          description={statusFilter !== 'all' ? 'No entries found matching this status.' : 'Add customers waiting for released appointment slots.'}
          action={<button className="btn btn-primary" onClick={() => setAddModalOpen(true)}>Add Waitlist Entry</button>}
        />
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Customer Details</th>
                <th>Requested Service</th>
                <th>Preferred Timeframe</th>
                <th>Status</th>
                <th>Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((entry) => (
                <tr key={entry.id}>
                  <td>
                    <strong style={{ display: 'block' }}>{entry.customer_name}</strong>
                    <span className="text-muted">{entry.customer_email} • {entry.customer_phone}</span>
                  </td>
                  <td>
                    <strong>{entry.service?.name || 'Service'}</strong>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.8125rem' }}>
                      <strong>From:</strong> {new Date(entry.preferred_start_date).toLocaleDateString()}
                    </div>
                    <div style={{ fontSize: '0.8125rem' }}>
                      <strong>To:</strong> {new Date(entry.preferred_end_date).toLocaleDateString()}
                    </div>
                  </td>
                  <td>
                    <StatusBadge status={entry.status} type="waitlist" />
                  </td>
                  <td>
                    <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      {entry.notes || 'None'}
                    </span>
                  </td>
                  <td>
                    {entry.status === 'active' && (
                      <button
                        className="btn btn-sm btn-ghost"
                        style={{ color: 'var(--danger)' }}
                        onClick={() => handleCancelEntry(entry.id)}
                      >
                        <Trash2 size={14} /> Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: Add Waitlist Entry */}
      <Modal
        isOpen={addModalOpen}
        onClose={() => setAddModalOpen(false)}
        title="Add Entry to Waitlist"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setAddModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleAddSubmit} disabled={actionLoading}>
              {actionLoading ? 'Saving...' : 'Add to Waitlist'}
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
        <form onSubmit={handleAddSubmit}>
          <div className="form-group">
            <label className="form-label">Customer Name *</label>
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
            <label className="form-label">Phone *</label>
            <input
              type="text"
              className="form-input"
              required
              value={formData.customer_phone}
              onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Requested Service *</label>
            <select
              className="form-select"
              required
              value={formData.service_id}
              onChange={(e) => setFormData({ ...formData, service_id: e.target.value })}
            >
              {services.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} (${s.price})
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Earliest Preferred Date *</label>
              <input
                type="date"
                className="form-input"
                required
                value={formData.preferred_start_date}
                onChange={(e) => setFormData({ ...formData, preferred_start_date: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Latest Preferred Date *</label>
              <input
                type="date"
                className="form-input"
                required
                value={formData.preferred_end_date}
                onChange={(e) => setFormData({ ...formData, preferred_end_date: e.target.value })}
              />
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Notes (Optional)</label>
            <textarea
              className="form-textarea"
              rows={2}
              placeholder="e.g. Morning preferences, specific therapist request..."
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            />
          </div>
        </form>
      </Modal>
    </div>
  );
};
