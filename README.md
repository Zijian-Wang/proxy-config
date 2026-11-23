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
- Microsoft Teams meeting signaling, media, and view-only streams use `DIRECT`
  in both clients. The rules cover the Teams Worldwide endpoint sets 11 and 12
  and Microsoft's commercial-cloud streaming domains. See [Teams endpoints](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges?view=o365-worldwide#microsoft-teams)
  and [Teams proxy guidance](https://learn.microsoft.com/en-us/microsoftteams/proxy-servers-for-skype-for-business-online#recommendation-for-teams-events-optimized-for-large-audiences-and-teams-view-only-meetings).
- Claude/Anthropic and other AI tools (Perplexity, Poe, Copilot, Cursor,
  Codeium/Windsurf, Midjourney) use the shared `JP` policy, which maps to
  `JP-Auto` in Clash. In legacy Clash profiles, Grok/xAI, X, and OpenAI/ChatGPT
  also use Japan. Shadowrocket and the opt-in Clash profiles send those three
  services to `AI Platform`. Gemini, Google AI Studio, NotebookLM, Google Labs,
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

The GitHub Action runs weekly and when routing sources or generators change
on `main`. It regenerates the same `shadowrocket.conf`, including `AI Platform`,
and commits changes to that file, its QR code, and the legacy Clash providers.
The config URL and QR destination do not change.

## AI Platform

| Client | Files | Existing fallback |
| --- | --- | --- |
| Clash Verge Rev | Opt-in: `clash-ai-merge.yaml` and `clash-ai-groups.yaml` | `MATCH,All-Auto` |
| Clash App | Opt-in: `clash/personal-ai-override.js` with the subscription's original rule scheme | Subscription rules and fallback |
| Shadowrocket | [`shadowrocket.conf`](shadowrocket.conf), existing URL and QR | `FINAL,AUTO` |

AI Platform defaults to Japan and uses the normal regional groups:

| Client | Japan (default) | Three-region auto | Taiwan | United States |
| --- | --- | --- | --- | --- |
| Clash Verge Rev | `JP-Auto` | `JP-TW-US-Auto` | `TW-Auto` | `US-Auto` |
| Clash App | `Personal-JP` | `Personal-JP-TW-US-Auto` | `Personal-TW` | `Personal-US` |
| Shadowrocket | `JP` | existing `AUTO` | `TW` | `US` |

The new Clash auto groups use node names to match Japan, Taiwan, and US,
excluding recognized mixed-region names, special and rate-limited nodes, and
high-multiplier nodes. Verge's all-region `All-Auto` is unchanged. Shadowrocket
keeps its original TW/JP/US-oriented `AUTO` name filter for both AI and general
fallback; it is a naming heuristic, not a strict geographic check.

The new provider covers OpenAI/ChatGPT, Grok/xAI, and X. It runs after the
existing US rules and before the existing JP rules. Clash App also keeps
the DSH routes first. Gemini, AI Studio, Vertex, the existing broker routes,
and the Fidelity `DIRECT` exception keep their policies. In the opt-in Clash
files, the shared region groups specify `REJECT` for zero eligible nodes.
The reused groups keep their node filters. Legacy scripts, enhancements,
shared rule providers, and the NAS are unchanged.

### Mihomo requirement and rollout check

For Mihomo, use **v1.19.27 or later**. That release added customizable
`empty-fallback`. Earlier Mihomo versions used `COMPATIBLE` for an empty group,
which dials directly like `DIRECT`.
[Mihomo v1.19.27 release notes](https://github.com/MetaCubeX/mihomo/releases/tag/v1.19.27)
[Legacy direct adapter](https://github.com/MetaCubeX/mihomo/blob/v1.19.26/adapter/outbound/direct.go#L89-L99)

Before adopting these files, verify fallback behavior with the actual core
build selected on **each device**, including embedded forks. Use an isolated
synthetic fixture with zero matching nodes after filtering. Confirm that
each of the shared groups in the table above resolves to `REJECT` when
empty in Clash. Also check Gemini and a non-Fidelity broker through `US-Auto`
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

### Shadowrocket rollout and rollback

The existing [`shadowrocket.conf`](shadowrocket.conf) URL and QR code now carry
`AI Platform`. A client that automatically refreshes this config may pick up
the routing change without a new import. No node subscription change is needed.

The config contains public routing rules and groups, not servers, login
details, subscription links, or authenticated modules. OpenAI/ChatGPT, Grok,
and X use `AI Platform`. The narrower `r.openai.com` rejection, Gemini's US
route, existing broker routes (including Fidelity `DIRECT`), and
`FINAL,AUTO` stay in place.

**Not validated on iOS.** Shadowrocket now uses the normal groups without an
explicit `REJECT` member. Its behavior when no node name matches is not verified;
do not assume it fails closed. To roll back the published change, revert the
rollout commit and refresh the same URL.

Build and test the Clash files locally with Python 3.10 or later. Node.js 18
or later also runs the script behavior test.

```sh
python3 scripts/build_ai_routing.py
python3 -m unittest discover -s tests -v
```

The opt-in Clash files reference the AI provider on `main`; the provider
must be present there before adopting those files.
