import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Outlet, Navigate, useLocation } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { OverviewPage } from './pages/OverviewPage';
import { AppointmentsPage } from './pages/AppointmentsPage';
import { WaitlistPage } from './pages/WaitlistPage';
import { RecoveryPage } from './pages/RecoveryPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { CustomerBookingPage } from './pages/CustomerBookingPage';
import { CustomerOfferPage } from './pages/CustomerOfferPage';
import { SignInPage } from './pages/SignInPage';
import { SignUpPage } from './pages/SignUpPage';
import { AuthProvider, useAuth } from './context/AuthContext';
import { api } from './api/client';

const StaffLayout: React.FC = () => {
  const [activeOffersCount, setActiveOffersCount] = useState(0);

  useEffect(() => {
    api
      .getMetrics()
      .then((m) => setActiveOffersCount(m.active_offers_count))
      .catch(() => {});
  }, []);

  return (
    <div className="app-container">
      <Navigation activeOffersCount={activeOffersCount} />
      <main className="main-content">
        <div className="page-body">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

const ProtectedRoute: React.FC = () => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--canvas)',
        }}
      >
        <div style={{ textAlign: 'center' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              border: '3px solid var(--border-color)',
              borderTopColor: 'var(--primary)',
              borderRadius: '50%',
              margin: '0 auto 1rem',
              animation: 'spin 1s linear infinite',
            }}
          />
          <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem', fontWeight: 500 }}>
            Verifying staff authorization...
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <StaffLayout />;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Customer Routes (No authentication required) */}
          <Route path="/book" element={<CustomerBookingPage />} />
          <Route path="/offer/:token" element={<CustomerOfferPage />} />

          {/* Authentication & Staff Invitation Routes */}
          <Route path="/login" element={<SignInPage />} />
          <Route path="/register" element={<SignUpPage />} />

          {/* Protected Staff Operations Portal */}
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/appointments" element={<AppointmentsPage />} />
            <Route path="/waitlist" element={<WaitlistPage />} />
            <Route path="/recovery" element={<RecoveryPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
