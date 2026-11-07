# ams Mira050 / Mira016 Linux driver

[![CI](https://github.com/ams-OSRAM/mira050_016_v4l2_driver/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ams-OSRAM/mira050_016_v4l2_driver/actions/workflows/ci.yml) [![License: GPL-2.0](https://img.shields.io/badge/license-GPL--2.0-blue.svg)](LICENSE) [![Tested kernel](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.github.com%2Frepos%2Fraspberrypi%2Flinux&query=%24.default_branch&label=tested%20kernel&logo=linux)](#supported-hardware-and-kernels) [![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-3%20%7C%204%20%7C%205%20%7C%20Zero%202%20W-c51a4a?logo=raspberrypi)](#supported-hardware-and-kernels)

One V4L2 driver for both the **Mira050** and the **Mira016** image sensor.
The driver reads the chip ID at probe time and configures itself for the
sensor it finds. The device tree overlay tells it which sensor to expect.

| Sensor  | Compatible     | Overlay   | Color filter                                   |
|---------|----------------|-----------|------------------------------------------------|
| Mira050 | `ams,mira050`  | `mira050` | mono, color or RGB-IR, read from the sensor OTP |
| Mira016 | `ams,mira016`  | `mira016` | mono                                           |

## Supported hardware and kernels

| Raspberry Pi | Camera connector | Kernel config tested in CI |
|---|---|---|
| Pi 3, Pi 4 | 15-pin | `bcm2711_defconfig` |
| Zero 2 W | 22-pin | `bcm2711_defconfig` |
| Pi 5 | 22-pin (CAM0 and CAM1) | `bcm2712_defconfig` |

Raspberry Pi OS 64-bit is required. The driver supports only the kernel that Raspberry Pi OS currently ships; the *tested kernel* badge shows that branch of [raspberrypi/linux](https://github.com/raspberrypi/linux).

CI runs on every push and every Monday. It:

- builds the module against that kernel for both configurations above,
- builds the device tree overlays and checks the binding with `dt_binding_check`,
- installs and removes the module with DKMS on Ubuntu 26.04.

Each run's summary lists the exact kernel version. CI does not test on real hardware.

## Installation

### Prerequisites

The driver supports the latest Raspberry Pi OS kernel only (Linux 6.18 or later). Run `sudo apt full-upgrade` and reboot first if `uname -r` shows an older kernel.

Install git and the kernel headers for the running kernel, then clone this repository.

```
sudo apt update
sudo apt install -y git device-tree-compiler linux-headers-$(uname -r)
git clone https://github.com/ams-OSRAM/mira050_016_v4l2_driver.git
cd mira050_016_v4l2_driver
```

### Driver (recommended: DKMS)

With [DKMS](https://github.com/dell/dkms) the driver is rebuilt automatically every time Raspberry Pi OS installs a new kernel, so the camera keeps working after `sudo apt full-upgrade`.

```
sudo apt install -y dkms
sudo ./dkms-install.sh
```

This builds `mira050.ko`, which handles both sensors and installs it under `/lib/modules/<kernel>/updates/dkms/`. Check it with `dkms status`. To remove it again, run `sudo ./dkms-uninstall.sh`.

### Driver (manual build)

Without DKMS you have to repeat these steps after every kernel update.

```
make
sudo mkdir -p /lib/modules/$(uname -r)/updates && sudo cp mira050.ko /lib/modules/$(uname -r)/updates/
sudo depmod -a
```

### Device tree

Build the device tree overlays (`mira050.dtbo` and `mira016.dtbo`) and copy them to `/boot/firmware/overlays/`:

```
make dtbo
sudo make install_dtbo
```

Set the device tree overlay in your platform. This may differ from platform to platform. Please refer to your platform documentation.

This is how to set the device tree overlay for Raspberry Pi, for Mira050:

```
echo "dtoverlay=mira050" | sudo tee -a /boot/firmware/config.txt
```

or for Mira016:

```
echo "dtoverlay=mira016" | sudo tee -a /boot/firmware/config.txt
```

Alternatively, add the line `dtoverlay=mira050` or `dtoverlay=mira016` at the end of the file.

Add `,cam0` (for example `dtoverlay=mira016,cam0`) if the camera is connected to the CAM0 port.

The Mira050 driver detects mono, color and RGB-IR sensors from the sensor OTP.
If that fails on a __monochrome__ Mira050, use `dtoverlay=mira050,mono` instead.
Mira016 is always monochrome and needs no option.

Finally, run `sudo reboot` to test your changes.
