#!/usr/bin/env python3
"""Generate the opt-in Clash AI files and share AI filters with Shadowrocket."""

from __future__ import annotations

import argparse
import json
import re

from build_clash_rule_providers import ROOT, render_provider, yaml_quote


SOURCE = ROOT / "source" / "ai-platform.list"
SELECTOR = "AI Platform"
JP = "JP"
TW = "TW"
US = "US"
VERGE_REGIONAL = "JP-TW-US-Auto"
APP_REGIONAL = "Personal-JP-TW-US-Auto"
VERGE_CHOICES = ["JP-Auto", VERGE_REGIONAL, "TW-Auto", "US-Auto"]
APP_CHOICES = ["Personal-JP", APP_REGIONAL, "Personal-TW", "Personal-US"]
CHECK = "https://www.gstatic.com/generate_204"
EXCLUDED_NODES = r"特殊|限速|\[\s*(?:[x×]\s*)?(?:[5-9]|\d\d+)(?:\.\d+)?\s*(?:[x×倍])?\s*\]"
OTHER_REGIONS = (
    r"🇭🇰|香港|\b(?:HK|Hong Kong)\b|🇨🇳|中国|中國|\b(?:CN|China)\b"
    r"|🇸🇬|新加坡|\b(?:SG|Singapore)\b|🇰🇷|韩国|韓國|\b(?:KR|Korea)\b"
    r"|🇨🇦|加拿大|\bCanada\b|🇦🇺|澳洲|\bAustralia\b"
    r"|🇬🇧|英国|英國|\b(?:UK|United Kingdom)\b"
    r"|🇩🇪|德国|德國|\b(?:DE|Germany)\b|🇫🇷|法国|法國|\b(?:FR|France)\b"
    r"|\b(?:North|South|Central|Latin)\s+America\b"
)
REGION_NAMES = {
    JP: r"🇯🇵|日本|\b(?:JP|Japan)\b",
    TW: r"🇹🇼|台[灣湾]|臺灣|\b(?:TW|Taiwan)\b",
    US: r"🇺🇸|美[國国]|\b(?:US|USA|United States)\b",
}


def route_entries() -> list[str]:
    rules = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        rule = line.split("#", 1)[0].strip()
        if not rule:
            continue
        if not re.fullmatch(r"DOMAIN-SUFFIX,[a-z0-9]+(?:[.-][a-z0-9]+)+", rule):
            raise ValueError(f"Invalid AI domain suffix rule: {rule}")
        rules.append(rule)
    if not rules or len(rules) != len(set(rules)):
        raise ValueError("AI rules must be nonempty and unique")
    return rules


def regional_filters() -> tuple[dict[str, str], str]:
    regions = {}
    for name, match in REGION_NAMES.items():
        excluded = [EXCLUDED_NODES, OTHER_REGIONS]
        excluded.extend(marker for region, marker in REGION_NAMES.items() if region != name)
        regions[name] = rf"^(?!.*(?:{'|'.join(excluded)})).*(?:{match})"
    combined = "(?i)(?:" + "|".join(regions.values()) + ")"
    return {name: "(?i)" + pattern for name, pattern in regions.items()}, combined


def mihomo_groups(*, app: bool) -> list[dict]:
    choices = APP_CHOICES if app else VERGE_CHOICES
    regional_name = APP_REGIONAL if app else VERGE_REGIONAL
    regions, combined = regional_filters()
    filters = {regional_name: combined}
    if not app:
        filters["TW-Auto"] = regions[TW]
    groups = [
        {
            "name": SELECTOR,
            "type": "select",
            "proxies": choices,
            "default-selected": choices[0],
            "empty-fallback": "REJECT",
        }
    ]
    for name, pattern in filters.items():
        group = {
            "name": name,
            "type": "url-test",
            "include-all": True,
            "filter": pattern,
            "empty-fallback": "REJECT",
            "url": CHECK,
            "interval": 300,
            "tolerance": 50,
            "lazy": False,
            "interrupt-exist-connections": not app,
        }
        if not app:
            group.update({"timeout": 3000, "max-failed-times": 3})
        groups.append(group)
    return groups


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Expected exactly one anchor: {old!r}")
    return text.replace(old, new, 1)


