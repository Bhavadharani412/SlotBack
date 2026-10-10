import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  UserPlus,
  Mail,
  Lock,
  User as UserIcon,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowLeft,
  ShieldCheck,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';

export const SignUpPage: React.FC = () => {
  const { user, isAdmin } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'staff' | 'admin'>('staff');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Client-side validations
    if (!fullName.trim()) {
      setError('Please provide the full name of the staff member.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setError('Please provide a valid staff email address.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter confirmation password.');
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await api.createStaffUser({
        full_name: fullName.trim(),
        email: email.trim(),
        role,
        password,
      });
      setSuccess(`Successfully created account for ${created.full_name} (${created.email}) with ${created.role} privileges.`);
      setFullName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to provision staff account. Please verify details and try again.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--canvas)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '520px',
          padding: '2.5rem',
          boxShadow: 'var(--shadow-lg)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-color)',
          backgroundColor: 'var(--surface)',
        }}
      >
        {/* Back navigation */}
        <div style={{ marginBottom: '1.5rem' }}>
          <Link
            to={user ? '/' : '/login'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.375rem',
              color: 'var(--text-muted)',
              textDecoration: 'none',
              fontSize: '0.875rem',
              fontWeight: 500,
            }}
          >
            <ArrowLeft size={16} />
            <span>Back to {user ? 'Dashboard' : 'Sign In'}</span>
          </Link>
        </div>

        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              backgroundColor: 'var(--primary-light)',
              color: 'var(--primary)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '1rem',
            }}
          >
            <UserPlus size={24} />
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.375rem' }}>
            Staff Invitation & Provisioning
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Provision authorized personnel accounts under SlotBack
          </p>
        </div>

        {/* Access barrier check: Requires authenticated administrator */}
        {!isAdmin ? (
          <div
            style={{
              padding: '1.5rem',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--info-bg)',
              border: '1px solid var(--info-border)',
              textAlign: 'center',
            }}
          >
            <ShieldAlert size={36} style={{ color: 'var(--info)', margin: '0 auto 0.75rem' }} />
            <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
              Administrator Authorization Required
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.25rem' }}>
              SlotBack enforces strict tenant boundaries. To prevent unauthorized access, staff accounts must be provisioned by an authenticated business administrator. Unrestricted public registration is disabled.
            </p>
            <Link
              to="/login"
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', display: 'flex', alignItems: 'center' }}
            >
              Sign In as Administrator
            </Link>
          </div>
        ) : (
          /* Form for authenticated administrator */
          <form onSubmit={handleSubmit} noValidate>
            {error && (
              <div
                role="alert"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '0.875rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--danger-bg)',
                  border: '1px solid var(--danger-border)',
                  color: 'var(--danger)',
                  fontSize: '0.875rem',
                  marginBottom: '1.5rem',
                }}
              >
                <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1 }}>{error}</div>
              </div>
            )}

            {success && (
              <div
                role="status"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '0.875rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--success-bg)',
                  border: '1px solid var(--success-border)',
                  color: 'var(--success)',
                  fontSize: '0.875rem',
                  marginBottom: '1.5rem',
                }}
              >
                <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
                <div style={{ flex: 1 }}>{success}</div>
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="fullname-input"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}
              >
                Full Name
              </label>
              <div style={{ position: 'relative' }}>
                <UserIcon
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="fullname-input"
                  type="text"
                  className="form-control"
                  style={{ paddingLeft: '2.5rem', width: '100%' }}
                  placeholder="e.g. Sarah Jenkins"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="signup-email-input"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}
              >
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="signup-email-input"
                  type="email"
                  className="form-control"
                  style={{ paddingLeft: '2.5rem', width: '100%' }}
                  placeholder="sarah@slotback.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="role-select"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}
              >
                Assigned Role
              </label>
              <select
                id="role-select"
                className="form-control"
                style={{ width: '100%' }}
                value={role}
                onChange={(e) => setRole(e.target.value as 'staff' | 'admin')}
                disabled={isSubmitting}
              >
                <option value="staff">Staff Member (Operational access)</option>
                <option value="admin">Administrator (Settings & full control)</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label
                htmlFor="signup-password-input"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}
              >
                Initial Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="signup-password-input"
                  type={showPassword ? 'text' : 'password'}
                  className="form-control"
                  style={{ paddingLeft: '2.5rem', paddingRight: '2.5rem', width: '100%' }}
                  placeholder="Min 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    padding: '4px',
                  }}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label
                htmlFor="confirm-password-input"
                style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.5rem' }}
              >
                Confirm Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={18}
                  style={{
                    position: 'absolute',
                    left: '0.875rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="confirm-password-input"
                  type={showPassword ? 'text' : 'password'}
                  className="form-control"
                  style={{ paddingLeft: '2.5rem', width: '100%' }}
                  placeholder="Re-enter password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '0.9375rem',
                fontWeight: 600,
                justifyContent: 'center',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              {isSubmitting ? (
                <span>Provisioning Account...</span>
              ) : (
                <>
                  <UserPlus size={16} />
                  <span>Provision Staff Account</span>
                </>
              )}
            </button>
          </form>
        )}

        <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.375rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            <ShieldCheck size={14} style={{ color: 'var(--success)' }} />
            <span>Authorized Administrator Control Plane</span>
          </div>
        </div>
      </div>
    </div>
  );
};
