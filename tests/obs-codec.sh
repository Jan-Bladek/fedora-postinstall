#!/usr/bin/env bash
# Real encoding regression test, under a disposable Fedora user account.
set -Eeuo pipefail
[[ ${FEDORA_POSTINSTALL_TEST_TARGET:-} == disposable && $EUID != 0 ]] || exit 1
source /etc/os-release
[[ $ID == fedora && $VERSION_ID =~ ^(44|45)$ ]] || exit 1
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/lib/core.sh"
source "$ROOT/modules/multimedia.sh"
RUN=$(mktemp -d)
trap 'rm -rf -- "$RUN"' EXIT
# Reproduce the stock KDE placeholder even when the fresh container's dependency
# resolver already chose the real codec. These mutations are fixture-only.
if rpm -q openh264 >/dev/null 2>&1; then
    if rpm -q mozilla-openh264 >/dev/null 2>&1; then
        sudo dnf5 -y --setopt=clean_requirements_on_remove=False remove mozilla-openh264
    fi
    sudo dnf5 -y --repo=fedora --repo=updates --setopt=clean_requirements_on_remove=False \
        --setopt=install_weak_deps=False swap openh264 noopenh264
else
    sudo dnf5 -y --repo=fedora --repo=updates --setopt=install_weak_deps=False install noopenh264
fi
rpm -q noopenh264
if ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i color=size=32x32:rate=1 \
    -frames:v 1 -c:v libopenh264 -an -f null -; then
    die 'The placeholder unexpectedly encoded H.264; the regression fixture is invalid.'
fi
rpm -qa --qf '%{NAME}\n' | sort -u > "$RUN/before"
configure_obs_codecs
configure_obs_codecs
rpm -qa --qf '%{NAME}\n' | sort -u > "$RUN/after"
comm -23 "$RUN/before" "$RUN/after" > "$RUN/removed"
while IFS= read -r package; do
    [[ $package == noopenh264 ]] || die "Unexpected removed package: $package"
done < "$RUN/removed"
ffmpeg -nostdin -hide_banner -loglevel error -f lavfi -i testsrc2=size=64x64:rate=2 \
    -frames:v 3 -c:v libopenh264 -an -y "$RUN/codec.mp4"
ffprobe -v error -count_frames -select_streams v:0 \
    -show_entries stream=codec_name,width,height,nb_read_frames -of json "$RUN/codec.mp4" > "$RUN/probe.json"
cat "$RUN/probe.json"
python3 - "$RUN/probe.json" <<'PY'
import json, sys
stream = json.load(open(sys.argv[1]))['streams'][0]
if (stream['codec_name'], stream['width'], stream['height'], int(stream['nb_read_frames'])) != ('h264', 64, 64, 3):
    raise SystemExit('H.264 round trip failed')
PY
sudo dnf5 check
