#!/usr/bin/python3
"""Check that FrameDuration and ExposureTime match reality in every sensor mode (issue #4).

For each mode and exposure: FrameDuration (metadata) vs the measured SensorTimestamp spacing,
and the requested vs reported ExposureTime. Exit code 0 when all agree within --tolerance.
Stop other camera users first (e.g. sudo systemctl stop mira-web).
"""

import argparse
import sys
import time

from picamera2 import Picamera2

parser = argparse.ArgumentParser()
parser.add_argument("--exposures", default="500,20000", help="exposure times in us")
parser.add_argument("--tolerance", type=float, default=0.02, help="relative tolerance")
args = parser.parse_args()

cam = Picamera2()
failures = 0
for mode in cam.sensor_modes:
    for exposure in (int(e) for e in args.exposures.split(",")):
        cfg = cam.create_video_configuration(raw={"format": mode["unpacked"], "size": mode["size"]},
                                             controls={"FrameDurationLimits": (int(1e6 / mode["fps"]) + 1, 1_000_000),
                                                       "AeEnable": False, "ExposureTime": exposure,
                                                       "AnalogueGain": 1.0})
        cam.configure(cfg)
        cam.start()
        time.sleep(1.0)
        stamps, mds = [], []
        for _ in range(20):
            md = cam.capture_metadata()
            stamps.append(md["SensorTimestamp"])
            mds.append(md)
        cam.stop()
        gaps = sorted((b - a) / 1e3 for a, b in zip(stamps, stamps[1:]))
        measured = gaps[len(gaps) // 2]          # median frame spacing in us
        reported = mds[-1]["FrameDuration"]
        exp_reported = mds[-1]["ExposureTime"]
        ok_fd = abs(reported - measured) <= args.tolerance * measured
        ok_exp = abs(exp_reported - exposure) <= max(args.tolerance * exposure, 30)
        failures += not (ok_fd and ok_exp)
        print(f"{'ok  ' if ok_fd and ok_exp else 'FAIL'} {mode['unpacked']:4s} exposure {exposure:6d} us: "
              f"FrameDuration {reported:7d} us vs measured {measured:9.1f} us ({(reported / measured - 1) * 100:+5.1f}%), "
              f"ExposureTime {exp_reported} us", flush=True)
cam.close()
print("ALL OK" if not failures else f"{failures} FAILED")
sys.exit(1 if failures else 0)
