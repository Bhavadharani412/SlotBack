import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { OfferAcceptResponse, RecoveryOffer } from '../types';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';
import { Clock, CheckCircle2, AlertTriangle, Sparkles, XCircle } from 'lucide-react';

export const CustomerOfferPage: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offer, setOffer] = useState<RecoveryOffer | null>(null);

  const [accepting, setAccepting] = useState(false);
  const [acceptResponse, setAcceptResponse] = useState<OfferAcceptResponse | null>(null);
  const [acceptError, setAcceptError] = useState<string | null>(null);
  const [timeLeft, setTimeLeft] = useState<string>('');

  const loadOffer = async () => {
    if (!token) {
      setError('Invalid recovery offer token');
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await api.getOfferByToken(token);
      setOffer(data);
    } catch (err: any) {
      setError(err.message || 'Recovery offer not found or no longer available.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOffer();
  }, [token]);

  // Countdown timer effect
  useEffect(() => {
    if (!offer || offer.status !== 'sent') return;

    const timer = setInterval(() => {
      const diff = new Date(offer.expires_at).getTime() - new Date().getTime();
      if (diff <= 0) {
        setTimeLeft('Expired');
        setOffer((prev) => (prev ? { ...prev, status: 'expired' } : prev));
        clearInterval(timer);
      } else {
        const mins = Math.floor(diff / 60000);
        const secs = Math.floor((diff % 60000) / 1000);
        setTimeLeft(`${mins}m ${secs}s`);
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [offer]);

  const handleAccept = async () => {
    if (!token) return;
    try {
      setAccepting(true);
      setAcceptError(null);
      const resp = await api.acceptOffer(token);
      setAcceptResponse(resp);
      setOffer((prev) => (prev ? { ...prev, status: 'accepted' } : prev));
    } catch (err: any) {
      setAcceptError(err.message || 'Failed to accept offer. It may have expired or already been claimed.');
    } finally {
      setAccepting(false);
    }
  };

  if (loading) return <LoadingSkeleton rows={5} />;

  if (error || !offer) {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: 'var(--canvas)', padding: '3rem 1rem' }}>
        <div style={{ maxWidth: '500px', margin: '0 auto' }}>
          <EmptyState
            title="Recovery Offer Unavailable"
            description={error || 'This recovery offer link is invalid or has expired.'}
            isError
          />
        </div>
      </div>
    );
  }

  const isExpired = offer.status === 'expired' || new Date(offer.expires_at) < new Date();
  const isAccepted = offer.status === 'accepted' || acceptResponse !== null;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--canvas)', padding: '2rem 1rem' }}>
      <div style={{ maxWidth: '550px', margin: '0 auto' }}>
        {/* Header Branding */}
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
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
              marginBottom: '0.5rem',
            }}
          >
            SB
          </div>
          <h1>Earlier Appointment Opening</h1>
          <p style={{ color: 'var(--text-muted)' }}>
            A slot just opened up for you because you were on our waitlist!
          </p>
        </div>

        {/* First time guide banner */}
        {!isAccepted && !isExpired && (
          <div
            style={{
              backgroundColor: '#EFF6FF',
              border: '1px solid #BFDBFE',
              borderRadius: 'var(--radius-md)',
              padding: '1rem',
              marginBottom: '1.25rem',
              fontSize: '0.875rem',
              color: '#1E293B',
            }}
          >
            <strong style={{ display: 'block', color: '#1D4ED8', marginBottom: '0.25rem' }}>
              How This Works:
            </strong>
            <span>
              Another customer cancelled their appointment, so this earlier time is offered to you first.
              Review the details below and tap <strong>Accept & Claim This Appointment</strong> before the timer expires.
            </span>
          </div>
        )}

        {/* Accepted Confirmed Screen */}
        {isAccepted ? (
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
            <h2>Offer Accepted & Booking Confirmed!</h2>
            <p style={{ marginTop: '0.5rem', marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
              You have claimed this appointment. Your booking is confirmed.
            </p>

            <div
              style={{
                backgroundColor: '#F8FAFC',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-md)',
                padding: '1.25rem',
                textAlign: 'left',
              }}
            >
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="text-muted">Customer Name:</span>{' '}
                <strong>{acceptResponse?.appointment?.customer_name || offer.waitlist_entry?.customer_name}</strong>
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="text-muted">Service:</span>{' '}
                <strong>{offer.appointment?.service?.name}</strong>
              </div>
              <div style={{ marginBottom: '0.5rem' }}>
                <span className="text-muted">Confirmed Date & Time:</span>{' '}
                <strong>
                  {new Date(offer.appointment?.start_time || '').toLocaleString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })}
                </strong>
              </div>
              <div>
                <span className="text-muted">Booking Reference:</span>{' '}
                <code>{offer.appointment?.id.slice(0, 8)}</code>
              </div>
            </div>
          </div>
        ) : (
          /* Active / Expired Offer Card */
          <div className="card">
            {/* Offer Timer Banner */}
            {!isExpired ? (
              <div
                style={{
                  padding: '0.875rem 1rem',
                  backgroundColor: 'var(--warning-bg)',
                  border: '1px solid var(--warning-border)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '1.25rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--warning)' }}>
                  <Clock size={18} />
                  <strong style={{ fontSize: '0.875rem' }}>Time Left to Claim</strong>
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--warning)' }}>
                  {timeLeft || '60m 00s'}
                </div>
              </div>
            ) : (
              <div className="alert alert-danger" style={{ marginBottom: '1.25rem' }}>
                <XCircle size={20} />
                <div>
                  <strong>Offer Expired</strong>
                  <div style={{ fontSize: '0.8125rem' }}>
                    This offer expired at {new Date(offer.expires_at).toLocaleTimeString()}.
                  </div>
                </div>
              </div>
            )}

            {acceptError && (
              <div className="alert alert-danger">
                <AlertTriangle size={16} />
                <span>{acceptError}</span>
              </div>
            )}

            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>
                {offer.appointment?.service?.name}
              </h3>
              <p className="text-muted" style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>
                {offer.appointment?.service?.description || 'Opening available from a cancelled appointment.'}
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', backgroundColor: 'var(--surface-hover)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <div>
                  <span className="text-muted" style={{ fontSize: '0.8125rem' }}>Offered Time Slot:</span>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {new Date(offer.appointment?.start_time || '').toLocaleString('en-US', {
                      weekday: 'long',
                      month: 'short',
                      day: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                  <span className="text-muted" style={{ fontSize: '0.8125rem' }}>Reserved For:</span>
                  <strong>{offer.waitlist_entry?.customer_name}</strong>
                </div>
              </div>
            </div>

            <button
              className="btn btn-primary"
              onClick={handleAccept}
              disabled={isExpired || accepting}
              style={{ width: '100%', padding: '0.875rem', fontSize: '1rem', fontWeight: 600 }}
            >
              {accepting ? 'Confirming Availability...' : isExpired ? 'Offer Expired' : 'Accept & Claim This Appointment'}
            </button>
            <p className="text-muted" style={{ textAlign: 'center', fontSize: '0.75rem', marginTop: '0.75rem' }}>
              We will hold and confirm this appointment for you as soon as you accept.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
