# Time-blocked MCSA benchmark for progressively drilled rotor-bar faults

Raw motor-current recordings, acquisition firmware, analysis code and results supporting a manuscript on guarded time-block evaluation of MCSA rotor-bar fault classification (submitted to Sensors) (Noor, Farooq, Noor, Farooq, Ali and Ali).

> Archive DOI: [https://doi.org/10.5281/zenodo.23438066](https://doi.org/10.5281/zenodo.23438066) · Code: [https://github.com/muhammadummarnoor/rotor-bar-mcsa-dataset](https://github.com/muhammadummarnoor/rotor-bar-mcsa-dataset)

## What this is

A 1.5 hp, 50 Hz, three-phase squirrel-cage induction motor on a belt-and-pulley loaded test rig. One stator phase current
was measured with an ACS712A20 Hall-effect sensor, digitised by an STM32 Nucleo-64 board and logged to a PC.
Four conditions were recorded at one fixed load (nominally 30 %):

| Label | Code label | Physical condition |
|---|---|---|
| H0 | `healthy` | Intact rotor. A **different** rotor-shaft-bearing assembly from F1–F3. |
| F1 | `drb_1` | One rotor bar with one partial drilled hole. |
| F2 | `drb_2` | A second bar drilled (axially offset, adjacent to the first). |
| F3 | `drb_3` | A third bar drilled (about 180° around the rotor). |

F1–F3 are three successive stages of **one** rotor, not three rotors. The holes are partial; the bars are not severed.
The primary task is F1/F2/F3 classification. H0 is used only in a secondary analysis.

## Folder map

```
rotor-bar-mcsa-dataset/
├── README.md, CITATION.cff, LICENSE-DATA.md, LICENSE-CODE.txt, requirements.txt, .zenodo.json
├── firmware/
│   └── acquisition/over_all_code.ino      acquisition sketch (see firmware/README.md)
└── analysis/
    ├── reproduce_primary.py               re-trains and re-tests the selected model
    ├── verify_raw_features.py             rebuilds every window and feature from the raw files
    ├── audit_archived_results.py          independent check of the saved metrics
    ├── validate_sampling_rate.py          checks the assumed 650 samples/s against the 50 Hz supply line
    └── Motor_Fault_Journal/
        ├── 04_raw_data/                   healthy/, drb_1/, drb_2/, drb_3/  (raw, unmodified)
        ├── 05_data_manifest/              window manifest, split manifest, frozen protocols, audits
        ├── 07_features/                   current_window_features.csv (+ window_sensitivity/)
        ├── 08_models/                     MODEL_CARD.md, selected_model.json (no pickles)
        ├── 09_results/                    leaderboard, predictions, metrics, confusion matrices, tables
        └── 10_code/                       feature extraction, classifiers, metrics, step_12 … step_18
```

## Quick start

```bash
pip install -r requirements.txt
cd analysis
python verify_raw_features.py     # 390 windows rebuilt from raw samples, all hashes and features match
python reproduce_primary.py       # selected model re-fitted; predictions compared with the archived ones
python audit_archived_results.py  # independent recomputation of the saved metrics
python validate_sampling_rate.py  # implied sampling rate 651-660 samples/s in all 8 long records
```

Add `--all-candidates` to `reproduce_primary.py` to repeat the full 144-configuration search (a few seconds).
Each run writes to a new timestamped folder under `analysis/Reproduction_Runs/`; archived results are never overwritten.

Verified for this package: `verify_raw_features.py` reports PASS for 390 of 390 windows (largest scaled feature
difference about 2e-15), and `reproduce_primary.py` reproduces macro-F1 0.9065, accuracy 0.9121 and 91 of 91 archived
test predictions.

## Data description

* **Raw files** (`04_raw_data/`): serial-logger exports of the current channel as raw ADC counts (unitless integers).
  Files also carry other logger content (timestamp columns and text markers). Do not read them as clean single-column
  signals; use `blocked_window_manifest.csv`, which gives the exact column and row range of every window.
* **Windows**: non-overlapping, 650 samples (1.0 s at the assumed 650 samples/s). 390 windows over the four classes,
  130 each in train, validation and test; the primary F1–F3 task uses 273 of them.
* **Splits**: complete 9,000-sample temporal blocks, each followed by a 650-sample guard gap, assigned to train, validation or test
  (`split_block_manifest.csv`). A random-window split is provided only as a leakage diagnostic.
* **Features** (`current_window_features.csv`): 13 time-domain and 10 spectral features per window, keyed by `window_hash`
  (SHA-256 of the raw samples). Column definitions are in `DATA_DICTIONARY.md`.
* **Results**: `09_results/step_12_primary/` holds the validation leaderboard (144 configurations), the selected configuration
  frozen before testing, test predictions, confusion matrix, per-class metrics and the block-bootstrap interval.


## Not included

Serialised `.joblib` models (pickle files can execute code when loaded; retrain with the scripts instead), legacy and
unlabelled recordings, second-motor recordings, vibration and temperature channels, and manuscript-building scripts.

## How to cite

See `CITATION.cff`. Please also cite the original test-rig paper: Ali, U.; Ali, W.; Noor, M.U.; Ramzan, M.U.; Aslam, M.U.; Farooq, H.
*Test Rig for the Fault Diagnosis of 3-Phase Small Scale Induction Motor.* ICIT 2023. https://doi.org/10.1109/ICIT59216.2023.10335706

## Licences

Data and documentation: CC BY 4.0 (`LICENSE-DATA.md`). Code: MIT (`LICENSE-CODE.txt`).
