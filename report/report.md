# Testing the Claims of a Published Sensor-Fusion System

## 1. Introduction

FusionCore is an open-source ROS 2 package released in May 2026 by M. Kharwar [1], [2]. It combines IMU, wheel encoder, GPS and visual SLAM data into one 100 Hz odometry stream using a 23-state Unscented Kalman Filter (UKF) [5]. Kharwar benchmarks it against `robot_localization` [4], *the* standard ROS package for this job, across twelve full-length sequences of the University of Michigan NCLT dataset [3], and reports a lower absolute trajectory error on 10 of the 12.

I chose this paper as a project anchor because it makes concrete claims that can be checked. The paper is honest about its worst failure, and proposes a specific fix in its future-work section backed by an arithmetic justification. It also introduces a novel 23rd state and claims that it improves performance, but never isolates it to test that.

So instead of simply reproducing the author's benchmark, I decided to test three specific claims:

1. That a velocity-consistency pre-gate would fix the author's documented failure on the 2012-08-20 sequence.
2. That the 23rd state *actually* improves performance.
3. That the paper's account of the failure mechanism is right: that covariance growth during a GPS blackout blinds the filter's statistical outlier gate, which then accepts corrupted fixes.

I implemented the proposed changes and wrote the unit tests that were missing from the repository. I then tested each claim against the source code and the original dataset.

Two out of three claims did not survive, and the failure the filter actually shows on this data is the reverse of the one the paper describes.

## 2. Establishing a Baseline

Nothing further counts if the build is wrong, so this came first. It ended up taking longer than I initially thought.

I built the system on an ARM64 Ubuntu 24.04 VM under UTM on an Apple Silicon Mac, running ROS 2 Jazzy. The benchmark harness ships with the repo: a data player that reads the raw NCLT CSVs, a launch file that runs FusionCore and both `robot_localization` filters at once against identical sensor streams, and scripts to score the output with the EVO toolbox [6].

The first obstacle came before anything ran: the program wouldn't start. The `fusioncore_datasets` package that holds the harness isn't included by the build command the project documents, so `ros2 launch` couldn't find it. Building that package on its own fixed it, but the benchmark path had been unavailable until then.

My first full-length run on the 2012-01-08 sequence took around 35 minutes at 3× playback, the same rate the author used. It scored 61.1 m of absolute trajectory error. The figure published by the author is 18.6 m.

The `robot_localization` baseline was off by a similar factor, 251 m against 41 m. Since that filter is separate from FusionCore and I hadn't altered it, the problem had to be somewhere upstream of both.

I had four explanations in mind:

1. **Playback rate.** I knew timing affects this filter. But the author's own launch log, shipped with the repo, records `rate=3.0x`, the same as mine.
2. **GPS conversion.** NCLT stores latitude and longitude in radians, and getting that wrong would affect every position. I read the loader in the data player and it converts correctly with `math.degrees`, reading the right columns.
3. **Ground truth.** I generate mine from `gps_rtk.csv` with a repository script; the author ships his. I diffed them. They were identical to six decimal places, with a 75-pose difference that turned out to be outlier fixes my converter rejects above 30 m/s.
4. **FusionCore's covariance handling.** I expected this one to be right. FusionCore's covariance handling is numerically delicate, with an explicit repair path for lost positive-definiteness. I'm on ARM64 while the author was likely building on x86, and different rounding could plausibly tip a borderline matrix. I captured a full run log and searched it for Cholesky failures, NaN, singularity warnings and so on. It came out clean, with no numerical errors of any kind.

That exhausted my hypotheses, so rather than keep guessing I ran a direct comparison.

The repo ships the author's own filter output for a GPS-spike test on this sequence. Scoring his trajectory through my evaluation pipeline gave 4.25 m, with 73.8% of poses inside 5 m. My evaluator, my ground truth and my extraction scripts were therefore all fine. I then ran the identical spike test on my own build and compared the two trajectories pose by pose across 2,792 matched timestamps.

They agreed to within 2.6 m for the entire run, and to 1.1 m on average, including through a deliberately injected 500 m GPS spike.

My build reproduces the author's filter.

What's left is limited to long runs and has a specific shape. Every full-length run develops one or two isolated excursions of a few hundred metres: 324 m at t+3911 s at 3× playback, and 600 m at t+4342 s when I re-ran at 1×. They're reproducible in the sense that they always happen, but the timestamp and the size move between runs, and they occur while GPS is present and reporting normal covariance. I couldn't explain them at this stage. They turned out to matter more than anything else in the project, and §5 shows what's behind them.

That result changed how I ran everything afterwards. Full 90-minute sequences are contaminated as a primary metric on this hardware, but the repo includes injectors for GPS spikes and outages, and I'd just validated short runs against the author's own output to within 3 m. So injected-fault experiments became the main evidence, with full sequences kept as supporting material. A self-injected fault is known, repeatable and isolated, which makes it much easier to defend than an aggregate number over 90 minutes.

## 3. Claim One: The Velocity Pre-Gate

