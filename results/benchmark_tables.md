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

### Long-run excursions on the old harness

| Run | Largest single-step jump | Mission time |
|---|---|---|
| 2012-01-08, 3x | 324.1 m | t+3910.9 s |
| 2012-01-08, 1x | 600.5 m | t+4341.8 s |

Consistent with the GPS lockout in section 3 below; these recordings no
longer exist, so that was not confirmed.

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

### Ordinary steps the pre-gate would reject (script: `figures/fig_speedgate.py`)

Of 19,741 fix-to-fix steps under 300 m on 2012-08-20, 30 imply more than
20 m/s (0.15%). With the 823.5 m teleport, a 20 m/s gate would reject 31
fixes on this sequence. Whether the 30 are GPS errors or valid readings
was not determined.

### The corrupted cluster (script: `gps_cluster_window.py`)

234 mode-3 fixes between t+3940 and t+4010 s. Consecutive steps 0.2 to 6.3 m
at intervals of 0.19 to 2.01 s, implied speeds 0.8 to 31.1 m/s.

### Gate decisions on 2012-08-20 (scripts: `rejection_reasons.py`, `gnss_status_window.py`)

| Quantity | Value |
|---|---|
| Fixes accepted | 17,093 |
| Fixes rejected by the chi-squared gate, whole run | 2,862 |
| Fix named by the paper, t+3959.6 s | rejected, d2 = 83.3, threshold 16.27 |
| Window t+3950 to t+3978 s | every fix rejected, d2 71 to 88 (4.4 to 5.4x threshold), in coast mode |
| Position sigma in that window | 63.4 to 68.0 m |
| First fix accepted, t+3978.4 s | d2 = 16.2; sigma 68.01 m to 3.06 m |

### Injected 200 s blackout on 2012-01-08, old harness (script: `coast_sigma.py`)

The injected spike did not land after the blackout (the injector times it
from playback start), so every fix arriving after the outage was genuine.

| Quantity | Value |
|---|---|
| Position sigma before the outage | 1.42 m median |
| Peak position sigma | 78.4 m (78.13 m on the 1 Hz health topic, 78.42 m at the last rejected fix) |
| Growth | about 55x |
| Rejections after the outage | 46, all chi-squared, none by the pre-gate |
| d2 of those rejections | 16.32 to 122.68 (closest 0.3% over the 16.27 threshold) |
| First fix accepted | d2 = 16.26, 0.06% under the threshold |

These 46 were good fixes, so this is a short lockout (section 3 below).

### Injected spike with no preceding blackout

| Configuration | Largest single-step jump |
|---|---|
| Pre-gate off | 1.22 m |
| Pre-gate on | 1.30 m |

The chi-squared gate rejected the same spike at d2 = 46,515 in an earlier run.

## 3. The GPS lockout (report section 5)

Four ablation runs on 2012-01-08, corrected harness.

### Rejection episodes (script: `rejection_episodes.py`)

| Run | Rejected overall | Longest episode | Rejections in it | Peak sigma |
|---|---|---|---|---|
| Active, no outage | 1,361 of 21,981 (6.2%) | t+3494 to 3714 s | 998 | 81.2 m |
| Frozen, no outage | 1,215 of 21,973 (5.5%) | t+3492 to 3712 s | 998 | 68.7 m |
| Active, outage | 7,347 of 21,020 (35.0%) | t+3492 s to end of run | 7,340 | 209.0 m |
| Frozen, outage | 1,352 of 21,023 (6.4%) | t+3493 to 3942 s | 1,115 | 97.5 m |

Episodes shared by all four runs: t+2971 (6 rejections), t+3419 (1),
t+3492 (above), t+4125 (54 to 55), t+5022 (155 to 300; the active arm's
longest). The active outage run has only the first three, because it never
left the t+3492 episode.

### Are the rejected fixes bad? (script: `fix_vs_truth.py`)

Error of each GNSS fix against the nearest RTK ground-truth fix within 1 s.

| Run | Fixes | Matched to RTK | Median error | 90th percentile |
|---|---|---|---|---|
| Active, no outage | accepted | 18,975 / 20,620 | 3.5 m | 10.5 m |
| | rejected, whole run | 1,063 / 1,361 | 4.3 m | 8.3 m |
| | rejected, t+3494 to 3714 s | 762 / 998 | 4.8 m | 8.2 m |
| Active, outage | accepted | 12,676 / 13,673 | 4.0 m | 12.8 m |
| | rejected, whole run | 6,408 / 7,347 | 3.2 m | 7.1 m |

