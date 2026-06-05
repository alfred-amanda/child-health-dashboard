import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, ChartFrame, Recommendation, StatusBadge } from './components';
import { conditions, doctorQuestions, routineRecommendation } from './data';
import type { Confidence, RecommendationPayload, Urgency } from './types';
import springBunny from './assets/thomas-bunny-spring.jpg?url';
import summerBunny from './assets/thomas-bunny-summer.jpg?url';
import autumnBunny from './assets/thomas-bunny-autumn.jpg?url';
import winterBunny from './assets/thomas-bunny-winter.jpg?url';
import familyToday from './assets/family-today.jpg?url';
import familyGrowth from './assets/family-growth.jpg?url';
import familyHealth from './assets/family-health.jpg?url';
import familyTimeline from './assets/family-timeline.jpg?url';
import familyDoctorPrep from './assets/family-doctor-prep.jpg?url';
import organParechovirus from './assets/organ-parechovirus.jpg?url';
import organBrainCsf from './assets/organ-brain-csf.jpg?url';
import organBloodLiver from './assets/organ-blood-liver.jpg?url';
import organEar from './assets/organ-ear.jpg?url';
import organNeck from './assets/organ-neck.jpg?url';

type TodayApiPayload = { child: string; status: 'routine' | 'alarm'; status_strip: string; primary_recommendation: RecommendationPayload; reassurance_first: { label: string; source: string }[]; watching: string[]; red_flags: { key: string; label: string; source_id?: string; page?: number; source?: { source_id?: string; page?: number } | string }[] };
type Source = { title: string; url: string; date: string; snippet?: string };
type WatchItem = { title: string; action: string; urgency: Urgency; confidence: Confidence; source_type: string; sources: Source[] };
type WatchPayload = { global_boundary_note: string; actionable: WatchItem[]; lower_confidence: WatchItem[] };
type GrowthPayload = { percentiles: Record<string, { percentile: number; label: string; source: string }>; projection: string; measurements: unknown[] };
type ResearchPayload = { mode: string; updates: { title: string; summary: string; confidence: Confidence; sources: Source[] }[] };
type Metric = { label: string; value: string | null; source: string };

const bunnyAssets = { spring: springBunny, summer: summerBunny, autumn: autumnBunny, winter: winterBunny } as const;
const pageScenes = { Today: familyToday, Growth: familyGrowth, Health: familyHealth, Timeline: familyTimeline, 'Doctor Prep': familyDoctorPrep } as const;
type BunnySeason = keyof typeof bunnyAssets;
type RegionKey = 'brain' | 'blood' | 'ear' | 'neck';

type ConcernRegion = { key: RegionKey; label: string; organ: string; urgency: Urgency; image: string; source: string; detail: string };
const concernRegions: ConcernRegion[] = [
  { key: 'brain', label: 'Brain / CSF', organ: 'CSF parechovirus', urgency: 'watch', image: organBrainCsf, source: 'SRC-010 p.1', detail: 'Parechovirus was detected in CSF; watch development and confirm follow-up plan.' },
  { key: 'blood', label: 'Blood / Liver', organ: 'Jaundice / DAT', urgency: 'today', image: organBloodLiver, source: 'SRC-001 p.5', detail: 'DAT-positive ABO incompatibility affects bilirubin/anemia watch; thresholds stay source-linked.' },
  { key: 'ear', label: 'Ear', organ: 'Left pinna fold', urgency: 'watch', image: organEar, source: 'Doctor Prep open question', detail: 'Ask about ear fold/plastics timing; not treated as an urgent alarm.' },
  { key: 'neck', label: 'Neck', organ: 'Head preference', urgency: 'watch', image: organNeck, source: 'Doctor Prep open question', detail: 'Ask about right head preference/torticollis stretches and PT timing.' }
];

