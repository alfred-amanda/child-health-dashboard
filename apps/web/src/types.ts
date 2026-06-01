
export type Urgency = 'routine' | 'watch' | 'soon' | 'today' | 'urgent' | '911';
export type Confidence = 'low' | 'moderate' | 'high';

export interface SourceRef {
  source_id: string;
  title: string;
  page?: number | null;
  snippet: string;
  confidence: number;
}

export interface RecommendationPayload {
  evidence: string;
  action: string;
  urgency: Urgency;
  confidence: Confidence;
  source: SourceRef;
}

export interface ChartPoint {
  hour?: number;
  date?: string;
  value: number;
  threshold_mg_dl?: number;
}
