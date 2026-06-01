import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({
    child: 'Thomas William Chen',
    status: 'routine',
    status_strip: 'Routine watch: reassuring signs first, keep red flags one tap away',
    primary_recommendation: {
      evidence: 'Thomas continued to feed well throughout his hospital stay and fever resolved by discharge',
      action: 'watch feeding, wet diapers, temperature, and use the discharge red-flag reference if symptoms appear',
      urgency: 'routine',
      confidence: 'moderate',
      source: { source_id: 'SRC-003', title: 'ER AVS May 31 2026', page: 1, snippet: 'continued to feed well throughout his hospital stay', confidence: 0.95 }
    },
    reassurance_first: [{ label: 'Clinically improved at discharge', source: 'SRC-003 p.1' }],
    watching: ['DAT-positive jaundice/anemia watch'],
    red_flags: [{ key: 'wet_diapers_24h', label: 'Less than 4 wet diapers in 24 hours', source: 'SRC-003 p.2' }]
  }), { status: 200 }))));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('App smoke', () => {
  it('renders the shell and Today page at root and hydrates API-backed data', async () => {
    window.history.pushState({}, '', '/');
    render(<App />);
    expect(screen.getByRole('navigation', { name: /primary/i })).toHaveTextContent('Thomas Health');
    expect(screen.getByText(/Routine watch/i)).toBeInTheDocument();
    expect(screen.getByText(/Current watch/i)).toBeInTheDocument();
    expect(await screen.findByText(/Live API data loaded for Thomas William Chen/)).toBeInTheDocument();
  });
});
