<h1 align="center">CPU Scaling Benchmark</h1>

<p align="center">
  Utility that benchmarks CPU scaling of a fixed PBKDF2 SHA-256 workload across configurable worker counts and reports runtime, speedup, CPU utilisation and memory in an HTML report.
</p>

<p align="center">
  <a href="https://github.com/brainlife/abcd-spec"><img src="https://img.shields.io/badge/ABCD_Spec-v1.1-green.svg" alt="ABCD Spec v1.1"></a>
  <a href="https://doi.org/10.25663/brainlife.app.977"><img src="https://img.shields.io/badge/Brainlife-brainlife.app.977-blue.svg" alt="Run on brainlife.io"></a>
</p>

## At a glance

<!-- brainlife-app:begin (generated from the App manifest; edit the manifest, not this block) -->

> **Utility that benchmarks CPU scaling of a fixed PBKDF2 SHA-256 workload across configurable worker counts and reports runtime, speedup, CPU utilisation and memory in an HTML report.**

Runs a fixed number of deterministic work items with Python multiprocessing at each requested worker count, repeating trials in shuffled order, and verifies results while recording wall time, CPU use and memory. Use it to check how many cores a brainlife compute resource effectively provides; it is not a neuroimaging analysis. The T1w input is a required placeholder and is never read.

| | |
|---|---|
| **Inputs** | `neuro/anat/t1w` |
| **Outputs** | `report/html` |
| **Run it** | [doi.org/10.25663/brainlife.app.977](https://doi.org/10.25663/brainlife.app.977) |

#### Inputs

| Input | Datatype | Required | Description |
|---|---|---|---|
| `t1w` | `neuro/anat/t1w` | yes | Required placeholder T1w input for Brainlife app selection. The benchmark does not read or use this image. |

#### Outputs

| Output | Datatype | Description |
|---|---|---|
| `report` | `report/html` | CPU scaling report with downloadable JSON and CSV |

<details>
<summary><b>Parameters</b> (6)</summary>

| Parameter | Type | Default | Description |
|---|---|---|---|
| `workers` | string | `1,2,4,8,16` | Comma-separated worker process counts. Include 1 for baseline. Max 64; values above the resource CPU allocation test oversubscription, not larger instances. |
| `tasks` | number | `64` | Fixed number of independent work items per trial. Must be at least the largest worker count. |
| `iterations` | number | `200000` | PBKDF2 SHA-256 iterations per work item. Increase to reduce process-startup overhead relative to computation. |
| `repeats` | number | `3` | Trials per worker count. Order is shuffled reproducibly each round. |
| `memory_mb_per_worker` | number | `16` | MiB allocated and page-touched per worker. Initialization is included in wall time. Not a memory-bandwidth test. |
| `seed` | number | `42` | Deterministic workload and trial-order seed; use the same seed across comparisons. |

</details>

<!-- brainlife-app:end -->

## Running the App

### On brainlife.io

Open the App at [doi.org/10.25663/brainlife.app.977](https://doi.org/10.25663/brainlife.app.977), choose `neuro/anat/t1w` from your project, set the parameters and press **Execute**. The results are saved to your project as `report/html`.

### Locally

You need [`jq`](https://jqlang.github.io/jq/).

1. Clone this repository.
2. Create `config.json` with the paths to your inputs and the parameters:

   ```json
   {
       "t1": "/path/to/t1w/t1",
       "workers": "1,2,4,8,16",
       "tasks": 64,
       "iterations": 200000,
       "repeats": 3,
       "memory_mb_per_worker": 16,
       "seed": 42
   }
   ```

3. Run `./main`.

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

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Citing

If you use this App, please cite it, the software it builds on and brainlife.io:

- CPU Scaling Benchmark. brainlife.io App. [doi:10.25663/brainlife.app.977](https://doi.org/10.25663/brainlife.app.977)
- Hayashi S, Caron BA, Heinsfeld AS, et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. *Nature Methods* 21:809–813 (2024). [doi:10.1038/s41592-024-02237-2](https://doi.org/10.1038/s41592-024-02237-2)
- Avesani P, McPherson B, Hayashi S, et al. The open diffusion data derivatives, brain data upcycling via integrated publishing of derivatives and reproducible open cloud services. *Scientific Data* 6:69 (2019). [doi:10.1038/s41597-019-0073-y](https://doi.org/10.1038/s41597-019-0073-y)

## Authors

Maintained by [@tjgrafft](https://github.com/tjgrafft).
