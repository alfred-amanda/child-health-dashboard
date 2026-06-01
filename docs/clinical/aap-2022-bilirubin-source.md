# AAP 2022 bilirubin threshold source

The app carries a local JSON threshold table under `apps/api/app/data/aap2022_thresholds.json`. It is used at runtime with no network dependency.

Table values were mirrored from public PediTools bili2022 API outputs for non-PHI synthetic inputs and cite:

Kemper AR et al. Clinical Practice Guideline Revision: Management of Hyperbilirubinemia in the Newborn Infant 35 or More Weeks of Gestation. Pediatrics. 2022;150(3):e2022058859.

Thomas-specific application: 39w6d rounds to the 40-week curve; DAT-positive/ABO isoimmune hemolytic disease selects the `any neurotoxicity risk factors` curve, lowering thresholds versus no-risk.
