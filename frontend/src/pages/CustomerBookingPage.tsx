import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Appointment, Service } from '../types';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { Calendar, Clock, CheckCircle2, AlertCircle, HelpCircle, X, Sparkles } from 'lucide-react';

export const CustomerBookingPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [services, setServices] = useState<Service[]>([]);

  // First-time customer guide state
  const [showGuide, setShowGuide] = useState<boolean>(() => {
    return localStorage.getItem('slotback_guide_seen') !== 'true';
  });

  const dismissGuide = () => {
    setShowGuide(false);
    localStorage.setItem('slotback_guide_seen', 'true');
  };

  // Steps: 1: Service, 2: Slot & Info, 3: Confirmed
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedService, setSelectedService] = useState<Service | null>(null);

  // Today in YYYY-MM-DD
  const todayStr = new Date().toISOString().split('T')[0];

  const [formData, setFormData] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    date: todayStr,
    time: '10:00',
  });

  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmedBooking, setConfirmedBooking] = useState<Appointment | null>(null);

  // Available times calculation
  const standardTimes = ['09:00', '10:00', '11:30', '14:00', '15:30', '17:00'];
  const now = new Date();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();

  const isToday = formData.date === todayStr;
  const availableTimes = isToday
    ? standardTimes.filter((t) => {
        const [h, m] = t.split(':').map(Number);
        return h * 60 + m > currentMinutes;
      })
    : standardTimes;

  // Auto-adjust selected time if current selection is in the past for today
  useEffect(() => {
    if (isToday && availableTimes.length > 0 && !availableTimes.includes(formData.time)) {
      setFormData((prev) => ({ ...prev, time: availableTimes[0] }));
    }
  }, [formData.date, isToday, availableTimes, formData.time]);

  useEffect(() => {
    api
      .getServices(true)
      .then((data) => {
        setServices(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load available services');
        setLoading(false);
      });
  }, []);

  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedService) return;
    if (!formData.customer_name || !formData.customer_email || !formData.customer_phone || !formData.date) {
      setSubmitError('Please complete all required fields.');
      return;
    }

    if (isToday && availableTimes.length === 0) {
      setSubmitError('All booking slots for today have already passed. Please select a future date.');
      return;
    }

    const selectedDateTime = new Date(`${formData.date}T${formData.time}:00`);
    if (selectedDateTime.getTime() <= Date.now()) {
      setSubmitError('Booking date and time must be in the future. Past or completed times cannot be booked.');
      return;
    }

    try {
      setSubmitLoading(true);
      setSubmitError(null);
      const startTime = selectedDateTime.toISOString();
      const app = await api.createAppointment({
        customer_name: formData.customer_name,
        customer_email: formData.customer_email,
        customer_phone: formData.customer_phone,
        service_id: selectedService.id,
        start_time: startTime,
      });
      setConfirmedBooking(app);
      setStep(3);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to confirm booking. The selected time slot may be unavailable.');
    } finally {
      setSubmitLoading(false);
    }
  };

  if (loading) return <LoadingSkeleton rows={5} />;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--canvas)', padding: '2rem 1rem' }}>
      <div style={{ maxWidth: '600px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem', position: 'relative' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              backgroundColor: 'var(--primary)',
              color: '#FFF',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              fontSize: '1.25rem',
              marginBottom: '0.75rem',
            }}
          >
            SB
          </div>
          <h1>Book an Appointment</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
            Choose a service and an upcoming time that works best for you.
          </p>

          {!showGuide && (
            <button
              onClick={() => setShowGuide(true)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--primary)',
                fontSize: '0.8125rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                marginTop: '0.5rem',
              }}
            >
              <HelpCircle size={14} />
              <span>How booking works</span>
            </button>
          )}
        </div>

        {/* Customer User Guide Banner */}
        {showGuide && (
          <div
            style={{
              backgroundColor: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: 'var(--radius-lg)',
              padding: '1.25rem',
              marginBottom: '1.5rem',
              position: 'relative',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#1D4ED8', fontWeight: 700, fontSize: '0.9375rem' }}>
                <Sparkles size={18} />
                <span>Quick Guide for New Customers</span>
              </div>
              <button
                onClick={dismissGuide}
                aria-label="Dismiss guide"
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#64748B',
                  padding: '2px',
                }}
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem', fontSize: '0.8125rem', color: '#1E293B', marginBottom: '0.875rem' }}>
              <div style={{ backgroundColor: '#FFF', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid #DBEAFE' }}>
                <strong style={{ display: 'block', color: '#1D4ED8', marginBottom: '0.25rem' }}>1. Pick Service</strong>
                See clear descriptions, time duration, and pricing.
              </div>
              <div style={{ backgroundColor: '#FFF', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid #DBEAFE' }}>
                <strong style={{ display: 'block', color: '#1D4ED8', marginBottom: '0.25rem' }}>2. Pick Upcoming Slot</strong>
                Select a future date and time. Past times are automatically blocked.
              </div>
              <div style={{ backgroundColor: '#FFF', padding: '0.75rem', borderRadius: 'var(--radius-md)', border: '1px solid #DBEAFE' }}>
                <strong style={{ display: 'block', color: '#1D4ED8', marginBottom: '0.25rem' }}>3. Instant Confirmation</strong>
                Get instant confirmation with your booking reference.
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: '#475569' }}>
              <span>Need a full slot? You can join the waitlist for instant notification if someone cancels.</span>
              <button
                className="btn btn-sm"
                onClick={dismissGuide}
                style={{
                  backgroundColor: '#2563EB',
                  color: '#FFF',
                  padding: '0.25rem 0.75rem',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Got It
              </button>
            </div>
          </div>
        )}

        {/* Step 1: Service Selection */}
        {step === 1 && (
          <div className="card">
            <h3 style={{ marginBottom: '1rem' }}>1. Choose a Service</h3>
            {error ? (
              <EmptyState title="Error Loading Services" description={error} isError />
            ) : services.length === 0 ? (
              <EmptyState title="No Services Available" description="No active services available for booking at this time." />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {services.map((svc) => (
                  <div
                    key={svc.id}
                    onClick={() => {
                      setSelectedService(svc);
                      setStep(2);
                    }}
                    style={{
                      padding: '1rem',
                      borderRadius: 'var(--radius-md)',
                      border: selectedService?.id === svc.id ? '2px solid var(--primary)' : '1px solid var(--border-color)',
                      backgroundColor: selectedService?.id === svc.id ? 'var(--primary-light)' : 'var(--surface)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div>
                      <strong style={{ display: 'block', fontSize: '1rem' }}>{svc.name}</strong>
                      <p className="text-muted" style={{ fontSize: '0.8125rem', margin: '0.25rem 0' }}>
                        {svc.description || 'Professional service treatment'}
                      </p>
                      <span className="text-muted" style={{ fontSize: '0.8125rem' }}>
                        <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
                        {svc.duration_minutes} Minutes
                      </span>
                    </div>
                    <div style={{ fontSize: '1.125rem', fontWeight: 700, color: 'var(--primary)' }}>
                      ${svc.price}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Slot Selection & Details */}
        {step === 2 && selectedService && (
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h3>2. Select Date & Details</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setStep(1)}>
                Change Service
              </button>
            </div>

            <div style={{ padding: '0.75rem', backgroundColor: 'var(--primary-light)', borderRadius: 'var(--radius-md)', marginBottom: '1.25rem' }}>
              <strong>{selectedService.name}</strong> — ${selectedService.price} ({selectedService.duration_minutes} mins)
            </div>

            {submitError && (
              <div className="alert alert-danger">
                <AlertCircle size={16} />
                <span>{submitError}</span>
              </div>
            )}

            <form onSubmit={handleBookingSubmit}>
              <div className="form-group">
                <label className="form-label">Your Full Name *</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. Sarah Jenkins"
                  value={formData.customer_name}
                  onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Email Address *</label>
                <input
                  type="email"
                  className="form-input"
                  required
                  placeholder="sarah@example.com"
                  value={formData.customer_email}
                  onChange={(e) => setFormData({ ...formData, customer_email: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Phone Number *</label>
                <input
                  type="tel"
                  className="form-input"
                  required
                  placeholder="(555) 000-0000"
                  value={formData.customer_phone}
                  onChange={(e) => setFormData({ ...formData, customer_phone: e.target.value })}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label className="form-label">Date *</label>
                  <input
                    type="date"
                    className="form-input"
                    required
                    min={todayStr}
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Available Time *</label>
                  {availableTimes.length === 0 ? (
                    <div style={{ color: 'var(--danger)', fontSize: '0.8125rem', padding: '0.5rem 0' }}>
                      All times for today have ended. Please choose tomorrow or an upcoming date.
                    </div>
                  ) : (
                    <select
                      className="form-select"
                      value={formData.time}
                      onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    >
                      {availableTimes.map((t) => {
                        const [h, m] = t.split(':').map(Number);
                        const period = h >= 12 ? 'PM' : 'AM';
                        const displayH = h % 12 || 12;
                        const displayTime = `${String(displayH).padStart(2, '0')}:${String(m).padStart(2, '0')} ${period}`;
                        return (
                          <option key={t} value={t}>
                            {displayTime}
                          </option>
                        );
                      })}
                    </select>
                  )}
                </div>
              </div>

              <button
                className="btn btn-primary"
                type="submit"
                disabled={submitLoading || (isToday && availableTimes.length === 0)}
                style={{ width: '100%', marginTop: '1rem', padding: '0.75rem' }}
              >
                {submitLoading ? 'Saving Booking...' : 'Book Appointment'}
              </button>
            </form>
          </div>
        )}

        {/* Step 3: Confirmed Ticket */}
        {step === 3 && confirmedBooking && (
          <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                backgroundColor: 'var(--success-bg)',
                color: 'var(--success)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '1rem',
              }}
            >
              <CheckCircle2 size={36} />
            </div>
            <h2>Appointment Confirmed!</h2>
            <p style={{ marginTop: '0.5rem', marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
              Your appointment is booked. We look forward to seeing you!
            </p>

            <div
              style={{
                backgroundColor: '#F8FAFC',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '1.25rem',
                textAlign: 'left',
                marginBottom: '1.5rem',
              }}
            >
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="text-muted">Customer:</span> <strong>{confirmedBooking.customer_name}</strong>
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="text-muted">Service:</span> <strong>{selectedService?.name}</strong>
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="text-muted">Date & Time:</span>{' '}
                <strong>
                  {new Date(confirmedBooking.start_time).toLocaleString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </strong>
              </div>
              <div>
                <span className="text-muted">Booking Reference:</span> <code>{confirmedBooking.id.slice(0, 8)}</code>
              </div>
            </div>

            <button
              className="btn btn-secondary"
              onClick={() => {
                setStep(1);
                setSelectedService(null);
                setConfirmedBooking(null);
              }}
            >
              Book Another Appointment
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
