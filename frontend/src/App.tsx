import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom';
import { Navigation } from './components/Navigation';
import { OverviewPage } from './pages/OverviewPage';
import { AppointmentsPage } from './pages/AppointmentsPage';
import { WaitlistPage } from './pages/WaitlistPage';
import { RecoveryPage } from './pages/RecoveryPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { CustomerBookingPage } from './pages/CustomerBookingPage';
import { CustomerOfferPage } from './pages/CustomerOfferPage';
import { api } from './api/client';

const StaffLayout: React.FC<{ activeOffersCount: number }> = ({ activeOffersCount }) => {
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

export const App: React.FC = () => {
  const [activeOffersCount, setActiveOffersCount] = useState(0);

  useEffect(() => {
    api
      .getMetrics()
      .then((m) => setActiveOffersCount(m.active_offers_count))
      .catch(() => {});
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Customer Routes */}
        <Route path="/book" element={<CustomerBookingPage />} />
        <Route path="/offer/:token" element={<CustomerOfferPage />} />

        {/* Staff Operations Portal Routes */}
        <Route element={<StaffLayout activeOffersCount={activeOffersCount} />}>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route path="/waitlist" element={<WaitlistPage />} />
          <Route path="/recovery" element={<RecoveryPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};

export default App;
