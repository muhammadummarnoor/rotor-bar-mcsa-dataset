# Confirmed Experimental Metadata

This record combines information verified from the archived files and 2023 conference paper with clarifications supplied by the experimenter.

| Item | Confirmed information | Evidence/status |
|---|---|---|
| Measured signals | Motor current and vibration | Conference paper and experimenter confirmation |
| Current sensor | ACS712A20 Hall-effect current sensor | Conference paper/project presentation and experimenter confirmation |
| Current channels | One motor phase was measured through a single ACS712A20/ADC channel; the archived material does not identify the phase as R, Y, or B | One sensor in the setup, one `CT` input in the schematic, acquisition code reads one ADC channel, and final data contain one current stream per acquisition |
| Controlled motor components | The same motor body/stator, measured phase, current sensor, and front accelerometer position were retained across all conditions. The rotor, shaft, and bearings remained together as one fixed assembly; this same assembly was removed, progressively drilled, and reinstalled between stages. Bearings were not replaced between fault stages. | Experimenter confirmation |
| Healthy assembly | The healthy condition used a different intact rotor-shaft-bearing assembly. The one-, two-, and three-hole conditions used a second assembly that was progressively modified. Both assemblies were the same motor model and physical dimensions. | Experimenter confirmation |
| Pre-drilling baseline of fault assembly | No healthy recording exists for the progressively modified rotor-shaft-bearing assembly before Hole 1 was introduced. | Experimenter confirmation |
| Vibration channels | ADXL335 X, Y, and Z axes | Raw files, apparatus photograph, and experimenter confirmation |
| Accelerometer mounting | ADXL335 bonded only to the front/drive-end motor housing for the final healthy and drilled-bar experiments; Z approximately vertical/radial and normal to the PCB, with X and Y as orthogonal in-plane directions | Photograph, archived placement note, stationary data with Z approximately -1 g, and experimenter confirmation |
| Back accelerometer position | Not used in the final four-class experiment; any X1/Y1/Z1 back-position material is exploratory and must be excluded | Experimenter confirmation |
| Simultaneous acquisition | Current and three-axis vibration were recorded together for healthy, one-, two-, and three-drilled-bar conditions | Experimenter confirmation |
| Current sampling rate | 650 Hz | Explicit `Sample rate 650` entry in the three-drilled-bar file; timestamp row rates are not reliable because records are mixed/batched |
| Vibration sampling rate | Nominal 1650 ADC conversions/s shared across X, Y, and Z, equivalent to approximately **550 samples/s per axis** and 550 complete X-Y-Z vectors/s | Archived `FFT of x, y, z at sample rate 1650` document plus timestamp verification: 516 vectors over 0.922 s = 558.57 vectors/s and 1675.70 axis conversions/s |
| Load condition | Same fixed load for the compared recordings; treated as 30% load | Experimenter confirmation; conference paper explicitly describes the healthy 1.5 hp motor at 30% load and describes faulty vibration/current measurements as under load |
| Load mechanism | Belt/pulley braking system adjusted by movable nut-bolts and measured using two vertical spring balances | Conference paper methodology and test-rig photographs |
| Rotor progression | The same physical rotor was progressively modified: one bar was drilled, followed by a second bar and then a third bar | Experimenter confirmation |
| Drilling severity | Each selected rotor bar was drilled partially; the holes did not completely pass through/sever the bars | Experimenter confirmation; photographs verify the visible surface holes but cannot independently determine their internal depth |
| Drill diameter | No explicit diameter was found in the conference paper, extracted project report, FFT notes, filenames, or data sheets. The clearest photograph shows an opening about 23-25 pixels wide, approximately 0.36-0.38 of the visible shaft diameter. Without a scale or confirmed shaft diameter, only a rough 6-9 mm visual range can be suggested; this is not a reportable measurement. | Document search and image analysis |
| Hole placement | Hole 1 targeted one rotor bar. Hole 2 targeted the adjacent bar and was axially offset (lower/not aligned with Hole 1). Hole 3 targeted a different bar approximately 180 degrees around the rotor circumference. | Experimenter confirmation; photographs support the offset/distributed placement but cannot independently map the concealed cage bars |
| Acquisition sequence | The motor was stopped and restarted before recording each condition; the four conditions were not captured as one continuous recording | Experimenter confirmation |
| Repeated trials | Measurements were repeated several times with motor restarts, but exact restart boundaries are not consistently encoded in every archived file | Experimenter confirmation plus source-file audit |
| Rotor speed | No RPM measurement is stored with the experimental recordings. The conference paper mentions 1489 RPM for an unhealthy case, but this is not available as verified run-level metadata and must not be assigned to all classes. | Raw-file audit and experimenter confirmation |
| Operating line voltage | **415 V three-phase** | Experimenter confirmation; no synchronized run-level voltage column is present in the ML CSV/XLSX files |
| Archived motor parameters | An older project slide states 230 V delta, 1-3 A, 1400 RPM, 1000 W, and four poles | Archived `Presentation1.pptx`; the 230 V delta entry must not replace the experimenter-confirmed 415 V operating line voltage |

## Caution

The conference paper explicitly attaches the 30% value to the healthy result. Applying 30% to every fault condition additionally relies on the experimenter's confirmation that the same fixed load was maintained across the compared recordings.

The three fault-severity classes are repeated stages of one progressively modified rotor. They must not be described as three independent faulty rotors, and validation cannot be interpreted as rotor-to-rotor generalization.

The fault classes should be called **partial drilled-rotor-bar faults** or **progressive drilled-bar damage**. They should not be described as completely broken bars unless additional physical evidence establishes full electrical interruption.

The progressive stages damaged different bars: the first two bars were adjacent, with axially offset holes, and the third damaged bar was approximately diametrically opposite. This geometry should be described explicitly instead of implying that all three damaged bars were adjacent.

Keeping the stator/body and sensors fixed reduces some hardware confounding. However, the healthy class used a different intact rotor-shaft-bearing assembly from the progressively drilled fault assembly. Healthy-versus-fault separation may therefore include assembly identity, bearing/shaft variation, balance, or fit differences in addition to drilled-bar damage. The trained model does not establish motor-to-motor or rotor-to-rotor generalization, and the binary 100% result must not be interpreted as pure fault-detection performance.

The archived presentation's 230 V delta, 1000 W, and 1400 RPM entries differ from the confirmed 415 V experimental supply and from the conference paper's description of a 1.5 hp motor and its reported 1489 RPM unhealthy case. The manuscript will use 415 V as the operating line voltage, while treating the older slide values as conflicting archival specifications rather than synchronized measurements.
