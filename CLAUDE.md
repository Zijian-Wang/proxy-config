# Context for Claude

## Home network / NAS

- NAS: QNAP TS-X64, hostname `Z-QNAP`, LAN IP `192.168.0.106` (LAN is `192.168.0.0/24`).
  Reach it with `ssh qnap` (alias already set up on the Mac).
- Docker is not on PATH on the NAS. Use
  `/share/CACHEDEV1_DATA/.qpkg/container-station/bin/docker`.
- Containers: `mihomo-1` (host network, `unless-stopped`) and `home-assistant-1`.

## mihomo on the NAS

- Config dir: `/share/Container/clash` (mounted at `/root/.config/mihomo`);
  the config is `config.yaml`. The subscription is a proxy-provider `sub`
  cached in `sub.yaml`.
- Runs TUN (`gvisor`) + fake-ip DNS listening on `192.168.0.106:53`; other
  LAN devices use the NAS as proxy/DNS. Controller/panel on port `9090`.
- **This NAS `config.yaml` is not generated from this repo.** Its
  `rule-providers` (`personal-us/jp/direct`) pull `clash/rules/*.yaml` from
  this repo's `main`, so all domain routing is edited in `source/*.list`
  (`clash-extra-rules.list` is Clash-only). The NAS config itself holds only
  `GEOIP,private`, the three RULE-SETs, `GEOSITE,cn`, `GEOIP,CN` and `MATCH`.
  Proxy groups (`PROXY`, `JP-Auto`, `US-Auto`), health-check settings and DNS
  are edited directly on the NAS. The `clash-*.yaml` files at the repo root
  are for Clash Verge on the Mac. The subscription's own rules/groups are not
  used by the NAS (the provider only exposes its nodes).
- Never commit the subscription URL or controller `secret`.
- Image is `docker.io/metacubex/mihomo:latest` (Docker Hub pulls work from
  the NAS; the old Huawei `swr.cn-north-4…` mirror was stale and dropped).
  The container is plain `docker run` (no compose); its exact flags live in
  `run_mihomo()` in `nas/mihomo-update.sh`.
- Dashboard: zashboard at `http://192.168.0.106:9090/ui/`, files in
  `ui/zashboard/` in the config dir (`external-ui: ui`,
  `external-ui-name: zashboard`). mihomo's own `/upgrade/ui` goes direct and
  times out on GitHub, so the script below fetches it via the proxy instead.

### Nightly auto-update

`nas/mihomo-update.sh` (installed at `/share/Container/mihomo-update/update.sh`,
log `update.log` next to it) runs from cron at 03:14 (NAS TZ is UTC+8 =
Taipei). It pulls `:latest`, and only if the image changed: validates
`config.yaml` with the new core, recreates `mihomo-1`, and rolls back to the
old container if the controller/DNS aren't healthy within 60s. Then it
updates zashboard if a new release exists. `DRY_RUN=1` skips all switching.
The cron line lives in `/etc/config/crontab`; reloading it needs root
(`sudo crontab /etc/config/crontab && sudo /etc/init.d/crond.sh restart`).
After editing the script here, `scp` it to the NAS.

### Editing the NAS config

1. Back up: `cp config.yaml config.yaml.bak-<date>` (in the config dir).
2. Edit, then validate:
   `docker exec mihomo-1 /mihomo -t -d /root/.config/mihomo`
3. Restart (`docker restart mihomo-1`) — this briefly cuts the LAN's proxy
   and DNS, so confirm with the user first.

### Group settings that matter

Region groups are `url-test` with an HTTPS `generate_204` URL,
`lazy: false`, `tolerance: 50`, `interrupt-exist-connections: true`
(without it, connections stay on a degraded node until the container is
restarted). Keep test URLs on HTTPS to avoid mihomo's warning.
