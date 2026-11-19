from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_ai_routing as ai
import build_clash_rule_providers as legacy


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def yaml_rules(text: str) -> list[str]:
    return [line.strip()[3:-1] for line in text.splitlines() if line.startswith("  - '")]


def domain_matches(kind: str, suffix: str, host: str) -> bool:
    if kind == "DOMAIN":
        return host == suffix
    if kind == "DOMAIN-SUFFIX":
        return host == suffix or host.endswith("." + suffix)
    if kind == "DOMAIN-KEYWORD":
        return suffix in host
    return False


def match_domain(rules: list[str], providers: dict[str, list[str]], host: str) -> str:
    for rule in rules:
        fields = rule.split(",")
        if fields[0] in {"FINAL", "MATCH"}:
            return fields[1]
        if len(fields) != 3:
            continue
        kind, key, target = fields
        if kind == "RULE-SET":
            if any(domain_matches(*line.split(","), host) for line in providers[key]):
                return target
        elif domain_matches(kind, key, host):
            return target
    raise AssertionError("Expected a fallback rule")


class AIRoutingTests(unittest.TestCase):
    def test_generated_clash_files_match(self) -> None:
        self.assertEqual(read("clash-ai-merge.yaml"), ai.verge_merge(read("clash-remote-merge.yaml")))
        self.assertEqual(read("clash-ai-groups.yaml"), ai.verge_groups(read("clash-remote-groups.yaml")))
        self.assertEqual(read("clash/personal-ai-override.js"), ai.clash_app_script(read("clash/personal-override.js")))
        self.assertEqual(
            read("clash/rules/ai-platform.yaml"),
            legacy.render_provider([ai.SOURCE], ai.SELECTOR, ai.route_entries()),
        )

    def test_legacy_providers_and_generation_are_separate(self) -> None:
        grouped: dict[str, list[str]] = defaultdict(list)
        for source in legacy.DEFAULT_SOURCES:
            legacy.parse_rules(source, grouped)
        for policy, rules in grouped.items():
            filename = legacy.POLICY_FILES[policy]
            self.assertEqual(
                read(f"clash/rules/{filename}"),
                legacy.render_provider(legacy.DEFAULT_SOURCES, policy, rules),
            )
        self.assertNotIn("AI Platform", read("shadowrocket.conf"))
        workflow = read(".github/workflows/update-shadowrocket.yml")
        for name in ["build_ai_routing.py", "ai-platform.list", "shadowrocket-ai.conf"]:
            self.assertNotIn(name, workflow)

    def test_ai_selection_and_empty_groups(self) -> None:
        for app in [False, True]:
            groups = ai.mihomo_groups(app=app)
            by_name = {group["name"]: group for group in groups}
            selector = by_name.pop(ai.SELECTOR)
            self.assertEqual(selector["proxies"], [ai.JP, ai.AUTO, ai.TW, ai.US])
            self.assertEqual(selector["default-selected"], ai.JP)
            self.assertEqual(set(by_name), set(selector["proxies"]))
            for group in by_name.values():
                self.assertEqual(group["type"], "url-test")
                self.assertTrue(group["include-all"])
                self.assertEqual(group["empty-fallback"], "REJECT")
                self.assertFalse(group.get("proxies"))
                self.assertEqual(group["interrupt-exist-connections"], not app)

        samples = {
            "Japan JP [1]": ai.JP,
            "台灣 TW [4.9]": ai.TW,
            "United States US": ai.US,
            "🇯🇵 Example": ai.JP,
            "台灣 01": ai.TW,
            "美國 01": ai.US,
            "Japan / US": None,
            "US via Hong Kong": None,
            "Singapore SG": None,
            "South America": None,
            "DIRECT": None,
            "特殊 JP": None,
            "US 限速": None,
            "TW [5]": None,
            "JP [x5.0]": None,
            "Taiwan [10×]": None,
        }
        filters = {group: re.compile(pattern) for group, pattern in ai.ai_filters().items()}
        for name, region in samples.items():
            with self.subTest(name=name):
                self.assertEqual(
                    [group for group in (ai.JP, ai.TW, ai.US) if filters[group].search(name)],
                    [region] if region else [],
                )
                self.assertEqual(bool(filters[ai.AUTO].search(name)), region is not None)
        excluded = [name for name, region in samples.items() if region is None]
        for group, compiled in filters.items():
            eligible = [name for name in excluded if compiled.search(name)]
            self.assertEqual(eligible, [], group)

    def test_verge_domain_order_and_fallback(self) -> None:
        merged = yaml_rules(read("clash-ai-merge.yaml"))
        legacy_rules = yaml_rules(read("clash-remote-merge.yaml"))
        new_rule = "RULE-SET,personal-ai-platform,AI Platform"
        self.assertEqual([rule for rule in merged if rule != new_rule], legacy_rules)
        self.assertEqual(merged[0], "DOMAIN-SUFFIX,maxon.net,DIRECT")
        self.assertEqual(merged[-1], "MATCH,All-Auto")
        providers = {
            f"personal-shadowrocket-{policy}": yaml_rules(read(f"clash/rules/shadowrocket-{policy}.yaml"))
            for policy in ("us", "jp", "direct")
        }
        providers["personal-ai-platform"] = ai.route_entries()
        for rule in ai.route_entries():
            domain = rule.split(",")[1]
            self.assertEqual(match_domain(merged, providers, f"api.{domain}"), ai.SELECTOR)
        controls = {
            "gemini.google.com": "US-Auto",
            "aistudio.google.com": "US-Auto",
            "us-central1-aiplatform.googleapis.com": "US-Auto",
            "api.interactivebrokers.com": "US-Auto",
            "etrade.com": "US-Auto",
            "fidelity.com": "DIRECT",
            "claude.ai": "JP-Auto",
            "maxon.net": "DIRECT",
            "fallback.example": "All-Auto",
        }
        for domain, policy in controls.items():
            with self.subTest(domain=domain):
                self.assertEqual(match_domain(merged, providers, domain), policy)

    def test_verge_fixed_us_group_configures_zero_match_rejection(self) -> None:
        group_header = "  - name: US-Auto\n"
        new = read("clash-ai-groups.yaml").split(group_header, 1)[1].split("\n  - name:", 1)[0]
        old = read("clash-remote-groups.yaml").split(group_header, 1)[1].split("\n  - name:", 1)[0]
        self.assertIn("    empty-fallback: REJECT\n", new)
        self.assertEqual(new.replace("    empty-fallback: REJECT\n", ""), old)
        fields = dict(line.strip().split(": ", 1) for line in new.splitlines())
        include = re.compile(fields["filter"].strip("'"))
        exclude = re.compile(fields["exclude-filter"].strip("'"))
        nodes = ["Synthetic Japan JP", "Synthetic Taiwan TW", "Synthetic USA [5.0]"]
        self.assertEqual([node for node in nodes if include.search(node) and not exclude.search(node)], [])
        self.assertIsNotNone(include.search("Synthetic USA"))
        self.assertIsNone(exclude.search("Synthetic USA"))

    def test_shadowrocket_preview_keeps_original_base(self) -> None:
        current = read("shadowrocket.conf")
        draft = ai.shadowrocket(current, ai.route_entries())
        self.assertTrue(draft.startswith("# DRAFT:"))
        marker = "# Base: Johnshall domestic/foreign split + ad blocking.\n"
        self.assertEqual(draft.split(marker, 1)[1], current.split(marker, 1)[1])
        fixture = (
            "[Proxy Group]\nJP = select,REJECT\nAUTO = select,REJECT\n"
            "[Rule]\nDOMAIN-SUFFIX,grok.com,JP\nDOMAIN-SUFFIX,x.com,JP\n"
            "DOMAIN-SUFFIX,gemini.google.com,US\nDOMAIN-SUFFIX,fidelity.com,DIRECT\n"
            + marker
            + "DOMAIN-SUFFIX,r.openai.com,REJECT\nFINAL,AUTO\n\n[Host]\n"
        )
        preview = ai.shadowrocket(fixture, ai.route_entries())
        rules = preview.split("[Rule]\n")[1].split("[Host]\n")[0].splitlines()
        self.assertEqual(match_domain(rules, {}, "r.openai.com"), "REJECT")
        self.assertEqual(match_domain(rules, {}, "api.openai.com"), ai.SELECTOR)
        self.assertEqual(match_domain(rules, {}, "grok.com"), ai.SELECTOR)
        self.assertEqual(match_domain(rules, {}, "x.com"), ai.SELECTOR)
        self.assertEqual(match_domain(rules, {}, "gemini.google.com"), "US")
        self.assertEqual(match_domain(rules, {}, "fidelity.com"), "DIRECT")
        self.assertEqual(match_domain(rules, {}, "fallback.example"), "AUTO")

    @unittest.skipUnless(shutil.which("node"), "Node.js required for script behavior")
    def test_clash_app_inherits_subscription_and_is_idempotent(self) -> None:
        fixture = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const baseline = 'clash/personal-override.js';
