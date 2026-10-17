"""Check the assumed 650 samples/s against the 50 Hz supply line.

The sampling rate was not logged with the recordings. For each long current record the
strongest spectral component between 40 and 60 Hz is located (Hann window, zero-padded FFT)
when 650 samples/s is assumed. If the supply is at its nominal 50 Hz, the sampling rate
implied by that peak is 650 * 50 / f_peak. This is a plausibility check on the average rate.
It does not show that the rate was constant inside a record.
"""
from pathlib import Path
import sys, json
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / 'Motor_Fault_Journal'
sys.path.insert(0, str(PROJECT / '10_code'))
from train_benchmark import read_columns

ASSUMED_FS = 650.0
SUPPLY_HZ = 50.0
MAX_SAMPLES = 29000
NFFT = 1 << 18
LABELS = {'healthy': 'H0', 'drb_1': 'F1', 'drb_2': 'F2', 'drb_3': 'F3'}

def main():
    blocks = pd.read_csv(PROJECT / '05_data_manifest/split_block_manifest.csv')
    rows = []
    for (src, col, run), g in blocks.groupby(['source_file', 'source_column', 'run_id'], sort=False):
        columns = read_columns(PROJECT / src.replace('\\', '/'))
        first = int(g.source_start_row.min()) - 1
        last = int(g.source_end_row.max())
        x = np.asarray(columns[int(col) - 1][first:last], dtype=float)[:MAX_SAMPLES]
        x = x - x.mean()
        spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)), NFFT))
        freq = np.fft.rfftfreq(NFFT, 1 / ASSUMED_FS)
        band = (freq > 40) & (freq < 60)
        peak = float(freq[np.argmax(spectrum * band)])
        rows.append({'class_label': g.class_label.iloc[0], 'paper_label': LABELS[g.class_label.iloc[0]],
                     'run_id': run, 'samples_used': len(x), 'peak_hz_at_assumed_rate': round(peak, 3),
                     'implied_sampling_rate': round(ASSUMED_FS * SUPPLY_HZ / peak, 1)})
    table = pd.DataFrame(rows)
    out = ROOT / 'Reproduction_Runs'
    out.mkdir(exist_ok=True)
    table.to_csv(out / 'sampling_rate_check.csv', index=False)
    print(table.to_string(index=False))
    print('implied rate range: %.1f to %.1f samples/s (assumed %.0f)' % (
        table.implied_sampling_rate.min(), table.implied_sampling_rate.max(), ASSUMED_FS))

if __name__ == '__main__':
    main()
