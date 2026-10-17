# Vibration-to-Condition Mapping Audit

## Archive-wide result

All CSV and XLSX filenames and structures in the supplied ZIP were inspected. The final current recordings and vibration recordings were stored separately. A four-class raw X-Y-Z dataset cannot presently be reconstructed with defensible condition labels.

| Condition/source | Raw current | Raw X-Y-Z vibration | Mapping status |
|---|---:|---:|---|
| Healthy file dated 2022-02-17 | Yes | Yes; a large three-column low-g section follows the current section | Healthy vibration is recoverable from this file, subject to confirming the internal marker/boundary |
| One-hole file dated 2022-03-04 | Yes | No complete condition-labelled X-Y-Z section identified | Missing/unmapped |
| Two-hole file dated 2022-03-04 | Yes | No; the file has only timestamp/value structure and contains current/temperature-like sections | Missing/unmapped |
| Three-hole file dated 2022-03-04 | Yes | No raw condition-labelled X-Y-Z section identified | Missing raw data; an FFT document states that the motor was faulty with three holes, but a plot is not a substitute for raw samples |
| `second motor ... front adxl335.csv` | Yes/mixed | Vibration-like values present | Belongs to a separately named second-motor experiment and must not be relabelled as one of the progressive fault stages |
| Generic `all sensor reading`, `adxl value`, calibration, and static files | Mixed/calibration | X-Y-Z values present | No reliable healthy/one-/two-/three-hole label; exclude from supervised four-class training |

## Consequence for modelling

The current four-class model can be reproduced from labelled current recordings. A true current-plus-vibration four-class model cannot be trained without the missing or unmapped one-, two-, and three-hole X-Y-Z recordings. Generic vibration files must not be assigned fault labels by date guesswork or visual similarity.

The working title should use **multisignal** only if the missing fault-stage vibration recordings are recovered and linked to acquisition sessions. Otherwise, the final paper should be framed as a current-signal benchmark, with vibration analysis from the conference study used only as prior experimental context.

