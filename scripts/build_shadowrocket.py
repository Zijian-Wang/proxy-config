#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import time
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import build_ai_routing as ai


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_URL = "https://johnshall.github.io/Shadowrocket-ADBlock-Rules-Forever/sr_cnip_ad.conf"
CUSTOM_RULES = ROOT / "source" / "shadowrocket-custom-rules.list"
OUTPUT = ROOT / "shadowrocket.conf"
BASE_MARKER = "# Base: Johnshall domestic/foreign split + ad blocking.\n"

HEADER = r"""[General]
bypass-system = true
skip-proxy = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local, captive.apple.com
tun-excluded-routes = 10.0.0.0/8, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4
dns-server = system
fallback-dns-server = system
ipv6 = false
prefer-ipv6 = false
private-ip-answer = true

[Proxy]
# Keep your airport/server subscription in Shadowrocket separately.
# Do not publish tokenized node definitions here unless this repo is private.

[Proxy Group]
# Region groups over nodes imported from your Shadowrocket subscription.
# Exclude "特殊" / "限速" nodes and nodes with a [rate] multiplier of 5.0 or more from every group.
# No commas inside the regex (e.g. {2,}): Shadowrocket splits group parameters on commas.
US = url-test,policy-regex-filter=^(?!.*(?:特殊|限速|\[(?:[5-9]|\d\d+)(?:\.\d+)?\])).*(美国|美國|US|USA|United States|America),url=https://www.gstatic.com/generate_204,interval=1800,timeout=5,tolerance=120
JP = url-test,policy-regex-filter=^(?!.*(?:特殊|限速|\[(?:[5-9]|\d\d+)(?:\.\d+)?\])).*(日本|Japan|JP),url=https://www.gstatic.com/generate_204,interval=1800,timeout=5,tolerance=120
AUTO = url-test,policy-regex-filter=^(?!.*(?:特殊|限速|\[(?:[5-9]|\d\d+)(?:\.\d+)?\])).*(台|台湾|台灣|Taiwan|TW|日本|Japan|JP|美国|美國|US|USA|United States|America),url=https://www.gstatic.com/generate_204,interval=1800,timeout=5,tolerance=120
# Dedicated group for the DSH Cloudflare Tunnel egress. Never use AUTO here:
# a latency-driven switch tears down cloudflared's HTTP/2 connection and the
# phone gets 1033. tolerance=10000 means the group only moves when the current
# node actually fails its health check, not on a latency win.
DSH = url-test,policy-regex-filter=^(?!.*(?:特殊|限速|\[(?:[5-9]|\d\d+)(?:\.\d+)?\])).*(日本|Japan|JP|美国|美國|US|USA|United States|America),url=https://www.gstatic.com/generate_204,interval=300,timeout=5,tolerance=10000
"""

FOOTER = """[Host]
localhost = 127.0.0.1

[URL Rewrite]

[Script]

[MITM]
hostname =
"""


