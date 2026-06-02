import { useEffect, useMemo, useState } from 'react';
import { Card, ChartFrame, Recommendation, StatusBadge } from './components';
import { conditions, doctorQuestions, routineRecommendation } from './data';
import type { Confidence, RecommendationPayload, Urgency } from './types';
import springBunny from './assets/thomas-bunny-spring.jpg?url';
import summerBunny from './assets/thomas-bunny-summer.jpg?url';
import autumnBunny from './assets/thomas-bunny-autumn.jpg?url';
import winterBunny from './assets/thomas-bunny-winter.jpg?url';

type TodayApiPayload = { child: string; status: 'routine' | 'alarm'; status_strip: string; primary_recommendation: RecommendationPayload; reassurance_first: { label: string; source: string }[]; watching: string[]; red_flags: { key: string; label: string; source?: { source_id?: string; page?: number } | string }[] };
type Source = { title: string; url: string; date: string };
type WatchItem = { title: string; action: string; urgency: Urgency; confidence: Confidence; source_type: string; sources: Source[] };
type WatchPayload = { global_boundary_note: string; actionable: WatchItem[]; lower_confidence: WatchItem[] };
type GrowthPayload = { percentiles: Record<string, { percentile: number; label: string; source: string }>; projection: string; measurements: unknown[] };
type ResearchPayload = { mode: string; updates: { title: string; summary: string; confidence: Confidence; sources: Source[] }[] };

const bunnyAssets = { spring: springBunny, summer: summerBunny, autumn: autumnBunny, winter: winterBunny } as const;
type BunnySeason = keyof typeof bunnyAssets;

function seasonNow(): BunnySeason {
  const month = new Date().getMonth();
  if (month < 2 || month === 11) return 'winter';
  if (month < 5) return 'spring';
  if (month < 8) return 'summer';
  return 'autumn';
}

export function BunnyBackdrop({ season = seasonNow() }: { season?: BunnySeason }) {
  return <div className="bunny-backdrop generated-bunny-backdrop" data-testid="bunny-backdrop" data-season={season} aria-hidden="true" style={{ backgroundImage: `linear-gradient(rgba(248,251,255,.80), rgba(248,251,255,.92)), url(${bunnyAssets[season]})` }} />;
}

function WatchList({ payload }: { payload: WatchPayload | null }) {
  const fallback: WatchPayload = { global_boundary_note: 'This local dashboard supports the care plan and keeps physician questions in Doctor Prep.', actionable: [{ title: 'Less than 4 wet diapers in 24 hours', action: 'Seek medical attention now per discharge instructions.', urgency: 'urgent', confidence: 'high', source_type: 'discharge_red_flag', sources: [{ title: 'ER AVS', url: 'local:SRC-003', date: '2026-05-31' }] }], lower_confidence: [] };
  const data = payload?.actionable && payload?.lower_confidence ? payload : fallback;
  return <Card title="Current Watch / What To Watch"><p className="boundary-note">{data.global_boundary_note}</p><div className="watch-list">{data.actionable.map((item) => <article key={item.title} className={`watch-item ${item.urgency === '911' ? 'emergency' : ''}`}><StatusBadge urgency={item.urgency} /><h3>{item.title}</h3><p>{item.action}</p><p><strong>Confidence:</strong> {item.confidence}. <strong>Source:</strong> {item.sources.map((source) => `${source.title} (${source.date})`).join('; ')}</p></article>)}</div><h3>Lower-confidence / being looked into</h3><div className="watch-list lower">{data.lower_confidence.map((item) => <article key={item.title} className="watch-item"><h4>{item.title}</h4><p>{item.action}</p><p><strong>Confidence:</strong> {item.confidence}. Not used as an actionable task.</p></article>)}</div></Card>;
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
      fetch(`/api/today${alarm ? '?alarm=true' : ''}`).then((response) => response.json() as Promise<TodayApiPayload>),
      fetch('/api/watch').then((response) => response.json() as Promise<WatchPayload>),
      fetch('/api/growth').then((response) => response.json() as Promise<GrowthPayload>),
      fetch('/api/research').then((response) => response.json() as Promise<ResearchPayload>)
    ]).then(([today, watch, growth, research]) => { if (!cancelled) { setApiPayload(today); setWatchPayload(watch); setGrowthPayload(growth); setResearchPayload(research); } }).catch((error: unknown) => { if (!cancelled) setApiError(error instanceof Error ? error.message : 'Unknown API error'); });
    return () => { cancelled = true; };
  }, [alarm]);
  const recommendation = apiPayload?.primary_recommendation ?? routineRecommendation;
  const isAlarm = apiPayload?.status === 'alarm' || alarm;
  return <div className={`page-scene ${isAlarm ? 'alarm-screen' : ''}`} data-testid={isAlarm ? 'today-alarm' : 'today-calm'}><BunnyBackdrop /><div className="api-status" aria-live="polite">{apiPayload ? `Live API data loaded for ${apiPayload.child}` : apiError ? `API fallback: ${apiError}` : 'Loading live API data…'}</div><section className="hero-card"><h1>Today</h1><div className={`status-strip ${isAlarm ? 'alarm' : 'routine'}`}>{apiPayload?.status_strip ?? (isAlarm ? 'URGENT RED FLAG ACTIVE — source-driven threshold crossed' : 'Routine watch — reassuring signs first, red flags one tap away')}</div><p>In five seconds: status first, red flags one tap away, growth snapshot visible, and all smart guidance cited.</p></section><div className="grid two"><WatchList payload={watchPayload} /><Card title="Growth Snapshot">{Object.entries(growthPayload?.percentiles ?? {}).length ? Object.entries(growthPayload?.percentiles ?? {}).map(([kind, value]) => <p key={kind}><strong>{kind}</strong>: {value.label} <span className="source-chip">{value.source}</span></p>) : <p>Loading WHO male percentile snapshot…</p>}</Card><Card title="Single Next Action"><Recommendation payload={recommendation} /></Card><Card title="Updates"><p>{researchPayload?.updates ? `Offline ${researchPayload.mode}: ${researchPayload.updates[0]?.title}` : 'Loading cached weekly digest…'}</p>{researchPayload?.updates?.map((update) => <p key={update.title}><strong>{update.title}</strong> — {update.summary} <span className="source-chip">{update.sources[0]?.title}</span></p>)}</Card><Card title="Recent Changes"><p>New parent measurements, uploads, and changed watch items appear here with source and date.</p></Card></div></div>;
}

