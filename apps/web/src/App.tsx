
import { Component, useCallback, useEffect, useState } from 'react';
import { flushSync } from 'react-dom';
import type { ErrorInfo, MouseEvent, ReactElement, ReactNode } from 'react';
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

type RoutePath = keyof typeof routes;
type TransitionCapableDocument = Document & { startViewTransition?: (callback: () => void) => unknown };

function normalizePath(path: string): RoutePath {
  return Object.prototype.hasOwnProperty.call(routes, path) ? (path as RoutePath) : '/';
}

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
}

function decodeHashTarget(hash: string) {
  const raw = hash.slice(1);
  if (!raw) return '';
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export default function App() {
  const [path, setPath] = useState<RoutePath>(() => normalizePath(window.location.pathname));
  const current = routes[path] ?? routes['/'];

  const scrollToCurrentHash = useCallback(() => {
    window.requestAnimationFrame(() => {
      const hash = decodeHashTarget(window.location.hash);
      if (hash) {
        const target = document.getElementById(hash);
        if (target && typeof target.scrollIntoView === 'function') target.scrollIntoView({ block: 'start', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
        return;
      }
      if (window.scrollY > 0 && typeof window.scrollTo === 'function') window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    });
  }, []);

  const applyRoute = useCallback((nextPath: RoutePath) => {
    const update = () => flushSync(() => setPath(nextPath));
    const transition = (document as TransitionCapableDocument).startViewTransition;
    if (transition && !prefersReducedMotion()) transition.call(document, update);
    else update();
  }, []);

  const navigate = useCallback((href: string) => {
    const url = new URL(href, window.location.origin);
    if (url.origin !== window.location.origin) {
      window.location.assign(url.href);
      return;
    }
    const nextPath = normalizePath(url.pathname);
    const nextLocation = `${url.pathname}${url.hash}`;
    if (`${window.location.pathname}${window.location.hash}` !== nextLocation) window.history.pushState({}, '', nextLocation);
    applyRoute(nextPath);
    scrollToCurrentHash();
  }, [applyRoute, scrollToCurrentHash]);

  const handleNavClick = useCallback((event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.currentTarget.target) return;
    event.preventDefault();
    navigate(event.currentTarget.href);
  }, [navigate]);

  useEffect(() => {
    const handlePopState = () => {
      applyRoute(normalizePath(window.location.pathname));
      scrollToCurrentHash();
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [applyRoute, scrollToCurrentHash]);

  return <DashboardErrorBoundary><div className="app-shell" data-testid="dashboard-shell"><nav className="nav" aria-label="Primary"><h1>Thomas Health</h1>{primaryRoutes.map((route) => <a key={route} aria-current={path === route || (path === '/' && route === '/today') ? 'page' : undefined} href={route} onClick={handleNavClick}>{routes[route].label}</a>)}<div className="global-actions" aria-label="Global actions"><a href="/growth#add-measurement" onClick={handleNavClick}>+ Add Measurement</a><a href="/timeline#upload" onClick={handleNavClick}>Upload Record</a><a href="/doctor-prep#print" onClick={handleNavClick}>Print Summary</a></div></nav><main key={path} className="main route-transition" data-route={path}>{current.element}</main></div></DashboardErrorBoundary>;
}