The paper's second loss is on the 2012-08-20 sequence, where FusionCore scores 98.3 m against `robot_localization`'s 10.6 m. Section VII-E of the paper [1] diagnoses it in detail. After a 211-second GPS blackout, a cluster of 105 corrupted fixes arrives, each landing 720 to 840 m from the true position. The author argues that the filter's covariance has grown so large during the blackout that its chi-squared outlier gate no longer finds them surprising, so it accepts them, and together they drag the position estimate 788 m off course.

The proposed fix appears in Section IX of the paper: check the implied speed before the statistical gate runs. A fix 720 m from the dead-reckoned position after a 211-second blackout implies roughly 3400 m/s of travel, which is of course impossible for a Segway that moves at 1.5 m/s. The paper describes this as having "zero effect on normal GPS operation," and the reasoning makes sense: a physics limit can't be fooled by uncertainty the way a statistical test can.

*I decided to implement it.* The changes to the code are pretty limited and live in four places:

- a new `SPEED_IMPLAUSIBLE` value in the rejection-reason enum
- a `gnss_max_implied_speed` configuration parameter, set to 20 m/s for my experiments (it defaults to off, so the modified code behaves like upstream unless someone enables it)
- the ROS parameter plumbing to expose it in the YAML
- the check itself, in `update_gnss()`

Placement mattered more than the arithmetic. The check goes immediately after the existing quality gate and before the branch that separates delayed from on-time measurements, because that's the single point both paths cross. It also has another useful property. The reference position it measures against, `last_gnss_x_` and `last_gnss_y_`, only advances when a fix is accepted, since the code that updates it runs after a successful filter update. Reject the first fix of a bad cluster and the reference stays anchored where it was, so the next fix is still measured against the old position and gets rejected too. One rejection then cascades through the whole burst without any cluster-detection logic.

Two unit tests cover it: a fix implying 3500 m/s must be rejected with the new reason, and one implying 1.5 m/s must not be. Both pass.

I then ran the baseline on 2012-08-20 to reproduce the failure I was supposed to be fixing.

It didn't reproduce. FusionCore scored 30.3 m, not 98.3 m, and `robot_localization` scored 216 m against the paper's 10.6 m. FusionCore beat it by 86%. The loss the whole contribution targets wasn't there.

The per-pose error profile did match, though, which confirmed the sequences line up. The paper describes a spike to about 100 m at around 42 minutes at the first blackout, a return to normal, then a larger spike at 62 minutes where the adversarial cluster arrives. My run shows both at the right times: a spike to 150 m at t≈2500 s and a second to 280 m at t≈3700 s.

So the spikes exist in my run too. But before spending another 35 minutes on a re-run with the gate enabled, I went to the raw GPS file to see exactly what the offending fixes look like, and that's where the paper's argument comes apart.

I scanned `gps.csv` for consecutive quality-3 fixes more than 300 m apart and computed the implied speed for each. The fix that arrives at the end of the blackout, at mission time t+3959.6 s, is 713.8 m from the previous fix. The gap since that fix is 211.19 seconds.

713.8 ÷ 211.19 = 3.4 m/s

Not 3400. The paper is off by a factor of a thousand, which is what you get from dividing by 0.211 seconds instead of 211. At 3.4 m/s the fix passes a 20 m/s threshold easily.

![Log-log scatter of every GPS fix-to-fix step on 2012-08-20, elapsed time against displacement, with a diagonal line for a 20 m/s speed threshold. The fix arriving after the 211-second blackout sits below the line; a genuine 823 m jump in 0.4 s sits far above it.](../figures/fig_speedgate.png)

*Figure 1. A displacement-over-elapsed-time check cannot reject the fix that arrives after the 211-second blackout: it implies 3.4 m/s, well under a 20 m/s threshold. Because the limit grows with the gap, it permits 4.2 km of movement after 211 seconds.*

I then looked at the rest of the cluster to see whether later fixes might still be catchable. Between t+3940 s and t+4010 s there are 234 quality-3 fixes. Step to step they move 0.2 to 6.3 m at intervals of about 0.2 s, giving implied speeds between 0.8 and 31 m/s. The cluster sits 700 m from the truth as a block, but looked at internally it's an ordinary GPS stream from a vehicle driving normally. In the whole window only one transition exceeds the threshold: an 823 m jump in 0.4 s at t+3984 s, which works out to 2051 m/s.

This points at something structural. A check of the form "displacement ÷ time since the last fix" has a denominator that grows with the length of the blackout. After 211 seconds, a 20 m/s limit permits a displacement of up to about 4.2 km. The check goes blind after long outages for exactly the same reason the chi-squared gate is said to. So this formulation of a physics check goes blind too.

The check isn't harmless on ordinary GPS either. Of the 19,741 normal fix-to-fix steps on 2012-08-20, 30 imply more than 20 m/s, so a 20 m/s gate would throw away 30 fixes from normal driving alongside the one real teleport. Whether those 30 are GPS errors or valid readings I didn't determine.