const optIn = 'clash/personal-ai-override.js';
function run(script, profile) {
  const output = vm.runInNewContext(fs.readFileSync(script, 'utf8') + '\nmain(config)',
    {config: structuredClone(profile)}, {timeout: 1000});
  return JSON.parse(JSON.stringify(output));
}
const input = {
  proxies: [{name: 'Synthetic Japan JP', type: 'example'}],
  'proxy-groups': [{name: 'Subscription Fallback', type: 'select', proxies: ['DIRECT']}],
  rules: ['DOMAIN,legacy.example,Subscription Fallback', 'MATCH,Subscription Fallback'],
  dns: {enable: false}, tun: {enable: false},
};
const before = run(baseline, input);
const after = run(optIn, input);
const extra = 'RULE-SET,personal-ai-platform,AI Platform';
assert.deepEqual(after.rules.filter((rule) => rule !== extra), before.rules);
assert.ok(after.rules.indexOf(extra) < after.rules.indexOf('RULE-SET,personal-jp,Personal-JP'));
const fixedUS = after['proxy-groups'].find((group) => group.name === 'Personal-US');
assert.equal(fixedUS['empty-fallback'], 'REJECT');
const include = new RegExp(fixedUS.filter.replace(/^\(\?i\)/, ''), 'i');
const exclude = new RegExp(fixedUS['exclude-filter'], 'u');
const names = ['Synthetic Japan JP', 'Synthetic Taiwan TW', 'Synthetic USA [5.0]'];
assert.deepEqual(names.filter((name) => include.test(name) && !exclude.test(name)), []);
assert.ok(include.test('Synthetic USA') && !exclude.test('Synthetic USA'));
assert.ok(after.rules.includes('RULE-SET,personal-us,Personal-US'));
const usPayload = fs.readFileSync('clash/rules/shadowrocket-us.yaml', 'utf8');
for (const domain of ['gemini.google.com', 'aistudio.google.com', 'interactivebrokers.com', 'etrade.com']) {
  assert.ok(usPayload.includes(`'DOMAIN-SUFFIX,${domain}'`));
}
const unchangedGroups = after['proxy-groups'].slice(5).map((group) => {
  if (group.name !== 'Personal-US') return group;
  const original = {...group};
  delete original['empty-fallback'];
  return original;
});
assert.deepEqual(unchangedGroups, before['proxy-groups']);
assert.deepEqual(after.proxies, input.proxies);
assert.deepEqual(after.dns, input.dns);
assert.deepEqual(after.tun, input.tun);
assert.deepEqual(run(optIn, after), after);
"""
        subprocess.run(
            ["node", "-e", fixture], cwd=ROOT, text=True, capture_output=True, check=True,
        )


if __name__ == "__main__":
    unittest.main()
