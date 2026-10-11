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

  const [staffUsers, setStaffUsers] = useState<any[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadStaffUsers = async () => {
    if (!isAdmin) return;
    try {
      setLoadingUsers(true);
      const users = await api.getStaffUsers();
      setStaffUsers(users);
    } catch {
      // ignore
    } finally {
      setLoadingUsers(false);
    }
  };

  React.useEffect(() => {
    if (isAdmin) {
      loadStaffUsers();
    }
  }, [isAdmin]);

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
      setSuccess(`Successfully created account for ${created.full_name} (${created.email}) with ${created.role} role.`);
      setFullName('');
      setEmail('');
      setPassword('');
      setConfirmPassword('');
      loadStaffUsers();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create staff account. Please verify details and try again.';
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
          maxWidth: '560px',
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
            Staff Accounts & Setup
          </h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Create and manage staff and admin access
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
              Admin Sign In Required
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.25rem' }}>
              Only business administrators can set up staff accounts. Sign in using the admin account configured in your <code>.env</code> file.
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
                <span>Creating Account...</span>
              ) : (
                <>
                  <UserPlus size={16} />
                  <span>Create Staff Account</span>
                </>
              )}
            </button>
          </form>
        )}

        {/* Existing staff accounts list */}
        {isAdmin && (
          <div style={{ marginTop: '2rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-color)' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
              Current Accounts ({staffUsers.length})
            </h3>
            {loadingUsers ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>Loading accounts...</div>
            ) : staffUsers.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>No staff accounts created yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {staffUsers.map((u) => (
                  <div
                    key={u.id}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.625rem 0.75rem',
                      backgroundColor: 'var(--surface-hover)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border-color)',
                      fontSize: '0.8125rem',
                    }}
                  >
                    <div>
                      <strong style={{ display: 'block', color: 'var(--text-primary)' }}>{u.full_name}</strong>
                      <span className="text-muted">{u.email}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span
                        style={{
                          backgroundColor: u.role === 'admin' ? 'var(--primary-light)' : 'var(--surface)',
                          color: u.role === 'admin' ? 'var(--primary)' : 'var(--text-secondary)',
                          border: '1px solid var(--border-color)',
                          fontSize: '0.75rem',
                          padding: '0.125rem 0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          fontWeight: 600,
                          textTransform: 'capitalize',
                        }}
                      >
                        {u.role}
                      </span>
                      <span
                        style={{
                          color: 'var(--success)',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                        }}
                      >
                        Active
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', textAlign: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.375rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
            <ShieldCheck size={14} style={{ color: 'var(--success)' }} />
            <span>Administrator Controls</span>
          </div>
        </div>
      </div>
    </div>
  );
};
