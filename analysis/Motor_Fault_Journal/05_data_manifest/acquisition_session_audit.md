# Acquisition-Session Audit

The source files were checked for explicit `Current Value Taken` markers, timestamp changes, separated numeric runs, and parallel recording columns. These source-level acquisitions must not be confused with the 9,000-sample blocks later created for machine-learning splitting.

| Condition | What is visible in the file | Defensible interpretation |
|---|---|---|
| Healthy | One contiguous current-like section of 92,241 samples, followed by a `Current Value Taken` marker and vibration-like values | The long section may contain repeated trials, but there are no internal restart markers. Treat it as one source session until its internal boundaries can be supplied. |
| One drilled bar | Four parallel full current-like sequences of 29,976 samples, each ending with a `Current Value Taken` marker; additional partial current-like material also appears later | At least four full captured current sequences are present. Whether each parallel column represents a separate physical restart is supported by the experimenter's statement but is not encoded by an explicit session ID. |
| Two drilled bars | One full current-like sequence of 29,975 samples ending with `Current Value Taken`, followed later by a short second current-like segment | Repeated capture is visible, but only one complete current sequence is unambiguously recoverable. |
| Three drilled bars | Two full current-like sequences of approximately 29,975 samples, each ending with `Current Value Taken` | Two complete current captures are unambiguously visible. |

## Conclusion

The experimenter confirms several stop-and-restart repetitions. The archived files contain evidence of repeated capture, particularly for the one- and three-drilled-bar stages. However, exact restart boundaries are not consistently stored for every condition. Therefore, the current blocked benchmark must not be described as a fully independent-session test.

