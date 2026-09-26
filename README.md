# Proxy Config

Two client-facing files live at the repo root:

- `clash-override.yaml`: Clash Verge rule enhancement.
- `clash-remote-merge.yaml` + `clash-remote-override.yaml`: auto-updating
  Clash Verge enhancements backed by remote rule providers.
- `shadowrocket.conf`: generated Shadowrocket config.

Shadowrocket uses your custom rules first, then a domestic/foreign split with
ad blocking from Johnshall's `sr_cnip_ad.conf`.

## Routing Notes

- In Clash, broker/account domains (except Fidelity) use the subscription's `🇺🇸 美国自动`
  `url-test` group so the fastest measured US node is selected automatically.
- In Shadowrocket, broker/account domains (except Fidelity) use its separate `US` `url-test`
  group. Shadowrocket node definitions are never copied into Clash.
- Broker coverage includes Interactive Brokers, thinkorswim/Schwab, Robinhood,
  E*TRADE, Webull, tastytrade, TradeStation, and Alpaca. Rules use
  domain suffixes for broker-owned web, login, and API subdomains.
  Fidelity (`fidelity.com`) uses `DIRECT` in both clients.
- Claude/Anthropic, other AI tools (Grok/xAI, Perplexity, Poe, Copilot,
  Cursor, Codeium/Windsurf, Midjourney) and X (Twitter) use the shared `TW`
  policy, which maps to `🇹🇼 台湾自动` in Clash. In Clash only, OpenAI/ChatGPT
  uses `🇺🇸 美国自动`. Gemini follows the shared `US` policy.
- Clash routes only to automatic (`url-test`) region groups, never the manual
  ones.
- Logitech Options+ domains use `DIRECT`; Clash also has process-name fallbacks
  for the Options+ app, agent, updater, and Electron helpers.
- Hugging Face China mirror (`hf-mirror.com`) uses `DIRECT`.

## Clash Verge Rev

### Policy mapping

Shadowrocket and Clash keep separate nodes and policy groups. The shared custom
rules map only the routing intent:

| Shadowrocket policy | Current Clash policy |
| --- | --- |
| `US` | `🇺🇸 美国自动` |
| `TW` | `🇹🇼 台湾自动` |
| `DIRECT` | `DIRECT` |

`🇺🇸 美国自动` and `🇹🇼 台湾自动` perform latency-based selection among the
subscription's US and Taiwan nodes. Shadowrocket's `JP` group is still defined
but no custom rule uses it, so Clash has no Japan provider. No Shadowrocket node
definitions are copied into Clash.

### Auto-updating rules

`scripts/build_clash_rule_providers.py` converts the shared Shadowrocket custom
rule source into policy-specific Mihomo `classical` providers under
`clash/rules/`. The GitHub workflow regenerates them with `shadowrocket.conf`.

After the generated files are published to `main`, bind both enhancements to
the active Clash subscription:

1. Merge: `clash-remote-merge.yaml`
2. Rules: `clash-remote-override.yaml`

Mihomo then refreshes each provider from the repository's raw GitHub URL every
seven days. The Merge defines provider URLs; the Rules file maps each provider
to the appropriate Clash policy group. Clash-only rules stay inline in the
Rules file.

### Static rules fallback

`clash-override.yaml` is a per-subscription Rules enhancement; Clash Verge does
not read the repository file automatically.

To apply it:

1. Open **Profiles** in Clash Verge Rev.
2. Right-click the active subscription and choose **Edit Rules**.
3. Open the advanced YAML editor and replace its contents with
   `clash-override.yaml`.
4. Save, then reload/apply the subscription.
5. In **Proxies**, confirm that `🇺🇸 美国自动` and `🇹🇼 台湾自动` are `URL Test`
   groups and run their latency tests once.

Rules are matched from top to bottom, so these entries must stay in `prepend`.
The policy-group names must also match the active subscription exactly.
After applying a routing change, reconnect or restart thinkorswim so its
existing long-lived connections are recreated through the newly selected node.
`url-test` may use a different exit for new connections; if a stable account IP
matters more than latency, point the relevant rules to the matching manual group.

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

The GitHub Action runs weekly, and also runs when the shared custom-rule source
or its Clash provider generator is pushed to `main`. It commits when
`shadowrocket.conf`, its QR code, or the generated Clash rule providers change.
