
import type { ChartPoint, RecommendationPayload } from './types';

export const redFlagRules = [
  { key: 'wet_diapers_24h', label: 'Less than 4 wet diapers in 24 hours', source: 'SRC-003 p.2', urgency: 'urgent' },
  { key: 'difficulty_feeding', label: 'Difficulty feeding', source: 'SRC-003 p.2', urgency: 'urgent' },
  { key: 'difficulty_breathing', label: 'Difficulty breathing', source: 'SRC-003 p.2', urgency: 'urgent' },
  { key: 'increasing_jaundice', label: 'Increasing jaundice', source: 'SRC-003 p.2', urgency: 'urgent' },
  { key: 'lethargy', label: 'Lethargy / decreased activity', source: 'SRC-003 p.2', urgency: 'urgent' },
  { key: 'seizure', label: 'Unsuppressible extremity shaking', source: 'SRC-003 p.2', urgency: '911' }
] as const;

export const routineRecommendation: RecommendationPayload = {
  evidence: 'Thomas continued to feed well during the admission, CRP/procalcitonin were low, and fever resolved by discharge',
  action: 'watch feeding, wet diapers, temperature, and keep the discharge red-flag reference one tap away',
  urgency: 'routine',
  confidence: 'moderate',
  source: { source_id: 'SRC-003', title: 'ER AVS May 31 2026', page: 1, snippet: 'continued to feed well throughout his hospital stay', confidence: 0.95 }
};

export const alarmRecommendation: RecommendationPayload = {
  evidence: 'wet diapers are below the discharge threshold of 4 in 24 hours',
  action: 'seek medical attention from the pediatrician, urgent care, or emergency department now',
  urgency: 'urgent',
  confidence: 'high',
  source: { source_id: 'SRC-003', title: 'ER AVS May 31 2026', page: 2, snippet: 'Less than 4 wet diapers in 24 hours', confidence: 0.99 }
};

export const bilirubinPoints: ChartPoint[] = [
  { hour: 12, value: 3.7, threshold_mg_dl: 8.5 },
  { hour: 25, value: 5.8, threshold_mg_dl: 10.67 },
  { hour: 100, value: 11.1, threshold_mg_dl: 18.2 },
  { hour: 288, value: 9.5 }
];

export const bilirubinCurve = [
  { hour: 12, threshold_mg_dl: 8.5 },
  { hour: 18, threshold_mg_dl: 9.5 },
  { hour: 24, threshold_mg_dl: 10.5 },
  { hour: 30, threshold_mg_dl: 11.5 },
  { hour: 36, threshold_mg_dl: 12.4 },
  { hour: 42, threshold_mg_dl: 13.2 },
  { hour: 48, threshold_mg_dl: 14.0 },
  { hour: 60, threshold_mg_dl: 15.4 },
  { hour: 72, threshold_mg_dl: 16.6 },
  { hour: 84, threshold_mg_dl: 17.5 },
  { hour: 96, threshold_mg_dl: 18.2 }
];

export const conditions = [
  'Parechovirus meningitis / neonatal fever admission',
  'Jaundice due to ABO isoimmunization / DAT-positive ABO incompatibility',
  'Congenital torticollis / right head preference',
  'Left pinna fold / ear deformity referral',
  'Hepatitis B vaccine deferred',
  'Feeding and hydration watch after discharge'
];

export const doctorQuestions = [
  'Confirm final blood, CSF, and urine culture status from the fever admission.',
  'What follow-up is needed after parechovirus meningitis?',
  'What fever threshold should we use now at home?',
  'Does DAT-positive ABO incompatibility require repeat bilirubin or anemia follow-up?',
  'Should CBC/anemia values be repeated?',
  'What is the Hep B catch-up plan?',
  'Is the newborn screen ACTION REQUIRED note resolved?',
  'What should we do for right head preference/torticollis?',
  'Does left pinna fold need plastics referral now?',
  'What feeding/diaper thresholds should trigger same-day contact?'
];
