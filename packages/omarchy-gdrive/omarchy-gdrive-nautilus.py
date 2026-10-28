"""Files integration for omarchy-gdrive.

- Background menu: "Add Google Drive Account…" runs the setup in a terminal.
- Item menu: "Disconnect"/"Connect Google Drive mount" on an account mount
  (~/GoogleDrive/<email>) or a Google Shared drive mount.

Installed as /usr/share/nautilus-python/extensions/omarchy-gdrive.py.
"""

import os
import re
import shutil
from pathlib import Path

from gi import require_version

require_version("Nautilus", "4.1")

from gi.repository import Gio, GObject, Nautilus  # noqa: E402

SETUP = "omarchy-gdrive-setup"
MOUNT = "omarchy-gdrive-mount"
LAUNCHER = "omarchy-launch-terminal"


def config_home():
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))


def mount_units():
    """Map every omarchy-gdrive mount point to the systemd unit that owns it."""
    units = {}
    unit_dir = config_home() / "systemd" / "user"
    try:
        unit_files = sorted(unit_dir.glob("rclone-*.service"))
    except OSError:
        return units
    for unit_file in unit_files:
        try:
            text = unit_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        match = re.search(r'^ExecStart=.* mount "[^"]*" "([^"]*)"', text, re.MULTILINE)
        if match:
            units[match.group(1)] = unit_file.stem
    return units


def path_of(file_info):
    try:
        location = file_info.get_location()
    except Exception:
        return None
    if location is None:
        return None
    path = location.get_path()
    return os.path.realpath(path) if path else None


def is_mount(path):
    try:
        return os.path.ismount(path)
    except OSError:
        return False


class OmarchyGDriveMenu(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, *args):
        files = args[-1] if args else []
        if not files:
            return []
        try:
            if len(files) != 1:
                return []
            file_info = files[0]
        except TypeError:
            return []

        path = path_of(file_info)
        if path is None or path not in mount_units():
            return []
        if shutil.which(MOUNT) is None:
            return []

        connected = is_mount(path)
        item = Nautilus.MenuItem(
            name="OmarchyGDrive::toggle_mount",
            label="Disconnect Google Drive mount"
            if connected
            else "Connect Google Drive mount",
            icon="media-playback-stop" if connected else "media-playback-start",
        )
        item.connect("activate", self._on_toggle, path, connected)
        return [item]

    def _on_toggle(self, _item, path, connected):
        helper = shutil.which(MOUNT)
        if helper is None:
            return
        # Gio.Subprocess.new does not wait, so Nautilus stays responsive.
        Gio.Subprocess.new(
            [helper, "--disconnect" if connected else "--connect", path],
            Gio.SubprocessFlags.NONE,
        )

    def _background_add_account(self):
        return not shutil.which(SETUP) or not shutil.which(LAUNCHER)

    def get_background_items(self, *args):
        if self._background_add_account():
            return []
        item = Nautilus.MenuItem(
            name="OmarchyGDrive::add_account",
            label="Add Google Drive Account…",
            icon="folder-remote",
        )
        item.connect("activate", self._on_activate)
        return [item]

    def _on_activate(self, _item):
        Gio.Subprocess.new(
            [
                "omarchy-launch-terminal",
                "bash",
                "-lc",
                SETUP
                + " --add-account || { printf '\\nPress Enter to close…'; read -r; }",
            ],
            Gio.SubprocessFlags.NONE,
        )
