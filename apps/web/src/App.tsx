
import { Component } from 'react';
import type { ErrorInfo, ReactElement, ReactNode } from 'react';
import { HealthPage, GrowthPage, DoctorPrepPage, TimelinePage, TodayPage } from './pages';

class DashboardErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('Dashboard render failed', error, info.componentStack); }
  render() {
    if (this.state.error) return <main className="main" role="alert"><section className="card"><h1>Dashboard failed to render</h1><p>{this.state.error.message}</p><p>API health: <a href="/api/health">/api/health</a></p></section></main>;
    return this.props.children;
  }
}

const routes: Record<string, { label: string; element: ReactElement }> = {
  '/': { label: 'Today', element: <TodayPage /> },
  '/today': { label: 'Today', element: <TodayPage /> },
  '/growth': { label: 'Growth', element: <GrowthPage /> },
  '/health': { label: 'Health', element: <HealthPage /> },
  '/timeline': { label: 'Timeline', element: <TimelinePage /> },
  '/doctor-prep': { label: 'Doctor Prep', element: <DoctorPrepPage /> }
};

const primaryRoutes = ['/today', '/growth', '/health', '/timeline', '/doctor-prep'];

export default function App() {
  const path = window.location.pathname;
  const current = routes[path] ?? routes['/'];
  return <DashboardErrorBoundary><div className="app-shell" data-testid="dashboard-shell"><nav className="nav" aria-label="Primary"><h1>Thomas Health</h1>{primaryRoutes.map((route) => <a key={route} aria-current={path === route || (path === '/' && route === '/today') ? 'page' : undefined} href={route}>{routes[route].label}</a>)}<div className="global-actions" aria-label="Global actions"><a href="/growth#add-measurement">+ Add Measurement</a><a href="/timeline#upload">Upload Record</a><a href="/doctor-prep#print">Print Summary</a></div></nav><main className="main route-transition">{current.element}</main></div></DashboardErrorBoundary>;
}