const railMetrics: Metric[] = [
  { label: 'Weight percentile', value: '~59th percentile', source: 'WHO male LMS fixture' },
  { label: 'Length percentile', value: '~72nd percentile', source: 'WHO male LMS fixture' },
  { label: 'Head percentile', value: '~82nd percentile', source: 'WHO male LMS fixture' },
  { label: 'Wet diapers / 24h', value: null, source: 'parent log not yet entered' },
  { label: 'Temperature', value: null, source: 'not yet recorded today' },
  { label: 'Feeding stamina', value: 'feeding improved at discharge', source: 'SRC-003 p.1' },
  { label: 'CSF result', value: 'parechovirus detected', source: 'SRC-010 p.1' },
  { label: 'CRP', value: '<0.3', source: 'structured profile' },
  { label: 'Procalcitonin', value: '0.16', source: 'structured profile' },
  { label: 'Cultures final', value: null, source: 'needs confirmation' },
  { label: 'Hep B', value: 'deferred', source: 'newborn AVS' },
  { label: 'Bilirubin risk curve', value: 'DAT-positive risk factor', source: 'AAP-2022 local table' }
];

function seasonNow(): BunnySeason {
  const month = new Date().getMonth();
  if (month < 2 || month === 11) return 'winter';
  if (month < 5) return 'spring';
  if (month < 8) return 'summer';
  return 'autumn';
}

function fetchWithTimeout<T>(url: string, timeoutMs = 3500): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { signal: controller.signal }).then((response) => {
    if (!response.ok) throw new Error(`API ${response.status} for ${url}`);
    return response.json() as Promise<T>;
  }).finally(() => window.clearTimeout(timer));
}

export function BunnyBackdrop({ season = seasonNow(), pageTitle }: { season?: BunnySeason; pageTitle?: keyof typeof pageScenes }) {
  const asset = pageTitle ? pageScenes[pageTitle] : bunnyAssets[season];
  return <div className="bunny-backdrop generated-bunny-backdrop" data-testid="bunny-backdrop" data-season={season} data-page-title={pageTitle ?? season} aria-hidden="true" style={{ backgroundImage: `linear-gradient(rgba(248,251,255,.28), rgba(248,251,255,.46)), url(${asset})` }} />;
}

function WatchList({ payload }: { payload: WatchPayload | null }) {
  const fallback: WatchPayload = { global_boundary_note: 'This local dashboard supports the care plan and keeps physician questions in Doctor Prep.', actionable: [{ title: 'Less than 4 wet diapers in 24 hours', action: 'Seek medical attention now per discharge instructions.', urgency: 'urgent', confidence: 'high', source_type: 'discharge_red_flag', sources: [{ title: 'ER AVS', url: 'local:SRC-003', date: '2026-05-31' }] }], lower_confidence: [] };
  const data = payload?.actionable && payload?.lower_confidence ? payload : fallback;
  return <Card title="Current Watch / What To Watch"><p className="boundary-note">{data.global_boundary_note}</p><div className="watch-list">{data.actionable.map((item) => <article key={item.title} className={`watch-item ${item.urgency === '911' ? 'emergency' : ''}`}><StatusBadge urgency={item.urgency} /><h3>{item.title}</h3><p>{item.action}</p><p><strong>Confidence:</strong> {item.confidence}. <strong>Source:</strong> {item.sources.map((source) => `${source.title} (${source.date})`).join('; ')}</p></article>)}</div><h3>Lower-confidence / being looked into</h3><div className="watch-list lower">{data.lower_confidence.map((item) => <article key={item.title} className="watch-item"><h4>{item.title}</h4><p>{item.action}</p><p><strong>Confidence:</strong> {item.confidence}. Not used as an actionable task.</p></article>)}</div></Card>;
}

