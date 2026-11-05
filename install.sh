#!/usr/bin/env bash
# ==============================================================================
#  Water Plane Reminder - Installer Script
#  Sets up the flying airplane hydration notification system on any Linux device.
# ==============================================================================

set -e

# Colors for terminal output
BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
CONFIG_DIR="${HOME}/.config/water-plane"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

# Select Python binary (prefer system python for desktop PyGObject bindings)
if [ -x "/usr/bin/python3" ]; then
    PY_BIN="/usr/bin/python3"
else
    PY_BIN="$(command -v python3 || echo "python3")"
fi

echo -e "${CYAN}${BOLD}✈️  Water Plane Hydration Reminder - Installer${NC}"
echo -e "${CYAN}===============================================${NC}"

# Handle --uninstall
if [[ "$1" == "--uninstall" || "$1" == "uninstall" ]]; then
    echo -e "${YELLOW}Uninstalling Water Plane Reminder...${NC}"
    systemctl --user disable --now water-plane.timer 2>/dev/null || true
    systemctl --user stop water-plane.service 2>/dev/null || true
    rm -f "${SYSTEMD_USER_DIR}/water-plane.timer"
    rm -f "${SYSTEMD_USER_DIR}/water-plane.service"
    systemctl --user daemon-reload 2>/dev/null || true
    rm -f "${BIN_DIR}/water-plane"
    rm -f "${BIN_DIR}/hydrate-plane"
    echo -e "${GREEN}✅ Uninstalled successfully.${NC}"
    exit 0
fi

# 1. Dependency Check & Helper
echo -e "\n${BOLD}[1/5] Checking system dependencies (${PY_BIN})...${NC}"

MISSING_DEPS=()

check_python_module() {
    "$PY_BIN" -c "import gi; gi.require_version('$1', '$2')" 2>/dev/null
}

if ! command -v "$PY_BIN" &>/dev/null; then
    MISSING_DEPS+=("python3")
fi

if ! check_python_module "Gtk" "3.0"; then
    MISSING_DEPS+=("Gtk 3.0 (PyGObject)")
fi

if ! check_python_module "GtkLayerShell" "0.1"; then
    MISSING_DEPS+=("gtk-layer-shell")
fi

if ! check_python_module "Pango" "1.0"; then
    MISSING_DEPS+=("Pango / PangoCairo")
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Missing dependencies detected:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "   - $dep"
    done
    echo ""

    # Distro detection and recommendation
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID="${ID:-unknown}"
        DISTRO_LIKE="${ID_LIKE:-unknown}"
    else
        DISTRO_ID="unknown"
    fi

    echo -e "${BOLD}Please install the required packages using your package manager:${NC}"
    case "$DISTRO_ID" in
        arch|manjaro|endeavouros)
            INSTALL_CMD="sudo pacman -S --needed python python-gobject gtk3 gtk-layer-shell python-cairo libnotify"
            ;;
        ubuntu|debian|pop|linuxmint)
            INSTALL_CMD="sudo apt update && sudo apt install -y python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 libnotify-bin pulseaudio-utils"
            ;;
        fedora|rhel)
            INSTALL_CMD="sudo dnf install -y python3 python3-gobject gtk3 gtk-layer-shell python3-cairo libnotify"
            ;;
        opensuse*|suse)
            INSTALL_CMD="sudo zypper install -y python3 python3-gobject gtk3 gtk-layer-shell python3-cairo libnotify-tools"
            ;;
        *)
            if [[ "$DISTRO_LIKE" == *"arch"* ]]; then
                INSTALL_CMD="sudo pacman -S --needed python python-gobject gtk3 gtk-layer-shell python-cairo libnotify"
            elif [[ "$DISTRO_LIKE" == *"debian"* || "$DISTRO_LIKE" == *"ubuntu"* ]]; then
                INSTALL_CMD="sudo apt update && sudo apt install -y python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 libnotify-bin pulseaudio-utils"
            elif [[ "$DISTRO_LIKE" == *"fedora"* ]]; then
                INSTALL_CMD="sudo dnf install -y python3 python3-gobject gtk3 gtk-layer-shell python3-cairo libnotify"
            else
                INSTALL_CMD="Install Python 3, PyGObject, GTK 3, and gtk-layer-shell for your distribution."
            fi
            ;;
    esac

    echo -e "   ${CYAN}${INSTALL_CMD}${NC}\n"

    read -p "Would you like to try installing them now with sudo? [y/N] " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        eval "$INSTALL_CMD"
    else
        echo -e "${YELLOW}Please install the dependencies above and run install.sh again.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ All dependencies found! (Python 3, GTK 3, GtkLayerShell, Cairo, Pango)${NC}"
