# Google Drive for Omarchy Files

Mounts every Google Drive account as its own local FUSE filesystem with
[rclone](https://rclone.org/drive/) and lists each one in the Nautilus sidebar
under its email address. Every mount is managed by its own systemd user service
and starts at login.

## Features

- Every account is mounted at `~/GoogleDrive/<email>` and every Google Shared
  drive at `~/GoogleDrive/Shared drives/<email>/<drive>`, each with its own
  systemd user service.
- One **Google Drive** sidebar entry; accounts and shared drives are folders
  inside it.
- Right-click a mounted account or shared drive in Files to **Disconnect** or
  **Connect** it.
- **Add Google Drive Account…** in the Files background right-click menu
  authorizes one more account and creates its mount, service, and sidebar
  entry.
- Files, folders, and Google Docs in **My Drive** are browsable.
- systemd user services start the mounts at login and retry on failure.
- 10 GiB local VFS cache and a 1 hour directory cache for normal file-manager
  behaviour (thumbnails, editors, renames, deletes).
- Setup script handles OAuth, the mount point, the service, and the bookmark,
  and re-runs safely.

Only **My Drive** is mounted. Google Drive's "Shared with me" view and
Workspace shared drives are not included by default; they need separate rclone
remotes/mounts.

## Requirements

- Omarchy (Arch Linux) with Nautilus and a systemd user session
- `rclone`, `fuse3`, `python`, `nautilus`, and `nautilus-python` (installed as
  package dependencies)
- A Google account

## Install

From the built architecture-independent package:

```bash
sudo pacman -S --needed rclone fuse3 python nautilus nautilus-python
sudo pacman -U omarchy-gdrive-0.2.0-1-any.pkg.tar.zst
```

Or build from source:

```bash
tar -xzf omarchy-gdrive-0.2.0.tar.gz
cd omarchy-gdrive-0.2.0
makepkg -si
```

Files loads extensions at startup, so reopen it once after installing:

```bash
nautilus --quit
```

## First run

```bash
omarchy-gdrive-setup
```

You can also launch **Google Drive Setup** from the Omarchy launcher, or
right-click an empty area in Files and choose **Add Google Drive Account…** -
the same command adds the first account.

The run opens the default browser for Google authorization. After approval it
creates:

- `~/GoogleDrive/<email>` - the mounted Drive
- `~/.config/systemd/user/rclone-<remote>.service` - the mount service for that
  account
- a **Google Drive** bookmark for `~/GoogleDrive` in
  `~/.config/gtk-3.0/bookmarks`
- `~/.config/omarchy-gdrive/accounts.tsv` - the `email <TAB> remote` mapping
- `~/.local/state/omarchy-gdrive/setup.log` - setup diagnostics

Files may need to be reopened once after the first mount:

```bash
nautilus --quit
```

Then open **Files** again.

## Shared drives

Google Shared drives (formerly Team drives) are separate Drive roots, so each
one gets its own mount beside the account's My Drive mount:

```text
~/GoogleDrive/marcelo@example.com                     My Drive
~/GoogleDrive/Shared drives/marcelo@example.com/Clients
~/GoogleDrive/Shared drives/marcelo@example.com/Corporate
```

`omarchy-gdrive-setup` lists the drives with `rclone backend drives` on every
run, writes one `rclone-<remote>-shared-<drive>.service` per drive, and adds a
`<drive> (<email>)` bookmark for each mounted drive. Drives that disappear from
the account are unmounted, and their units and bookmarks are removed.

| Variable | Default | Effect |
|---|---|---|
| `GDRIVE_SHARED_DRIVES` | `on` | `off` stops and removes every shared-drive mount |
| `GDRIVE_SHARED_WITH_ME` | `off` | `1` adds a `~/GoogleDrive/Shared with me/<email>` mount using `--drive-shared-with-me` |

Every mount keeps its own 10 GiB VFS cache budget, so N shared drives can use up
to N x 10 GiB of `~/.cache/rclone` under heavy offline use. Lower
`--vfs-cache-max-size` in the generated units if that matters.

Listing shared drives costs one Drive API call per account per run. With
rclone's shared OAuth client that call can take 15-30 s, which makes a setup run
with several drives slower than the My Drive-only version; a user OAuth client
makes it fast.

## Connect and disconnect

Files shows one **Google Drive** entry. Inside it, each account mount and each
shared-drive mount is a folder; right-click one and choose **Disconnect Google
Drive mount**, or **Connect Google Drive mount** when it is down. The same helper
is available on the command line:

```bash
omarchy-gdrive-mount --status     ~/GoogleDrive/<email>
omarchy-gdrive-mount --disconnect ~/GoogleDrive/<email>
omarchy-gdrive-mount --connect    ~/GoogleDrive/<email>
```

Disconnecting stops the mount and disables its systemd unit, so it stays down
across logins. `omarchy-gdrive-setup` re-enables and starts it again; that is the
repair path, so a full setup run undoes a manual disconnect.

## Add an account

Right-click an empty area in Files and choose **Add Google Drive Account…**. A
terminal opens and runs:

```bash
omarchy-gdrive-setup --add-account
```

Authorize the additional Google account in the browser. Its email address
becomes the folder name and the sidebar label, so two accounts never collide.
Re-running it for an account that is already configured only refreshes its
token:

```
Account name@example.com is already configured; token updated.
```

New rclone remotes are named `gdrive-<slug>-<hash8>`, where the slug comes from
the email's local part and `hash8` is the first eight hex characters of
`sha256(email)`. The very first account keeps the plain `gdrive` remote name.

## Upgrade from 0.1.0

0.1.0 mounted a single account at `~/GoogleDrive` and labelled it
`Google Drive`. After upgrading, run:

```bash
omarchy-gdrive-setup
```

It stops the old service, unmounts `~/GoogleDrive`, creates the mount at
`~/GoogleDrive/<email>`, and rewrites the bookmark and the systemd unit. It
also adopts `gdrive` and `gdrive-*` remotes that are not yet recorded in
`accounts.tsv`.

If you previously used `GDRIVE_REMOTE`/`GDRIVE_MOUNT`/`GDRIVE_LABEL` for extra
accounts, those variables are gone. Drop them from your shell configuration and
run the default mode instead: every `gdrive-*` Drive remote is discovered and
mounted at `~/GoogleDrive/<email>`.

## Reauthorize

```bash
omarchy-gdrive-setup --reauth                     # only account, or the legacy gdrive remote
omarchy-gdrive-setup --reauth name@example.com
omarchy-gdrive-setup --reauth gdrive-name-1a2b3c4d
```

With several accounts configured, pass an email address or an rclone remote
name. The script refuses to bind a remote to a different Google account than
the one it already belongs to.

## Manage

```bash
rclone listremotes                                # configured remotes
systemctl --user status rclone-<remote>.service
journalctl --user -u rclone-<remote>.service -n 50 --no-pager
systemctl --user restart rclone-<remote>.service
mountpoint ~/GoogleDrive/<email>
```

`~/GoogleDrive` itself is only a container for the per-account mounts.
`GDRIVE_ROOT` overrides that container if you want the accounts elsewhere:

```bash
GDRIVE_ROOT="$HOME/Drive" omarchy-gdrive-setup
```

## OAuth client: recommended for reliable use

Without your own OAuth client, the script uses rclone's shared Google client.
That client is heavily rate-limited and rclone is retiring it during 2026.
Browsing can stall or fail with `RATE_LIMIT_EXCEEDED`.

Create your own Desktop OAuth client once:

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project and enable the
   [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com).
3. Configure the OAuth consent screen:
   - **Internal** for a Google Workspace account, or
   - **External** for a personal account. External apps in **Testing** issue
     refresh tokens that expire after 7 days; publish the app or use Internal
     for a long-lived token.
4. Go to **Credentials** -> **Create credentials** -> **OAuth client ID** ->
   **Desktop app**, then copy the client ID and client secret.
5. Add them to the first account's remote and re-authorize:

```bash
rclone config update gdrive client_id "<CLIENT_ID>" client_secret "<CLIENT_SECRET>"
omarchy-gdrive-setup --reauth
```

Later accounts reuse that client automatically: the setup script passes it to
`rclone authorize` and writes it into the new remote section, because refreshing
a token requires the client that issued it. Tokens are written to
`~/.config/rclone/rclone.conf` (mode `0600`) and are never printed by the setup
script.

## Troubleshooting

- **No "Add Google Drive Account…" item in Files**: `nautilus-python` must be
  installed and Files must be restarted (`nautilus --quit`). The item is hidden
  when `omarchy-gdrive-setup` is not on `PATH`.
- **No Connect/Disconnect entry when right-clicking a drive folder**: the item
  only appears for the mount point itself, single selection, and when
  `omarchy-gdrive-mount` is on `PATH`. Restart Files after upgrading the package.
- **Files shows "Loading..." or an empty folder after setup**: quit and reopen
  Files (`nautilus --quit`). Nautilus can cache the empty mount point from
  before the mount existed.
- **`RATE_LIMIT_EXCEEDED`, 403, or long stalls**: switch to your own OAuth
  client as described above.
- **A shared drive is missing**: `systemctl --user status
  rclone-<remote>-shared-<drive>.service`. A drive you were removed from is
  dropped on the next `omarchy-gdrive-setup`; a newly granted drive appears on the
  next run.
- **Stale FUSE mount** (`Transport endpoint is not connected`): the setup
  script clears it automatically. Manually:
  `fusermount3 -uz ~/GoogleDrive/<email>`, then rerun `omarchy-gdrive-setup`.
- **Google Docs appear as `.docx`, `.xlsx`, or `.pptx`**: rclone exports Google
  Docs formats. Editing the exported file creates an Office file rather than
  editing the Google Doc.
- **Token expired or revoked**: `omarchy-gdrive-setup --reauth <email>`.
- **The setup says an account email could not be resolved**: the token is
  unusable. Reauthorize that account with `--reauth`.
- **Service fails before the network is ready**: the unit restarts every 10
  seconds; it does not need a manual restart.

## Security

- OAuth tokens remain only in `~/.config/rclone/rclone.conf`, which is mode
  `0600`. The setup script never prints them, and the log does not contain
  them.
- `~/.config/omarchy-gdrive/accounts.tsv` (mode `0600`, parent directory `0700`)
  contains email addresses and rclone remote names only.
- Revoke access at <https://myaccount.google.com/permissions>.
- Do not share `~/.config/rclone/rclone.conf`.

## Uninstall

```bash
for unit in ~/.config/systemd/user/rclone-*.service; do
  systemctl --user disable --now "$(basename "$unit")"
done
rm ~/.config/systemd/user/rclone-*.service
systemctl --user daemon-reload
sudo pacman -R omarchy-gdrive
```

The package does not own per-user data, so it leaves these behind:

- `~/GoogleDrive/<email>` folders (one per account)
- `~/GoogleDrive/Shared drives/` and `~/GoogleDrive/Shared with me/` mounts and
  their empty parent folders
- `~/.config/omarchy-gdrive/` (`accounts.tsv`, `setup.lock`)
- `~/.config/rclone/rclone.conf` (remove only the `gdrive*` sections if you use
  other rclone remotes)
- the **Google Drive** line in `~/.config/gtk-3.0/bookmarks`
- `~/.local/state/omarchy-gdrive/`

Delete them by hand after unmounting (`fusermount3 -uz ~/GoogleDrive/<email>`).

## How it works

The package installs a setup script, a Nautilus extension, a launcher entry, and
documentation. For every account the script writes a systemd unit that runs:

```bash
rclone mount gdrive-<slug>-<hash>: ~/GoogleDrive/<email> --vfs-cache-mode full ...
```

The service uses systemd `Type=notify`, so it is considered started only after
the FUSE mount is ready. The Files sidebar entries are GTK bookmarks pointing at
the account mount points.

## Development

```bash
bash -n omarchy-gdrive-setup
bash -n omarchy-gdrive-mount
python3 -c 'compile(open("omarchy-gdrive-nautilus.py").read(), "x", "exec")'
updpkgsums
makepkg --printsrcinfo > .SRCINFO
makepkg -f
```

The `PKGBUILD` builds from the files in this directory. This repository also
holds the published pacman repository: the `pages` workflow builds every package
inside an `archlinux:base-devel` container and deploys it to GitHub Pages.

```ini
[omarchy-pkgs]
SigLevel = Optional TrustAll
Server = https://skystone-studio.github.io/omarchy-pkgs/x86_64
```

Do not commit `dist/`, `pkg/`, `repo/`, or `src/`.

## License

MIT. See `LICENSE`.
