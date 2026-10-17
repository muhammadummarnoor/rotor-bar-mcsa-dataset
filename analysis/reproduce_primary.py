"""Repeat archived primary training in a fresh folder, never overwrite evidence.

This is a retrospective reproducibility check. The original test has already
been examined, so this cannot create a new untouched confirmatory test.
No archived .joblib file is loaded.
"""
from pathlib import Path
from datetime import datetime
import argparse, importlib.metadata, json, sys

ROOT = Path(__file__).resolve().parent
local_packages = ROOT/('runtime_readable' if (ROOT/'runtime_readable').exists() else 'runtime_packages')
if local_packages.exists(): sys.path.insert(0, str(local_packages))
sys.path.insert(0,str(ROOT/'Motor_Fault_Journal'/'10_code'))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-candidates',action='store_true',help='Repeat 144-candidate training/validation search')
    args = parser.parse_args()
    import pandas as pd
    import joblib
    from sklearn.base import clone
    import step_12_primary_benchmark as benchmark
    from train_benchmark import candidates
    from ml_metrics import classification_metrics, PRIMARY_LABELS
    out = ROOT/'Reproduction_Runs'/datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    out.mkdir(parents=True,exist_ok=False)
    frame, families = benchmark.load_inputs()
    archived = json.loads((benchmark.RESULT_DIR/'selected_configuration_before_test.json').read_text())
    selected = archived
    if args.all_candidates:
        leaderboard, selected = benchmark.selection_phase(frame,families)
        leaderboard.to_csv(out/'validation_leaderboard.csv',index=False)
    columns = families[selected['feature_family']]
    model = clone(candidates()[selected['classifier']][selected['variant_index']])
    fit = frame[frame['split'].isin(['train','validation'])]
    test = frame[frame['split']=='test']
    model.fit(fit[columns],fit['label'])
    predicted = model.predict(test[columns])
    values = classification_metrics(test['label'],predicted,PRIMARY_LABELS)
    records = test[['window_hash','run_id','block_id','window_start','label']].copy()
    records['prediction'] = predicted
    records.to_csv(out/'test_predictions.csv',index=False)
    old = pd.read_csv(benchmark.RESULT_DIR/'test_predictions.csv')
    merged = records.merge(old[['window_hash','prediction']],on='window_hash',suffixes=('_new','_archived'),validate='one_to_one')
    report = {'created_at':datetime.now().astimezone().isoformat(),
              'purpose':'Retrospective reproducibility check, not a new confirmatory experiment',
              'all_candidates_retrained':args.all_candidates,'selected':selected,
              'matches_archived_selected_classifier':selected['classifier']==archived['classifier'],
              'matches_archived_selected_features':selected['feature_family']==archived['feature_family'],
              'test_metrics':values,
              'matching_predictions':int((merged.prediction_new==merged.prediction_archived).sum()),
              'test_windows':len(test),'training_and_validation_windows':len(fit),
              'python':sys.version,
              'software':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','scikit-learn','joblib']}}
    (out/'reproduction_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    joblib.dump({'model':model,'features':columns,'labels':PRIMARY_LABELS},out/'retrained_model.joblib')
    print(json.dumps(report,indent=2))
    print('Output folder:',out)

if __name__=='__main__': main()