The injected-fault tests showed the same thing from the other direction. A 500 m spike at t=120 s with no preceding blackout produced the same trajectories with the gate on and off: a maximum single-step jump of 1.22 m against 1.30 m. The debug topic showed my gate fired first and caught the spike before the chi-squared gate ran, but in an earlier run of the same test the chi-squared gate had rejected it on its own, with a Mahalanobis distance of 46,515 against a threshold of 16.27. With the covariance small, the existing gate isn't blinded and mine has nothing to add.

The test that actually mattered was a long blackout, since that's the condition the paper describes. I injected a 200-second outage from t=100 s. I also scheduled a spike for one second after GPS returned, but the injector times it from playback start and it didn't land in that window, so what this test actually measured was the gate after a long blackout. The covariance inflation is real and large: position sigma climbed from a median of 1.4 m before the outage to 78.4 m by the end of it, about 55 times larger.

What happened next I misread at first. With no spike in the data, every fix arriving after the outage was genuine, and the chi-squared gate rejected the first 46 of them anyway, with Mahalanobis distances from 16.32 up to 122.7. None were rejected by my pre-gate. The filter had drifted during the outage, so correct fixes looked like outliers. It only accepted one when a fix scored 16.26, just under the 16.27 threshold. I took this as the gate holding up. It's actually a short version of the failure in §5: the gate refusing good GPS after a gap.

![Filter position uncertainty rising steadily through a 200-second injected GPS blackout, with the Mahalanobis distance of each GPS fix on a second axis. After the blackout a cluster of rejected fixes sits just above the gate threshold until one falls below it.](../figures/fig_blackout.png)

*Figure 2. During a 200-second injected blackout the filter's position uncertainty grows from 1.4 m to 78.4 m. When GPS returns, the gate rejects 46 genuine fixes before one scores 16.26 against the 16.27 threshold.*

The last test settled it. I re-ran the full 2012-08-20 sequence with the debug topics recorded, which capture the rejection reason and Mahalanobis distance for every single fix. Across the run:

- 17,093 fixes accepted
- 2,862 rejected by the chi-squared gate

In the window from t+3950 s to t+3978 s, every fix was rejected, continuously, with the filter in coast mode and position sigma between 63 and 68 m. The specific fix the paper names, at t+3959.6 s, was rejected with a Mahalanobis distance of **83.3** against a threshold of 16.27. Five times over. At t+3978.4 s one fix finally passed at 16.2, just under the line, and sigma collapsed from 68.0 m to 3.06 m in a single update.

The gate rejected the entire adversarial cluster, including the fix the paper singles out.

That leaves the excursion in the error profile needing a different explanation, and the data supplies one. The error climbs from t≈3700 s, peaks near 280 m, and drops sharply at the first accepted fix. That interval covers the blackout and the rejected cluster after it. The filter isn't being pulled off course by bad GPS. It's dead-reckoning on wheels and IMU for nearly four minutes with GPS correctly refused throughout, and drifting, which is what dead-reckoning does.

So no GPS gate can fix it, because the GPS is already being thrown away. The pre-gate is implemented, tested, and has no target on the sequence it was designed for.

## 4. Claim Two: The 23rd State

The paper's novelty is a single number, which the author describes as the 23rd state. Alongside the usual gyroscope and accelerometer biases, the 23rd state, `b_ewz`, estimates the wheel encoder's systematic yaw-rate error. On a differential-drive robot this comes from wheel radius mismatch and mechanical asymmetry, and it's close to constant. The filter identifies it from GPS heading while GPS is available, and the paper argues this reduces heading drift during blackouts.

All the other states are pretty standard and established practice, and the author implements them carefully. This one state is the paper's claim to novelty, and it's the one thing the evaluation never isolates. The author added it and changed the set of evaluation sequences in the same step, so the reported improvement has two candidate causes and no way to separate them.

Running the controlled version needed a switch, which wasn't in the codebase.

Finding where in the code to put the switch proved more difficult than I expected. My assumption was that `b_ewz` was grown and applied somewhere in the motion model, but it wasn't. *The identifier doesn't appear in `motion_model.cpp` at all.* The predict step copies index 22 through untouched, which is correct for a random-walk bias, since its predicted mean is its current value. What lets the state move is a single scalar in `ukf.cpp`: the process-noise entry `q_encoder_wz_bias`, which sets how much variance it accumulates each step. Kill that and the state can never adapt, because measurements have no uncertainty to work against.

The author had already built this mechanism twice, for position and for gyro bias, as runtime multipliers on the process noise inside `predict()`. So the lever is three lines mirroring a pattern already in the file, plus a setter, a member and configuration plumbing. Setting the scale to zero freezes `b_ewz` at its initialised value of zero, which makes its term in the encoder measurement inert. `STATE_DIM` stays at 23, the sigma point count stays at 47, and every matrix keeps its shape. The only thing that changes is whether the 23rd state can adapt.

When I read the encoder measurement function to confirm the term goes inert, something interesting came up. The code computes `z[2] = x[WZ] + x[B_EWZ]`, adding the bias, while the paper's equation 13 subtracts it. I cover that and three other documentation defects in §7.