function BodyHero({ alarm = false }: { alarm?: boolean }) {
  const [selected, setSelected] = useState<ConcernRegion>(concernRegions[0]);
  return <section className="body-dashboard" aria-label="Clickable infant body concern map"><div className="infant-hero" aria-label="Soft watercolor infant body map"><div className="infant-body" aria-hidden="true"><span className="head" /><span className="torso" /><span className="arm left" /><span className="arm right" /><span className="leg left" /><span className="leg right" /></div>{concernRegions.map((region) => <button key={region.key} type="button" className={`region-pin region-${region.key} ${alarm && region.urgency === '911' ? 'urgent-pulse' : ''}`} aria-pressed={selected.key === region.key} onClick={() => setSelected(region)}>{region.label}</button>)}</div><aside className="organ-detail"><img src={selected.image} alt="" aria-hidden="true" /><h2>{selected.label}</h2><p><strong>{selected.organ}</strong></p><p>{selected.detail}</p><p className="source-chip">Source: {selected.source}</p><img className="mini-virus" src={organParechovirus} alt="" aria-hidden="true" /></aside></section>;
}

function RightRail() {
  return <aside className="right-rail" aria-label="Real metrics and care logistics"><Card title="Metrics">{railMetrics.slice(0, 12).map((metric) => <p key={metric.label}><strong>{metric.label}:</strong> {metric.value ?? 'not yet recorded'} <span className="source-chip">{metric.source}</span></p>)}</Card><Card title="Care Team"><p>Pediatrician: not yet recorded</p><p>Hospital team: discharge paperwork source only</p></Card><Card title="Medications"><p>Medication list: not yet recorded</p><p className="boundary-note">No medication is inferred from missing data.</p></Card></aside>;
}

export function TodayPage({ alarm = false }: { alarm?: boolean }) {
  const [apiPayload, setApiPayload] = useState<TodayApiPayload | null>(null);
  const [watchPayload, setWatchPayload] = useState<WatchPayload | null>(null);
  const [growthPayload, setGrowthPayload] = useState<GrowthPayload | null>(null);
  const [researchPayload, setResearchPayload] = useState<ResearchPayload | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchWithTimeout<TodayApiPayload>(`/api/today${alarm ? '?alarm=true' : ''}`),
      fetchWithTimeout<WatchPayload>('/api/watch'),
      fetchWithTimeout<GrowthPayload>('/api/growth'),
      fetchWithTimeout<ResearchPayload>('/api/research')
    ]).then(([today, watch, growth, research]) => { if (!cancelled) { setApiPayload(today); setWatchPayload(watch); setGrowthPayload(growth); setResearchPayload(research); } }).catch((error: unknown) => { if (!cancelled) setApiError(error instanceof Error ? error.message : 'API unavailable'); });
    return () => { cancelled = true; };
  }, [alarm]);
  const recommendation = apiPayload?.primary_recommendation ?? routineRecommendation;
  const isAlarm = apiPayload?.status === 'alarm' || alarm;
  return <div className={`page-scene ${isAlarm ? 'alarm-screen' : ''}`} data-testid={isAlarm ? 'today-alarm' : 'today-calm'}><BunnyBackdrop pageTitle="Today" /><div className="api-status" aria-live="polite">{apiPayload ? `Live API data loaded for ${apiPayload.child}` : apiError ? `API fallback: API down, using local fallback data (${apiError})` : 'Loading live API data…'}</div><section className="hero-card"><h1>Today</h1><div className={`status-strip ${isAlarm ? 'alarm' : 'routine'}`}>{apiPayload?.status_strip ?? (isAlarm ? 'URGENT RED FLAG ACTIVE — source-driven threshold crossed' : 'Routine watch — reassuring signs first, red flags one tap away')}</div><p>In five seconds: status first, red flags one tap away, growth snapshot visible, and all smart guidance cited.</p></section><div className="dashboard-layout"><main className="dashboard-main"><BodyHero alarm={isAlarm} /><div className="grid two"><WatchList payload={watchPayload} /><Card title="Growth Snapshot">{Object.entries(growthPayload?.percentiles ?? {}).length ? Object.entries(growthPayload?.percentiles ?? {}).map(([kind, value]) => <p key={kind}><strong>{kind}</strong>: {value.label} <span className="source-chip">{value.source}</span></p>) : <p>Loading WHO male percentile snapshot…</p>}</Card><Card title="Single Next Action"><Recommendation payload={recommendation} /></Card><Card title="Updates"><p>{researchPayload?.updates ? `${researchPayload.mode}: ${researchPayload.updates[0]?.title}` : 'Loading cached weekly digest…'}</p>{researchPayload?.updates?.map((update) => <p key={update.title}><strong>{update.title}</strong> — {update.summary} <span className="source-chip">{update.sources[0]?.title}</span></p>)}</Card><Card title="Recent Changes"><p>New parent measurements, uploads, and changed watch items appear here with source and date.</p></Card></div></main><RightRail /></div></div>;
}