fi

# 2. Set up symlinks in ~/.local/bin
echo -e "\n${BOLD}[2/5] Creating executable symlinks...${NC}"
mkdir -p "${BIN_DIR}"
chmod +x "${APP_DIR}/water_plane.py" "${APP_DIR}/renderer.py" "${APP_DIR}/sound.py"

ln -sf "${APP_DIR}/water_plane.py" "${BIN_DIR}/water-plane"
ln -sf "${APP_DIR}/water_plane.py" "${BIN_DIR}/hydrate-plane"
echo -e "${GREEN}✓ Linked: ${BIN_DIR}/water-plane${NC}"
echo -e "${GREEN}✓ Linked: ${BIN_DIR}/hydrate-plane${NC}"

# Check PATH
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    echo -e "${YELLOW}⚠️  Note: ${BIN_DIR} is not in your current PATH.${NC}"
    echo -e "   Add this line to your ~/.bashrc or ~/.zshrc:"
    echo -e "   ${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
fi

# 3. Default Configuration
echo -e "\n${BOLD}[3/5] Setting up configuration...${NC}"
mkdir -p "${CONFIG_DIR}"
if [ ! -f "${CONFIG_DIR}/config.json" ]; then
    cat << 'CONFIG_EOF' > "${CONFIG_DIR}/config.json"
{
    "interval_seconds": 3600,
    "message": "TIME TO DRINK WATER! STAY HYDRATED",
    "sound": true,
    "desktop_notification": false,
    "flight_duration": 8.0,
    "altitude": 85,
    "monitor_mode": "focused",
    "font": "Sans Bold 15"
}
CONFIG_EOF
    echo -e "${GREEN}✓ Created default config at ${CONFIG_DIR}/config.json${NC}"
else
    echo -e "${GREEN}✓ Existing config preserved at ${CONFIG_DIR}/config.json${NC}"
fi

# 4. Set up systemd user timer & service
echo -e "\n${BOLD}[4/5] Configuring systemd user timer...${NC}"
mkdir -p "${SYSTEMD_USER_DIR}"

cat << SERVICE_EOF > "${SYSTEMD_USER_DIR}/water-plane.service"
[Unit]
Description=Water Plane Hydration Reminder
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=${PY_BIN} ${BIN_DIR}/water-plane fly
Environment=DISPLAY=${DISPLAY:-:0}
Environment=WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
Environment=XDG_CURRENT_DESKTOP=${XDG_CURRENT_DESKTOP:-Hyprland}

[Install]
WantedBy=default.target
SERVICE_EOF

cat << 'TIMER_EOF' > "${SYSTEMD_USER_DIR}/water-plane.timer"
[Unit]
Description=Water Plane Hourly Hydration Reminder Timer

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
TIMER_EOF

if command -v systemctl &>/dev/null; then
    systemctl --user daemon-reload
    systemctl --user enable --now water-plane.timer
    echo -e "${GREEN}✓ Hourly timer enabled and started!${NC}"
else
    echo -e "${YELLOW}⚠️  systemctl not found. You can run 'water-plane daemon &' in your autostart instead.${NC}"
fi

# 5. Test Run
echo -e "\n${BOLD}[5/5] Testing installation...${NC}"
echo -e "Flying a quick 3-second test plane across your screen..."
"${BIN_DIR}/water-plane" fly --duration 3 || true

echo -e "\n${GREEN}${BOLD}🎉 Installation Complete!${NC}"
echo -e "${CYAN}=================================================${NC}"
echo -e "Your airplane will fly across your screen ${BOLD}every 1 hour${NC} to remind you to drink water."
echo -e "\nQuick commands:"
echo -e "  • ${BOLD}water-plane fly${NC}          - Test fly the plane right now"
echo -e "  • ${BOLD}water-plane status${NC}       - Check timer schedule and settings"
echo -e "  • ${BOLD}water-plane start -i 45m${NC} - Change interval (e.g. 45m)"
echo -e "  • ${BOLD}water-plane stop${NC}         - Stop hourly reminders"
echo -e "  • ${BOLD}./install.sh --uninstall${NC}    - Remove timer and links\n"
