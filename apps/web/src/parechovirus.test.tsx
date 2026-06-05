import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ParechovirusPage } from './pages';

const catalogResponse = {
  symptoms: [
    {
      key: 'fever',
      label: 'Fever (measured)',
      category: 'systemic',
      severity_min: 2,
      severity_max: 5,
      measurement: 'temperature_c',
      unit: 'C',
      description: 'A measured rectal or axillary temperature at or above 38.0 C.',
      parent_prompt: 'What was the measured temperature?',
      source_id: 'SRC-003',
      source_title: 'ER AVS May 31 2026',
      page: 2,
      snippet: 'call your pediatrician for fevers reaching 38.0 c or above',
      confidence: 0.99,
    },
    {
      key: 'seizure',
      label: 'Seizure activity',
      category: 'neurologic',
      severity_min: 5,
      severity_max: 5,
      measurement: 'duration_minutes',
      unit: 'min',
      description: 'Always emergent.',
      parent_prompt: 'How long did the episode last?',
      source_id: 'SRC-003',
      source_title: 'ER AVS May 31 2026',
      page: 2,
      snippet: 'call 911 immediately if ... seizure',
      confidence: 0.99,
    },
  ],
  rules: [
    {
      rule_key: 'parecho_seizure',
      label: 'Seizure activity',
      urgency: '911',
      action: 'Call 911 immediately',
      source_id: 'SRC-003',
      source_title: 'ER AVS May 31 2026',
      page: 2,
      snippet: 'call 911',
      confidence: 0.99,
    },
    {
      rule_key: 'parecho_fever_neonate',
      label: 'Fever >=38.0 C in infant under 3 months',
      urgency: 'today',
      action: 'Call the pediatrician now',
      source_id: 'SRC-003',
      source_title: 'ER AVS May 31 2026',
      page: 2,
      snippet: 'call your pediatrician',
      confidence: 0.99,
    },
  ],
};

const emptyToday = {
  child_id: 'thomas',
  generated_at: '2026-06-04T23:00:00Z',
  highest_urgency: 'routine',
  symptom_count_24h: 0,
  open_issue_count: 0,
  symptoms_today: [],
  open_issues: [],
};

const feverToday = {
  child_id: 'thomas',
  generated_at: '2026-06-04T23:00:00Z',
  highest_urgency: 'today',
  symptom_count_24h: 1,
  open_issue_count: 1,
  symptoms_today: [
    {
      id: 'sym1',
      symptom_key: 'fever',
      severity: 3,
      measurement_value: 38.5,
      duration_minutes: null,
      observed_at: '2026-06-04T18:00:00Z',
      notes: 'felt warm at 6pm',
      actor: 'parent',
      source: 'parent_log',
    },
  ],
  open_issues: [
    {
      id: 'iss1',
      rule_key: 'parecho_fever_neonate',
      label: 'Fever >=38.0 C in infant under 3 months',
      urgency: 'today',
      action: 'Call the pediatrician now',
      evidence: 'triage rule parecho_fever_neonate fired for symptoms: fever',
      source_id: 'SRC-003',
      source_title: 'ER AVS May 31 2026',
      page: 2,
      snippet: 'call your pediatrician',
      confidence: 0.99,
      status: 'open',
      opened_at: '2026-06-04T18:01:00Z',
      acknowledged_at: null,
      acknowledged_by: null,
      resolved_at: null,
      resolved_by: null,
      resolution_notes: null,
    },
  ],
};

const emptyList = { count: 0, symptoms: [] };
const emptyIssues = { count: 0, issues: [] };

function mockFetchSequence(responses: Array<{ url: RegExp; body: unknown }>) {
  return vi.fn((input: RequestInfo | URL) => {
    const url = typeof input === 'string' ? input : (input as URL).toString();
    const match = responses.find((r) => r.url.test(url));
    if (!match) return Promise.reject(new Error(`unmocked ${url}`));
    return Promise.resolve(
      new Response(JSON.stringify(match.body), { status: 200, headers: { 'Content-Type': 'application/json' } })
    );
  });
}

describe('ParechovirusPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it('shows the routine state when there are no open issues', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetchSequence([
        { url: /\/api\/parechovirus\/catalog/, body: catalogResponse },
        { url: /\/api\/parechovirus\/today/, body: emptyToday },
        { url: /\/api\/parechovirus\/symptoms/, body: emptyList },
        { url: /\/api\/parechovirus\/triage/, body: emptyIssues },
      ])
    );
    render(<ParechovirusPage />);
    expect(await screen.findByTestId('parechovirus-page')).toBeInTheDocument();
    expect(screen.getByText(/Routine/i)).toBeInTheDocument();
    expect(screen.getByText(/No open issues/)).toBeInTheDocument();
  });

  it('renders open issues with urgency badges', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetchSequence([
        { url: /\/api\/parechovirus\/catalog/, body: catalogResponse },
        { url: /\/api\/parechovirus\/today/, body: feverToday },
        { url: /\/api\/parechovirus\/symptoms/, body: { count: 1, symptoms: feverToday.symptoms_today } },
        { url: /\/api\/parechovirus\/triage/, body: { count: 0, issues: [] } },
      ])
    );
    render(<ParechovirusPage />);
    await waitFor(() => expect(screen.getByTestId('parecho-triage-queue')).toBeInTheDocument());
    const queue = screen.getByTestId('parecho-triage-queue');
    expect(within(queue).getByText(/Fever >=38.0 C/)).toBeInTheDocument();
    expect(within(queue).getByText(/Call the pediatrician now/)).toBeInTheDocument();
    expect(screen.getByText(/felt warm at 6pm/)).toBeInTheDocument();
  });

  it('shows a loading state when the API is down', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('boom'))));
    render(<ParechovirusPage />);
    expect(await screen.findByTestId('parechovirus-loading')).toBeInTheDocument();
    expect(screen.getByText(/Loading parechovirus catalog/)).toBeInTheDocument();
  });
});
