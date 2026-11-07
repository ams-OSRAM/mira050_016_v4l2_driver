#!/usr/bin/python3
"""Stress test for camera close/reopen (issue #3): open, stream until the first frame, stop,
close, wait a gap, repeat. Gaps around the runtime-PM autosuspend delay (1 s) make the
regulator switch off and on again quickly.

    python3 tools/reopen_stress.py [--gaps 0.2,0.9,1.0,1.05,1.1,1.2,1.5] [--rounds 5]

Stops at the first failure (no frame within 5 s). Exit code 0 = no failure.
Stop other camera users first (e.g. sudo systemctl stop mira-web).
"""

import argparse
import subprocess
import sys
import threading
import time

from picamera2 import Picamera2

parser = argparse.ArgumentParser()
parser.add_argument("--gaps", default="0.2,0.9,0.95,1.0,1.02,1.05,1.1,1.2,1.5,2.0")
parser.add_argument("--rounds", type=int, default=5)
parser.add_argument("--timeout", type=float, default=5.0)
args = parser.parse_args()
gaps = [float(g) for g in args.gaps.split(",")]


def first_frame(timeout):
    """Open, start, wait for one frame; returns seconds to the first frame or None."""
    cam = Picamera2()
    cam.configure(cam.create_video_configuration())
    t0 = time.monotonic()
    cam.start()
    got = {}
    t = threading.Thread(target=lambda: got.setdefault("md", cam.capture_metadata()), daemon=True)
    t.start()
    t.join(timeout)
    dt = time.monotonic() - t0 if "md" in got else None
    if dt is None:
        return None, cam   # leave it open: closing a hung camera can block
    cam.stop()
    cam.close()
    return dt, None


def diagnose():
    """State of the sensor while a reopen hangs: runtime PM, regulators, I2C answer."""
    import glob
    out = {}
    dev = "/sys/bus/i2c/devices/10-0036/power/"
    for f in ("runtime_status", "runtime_suspended_time", "runtime_active_time"):
        try:
            out[f] = open(dev + f).read().strip()
        except OSError:
            pass
    for r in glob.glob("/sys/class/regulator/regulator.*"):
        try:
            name = open(r + "/name").read().strip()
            if "cam" in name:
                out[f"reg {name}"] = open(r + "/state").read().strip()
        except OSError:
            pass
    try:
        from smbus2 import SMBus, i2c_msg
        with SMBus(10) as bus:
            vals = {}
            for reg in (0xE000, 0x0000, 0x000A, 0x011B):
                w, r = i2c_msg.write(0x36, [reg >> 8, reg & 0xFF]), i2c_msg.read(0x36, 1)
                bus.i2c_rdwr(w, r)
                vals[hex(reg)] = hex(list(r)[0])
            out["i2c"] = vals
    except Exception as e:  # noqa: BLE001
        out["i2c"] = f"no answer ({e})"
    return out


def kernel_errors():
    out = subprocess.run(["dmesg"], capture_output=True, text=True).stdout.splitlines()
    return [line for line in out if "Error writing reg" in line or "stream on failed" in line]


errors_before = len(kernel_errors())
n = 0
gap_prev = 0.0
for rnd in range(args.rounds):
    for gap in gaps:
        n += 1
        dt, hung = first_frame(args.timeout)
        if dt is None:
            new = kernel_errors()[errors_before:]
            print(f"FAIL at reopen {n} (round {rnd + 1}, after a gap of {gap_prev:.3f} s): no frame in "
                  f"{args.timeout} s; kernel: {new[-2:] if new else 'no errors'}", flush=True)
            print(f"     while hung: {diagnose()}", flush=True)
            sys.exit(1)
        print(f"ok   reopen {n:3d}  gap before {gap_prev if n > 1 else 0:.3f} s  first frame {dt:.3f} s", flush=True)
        gap_prev = gap
        time.sleep(gap)
print(f"PASS: {n} reopens, gaps {gaps}")
