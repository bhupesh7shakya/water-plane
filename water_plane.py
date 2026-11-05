#!/usr/bin/python3
"""
Water Plane Notification System
Spawns an airplane flying across your screen from Left to Right
in the middle of the screen, pulling a banner reminding you to drink water!
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time

# Add current directory to path
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")
import cairo
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell

import renderer
import sound

CONFIG_DIR = os.path.expanduser("~/.config/water-plane")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_CONFIG = {
    "interval_seconds": 3600,
    "message": "TIME TO DRINK WATER! STAY HYDRATED",
    "sound": True,
    "desktop_notification": False,
    "flight_duration": 18.0,
    "altitude": "middle",
    "direction": "ltr",
    "monitor_mode": "focused",
    "font": "Sans Bold 16",
}


def load_config():
    """Load configuration from ~/.config/water-plane/config.json with defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                cfg.update(saved)
        except Exception as e:
            print(f"Warning: Could not read config file: {e}", file=sys.stderr)
    return cfg


def save_config(cfg):
    """Save configuration to ~/.config/water-plane/config.json."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


def get_hyprland_focused_monitor():
    """Detects focused monitor in Hyprland compositor."""
    try:
        out = subprocess.check_output(["hyprctl", "monitors", "-j"], timeout=2).decode(
            "utf-8"
        )
        data = json.loads(out)
        for m in data:
            if m.get("focused"):
                return m
        if data:
            return data[0]
    except Exception:
        pass
    return None


def get_target_gdk_monitors(mode="focused"):
    """
    Returns list of tuples: (gdk_monitor, width, height, name)
    based on the specified mode ('focused', 'all', or a specific monitor name).
    """
    display = Gdk.Display.get_default()
    if not display:
        return []

    n_mon = display.get_n_monitors()
    gdk_monitors = []
    for i in range(n_mon):
        m = display.get_monitor(i)
        geo = m.get_geometry()
        model = m.get_model() or f"Monitor-{i}"
        gdk_monitors.append((m, geo.x, geo.y, geo.width, geo.height, model))

    if mode == "all":
        return [(m, w, h, model) for (m, x, y, w, h, model) in gdk_monitors]

    # Check Hyprland focused monitor
    h_focused = get_hyprland_focused_monitor()
    if h_focused:
        fx, fy = h_focused.get("x", 0), h_focused.get("y", 0)
        h_name = h_focused.get("name", "focused")
        for m, x, y, w, h, model in gdk_monitors:
            if x == fx and y == fy:
                return [(m, w, h, h_name)]

    # If specific name requested
    if mode != "focused":
        for m, x, y, w, h, model in gdk_monitors:
            if mode.lower() in model.lower():
                return [(m, w, h, model)]

    # Fallback to primary/first monitor
    if gdk_monitors:
        m, x, y, w, h, model = gdk_monitors[0]
        return [(m, w, h, model)]
    return []


class FlightWindow:
    def __init__(self, gdk_monitor, mon_w, mon_h, mon_name, config, on_finish_cb=None):
        self.mon_w = mon_w
        self.mon_h = mon_h
        self.mon_name = mon_name
        self.config = config
        self.on_finish_cb = on_finish_cb

        self.duration = float(config.get("flight_duration", 13.0))
        self.direction = config.get("direction", "ltr").lower()
        self.message = config.get("message", "TIME TO DRINK WATER! STAY HYDRATED")
        self.font = config.get("font", "Sans Bold 15")

        # Altitude in middle of the screen by default
        raw_alt = config.get("altitude", "middle")
        if raw_alt == "middle" or raw_alt is None:
            self.altitude = (self.mon_h // 2) - 25
        else:
            try:
                self.altitude = int(raw_alt)
            except ValueError:
                self.altitude = (self.mon_h // 2) - 25

        self.renderer = renderer.SceneRenderer(
            message=self.message, font_name=self.font, direction=self.direction
        )

        # Window setup: span full monitor width and height
        self.window = Gtk.Window()
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)

        if gdk_monitor:
            GtkLayerShell.set_monitor(self.window, gdk_monitor)

        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)

        # Transparent RGBA visual
        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)
        self.window.set_app_paintable(True)

        # Connect signals
        self.window.connect("realize", self.on_realize)
        self.window.connect("draw", self.on_draw)

        self.start_time = None

        # Start and End positions based on direction
        if self.direction == "ltr":
            # Left to Right: nose starts just before left edge, flies past right edge
            self.start_x = -40
            self.end_x = self.mon_w + self.renderer.total_length + 60
        else:
            # Right to Left: starts offscreen right, flies past left edge
            self.start_x = self.mon_w + 50
            self.end_x = -self.renderer.total_length - 60

        self.finished = False

    def on_realize(self, widget):
        # 100% click-through: empty input region means pointer events pass directly to underlying apps
        empty_region = cairo.Region()
        widget.get_window().input_shape_combine_region(empty_region, 0, 0)

    def start(self):
        self.start_time = time.time()
        self.window.show_all()
        GLib.timeout_add(16, self.update_frame)

    def update_frame(self):
        if self.finished:
            return False

        now = time.time()
        elapsed = now - self.start_time

        if elapsed >= self.duration:
            self.finished = True
            self.window.destroy()
            if self.on_finish_cb:
                self.on_finish_cb(self)
            return False

        self.window.queue_draw()
        return True

    def on_draw(self, widget, cr):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        if not self.start_time:
            return False

        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.duration)

        # Linear motion across the screen
        plane_x = self.start_x + (self.end_x - self.start_x) * progress

        # Render complete flight scene
        self.renderer.render(cr, plane_x, self.altitude, elapsed, bobbing=True)
        return False


def run_flight(config=None):
    """Triggers the flying airplane across target monitor(s)."""
    if config is None:
        config = load_config()

    # Play water drop sound
    if config.get("sound", True):
        sound.play_chime(True)

    # Optional desktop notification
    if config.get("desktop_notification", False):
        try:
            subprocess.Popen(
                [
                    "notify-send",
                    "-a",
                    "Water Plane",
                    "-i",
                    "dialog-information",
                    "💧 Hydration Reminder",
                    config.get("message", "Time to drink water! Stay hydrated."),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

    mode = config.get("monitor_mode", "focused")
    monitors = get_target_gdk_monitors(mode)
    if not monitors:
        print("Error: No display monitors detected.", file=sys.stderr)
        return 1

    active_windows = []

    def on_window_done(win):
        if win in active_windows:
            active_windows.remove(win)
        if not active_windows:
            Gtk.main_quit()

    for gdk_mon, w, h, name in monitors:
        win = FlightWindow(gdk_mon, w, h, name, config, on_finish_cb=on_window_done)
        active_windows.append(win)
        win.start()

    # Enter GTK main loop until all windows finish
    Gtk.main()
    return 0


def run_daemon(interval_seconds=3600, config=None):
    """Runs continuous reminder loop every interval_seconds."""
    if config is None:
        config = load_config()

    config["interval_seconds"] = interval_seconds
    print(
        f"✈️  Water Plane daemon started. Reminding every {interval_seconds} seconds ({interval_seconds / 3600:.1f} hours)."
    )
    print("Press Ctrl+C to stop.")

    print("🌊 Launching initial hydration reminder flight...")
    run_flight(config)

    running = True

    def sig_handler(sig, frame):
        nonlocal running
        print("\nStopping Water Plane daemon...")
        running = False
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    while running:
        next_time = time.time() + interval_seconds
        print(
            f"⏳ Next flight scheduled in {interval_seconds}s (at {time.strftime('%H:%M:%S', time.localtime(next_time))})..."
        )
        time.sleep(interval_seconds)
        if running:
            print("✈️  Flying water plane reminder across screen...")
            run_flight(config)


def parse_interval(interval_str):
    """Parse string like '1h', '60m', '3600s', '3600' into integer seconds."""
    s = str(interval_str).strip().lower()
    if s.endswith("h"):
        return int(float(s[:-1]) * 3600)
    elif s.endswith("m"):
        return int(float(s[:-1]) * 60)
    elif s.endswith("s"):
        return int(float(s[:-1]))
    return int(float(s))


SERVICE_CONTENT = """[Unit]
Description=Water Plane Hydration Reminder
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/home/user/.local/bin/water-plane fly
Environment=DISPLAY=:0
Environment=WAYLAND_DISPLAY=wayland-1
Environment=XDG_CURRENT_DESKTOP=Hyprland

