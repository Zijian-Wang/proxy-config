#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import time
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_URL = "https://johnshall.github.io/Shadowrocket-ADBlock-Rules-Forever/sr_cnip_ad.conf"
CUSTOM_RULES = ROOT / "source" / "shadowrocket-custom-rules.list"
OUTPUT = ROOT / "shadowrocket.conf"

HEADER = """[General]
bypass-system = true
skip-proxy = 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local, captive.apple.com
tun-excluded-routes = 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, 169.254.0.0/16, 172.16.0.0/12, 192.168.0.0/16, 224.0.0.0/4
dns-server = system
fallback-dns-server = system
ipv6 = false
prefer-ipv6 = false
private-ip-answer = true

[Proxy]
# Keep your airport/server subscription in Shadowrocket separately.
# Do not publish tokenized node definitions here unless this repo is private.

[Proxy Group]
# Manually choose one stable US node here for broker/account domains.
US-STABLE = select,policy-regex-filter=美国|美國|US|USA|United States|America,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5

# AI groups. AI-OPENAI intentionally excludes Hong Kong.
AI-OPENAI = select,policy-regex-filter=美国|美國|US|USA|United States|America|日本|Japan|JP|台|台湾|台灣|Taiwan|TW,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5
AI-JP-TW = select,policy-regex-filter=日本|Japan|JP|台|台湾|台灣|Taiwan|TW,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5

# Region groups over nodes imported from your Shadowrocket subscription.
TW = select,policy-regex-filter=台|台湾|台灣|Taiwan|TW,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5
JP = select,policy-regex-filter=日本|Japan|JP,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5
HK = select,policy-regex-filter=香港|HongKong|Hong Kong|HK,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5
KR = select,policy-regex-filter=韩国|韓國|韩|韓|Korea|KR,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5

# General proxy group over nodes imported from your Shadowrocket subscription.
PROXY = select,policy-regex-filter=.*,select=0,url=http://www.gstatic.com/generate_204,interval=86400,timeout=5
AUTO = url-test,policy-regex-filter=.*,url=http://www.gstatic.com/generate_204,interval=600,timeout=5,tolerance=50
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
        "Proxy": "PROXY",
        "proxy": "PROXY",
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


def build(upstream_text: str, source_url: str) -> str:
    custom_rules = CUSTOM_RULES.read_text(encoding="utf-8").strip()
    upstream_rules = normalize_rule_section(extract_rule_section(upstream_text))
    return (
        HEADER.rstrip()
        + "\n\n[Rule]\n"
        + custom_rules
        + "\n\n"
        + "# Base: Johnshall domestic/foreign split + ad blocking.\n"
        + f"# Source: {source_url}\n"
        + upstream_rules
        + "\n\n"
        + FOOTER
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
