import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, Navigate, useNavigate } from 'react-router-dom';
import { Layout, ConfigProvider, Typography, theme as antTheme } from 'antd';
import {
  Database, Activity, ClipboardCheck, BarChart2,
  Settings, ChevronLeft, ChevronRight, Zap, LogOut
} from 'lucide-react';

import LookupView from './pages/LookupView';
import ActivityView from './pages/ActivityView';
import ReviewQueueView from './pages/ReviewQueueView';
import AnalyticsView from './pages/AnalyticsView';
import AdminView from './pages/AdminView';
import UbidDetailView from './pages/UbidDetailView';
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import './App.css';

/* Simple auth guard — checks localStorage flag set by LoginPage */
const RequireAuth: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  if (!localStorage.getItem('ubid_authed')) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const { Sider, Content } = Layout;
const { Text } = Typography;

const ORANGE = '#FF6B2C';
const SIDEBAR_BG = '#111111';
const SIDEBAR_BORDER = '#2a2a2a';
const TEXT_WHITE = '#ffffff';
const TEXT_MUTED = '#aaaaaa';
const ACTIVE_BG = '#FF6B2C22';
const ACTIVE_TEXT_ORANGE = '#FF6B2C';

const navItems = [
  { key: '/dashboard/lookup',    icon: Database,       label: 'UBID Directory' },
  { key: '/dashboard/activity',  icon: Activity,       label: 'Activity Intelligence' },
  { key: '/dashboard/review',    icon: ClipboardCheck, label: 'Reviewer Queue' },
  { key: '/dashboard/analytics', icon: BarChart2,      label: 'Analytics' },
  { key: '/dashboard/admin',     icon: Settings,       label: 'Admin Console' },
];

