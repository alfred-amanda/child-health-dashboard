
import { useEffect, useState } from 'react';
import { BilirubinChart, Card, ChartFrame, Recommendation, StatusBadge } from './components';
import { alarmRecommendation, bilirubinCurve, bilirubinPoints, conditions, doctorQuestions, redFlagRules, routineRecommendation } from './data';
import type { RecommendationPayload } from './types';

type TodayApiPayload = {
  child: string;
  status: 'routine' | 'alarm';
  status_strip: string;
  primary_recommendation: RecommendationPayload;
  reassurance_first: { label: string; source: string }[];
  watching: string[];
  red_flags: { key: string; label: string; source?: { source_id?: string; page?: number } | string }[];
};

export function TokenCatalog() {
  return <div className="grid"><h1>Design tokens: calm + alarm</h1><Card title="Status catalog">{(['routine', 'watch', 'soon', 'today', 'urgent', '911'] as const).map((urgency) => <p key={urgency}><StatusBadge urgency={urgency} /> status uses hue + shape + icon + text.</p>)}</Card><div className="alarm-screen"><div className="status-strip alarm">Alarm language preview — saturated, high contrast, not watercolor calm</div><Recommendation payload={alarmRecommendation} /></div></div>;
}

export function TodayPage({ alarm = false }: { alarm?: boolean }) {
  const [apiPayload, setApiPayload] = useState<TodayApiPayload | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/today${alarm ? '?alarm=true' : ''}`)
      .then((response) => {
        if (!response.ok) throw new Error(`API returned ${response.status}`);
        return response.json() as Promise<TodayApiPayload>;
      })
      .then((payload) => { if (!cancelled) setApiPayload(payload); })
      .catch((error: unknown) => { if (!cancelled) setApiError(error instanceof Error ? error.message : 'Unknown API error'); });
    return () => { cancelled = true; };
  }, [alarm]);
  const recommendation = apiPayload?.primary_recommendation ?? (alarm ? alarmRecommendation : routineRecommendation);
  const isAlarm = apiPayload?.status === 'alarm' || alarm;
  const redFlags = apiPayload?.red_flags ?? redFlagRules;
  const redFlagSource = (rule: TodayApiPayload['red_flags'][number] | typeof redFlagRules[number]) => typeof rule.source === 'string' ? rule.source : rule.source?.source_id ? `${rule.source.source_id} p.${rule.source.page ?? '?'}` : 'source attached';
  const shell = <><div className="api-status" aria-live="polite">{apiPayload ? `Live API data loaded for ${apiPayload.child}` : apiError ? `API fallback: ${apiError}` : 'Loading live API data…'}</div><div className={`status-strip ${isAlarm ? 'alarm' : 'routine'}`}>{apiPayload?.status_strip ?? (isAlarm ? 'URGENT RED FLAG ACTIVE — source-driven threshold crossed' : 'Routine watch — reassuring signs first, red flags one tap away')}</div><div className="grid two"><Card title="Current watch"><p><strong>What is going well:</strong> {apiPayload?.reassurance_first.map((item) => item.label).join('; ') ?? 'feeding improved during hospital stay; low CRP/procalcitonin; clinically improved at discharge'}.</p><p><strong>What we are watching:</strong> {apiPayload?.watching.join('; ') ?? 'jaundice/DAT-positive hemolysis risk, culture-final confirmation, Hep B catch-up'}.</p></Card><Card title="Single next action"><Recommendation payload={recommendation} /></Card><Card title="Red flags"><ul>{redFlags.map((rule) => <li key={rule.key}><strong>{rule.label}</strong> — {redFlagSource(rule)}</li>)}</ul></Card><Card title="What changed"><p>Parechovirus detected; fever resolved; discharge instructions drive urgent thresholds.</p></Card></div></>;
  return isAlarm ? <div className="alarm-screen" data-testid="today-alarm">{shell}</div> : <div data-testid="today-calm">{shell}</div>;
}

export function ReassuranceWatch() {
  return <div className="grid"><h1>Reassurance & Watch</h1><Card title="What is going well"><ul><li>CSF had 1 WBC/uL — source structured profile key results.</li><li>CRP &lt;0.3 and procalcitonin 0.16 — source structured profile.</li><li>Clinically improved at discharge — source SRC-003 p.1.</li></ul></Card><Card title="What we are watching"><ul><li>DAT-positive bilirubin/anemia context.</li><li>Hep B catch-up.</li><li>Culture-final confirmation.</li></ul></Card><Card title="What needs action"><Recommendation payload={routineRecommendation} /></Card></div>;
}

export function TimelinePage() {
  return <div className="grid"><h1>Timeline</h1><Card title="Birth → discharge"><ol><li>2026-05-17 birth/newborn: DAT-positive ABO incompatibility watch. <button>Ask doctor</button> <button>Mark reviewed</button></li><li>2026-05-21 office visit: bilirubin/weight check.</li><li>2026-05-29 fever admission.</li><li>2026-05-31 discharge with source-driven red flags.</li></ol><p>Filters: date, category, concern, source, reviewed.</p></Card></div>;
}

export function ConditionsPage() {
  return <div className="grid"><h1>Conditions</h1>{conditions.map((condition) => <Card key={condition} title={condition}><p>Status/severity, evidence, trends, watch items, questions, next action, and source disclosure are attached.</p><button>Add to doctor questions</button></Card>)}</div>;
}

export function ChartsPage() {
  return <div className="grid"><h1>Charts</h1><BilirubinChart points={bilirubinPoints} curve={bilirubinCurve} /><ChartFrame title="Growth WHO 0–24 months" interpretation="Newborn weight loss/regain leads; projected range suppressed when sparse." source="WHO Child Growth Standards local note" action="Ask about next weigh-in"><p>WHO curve placeholder with birthweight recovery metrics.</p></ChartFrame><ChartFrame title="CBC / anemia" interpretation="Neonatal reference bands vary by age at measurement and DAT-positive context is shown." source="Local neonatal reference-band table"><p>Hemoglobin, hematocrit, RBC, retic plotted with age bands.</p></ChartFrame><ChartFrame title="Infection markers" interpretation="Low CRP/procalcitonin and culture status shown explicitly." source="SRC-019/SRC-030/SRC-008"><p>Culture-final status: confirm at visit.</p></ChartFrame><ChartFrame title="Temperature events" interpretation="Discrete fever events use discharge threshold source, not a generic constant." source="SRC-003 p.2"><p>Fever threshold from AVS: 39 C call pediatrician; multiple &gt;38 C/24h call pediatrician.</p></ChartFrame><ChartFrame title="Hydration / feeding" interpretation="Parent-entered wet diapers trigger source-driven urgent rule." source="SRC-003 p.2"><p>&lt;4 wet diapers/24h links to urgent recommendation.</p></ChartFrame></div>;
}

export function GrowthFeedingPage() {
  return <div className="grid"><h1>Growth & Feeding</h1><Card title="One-tap quick add"><div className="quick-add"><button>+ Feed</button><button>+ Wet diaper</button><button>+ Stool</button><button>+ Weight</button></div></Card><Card title="Safe empty state"><p>No fake trends: if there are too few points, charts render points only with no projection.</p></Card></div>;
}

export function DevelopmentPage() {
  return <div className="grid"><h1>Development + enhanced post-parechovirus watch</h1><Card title="Monthly year-1 check-ins"><p>Track tone, symmetry, feeding, alertness, seizure-like activity, and regression at well visits.</p><ul><li>Seizure-like unsuppressible shaking → 911 per SRC-003 p.2.</li><li>Regression → call pediatrician today.</li><li>Poor feeding + lethargy → urgent care/ED per discharge.</li><li>Asymmetry/tone concern → ask pediatrician.</li></ul></Card></div>;
}

export function VaccinesPage() {
  return <div className="grid"><h1>Vaccines & Prevention</h1><Card title="Hep B"><p>Status: deferred. Reason: deferred by family in newborn records. Catch-up prompt: ask pediatrician for schedule.</p><p>Statuses supported: due / upcoming / given / deferred / overdue.</p></Card></div>;
}

export function TasksPage() {
  return <div className="grid"><h1>Tasks, alerts, predictions</h1><Card title="Unified tasks"><ul><li>PCP follow-up after fever admission — source SRC-003.</li><li>Ask for Hep B catch-up plan — source newborn record.</li><li>Confirm cultures final — source culture notes.</li></ul><button>Resolve selected task</button></Card><Card title="Alerts"><p>Passive dashboard, active dummy local channel, urgent full-screen alarm language. No alert fires without source.</p></Card><Card title="Predictions"><p>Bounded and confidence-labeled. Insufficient data says “not computable from available records.” No copy says to defer care.</p></Card></div>;
}

export function DoctorPrepPage() {
  const [mode, setMode] = useState<'parent' | 'clinician'>('parent');
  const rec: RecommendationPayload = mode === 'parent' ? routineRecommendation : { ...routineRecommendation, action: 'review raw values, units, reference ranges, encounter dates, and source snippets before the visit' };
  return <div className="grid"><h1>Doctor Prep</h1><div className="mode-toggle"><button aria-pressed={mode === 'parent'} onClick={() => setMode('parent')}>Parent mode</button><button aria-pressed={mode === 'clinician'} onClick={() => setMode('clinician')}>Clinician mode</button></div><Card title="10 questions"><ol>{doctorQuestions.map((question) => <li key={question}>{question}</li>)}</ol></Card><Recommendation payload={rec} />{mode === 'clinician' ? <Card title="Clinician details"><p>Raw values, units, reference ranges, encounter dates, source, confidence, and snippets are exposed here.</p></Card> : <Card title="Parent summary"><p>Plain-language summary; raw source hidden behind disclosure controls.</p></Card>}</div>;
}

export function ReviewQueuePage() {
  return <div className="grid"><h1>Review Queue</h1><Card title="Fact review"><p>Fact + source snippet + confidence + category. Actions: accept, edit, reject, doctor-confirm. No accepted fact bypasses reviewer/timestamp.</p><button>Accept with actor/timestamp</button><button>Reject with reason</button></Card></div>;
}
