# Child Health Dashboard ER diagram

```mermaid
erDiagram
  Child ||--o{ SourceDocument : owns
  Child ||--o{ ExtractedFact : has
  Child ||--o{ Encounter : has
  Child ||--o{ Measurement : has
  Child ||--o{ LabResult : has
  Child ||--o{ Condition : has
  Child ||--o{ RiskSignal : has
  Child ||--o{ Task : has
  Child ||--o{ ParentObservation : logs
  Child ||--o{ VaccineEvent : has
  Child ||--o{ DevelopmentMilestone : tracks
  SourceDocument ||--o{ ExtractedFact : proves
  SourceDocument ||--o{ RiskSignal : cites
```

Model invariant: accepted/doctor-confirmed facts require source document, page, snippet, confidence, reviewer actor, and review timestamp. Facts-vs-interpretation is encoded by `fact_type`.