def fetch_url(url: str, attempts: int = 4) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": "proxy-config-updater/1.0"})
            with urlopen(request, timeout=60) as response:
                chunks = []
                while True:
                    chunk = response.read(1024 * 64)
                    if not chunk:
                        break
                    chunks.append(chunk)
            text = b"".join(chunks).decode("utf-8")
            if "[Rule]" not in text or "[MITM]" not in text or not re.search(r"^FINAL,", text, re.M):
                raise RuntimeError("upstream content looked incomplete")
            return text
        except (OSError, URLError, UnicodeDecodeError, IncompleteRead, RuntimeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def extract_rule_section(config_text: str) -> str:
    if "[Rule]" not in config_text:
        raise ValueError("upstream config has no [Rule] section")
    rule_text = config_text.split("[Rule]", 1)[1]
    return re.split(r"\n\[(?:Host|URL Rewrite|Script|MITM)\]", rule_text, maxsplit=1)[0]


def normalize_rule_line(line: str) -> str:
    line = line.rstrip()
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return line

    line = re.sub(r"\s+#.*$", "", line).rstrip()
    mappings = {
        "Proxy": "AUTO",
        "proxy": "AUTO",
        "PROXY": "AUTO",
        "Reject": "REJECT",
        "reject": "REJECT",
        "Direct": "DIRECT",
        "direct": "DIRECT",
    }
    for old, new in mappings.items():
        line = re.sub(rf"(?<=,){re.escape(old)}(?=,|$)", new, line)
    return line


def normalize_rule_section(rule_text: str) -> str:
    lines = [normalize_rule_line(line) for line in rule_text.strip().splitlines()]
    return "\n".join(lines).strip()


def ai_groups() -> str:
    regions, _ = ai.regional_filters()
    return (
        f"TW = url-test,policy-regex-filter={regions[ai.TW]},url={ai.CHECK},"
        "interval=1800,timeout=5,tolerance=120\n\n"
        "# Reuse the normal regional groups and the existing AUTO group.\n"
        f"{ai.SELECTOR} = select,JP,AUTO,TW,US,select=0,policy-select-name=JP"
    )


def custom_rules_with_ai(custom: str, upstream: str) -> str:
    entries = ai.route_entries()
    entry_set = set(entries)
    custom = custom.replace(
        "# X (Twitter) and its short-link/static domains use the Japan group.",
        "# X (Twitter) and its short-link/static domains use AI Platform.",
    ).replace(
        "# Legacy US routing for Google AI services. AI-enabled profiles override Gemini.",
        "# Gemini uses AI Platform. Other Google AI services use US.",
    ).replace(
        "# Other AI tools (Grok, Perplexity, Poe, Copilot, Cursor, etc.) prefer Japan.\n"
        "# OpenAI also uses Japan in legacy Clash profiles.",
        "# Other AI tools prefer Japan. Grok uses AI Platform.",
    )
    custom_lines = custom.splitlines()
    routed = set()
    for index, line in enumerate(custom_lines):
        rule, _, policy = line.rpartition(",")
        if policy in {ai.JP, ai.US} and rule in entry_set:
            routed.add(rule)
            custom_lines[index] = f"{rule},{ai.SELECTOR}"

    added = [entry for entry in entries if entry not in routed]
    suffixes = [entry.split(",", 1)[1] for entry in added]
    # Preserve existing narrower upstream exceptions, including r.openai.com.
    exceptions = []
    for line in upstream.splitlines():
        parts = line.split(",")
        if len(parts) == 3 and parts[0] in {"DOMAIN", "DOMAIN-SUFFIX"}:
            if any(parts[1].endswith("." + suffix) for suffix in suffixes):
                exceptions.append(line)
    new_rules = ["# OpenAI / ChatGPT. Keep existing narrower upstream exceptions first."]
    return "\n".join(custom_lines + [""] + new_rules + exceptions + [
        f"{entry},{ai.SELECTOR}" for entry in added
    ])


def validate_public_rules(rules: str, source_url: str) -> None:
    """Only routing rules and public source URLs can enter the generated config."""
    source = urlsplit(source_url)
    if (
        source.scheme not in {"http", "https"} or not source.hostname
        or source.username is not None or source.password is not None
        or source.query or source.fragment or any(c.isspace() for c in source_url)
    ):
        raise ValueError("Expected a public rule source URL without credentials, query or fragment")
    urls = set(re.findall(r"[a-zA-Z][a-zA-Z0-9+.-]*://[^\s,]+", rules))
    if urls - {source_url, ai.CHECK} or re.search(
        r"(?i)\b(?:token|password|secret|subscription|auth[-_]?key|api[-_]?key|private[-_]?key)\s*=",
        rules,
    ):
        raise ValueError("Unexpected URL or credential-like field in the Shadowrocket rules")
    rule_pattern = re.compile(
        r"(?:DOMAIN(?:-SUFFIX|-KEYWORD)?|IP-CIDR6?|GEOIP|PROCESS-NAME),"
        rf"[A-Za-z0-9_.*:/-]+,(?:AUTO|DIRECT|DSH|JP|REJECT|TAILSCALE|US|{ai.SELECTOR})"
        r"(?:,no-resolve)?"
    )
    active = [line for line in rules.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not active or active[-1] != "FINAL,AUTO":
        raise ValueError("Expected to end the rules with FINAL,AUTO")
    if any(not rule_pattern.fullmatch(line) for line in active[:-1]):
        raise ValueError("Unexpected syntax in a public Shadowrocket rule")


def build(upstream_text: str, source_url: str) -> str:
    upstream_rules = normalize_rule_section(extract_rule_section(upstream_text))
    custom_rules = custom_rules_with_ai(CUSTOM_RULES.read_text(encoding="utf-8").strip(), upstream_rules)
    public_rules = (
        f"{custom_rules}\n\n{BASE_MARKER}# Source: {source_url}\n{upstream_rules}"
    )
    validate_public_rules(public_rules, source_url)
    return (
        HEADER.rstrip()
        + "\n\n" + ai_groups()
        + "\n\n[Rule]\n" + public_rules
        + "\n\n" + FOOTER
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if args.source_file:
        upstream_text = args.source_file.read_text(encoding="utf-8")
        source_label = args.source_url
    else:
        upstream_text = fetch_url(args.source_url)
        source_label = args.source_url

    rendered = build(upstream_text, source_label)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output} ({len(rendered.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
