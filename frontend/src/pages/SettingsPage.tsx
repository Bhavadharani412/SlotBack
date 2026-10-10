import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { BusinessSetting, Service } from '../types';
import { Modal } from '../components/Modal';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { Settings as SettingsIcon, Plus, Save, AlertCircle, CheckCircle2 } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<BusinessSetting | null>(null);
  const [services, setServices] = useState<Service[]>([]);

  const [saveSuccess, setSaveSuccess] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Service Modal
  const [serviceModalOpen, setServiceModalOpen] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [serviceForm, setServiceForm] = useState({
    name: '',
    description: '',
    duration_minutes: 60,
    price: 90,
  });

  const loadSettingsData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [settingData, svcData] = await Promise.all([
        api.getSettings(),
        api.getServices(),
      ]);
      setSettings(settingData);
      setServices(svcData);
    } catch (err: any) {
      setError(err.message || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettingsData();
  }, []);

  const handleSettingsSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings) return;
    try {
      setActionLoading(true);
      setActionError(null);
      setSaveSuccess(false);
      const updated = await api.updateSettings(settings);
      setSettings(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setActionError(err.message || 'Failed to save settings');
    } finally {
      setActionLoading(false);
    }
  };

  const handleServiceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setActionLoading(true);
      setActionError(null);
      if (editingService) {
        await api.updateService(editingService.id, serviceForm);
      } else {
        await api.createService(serviceForm);
      }
      setServiceModalOpen(false);
      setEditingService(null);
      setServiceForm({ name: '', description: '', duration_minutes: 60, price: 90 });
      loadSettingsData();
    } catch (err: any) {
      setActionError(err.message || 'Failed to save service');
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleService = async (service: Service) => {
    try {
      await api.updateService(service.id, { is_active: !service.is_active });
      loadSettingsData();
    } catch (err: any) {
      alert(err.message || 'Failed to toggle service status');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h1>Platform & Business Settings</h1>
          <p>Configure services, default offer expiration windows, and notification preferences.</p>
        </div>
      </div>

      {loading ? (
        <LoadingSkeleton rows={6} />
      ) : error ? (
        <EmptyState title="Error Loading Settings" description={error} isError action={<button className="btn btn-primary" onClick={loadSettingsData}>Retry</button>} />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '1.5rem' }}>
          {/* General & Recovery Settings */}
          <div className="card">
            <div className="card-header">
              <h3>Recovery & Notification Settings</h3>
            </div>
            {saveSuccess && (
              <div className="alert alert-success">
                <CheckCircle2 size={16} />
                <span>Settings saved successfully!</span>
              </div>
            )}
            {actionError && (
              <div className="alert alert-danger">
                <AlertCircle size={16} />
                <span>{actionError}</span>
              </div>
            )}
            {settings && (
              <form onSubmit={handleSettingsSave}>
                <div className="form-group">
                  <label className="form-label">Business Name</label>
                  <input
                    type="text"
                    className="form-input"
                    value={settings.business_name}
                    onChange={(e) => setSettings({ ...settings, business_name: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Default Recovery Offer Expiry (Minutes)</label>
                  <input
                    type="number"
                    className="form-input"
                    min={15}
                    max={1440}
                    value={settings.default_offer_expiry_minutes}
                    onChange={(e) => setSettings({ ...settings, default_offer_expiry_minutes: parseInt(e.target.value) || 60 })}
                  />
                  <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                    Time window customers have to accept a released slot offer before it expires.
                  </span>
                </div>
                <div className="form-group">
                  <label className="form-label">Staff Notification Email</label>
                  <input
                    type="email"
                    className="form-input"
                    value={settings.notification_email}
                    onChange={(e) => setSettings({ ...settings, notification_email: e.target.value })}
                  />
                </div>
                <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="checkbox"
                    id="autoMatch"
                    checked={settings.auto_match_waitlist}
                    onChange={(e) => setSettings({ ...settings, auto_match_waitlist: e.target.checked })}
                  />
                  <label htmlFor="autoMatch" style={{ fontSize: '0.875rem', cursor: 'pointer' }}>
                    Automatically trigger waitlist matching upon appointment cancellation
                  </label>
                </div>
                <button className="btn btn-primary" type="submit" disabled={actionLoading} style={{ marginTop: '1rem' }}>
                  <Save size={16} /> {actionLoading ? 'Saving...' : 'Save Preferences'}
                </button>
              </form>
            )}
          </div>

          {/* Service Configuration List */}
          <div className="card">
            <div className="card-header">
              <h3>Service Catalogue ({services.length})</h3>
              <button
                className="btn btn-sm btn-primary"
                onClick={() => {
                  setEditingService(null);
                  setServiceForm({ name: '', description: '', duration_minutes: 60, price: 90 });
                  setServiceModalOpen(true);
                }}
              >
                <Plus size={14} /> Add Service
              </button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {services.map((svc) => (
                <div
                  key={svc.id}
                  style={{
                    padding: '0.875rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    opacity: svc.is_active ? 1 : 0.6,
                  }}
                >
                  <div>
                    <strong style={{ display: 'block', fontSize: '0.9375rem' }}>
                      {svc.name} {!svc.is_active && <span className="badge badge-neutral">Inactive</span>}
                    </strong>
                    <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                      ${svc.price} • {svc.duration_minutes} mins
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className="btn btn-sm btn-ghost"
                      onClick={() => {
                        setEditingService(svc);
                        setServiceForm({
                          name: svc.name,
                          description: svc.description || '',
                          duration_minutes: svc.duration_minutes,
                          price: svc.price,
                        });
                        setServiceModalOpen(true);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => handleToggleService(svc)}
                    >
                      {svc.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add/Edit Service */}
      <Modal
        isOpen={serviceModalOpen}
        onClose={() => setServiceModalOpen(false)}
        title={editingService ? 'Edit Service' : 'Add New Service'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setServiceModalOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" onClick={handleServiceSubmit} disabled={actionLoading}>
              {actionLoading ? 'Saving...' : 'Save Service'}
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
        <form onSubmit={handleServiceSubmit}>
          <div className="form-group">
            <label className="form-label">Service Name *</label>
            <input
              type="text"
              className="form-input"
              required
              value={serviceForm.name}
              onChange={(e) => setServiceForm({ ...serviceForm, name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Description</label>
            <input
              type="text"
              className="form-input"
              value={serviceForm.description}
              onChange={(e) => setServiceForm({ ...serviceForm, description: e.target.value })}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Duration (Minutes) *</label>
              <input
                type="number"
                className="form-input"
                required
                min={15}
                step={15}
                value={serviceForm.duration_minutes}
                onChange={(e) => setServiceForm({ ...serviceForm, duration_minutes: parseInt(e.target.value) || 30 })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Price ($ USD) *</label>
              <input
                type="number"
                className="form-input"
                required
                min={0}
                step={0.01}
                value={serviceForm.price}
                onChange={(e) => setServiceForm({ ...serviceForm, price: parseFloat(e.target.value) || 0 })}
              />
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
};