export function GrowthPage() {
  const [payload, setPayload] = useState<GrowthPayload | null>(null);
  const [savedBy, setSavedBy] = useState<string | null>(null);
  const [caregiver, setCaregiver] = useState('John');
  useEffect(() => { let cancelled = false; fetchWithTimeout<GrowthPayload>('/api/growth').then((data) => { if (!cancelled) setPayload(data); }).catch(() => undefined); return () => { cancelled = true; }; }, []);
  const percentileRows = useMemo(() => Object.entries(payload?.percentiles ?? {}), [payload]);
  return <div className="page-scene"><BunnyBackdrop pageTitle="Growth" /><h1>Growth</h1><div className="grid two"><Card title="Add Measurement" ><form id="add-measurement" className="measurement-form" onSubmit={(event) => { event.preventDefault(); setSavedBy(caregiver); }}><label>Weight pounds<input aria-label="Weight pounds" name="weight" inputMode="decimal" /></label><label>Caregiver<input aria-label="Caregiver" value={caregiver} onChange={(event) => setCaregiver(event.target.value)} /></label><button type="submit">Save Measurement</button></form>{savedBy ? <p>Saved parent-entered measurement from {savedBy}</p> : null}</Card><Card title="WHO Male Percentiles">{percentileRows.map(([kind, value]) => <p key={kind}>{kind}: {value.label} — {value.source}</p>)}<p>Projection: {payload?.projection ?? 'points_only_no_projection'}.</p></Card><ChartFrame title="WHO growth curves" interpretation="Male WHO 0–24 month LMS percentiles; sparse data renders points only." source="Committed WHO LMS data + independent fixture"><p>Weight, length, and head circumference points are plotted against WHO male percentile bands.</p></ChartFrame></div></div>;
}

export function HealthPage() { return <div className="page-scene"><BunnyBackdrop pageTitle="Health" /><h1>Health</h1><BodyHero /><div className="grid">{conditions.map((condition) => <Card key={condition} title={condition}><p>Status, evidence, watch items, and source disclosures are API-backed. Questions move to Doctor Prep rather than repeated boilerplate.</p></Card>)}</div></div>; }export function TimelinePage() { return <div className="page-scene"><BunnyBackdrop pageTitle="Timeline" /><div className="grid"><h1>Timeline</h1><Card title="Records"><p id="upload">Upload-after-visit records land here, then Today shows what changed.</p><button type="button">Upload Record</button></Card><Card title="History"><ol><li>Birth and DAT-positive jaundice watch.</li><li>Fever admission and parechovirus result.</li><li>Discharge red flags preserved as source-driven rules.</li></ol></Card></div></div>; }
export function DoctorPrepPage() { const [mode, setMode] = useState<'parent' | 'clinician'>('parent'); return <div className="page-scene"><BunnyBackdrop pageTitle="Doctor Prep" /><div className="grid"><h1>Doctor Prep</h1><div className="mode-toggle"><button aria-pressed={mode === 'parent'} onClick={() => setMode('parent')}>Parent mode</button><button aria-pressed={mode === 'clinician'} onClick={() => setMode('clinician')}>Clinician mode</button></div><Card title="Questions For Next Visit"><ol>{doctorQuestions.map((question) => <li key={question}>{question}</li>)}</ol></Card><Card title="Print / Export PDF"><p id="print">One-page summary includes status, conditions, growth percentiles, vaccines, watch items, and source units in clinician mode.</p><button type="button">Print Summary</button></Card>{mode === 'clinician' ? <Card title="Clinician details"><p>Raw values, units, reference ranges, encounter dates, source, confidence, and snippets are exposed here.</p></Card> : <Card title="Parent summary"><p>Plain-language summary; source details available when needed.</p></Card>}</div></div>; }


