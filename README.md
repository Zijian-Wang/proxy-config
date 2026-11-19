# Proxy Config

- `clash-remote-merge.yaml` + `clash-remote-groups.yaml`: recommended Clash
  Verge Rev enhancements with a complete routing policy and remote rule sets.
- `shadowrocket.conf`: generated Shadowrocket config.

Shadowrocket uses your custom rules first, then a domestic/foreign split with
ad blocking from Johnshall's `sr_cnip_ad.conf`.

## Routing Notes

- In Clash Verge, broker/account domains (except Fidelity) use `US-Auto`.
  The Clash App script routes those domains to `Personal-US`.
- In Shadowrocket, broker/account domains (except Fidelity) use its separate `US` `url-test`
  group. Shadowrocket node definitions are never copied into Clash.
- Broker coverage includes Interactive Brokers, thinkorswim/Schwab, Robinhood,
  E*TRADE, Webull, tastytrade, TradeStation, and Alpaca. Rules use
  domain suffixes for broker-owned web, login, and API subdomains.
  Fidelity (`fidelity.com`) uses `DIRECT` in both clients.
- Claude/Anthropic, other AI tools (Grok/xAI, Perplexity, Poe, Copilot,
  Cursor, Codeium/Windsurf, Midjourney) and X (Twitter) use the shared `JP`
  policy, which maps to `JP-Auto` (Japan nodes) in Clash. In Clash only, OpenAI/ChatGPT
  also uses Japan. Gemini, Google AI Studio, NotebookLM, Google Labs,
  Gemini Code Assist, and the listed Vertex AI APIs follow the shared `US`
  policy. Vertex AI API hostnames are shared with other Vertex AI services;
  Google sign-in and static-resource hostnames retain their existing routes.
- Meta products (Muse/Meta AI, Facebook, Instagram, WhatsApp, Messenger,
  Threads, Quest) use the shared `US` policy. The macOS Muse app also gets a
  `PROCESS-NAME,Muse` fallback, so endpoints outside the listed domains still
  take the US route.
- DeepSeek (official site/web app, platform, API, API docs, CDN, downloads,
  status) and the DeepSeek Harness desktop app (API, login, update feed, and
  telemetry on `deepseeksvc.com`) use `DIRECT` in both clients.
- Clash routes only to automatic (`url-test`) region groups, never the manual
  ones.
- Logitech Options+ domains use `DIRECT`; Clash also has process-name fallbacks
  for the Options+ app, agent, updater, and Electron helpers.
- Hugging Face China mirror (`hf-mirror.com`) uses `DIRECT`.

## Clash Verge Rev (recommended)

Keep the existing node subscription. Open its enhancement settings and install
these two files together:

1. **Merge** (`clash-remote-merge.yaml`) replaces the subscription's entire
   `rules` list while keeping its nodes and groups. It checks the US, JP, and
   DIRECT rule sets in that order, then sends unmatched traffic to
   `MATCH,All-Auto`.
2. **Groups** (`clash-remote-groups.yaml`) adds `US-Auto`, `JP-Auto`, and
   `All-Auto` as `url-test` groups. `All-Auto` measures the subscription's
   nodes across all regions and is also used to download the rule sets.
   The region groups filter node names and exclude 特殊/限速 and ≥5x nodes.

Leave the subscription's **Rules** and **Script** enhancements empty for this
setup. If migrating an existing setup, replace Merge and Groups together and
reactivate the profile. The optional `clash-remote-override.yaml` is for keeping
the subscription's routing as a fallback. To use it, keep only the
`rule-providers` section of the Merge, install the Groups file, and put the
optional file in **Rules**.

### Policy mapping

Shadowrocket and Clash keep separate nodes and policy groups. The shared custom
rules map only the routing intent:

| Shadowrocket policy | Clash Verge policy |
| --- | --- |
| `US` | `US-Auto` |
| `JP` | `JP-Auto` |
| `DIRECT` | `DIRECT` |

### Auto-updating rules

Mihomo refreshes the three remote rule sets under `clash/rules/` every day.
Edit `source/shadowrocket-custom-rules.list` for shared rules or
`source/clash-extra-rules.list` for Clash-only rules. The GitHub workflow
runs `scripts/build_clash_rule_providers.py` to publish the generated files.
For changes to the Merge or Groups file itself, refresh those enhancements
in Clash Verge and reactivate the profile.

The provider generator skips `TAILSCALE`, Shadowrocket's built-in module.
`DSH` has a separate provider consumed by the personal override below; the
existing Clash Verge/NAS enhancements do not reference it.

## Clash App on Mac, iPhone, and iPad

Keep the existing node subscription and its original rule scheme. Under the
profile's **Override Script**, import and select:

```text
https://raw.githubusercontent.com/Zijian-Wang/proxy-config/refs/heads/main/clash/personal-override.js
```

The same script can be used as a Clash Verge Script enhancement. It preserves
subscription nodes and base routing, adds `Personal-US`, `Personal-JP`, and
`Personal-TW` region groups, and prepends the shared US/JP/DIRECT rule providers.
There are currently no personal Taiwan domain rules. DSH tunnel traffic uses
`Personal-DSH`, a Japan/US group with tolerance 10000 rather than ordinary
latency switching. Existing connections are not forcibly interrupted on auto
selection. Region membership depends on subscription node names.

Update the script in the App to receive script changes; rule providers refresh
daily. Back up **All data** to iCloud after selecting the script so the phone
can restore both the profile and its referenced script. Process rules apply on
macOS; iOS uses the corresponding domain/IP rules. Shadowrocket's authenticated
Tailscale module is not transferred by this script.

## Shadowrocket

After this repo is pushed to GitHub, the workflow generates:

```text
assets/shadowrocket-qr.png
```

Scan that QR code in Shadowrocket to add the config directly.

![Shadowrocket QR](assets/shadowrocket-qr.png)

If you want to generate the QR manually:

```bash
python3 scripts/update_qr.py --url "https://raw.githubusercontent.com/OWNER/REPO/refs/heads/main/shadowrocket.conf"
```

To rebuild manually:

```bash
python3 scripts/build_shadowrocket.py
```

To edit your personal Shadowrocket overrides, change:

```text
source/shadowrocket-custom-rules.list
```

The GitHub Action runs weekly, and also runs when the shared custom-rule source,
the Clash-only source, or the provider generator is pushed to `main`. It commits when
`shadowrocket.conf`, its QR code, or the generated Clash rule providers change.
