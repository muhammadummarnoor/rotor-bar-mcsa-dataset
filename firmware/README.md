# Acquisition firmware

`acquisition/over_all_code.ino` is the Arduino-framework sketch used to log the motor current (ACS712A20 on analog pin A0).

* Reads the ACS712 output with `analogRead` in bursts of 30,000 reads and streams the raw ADC counts over serial at 57,600 baud.
* Prints `Current Value Taken` after each burst. These markers are the capture boundaries visible in the raw files
  (full captured sequences of about 29,975 samples).
* The same sketch also reads a DHT22 temperature sensor; the ADXL335 vibration section is commented out in this version.
* Libraries: `Filters` (RunningStatistics), `DHT`, `Adafruit_Sensor`.

**Status of this file:** the sketch is the project's overall acquisition program, whose burst length and markers match the raw
files. The authors should confirm it is the exact version used for the final recordings and the board it was compiled for.
**The sampling rate has not been derived from this code:** the sketch prints at most once per millisecond and includes a
2 microsecond delay per read, and the 650 samples/s used in the paper comes from a note in the recordings and the conference
paper, not from this program. Treat 650 samples/s as an acquisition assumption that is supported, not proven, by the supply-line check in `analysis/validate_sampling_rate.py`.
