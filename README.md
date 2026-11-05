# ✈️ Water Plane Reminder

An animated skywriter airplane that glides across your screen from **left to right** in the **middle of your screen** every 1 hour, pulling a banner reminding you to drink water!

Designed for **Linux (Wayland / Hyprland)** using native `GtkLayerShell` and anti-aliased vector Cairo rendering.

---

## 📦 Setup On Any Device

To install this on any machine:

```bash
git clone <your-repo-or-copy-folder> water-plane
cd water-plane
./install.sh
```

The installer will:
1. Detect your Linux distribution (Arch, Ubuntu/Debian, Fedora, openSUSE) and check for dependencies.
2. Link `water-plane` and `hydrate-plane` commands into `~/.local/bin/`.
3. Create the default configuration file in `~/.config/water-plane/config.json`.
4. Configure and enable the hourly systemd user timer (`water-plane.timer`).
5. Run a test flight to verify setup.

To uninstall anytime:
```bash
./install.sh --uninstall
```

---

## ✨ Features

- 🛫 **Smooth Left-to-Right Flight**: Airplane emerges from the left edge and glides across the exact vertical middle of the screen towards the right, pulling the banner behind it.
- 🐢 **Calm, Gentle Cruising Speed**: Default 13-second relaxed flight pace that is easy to read and unhurried.
- 📜 **Fluttering Banner**: Realistic waving banner cloth with swallowtail cutout, wooden spreader bar, brass grommets, and 3D vector water droplets.
- 💨 **Animated Details**: Spinning propeller blur disk, yellow blade tips, cockpit aviator with goggles, trailing exhaust puffs, and water sparkles.
- 🖱️ **100% Click-Through**: Built with Wayland layer-shell empty input masks. The plane never interrupts your clicks, typing, gaming, or code.
- 💧 **Soothing Water Droplet Chime**: Gentle double-drop sound (`bloop... bloop!`) synthesized directly in Python—no external audio files required.
- ⚡ **Zero Background Memory**: Uses a native `systemd` user timer (`water-plane.timer`). The app only launches for the flight duration, then exits cleanly.
- 🖥️ **Smart Monitor Detection**: Automatically flies across your currently focused Hyprland monitor (or `--monitor all`).

---

## 🚀 Quick Usage

| Command | Description |
|---|---|
| `water-plane fly` | Fly the airplane across your screen right now (for testing or manual reminder) |
| `water-plane fly --duration 8` | Fly faster (e.g. 8 seconds) |
| `water-plane fly --direction rtl` | Fly right-to-left if ever desired |
| `water-plane fly --no-sound` | Fly silently without the water drop chime |
| `water-plane status` | Check timer status, next scheduled flight, and configuration |
| `water-plane start` | Enable and start the systemd timer (reminds every 1 hour) |
| `water-plane start -i 45m` | Change reminder interval (e.g. every 45 minutes or 30m) |
| `water-plane stop` | Stop and disable the timer |
| `water-plane daemon` | Run as an independent foreground loop instead of systemd |

---

## ⚙️ Configuration

Settings are saved in `~/.config/water-plane/config.json`:

```json
{
    "interval_seconds": 3600,
    "message": "TIME TO DRINK WATER! STAY HYDRATED",
    "sound": true,
    "desktop_notification": false,
    "flight_duration": 13.0,
    "altitude": "middle",
    "direction": "ltr",
    "monitor_mode": "focused",
    "font": "Sans Bold 15"
}
```

Update settings via CLI:
```bash
water-plane config --set-message "Take a sip of water! 💧"
water-plane config --set-duration 15.0
water-plane config --set-interval 1h
```

---

## ⌨️ Optional Hyprland Keybinding

To trigger a hydration plane anytime with a hotkey, add this to `~/.config/hypr/bindings.conf`:
```ini
bind = $mainMod, W, exec, water-plane fly
```
