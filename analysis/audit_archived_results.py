"""Recompute archived classification results without loading trained pickle files.

This checks saved predictions and split provenance. It does not retrain models
or certify experimental independence, calibration, or sample timing.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import csv, hashlib, json, math

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / 'Motor_Fault_Journal'

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def metrics(records, labels):
    cm = [[sum(r['label'] == a and r['prediction'] == b for r in records)
           for b in labels] for a in labels]
    truth = [sum(r) for r in cm]
    pred = [sum(r[j] for r in cm) for j in range(len(labels))]
    n = sum(truth)
    c = sum(cm[i][i] for i in range(len(labels)))
    precision = [cm[i][i]/pred[i] if pred[i] else 0 for i in range(len(labels))]
    recall = [cm[i][i]/truth[i] if truth[i] else 0 for i in range(len(labels))]
    f1 = [2*p*r/(p+r) if p+r else 0 for p,r in zip(precision,recall)]
    den = math.sqrt((n*n-sum(x*x for x in pred))*(n*n-sum(x*x for x in truth)))
    return cm, {'accuracy': c/n, 'macro_f1': sum(f1)/len(labels),
                'balanced_accuracy': sum(recall)/len(labels),
                'macro_precision': sum(precision)/len(labels),
                'macro_recall': sum(recall)/len(labels),
                'mcc': (c*n-sum(p*t for p,t in zip(pred,truth)))/den if den else 0}

def main():
    result = {'checked_at': datetime.now().astimezone().isoformat(), 'checks': {},
              'scope': 'Saved predictions and provenance only; no model retraining'}
    for name, labels in [('step_12_primary',['drb_1','drb_2','drb_3']),
                         ('step_13_random_comparison',['drb_1','drb_2','drb_3']),
                         ('step_16_secondary_four_class',['healthy','drb_1','drb_2','drb_3'])]:
        folder = PROJECT/'09_results'/name
        prediction_path = folder/'test_predictions.csv'
        if not prediction_path.exists():
            result['checks'][name+'_available'] = False
            continue
        records = rows(prediction_path)
        cm, values = metrics(records, labels)
        saved = json.loads((folder/'test_metrics.json').read_text())
        comparison = {k: abs(v-saved[k])<1e-12 for k,v in values.items()}
        result['checks'][name+'_metrics_match'] = all(comparison.values())
        result[name] = {'labels': labels, 'confusion_matrix':cm,'metrics':values,
                        'metric_checks':comparison,'windows':len(records),
                        'blocks':len({r['block_id'] for r in records})}
    manifest = rows(PROJECT/'05_data_manifest'/'blocked_window_manifest.csv')
    primary = [r for r in manifest if r['class_label'] != 'healthy']
    for key in ['block_id','window_hash']:
        groups = defaultdict(set)
        for r in primary: groups[r[key]].add(r['split'])
        result['checks'][key+'_disjoint'] = all(len(s)==1 for s in groups.values())
    ranges = defaultdict(list)
    for r in primary:
        ranges[r['run_id']].append((int(r['within_run_start']),int(r['within_run_end_exclusive']),r['split']))
    overlaps = []
    gaps = []
    for run, intervals in ranges.items():
        intervals.sort()
        for a,b in zip(intervals,intervals[1:]):
            if a[2] != b[2]:
                gaps.append(b[0]-a[1])
                if b[0]<a[1]: overlaps.append(run)
    result['checks']['cross_split_sample_ranges_disjoint'] = not overlaps
    result['smallest_cross_split_gap_samples'] = min(gaps) if gaps else None
    result['primary_windows_by_split'] = dict(Counter(r['split'] for r in primary))
    result['primary_test_support'] = dict(Counter(r['paper_label'] for r in primary if r['split']=='test'))
    result['runs_shared_across_splits'] = {run: sorted({x[2] for x in intervals}) for run,intervals in ranges.items() if len({x[2] for x in intervals})>1}
    record = json.loads((PROJECT/'09_results'/'step_12_primary'/'run_record.json').read_text())
    paths = {'features':'07_features/current_window_features.csv',
             'feature_config':'05_data_manifest/frozen_feature_sets.json',
             'classifier_config':'05_data_manifest/frozen_classifier_search.json',
             'split_audit':'05_data_manifest/blocked_split_leakage_audit.json'}
    result['input_hash_checks'] = {k:digest(PROJECT/v)==record['input_hashes'][k] for k,v in paths.items()}
    result['checks']['archived_input_hashes_match'] = all(result['input_hash_checks'].values())
    result['status'] = 'PASS' if all(result['checks'].values()) else 'FAIL'
    result['interpretation'] = 'PASS confirms these checks only. Time-block separation does not establish independent recording sessions or motors. Sampling rate remains an acquisition assumption until validated from source timing.'
    out = Path(__file__).with_name('independent_prediction_audit.json')
    out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result

if __name__ == '__main__':
    main()
