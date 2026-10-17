# ADXL335 Sampling-Rate Audit

## Documentary evidence

An archived project document is titled `FFT of x, y, z at sample rate 1650`.

## Timestamp verification

The clean `vibration static value.xlsx` recording contains 516 complete X-Y-Z vectors over 0.922 seconds between its first and last timestamps.

- Observed complete-vector rate: `(516 - 1) / 0.922 = 558.57 vectors/s`
- Observed aggregate axis-conversion rate: `3 x 558.57 = 1675.70 conversions/s`

The small difference between 1675.70 and the documented 1650 is consistent with timestamp quantization, host-side logging jitter, and/or nominal timer rounding.

Another mixed motor recording gives approximately 555.59 timestamped rows/s over its complete duration, again close to one third of 1650 when each row is treated as one acquisition cycle. Mixed sensor sections prevent using that entire file as a clean independent estimate.

## Interpretation

The evidence does **not** support 1650 complete X-Y-Z vectors per second. It supports a nominal aggregate ADC rate of 1650 conversions/s shared across three sequential axes, giving approximately **550 samples/s per axis** and 550 complete X-Y-Z vectors/s.

For multisignal modelling, use nominal rates of 650 Hz for current and 550 Hz per vibration axis, align them by time, and do not align current and vibration by raw row number.

