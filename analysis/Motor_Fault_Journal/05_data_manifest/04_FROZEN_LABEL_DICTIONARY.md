# Frozen Class-Label Dictionary

**Status:** Frozen before final model rerun  
**Date frozen:** 24 August 2026  
**Applies to:** all processed data, features, split manifests, models, results, figures, and manuscript text

## 1. Canonical labels

| Paper label | Code label | Physical condition | Assembly | Primary task | Secondary task |
|---|---|---|---|---|---|
| H0 | `healthy` | Intact healthy rotor condition | Separate intact rotor-shaft-bearing assembly of the same model/dimensions | Excluded | Included with assembly-confounding warning |
| F1 | `drb_1` | One rotor bar containing one partial drilled hole | Progressively modified fault rotor-shaft-bearing assembly | Included | Included |
| F2 | `drb_2` | Two rotor bars containing partial drilled holes | Same progressively modified fault assembly as F1 and F3 | Included | Included |
| F3 | `drb_3` | Three rotor bars containing partial drilled holes | Same progressively modified fault assembly as F1 and F2 | Included | Included |

The code labels are retained to preserve compatibility with the existing manifests and modelling pipeline. Paper labels H0/F1/F2/F3 provide concise notation for tables and figures.

## 2. Physical label definitions

### H0 - healthy condition

- Intact rotor condition.
- Measured using a different rotor-shaft-bearing assembly from the progressively drilled fault assembly.
- Assembly model and dimensions were reported as the same.
- H0 must not be treated as a matched pre-drilling baseline of the fault assembly.
- Healthy-versus-fault differences may include assembly-specific information.

### F1 - first partial-drilling stage

- One partial hole was introduced into one rotor bar.
- The bar was not confirmed to be completely severed.
- This is the first ordinal fault stage, not a measured percentage of physical damage.

### F2 - second partial-drilling stage

- A partial hole was introduced into an adjacent rotor bar.
- The second hole was axially offset downward and was not aligned with the first hole.
- F2 contains the F1 damage plus the newly introduced second-bar damage.

### F3 - third partial-drilling stage

- A third rotor bar was partially drilled.
- The third affected bar was approximately 180 degrees around the rotor circumference relative to the earlier damaged region.
- F3 contains the previous progressive damage plus the third affected bar.

## 3. Label ordering

The only permitted ordinal order is:

> H0 < F1 < F2 < F3

This ordering represents the experimental sequence and number of partially drilled bars. It does not represent a calibrated physical-damage scale because drill diameter and numerical drill depth are unavailable.

For the primary task, the permitted order is:

> F1 < F2 < F3

Models may be evaluated as nominal multiclass classifiers. Any future ordinal model must state that the target represents experimental stage, not an equal-interval severity measurement.

## 4. Frozen classification tasks

### Task P - primary progressive-stage classification

- **Classes:** F1, F2, F3.
- **Purpose:** distinguish progressive partial-drilling stages on the same fault rotor-shaft-bearing assembly.
- **Main manuscript role:** central benchmark and primary abstract result.

### Task S - secondary four-class classification

- **Classes:** H0, F1, F2, F3.
- **Purpose:** exploratory healthy-to-progressive-stage discrimination.
- **Required limitation:** H0 uses a different assembly, so separation of H0 from F1/F2/F3 is assembly-confounded.

### Task E - exploratory binary classification

- **Classes:** H0 versus {F1, F2, F3}.
- **Purpose:** historical comparison only.
- **Required limitation:** the binary result cannot isolate fault detection from assembly identity.
- **Manuscript role:** supplementary or appendix material, not a principal contribution.

No other regrouping or relabelling is permitted without a dated amendment.

## 5. Label provenance

Labels are supported by the combination of:

1. Explicit healthy/first-hole/second-hole/third-hole source filenames.
2. The organized raw-data folder mapping.
3. Rotor photographs showing progressive drilled-hole conditions.
4. The conference paper's experimental context.
5. Experimenter confirmation of the same progressively modified fault rotor and the hole-placement sequence.

Generic ADXL, all-sensor, calibration, temperature, and second-motor files do not satisfy this provenance chain and receive no H0/F1/F2/F3 label.

## 6. Required terminology

### Approved terms

- healthy condition
- one, two, or three partially drilled rotor bars
- progressive partial-drilling stage
- controlled drilled-rotor-bar fault emulation
- F1/F2/F3 severity-stage classification
- experimental ordinal stage

### Prohibited or misleading terms

- naturally broken rotor bar
- fully broken rotor bar
- completely severed bar
- one-, two-, or three-hole vibration class
- measured drill severity percentage
- equal damage increment
- matched healthy baseline of the fault assembly

The abbreviation BRB may be used when discussing the broader literature. When describing this experiment, it must be qualified as partial drilled-bar fault emulation.

## 7. Required fields attached to every model observation

Every window or feature row must retain:

- `class_label`: `healthy`, `drb_1`, `drb_2`, or `drb_3`;
- `paper_label`: H0, F1, F2, or F3;
- canonical source file;
- source SHA-256;
- recovered run identifier;
- source column;
- source start and end rows;
- block identifier;
- window start and end sample indices;
- train/validation/test assignment;
- assembly group: `healthy_assembly` or `progressive_fault_assembly`.

The assembly field is mandatory for interpreting the secondary task and for preventing language that treats H0 as a matched baseline.

## 8. Label-integrity checks

Before final model training, verify that:

1. Every observation has exactly one permitted code label.
2. Every code label maps to exactly one paper label.
3. F1/F2/F3 observations map only to the progressive fault assembly.
4. H0 observations map only to the separate healthy assembly.
5. No duplicate file, calibration trial, generic sensor recording, or second-motor file has a supervised class label.
6. No signal window crosses between source runs or condition labels.
7. Class names and ordering are identical across feature tables, model code, result files, figures, and manuscript tables.

## 9. Step 4 completion decision

Step 4 is complete because the label codes, paper labels, physical meanings, ordinal interpretation, provenance, permitted tasks, terminology, assembly mapping, and integrity checks are explicitly frozen.
