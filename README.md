# Proxy Config

- [`clash/verge-subscription-overlay.js`](clash/verge-subscription-overlay.js)
  is the recommended Clash Verge Rev enhancement on Windows. It adds personal
  exceptions to the subscription's own rules.
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
  also use Japan and Gemini uses the shared US policy. Shadowrocket and the
  opt-in Clash profiles send those three services and `gemini.google.com` to
  `AI Platform`. The Windows overlay sends that same list to the subscription's
  `🤖 AI平台` group when available. Google AI Studio, the Gemini API used by
  AI Studio, NotebookLM, Google Labs, Gemini Code Assist, and the listed
  Vertex AI APIs still use the shared `US` policy. Google sign-in and
  static-resource hostnames retain their existing routes.
- Meta products (Muse/Meta AI, Facebook, Instagram, WhatsApp, Messenger,
  Threads, Quest) use the shared `US` policy. The macOS Muse app also gets a
  `PROCESS-NAME,Muse` fallback, so endpoints outside the listed domains still
  take the US route.
- DeepSeek (official site/web app, platform, API, API docs, CDN, downloads,
  status) and the DeepSeek Harness desktop app (API, login, update feed, and
  telemetry on `deepseeksvc.com`) use `DIRECT` in both clients.
- Legacy personal regional policies use the named automatic (`url-test`) groups.
  The Windows overlay uses the subscription's own group types and choices.
- Logitech Options+ domains use `DIRECT`; Clash also has process-name fallbacks
  for the Options+ app, agent, updater, and Electron helpers.
- Hugging Face China mirror (`hf-mirror.com`) uses `DIRECT`.

## Clash Verge Rev on Windows

Use the original subscription and install the
[`verge-subscription-overlay.js`](clash/verge-subscription-overlay.js) script.
It keeps the subscription's groups, rule providers, and fallback such as
`MATCH`. It inserts the personal rules after recognized LAN and ad-blocking
rules. Only unprotected rules with an identical matcher and options are
replaced. All other subscription rules keep their relative order.

1. Test on a local copy of the subscription first. Back up any current
   enhancements and remove the old personal snippets from **Global Extend
   Config** and the profile's **Extend Config** (Merge). In **Edit Proxy
   Groups**, remove the old personal `prepend` / `append` entries. Also clear
   the old personal Rules enhancement, if installed. Do this for either legacy
   Merge/Groups pair and keep each profile's original subscription.
2. Open **Profiles → Global Extend Script** (订阅 → 全局扩展脚本), paste the
   contents of the generated JavaScript file, and save. This applies to every
   profile on that Windows client. To limit the change to one test profile,
   paste the script into that profile's **Extend Script** instead. Use one
   script slot and remove any previous personal override from the other slot.
3. Reactivate the profile and open **View Runtime Config**. Check the
   subscription groups, `cn_domain`, `cn_ip`, and the original `MATCH`.
   In the global Script card's **Script Console**, check for warnings about
   missing groups or broad rules ahead of LAN/ad rules.
4. On Windows with TUN on, verify new connections for
   `filecdn.minimax.chat` → `DIRECT`, Gemini and ChatGPT → `🤖 AI平台`,
   a non-Fidelity broker → `US-Auto`, and Fidelity → `DIRECT`.
   Change the AI group's selection in **Proxies** and check a new connection.
   Confirm the approved US exit and existing LAN/ad routing before switching
   your regular profile.

If `🤖 AI平台` is missing, the AI entries use the subscription's own routing.
If `US-Auto` is missing, the script inserts `REJECT` for the fixed broker
domains and skips other personal US rules. Without `JP-Auto`, the personal JP
rules use subscription routing. These checks use exact group names and do
not create groups. The script warns when it detects a broad rule before a
recognized LAN/ad rule. Earlier rules can still win in that layout. Review
the first match, including the broker routes, before relying on the overlay.

To roll back, restore the backed-up script or use the default script that
returns `config`, then reactivate the profile. Restore the old Merge/Groups
only if returning to that compatibility setup.