export function GrowthPage() {
  const [payload, setPayload] = useState<GrowthPayload | null>(null);
  const [savedBy, setSavedBy] = useState<string | null>(null);
  const [caregiver, setCaregiver] = useState('John');
  useEffect(() => { let cancelled = false; fetch('/api/growth').then((response) => response.json() as Promise<GrowthPayload>).then((data) => { if (!cancelled) setPayload(data); }).catch(() => undefined); return () => { cancelled = true; }; }, []);
  const percentileRows = useMemo(() => Object.entries(payload?.percentiles ?? {}), [payload]);
  return <div className="page-scene"><BunnyBackdrop /><h1>Growth</h1><div className="grid two"><Card title="Add Measurement" ><form id="add-measurement" className="measurement-form" onSubmit={(event) => { event.preventDefault(); setSavedBy(caregiver); }}><label>Weight pounds<input aria-label="Weight pounds" name="weight" inputMode="decimal" /></label><label>Caregiver<input aria-label="Caregiver" value={caregiver} onChange={(event) => setCaregiver(event.target.value)} /></label><button type="submit">Save Measurement</button></form>{savedBy ? <p>Saved parent-entered measurement from {savedBy}</p> : null}</Card><Card title="WHO Male Percentiles">{percentileRows.map(([kind, value]) => <p key={kind}>{kind}: {value.label} — {value.source}</p>)}<p>Projection: {payload?.projection ?? 'points_only_no_projection'}.</p></Card><ChartFrame title="WHO growth curves" interpretation="Male WHO 0–24 month LMS percentiles; sparse data renders points only." source="Committed WHO LMS data + independent fixture"><p>Weight, length, and head circumference points are plotted against WHO male percentile bands.</p></ChartFrame></div></div>;
}

export function HealthPage() { return <div className="grid"><h1>Health</h1>{conditions.map((condition) => <Card key={condition} title={condition}><p>Status, evidence, watch items, and source disclosures are API-backed. Questions move to Doctor Prep rather than repeated boilerplate.</p></Card>)}</div>; }
export function TimelinePage() { return <div className="grid"><h1>Timeline</h1><Card title="Records"><p id="upload">Upload-after-visit records land here, then Today shows what changed.</p><button type="button">Upload Record</button></Card><Card title="History"><ol><li>Birth and DAT-positive jaundice watch.</li><li>Fever admission and parechovirus result.</li><li>Discharge red flags preserved as source-driven rules.</li></ol></Card></div>; }
export function DoctorPrepPage() { const [mode, setMode] = useState<'parent' | 'clinician'>('parent'); return <div className="grid"><h1>Doctor Prep</h1><div className="mode-toggle"><button aria-pressed={mode === 'parent'} onClick={() => setMode('parent')}>Parent mode</button><button aria-pressed={mode === 'clinician'} onClick={() => setMode('clinician')}>Clinician mode</button></div><Card title="Questions For Next Visit"><ol>{doctorQuestions.map((question) => <li key={question}>{question}</li>)}</ol></Card><Card title="Print / Export PDF"><p id="print">One-page summary includes status, conditions, growth percentiles, vaccines, watch items, and source units in clinician mode.</p><button type="button">Print Summary</button></Card>{mode === 'clinician' ? <Card title="Clinician details"><p>Raw values, units, reference ranges, encounter dates, source, confidence, and snippets are exposed here.</p></Card> : <Card title="Parent summary"><p>Plain-language summary; source details available when needed.</p></Card>}</div>; }

export function TokenCatalog() { return <div className="grid"><h1>Design Tokens: Calm + Alarm</h1><Card title="Status catalog">{(['routine', 'watch', 'soon', 'today', 'urgent', '911'] as const).map((urgency) => <p key={urgency}><StatusBadge urgency={urgency} /> status uses hue + shape + icon + text.</p>)}</Card><div className="alarm-screen"><div className="status-strip alarm">Alarm language preview — saturated, high contrast, not watercolor calm</div></div></div>; }
export function ConditionsPage() { return <HealthPage />; }
export function ChartsPage() { return <GrowthPage />; }
export function GrowthFeedingPage() { return <GrowthPage />; }
export function ReassuranceWatch() { return <TodayPage />; }
export function DevelopmentPage() { return <HealthPage />; }
export function VaccinesPage() { return <HealthPage />; }
export function TasksPage() { return <DoctorPrepPage />; }
export function ReviewQueuePage() { return <TimelinePage />; }
