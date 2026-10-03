#!/bin/sh
# Nightly mihomo update (cron, 03:14 Asia/Taipei).
# Pulls metacubex/mihomo:latest; if the image changed, validates config.yaml
# with the new core, recreates the container and rolls back if it does not
# come up healthy. Also refreshes the zashboard UI (fetched through the proxy;
# mihomo's own /upgrade/ui goes direct and times out on GitHub).
# DRY_RUN=1 stops before touching the running container.

set -u
D=/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker
IMG=docker.io/metacubex/mihomo:latest
NAME=mihomo-1
CONF=/share/Container/clash
API=http://127.0.0.1:9090
DNS=192.168.0.106
LOG=/share/Container/mihomo-update/update.log

[ -t 1 ] || exec >>"$LOG" 2>&1
echo "=== $(date '+%F %T')"

secret=$(sed -n 's/^secret: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$CONF/config.yaml")
api() { curl -fsS -m 10 ${secret:+-H "Authorization: Bearer $secret"} "$@"; }

run_mihomo() {
  $D run -d --name "$NAME" --restart unless-stopped --network host \
    --cap-add NET_ADMIN --device /dev/net/tun \
    --log-opt max-size=10m --log-opt max-file=10 \
    -v "$CONF:/root/.config/mihomo" "$1"
}

healthy() {
  i=0
  while [ $i -lt 12 ]; do
    sleep 5; i=$((i + 1))
    [ "$($D inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" = true ] || continue
    api "$API/version" >/dev/null 2>&1 || continue
    nslookup www.google.com "$DNS" >/dev/null 2>&1 && return 0
  done
  return 1
}

update_core() {
  $D pull -q "$IMG" || { echo "pull failed"; return 1; }
  new=$($D image inspect -f '{{.Id}}' "$IMG")
  cur=$($D inspect -f '{{.Image}}' "$NAME" 2>/dev/null)
  newver=$($D run --rm --entrypoint /mihomo "$IMG" -v 2>/dev/null | sed -n 1p)
  if [ "$new" = "$cur" ]; then echo "core up to date: $newver"; return 0; fi

  if ! $D run --rm --network none -v "$CONF:/root/.config/mihomo" \
      --entrypoint /mihomo "$IMG" -t -d /root/.config/mihomo >/tmp/mihomo-test.log 2>&1; then
    echo "config test FAILED on $newver, keeping current core:"; tail -5 /tmp/mihomo-test.log
    return 1
  fi
  echo "updating core -> $newver"
  [ "${DRY_RUN:-0}" = 1 ] && { echo "dry run, not switching"; return 0; }

  $D rm -f "$NAME-old" >/dev/null 2>&1
  $D stop "$NAME" >/dev/null && $D rename "$NAME" "$NAME-old"
  if run_mihomo "$IMG" >/dev/null && healthy; then
    $D rm "$NAME-old" >/dev/null
    $D image prune -f >/dev/null
    echo "core updated OK"
  else
    echo "new core unhealthy, rolling back"; $D logs --tail 20 "$NAME"
    $D rm -f "$NAME" >/dev/null
    $D rename "$NAME-old" "$NAME" && $D start "$NAME" >/dev/null
    return 1
  fi
}

update_ui() {
  ui=$CONF/ui/zashboard
  tag=$(curl -fsS -m 30 -x http://127.0.0.1:7890 \
    https://api.github.com/repos/Zephyruso/zashboard/releases/latest |
    sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p')
  [ -n "$tag" ] || { echo "ui: release lookup failed"; return 1; }
  [ "$tag" = "$(cat "$ui/.version" 2>/dev/null)" ] && { echo "ui up to date: $tag"; return 0; }
  [ "${DRY_RUN:-0}" = 1 ] && { echo "ui: would update to $tag"; return 0; }

  tmp=$CONF/ui/.tmp; rm -rf "$tmp"; mkdir -p "$tmp"
  if curl -fsSL -m 600 -x http://127.0.0.1:7890 -o "$tmp/dist.zip" \
      https://github.com/Zephyruso/zashboard/releases/download/$tag/dist.zip &&
      unzip -q "$tmp/dist.zip" -d "$tmp" && [ -f "$tmp/dist/index.html" ]; then
    echo "$tag" > "$tmp/dist/.version"
    rm -rf "$ui.old"; mv "$ui" "$ui.old" 2>/dev/null
    mv "$tmp/dist" "$ui" && rm -rf "$ui.old"
    echo "ui updated -> $tag"
  else
    echo "ui: download failed"
  fi
  rm -rf "$tmp"
}

update_core
update_ui

# Keep the log short.
tail -n 500 "$LOG" > "$LOG.tmp" 2>/dev/null && mv "$LOG.tmp" "$LOG"
