"""Add an "Add Google Drive Account…" item to the Files background menu.

Installed as /usr/share/nautilus-python/extensions/omarchy-gdrive.py by the
omarchy-gdrive package. The item only appears when omarchy-gdrive-setup and a
terminal launcher are installed.
"""

import shutil

from gi import require_version

require_version("Nautilus", "4.1")

from gi.repository import Gio, GObject, Nautilus  # noqa: E402

COMMAND = "omarchy-gdrive-setup --add-account"


class OmarchyGDriveMenu(GObject.GObject, Nautilus.MenuProvider):
    def get_file_items(self, *args):
        return []

    def get_background_items(self, *args):
        if not shutil.which("omarchy-gdrive-setup") or not shutil.which(
            "omarchy-launch-terminal"
        ):
            return []
        item = Nautilus.MenuItem(
            name="OmarchyGDrive::add_account",
            label="Add Google Drive Account…",
            icon="folder-remote",
        )
        item.connect("activate", self._on_activate)
        return [item]

    def _on_activate(self, _item):
        # Gio.Subprocess.new does not wait, so Nautilus stays responsive.
        Gio.Subprocess.new(
            [
                "omarchy-launch-terminal",
                "bash",
                "-lc",
                COMMAND + " || { printf '\\nPress Enter to close…'; read -r; }",
            ],
            Gio.SubprocessFlags.NONE,
        )
