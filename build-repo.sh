#!/usr/bin/env bash
# Build every packages/*/PKGBUILD and refresh the pacman repository in
# repo/x86_64, so GitHub Pages can serve it.
#
#   ./build-repo.sh              unsigned database
#   ./build-repo.sh --sign       sign the database with the default GPG key
#   ./build-repo.sh --key KEY    sign the database with KEY
set -euo pipefail
shopt -s nullglob

root="$(cd -- "$(dirname -- "$0")" && pwd)"
repo="$root/repo/x86_64"
db="$repo/omarchy-pkgs.db.tar.gz"

sign=false
key=""
while (( $# > 0 )); do
  case "$1" in
    --sign) sign=true ;;
    --key) key="${2:-}"; [[ -n "$key" ]] || { printf 'error: --key needs a key id\n' >&2; exit 2; }; shift ;;
    -h|--help) sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'error: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

packager="${PACKAGER:-SkyStone-Studio}"
mkdir -p "$repo"

for dir in "$root"/packages/*/; do
  [[ -f "$dir/PKGBUILD" ]] || continue
  printf '\n==> %s\n' "${dir%/}"
  ( cd "$dir" && PACKAGER="$packager" makepkg -f --nodeps )

  pkgname="$(sed -n 's/^pkgname=//p' "$dir/PKGBUILD")"
  pkgver="$(sed -n 's/^pkgver=//p' "$dir/PKGBUILD")"
  pkgrel="$(sed -n 's/^pkgrel=//p' "$dir/PKGBUILD")"

  cp -f "$dir/$pkgname-$pkgver-$pkgrel"-*.pkg.tar.zst "$repo/"
  # Keep one version per package so the published repository stays small.
  find "$repo" -maxdepth 1 -name "$pkgname-*.pkg.tar.zst" \
    ! -name "$pkgname-$pkgver-$pkgrel-*.pkg.tar.zst" -delete
done

packages=("$repo"/*.pkg.tar.zst)
((${#packages[@]})) || { printf 'error: no packages built\n' >&2; exit 1; }

args=(--remove)
[[ "$sign" == true ]] && args+=(--sign)
[[ -n "$key" ]] && args+=(--key "$key")
repo-add "${args[@]}" "$db" "${packages[@]}"

# Static hosts such as GitHub Pages do not preserve the .db/.files symlinks
# that repo-add creates, so publish real copies.
for link in "$repo"/*.db "$repo"/*.files; do
  [[ -L "$link" ]] || continue
  target="$(readlink -f "$link")"
  rm -f "$link"
  cp -p "$target" "$link"
done
find "$repo" -maxdepth 1 -name '*.old' -delete

printf '\nRepository ready in %s:\n' "$repo"
ls -1 "$repo"