No test in the repo validates the 23rd state. Both encoder measurement tests leave `b_ewz` at zero, so the term is never observed with a value. The magnetometer feature added in version 0.3.1 got twelve new tests; the paper's headline contribution has none. I wrote two: one setting `b_ewz` to 0.05 with a yaw rate of 0.40 and asserting the measurement comes out at 0.45 rather than 0.35, pinning the sign convention against equation 13, and one confirming the lever freezes the state's variance while leaving `STATE_DIM` at 23.

### The experiment

I ran four runs on 2012-01-08 at 3× playback, all on the corrected harness from §6. They form a two-by-two: the 23rd state active or frozen, crossed with a 200-second GPS outage injected at t=120 s, present or absent. Nothing else changed between them.

The `robot_localization` EKF runs alongside FusionCore in every run and the ablation doesn't touch it, so it works as a control. Across the four runs it scored 253.8, 254.4, 254.6 and 254.6 m, a spread of 0.8 m on a 254 m baseline. The runs are comparable.

| | 23rd state active | 23rd state frozen |
|---|---|---|
| No outage | 66.5 m | 60.7 m |
| 200 s outage | 294.6 m | 75.1 m |

![Grouped bar chart of trajectory error for the 23rd state active and frozen, with and without a 200-second outage, and a shaded band showing the untouched control filter at 253.8 to 254.6 m.](../figures/fig_ablation_result.png)

*Figure 3. Freezing the 23rd state gave lower trajectory error with and without an outage: 60.7 m against 66.5 m, and 75.1 m against 294.6 m. The untouched `robot_localization` control scored within 0.8 m across all four runs, so the runs are comparable.*

Freezing the state gave a lower error in both conditions: 9% lower without an outage and 75% lower with one.

The second number is big enough to be suspicious, so I checked what produced it before reporting it. My first two explanations failed against the data:

1. **A wrongly converged bias corrupting encoder measurements during the outage.** If that were happening, the filter's health diagnostics should show it. They don't. Encoder innovation norm, heading sigma and position sigma are indistinguishable between the two arms for the whole outage.
2. **The active arm mishandling the moment GPS returns.** Both arms make the same ~190 m re-anchoring jump within two seconds of the outage ending, and agree to within 0.7 m straight after. That's normal behaviour after coasting, not a failure of one arm.

The shape of the trajectory showed what the damage looked like:

| Run | Path length ratio | RPE at 10 m | Drift rate |
|---|---|---|---|
| Active, outage | **0.876** | 20.1 m | 40.4 m/km |
| Frozen, outage | 1.015 | 26.9 m | 10.3 m/km |
| Active, no outage | 1.002 | 26.5 m | 9.1 m/km |
| Frozen, no outage | 0.997 | 25.4 m | 8.3 m/km |

Three runs get the total path length to within about 1.5% of the truth. The active arm with an outage comes up **12% short**. Its relative pose error over 10 m segments is the lowest of the four, so the problem isn't local. It's the accumulated distance that's wrong, and the drift rate is four times the others.

That's also why the per-pose error plot for that run looks so much worse. SE(3) alignment can rotate and shift a trajectory but not rescale it, so there's no good fit for a path that's 12% short. The alignment compromises and spreads the mismatch across the whole run, putting hundreds of metres of error even on stretches where the filter was doing no worse than the others.

That describes the damage but not where it came from. The cause turned out to be the GPS gate, and it's the subject of §5. In short: every run locks out of GPS at the same point, just after a natural GPS gap in the data around t≈3492 s, and every run is still locked out when a longer natural gap begins at t+3700 s. When GPS returns after that gap, the frozen arm gets a fix accepted within 26 seconds. The active arm never does, and spends the last 2,000 seconds of the run refusing GPS. That's where the 294.6 m comes from. Not from the injected outage at t=120 s, which both arms came through cleanly, but from a lockout more than 3,000 seconds later. The gap without an outage follows the same pattern: after the last natural gap, at t≈5022 s, the active arm's lockout lasted 300 rejections against the frozen arm's 155.

During the injected outage itself, the two arms' headings drifted about 37° apart, then came back together once GPS returned. Whatever lasting difference the outage left between them, it was small enough that their positions agreed to within 0.7 m straight afterwards.

### What this establishes

The 23rd state didn't improve accuracy in either condition I tested. In one configuration, the filter with it active entered a GPS lockout and never recovered, while the identical filter with it frozen recovered after about 450 seconds.

What I can't establish is whether that's systematic. Escaping a lockout is a knife-edge event, decided by whether a single fix scores just under the threshold, and with one run per configuration I can't tell whether the 23rd state makes escape harder or just happened to nudge this run onto the wrong side of the edge. Settling it would need many runs under slightly different conditions, such as other outage timings or other sequences. So the paper's claim that the 23rd state helps isn't supported by these runs, but the stronger claim that it hurts isn't established either.

## 5. What Actually Happens: The Gate Locks Out Good GPS

While rechecking the figures in §3 against the filter's per-fix debug output, I grouped consecutive chi-squared rejections into episodes for each of the four ablation runs. The same pattern turned up in all of them.

