# omarchy-pkgs

Pacman repository for Omarchy packages, built and published with GitHub Pages:
<https://skystone-studio.github.io/omarchy-pkgs>.

## Add the repository

```bash
sudo tee -a /etc/pacman.conf >/dev/null <<'EOF'

[omarchy-pkgs]
SigLevel = Optional TrustAll
Server = https://skystone-studio.github.io/omarchy-pkgs/x86_64
EOF
sudo pacman -Syyu
```

Then install a package:

```bash
sudo pacman -S omarchy-gdrive
```

The database is unsigned, hence `SigLevel = Optional TrustAll`. The site is
HTTPS-only, so transport integrity is still enforced by TLS.

## Packages

| Package | Description |
|---|---|
| `omarchy-gdrive` | Google Drive accounts mounted under `~/GoogleDrive/<email>` and listed in Files |
| `omarchy-agent-usage-omp` | omp (Oh My Pi) usage collector for the omarchy agents bar widget |

Package sources live in `packages/<name>/` with a normal `PKGBUILD`.

## Publishing

1. Add or update `packages/<name>/` (bump `pkgver`, run `updpkgsums` in that
   directory, refresh any hand-written `.SRCINFO`).
2. `./build-repo.sh` locally to check the build (writes the ignored `repo/`).
3. Commit and push to `main`. The `pages` workflow builds every package inside
   an `archlinux:base-devel` container, writes `repo/x86_64` with `repo-add`,
   and deploys it.
4. Clients pick the new version up with `sudo pacman -Syu`.

The workflow keeps `.BUILDINFO` limited to container packages, so published
packages do not expose the builder's installed software.
