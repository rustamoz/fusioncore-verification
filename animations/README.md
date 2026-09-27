# Animations

Two short animations of the report's findings, styled to match the portfolio
site. Each has a poster frame, and a GIF version for places that can't play
MP4. Neither has audio. Everything shown is measured data; the full caption
text is below, so nothing depends on watching them.

## `lockout.mp4` (45 s) — report section 5

Two synchronised map panels of the same stretch of NCLT 2012-01-08, one run
with the 23rd state active and one with it frozen, both with the 200 s
injected outage earlier in the run. Each panel shows the true path (RTK),
the true position, the filter's estimate with its 1-sigma uncertainty, and
each GPS fix as it arrives: a green dot if accepted, a red cross if
rejected. A readout gives the error against the truth, the uncertainty, the
latest fix's Mahalanobis distance against the 16.27 gate, and the number of
fixes rejected in a row. A timeline underneath marks the GPS gaps and every
accepted and rejected fix.

Captions, in order:

1. Normal operation. Each GPS fix is accepted and keeps the estimate on the true path.
2. The receiver loses its signal. The filter dead-reckons, and its uncertainty grows.
3. The signal returns. The first fix is 157 m from the truth, but the enlarged gate lets it through.
4. Uncertainty collapses to 3 m at the wrong place. The good fixes that follow are all rejected.
5. Locked out. Every fix is refused, so nothing can correct the drift.
6. The signal is lost again, this time for 203 s.
7. GPS returns and the fixes are good, but both estimates are now hundreds of metres away.
8. Frozen run: one fix scores 16.25 against the 16.27 threshold, and the estimate snaps back. Active run: never.

It ends with the active run 536 m from the truth after 1,357 consecutive
rejections, and the frozen run 11 m from it.

Time runs at up to 51x through quiet stretches and is slowed to 0.04x around
the corrupted fix, with the speed shown on screen. Both runs are shown on one
clock (the frozen run's; the two runs' zeros differ by 0.601 s). Positions
are drawn exactly as recorded, with no alignment; accepted fixes sit a median
0.64 m from the estimate in normal operation, confirming the frames agree.

## `threshold.mp4` (41 s) — report sections 3 and 5

The proposed velocity check measures a new fix against the last accepted fix
and rejects anything faster than 20 m/s, so the distance it allows grows with
the time since that fix. A cursor sweeps that time from 0.1 s to 1,000 s.

Captions, in order:

1. The proposed check divides a new fix's distance by the time since the last accepted fix, and rejects anything faster than 20 m/s.
2. Between normal fixes, 0.2 s apart, it allows 4 m of movement.
3. As the gap lengthens, the distance it will accept grows with it.
4. After a real 112 s signal loss, a fix 157 m from the truth implies 1.48 m/s. It passes.
5. After 211 s, the fix the paper cites implies 3.4 m/s, not 3,400. It passes.
6. The allowance grows with the gap. After 211 s it is 4.2 km, so the longer the blackout, the less it can catch.

"Passes" means the proposed check would let the fix through. It says nothing
about the filter's own chi-squared gate, which rejected the 2012-08-20 fix and
accepted the 2012-01-08 one (report sections 3 and 5).

## Regenerating

Scripts are in `scripts/animations/`. The export needs the bags and ROS; the
rendering needs only Python, matplotlib, ffmpeg and the site's two fonts,
Geist and JetBrains Mono (both SIL Open Font License), in a `fonts/` folder.

```
python3 export_anim.py out3_ON out3_OFF --rtk 2012-01-08/gps_rtk.csv
python3 render_lockout.py --data anim_export --health figdata --out lockout.mp4
python3 render_threshold.py --out threshold.mp4
python3 first_fix.py --data anim_export        # the numbers behind section 5
```

`--preview 12 20 30` on either renderer writes PNG frames at those video times
instead of a video. The exported CSVs derive from NCLT (Open Database License)
and are gitignored.
