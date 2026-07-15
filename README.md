# Proxy Config

Two client-facing files live at the repo root:

- `clash-override.yaml`: Clash Verge rule enhancement.
- `shadowrocket.conf`: generated Shadowrocket config.

Shadowrocket uses your custom rules first, then a domestic/foreign split with
ad blocking from Johnshall's `sr_cnip_ad.conf`.

## Routing Notes

- In Clash, broker/account domains use the subscription's `🇺🇸 美国自动`
  `url-test` group so the fastest measured US node is selected automatically.
- In Shadowrocket, broker/account domains use the manually selected `US-STABLE`
  group to preserve a stable account IP.
- Broker coverage includes Interactive Brokers, thinkorswim/Schwab, Robinhood,
  Fidelity, E*TRADE, Webull, tastytrade, TradeStation, and Alpaca. Rules use
  domain suffixes for broker-owned web, login, and API subdomains.
- OpenAI/ChatGPT always uses `US-STABLE`.
- Most other AI tools use `AI-JP-TW`, which filters Japan/Taiwan nodes.
- Hugging Face China mirror (`hf-mirror.com`) uses `DIRECT`.

## Clash Verge Rev

`clash-override.yaml` is a per-subscription Rules enhancement; Clash Verge does
not read the repository file automatically.

To apply it:

1. Open **Profiles** in Clash Verge Rev.
2. Right-click the active subscription and choose **Edit Rules**.
3. Open the advanced YAML editor and replace its contents with
   `clash-override.yaml`.
4. Save, then reload/apply the subscription.
5. In **Proxies**, confirm that `🇺🇸 美国自动` is a `URL Test` group and
   run its latency test once.

Rules are matched from top to bottom, so these entries must stay in `prepend`.
The policy-group names must also match the active subscription exactly.
After applying a routing change, reconnect or restart thinkorswim so its
existing long-lived connections are recreated through the newly selected node.
If a stable account IP matters more than latency, point the broker rules back to
`🇺🇸 美国手动`; `url-test` may use a different US exit for new connections.

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

The GitHub Action runs weekly and only commits when the generated
`shadowrocket.conf` changes.
