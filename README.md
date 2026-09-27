# Testing the claims of a published sensor-fusion system

[FusionCore](https://github.com/manankharwar/fusioncore) is an open-source
ROS 2 package that fuses IMU, wheel encoders, GPS and visual SLAM with a
23-state Unscented Kalman Filter. Its paper
([arXiv:2605.25239](https://arxiv.org/abs/2605.25239)) reports lower
trajectory error than `robot_localization` on ten of twelve sequences of
the NCLT dataset.

I tested three of its claims against its source code and the original
data. Two did not hold, and the failure the filter actually shows is the
reverse of the one the paper describes.

Full report: [`report/report.md`](report/report.md).

## 1. The proposed GPS velocity check has nothing to catch

The paper attributes its worst failure to corrupted GPS fixes slipping
past the filter's statistical outlier gate after a 211 s blackout, and
proposes an implied-speed check to stop them. It justifies this by saying
the offending fix implies about 3,400 m/s.

It implies **3.4 m/s**: 713.8 m over 211.19 s. A speed check cannot reject
it. And the statistical gate had already rejected it at five times its
threshold, along with every other fix in the corrupted cluster.

The check has a structural problem too. Dividing displacement by the time
since the last fix gives a limit that grows with the blackout: a 20 m/s
threshold allows 4.2 km of movement after 211 s.

![Speed check](figures/fig_speedgate.png)

## 2. The real failure: the gate locks out good GPS

The paper worries about a blackout blinding the gate so that it accepts
bad GPS. On this data it does the opposite. Once the filter's estimate
drifts, the gate starts rejecting **good** fixes, the drift grows, and the
gate keeps rejecting.

Every full run I analysed locked out at the same point for around a
thousand consecutive fixes. The rejected fixes were as close to RTK ground
truth as the accepted ones (median 4.8 m against 3.5 m). One run never
recovered, and refused GPS for the last 2,000 seconds of the sequence.

This also explains the few-hundred-metre excursions that inflate every
full-length run: they are what happens when a lockout ends and the
estimate snaps back.

## 3. No evidence the novel state helps

The paper's one new contribution is a 23rd filter state estimating the
wheel encoders' yaw-rate bias. Its evaluation never isolates it: the state
was added in the same step as a change to the test sequences.

I built a switch that freezes that state and changes nothing else, then ran
four matched runs. An untouched baseline filter running alongside agreed to
within 0.8 m across all four, confirming the runs are comparable.

The state didn't improve accuracy in either condition. Freezing it gave
lower error with GPS available (9%) and across a 200 s outage (75%).

![Ablation result](figures/fig_ablation_result.png)

Both differences trace back to the lockouts. In the outage runs, the frozen
arm escaped its lockout after about 450 seconds; the active arm never did.
Escaping is knife-edge, so with one run per configuration this can't show
whether the state *systematically* makes lockouts worse. What it does show
is that the claimed improvement isn't supported.

![Mechanism](figures/fig_ablation_mechanism.png)

## 4. The benchmark harness recorded mostly duplicates

Between 38% and 95% of recorded odometry carried duplicate timestamps, the
data player never exited, and the launch never shut down. I fixed all
three, plus a fourth problem they were hiding. The published error figures
are unaffected, because the evaluation matches poses by timestamp, but
anything based on message counts is not.

![Duplicates](figures/fig_duplicates.png)

## Also found

The paper and its code disagree in four places. The encoder measurement
equation in the paper subtracts the bias; the code adds it. The abstract
describes the bias being subtracted during GPS blackouts; no such code path
exists. The paper attributes a failure to a recovery mode that the benchmark
configuration switches off, with a comment explaining it was disabled for
causing that failure. And the novel state is observable only through GPS,
which the paper does not state.

## Limits

- What starts the lockout, and why the author's runs apparently don't
  suffer it, is not established.
- One sequence for the ablation, one run per configuration. Playback is
  deterministic, so repeats would be identical, but this does not
  generalise beyond that sequence.
- The lockouts inflate my absolute error figures well above the paper's.
  Compare configurations with each other, not with the paper.
- The `robot_localization` baseline scores 5 to 20 times worse on my setup
  than in the paper, for reasons I did not investigate.
- The mechanism behind the duplicate timestamps is not established. The
  measurement and the fix are.

## Contents

| | |
|---|---|
| [`report/`](report/report.md) | The full report |
| [`results/`](results/benchmark_tables.md) | Every number, with the run that produced it |
| [`scripts/`](scripts/README.md) | Analysis and figure scripts, and how to reproduce |
| [`patches/`](patches/) | The code changes to FusionCore |
| Code | [Branch `verification` on my fork](https://github.com/rustamoz/fusioncore/tree/verification), [all changes on one page](https://github.com/rustamoz/fusioncore/compare/99503ca...verification) |

## Credit

FusionCore is by Manan Kharwar, Apache 2.0. The NCLT dataset is from the
University of Michigan (Carlevaris-Bianco, Ushani and Eustice, 2016) and is
released under the Open Database License; none of it is redistributed here.
See [`NOTICE.md`](NOTICE.md).
