#!/usr/bin/env python3
"""Fixed-work, deterministic CPU scaling benchmark. Python standard library only."""
import csv
import hashlib
import html
import json
import multiprocessing as mp
import os
import platform
import random
import resource
import ssl
import statistics
import sys
import time
from pathlib import Path

_BUFFER = None

def integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer from {minimum} to {maximum}')
    return value

def validate(raw):
    value = raw.get('workers', '1,2,4,8,16')
    if not isinstance(value, str):
        raise ValueError('workers must be a comma-separated string')
    try:
        workers = list(dict.fromkeys(int(x.strip()) for x in value.split(',')))
    except ValueError:
        raise ValueError('workers must be comma-separated integer counts') from None
    for count in workers:
        integer(count, 'worker count', 1, 64)
    if 1 not in workers:
        raise ValueError('Include 1 worker to establish a measured speedup baseline')
    c = {
        'workers': workers,
        'tasks': integer(raw.get('tasks', 64), 'tasks', 1, 2048),
        'iterations': integer(raw.get('iterations', 200000), 'iterations', 1000, 2000000),
        'repeats': integer(raw.get('repeats', 3), 'repeats', 1, 10),
        'memory_mb_per_worker': integer(raw.get('memory_mb_per_worker', 16), 'memory_mb_per_worker', 0, 256),
        'seed': integer(raw.get('seed', 42), 'seed', 0, 2147483647),
    }
    if c['tasks'] < max(workers):
        raise ValueError('tasks must be at least the largest worker count')
    if c['tasks'] * c['iterations'] * c['repeats'] * len(workers) > 1000000000:
        raise ValueError('Workload too large: reduce tasks, iterations, repeats, or worker counts')
    return c

def initialize(memory_mb):
    global _BUFFER
    _BUFFER = bytearray(memory_mb * 1024 * 1024)
    # Explicitly touch each page; allocated memory stays resident for the pool lifetime.
    for i in range(0, len(_BUFFER), 4096):
        _BUFFER[i] = 1

def calculate(arg):
    task_id, iterations, seed = arg
    started = time.process_time()
    digest = hashlib.pbkdf2_hmac('sha256', f'{seed}:{task_id}'.encode(), b'brainlife-cpu-benchmark-v1', iterations).hex()
    cpu = time.process_time() - started
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin':
        rss *= 1024
    return digest, cpu, rss

def run_trial(workers, config):
    tasks = [(i, config['iterations'], config['seed']) for i in range(config['tasks'])]
    start = time.perf_counter()
    with mp.get_context('spawn').Pool(workers, initializer=initialize, initargs=(config['memory_mb_per_worker'],)) as pool:
        results = pool.map(calculate, tasks, chunksize=1)
    wall = time.perf_counter() - start
    checksum = hashlib.sha256(''.join(r[0] for r in results).encode()).hexdigest()
    cpu = sum(r[1] for r in results)
    return {'workers': workers, 'wall_seconds': wall, 'kernel_cpu_seconds': cpu,
            'average_busy_cpu_equivalents': cpu / wall,
            'tasks_per_second': config['tasks'] / wall,
            'max_individual_worker_peak_rss_mib': max(r[2] for r in results) / 1024**2,
            'checksum': checksum}

