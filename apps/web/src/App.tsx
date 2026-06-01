
import type { ReactElement } from 'react';
import { ChartsPage, ConditionsPage, DevelopmentPage, DoctorPrepPage, GrowthFeedingPage, ReassuranceWatch, ReviewQueuePage, TasksPage, TimelinePage, TodayPage, TokenCatalog, VaccinesPage } from './pages';

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
  return <div className="app-shell"><nav className="nav" aria-label="Primary"><h1>Thomas Health</h1>{Object.keys(routes).filter((route) => route !== '/').map((route) => <a key={route} href={route}>{route.replace('/', '').replace('-', ' ')}</a>)}</nav><main className="main">{routes[path] ?? <TodayPage />}</main></div>;
}