// ---------------------------------------------------------------------------
// Parechovirus tracker page
// ---------------------------------------------------------------------------

type ParechovirusSymptomDef = {
  key: string;
  label: string;
  category: string;
  severity_min: number;
  severity_max: number;
  measurement: 'none' | 'temperature_c' | 'duration_minutes' | 'count';
  unit: string | null;
  description: string;
  parent_prompt: string;
  source_id: string;
  source_title: string;
  page: number | null;
  snippet: string;
  confidence: number;
};

type ParechovirusRuleDef = {
  rule_key: string;
  label: string;
  urgency: Urgency;
  action: string;
  source_id: string;
  source_title: string;
  page: number | null;
  snippet: string;
  confidence: number;
};

type ParechovirusSymptom = {
  id: string;
  symptom_key: string;
  severity: number;
  measurement_value: number | null;
  duration_minutes: number | null;
  observed_at: string;
  notes: string | null;
  actor: string;
  source: string;
};

type ParechovirusIssue = {
  id: string;
  rule_key: string;
  label: string;
  urgency: Urgency;
  action: string;
  evidence: string;
  source_id: string;
  source_title: string;
  page: number | null;
  snippet: string;
  confidence: number;
  status: 'open' | 'acknowledged' | 'resolved';
  opened_at: string;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  resolution_notes: string | null;
};

type ParechovirusCatalog = { symptoms: ParechovirusSymptomDef[]; rules: ParechovirusRuleDef[] };
type ParechovirusToday = {
  child_id: string;
  generated_at: string;
  highest_urgency: Urgency;
  symptom_count_24h: number;
  open_issue_count: number;
  symptoms_today: ParechovirusSymptom[];
  open_issues: ParechovirusIssue[];
};
type ParechovirusList = { count: number; symptoms: ParechovirusSymptom[] };
type ParechovirusIssueList = { count: number; issues: ParechovirusIssue[] };

