#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import shutil
import subprocess
import time
import os
import pandas as pd

from run_fault_generalization_ieee30_serial_resume import (
    PROJECT_ROOT, ROOT, MANIFEST, RAW, DIAG, MATLAB, MATLAB_SCRIPT_DIR,
    validate_csv, load_manifest, sync_manifest, write_pending_diagnostics, cleanup_caches,
)

LOGDIR = ROOT / 'logs' / 'ieee30_two_worker_resume'
WORK = ROOT / 'worker_state'
SOURCE_MODEL = Path('/home/hy/문서/matlab/Thirtybussys_WMU_IBR_auto.slx')


def prepare_worker(worker_id: int) -> tuple[Path, Path]:
    wdir = WORK / f'worker_{worker_id}'
    wdir.mkdir(parents=True, exist_ok=True)
    model = wdir / f'Thirtybussys_WMU_IBR_auto_worker{worker_id}.slx'
    if (not model.exists()) or model.stat().st_mtime < SOURCE_MODEL.stat().st_mtime:
        shutil.copy2(SOURCE_MODEL, model)
    cache = wdir / 'simulink_cache'
    cache.mkdir(exist_ok=True)
    return model, cache


def run_case_worker(case_id: int, worker_id: int, timeout_s: int, attempt: int) -> dict:
    model, cache = prepare_worker(worker_id)
    LOGDIR.mkdir(parents=True, exist_ok=True)
    log = LOGDIR / f'worker{worker_id}_case_{case_id:04d}_attempt{attempt}.log'
    env = os.environ.copy()
    env['WMU_FG_NO_MANIFEST'] = '1'
    env['WMU30_MODEL_OVERRIDE'] = str(model)
    env['WMU_FG_CACHE_DIR'] = str(cache)
    cmd = [MATLAB, '-batch', f"addpath('{MATLAB_SCRIPT_DIR}'); run_fault_generalization_v1('case_{case_id}')"]
    start = time.time()
    status = 'FAILED'; msg = ''
    with log.open('w') as f:
        f.write(f'=== start {time.strftime("%Y-%m-%dT%H:%M:%S%z")} worker={worker_id} case={case_id} attempt={attempt}\n')
        f.write(f'model={model}\ncache={cache}\ncmd={" ".join(cmd)}\n')
        f.flush()
        try:
            r = subprocess.run(cmd, cwd=PROJECT_ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout_s)
            if r.returncode != 0:
                status = 'FAILED'; msg = f'exit_code={r.returncode}; log={log}'
            else:
                df = load_manifest()
                row = df[(df['NetworkID'].astype(str)=='ieee30') & (df['CaseID'].astype(int)==case_id)].iloc[0]
                ok, vmsg = validate_csv(Path(str(row['OutputFile'])), 30)
                status = 'SUCCESS' if ok else 'FAILED'
                msg = vmsg + f'; log={log}'
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'; msg = f'timeout after {timeout_s}s; log={log}'
            timeout_diag = DIAG / f'ieee30_timeout_case_{case_id}.txt'
            timeout_diag.write_text(f'CaseID={case_id}\nworker={worker_id}\ntimeout={timeout_s}\nmodel={model}\ncache={cache}\nlog={log}\ncommand={" ".join(cmd)}\n', encoding='utf-8')
    elapsed = time.time() - start
    return {'CaseID': case_id, 'Worker': worker_id, 'Attempt': attempt, 'Status': status, 'Elapsed': elapsed, 'Message': msg}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--timeout', type=int, default=600)
    ap.add_argument('--max-retry', type=int, default=1)
    args = ap.parse_args()
    if args.workers > 2:
        raise SystemExit('Use at most 2 workers for stabilized run')
    df = sync_manifest(load_manifest())
    write_pending_diagnostics(df)
    pending = df[(df['NetworkID'].astype(str)=='ieee30') & (df['Status'].astype(str)!='SUCCESS')].sort_values('CaseID')
    case_ids = [int(x) for x in pending['CaseID'].tolist()]
    if args.limit > 0:
        case_ids = case_ids[:args.limit]
    progress = ROOT / 'logs' / 'ieee30_two_worker_resume_progress.log'
    start_all = time.time(); done = retries = timeouts = failures = 0; max_elapsed = 0.0
    attempt_by_case = {cid: 1 for cid in case_ids}
    queue = list(case_ids)
    while queue:
        batch = []
        for wid in range(1, args.workers + 1):
            if queue:
                cid = queue.pop(0)
                batch.append((cid, wid, attempt_by_case[cid]))
        with ThreadPoolExecutor(max_workers=len(batch)) as ex:
            futs = [ex.submit(run_case_worker, cid, wid, args.timeout, att) for cid, wid, att in batch]
            for fut in as_completed(futs):
                res = fut.result(); cid = int(res['CaseID']); status = str(res['Status']); elapsed = float(res['Elapsed'])
                max_elapsed = max(max_elapsed, elapsed)
                df = load_manifest()
                idx = df[(df['NetworkID'].astype(str)=='ieee30') & (df['CaseID'].astype(int)==cid)].index[0]
                df.at[idx,'Status'] = status
                df.at[idx,'Runtime'] = elapsed
                df.at[idx,'ErrorMessage'] = '' if status == 'SUCCESS' else str(res['Message'])
                df.to_csv(MANIFEST, index=False)
                if status != 'SUCCESS' and attempt_by_case[cid] <= args.max_retry:
                    attempt_by_case[cid] += 1
                    retries += 1
                    cleanup_caches()
                    queue.append(cid)
                else:
                    done += 1
                    if status == 'TIMEOUT': timeouts += 1
                    if status == 'FAILED': failures += 1
                df = sync_manifest(load_manifest())
                remaining = int((df[(df['NetworkID'].astype(str)=='ieee30')]['Status'].astype(str)!='SUCCESS').sum())
                avg = (time.time()-start_all)/max(done,1)
                line = f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} case={cid} worker={res['Worker']} status={status} elapsed={elapsed:.2f} done={done} remaining={remaining} avg={avg:.2f} max={max_elapsed:.2f} retries={retries} timeouts={timeouts} failures={failures}\n"
                progress.parent.mkdir(parents=True, exist_ok=True)
                with progress.open('a') as f: f.write(line)
                print(line, end='', flush=True)
    df = sync_manifest(load_manifest())
    write_pending_diagnostics(df)
    print(df[df['NetworkID'].astype(str)=='ieee30']['Status'].value_counts().to_string())
    return 0 if failures == 0 and timeouts == 0 else 2

if __name__ == '__main__':
    raise SystemExit(main())
