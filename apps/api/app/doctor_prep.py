
from __future__ import annotations

from pathlib import Path

THOMAS_QUESTIONS = [
    'Confirm final blood, CSF, and urine culture status from the fever admission.',
    'What follow-up is needed after parechovirus meningitis? Any neurology/development monitoring changes?',
    'What fever threshold should we use now at home, and when should we call vs go to urgent care/ER?',
    'Does DAT-positive ABO incompatibility require any repeat bilirubin or anemia follow-up?',
    'Should CBC/anemia values be repeated because of DAT-positive/hemolysis risk?',
    'What is the Hep B catch-up plan after newborn deferral?',
    'Is the newborn screen ACTION REQUIRED note fully resolved, and do we need documentation?',
    'What should we do for right head preference/torticollis: stretches, PT timing, red flags?',
    'Does left pinna fold need plastics referral now, and what timing matters?',
    'What feeding/diaper thresholds should trigger same-day contact for Thomas specifically?',
]


def generate_markdown(report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    body = '# Thomas Chen — Next Visit Doctor Prep\n\n'
    body += 'Medical boundary: this organizes records; Thomas’s pediatrician decides care.\n\n'
    body += '## Clinician summary\n\nTerm infant, DAT-positive ABO incompatibility/jaundice watch, recent parechovirus meningitis/neonatal fever admission, clinically improved at discharge.\n\n'
    body += '## New data since last visit\n\n- Fever admission 2026-05-29 to 2026-05-31; parechovirus detected; CRP/procalcitonin low; cultures need final confirmation.\n- Bilirubin values remain source-linked and interpreted against AAP-2022 with hemolytic risk factor.\n\n'
    body += '## Open questions\n\n'
    for idx, question in enumerate(THOMAS_QUESTIONS, start=1):
        body += f'{idx}. {question}\n'
    body += '\n## Meds/allergies\n\nNo active allergies in AVS; no discharge medication changes. Source: SRC-003 p.1.\n\n'
    body += '## Vaccine status\n\nHep B deferred; needs catch-up plan. Source: structured profile + newborn AVS.\n\n'
    body += '## Growth summary\n\nBirth weight 3.59 kg; later weights above birthweight but inpatient values vary. Use WHO 0–24 month standard and pediatrician trend.\n\n'
    body += '## Abnormal/watch labs\n\nBilirubin, CBC/anemia markers, culture status — all values require source disclosure in the app.\n'
    path = report_dir / 'thomas-next-visit.md'
    path.write_text(body)
    return path


def generate_minimal_pdf(report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    text = 'Thomas Chen Doctor Prep - see Markdown packet for full source-linked questions.'
    stream = f'BT /F1 12 Tf 72 720 Td ({text}) Tj ET'
    pdf = (
        '%PDF-1.4\n'
        '1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n'
        '2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n'
        '3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n'
        f'4 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n'
        '5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n'
        'xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000274 00000 n \n0000000380 00000 n \n'
        'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n'
    )
    path = report_dir / 'thomas-next-visit.pdf'
    path.write_bytes(pdf.encode('latin-1'))
    return path
