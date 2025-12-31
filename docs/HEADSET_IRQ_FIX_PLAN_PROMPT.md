# Plan Prompt: Fix Headset IRQ Hardware Issue on R58 Device

## Role
You are a Linux kernel and embedded systems specialist. Your task is to permanently disable the faulty headset detection IRQ on an RK3588-based device (R58).

## Context and Problem

### The Issue
The R58 device has a headset detection GPIO (IRQ 159) that is constantly triggering due to a floating input (no pull-up/pull-down resistor). This causes:

- **277,464 interrupts per second** (measured)
- **29-36% CPU usage** wasted on interrupt handling
- **Reduced system stability** (contributes to crashes)
- **Network instability** (delays packet processing)
- **Prevents CPU idle** (increased power/thermal issues)

### Hardware Details
```
Device: R58 (Rockchip RK3588 SoC)
OS: Linux (Debian-based, kernel 6.1.x)
IRQ: 159 (rockchip_gpio_irq, Edge-triggered)
Handler: headset_detect
Driver: rk817-headset (RK817 PMIC headset detection)
GPIO Controller: rockchip_gpio_irq pin 16
```

### Evidence from /proc/interrupts
```
           CPU0       CPU1-7
159:  636903544          0  rockchip_gpio_irq  16 Edge  headset_detect
```

### Why This Matters
The R58 is a multi-camera video recorder that runs GStreamer pipelines at 200%+ CPU. The 29% IRQ overhead:
1. Reduces headroom for video processing
2. May contribute to hardware timeout crashes (RGA, VPU)
3. Prevents system recovery during failures
4. Wastes power and generates unnecessary heat

### What We've Tried (Failed)
```bash
# These don't work:
echo 0 > /proc/irq/159/smp_affinity  # I/O error
echo disabled > /proc/irq/159/spurious_unhandled  # Path doesn't exist
```

### What We DON'T Want
- We do NOT use the headset jack (3.5mm audio)
- We do NOT need headset detection
- All audio comes from HDMI inputs
- Safe to completely disable this functionality

## Goal
Permanently disable IRQ 159 (headset detection) using one of these approaches:

1. **Device Tree Overlay** (Preferred) - Disable the headset node in DT
2. **Kernel Module Blacklist** - Prevent the driver from loading
3. **ACPI/Firmware Fix** - If applicable
4. **udev Rule** - Unbind the driver after boot

The fix must:
- Survive reboots
- Be deployable via git (no manual intervention)
- Not break other audio functionality (HDMI audio must still work)
- Reduce IRQ 159 rate to 0

## Available Information

### Device Tree Location (Likely)
```
/boot/dtb/rockchip/rk3588*.dtb
/sys/firmware/devicetree/base/
```

### Kernel Modules (Audio-related)
```bash
lsmod | grep -i snd
lsmod | grep -i rk817
lsmod | grep -i codec
```

### GPIO Info
```bash
cat /sys/kernel/debug/gpio | grep -A2 -B2 headset
```

### Headset Driver Source (Reference)
The RK817 PMIC headset detection is typically in:
- `drivers/input/misc/rk8xx-keys.c`
- `drivers/extcon/extcon-rk817-headset.c`

## Constraints

- SSH access to device via: `./connect-r58-frp.sh "command"`
- Device path: `/opt/preke-r58-recorder`
- Deployment script: `./deploy-simple.sh`
- Must test after fix to verify IRQ rate drops to 0
- Document the fix in `docs/HEADSET_IRQ_FIX.md` (already exists, update it)

## Success Criteria

1. IRQ 159 fires 0 times per second (verify with):
   ```bash
   IRQ1=$(cat /proc/interrupts | grep headset | awk '{print $2}')
   sleep 5
   IRQ2=$(cat /proc/interrupts | grep headset | awk '{print $2}')
   echo "Rate: $(( (IRQ2-IRQ1) / 5 )) per second"
   # Should output: Rate: 0 per second
   ```

2. CPU usage for `irq/159-headset_detect` drops to 0%

3. HDMI audio still works (not affected by fix)

4. Fix persists across reboots

5. Fix is committed to git and deployable

## Exploration Steps

1. **Identify the driver/module:**
   ```bash
   cat /proc/irq/159/headset_detect/actions
   lsmod | grep -i rk817
   modinfo rk817_codec 2>/dev/null || echo "Not a module"
   ```

2. **Find device tree node:**
   ```bash
   find /sys/firmware/devicetree -name "*headset*" 2>/dev/null
   find /sys/firmware/devicetree -name "*rk817*" 2>/dev/null
   ```

3. **Check if it's a loadable module or built-in:**
   ```bash
   cat /proc/config.gz | gunzip | grep -i RK817
   # Or
   zcat /proc/config.gz | grep -i HEADSET
   ```

4. **Test module unload (if applicable):**
   ```bash
   sudo modprobe -r rk817_codec
   # Check if IRQ stops
   ```

5. **Create device tree overlay (if needed):**
   - Identify the headset node in DT
   - Create overlay to set `status = "disabled"`
   - Test with `fdtoverlay` or boot parameter

## Deliverables

1. Working fix (one of: DT overlay, module blacklist, udev rule)
2. Updated `docs/HEADSET_IRQ_FIX.md` with implementation details
3. Deployment file (e.g., `deployment/disable-headset.conf` or `.dts`)
4. Installation script or instructions
5. Verification that IRQ rate is 0

## Reference Files

- Existing documentation: `docs/HEADSET_IRQ_FIX.md`
- Existing (non-working) service: `deployment/disable-headset-irq.service`
- Connection script: `./connect-r58-frp.sh`
- Deploy script: `./deploy-simple.sh`