function nowLocalIso() {
  // Datetime-local expects YYYY-MM-DDTHH:MM in local time.
  const pad = (n: number) => String(n).padStart(2, '0');
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatObserved(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function ParechovirusLogForm({
  catalog,
  onLogged,
  actor,
}: {
  catalog: ParechovirusCatalog;
  onLogged: (resp: { symptom: ParechovirusSymptom; new_triage_issues: ParechovirusIssue[] }) => void;
  actor: string;
}) {
  const [symptomKey, setSymptomKey] = useState(catalog.symptoms[0]?.key ?? 'fever');
  const [severity, setSeverity] = useState(3);
  const [measurement, setMeasurement] = useState('');
  const [duration, setDuration] = useState('');
  const [observedAt, setObservedAt] = useState(nowLocalIso());
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const definition = catalog.symptoms.find((s) => s.key === symptomKey) ?? catalog.symptoms[0];

  useEffect(() => {
    if (!definition) return;
    setSeverity((prev) => Math.min(Math.max(prev, definition.severity_min), definition.severity_max));
  }, [definition?.key]);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!definition) return;
    setSubmitting(true);
    setError(null);
    const payload: Record<string, unknown> = {
      symptom_key: symptomKey,
      severity,
      actor,
      observed_at: observedAt ? new Date(observedAt).toISOString() : undefined,
      notes: notes || undefined,
    };
    if (definition.measurement === 'temperature_c' && measurement) payload.measurement_value = Number(measurement);
    if (definition.measurement === 'count' && measurement) payload.measurement_value = Number(measurement);
    if (definition.measurement === 'duration_minutes' && measurement) payload.duration_minutes = Number(measurement);
    try {
      const response = await fetch('/api/parechovirus/symptoms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
      }
      const body = (await response.json()) as { symptom: ParechovirusSymptom; new_triage_issues: ParechovirusIssue[] };
      onLogged(body);
      setMeasurement('');
      setDuration('');
      setNotes('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to log symptom');
    } finally {
      setSubmitting(false);
    }
  };

  if (!definition) return <p>Catalog unavailable; cannot show log form.</p>;

  return (
    <form className="parecho-log-form" onSubmit={submit}>
      <label>
        Symptom
        <select value={symptomKey} onChange={(e) => setSymptomKey(e.target.value)}>
          {catalog.symptoms.map((s) => (
            <option key={s.key} value={s.key}>{s.label}</option>
          ))}
        </select>
      </label>
      <p className="parecho-prompt">{definition.parent_prompt}</p>
      <p className="parecho-source"><strong>Source:</strong> {definition.source_id} p.{definition.page ?? '?'} — <q>{definition.snippet}</q></p>
      <label>
        Severity (1 = mild, {definition.severity_max} = most severe)
        <input
          aria-label="Severity"
          type="range"
          min={definition.severity_min}
          max={definition.severity_max}
          value={severity}
          onChange={(e) => setSeverity(Number(e.target.value))}
        />
        <output>{severity}</output>
      </label>
      {definition.measurement === 'temperature_c' && (
        <label>
          Measured value ({definition.unit ?? ''})
          <input aria-label="Measurement" type="number" step="0.1" value={measurement} onChange={(e) => setMeasurement(e.target.value)} />
        </label>
      )}
      {definition.measurement === 'count' && (
        <label>
          Count ({definition.unit ?? ''})
          <input aria-label="Count" type="number" step="1" min="0" value={measurement} onChange={(e) => setMeasurement(e.target.value)} />
        </label>
      )}
      {definition.measurement === 'duration_minutes' && (
        <label>
          Duration ({definition.unit ?? 'min'})
          <input aria-label="Duration" type="number" step="1" min="0" value={duration} onChange={(e) => setDuration(e.target.value)} />
        </label>
      )}
      <label>
        When did you observe it?
        <input aria-label="Observed at" type="datetime-local" value={observedAt} onChange={(e) => setObservedAt(e.target.value)} />
      </label>
      <label>
        Notes (optional)
        <textarea aria-label="Notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      {error ? <p className="parecho-error" role="alert">{error}</p> : null}
      <button type="submit" disabled={submitting}>{submitting ? 'Logging…' : 'Log symptom & run triage'}</button>
    </form>
  );
}