### Compatibility Merge and Groups

For the legacy full-routing setup, install these two enhancements together:

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
setup and remove the Windows overlay from the global Script slot if installed.
The optional `clash-remote-override.yaml` is for keeping
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
runs `scripts/build_clash_rule_providers.py` and `scripts/build_ai_routing.py`.
To update the Windows overlay, paste the regenerated script and reactivate the
profile. For compatibility Merge or Groups changes, refresh those enhancements.

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
| Clash Verge Rev on Windows | Subscription overlay with `🤖 AI平台` | Original subscription fallback |
| Clash Verge Rev compatibility setup | Opt-in: `clash-ai-merge.yaml` and `clash-ai-groups.yaml` | `MATCH,All-Auto` |
| Clash App | Opt-in: `clash/personal-ai-override.js` with the subscription's original rule scheme | Subscription rules and fallback |
| Shadowrocket | [`shadowrocket.conf`](shadowrocket.conf), existing URL and QR | `FINAL,AUTO` |

The repository-managed `AI Platform` defaults to Japan and uses the following
regional groups. The Windows overlay uses the subscription's existing selector
and its current selection.

| Client | Japan (default) | Three-region auto | Taiwan | United States |
| --- | --- | --- | --- | --- |
| Clash Verge Rev compatibility setup | `JP-Auto` | `JP-TW-US-Auto` | `TW-Auto` | `US-Auto` |
| Clash App | `Personal-JP` | `Personal-JP-TW-US-Auto` | `Personal-TW` | `Personal-US` |
| Shadowrocket | `JP` | existing `AUTO` | `TW` | `US` |

The new Clash auto groups use node names to match Japan, Taiwan, and US,
excluding recognized mixed-region names, special and rate-limited nodes, and
high-multiplier nodes. Verge's all-region `All-Auto` is unchanged. Shadowrocket
keeps its original TW/JP/US-oriented `AUTO` name filter for both AI and general
fallback; it is a naming heuristic, not a strict geographic check.

Clash checks the AI provider for Gemini, OpenAI/ChatGPT, Grok/xAI, and X
before the shared US and JP rules. Clash App checks the DSH rules first.
In both Clash profiles, the shared region groups specify `REJECT` for zero
eligible nodes.

- **Clash App** — Select the AI override script if you use the legacy script.
  If you already use the AI script, update it and reapply the profile to load
  the new provider order. The provider itself refreshes daily.
  [AI override script](https://raw.githubusercontent.com/Zijian-Wang/proxy-config/refs/heads/main/clash/personal-ai-override.js)
- **Clash Verge Rev compatibility setup** — Use the AI Merge and Groups together
  for the legacy full-routing profile.
- **Shadowrocket** — Refresh the existing remote config. See the rollout notes
  below.

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
empty in Clash. Select the US option in `AI Platform` and check Gemini and an
OpenAI endpoint. Check a non-Fidelity broker through `US-Auto` (Verge) or
`Personal-US` (Clash App) with zero eligible US nodes. The core must reject
these routes without dialing directly or selecting another region.
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
details, subscription links, or authenticated modules. Gemini,
OpenAI/ChatGPT, Grok, and X use `AI Platform`. The narrower `r.openai.com`
rejection, existing broker routes (including Fidelity `DIRECT`), and
`FINAL,AUTO` stay in place.

**Not validated on iOS.** Shadowrocket now uses the normal groups without an
explicit `REJECT` member. Its behavior when no node name matches is not verified;
do not assume it fails closed. To roll back the published change, revert the
rollout commit and refresh the same URL.

Build and test the Clash files locally with Python 3.10 or later and Node.js
18 or later.

```sh
python3 scripts/build_ai_routing.py
python3 -m unittest discover -s tests -v
node --test tests/verge-subscription-overlay.test.cjs
```

The legacy opt-in Clash files reference the AI provider on `main`. The
Windows overlay bundles its personal rules in the script.
