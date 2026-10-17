"""Read-only reconstruction of archived windows and features from source files."""
from pathlib import Path
from datetime import datetime
import sys,json,hashlib
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/('runtime_readable' if (ROOT/'runtime_readable').exists() else 'runtime_packages')))
sys.path.insert(0,str(ROOT/'Motor_Fault_Journal/10_code'))
import numpy as np
import pandas as pd
from train_benchmark import read_columns,features_for_window,sha256

def main():
    project=ROOT/'Motor_Fault_Journal'
    manifest=pd.read_csv(project/'05_data_manifest/blocked_window_manifest.csv')
    features=pd.read_csv(project/'07_features/current_window_features.csv').set_index('window_hash')
    config=json.loads((project/'05_data_manifest/frozen_feature_sets.json').read_text())
    names=config['time_domain']+config['frequency_domain']
    failures=[]; checked=0; source_checks={}; largest=0.0
    for rel,group in manifest.groupby('canonical_source_file',sort=False):
        path=project/rel.replace('\\','/')
        source_checks[rel]=sha256(path)==group.iloc[0]['source_sha256']
        columns=read_columns(path)
        for row in group.itertuples(index=False):
            values=columns[int(row.source_column)-1][int(row.source_start_row)-1:int(row.source_end_row_inclusive)]
            hashed=hashlib.sha256(np.asarray(values,dtype=np.float64).tobytes()).hexdigest()
            if hashed!=row.window_hash or len(values)!=int(row.window_samples):
                failures.append({'window':row.observation_id,'reason':'raw hash or length mismatch'});continue
            rebuilt=features_for_window(values)
            expected=features.loc[row.window_hash]
            a=np.array([rebuilt[k] for k in names]);b=expected[names].to_numpy(dtype=float)
            largest=max(largest,float(np.max(np.abs(a-b)/(1+np.abs(b)))))
            if not np.allclose(a,b,rtol=1e-9,atol=1e-9):
                failures.append({'window':row.observation_id,'reason':'feature mismatch'})
            checked+=1
        print('Checked source:',rel,flush=True)
    report={'checked_at':datetime.now().astimezone().isoformat(),
            'status':'PASS' if not failures and all(source_checks.values()) and checked==len(manifest) else 'FAIL',
            'windows_checked':checked,'windows_in_manifest':len(manifest),'source_hash_checks':source_checks,
            'features_per_window':len(names),'maximum_scaled_absolute_difference':largest,'failures':failures,
            'scope':'Reconstruction from archived source rows. Does not validate acquisition timing or calibration.'}
    out=ROOT/'Reproduction_Runs'/'raw_feature_reconstruction.json'; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
