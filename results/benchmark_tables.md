# Results

Every number reported, with the run that produced it. Sequences are from
the NCLT dataset. ATE is RMSE after SE(3) alignment to RTK ground truth,
computed with `tools/evaluate.py` from the FusionCore repository (which
uses evo). All FusionCore runs used 3x playback unless stated.

## 1. Baseline reproduction (report section 2)

### 2012-01-08, full sequence

| Run | FusionCore ATE 3D | RL-EKF ATE 3D |
|---|---|---|
| Author, published (`results_full/BENCHMARK.md`) | 18.625 m | 41.189 m |
| Mine, first run | 61.087 m | 251.364 m |
| Mine, repeat | 64.719 m | 253.534 m |
| Mine, 1x playback | 149.913 m | 254.982 m |

### Build validation against the author's own output

| Check | Result |
|---|---|
| Author's `fusioncore_spike.tum` scored through my pipeline | 4.253 m ATE 3D, 73.8% of poses within 5 m |
| My spike-test output vs the author's, matched timestamps | 2,792 |
| Pose-by-pose disagreement over the whole run | 0.0 to 1.9 m |
| My ground truth vs the author's shipped ground truth | identical to 6 d.p.; 11,679 vs 11,754 poses (75 outliers above 30 m/s removed by my converter) |

### Unexplained long-run excursion

| Run | Largest single-step jump | Mission time |
|---|---|---|
| 2012-01-08, 3x | 324.1 m | t+3910.9 s |
| 2012-01-08, 1x | 600.5 m | t+4341.8 s |

## 2. Claim one: the velocity pre-gate (report section 3)

### 2012-08-20, full sequence

| Run | FusionCore ATE 3D | RL-EKF ATE 3D |
|---|---|---|
| Author, published | 98.314 m | 10.553 m |
| Mine, baseline | 30.330 m | 216.465 m |

### Large GPS steps in the raw `gps.csv` (script: `scan_gps_jumps.py`)

| Mission time | Step | Elapsed | Implied speed |
|---|---|---|---|
| t+3959.6 s | 713.8 m | 211.19 s | **3.4 m/s** (paper states ~3400) |
| t+3984.2 s | 823.5 m | 0.40 s | 2051.4 m/s |
| t+4352.4 s | 324.0 m | 36.00 s | 9.0 m/s |

### The adversarial cluster (script: `gps_cluster_window.py`)

234 mode-3 fixes between t+3940 and t+4010 s. Consecutive steps 0.2 to 6.3 m
at intervals of 0.19 to 2.01 s, implied speeds 0.8 to 31.1 m/s.

### Gate decisions on 2012-08-20 (script: `rejection_reasons.py`, `gnss_status_window.py`)

| Quantity | Value |
|---|---|
| Fixes accepted | 17,093 |
| Fixes rejected by the chi-squared gate | 2,862 |
| Fix named by the paper, t+3959.6 s | rejected, d2 = 83.3, threshold 16.27 |
| Window t+3950 to t+3978 s | every fix rejected, d2 71 to 88, in coast mode |
| Position sigma in that window | 63.4 to 68.0 m |
| First fix accepted, t+3978.4 s | d2 = 16.2; sigma 68.01 m to 3.06 m |

### Ordinary steps the pre-gate would reject (script: `figures/fig_speedgate.py`)

Of 19,741 fix-to-fix steps under 300 m on 2012-08-20, 30 imply more than
20 m/s (0.15%). With the 823.5 m teleport, a 20 m/s gate would reject 31
fixes on this sequence. Whether the 30 are GPS errors or valid readings
was not determined.

### Injected blackout, 200 s, on 2012-01-08

| Quantity | Value |
|---|---|
| Position sigma, nominal | 2 to 3 m |
| Position sigma, peak during coast | 77.5 m * |
| d2 of rejected fixes during coast | 16.3 to 18.3 |
| Rejections | 46 chi-squared, 0 pre-gate; 777 accepted |

\* The recorded peak and the value just before re-acquisition (78.42 m)
disagree slightly. To be confirmed by re-extracting from the bag before
the report is final.

### Injected spike with no preceding blackout

| Configuration | Largest single-step jump |
|---|---|
| Pre-gate off | 1.22 m |
| Pre-gate on | 1.30 m |

The chi-squared gate rejected the same spike at d2 = 46,515 in an earlier run.

## 3. Claim two: the 23rd state (report section 4)

Four runs of 2012-01-08 on the corrected harness, differing only in
`ukf.encoder_wz_bias_noise_scale` and the presence of an injected
200 s GPS outage from t=120 s.

### ATE

| | Active (1.0) | Frozen (0.0) |
|---|---|---|
| No outage | 66.504 m | 60.723 m |
| 200 s outage | 294.611 m | 75.123 m |

### Control: RL-EKF, untouched by the ablation

| Run | RL-EKF ATE 3D |
|---|---|
| No outage, active | 254.445 m |
| No outage, frozen | 253.812 m |
| Outage, active | 254.599 m |
| Outage, frozen | 254.557 m |

Spread 0.787 m on a 253.8 m baseline.

### Mechanism

| Run | Path length ratio | RPE at 10 m | Drift |
|---|---|---|---|
| No outage, active | 1.0024 | 26.511 m | 9.11 m/km |
| No outage, frozen | 0.9974 | 25.362 m | 8.32 m/km |
| Outage, active | **0.8757** | 20.077 m | 40.36 m/km |
| Outage, frozen | 1.0152 | 26.894 m | 10.29 m/km |

### Largest single-step jumps (script: `largest_jump.py`)

| Run | Jump | Time | Attribution |
|---|---|---|---|
| No outage, active | 373.1 m | t+3917 s | long-run excursion |
| No outage, frozen | 343.1 m | t+3916 s | long-run excursion |
| Outage, active | 187.3 m | t+306 s | GPS re-anchoring after outage |
| Outage, frozen | 387.0 m | t+3942 s | long-run excursion |

The re-anchoring jump at t+306 s occurs in both outage arms
(`compare_arms.py`); after it they agree to 0.7 m.

## 4. Harness defects (report section 5)

### Duplicate timestamps in recorded odometry (script: `dedup.py`)

| Recording | Poses | Unique | Duplicate |
|---|---|---|---|
| 2012-01-08, 3x | 202,659 | 126,658 | 37.5% |
| 2012-01-08, 1x | 939,242 | 432,262 | 54.0% |
| 2012-08-20 | 558,396 | 117,813 | 78.9% |
| Ablation, first attempt | 242,195 | 11,995 | 95.0% |
| 60 s slice, before fix | 1,671 | 1,054 | 36.9% |
| 60 s slice, after fix | 1,234 | 1,234 | 0.0% |

After the fix the stack exits on its own, 41 s after launch for the 60 s slice.

Re-scoring earlier runs from de-duplicated trajectories reproduced every
ATE to three decimal places (64.719, 149.913, 30.330 m).

## Superseded results

Kept for the record; not used in the report.

| Result | Why superseded |
|---|---|
| First ablation pair: 56.446 m vs 86.832 m | RL-EKF control differed tenfold between arms; runs not comparable |
| Second ablation pair (old harness): 73.948 m vs 65.832 m | Replaced by the four-run set on the corrected harness |
| 2012-01-08 at 1.5x: 448.468 m | Bag written without a message index; trajectory scrambled |
