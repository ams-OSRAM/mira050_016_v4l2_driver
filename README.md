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

## Contexts and register access

The Mira050 and Mira016 register map has two banks (`BANK_SEL`). Bank 1 holds the context
registers, once per context: A and B on the Mira050, A to D on the Mira016 (`RW_CONTEXT`). The
driver selects the bank and context for every access and returns to bank 0 / context A afterwards.
It writes the ROI and row length to every context, and exposure and frame time to the contexts
chosen with `controls_context`.

The driver has these controls on the sensor sub-device (`v4l2-ctl -d /dev/v4l-subdevN -l`):

| Control | |
|---------|-|
| `context` | the context the sensor switches to (`NEXT_ACTIVE_CONTEXT`) |
| `current_context` | the context in use (`CURRENT_ACTIVE_CONTEXT`), read-only, while streaming |
| `auto_context_switch`, `auto_switch_to_context` | automatic context switching (`EN_AUTO_CNTXT_SWITCH`, `AUTO_SWITCHTO_CNTXT`) |
| `controls_context` | where exposure and frame time go: `All` (default) or one context |
| `register_address`, `register_width` (1-4 bytes), `register_bank`, `register_context` | the register for the next access |
| `register_value` | reading it reads the register, setting it writes it (big-endian) |

Register access runs under the driver's lock, so it does not interfere with the driver's own
register writes, and only works while the sensor streams (`EBUSY` otherwise). Set the address,
width, bank and context before the value, or list them before it in the same call:

```
v4l2-ctl -d /dev/v4l-subdev2 -c register_address=0x000e,register_width=4,register_bank=1,register_context=1
v4l2-ctl -d /dev/v4l-subdev2 -C register_value
v4l2-ctl -d /dev/v4l-subdev2 -c register_value=5000
```

Registers at offsets `0x000`-`0x005` of each block (`BANK_SEL`, `RW_CONTEXT`, ...) are bankless and
ignore bank and context. The driver does not know about values written this way and may overwrite
them at the next stream start or exposure change.

The control IDs start at `V4L2_CID_USER_BASE + 0x2000`; see `MIRA_CID_*` in `mira050.c`. The web UI
of [ams_rpi_viewer](https://github.com/ams-OSRAM/mira_rpi_viewer) uses them in its Registers tab.