| Run | Rejected overall | Longest episode | Rejections in it | Peak sigma | Largest jump |
|---|---|---|---|---|---|
| Active, no outage | 1,361 (6.2%) | t+3494 to 3714 s | 998 | 81.2 m | 373 m at t+3917 s |
| Frozen, no outage | 1,215 (5.5%) | t+3492 to 3712 s | 998 | 68.7 m | 343 m at t+3916 s |
| Active, outage | 7,347 (35.0%) | t+3492 s to end | 7,340 | 209.0 m | never recovered |
| Frozen, outage | 1,352 (6.4%) | t+3493 to 3942 s | 1,115 | 97.5 m | 387 m at t+3942 s |

Every run starts rejecting at the same point, t+3492–3494 s, so this is a property of the sequence and the filter, not of the ablation. Smaller episodes at t≈4125 s and t≈5022 s also appear in all four.

The obvious question is whether those fixes were bad. I checked every fix against the RTK ground truth:

| Run | Fixes | Median error against RTK | 90th percentile |
|---|---|---|---|
| Active, no outage | accepted | 3.5 m | 10.5 m |
| | rejected, whole run | 4.3 m | 8.3 m |
| | rejected, t+3494 to 3714 s | 4.8 m | 8.2 m |
| Active, outage | accepted | 4.0 m | 12.8 m |
| | rejected, whole run | 3.2 m | 7.1 m |

