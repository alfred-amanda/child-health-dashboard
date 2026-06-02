import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { BunnyBackdrop, GrowthPage, TodayPage } from './pages';
import { contrastRatio } from './tokens';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.includes('/api/growth')) {
      return Promise.resolve(new Response(JSON.stringify({
        percentiles: {
          weight: { percentile: 58.9, label: 'tracking along the ~59th percentile', source: 'WHO male LMS fixture' },
          length: { percentile: 72.4, label: 'tracking along the ~72nd percentile', source: 'WHO male LMS fixture' },
          head: { percentile: 82.1, label: 'tracking along the ~82nd percentile', source: 'WHO male LMS fixture' }
        },
        projection: 'points_only_no_projection',
        measurements: []
      }), { status: 200 }));
    }
    if (url.includes('/api/research')) {
      return Promise.resolve(new Response(JSON.stringify({
        mode: 'offline-cache',
        updates: [{ title: 'Respiratory virus activity', summary: 'Watch breathing and feeding patterns.', confidence: 'high', sources: [{ title: 'CDC RSV', url: 'https://cdc.gov/rsv', date: '2026-06-01' }] }]
      }), { status: 200 }));
    }
    if (url.includes('/api/watch')) {
      return Promise.resolve(new Response(JSON.stringify({
        global_boundary_note: 'This local dashboard supports the care plan and keeps physician questions in Doctor Prep.',
        actionable: [
          { title: 'Unsuppressible shaking', action: 'Call 911 now per discharge instructions.', urgency: '911', confidence: 'high', source_type: 'discharge_red_flag', sources: [{ title: 'ER AVS', url: 'local:SRC-003', date: '2026-05-31' }] },
          { title: 'Respiratory virus activity', action: 'Watch breathing and feeding patterns.', urgency: 'watch', confidence: 'high', source_type: 'research', sources: [{ title: 'CDC RSV', url: 'https://cdc.gov/rsv', date: '2026-06-01' }] }
        ],
        lower_confidence: [{ title: 'Lower-confidence signal', action: 'Shown for awareness only.', urgency: 'routine', confidence: 'low', source_type: 'research', sources: [{ title: 'County digest', url: 'https://example.org', date: '2026-06-01' }] }]
      }), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({
      child: 'Thomas William Chen',
      status: 'routine',
      status_strip: 'Routine watch: reassuring signs first, keep red flags one tap away',
      primary_recommendation: { evidence: 'feeding improved', action: 'watch feeding and wet diapers', urgency: 'routine', confidence: 'moderate', source: { source_id: 'SRC-003', title: 'ER AVS', page: 1, snippet: 'feeding improved', confidence: 0.95 } },
      reassurance_first: [{ label: 'Clinically improved at discharge', source: 'SRC-003 p.1' }],
      watching: ['DAT-positive jaundice/anemia watch'],
      red_flags: [{ key: 'seizure', label: 'Unsuppressible shaking', source: 'SRC-003 p.2' }]
    }), { status: 200 }));
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  cleanup();
});

describe('v2 redesign contract', () => {
  it('renders exactly the lean Title Case nav and global actions', () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    const nav = screen.getByRole('navigation', { name: /primary/i });
    for (const label of ['Today', 'Growth', 'Health', 'Timeline', 'Doctor Prep']) expect(nav).toHaveTextContent(label);
    for (const removed of ['Tokens', 'Fact Review', 'Today Alarm', 'Growth Feeding']) expect(nav).not.toHaveTextContent(removed);
    expect(screen.getByRole('link', { name: /upload record/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /print summary/i })).toBeInTheDocument();
  });

  it('uses decorative bunny art behind scrim with AA-safe surfaces', () => {
    render(<BunnyBackdrop season="spring" />);
    expect(screen.getByTestId('bunny-backdrop')).toHaveAttribute('aria-hidden', 'true');
    expect(contrastRatio('#17324d', '#f8fbff')).toBeGreaterThanOrEqual(4.5);
  });

  it('today shows high-confidence actionable watch, separated lower-confidence signals, and one global boundary note', async () => {
    render(<TodayPage />);
    expect(await screen.findByText(/Unsuppressible shaking/)).toBeInTheDocument();
    expect(screen.getByText(/Call 911 now/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /Lower-confidence \/ being looked into/i })).toBeInTheDocument();
    expect(screen.getByText(/Shown for awareness only/)).toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toContain('ask your pediatrician');
    expect(document.body.textContent?.toLowerCase()).not.toContain('ask your doctor');
    expect(document.body.textContent?.toLowerCase()).not.toContain('safe to wait');
    expect(screen.getAllByText(/supports the care plan/i)).toHaveLength(1);
  });

  it('growth page logs an at-home weight with <=3 required fields and renders WHO male percentiles', async () => {
    render(<GrowthPage />);
    expect(await screen.findByText(/tracking along the ~59th percentile/i)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/weight pounds/i), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText(/caregiver/i), { target: { value: 'John' } });
    fireEvent.click(screen.getByRole('button', { name: /save measurement/i }));
    expect(screen.getByText(/Saved parent-entered measurement from John/i)).toBeInTheDocument();
  });
});
