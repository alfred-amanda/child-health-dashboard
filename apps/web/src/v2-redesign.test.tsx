import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { BunnyBackdrop, GrowthPage, TodayPage } from './pages';
import { contrastRatio } from './tokens';

type ArtManifest = { provider: string; model: string; subject_name?: string; privacy_note?: string; assets: { season?: string; slug?: string; file: string; format: string; bytes: number; sha256: string; prompt: string; vision_review: { name_exact?: boolean; newborn_appropriate?: boolean; non_scary?: boolean; no_logos_or_watermarks?: boolean } }[] };

function repoPath(...segments: string[]) {
  let current = process.cwd();
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = join(current, ...segments);
    if (existsSync(candidate)) return candidate;
    const parent = dirname(current);
    if (parent === current) break;
    current = parent;
  }
  throw new Error(`Could not locate ${segments.join('/')}`);
}

function loadArtProvenance() {
  return JSON.parse(readFileSync(repoPath('docs/assets/thomas-bunny-art-provenance.json'), 'utf8')) as ArtManifest;
}

function loadV6ArtProvenance() {
  return JSON.parse(readFileSync(repoPath('docs/assets/v6-generated-art-provenance.json'), 'utf8')) as ArtManifest;
}

function readAsset(file: string) {
  return readFileSync(repoPath('apps/web/src/assets', file));
}

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
  Reflect.deleteProperty(document, 'startViewTransition');
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
    const backdrop = screen.getByTestId('bunny-backdrop');
    expect(backdrop).toHaveAttribute('aria-hidden', 'true');
    expect(backdrop).toHaveAttribute('data-season', 'spring');
    expect(backdrop.getAttribute('style')).toContain('thomas-bunny-spring.jpg');
    expect(contrastRatio('#17324d', '#f8fbff')).toBeGreaterThanOrEqual(4.5);
  });

  it('commits generated GPT Image provenance for all Thomas seasonal backgrounds', () => {
    const artProvenance = loadArtProvenance();
    expect(artProvenance.provider).toBe('openai-codex');
    expect(artProvenance.model).toBe('gpt-image-2-medium');
    expect(artProvenance.subject_name).toBe('Thomas');
    expect(artProvenance.assets).toHaveLength(4);
    for (const season of ['spring', 'summer', 'autumn', 'winter']) {
      const asset = artProvenance.assets.find((item) => item.season === season);
      expect(asset?.file).toBe(`thomas-bunny-${season}.jpg`);
      expect(asset?.format).toBe('jpeg');
      expect(asset?.bytes).toBe(readAsset(asset?.file ?? '').byteLength);
      expect(asset?.sha256).toMatch(/^[a-f0-9]{64}$/);
      expect(asset?.prompt).toContain('Thomas');
      expect(createHash('sha256').update(readAsset(asset?.file ?? '')).digest('hex')).toBe(asset?.sha256);
      expect(asset?.vision_review.name_exact).toBe(true);
      expect(asset?.vision_review.newborn_appropriate).toBe(true);
    }
  });

  it('uses client-side route transitions between dashboard pages', async () => {
    window.history.pushState({}, '', '/today');
    const startViewTransition = vi.fn((callback: () => void) => {
      callback();
      return { finished: Promise.resolve() };
    });
    Object.defineProperty(document, 'startViewTransition', { configurable: true, value: startViewTransition });
    render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'Growth' }));
    expect(window.location.pathname).toBe('/growth');
    expect(screen.getByRole('heading', { name: 'Growth' })).toBeInTheDocument();
    expect(await screen.findByText(/tracking along the ~59th percentile/i)).toBeInTheDocument();
    expect(document.querySelector('[data-route="/growth"]')).toHaveClass('route-transition');
    expect(startViewTransition).toHaveBeenCalledOnce();
  });

  it('skips document view transitions when reduced motion is requested', async () => {
    window.history.pushState({}, '', '/today');
    const startViewTransition = vi.fn((callback: () => void) => {
      callback();
      return { finished: Promise.resolve() };
    });
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn()
    })));
    Object.defineProperty(document, 'startViewTransition', { configurable: true, value: startViewTransition });
    render(<App />);
    fireEvent.click(screen.getByRole('link', { name: 'Growth' }));
    expect(window.location.pathname).toBe('/growth');
    expect(await screen.findByText(/tracking along the ~59th percentile/i)).toBeInTheDocument();
    expect(startViewTransition).not.toHaveBeenCalled();
  });

  it('supports hash-target navigation without document reload', async () => {
    window.history.pushState({}, '', '/today');
    render(<App />);
    fireEvent.click(screen.getByRole('link', { name: /add measurement/i }));
    expect(window.location.pathname).toBe('/growth');
    expect(window.location.hash).toBe('#add-measurement');
    expect(await screen.findByText(/tracking along the ~59th percentile/i)).toBeInTheDocument();
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

  it('renders V6 infant body hero, right rail, concern detail, and friendly API-down state', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network timeout'))));
    render(<TodayPage />);
    expect(await screen.findByText(/API fallback: API down, using local fallback data/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Clickable infant body concern map/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Brain \/ CSF/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Blood \/ Liver/i }));
    expect(screen.getByText(/Jaundice \/ DAT/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Real metrics and care logistics/i)).toHaveTextContent('not yet recorded');
    expect(screen.getByText(/Medication list: not yet recorded/i)).toBeInTheDocument();
  });

  it('commits generated V6 family scene and organ art provenance with SHA checks', () => {
    const artProvenance = loadV6ArtProvenance();
    expect(artProvenance.provider).toBe('openai-codex');
    expect(artProvenance.model).toBe('gpt-image-2-medium');
    expect(artProvenance.assets.map((asset) => asset.prompt).join(' ')).not.toMatch(/diagnos|MRN|address/i);
    for (const slug of ['family-today', 'family-growth', 'family-health', 'family-timeline', 'family-doctor-prep', 'organ-parechovirus', 'organ-brain-csf', 'organ-blood-liver', 'organ-ear', 'organ-neck']) {
      const asset = artProvenance.assets.find((item) => item.slug === slug);
      expect(asset?.file).toBe(`apps/web/src/assets/${slug}.jpg`);
      const bytes = readFileSync(repoPath(asset?.file ?? ''));
      expect(asset?.bytes).toBe(bytes.byteLength);
      expect(createHash('sha256').update(bytes).digest('hex')).toBe(asset?.sha256);
      expect(asset?.vision_review.non_scary).toBe(true);
      expect(asset?.vision_review.no_logos_or_watermarks).toBe(true);
    }
  });
});
