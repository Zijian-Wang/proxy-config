const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(path.join(__dirname, "../clash/verge-subscription-overlay.js"), "utf8");
const ai = "🤖 AI平台";
const us = "US-Auto";
const jp = "JP-Auto";
const guards = [
  "RULE-SET,anti-ad,Ads",
  "GEOSITE,private,DIRECT",
  "RULE-SET,lan_ip,DIRECT,no-resolve",
  "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
  "DOMAIN-SUFFIX,r.openai.com,REJECT",
  "DOMAIN-SUFFIX,oaistatic.com,Ads",
];
const conflicts = [
  "DOMAIN, filecdn.MINIMAX.chat, International",
  "DOMAIN,filecdn.minimax.chat,Default",
  "DOMAIN-SUFFIX,chatgpt.com,International",
  "DOMAIN-SUFFIX,schwab.com,International",
];
const tail = [
  "DOMAIN-SUFFIX,filecdn.minimax.chat,International",
  "DOMAIN-SUFFIX,minimax.chat,International",
  "DOMAIN-SUFFIX,similar-schwab.com,Default",
  "IP-CIDR,52.112.0.0/14,International",
  "RULE-SET,google,International",
  "RULE-SET,cn_domain,DIRECT",
  "RULE-SET,cn_ip,DIRECT,no-resolve",
  "MATCH,Default",
];

function subscription() {
  const inline = (payload) => ({type: "inline", behavior: "classical", payload});
  return {
    proxies: [{name: "Fixture US", type: "socks5", server: "192.0.2.10", port: 1080}],
    "proxy-groups": [
      {name: "Default", type: "select", proxies: ["International", "DIRECT"]},
      {name: "Ads", type: "select", proxies: ["REJECT", "DIRECT"]},
      {name: "International", type: "select", proxies: ["Fixture US"]},
      {name: ai, type: "select", proxies: ["Fixture US", "DIRECT"]},
      {name: us, type: "select", proxies: ["Fixture US"]},
      {name: jp, type: "select", proxies: ["International"]},
    ],
    "rule-providers": {
      "anti-ad": inline(["DOMAIN-SUFFIX,ads.openai.com"]),
      lan_ip: inline(["IP-CIDR,192.168.0.0/16"]),
      google: inline(["DOMAIN-SUFFIX,google.com"]),
      cn_domain: inline(["DOMAIN-SUFFIX,local-services.test"]),
      cn_ip: inline(["IP-CIDR,198.51.100.0/24"]),
    },
    "proxy-providers": {
      fixture: {type: "inline", payload: [{name: "Fixture Pass", type: "direct"}]},
    },
    dns: {enable: true, "enhanced-mode": "fake-ip"},
    tun: {enable: true},
    rules: [...guards, ...conflicts, ...tail],
  };
}

function apply(config) {
  const warnings = [];
  const context = {config: structuredClone(config), console: {warn: (message) => warnings.push(message)}};
  const result = vm.runInNewContext(script + "\nmain(config);", context);
  return {config: structuredClone(result), warnings};
}

function domainMatches(type, domain, host) {
  return (type === "DOMAIN" && host === domain) ||
    (type === "DOMAIN-SUFFIX" && (host === domain || host.endsWith("." + domain)));
}

function policy(config, host) {
  for (const rule of config.rules) {
    const [type, value, target] = rule.split(",");
    if (type === "MATCH" || type === "FINAL") return value;
    if (type === "RULE-SET" && config["rule-providers"][value].payload.some((matcher) => {
      const [kind, domain] = matcher.split(",");
      return domainMatches(kind, domain, host);
    })) return target;
    if (domainMatches(type, value, host)) return target;
  }
}

