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
   `rules` list while keeping its nodes and groups. It sends `maxon.net` to
   `DIRECT` first, checks the US, JP, and DIRECT rule sets in that order,
   then sends unmatched traffic to
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

## Opt-in AI Platform

| Client | Files | Existing fallback |
| --- | --- | --- |
| Clash Verge Rev | `clash-ai-merge.yaml` and `clash-ai-groups.yaml` | `MATCH,All-Auto` |
| Clash App | `clash/personal-ai-override.js` with the subscription's original rule scheme | Subscription rules and fallback |
| Shadowrocket | Local preview only | `FINAL,AUTO` in the preview |

`AI Platform` starts on **AI JP Auto**. Select **AI Auto** to test eligible
Japan, Taiwan, and US nodes together, or choose **AI TW Auto** or **AI US
Auto** for a single region. The filters use the subscription's node names.
They exclude special, rate-limited, and high-multiplier nodes, plus recognized
mixed or out-of-region labels. On clients that offer pinning in a `url-test`
group, pin a member there if needed.

The new provider covers OpenAI/ChatGPT, Grok/xAI, and X. It runs after the
existing US rules and before the existing JP rules. Clash App also keeps
the DSH routes first. Gemini, AI Studio, Vertex, the existing broker routes,
and the Fidelity `DIRECT` exception keep their policies. In the opt-in files,
Verge's `US-Auto` and Clash App's `Personal-US` reject when zero eligible US
nodes match. Their filters and normal node selection stay the same. Legacy
scripts, enhancements, shared rule providers, and the NAS keep their existing
files. The scheduled Shadowrocket generation remains on the legacy path.

### Core requirement and rollout check

For Mihomo, use **v1.19.27 or later**. That release added customizable
`empty-fallback`. Earlier Mihomo versions used `COMPATIBLE` for an empty group,
which dials directly like `DIRECT`.
[Mihomo v1.19.27 release notes](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.27)
[Legacy direct adapter](https://github.com/MetaCubeX/mihomo/blob/v1.19.26/adapter/outbound/direct.go#L89-L99)

Before adopting these files, verify fallback behavior with the actual core
build selected on **each device**, including embedded forks. Use an isolated
synthetic fixture with zero matching nodes after filtering. Confirm that
`AI JP Auto`, `AI TW Auto`, `AI US Auto`, and `AI Auto` resolve to `REJECT`
when empty. Also check Gemini and a non-Fidelity broker through `US-Auto`
(Verge) or `Personal-US` (Clash App) with zero eligible US nodes. The core must
reject those routes without dialing directly or selecting another region.
Keep the current profile on any device where this behavior cannot be verified.

A successful configuration parse checks acceptance only. It does not verify
the selected outbound or a rejected connection. A group with eligible members
that all fail their health checks is a separate case from a zero-match group.

The reference Mac Verge installation selects its bundled Mihomo v1.19.33.
Earlier offline parser checks with that version passed. The updated tests
check the generated policy and rule selection with synthetic fixtures. The
per-device rejection check is still required.

### Shadowrocket preview

For Shadowrocket, the legacy file sends Grok and X to JP. Its base rules
handle OpenAI. The local preview moves Grok and X to `AI Platform` and adds
the five OpenAI suffixes already known to Clash, with the existing narrower
rejection for `r.openai.com` ahead of the new suffix. Public release notes do
not establish how an empty filtered `url-test` group handles the explicit
`REJECT` member, or whether that member can win a health test. Keep the
preview for review until the app's behavior is confirmed.

Build and test the Clash files locally with Python 3.10 or later. Node.js 18
or later also runs the script behavior test.

```sh
python3 scripts/build_ai_routing.py
python3 -m unittest discover -s tests -v
```

For local Shadowrocket review, add `--shadowrocket-draft PATH` and choose a
new file path outside the checkout. The generator does not publish a
Shadowrocket artifact. The opt-in Clash files reference the AI provider on
`main`; the provider must be present there before adopting those files.
