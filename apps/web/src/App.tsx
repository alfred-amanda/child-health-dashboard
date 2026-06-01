
import { Component } from 'react';
import type { ErrorInfo, ReactElement, ReactNode } from 'react';
import { ChartsPage, ConditionsPage, DevelopmentPage, DoctorPrepPage, GrowthFeedingPage, ReassuranceWatch, ReviewQueuePage, TasksPage, TimelinePage, TodayPage, TokenCatalog, VaccinesPage } from './pages';

class DashboardErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Dashboard render failed', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return <main className="main" role="alert"><section className="card"><h1>Dashboard failed to render</h1><p>{this.state.error.message}</p><p>API health: <a href="/api/health">/api/health</a></p></section></main>;
    }
    return this.props.children;
  }
}

const routes: Record<string, ReactElement> = {
  '/': <TodayPage />,
  '/today': <TodayPage />,
  '/today-alarm': <TodayPage alarm />,
  '/tokens': <TokenCatalog />,
  '/timeline': <TimelinePage />,
  '/conditions': <ConditionsPage />,
  '/review': <ReviewQueuePage />,
  '/reassurance': <ReassuranceWatch />,
  '/charts': <ChartsPage />,
  '/growth-feeding': <GrowthFeedingPage />,
  '/development': <DevelopmentPage />,
  '/vaccines': <VaccinesPage />,
  '/tasks': <TasksPage />,
  '/doctor-prep': <DoctorPrepPage />
};

export default function App() {
  const path = window.location.pathname;
  return <DashboardErrorBoundary><div className="app-shell" data-testid="dashboard-shell"><nav className="nav" aria-label="Primary"><h1>Thomas Health</h1>{Object.keys(routes).filter((route) => route !== '/').map((route) => <a key={route} href={route}>{route.replace('/', '').replace('-', ' ')}</a>)}</nav><main className="main">{routes[path] ?? <TodayPage />}</main></div></DashboardErrorBoundary>;
}