def read_optional(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None

def environment():
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    return {'python': sys.version, 'openssl': ssl.OPENSSL_VERSION, 'platform': platform.platform(),
            'logical_cpus_visible': os.cpu_count(), 'cpu_affinity': affinity,
            'cgroup_v2_cpu_max': read_optional('/sys/fs/cgroup/cpu.max'),
            'cgroup_v2_memory_max': read_optional('/sys/fs/cgroup/memory.max'),
            'cgroup_v1_cpu_quota_us': read_optional('/sys/fs/cgroup/cpu/cpu.cfs_quota_us'),
            'cgroup_v1_cpu_period_us': read_optional('/sys/fs/cgroup/cpu/cpu.cfs_period_us'),
            'cgroup_v1_memory_limit_bytes': read_optional('/sys/fs/cgroup/memory/memory.limit_in_bytes'),
            'aws_batch_job_id': os.environ.get('AWS_BATCH_JOB_ID'),
            'brainlife_task_id': os.environ.get('AMARETTI_TASK_ID')}

def render_report(result, folder):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'html').mkdir(exist_ok=True)  # report/html datatype's required directory
    (folder / 'html' / 'README.txt').write_text('Open ../index.html for the benchmark report.\n')
    (folder / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    with (folder / 'trials.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(result['trials'][0]))
        writer.writeheader()
        writer.writerows(result['trials'])
    rows = ''.join(f"<tr><td>{r['workers']}</td><td>{r['median_wall_seconds']:.3f}</td><td>{r['min_wall_seconds']:.3f}–{r['max_wall_seconds']:.3f}</td><td>{r['speedup']:.2f}×</td><td>{r['parallel_efficiency']*100:.1f}%</td><td>{r['median_busy_cpu_equivalents']:.2f}</td></tr>" for r in result['summary'])
    bars = ''.join(f"<div class='barrow'><span>{r['workers']} workers</span><div class='bar' style='width:{max(1,90*r['speedup']/max(x['speedup'] for x in result['summary'])):.2f}%'></div><b>{r['speedup']:.2f}×</b></div>" for r in result['summary'])
    body = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CPU Scaling Benchmark</title><style>
body{{font:16px system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;color:#192536;background:#f5f7fa}}h1{{margin-bottom:8px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #dde3eb}}.barrow{{display:flex;align-items:center;gap:12px;margin:12px 0}}.barrow span{{min-width:95px}}.bar{{height:22px;background:#3267ba;border-radius:3px}}pre{{white-space:pre-wrap;background:white;padding:16px}}a{{color:#245eab}}</style></head><body>
<h1>CPU Scaling Benchmark</h1><p>Fixed total work across worker counts. Result consistency: <strong>{'PASS' if result['consistent'] else 'FAIL'}</strong>.</p>
<p><a href="results.json">Download full JSON</a> · <a href="trials.csv">Download trial CSV</a></p>
<h2>Speedup relative to one worker</h2>{bars}
<table><thead><tr><th>Workers</th><th>Median seconds</th><th>Min–max seconds</th><th>Speedup</th><th>Efficiency</th><th>Busy CPU equivalents</th></tr></thead><tbody>{rows}</tbody></table>
<p>Wall time includes process startup, memory initialization, computation and shutdown, but excludes Brainlife/AWS queueing and bootstrap. CPU equivalents count only timed kernel CPU seconds divided by wall seconds. Peak RSS is the largest individual worker measurement, not total job memory.</p>
<p>This synthetic PBKDF2/SHA-256 workload tests independent CPU processes. It is not a prediction of scientific-app performance or a memory-bandwidth benchmark. More workers may slow small workloads. vCPUs can be hardware threads; CPU visibility/affinity may exceed the Batch allocation.</p>
<h2>Configuration</h2><pre>{html.escape(json.dumps(result['config'],indent=2))}</pre><h2>Environment</h2><pre>{html.escape(json.dumps(result['environment'],indent=2))}</pre></body></html>'''
    (folder / 'index.html').write_text(body)

def main():
    config = validate(json.loads(Path('config.json').read_text()))
    trials = []
    rng = random.Random(config['seed'])
    # Warm OpenSSL without consuming a full benchmark workload.
    calculate((0, 1000, config['seed']))
    for repeat in range(config['repeats']):
        order = config['workers'].copy()
        rng.shuffle(order)
        for workers in order:
            print(f'Repeat {repeat+1}/{config["repeats"]}: {workers} workers', flush=True)
            trial = run_trial(workers, config)
            trial['repeat'] = repeat + 1
            trials.append(trial)
            print(f'  {trial["wall_seconds"]:.3f}s, {trial["average_busy_cpu_equivalents"]:.2f} busy CPU equivalents', flush=True)
    baseline = statistics.median(t['wall_seconds'] for t in trials if t['workers'] == 1)
    summary = []
    for workers in sorted(config['workers']):
        group = [t for t in trials if t['workers'] == workers]
        times = [t['wall_seconds'] for t in group]
        median = statistics.median(times)
        summary.append({'workers':workers,'median_wall_seconds':median,'min_wall_seconds':min(times),'max_wall_seconds':max(times),'speedup':baseline/median,'parallel_efficiency':baseline/median/workers,'median_busy_cpu_equivalents':statistics.median(t['average_busy_cpu_equivalents'] for t in group)})
    result = {'schema_version':1,'config':config,'environment':environment(),'trials':trials,'summary':summary,'consistent':len({t['checksum'] for t in trials})==1}
    render_report(result, Path('report'))
    if not result['consistent']:
        raise RuntimeError('Results changed across worker counts/repeats; see report/results.json')
    print('Complete: report/index.html, report/results.json, report/trials.csv', flush=True)

if __name__ == '__main__':
    main()
