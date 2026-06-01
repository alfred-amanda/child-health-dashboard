
import { useState } from 'react';
import type { PropsWithChildren } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, XAxis, YAxis } from 'recharts';
import { tokens } from './tokens';
import type { ChartPoint, RecommendationPayload, Urgency } from './types';

export function Card({ title, children }: PropsWithChildren<{ title?: string }>) {
  return <section className="card">{title ? <h2>{title}</h2> : null}{children}</section>;
}

export function StatusBadge({ urgency }: { urgency: Urgency }) {
  const key = urgency === 'soon' || urgency === 'today' ? 'action' : urgency === '911' ? '911' : urgency;
  const status = tokens.statuses[key as keyof typeof tokens.statuses];
  return <span className="badge" style={{ backgroundColor: status.background, color: status.text }} aria-label={`${status.label} status ${status.shape} ${status.icon}`}><span aria-hidden="true">{status.shape}</span><span>{status.icon}</span><span>{status.label}</span></span>;
}

export function ProvenanceDisclosure({ source }: { source: RecommendationPayload['source'] }) {
  const [open, setOpen] = useState(false);
  return <div className="provenance"><button type="button" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? 'Hide source' : 'Show source'}</button>{open ? <div role="note"><strong>{source.source_id}</strong> p.{source.page ?? '?'} — confidence {Math.round(source.confidence * 100)}%<br /><q>{source.snippet}</q></div> : null}</div>;
}

export function Recommendation({ payload }: { payload: RecommendationPayload }) {
  const urgentClass = payload.urgency === '911' ? 'nine-one-one' : payload.urgency;
  return <article className={`card rec ${urgentClass}`}><StatusBadge urgency={payload.urgency} /><p><strong>Because</strong> {payload.evidence}, {payload.action}.</p><p><strong>Urgency:</strong> {payload.urgency}. <strong>Confidence:</strong> {payload.confidence}. <strong>Source:</strong> {payload.source.source_id} p.{payload.source.page ?? '?'}</p><ProvenanceDisclosure source={payload.source} /></article>;
}

export function ChartFrame({ title, interpretation, source, action, children }: PropsWithChildren<{ title: string; interpretation: string; source: string; action?: string }>) {
  return <section className="card" data-chart-frame="true"><h2>{title}</h2><p><strong>Interpretation:</strong> {interpretation}</p><div aria-label={`${title} chart`}>{children}</div><p><strong>Source:</strong> {source}</p>{action ? <button type="button">{action}</button> : null}</section>;
}

export function BilirubinChart({ points, curve }: { points: ChartPoint[]; curve: { hour: number; threshold_mg_dl: number }[] }) {
  return <ChartFrame title="Bilirubin AAP-2022 risk curve" interpretation="DAT-positive/hemolytic risk factor applied. Under-claim safety when data are uncertain." source="Local AAP-2022 threshold table mirrored from PediTools/AAP guideline" action="Ask pediatrician if repeat bilirubin is needed"><ResponsiveContainer width="100%" height={260}><LineChart data={curve} margin={{ top: 20, right: 30, left: 0, bottom: 10 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="hour" label={{ value: 'hours of life', position: 'insideBottom', offset: -5 }} /><YAxis label={{ value: 'mg/dL', angle: -90, position: 'insideLeft' }} /><Line type="monotone" dataKey="threshold_mg_dl" stroke="#7f0000" strokeWidth={3} dot={false} name="AAP threshold with risk factors" /><ReferenceLine y={0} stroke="#1f2937" /></LineChart></ResponsiveContainer><ResponsiveContainer width="100%" height={180}><ScatterChart><CartesianGrid /><XAxis dataKey="hour" type="number" name="hour" /><YAxis dataKey="value" type="number" name="bilirubin" /><Scatter data={points} fill="#173b8e" /></ScatterChart></ResponsiveContainer></ChartFrame>;
}
