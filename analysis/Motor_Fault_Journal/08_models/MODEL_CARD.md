# Model Card: Progressive Drilled-Rotor-Bar Classifier

## Intended use

Preliminary comparison of healthy, one-, two-, and three-drilled-rotor-bar conditions from current-like laboratory recordings. It is a research benchmark, not a production safety or maintenance decision system.

## Input and output

- Input: 24 engineered time- and frequency-domain features from a 650-sample window.
- Output: one of `healthy`, `drb1`, `drb2`, or `drb3`.
- Selected family: balanced random forest.

## Main blocked-test uncertainty

- accuracy: 0.931 (95% block-bootstrap CI 0.869–0.985)
- macro_f1: 0.917 (95% block-bootstrap CI 0.863–0.974)
- mcc: 0.904 (95% block-bootstrap CI 0.832–0.978)

## Split controls

Complete guard-separated blocks are assigned to only one partition, and duplicate window hashes across partitions were checked. However, some blocks may originate from the same physical acquisition. The result therefore does not yet demonstrate independent-session or new-motor generalization.

## Important limitations

- The 650 Hz sampling rate is taken from archived notes and should be confirmed.
- Signal/channel identities and physical units require final experimental verification.
- The present fitted model uses recovered current-like data; it is not yet a verified current-vibration-temperature fusion model.
- Class counts are unequal, especially for the two-drilled-bar class.
- The laboratory drilled-hole faults emulate progressive bar damage and are not identical to naturally developed broken bars.
- The healthy class used a different intact rotor-shaft-bearing assembly from the progressively drilled fault assembly. Healthy-versus-fault predictions may therefore exploit assembly-specific differences; the binary 100% result is not evidence of assembly-independent fault detection.
- New independent sessions, loads, days, and preferably a second motor are needed for external validation.