test("overlays only approved matchers and preserves native groups, providers and rule order", () => {
  const before = subscription();
  const {config, warnings} = apply(before);
  assert.deepEqual(warnings, []);
  assert.deepEqual({...config, rules: before.rules}, before);
  assert.deepEqual(config.rules.filter((rule) => before.rules.includes(rule)), [...guards, ...tail]);
  assert.deepEqual(config.rules.slice(0, guards.length), guards);
  assert.equal(config.rules[guards.length], "DOMAIN,filecdn.minimax.chat,DIRECT");
  assert.equal(config.rules.at(-1), "MATCH,Default");
  assert.ok(config.rules.includes("IP-CIDR,52.112.0.0/14,DIRECT,no-resolve"));
  assert.ok(config.rules.includes("PROCESS-NAME,ToDesk.exe,DIRECT"));

  const routes = {
    "filecdn.minimax.chat": "DIRECT",
    "nested.filecdn.minimax.chat": "International",
    "other.minimax.chat": "International",
    "ads.openai.com": "Ads",
    "r.openai.com": "REJECT",
    "assets.oaistatic.com": "Ads",
    "gemini.google.com": ai,
    "api.openai.com": ai,
    "chatgpt.com": ai,
    "grok.com": ai,
    "x.com": ai,
    "accounts.google.com": "International",
    "aistudio.google.com": us,
    "claude.ai": jp,
    "api.schwab.com": us,
    "etrade.com": us,
    "fidelity.com": "DIRECT",
    "similar-schwab.com": "Default",
    "maxon.net": "DIRECT",
    "teams.microsoft.com": "DIRECT",
    "service.local-services.test": "DIRECT",
    "unrelated.test": "Default",
  };
  for (const [host, expected] of Object.entries(routes)) {
    assert.equal(policy(config, host), expected, host);
  }
  assert.deepEqual(apply(config).config, config);
});

test("missing AI group keeps native AI routing and warns while other local routes apply", () => {
  const before = subscription();
  before["proxy-groups"].find((group) => group.name === ai).name = "AI Platform";
  const {config, warnings} = apply(before);
  assert.equal(warnings.length, 1);
  assert.match(warnings[0], /AI平台 is missing/);
  assert.deepEqual(config["proxy-groups"], before["proxy-groups"]);
  assert.ok(config.rules.includes("DOMAIN-SUFFIX,chatgpt.com,International"));
  for (const host of ["gemini.google.com", "chatgpt.com", "api.openai.com", "grok.com", "x.com"]) {
    assert.equal(policy(config, host), policy(before, host), host);
  }
  assert.equal(policy(config, "api.schwab.com"), us);
  assert.equal(policy(config, "filecdn.minimax.chat"), "DIRECT");
  assert.deepEqual(apply(config).config, config);
});

test("missing fixed exit rejects brokers without selecting another outbound", () => {
  const before = subscription();
  before["proxy-groups"].find((group) => group.name === us).name = "Other US";
  const {config, warnings} = apply(before);
  assert.match(warnings[0], /US-Auto is missing.*REJECT/);
  assert.deepEqual(config["proxy-groups"], before["proxy-groups"]);
  assert.equal(policy(config, "api.schwab.com"), "REJECT");
  assert.equal(policy(config, "etrade.com"), "REJECT");
  assert.equal(policy(config, "fidelity.com"), "DIRECT");
  assert.equal(policy(config, "aistudio.google.com"), "International");
  assert.equal(policy(config, "chatgpt.com"), ai);
  assert.equal(policy(config, "unrelated.test"), "Default");
  assert.deepEqual(apply(config).config, config);
});

test("retains an exact protected rule, with a warning if native broad rules come first", () => {
  const before = subscription();
  const early = "DOMAIN-SUFFIX,minimax.chat,International";
  const exactDeny = "DOMAIN,filecdn.minimax.chat,REJECT-DROP";
  before.rules.unshift(early, exactDeny);
  const {config, warnings} = apply(before);
  assert.match(warnings[0], /Broad subscription rules precede/);
  assert.deepEqual(config.rules.slice(0, 2), [early, exactDeny]);
  assert.ok(!config.rules.includes("DOMAIN,filecdn.minimax.chat,DIRECT"));
  assert.deepEqual(apply(config).config, config);
});

test("handles an empty profile and preserves rules from the first fallback onward", () => {
  assert.deepEqual(apply({}).config, {});
  const before = subscription();
  before.rules = ["FINAL,Default", "DOMAIN,filecdn.minimax.chat,International", "MATCH,International"];
  const {config} = apply(before);
  assert.deepEqual(config.rules.slice(-3), before.rules);
  assert.equal(policy(config, "filecdn.minimax.chat"), "DIRECT");
  assert.equal(policy(config, "unrelated.test"), "Default");
  assert.deepEqual(apply(config).config, config);
});