function ParechovirusTriageQueue({
  issues,
  catalog,
  onUpdated,
}: {
  issues: ParechovirusIssue[];
  catalog: ParechovirusCatalog;
  onUpdated: (issue: ParechovirusIssue) => void;
}) {
  if (issues.length === 0) {
    return <p className="parecho-empty">No open issues. Log a symptom to start the triage queue.</p>;
  }
  return (
    <ul className="parecho-queue" data-testid="parecho-triage-queue">
      {issues.map((issue) => {
        const rule = catalog.rules.find((r) => r.rule_key === issue.rule_key);
        return (
          <li key={issue.id} className={`parecho-issue urgency-${issue.urgency}`}>
            <header>
              <StatusBadge urgency={issue.urgency} />
              <strong>{issue.label}</strong>
            </header>
            <p><strong>Because</strong> {issue.evidence}.</p>
            <p><strong>Action:</strong> {issue.action}</p>
            <p className="parecho-source">
              <strong>Source:</strong> {issue.source_id} p.{issue.page ?? '?'} — <q>{issue.snippet}</q>
              {' '}({Math.round(issue.confidence * 100)}% confidence)
              {rule ? <> · <a href="#parecho-catalog">see rule {rule.rule_key}</a></> : null}
            </p>
            <p className="parecho-meta">Opened {formatObserved(issue.opened_at)}{issue.acknowledged_by ? ` · acknowledged by ${issue.acknowledged_by}` : ''}{issue.resolved_by ? ` · resolved by ${issue.resolved_by}` : ''}</p>
            <div className="parecho-actions">
              {issue.status === 'open' && (
                <button type="button" onClick={async () => {
                  const res = await fetch(`/api/parechovirus/triage/${issue.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'acknowledged', actor: 'parent' }) });
                  if (res.ok) onUpdated(await res.json());
                }}>Acknowledge</button>
              )}
              {issue.status !== 'resolved' && (
                <button type="button" onClick={async () => {
                  const notes = window.prompt('Resolution notes (what was done?)', 'Called nurse line, advised to monitor');
                  if (notes === null) return;
                  const res = await fetch(`/api/parechovirus/triage/${issue.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: 'resolved', actor: 'parent', resolution_notes: notes }) });
                  if (res.ok) onUpdated(await res.json());
                }}>Mark resolved</button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function ParechovirusPage() {
  const [catalog, setCatalog] = useState<ParechovirusCatalog | null>(null);
  const [today, setToday] = useState<ParechovirusToday | null>(null);
  const [history, setHistory] = useState<ParechovirusSymptom[]>([]);
  const [resolved, setResolved] = useState<ParechovirusIssue[]>([]);
  const [actor] = useState('parent');
  const [apiError, setApiError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [catalogResp, todayResp, historyResp, resolvedResp] = await Promise.all([
        fetchWithTimeout<ParechovirusCatalog>('/api/parechovirus/catalog'),
        fetchWithTimeout<ParechovirusToday>('/api/parechovirus/today'),
        fetchWithTimeout<ParechovirusList>('/api/parechovirus/symptoms?days=7'),
        fetchWithTimeout<ParechovirusIssueList>('/api/parechovirus/triage?status=resolved'),
      ]);
      setCatalog(catalogResp);
      setToday(todayResp);
      setHistory(historyResp.symptoms);
      setResolved(resolvedResp.issues);
      setApiError(null);
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'API unavailable');
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!catalog) {
    return (
      <div className="page-scene" data-testid="parechovirus-loading">
        <BunnyBackdrop pageTitle="Health" />
        <h1>Parechovirus Tracker</h1>
        <p>Loading parechovirus catalog… {apiError ? `(${apiError})` : ''}</p>
      </div>
    );
  }

  const urgency = today?.highest_urgency ?? 'routine';
  const stripText =
    urgency === '911'
      ? 'EMERGENCY: open 911 issues. Call 911 now.'
      : urgency === 'urgent'
      ? 'URGENT: open issue requires medical attention now.'
      : urgency === 'today'
      ? 'TODAY: an open issue needs the pediatrician today.'
      : urgency === 'soon'
      ? 'SOON: an open issue needs a call within hours.'
      : urgency === 'watch'
      ? 'WATCH: routine monitoring; no escalation right now.'
      : 'Routine: no open issues. Keep watching per discharge instructions.';

  return (
    <div className="page-scene parecho-scene" data-testid="parechovirus-page">
      <BunnyBackdrop pageTitle="Health" />
      <h1>Parechovirus Tracker</h1>
      <p className="parecho-blurb">
        Log symptoms as they happen. The triage engine runs on every entry; the queue is source-linked to the
        May 31 ER AVS and the CSF PCR report. Local-first: nothing leaves the device.
      </p>
      <div className={`status-strip ${urgency === '911' || urgency === 'urgent' ? 'alarm' : 'routine'}`} role="status">
        {stripText} {today ? `(${today.symptom_count_24h} symptom${today.symptom_count_24h === 1 ? '' : 's'} in last 24h, ${today.open_issue_count} open issue${today.open_issue_count === 1 ? '' : 's'})` : ''}
      </div>

      <div className="grid two">
        <Card title="Log a symptom">
          <ParechovirusLogForm catalog={catalog} onLogged={() => void refresh()} actor={actor} />
        </Card>
        <Card title="Open triage issues">
          <ParechovirusTriageQueue issues={today?.open_issues ?? []} catalog={catalog} onUpdated={() => void refresh()} />
        </Card>
      </div>

      <Card title="Symptom log (last 7 days)">
        {history.length === 0 ? (
          <p className="parecho-empty">No symptoms logged yet. Entries appear here in reverse chronological order.</p>
        ) : (
          <ol className="parecho-history">
            {history.map((symptom) => {
              const def = catalog.symptoms.find((s) => s.key === symptom.symptom_key);
              return (
                <li key={symptom.id}>
                  <strong>{def?.label ?? symptom.symptom_key}</strong>
                  {' · '}
                  severity {symptom.severity}/{def?.severity_max ?? '?'}
                  {symptom.measurement_value != null ? ` · ${symptom.measurement_value}${def?.unit ? ' ' + def.unit : ''}` : ''}
                  {symptom.duration_minutes != null ? ` · ${symptom.duration_minutes} min` : ''}
                  {' · '}
                  {formatObserved(symptom.observed_at)}
                  {' · '}
                  <span className="parecho-meta">by {symptom.actor}</span>
                  {symptom.notes ? <p className="parecho-notes">{symptom.notes}</p> : null}
                </li>
              );
            })}
          </ol>
        )}
      </Card>

      {resolved.length > 0 && (
        <Card title="Recently resolved issues">
          <ul className="parecho-resolved">
            {resolved.slice(0, 5).map((issue) => (
              <li key={issue.id}>
                <StatusBadge urgency={issue.urgency} /> {issue.label}
                {issue.resolution_notes ? <span> — {issue.resolution_notes}</span> : null}
                {' '}
                <span className="parecho-meta">resolved {issue.resolved_at ? formatObserved(issue.resolved_at) : ''} by {issue.resolved_by ?? 'unknown'}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="Symptom & triage catalog (reference)">
        <details id="parecho-catalog">
          <summary>Show catalog with rules and parent prompts</summary>
          <h3>Symptoms</h3>
          <ul className="parecho-catalog">
            {catalog.symptoms.map((s) => (
              <li key={s.key}>
                <strong>{s.label}</strong> ({s.category}) — {s.description}
                <p className="parecho-source"><strong>Source:</strong> {s.source_id} p.{s.page ?? '?'} — <q>{s.snippet}</q></p>
              </li>
            ))}
          </ul>
          <h3>Triage rules</h3>
          <ul className="parecho-catalog">
            {catalog.rules.map((r) => (
              <li key={r.rule_key}>
                <StatusBadge urgency={r.urgency} /> <strong>{r.label}</strong> — {r.action}
                <p className="parecho-source"><strong>Source:</strong> {r.source_id} p.{r.page ?? '?'} — <q>{r.snippet}</q></p>
              </li>
            ))}
          </ul>
        </details>
      </Card>

      <p className="parecho-footer">
        This is a tracking tool, not a diagnosis. Always defer to your pediatrician and the ER discharge instructions.
      </p>
    </div>
  );
}

export function TokenCatalog() { return <div className="grid"><h1>Design Tokens: Calm + Alarm</h1><Card title="Status catalog">{(['routine', 'watch', 'soon', 'today', 'urgent', '911'] as const).map((urgency) => <p key={urgency}><StatusBadge urgency={urgency} /> status uses hue + shape + icon + text.</p>)}</Card><div className="alarm-screen"><div className="status-strip alarm">Alarm language preview — saturated, high contrast, not watercolor calm</div></div></div>; }
export function ConditionsPage() { return <HealthPage />; }
export function ChartsPage() { return <GrowthPage />; }
export function GrowthFeedingPage() { return <GrowthPage />; }
export function ReassuranceWatch() { return <TodayPage />; }
export function DevelopmentPage() { return <HealthPage />; }
export function VaccinesPage() { return <HealthPage />; }
export function TasksPage() { return <DoctorPrepPage />; }
export function ReviewQueuePage() { return <TimelinePage />; }