const AppLayout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('ubid_authed');
    navigate('/');
  };

  return (
    <Layout style={{ minHeight: '100vh', background: 'linear-gradient(145deg, #ffffff 0%, #fffaf7 40%, #ffefe6 100%)' }}>
      <Sider
        width={240}
        collapsedWidth={64}
        collapsed={collapsed}
        style={{
          background: SIDEBAR_BG,
          borderRight: `1px solid ${SIDEBAR_BORDER}`,
          position: 'fixed',
          height: '100vh',
          left: 0,
          top: 0,
          zIndex: 100,
          overflow: 'hidden',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Logo */}
        <div 
          onClick={() => navigate('/')}
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            padding: '0 16px',
            borderBottom: `1px solid ${SIDEBAR_BORDER}`,
            gap: 12,
            flexShrink: 0,
            cursor: 'pointer'
          }}
        >
          <img src="/logo.png" alt="Logo" style={{ height: 42, width: 'auto', flexShrink: 0 }} />
          {!collapsed && (
            <span style={{ fontFamily: '"Josefin Sans", sans-serif', fontSize: 20, fontWeight: 700, color: '#ffffff', letterSpacing: '0.05em', whiteSpace: 'nowrap' }}>SAMVAYA</span>
          )}
        </div>

        {/* Nav items */}
        <div style={{ padding: '12px 0', flex: 1 }}>
          {navItems.map(({ key, icon: Icon, label }) => {
            const active = location.pathname === key || (key === '/dashboard/lookup' && location.pathname === '/dashboard');
            return (
              <Link to={key} key={key} style={{ textDecoration: 'none' }}>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '11px 16px',
                    margin: '2px 8px',
                    borderRadius: 6,
                    background: active ? ACTIVE_BG : 'transparent',
                    borderLeft: active ? `3px solid ${ORANGE}` : '3px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => {
                    if (!active) e.currentTarget.style.background = '#FF6B2C22';
                    (e.currentTarget.querySelector('.nav-icon') as HTMLElement | null)?.style && ((e.currentTarget.querySelector('.nav-icon') as any).style.color = ORANGE);
                    (e.currentTarget.querySelector('.nav-label') as HTMLElement | null)?.style && ((e.currentTarget.querySelector('.nav-label') as any).style.color = ORANGE);
                  }}
                  onMouseLeave={e => {
                    if (!active) e.currentTarget.style.background = 'transparent';
                    (e.currentTarget.querySelector('.nav-icon') as HTMLElement | null)?.style && ((e.currentTarget.querySelector('.nav-icon') as any).style.color = active ? ACTIVE_TEXT_ORANGE : TEXT_MUTED);
                    (e.currentTarget.querySelector('.nav-label') as HTMLElement | null)?.style && ((e.currentTarget.querySelector('.nav-label') as any).style.color = active ? ACTIVE_TEXT_ORANGE : TEXT_WHITE);
                  }}
                >
                  <Icon className="nav-icon" size={17} color={active ? ACTIVE_TEXT_ORANGE : TEXT_MUTED} style={{ flexShrink: 0, transition: 'color 0.15s' }} />
                  {!collapsed && (
                    <Text className="nav-label" style={{
                      color: active ? ACTIVE_TEXT_ORANGE : TEXT_WHITE,
                      fontSize: 13,
                      fontFamily: 'monospace',
                      fontWeight: active ? 600 : 400,
                      whiteSpace: 'nowrap',
                      transition: 'color 0.15s',
                    }}>
                      {label}
                    </Text>
                  )}
                </div>
              </Link>
            );
          })}
        </div>

        {/* Collapse toggle */}
        <div
          onClick={() => setCollapsed(!collapsed)}
          style={{
            height: 48,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-end',
            padding: '0 20px',
            borderTop: `1px solid ${SIDEBAR_BORDER}`,
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          {collapsed
            ? <ChevronRight size={15} color={TEXT_MUTED} />
            : <ChevronLeft size={15} color={TEXT_MUTED} />}
        </div>

        {/* Logout Button */}
        <div style={{ padding: '8px', borderTop: `1px solid ${SIDEBAR_BORDER}` }}>
          <div
            onClick={handleLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              padding: '11px 16px',
              borderRadius: 6,
              cursor: 'pointer',
              transition: 'all 0.15s',
              justifyContent: collapsed ? 'center' : 'flex-start',
              background: ORANGE,
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#e85a1f'}
            onMouseLeave={(e) => e.currentTarget.style.background = ORANGE}
          >
            <LogOut size={17} color="#ffffff" style={{ flexShrink: 0 }} />
            {!collapsed && (
              <Text style={{
                color: '#ffffff',
                fontSize: 13,
                fontFamily: 'monospace',
                fontWeight: 500,
                whiteSpace: 'nowrap',
              }}>
                Log Out
              </Text>
            )}
          </div>
        </div>
        </div>
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 64 : 240, transition: 'margin-left 0.2s', background: 'transparent', minHeight: '100vh' }}>
        <Content style={{ padding: 28 }}>
          <div key={location.pathname} className="page-transition-enter">
            <Routes>
              <Route index                  element={<LookupView />} />
              <Route path="lookup"          element={<LookupView />} />
              <Route path="lookup/:ubid"    element={<UbidDetailView />} />
              <Route path="activity"        element={<ActivityView />} />
              <Route path="review"          element={<ReviewQueueView />} />
              <Route path="analytics"       element={<AnalyticsView />} />
              <Route path="admin"           element={<AdminView />} />
            </Routes>
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => (
  <ConfigProvider
    theme={{
      algorithm: antTheme.defaultAlgorithm,
      token: {
        colorPrimary: ORANGE,
        colorLink: ORANGE,
        borderRadius: 6,
      },
      components: {
        Button: { colorPrimary: ORANGE },
        Card: { borderRadiusLG: 8 },
        Table: { headerBg: '#fafafa', borderColor: '#f0f0f0' },
        Tag: { borderRadiusSM: 4 },
      },
    }}
  >
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/"      element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />

        {/* UBID detail — standalone, no sidebar, auth-gated */}
        <Route path="/ubid/:ubid" element={<RequireAuth><UbidDetailView /></RequireAuth>} />

        {/* Dashboard — all dashboard pages behind auth */}
        <Route path="/dashboard/*" element={<RequireAuth><AppLayout /></RequireAuth>} />

        {/* Legacy redirects so old /lookup etc. still work */}
        <Route path="/lookup"    element={<Navigate to="/dashboard/lookup"    replace />} />
        <Route path="/activity"  element={<Navigate to="/dashboard/activity"  replace />} />
        <Route path="/review"    element={<Navigate to="/dashboard/review"    replace />} />
        <Route path="/analytics" element={<Navigate to="/dashboard/analytics" replace />} />
        <Route path="/admin"     element={<Navigate to="/dashboard/admin"     replace />} />
      </Routes>
    </BrowserRouter>
  </ConfigProvider>
);

export default App;
