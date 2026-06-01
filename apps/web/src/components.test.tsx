
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BilirubinChart, ChartFrame, ProvenanceDisclosure, Recommendation, StatusBadge } from './components';
import { bilirubinCurve, bilirubinPoints, routineRecommendation } from './data';
import { DoctorPrepPage, TodayPage, TokenCatalog } from './pages';


describe('core component library', () => {
  it('renders Recommendation in A5 shape for every urgency', () => {
    for (const urgency of ['routine', 'soon', 'today', 'urgent', '911'] as const) {
      render(<Recommendation payload={{ ...routineRecommendation, urgency }} />);
      expect(screen.getByText(/Because/i)).toBeInTheDocument();
      expect(document.body).toHaveTextContent(new RegExp(`Urgency:\\s*${urgency}`));
      cleanup();
    }
  });

  it('progressively discloses provenance', () => {
    render(<ProvenanceDisclosure source={routineRecommendation.source} />);
    expect(screen.queryByText(/continued to feed well/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /show source/i }));
    expect(screen.getByText(/continued to feed well/)).toBeInTheDocument();
  });

  it('status badges use text, icon, and shape not color alone', () => {
    render(<StatusBadge urgency="urgent" />);
    expect(screen.getByLabelText(/Urgent status/)).toHaveTextContent('◆');
    expect(screen.getByLabelText(/Urgent status/)).toHaveTextContent('!!');
  });

  it('ChartFrame enforces interpretation, chart, source, and action', () => {
    render(<ChartFrame title="Test chart" interpretation="interpret first" source="SRC-1" action="Ask doctor"><p>chart middle</p></ChartFrame>);
    expect(screen.getByText(/Interpretation:/)).toBeInTheDocument();
    expect(screen.getByText(/chart middle/)).toBeInTheDocument();
    expect(screen.getByText(/Source:/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /ask doctor/i })).toBeInTheDocument();
  });

  it('bilirubin chart uses a non-flat risk curve inside ChartFrame', () => {
    render(<BilirubinChart points={bilirubinPoints} curve={bilirubinCurve} />);
    expect(screen.getByText(/DAT-positive/)).toBeInTheDocument();
    expect(new Set(bilirubinCurve.map((point) => point.threshold_mg_dl)).size).toBeGreaterThan(5);
  });
});

describe('pages and safety UX', () => {
  it('token catalog renders calm and visibly distinct alarm preview', () => {
    render(<TokenCatalog />);
    expect(screen.getByText(/Alarm language preview/)).toBeInTheDocument();
    expect(screen.getByText(/saturated, high contrast/)).toBeInTheDocument();
  });

  it('today page shows status above fold and switches to alarm language', () => {
    render(<TodayPage alarm />);
    expect(screen.getByTestId('today-alarm')).toHaveClass('alarm-screen');
    expect(screen.getByText(/URGENT RED FLAG ACTIVE/)).toBeInTheDocument();
    expect(screen.getByText(/Less than 4 wet diapers/)).toBeInTheDocument();
  });

  it('doctor prep has parent/clinician mode over same questions', () => {
    render(<DoctorPrepPage />);
    expect(screen.getAllByRole('listitem')).toHaveLength(10);
    fireEvent.click(screen.getByRole('button', { name: /clinician mode/i }));
    expect(screen.getByText(/Raw values, units, reference ranges/)).toBeInTheDocument();
  });
});
