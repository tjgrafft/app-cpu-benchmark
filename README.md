# CPU Scaling Benchmark

A Brainlife app for benchmarking **fixed total work** across CPU worker counts. Designed for the Heavy CPU resource (16 vCPUs / 28 GiB job RAM), but usable on any Python 3 Linux resource.

## Quick start

```bash
cp config.json.example config.json
./main
```

The Brainlife app requires a `neuro/anat/t1w` placeholder input for process-editor compatibility, but the benchmark does not read or use it. Standalone runs need no dataset. No pip packages, AWS credentials, or image pulls are required by the computation. Input staging time is excluded from benchmark measurements. It uses the runner's Python 3 and records Python/OpenSSL/platform versions. It does not execute the Batch bootstrap itself. Brainlife supplies `config.json`, then runs `main`.

## Parameters

| Parameter | Default | Meaning |
|---|---|---|
| `workers` | `1,2,4,8,16` | Comma-separated process counts; must include 1 |
| `tasks` | 64 | Fixed work items per trial; at least the largest worker count |
| `iterations` | 200000 | PBKDF2 SHA-256 iterations per work item |
| `repeats` | 3 | Trials for every worker count |
| `memory_mb_per_worker` | 16 | MiB allocated and touched per worker |
| `seed` | 42 | Workload and execution-order seed |

All numeric parameters must be whole numbers. Whole-number strings from edited Brainlife form fields are normalized automatically. Bounds and a total-work safety limit are enforced. App parameters **do not change the AWS job allocation**. For example, 32 workers on Heavy CPU oversubscribes its 16 vCPUs.

## Suggested experiments

1. Run defaults on Heavy CPU and inspect speedup from 1 to 16 workers.
2. Change workers to `1,2,4,8,16,32` to observe oversubscription.
3. Increase `iterations` to 500000 to amortize startup overhead.
4. Compare 0, 64 and 256 MiB per worker, leaving other settings fixed. This changes memory footprint and startup cost; it is not a memory-bandwidth benchmark.
5. Compare the same configuration on different resources only after administrators enable this app there.

Each trial processes exactly the same tasks using a multiprocessing pool (spawn, chunksize 1). Processes avoid Python's GIL bottleneck. Each task computes deterministic PBKDF2 output; ordered task outputs are hashed into a trial checksum. Every trial must have the same checksum or the app fails. Worker counts are shuffled for each repeat with a seeded RNG to reduce order bias.

## Outputs

`report/index.html` displays median runtime, min/max spread, speedup relative to one worker, parallel efficiency, and average busy CPU equivalents. `report/results.json` contains raw trials, checksums, configuration and environment; `report/trials.csv` provides raw measurements. The `report/html/` directory satisfies Brainlife's `report/html` datatype.

Wall time includes pool startup, memory initialization, computation and pool shutdown. It excludes AWS queueing, instance startup and Brainlife bootstrap. Kernel CPU seconds sum process CPU time spent inside the computational function; dividing by end-to-end wall time estimates average busy CPU equivalents and excludes setup overhead. Peak RSS is the maximum *individual worker* observation, not aggregate or peak job RAM.

Host CPU counts and affinity may exceed a container's Batch allocation; cgroup limits are recorded where exposed. Check the job's actual AWS allocation when interpreting results. vCPUs can be simultaneous hardware threads, so 16 vCPUs does not imply 16 physical cores or 16x speedup. Results depend on hardware, host load, Python/OpenSSL versions, and workload size.

This is a synthetic CPU-throughput benchmark, not a scientific algorithm, GPU benchmark, BLAS/OpenMP threading benchmark, or prediction of an app's output quality. Its exact checksums demonstrate determinism of this workload only.

## Tests

```bash
python3 -m unittest discover -s tests -v
```