The rejected fixes are ordinary GPS, within a few metres of the truth:
slightly worse than accepted fixes at the median in one run, better in the
other, and better at the 90th percentile in both. The corrupted fixes on
2012-08-20 were about 700 m off. The gate was rejecting good GPS.

### Natural GPS gaps and what follows them (script: `figures/gps_gaps.py`)

Gaps longer than 10 s between fixes. Two gaps are interrupted by a single
rejected fix (at t+3421 and t+3714 s) and are listed merged. Times from the
active no-outage run; the other runs agree to within 2 s.

| Gap | Length | Sigma on return | What happens next |
|---|---|---|---|
| t+2974 to 3138 s | 165 s | 59.7 to 61.5 m | first fix accepted in all runs, no lockout |
| t+3382 to 3494 s | 112 s | 42.2 to 44.7 m | first fix accepted in all runs, then the ~1,000-fix lockout |
| t+3700 to 3917 s | 217 s | 95.4 to 105.3 m | no-outage runs: first fix accepted. Frozen outage: 117 rejected, accepted after 25.6 s. Active outage: never accepted |
| t+4928 to 5021 s | 93 s | 39.0 to 40.3 m | first fix accepted, then 155 to 300 rejections (active outage run still locked out, sigma 183.4 m) |

The injected 200 s outage in the outage runs (t+106 to 306 s) ended with the
first fix accepted and no rejections, unlike the same outage on the old
harness in section 2 above, which was followed by 46.

## 4. Claim two: the 23rd state (report section 4)

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

### Trajectory shape

| Run | Path length ratio | RPE at 10 m | Drift |
|---|---|---|---|
| No outage, active | 1.0024 | 26.511 m | 9.11 m/km |
| No outage, frozen | 0.9974 | 25.362 m | 8.32 m/km |
| Outage, active | **0.8757** | 20.077 m | 40.36 m/km |
| Outage, frozen | 1.0152 | 26.894 m | 10.29 m/km |

### Largest single-step jumps (script: `largest_jump.py`)

| Run | Jump | Time | Attribution |
|---|---|---|---|
| No outage, active | 373.1 m | t+3917 s | about 200 s after the lockout's last rejection |
| No outage, frozen | 343.1 m | t+3916 s | about 200 s after the lockout's last rejection |
| Outage, active | 187.3 m | t+306 s | re-anchoring after the injected outage; never left the later lockout |
| Outage, frozen | 387.0 m | t+3942 s | end of the lockout, same second |

The re-anchoring jump at about t+306 s occurs in both outage arms
(`compare_arms.py`); after it they agree to 0.7 m.

## 5. Harness defects (report section 6)

### Duplicate timestamps in recorded odometry (script: `dedup.py`)

| Recording | Poses | Unique | Duplicate |
|---|---|---|---|
| 2012-01-08, 3x | 202,659 | 126,658 | 37.5% |
| 2012-01-08, 1x | 939,242 | 432,262 | 54.0% |
| 2012-08-20 | 558,396 | 117,813 | 78.9% |
| Ablation, first attempt | 242,195 | 11,995 | 95.0% |
| 60 s slice, after the shutdown fixes | 1,671 | 1,054 | 36.9% |
| 60 s slice, after the publish check | 1,234 | 1,234 | 0.0% |

After the shutdown fixes the stack exits on its own, 41 s after launch for
the 60 s slice.

Re-scoring earlier runs from de-duplicated trajectories reproduced every
ATE to three decimal places (64.719, 149.913, 30.330 m).

## Superseded results

Kept for the record; not used in the report.

| Result | Why superseded |
|---|---|
| First ablation pair: 56.446 m vs 86.832 m | RL-EKF control differed tenfold between arms; runs not comparable |
| Second ablation pair (old harness): 73.948 m vs 65.832 m | Replaced by the four-run set on the corrected harness |
| 2012-01-08 at 1.5x: 448.468 m | Bag written without a message index; trajectory scrambled |
| Injected blackout: sigma 77.5 m, d2 16.3 to 18.3 | Read from a partial window; replaced by full extraction above |
