"""Bounded VLM batch: one disposable worker per CV, incremental standard reports."""
import argparse
import ctypes
import gc
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from run_experiment import PROJECT_ROOT, prepare_config, capture_environment, save_stage
from cv_extraction.extraction.pipeline import run_extraction
from cv_extraction.monitoring.reporting import build_document_summaries
from cv_extraction.storage import save_json


def worker(run_directory, document_id):
    config = json.loads((run_directory / 'config.json').read_text(encoding='utf-8'))
    document = next(d for d in config['inputs'] if d['id'] == document_id)
    directory = run_directory / 'documents' / document_id / 'repeat_001'
    for retry in range(4):
        result = run_extraction(
            PROJECT_ROOT / document['file'], config['stages'],
            on_stage_finished=lambda report, output: save_stage(directory, report, output),
            monitoring=config['monitoring'], attempt_directory=directory,
        )
        oom = any('out of memory' in str(stage.get('error', '')).lower()
                  for stage in result['stages'])
        vision = next(s for s in config['stages'] if s['method'] == 'vlm_structuring')
        pixels = vision['settings']['max_pixels']
        if not oom or retry == 3 or pixels <= 65536:
            break
        # Preserve failure diagnostics before overwriting the final stage report.
        shutil.copytree(directory / vision['name'],
                        directory / f'memory_retry_{retry + 1:03d}' / vision['name'])
        vision['settings']['max_pixels'] = max(65536, pixels // 2)
        print(f'OOM: retrying with max_pixels={vision["settings"]["max_pixels"]}', flush=True)
        import torch
        gc.collect()
        torch.cuda.empty_cache()
    result.pop('extracted_data')
    save_json(directory / 'report.json', {
        'document_id': document_id, 'repetition': 1, **result,
    })


def run_batch(config_path, hours, timeout_seconds):
    config = prepare_config(config_path)
    if config['repetitions'] != 1:
        raise ValueError('Overnight runs require repetitions=1.')
    started = datetime.now(timezone.utc)
    deadline = time.monotonic() + hours * 3600
    run_id = started.strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex[:8]
    directory = PROJECT_ROOT / 'results' / run_id
    directory.mkdir(parents=True)
    config['overnight'] = {'hours': hours, 'document_timeout_seconds': timeout_seconds}
    save_json(directory / 'config.json', config)
    save_json(directory / 'environment.json', capture_environment())
    reports = []
    stop_reason = 'completed'

    def checkpoint():
        save_json(directory / 'summary.json', {
            'run_id': run_id, 'started_at_utc': started.isoformat(),
            'finished_at_utc': datetime.now(timezone.utc).isoformat(),
            'document_count': len(config['inputs']), 'attempt_count': len(reports),
            'stop_reason': stop_reason,
            'documents': build_document_summaries(reports, config['inputs']),
        })

    # Keep this Windows batch awake; restore normal sleep behavior on exit.
    if os.name == 'nt':
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    print(f'Run: {run_id}; deadline: {hours:g} hours; {len(config["inputs"])} CVs', flush=True)
    try:
        for index, document in enumerate(config['inputs'], 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stop_reason = 'batch_time_limit'
                break
            attempt = directory / 'documents' / document['id'] / 'repeat_001'
            attempt.mkdir(parents=True)
            print(f'[{index}/{len(config["inputs"])}] {document["id"]}', flush=True)
            begin = time.monotonic()
            failure = None
            with (attempt / 'worker.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen(
                    [sys.executable, '-u', str(Path(__file__).resolve()),
                     '--worker-run', str(directory), '--document-id', document['id']],
                    cwd=PROJECT_ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env={**os.environ, 'HF_HUB_OFFLINE': '1'},
                )
                try:
                    code = process.wait(timeout=min(timeout_seconds, remaining))
                    if code:
                        failure = ('WorkerError', f'Worker exited with code {code}; see worker.log')
                except subprocess.TimeoutExpired:
                    failure = ('TimeoutError', 'Document or batch time limit exceeded')
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
            report_path = attempt / 'report.json'
            if not report_path.exists():
                kind, message = failure or ('WorkerError', 'Worker produced no report')
                stages = []
                for stage in config['stages']:
                    saved = attempt / stage['name'] / 'report.json'
                    if saved.exists():
                        stages.append(json.loads(saved.read_text(encoding='utf-8')))
                    else:
                        stages.append({
                            'name': stage['name'], 'method': stage['method'],
                            'execution_status': 'error', 'outcome': None,
                            'metrics': {'duration_seconds': time.monotonic() - begin},
                            'error': {'type': kind, 'message': message},
                        })
                save_json(report_path, {
                    'document_id': document['id'], 'repetition': 1, 'status': 'error',
                    'metrics': {'processing_seconds': time.monotonic() - begin},
                    'stages': stages,
                })
            report = json.loads(report_path.read_text(encoding='utf-8'))
            reports.append(report)
            stop_reason = 'running'
            checkpoint()
            print(f'  {report["status"]} in {time.monotonic() - begin:.1f}s', flush=True)
        else:
            stop_reason = 'completed'
    except BaseException:
        stop_reason = 'interrupted'
        raise
    finally:
        checkpoint()
        if os.name == 'nt':
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        print(f'Results: {directory}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=PROJECT_ROOT / 'experiments/configs/vision_overnight.json')
    parser.add_argument('--hours', type=float, default=8)
    parser.add_argument('--document-timeout-seconds', type=int, default=840)
    parser.add_argument('--worker-run', type=Path)
    parser.add_argument('--document-id')
    args = parser.parse_args()
    if args.worker_run:
        worker(args.worker_run, args.document_id)
    else:
        if args.hours <= 0 or args.document_timeout_seconds <= 0:
            parser.error('Time limits must be positive.')
        run_batch(args.config, args.hours, args.document_timeout_seconds)


if __name__ == '__main__':
    main()