[Install]
WantedBy=default.target
"""

TIMER_HOURLY_CONTENT = """[Unit]
Description=Water Plane Hourly Hydration Reminder Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
"""

TIMER_CUSTOM_CONTENT = """[Unit]
Description=Water Plane Hydration Reminder Timer ({interval_str})

[Timer]
OnBootSec=10min
OnUnitActiveSec={interval_str}
AccuracySec=1min
Persistent=true

[Install]
WantedBy=timers.target
"""


def setup_systemd(interval_seconds=3600):
    """Installs systemd user service and timer for scheduled execution."""
    systemd_user_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(systemd_user_dir, exist_ok=True)

    service_file = os.path.join(systemd_user_dir, "water-plane.service")
    timer_file = os.path.join(systemd_user_dir, "water-plane.timer")

    with open(service_file, "w") as f:
        f.write(SERVICE_CONTENT)

    if interval_seconds == 3600:
        timer_text = TIMER_HOURLY_CONTENT
        interval_desc = "hourly on the hour"
    else:
        if interval_seconds % 3600 == 0:
            interval_str = f"{interval_seconds // 3600}h"
        elif interval_seconds % 60 == 0:
            interval_str = f"{interval_seconds // 60}min"
        else:
            interval_str = f"{interval_seconds}s"
        timer_text = TIMER_CUSTOM_CONTENT.format(interval_str=interval_str)
        interval_desc = f"every {interval_str}"

    with open(timer_file, "w") as f:
        f.write(timer_text)

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(
        ["systemctl", "--user", "enable", "--now", "water-plane.timer"], check=True
    )
    print(f"✅ Systemd timer installed and enabled ({interval_desc})!")
    print("Status:")
    subprocess.run(["systemctl", "--user", "status", "water-plane.timer", "--no-pager"])


def stop_systemd():
    """Disables and stops systemd timer and service."""
    try:
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", "water-plane.timer"],
            check=False,
        )
        subprocess.run(
            ["systemctl", "--user", "stop", "water-plane.service"], check=False
        )
        print("🛑 Systemd timer and service stopped.")
    except Exception as e:
        print(f"Error stopping systemd unit: {e}", file=sys.stderr)


def get_status():
    """Prints current status of timer, daemon, and configuration."""
    cfg = load_config()
    print("=== Water Plane Reminder Status ===")
    print(
        f"• Reminder Interval: {cfg.get('interval_seconds', 3600)}s ({cfg.get('interval_seconds', 3600) / 3600:.1f} hours)"
    )
    print(f"• Direction: {cfg.get('direction', 'ltr').upper()} (Left to Right)")
    print(
        f"• Position: Middle of the screen (altitude: {cfg.get('altitude', 'middle')})"
    )
    print(
        f"• Flight Duration (Speed): {cfg.get('flight_duration', 13.0)}s (Gentle & Calm)"
    )
    print(f'• Message: "{cfg.get("message")}"')
    print(f"• Sound Enabled: {cfg.get('sound')}")
    print(f"• Monitor Mode: {cfg.get('monitor_mode')}")
    print("\n--- Systemd Timer Status ---")
    res = subprocess.run(
        ["systemctl", "--user", "is-active", "water-plane.timer"],
        capture_output=True,
        text=True,
    )
    timer_active = res.stdout.strip()
    print(f"• Timer Active: {timer_active}")
    if timer_active == "active":
        subprocess.run(
            ["systemctl", "--user", "list-timers", "water-plane.timer", "--no-pager"]
        )


def main():
    parser = argparse.ArgumentParser(
        description="Water Plane Reminder - Animated Flying Airplane Hydration Reminder for Wayland/Hyprland",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  water-plane fly                      # Fly the plane right now from left to right in the middle
  water-plane fly --duration 8         # Fly faster
  water-plane start                    # Enable hourly reminder via systemd timer
  water-plane start -i 30m             # Remind every 30 minutes
  water-plane stop                     # Stop and disable reminders
  water-plane status                   # Check reminder timer schedule and config
""",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to run")

    # fly / test
    fly_parser = subparsers.add_parser(
        "fly", aliases=["test", "trigger"], help="Fly the airplane once right now"
    )
    fly_parser.add_argument("--message", type=str, help="Custom reminder text")
    fly_parser.add_argument(
        "--duration", type=float, help="Flight duration in seconds (default 18.0)"
    )
    fly_parser.add_argument(
        "--altitude", type=str, help="Y-position or 'middle' (default 'middle')"
    )
    fly_parser.add_argument(
        "--direction",
        type=str,
        choices=["ltr", "rtl"],
        help="Flight direction ('ltr' or 'rtl')",
    )
    fly_parser.add_argument(
        "--no-sound", action="store_true", help="Mute water chime sound"
    )
    fly_parser.add_argument(
        "--monitor", type=str, help="Monitor mode: 'focused', 'all', or monitor name"
    )

    # daemon
    daemon_parser = subparsers.add_parser("daemon", help="Run background daemon loop")
    daemon_parser.add_argument(
        "--interval",
        "-i",
        type=str,
        default="1h",
        help="Interval between reminders (e.g. 1h, 60m, 3600s)",
    )
    daemon_parser.add_argument(
        "--no-sound", action="store_true", help="Mute water chime sound"
    )
    daemon_parser.add_argument("--message", type=str, help="Custom reminder text")

    # start / enable systemd
    start_parser = subparsers.add_parser(
        "start", help="Enable and start hourly systemd timer"
    )
    start_parser.add_argument(
        "--interval", "-i", type=str, default="1h", help="Interval (e.g. 1h, 45m)"
    )

    # stop
    subparsers.add_parser("stop", help="Stop timer or daemon")

    # status
    subparsers.add_parser("status", help="Check status of timer and configuration")

    # config
    cfg_parser = subparsers.add_parser("config", help="View or update configuration")
    cfg_parser.add_argument("--set-message", type=str, help="Update default message")
    cfg_parser.add_argument("--set-interval", type=str, help="Update default interval")
    cfg_parser.add_argument(
        "--set-sound",
        type=str,
        choices=["true", "false", "on", "off"],
        help="Enable/disable sound",
    )
    cfg_parser.add_argument(
        "--set-duration", type=float, help="Update flight duration (seconds)"
    )
    cfg_parser.add_argument(
        "--set-direction",
        type=str,
        choices=["ltr", "rtl"],
        help="Update direction ('ltr' or 'rtl')",
    )
    cfg_parser.add_argument(
        "--set-altitude", type=str, help="Update altitude ('middle' or Y-coordinate)"
    )

    args = parser.parse_args()

    cfg = load_config()

    if args.command in ["fly", "test", "trigger", None]:
        if args.command is not None:
            if args.message:
                cfg["message"] = args.message
            if args.duration:
                cfg["flight_duration"] = args.duration
            if args.altitude:
                cfg["altitude"] = args.altitude
            if args.direction:
                cfg["direction"] = args.direction
            if args.no_sound:
                cfg["sound"] = False
            if args.monitor:
                cfg["monitor_mode"] = args.monitor
        return run_flight(cfg)

    elif args.command == "daemon":
        interval = (
            parse_interval(args.interval)
            if args.interval
            else cfg.get("interval_seconds", 3600)
        )
        if args.no_sound:
            cfg["sound"] = False
        if args.message:
            cfg["message"] = args.message
        run_daemon(interval, cfg)

    elif args.command == "start":
        interval = (
            parse_interval(args.interval)
            if args.interval
            else cfg.get("interval_seconds", 3600)
        )
        setup_systemd(interval)

    elif args.command == "stop":
        stop_systemd()

    elif args.command == "status":
        get_status()

    elif args.command == "config":
        modified = False
        if args.set_message:
            cfg["message"] = args.set_message
            modified = True
        if args.set_interval:
            cfg["interval_seconds"] = parse_interval(args.set_interval)
            modified = True
        if args.set_sound:
            cfg["sound"] = args.set_sound in ["true", "on"]
            modified = True
        if args.set_duration:
            cfg["flight_duration"] = args.set_duration
            modified = True
        if args.set_direction:
            cfg["direction"] = args.set_direction
            modified = True
        if args.set_altitude:
            cfg["altitude"] = args.set_altitude
            modified = True

        if modified:
            save_config(cfg)
            print("✅ Configuration updated successfully:")
        print(json.dumps(cfg, indent=4))


if __name__ == "__main__":
    sys.exit(main() or 0)
