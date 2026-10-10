import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Calendar,
  Users,
  RefreshCw,
  BarChart3,
  Settings,
  Menu,
  X,
  ExternalLink,
  Sparkles,
} from 'lucide-react';

interface NavigationProps {
  activeOffersCount?: number;
}

export const Navigation: React.FC<NavigationProps> = ({ activeOffersCount = 0 }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/appointments', label: 'Appointments', icon: Calendar },
    { to: '/waitlist', label: 'Waitlist', icon: Users },
    {
      to: '/recovery',
      label: 'Slot Recovery',
      icon: RefreshCw,
      badge: activeOffersCount > 0 ? activeOffersCount : undefined,
    },
    { to: '/reports', label: 'Reports', icon: BarChart3 },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Persistent Desktop Sidebar */}
      <aside className={`sidebar ${mobileMenuOpen ? 'mobile-open' : ''}`}>
        <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: 'var(--primary)', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
              SB
            </div>
            <div>
              <span style={{ fontWeight: 700, fontSize: '1.125rem', color: 'var(--text-primary)', display: 'block', lineHeight: 1.2 }}>SlotBack</span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Staff Recovery Portal</span>
            </div>
          </div>
          {mobileMenuOpen && (
            <button className="btn btn-ghost btn-sm" onClick={() => setMobileMenuOpen(false)} style={{ display: 'md-none' }}>
              <X size={18} />
            </button>
          )}
        </div>

        <nav style={{ padding: '1rem 0.75rem', flex: 1, display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `btn btn-ghost ${isActive ? 'active-nav' : ''}`
                }
                style={({ isActive }) => ({
                  justifyContent: 'flex-start',
                  padding: '0.625rem 0.875rem',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: isActive ? 'var(--primary-light)' : 'transparent',
                  color: isActive ? 'var(--primary)' : 'var(--text-secondary)',
                  fontWeight: isActive ? 600 : 500,
                  position: 'relative',
                })}
              >
                <Icon size={18} />
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.badge !== undefined && (
                  <span
                    style={{
                      backgroundColor: 'var(--warning)',
                      color: '#FFF',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '0.125rem 0.5rem',
                      borderRadius: 'var(--radius-full)',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}

          <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
            <NavLink
              to="/book"
              target="_blank"
              className="btn btn-secondary btn-sm"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <ExternalLink size={14} />
              <span>Public Customer Booking</span>
            </NavLink>
          </div>
        </nav>
      </aside>

      {/* Topbar */}
      <header className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            className="btn btn-ghost btn-sm mobile-only-menu"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation"
          >
            <Menu size={20} />
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10B981' }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-secondary)' }}>System Active</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
          </div>
        </div>
      </header>
    </>
  );
};