def verge_merge(legacy: str) -> str:
    legacy = legacy[legacy.index("rule-providers:") :]
    provider = (
        "  personal-ai-platform:\n"
        "    type: http\n"
        "    behavior: classical\n"
        "    format: yaml\n"
        "    interval: 86400\n"
        "    proxy: All-Auto\n"
        "    path: ./ruleset/personal-ai-platform.yaml\n"
        "    url: https://raw.githubusercontent.com/Zijian-Wang/proxy-config/refs/heads/main/"
        "clash/rules/ai-platform.yaml\n"
    )
    legacy = replace_once(legacy, "rule-providers:\n", "rule-providers:\n" + provider)
    us = "  - 'RULE-SET,personal-shadowrocket-us,US-Auto'\n"
    return "# Opt-in for use with clash-ai-groups.yaml.\n\n" + replace_once(
        legacy, us, us + "  - 'RULE-SET,personal-ai-platform,AI Platform'\n"
    )


def verge_groups(legacy: str) -> str:
    legacy = legacy[legacy.index("prepend:") :]
    for name in ("JP-Auto", "US-Auto"):
        existing = f"  - name: {name}\n    type: url-test\n"
        legacy = replace_once(legacy, existing, existing + "    empty-fallback: REJECT\n")
    entries = []
    for group in mihomo_groups(app=False):
        for ordinal, (key, value) in enumerate(group.items()):
            if isinstance(value, str):
                value = yaml_quote(value)
            else:
                value = json.dumps(value, ensure_ascii=False)
            prefix = "  - " if ordinal == 0 else "    "
            entries.append(f"{prefix}{key}: {value}\n")
    return "# Opt-in for use with clash-ai-merge.yaml.\n\n" + replace_once(
        legacy, "prepend:\n", "prepend:\n" + "".join(entries)
    )


def clash_app_script(legacy: str) -> str:
    groups = json.dumps(mihomo_groups(app=True), ensure_ascii=False, indent=2)
    base = replace_once(legacy, "function main(config)", "function legacyOverride(config)")
    return (
        "// Generated by scripts/build_ai_routing.py. Select this script to opt in.\n"
        + base.rstrip()
        + "\n\nfunction main(config) {\n"
        + "  config = legacyOverride(config);\n"
        + '''  config["proxy-groups"].forEach(function (group) {
    if (["Personal-JP", "Personal-TW", "Personal-US"].indexOf(group.name) !== -1) {
      group["empty-fallback"] = "REJECT";
    }
  });
'''
        + "  var aiGroups = " + groups.replace("\n", "\n  ") + ";\n"
        + '''  // Drop obsolete groups if a config already contains the previous override.
  var names = aiGroups.map(function (group) { return group.name; })
    .concat(["AI Auto", "AI JP Auto", "AI TW Auto", "AI US Auto"]);
  config["proxy-groups"] = aiGroups.concat(config["proxy-groups"].filter(function (group) {
    return names.indexOf(group.name) === -1;
  }));
  config["rule-providers"]["personal-ai-platform"] = {
    type: "http", behavior: "classical", format: "yaml", interval: 86400,
    url: "https://raw.githubusercontent.com/Zijian-Wang/proxy-config/refs/heads/main/clash/rules/ai-platform.yaml",
    path: "./ruleset/personal-ai-platform.yaml"
  };
  config.rules = config.rules.filter(function (rule) {
    return rule.indexOf("RULE-SET,personal-ai-platform,") !== 0;
  });
  var us = config.rules.indexOf("RULE-SET,personal-us,Personal-US");
  config.rules.splice(us + 1, 0, "RULE-SET,personal-ai-platform,AI Platform");
  return config;
}
'''
    )


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    entries = route_entries()
    outputs = {
        "clash/rules/ai-platform.yaml": render_provider([SOURCE], SELECTOR, entries),
        "clash-ai-merge.yaml": verge_merge((ROOT / "clash-remote-merge.yaml").read_text(encoding="utf-8")),
        "clash-ai-groups.yaml": verge_groups((ROOT / "clash-remote-groups.yaml").read_text(encoding="utf-8")),
        "clash/personal-ai-override.js": clash_app_script((ROOT / "clash/personal-override.js").read_text(encoding="utf-8")),
    }
    for target, text in outputs.items():
        (ROOT / target).write_text(text, encoding="utf-8")
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
