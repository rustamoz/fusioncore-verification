# Scripts

## Setup

The analysis runs on Ubuntu 24.04 with ROS 2 Jazzy, using the modified
FusionCore on branch `verification` of
https://github.com/rustamoz/fusioncore.

1. Build FusionCore **including** the datasets package. The upstream build
   command `--packages-up-to fusioncore_ros` omits it:
   ```
   colcon build --packages-up-to fusioncore_ros
   colcon build --packages-select fusioncore_datasets
   ```
2. Download the per-date sensor bundle from
   https://robots.engin.umich.edu/nclt/ (for example
   `2012-01-08_sen.tar.gz`, 114 MB) and unpack it. The LiDAR and image
   bundles are not needed.
3. Install evo: `pip install evo --break-system-packages`

## Producing a run

```
ros2 launch fusioncore_datasets nclt_benchmark.launch.py \
  data_dir:=/path/to/2012-01-08 \
  output_bag:=/path/to/run \
  playback_rate:=3.0
```

Add `gps_outage_start_s:=120.0 gps_outage_duration_s:=200.0` for the
injected blackout. The ablation is switched with
`ukf.encoder_wz_bias_noise_scale` and the pre-gate with
`gnss.max_implied_speed`, both in `config/nclt_fusioncore.yaml`. The
datasets package must be rebuilt after editing that file, since it is read
from the install tree.

On the corrected branch the stack shuts itself down when playback ends.

Extract trajectories and score them with the tools shipped in FusionCore:

```
python3 tools/nclt_rtk_to_tum.py --rtk DATA/gps_rtk.csv --out gt.tum
python3 tools/odom_to_tum.py --bag RUN --topic /fusion/odom --out fc.tum
python3 tools/odom_to_tum.py --bag RUN --topic /rl/odometry --out rl.tum
python3 tools/evaluate.py --gt gt.tum --fusioncore fc.tum --rl rl.tum \
  --sequence 2012-01-08 --out_dir eval
```

## Which script supports which finding

| Finding | Script |
|---|---|
| Build reproduces the author's filter to within 2.6 m | `analysis/trajectory_agreement.py` |
| Paper's implied-speed arithmetic is off by 1000x | `analysis/scan_gps_jumps.py` |
| The adversarial cluster is internally smooth | `analysis/gps_cluster_window.py` |
| Chi-squared gate rejects the corrupted cluster | `analysis/rejection_reasons.py`, `analysis/gnss_status_window.py` |
| Injected outage landed where intended | `analysis/outage_gaps.py` |
| Every run initialised at the origin | `analysis/first_pose.py` |
| Health metrics do not separate the ablation arms | `analysis/filter_health_window.py` |
| Heading and position divergence between arms | `analysis/compare_arms.py` |
| Long-run excursion vs outage re-anchoring | `analysis/largest_jump.py` |
| Duplicate timestamps in recordings | `analysis/dedup.py` |
| The gate locks out: ~1,000 consecutive rejections in every run | `analysis/rejection_episodes.py` |
| Rejected fixes are as accurate as accepted ones | `analysis/fix_vs_truth.py` |
| Sigma grows 55x in a blackout; 46 good fixes rejected after | `analysis/coast_sigma.py` |
| Lockouts follow natural GPS gaps, starting after an accepted fix | `figures/gps_gaps.py` |

Scripts that read bags import `_bag.py` and need a sourced ROS 2
environment with the FusionCore messages built. The rest need only Python.

Every script prints its usage with `--help`.

## Figures

| Figure | Script | Input |
|---|---|---|
| `fig_speedgate.png` | `figures/fig_speedgate.py DATA/2012-08-20/gps.csv` | raw GPS |
| `fig_ablation_result.png` | `figures/fig_ablation.py` | values in the script |
| `fig_duplicates.png` | `figures/fig_duplicates.py` | values in the script |
| `fig_lockout.png`, `fig_fix_accuracy.png`, `fig_blackout.png` | `figures/fig_lockout.py`, `fig_fix_accuracy.py`, `fig_blackout.py` | CSVs from `figures/extract_figdata.py` |

The last three read small CSVs extracted from the bags:

```
python3 extract_figdata.py noout_ON noout_OFF out3_ON out3_OFF blackout_spike_ON \
    --rtk 2012-01-08/gps_rtk.csv --out figdata
```

The CSVs are derived from NCLT and are gitignored.

## Provenance

These scripts consolidate the one-off scripts used during the
investigation, most of which were lost when the VM's `/tmp` was cleared.
The logic is unchanged; paths became arguments.

Every script in `analysis/` has been re-run against the original bags and
data and reproduces the figures in `results/`. Re-running
`trajectory_agreement.py` on the full set of matched timestamps corrected
one figure: the build agrees with the author's trajectory to within
2.60 m (mean 1.09 m), not the 1.9 m first reported from a sample of rows.