![Two cumulative distribution plots of each GPS fix's error against RTK ground truth, split into fixes the gate accepted and fixes it rejected. The accepted and rejected curves lie close together in both runs.](../figures/fig_fix_accuracy.png)

*Figure 4. The fixes the gate rejected were ordinary GPS, within a few metres of RTK ground truth, much like the ones it accepted. For scale, the corrupted fixes on 2012-08-20 were about 700 m off.*

The rejected fixes were ordinary GPS, within a few metres of the truth. At the median they're slightly worse than the accepted ones in one run and better in the other, and at the 90th percentile they're better in both. For comparison, the corrupted fixes on 2012-08-20 were about 700 m off. The gate was throwing away good GPS.

### Where the lockouts come from

Plotting the runs over time showed something the tables hadn't. 2012-01-08 has natural GPS gaps of its own, stretches where the receiver produced no usable fixes, and they're identical in every run:

| Natural gap | Length | Sigma when GPS returns | What happens next |
|---|---|---|---|
| t+2974 to 3138 s | 165 s | about 60 m | first fix accepted, no lockout |
| t+3382 to 3494 s | 112 s | about 43 m | first fix accepted, then about 1,000 rejections |
| t+3700 to 3917 s | 217 s | 95–105 m | depends on the run, below |
| t+4928 to 5021 s | 93 s | about 40 m | first fix accepted, then 155–300 rejections |

![Four stacked timelines, one per ablation run, showing filter position uncertainty on a log scale, rejected GPS fixes as red marks, and natural GPS gaps as grey bands. All four runs start rejecting fixes at the same moment; in one, the rejections continue to the end of the run.](../figures/fig_lockout.png)

*Figure 5. Every run locks out of GPS just after the same natural gap in the data, ending at t+3492–3494 s. Three runs re-acquire GPS after the next gap. The active run with an outage never does, and rejects the last 7,340 fixes of the run.*

Two things stand out. Gap length doesn't decide it: the 165-second gap caused no lockout, while the 112-second one caused the longest. And the lockout doesn't start when GPS comes back. The first fix after the gap is accepted, the filter's uncertainty collapses to a few metres, and within a second the gate starts rejecting the fixes that follow. My best guess is that a single position fix corrects where the filter thinks it is but not which way it thinks it's heading, so its prediction runs away from the next fixes while its uncertainty says it's confident. I didn't verify that; it would need the filter's heading compared against the ground-truth track at t+3494 s.

Once a lockout starts, it feeds itself. Every correct fix looks like an outlier, so the gate refuses the only information that could correct the drift, and the drift keeps growing. The way out is for the uncertainty to grow until the gate is wide enough to let a fix through, and that's a knife-edge: in the injected-blackout test in §3, it ended when one fix scored 16.26 against a threshold of 16.27. How a gap ends is sensitive in the same way. The injected 200-second outage in §3 was followed by 46 rejections, but the same outage in the four ablation runs ended with the first fix accepted and none at all.

The third gap is where the runs part ways. It begins in the middle of the lockout, at t+3700 s, so every run enters it already locked out, and when GPS returns about 215 seconds later the uncertainty is around 95–105 m in all of them. After that:

- both no-outage runs accept the first fix and snap back, which is their largest position jump of the run (343–373 m at t+3916–3917 s);
- the frozen outage run rejects 117 more fixes, accepts one 26 seconds later at t+3942 s, and snaps back 387 m;
- the active outage run never accepts another fix. It refuses the rest of the sequence, 7,340 fixes in a row, while its uncertainty climbs past 200 m.

This explains the long-run excursions I couldn't account for in §2. I had checked the GPS in a five-second window around one of the jumps, seen healthy fixes and normal covariance, and concluded GPS wasn't involved. It was: the jump is the moment the filter finally accepted GPS after minutes of refusing it. The 324 m and 600 m excursions from my earlier runs look like the same thing, but those recordings no longer exist, so I couldn't confirm it.

It also changes how §3 should be read. The paper worries about a blackout blinding the gate so that it accepts bad GPS. On this data the gate rejected the bad GPS correctly. Its real problem was the opposite: rejecting good GPS for minutes at a time, and in one run for the whole last third of the sequence.

What I didn't find is why the fixes that follow an accepted one get rejected, or why the author's own runs, which score 18.6 m on this sequence, apparently don't lock out. Both are in §8.

## 6. Reproducibility Defects in the Benchmark Harness

Three defects in the benchmark harness produced malformed recordings on every run I made, and would on any run made with the repo as shipped. I found them while trying to work out why two supposedly identical runs had wildly different message counts. Fixing them exposed a fourth problem, which I fixed too.

### The recordings were mostly duplicates

The first sign was a mismatch that made no sense. Two ablation runs that differed in one configuration value produced 242,195 and 591,072 filter poses. The `robot_localization` baseline, which neither run changed, produced 11,743 and 112,404. A control filter can't legitimately differ by a factor of ten.

Deduplicating the recorded trajectories by timestamp showed how bad it was:

| Recording | Poses | Unique timestamps | Duplicates |
|---|---|---|---|
| 2012-01-08 at 3× | 202,659 | 126,658 | 38% |
| 2012-01-08 at 1× | 939,242 | 432,262 | 54% |
| 2012-08-20 | 558,396 | 117,813 | 79% |
| Ablation, first attempt | 242,195 | 11,995 | **95%** |

![Bar chart of the percentage of recorded FusionCore poses carrying a duplicate timestamp, for four recordings before the harness fix and one after it.](../figures/fig_duplicates.png)

*Figure 6. Share of recorded FusionCore poses carrying a duplicate timestamp: between 38% and 95% before the harness fixes, and none after.*

The `robot_localization` recordings, checked the same way, had no duplicates at all.

That contrast points at the cause. `robot_localization` publishes when odometry arrives, so it stops when the data stops. FusionCore publishes on a wall-clock timer but stamps its messages with simulated time, so it keeps publishing whether or not simulated time is moving.

### Defect one: the player never exits

`nclt_player.py` prints `Playback complete.` and then keeps spinning. Its `main()` calls `rclpy.spin(node)` and nothing ever stops the executor, so the process never ends.

### Defect two: shutdown raises an error

When the process is finally interrupted, `main()` calls `rclpy.shutdown()` in a `finally` block. By then the context is already down, so it raises `RCLError: rcl_shutdown already called` and the process exits with code 1 instead of cleanly.

### Defect three: the launch file never shuts down

`nclt_benchmark.launch.py` starts six processes and has no handler for the player finishing. Because of defect one there was nothing to trigger one anyway, but the result is that after playback ends, FusionCore and the recorder keep running until someone stops them. `/clock` has stopped by then, so every pose published in that time has the same frozen timestamp and the same state. At 100 Hz, a run left for twenty minutes after playback picks up around 120,000 duplicate entries.

### A fourth problem: duplicates during the run

With those three fixed, a 60-second slice still came out 37% duplicates, so something was also producing them while the data was playing.

About a third of the time, the publish timer reads the same simulated time as the fire before it. Those messages carry the same state as well as the same timestamp, because the filter only predicts when an IMU message arrives and no simulated time has passed. Nothing is lost by not sending them, and odometry with duplicate timestamps is malformed anyway: anything interpolating over time gets zero-length intervals.

What I didn't establish is *why* the node's clock value doesn't advance between those fires. The obvious explanation would be the timer running faster than the clock, but the numbers rule that out. The recordings hold about 902,000 `/clock` messages over roughly 5,500 simulated seconds, which at 3× playback is about 490 clock updates per second of wall time against the timer's 100. The clock updates around five times more often than the timer fires. My best guess is something in how the node caches its clock value, since the timer and the `/clock` subscription run in separate callback groups, but I haven't verified it. The measurement and the fix are solid; the mechanism isn't.

### The fixes

- **Player:** call `rclpy.shutdown()` when playback ends so the executor stops and the process exits, and guard the call in `main()` so it isn't made a second time.
- **Launch file:** an `OnProcessExit` handler on the player that triggers a `Shutdown` after three seconds, giving the recorder time to flush.
- **Node:** a check in `publish_state()` that skips publishing when the clock hasn't advanced since the last message.

I verified them on 60-second slices. With the shutdown fixes in, the whole stack exits on its own 41 seconds after launch. With the publish check added, the same slice went from 1,671 poses with 617 duplicates to 1,234 poses with none.

### What this did and didn't affect

I re-scored every earlier result from deduplicated trajectories, and every absolute trajectory error came out identical to three decimal places. The evaluation matches estimated poses to ground truth by timestamp, so duplicates sharing a timestamp collapse into one matched pose and add nothing.

The damage was to interpretation, not the numbers. Message counts stopped meaning anything as a diagnostic, and twice I spent a lot of time chasing differences between runs that came down to how long each had been left running after playback. One ablation comparison had to be thrown out because I couldn't show the arms were comparable.

It also means bags recorded with the harness as shipped contain a large share of malformed odometry. That doesn't change error figures computed the way the paper computes them, for the reason above, but anything based on message rates or recording length can't be trusted.

## 7. Documentation Defects

Four places where the paper and the code disagree came up while I was working out where to put my changes. None of them changes how the system behaves, but each would mislead someone working from the paper alone. Below, "the paper" means [1] and "the code" means [2].

**The encoder measurement equation has the wrong sign.** Equation 13 gives the encoder measurement function as `h_enc(x) = [vx, vy, ωz − b_ewz]`, subtracting the bias. The code computes `z[2] = x[WZ] + x[B_EWZ]`, adding it. The code is right, and matches the paper's own equation 11, which adds the gyro bias to angular velocity for the IMU. So the paper contradicts itself: equations 11 and 13 use opposite conventions for the same operation, and only one matches the implementation. My unit test for the 23rd state pins the implemented convention, partly to document it.

**The coast-mode subtraction path doesn't exist.** The abstract says the 23rd state's bias is "subtracted during GPS blackouts to reduce heading drift in coast mode," and Section IV-A describes the same thing in more detail. There's no such path in the code. The bias sits permanently in the encoder measurement function and behaves the same whether GPS is there or not. So the abstract's one-sentence description of the paper's main contribution gets both the sign and the mechanism wrong. It made my ablation simpler, since there was no blackout-specific code to disable, but the paper's account of how its own contribution works doesn't match what the code does.

**The paper contradicts its own benchmark configuration.** Section VII-E blames the 2012-08-20 failure partly on coast mode relaxing the chi-squared gate on recovery, to accept the first returning fix. In the configuration used for the benchmark, that relaxation is switched off. Two parameters control it, both set to zero, with the author's comments explaining why: "disabled: P inflation via recovery mode was causing outlier acceptance" and "disabled: chi2 gate with coast_q_factor=10 handles GPS recovery correctly." He turned the mechanism off because it caused the problem the paper attributes to it, then described it as active.

**The 23rd state is only observable through GPS.** The paper doesn't say this, but the author documents it in a test comment: "Without that prior, WZ and the two biases are individually unobservable from IMU + encoder alone." The test has to set the state's initial covariance to 1e-8 to make it converge at all. It also means that during a blackout the state is stuck at whatever value it reached and applied to every encoder measurement, with nothing to correct it. That's one plausible way the outage in §4 could leave a lasting difference between the two arms, but I didn't log the state's value, so I can't confirm it.

Separately, the benchmark configuration sets the ground-constraint z-position sigma to zero, while its own comment describes a value of 0.3 m.

## 8. Limitations and Unresolved Anomalies

These are the things I couldn't explain or rule out. They limit what the rest of the report can claim.

**Why the lockouts happen.** The lockouts start right after natural GPS gaps in the data, but not at the gaps themselves: GPS returns, the first fix is accepted, and the fixes after it are rejected. I didn't establish why. My best guess, that one position fix corrects position but not heading, is untested; comparing the filter's heading with the ground-truth track around t+3494 s would settle it. Gap length isn't the trigger, since a 165-second gap caused no lockout and a 112-second one caused the longest. I also don't know why the author's runs, which score 18.6 m on this sequence, apparently don't lock out. Before finding the lockout I had ruled out four other explanations for the excursions: playback timing, GPS coordinate conversion, ground-truth construction, and ARM64 numerical differences in the covariance repair path. Those still stand, and the build reproduces the author's own trajectory to within 2.6 m, so the difference lies in how the runs play out rather than in the build. Either way, the lockouts inflate every absolute error figure in this report, so none of my absolute figures should be compared against the paper's.

**The `robot_localization` baseline.** In every run I made, on both sequences, the EKF baseline scored five to twenty times worse than the author's published figures: around 254 m on 2012-01-08 where he reports 41 m, and 216 m on 2012-08-20 where he reports 10.6 m. It's very consistent, 253.8 to 254.6 m across the four ablation runs, which is what makes it useful as a control. But it also means something systematic differs between my setup and his, in a filter I never touched. I didn't investigate it, because it's outside both contributions and the control property was all I needed from it.

**Whether the 23rd state's effect is systematic.** My first two explanations for the §4 result failed, and the one that survived explains *how* the arms differ, through the lockout, but not *why* the state should change the outcome. Escaping a lockout is knife-edge, I ran one run per configuration, and I didn't log the state's value, so I can't tell whether the state makes lockouts systematically worse or just tipped one run. The 12% path-length shortfall is measured three ways and is solid, but I also didn't trace how a yaw-rate bias ends up shortening the estimated distance, since a heading error on its own rotates each step without shortening it.

**Scope.** The ablation is one sequence, one outage configuration and one run per cell. Playback is deterministic, so repeating a configuration gives identical results and adds nothing, but that's not the same as generalising. The paper's claim is about the general case; my result is about 2012-01-08 with a 200-second injected outage.

In the same way, §3's finding that the chi-squared gate rejects the corrupted cluster only holds for 2012-08-20. There it rejected the corrupted fixes at 4.4 to 5.4 times the threshold with position sigma at 63–68 m. The paper documents a second loss on 2012-06-15, with a much longer blackout, which I didn't run. A longer blackout inflates the covariance further and could close that gap, so whether bad fixes ever get through is still open. It's also what would decide whether the proposed pre-gate has a target anywhere.

**A note on the harness.** The results in §2 and §3 were produced before the §6 fixes. The four ablation runs that §4 and §5 rely on used the corrected build. The fixes don't touch state estimation, and re-scoring the earlier results from deduplicated trajectories reproduced every figure to three decimal places, so the two sets are comparable. They still weren't produced by identical software, and I'd rather state that than leave it implied.

## 9. Conclusions

I set out to test three claims. Two did not hold, and the third pointed at the wrong failure.

The proposed velocity pre-gate has no target on the sequence it was designed for. The arithmetic behind it is off by a factor of a thousand: the fix that arrives after the 211-second blackout implies 3.4 m/s, not 3400, and no sensible speed threshold rejects it. The failure it's meant to fix isn't happening either. The chi-squared gate rejected every fix in the corrupted cluster, including the one the paper names at five times the threshold. The error in that stretch is dead-reckoning drift during a blackout in which GPS was correctly refused the whole time, and no GPS gate can help with that. The check also has a structural problem: dividing displacement by the time since the last fix gives a limit that grows with the blackout, so it goes blind after long outages for the same reason the statistical gate is said to.

The 23rd state didn't improve accuracy in any condition I tested. Freezing it gave a lower trajectory error both with GPS available (9%) and across a 200-second outage (75%). But both differences come down to how long each run was locked out of GPS, and escaping a lockout is knife-edge, so I can't say whether the state makes it systematically worse. What I can say is that the paper's claimed improvement isn't supported.

The paper's account of the failure mechanism is half right, and the half that's wrong is the most interesting result here. Covariance growth during a blackout is real: position sigma reached 78.4 m against a normal 1.4 m. But it didn't blind the gate to bad GPS. With sigma at 63–68 m, the gate still rejected the corrupted cluster at four to five times its threshold. The failure the filter actually shows is the reverse. After natural GPS gaps in the data, it accepts one returning fix and then rejects the good fixes that follow, and once that starts it feeds itself: the drift grows and the gate keeps rejecting. Every full run I analysed locked out at the same point for around a thousand fixes, and one never recovered. On this data, the real risk is a filter that trusts its own estimate too much, not one that trusts GPS too much.

Along the way I fixed three defects in the benchmark harness, plus a fourth they were hiding. Recorded odometry was between 38% and 95% duplicate timestamps, the player never exited, and the launch never shut down. Those recordings are malformed, although the published error figures don't depend on it.

What I'd take from this is narrow and worth saying plainly. Every claim here could be checked against the source and the data, and checking took far longer than implementing. The implementations were small. The verification was the work.

## Code and Data

- Study, scripts, figures and results: https://github.com/rustamoz/fusioncore-verification
- Code changes to FusionCore: branch `verification` of https://github.com/rustamoz/fusioncore, based on upstream commit `99503ca`. All changes on one page: https://github.com/rustamoz/fusioncore/compare/99503ca...verification

## Acknowledgements

This work analyses FusionCore, released by Manan Kharwar under the Apache License 2.0 [8], using the NCLT dataset from the University of Michigan, released under the Open Database License [7]. No dataset files are redistributed.

## References

[1] M. Kharwar, "FusionCore: A 23-state unscented Kalman filter for IMU, wheel encoder, GPS, and visual SLAM fusion in ROS 2," arXiv:2605.25239 [cs.RO], 2026. doi: 10.48550/arXiv.2605.25239

[2] M. Kharwar, "FusionCore: ROS 2 UKF sensor fusion," Zenodo, 2026. doi: 10.5281/zenodo.20091053. [Online]. Available: https://github.com/manankharwar/fusioncore

[3] N. Carlevaris-Bianco, A. K. Ushani, and R. M. Eustice, "University of Michigan North Campus long-term vision and lidar dataset," *The International Journal of Robotics Research*, vol. 35, no. 9, pp. 1023–1035, 2016. doi: 10.1177/0278364915614638

[4] T. Moore and D. Stouch, "A generalized extended Kalman filter implementation for the Robot Operating System," in *Proc. 13th Int. Conf. Intelligent Autonomous Systems (IAS-13)*, 2014, pp. 335–348. doi: 10.1007/978-3-319-08338-4_25

[5] S. J. Julier and J. K. Uhlmann, "Unscented filtering and nonlinear estimation," *Proceedings of the IEEE*, vol. 92, no. 3, pp. 401–422, 2004. doi: 10.1109/JPROC.2003.823141

[6] M. Grupp, "evo: Python package for the evaluation of odometry and SLAM," 2017. [Online]. Available: https://github.com/MichaelGrupp/evo

[7] Open Knowledge Foundation, "Open Database License (ODbL) v1.0." [Online]. Available: https://opendatacommons.org/licenses/odbl/1-0/

[8] Apache Software Foundation, "Apache License, Version 2.0," 2004. [Online]. Available: https://www.apache.org/licenses/LICENSE-2.0
