// Clash (Apple platforms) / Clash Verge Script enhancement.
// Keep node subscriptions private. Routing conditions come from source/*.list
// through scripts/build_clash_rule_providers.py and the remote providers below.
function main(config) {
  var base = "https://raw.githubusercontent.com/Zijian-Wang/proxy-config/refs/heads/main/clash/rules/";
  var names = ["Personal-US", "Personal-JP", "Personal-TW", "Personal-DSH"];
  var exclude = "特殊|限速|\\[(?:[5-9]|\\d\\d+)(?:\\.\\d+)?\\]";
  var regions = [
    "(?i)美[國国]|\\bUSA?\\b|united states|america",
    "(?i)日本|japan|\\bJP\\b",
    "(?i)台[灣湾]|taiwan|\\bTW\\b",
    "(?i)日本|japan|\\bJP\\b|美[國国]|\\bUSA?\\b|united states|america"
  ];
  var groups = names.map(function (name, i) {
    return {
      name: name,
      type: "url-test",
      "include-all": true,
      filter: regions[i],
      "exclude-filter": exclude,
      url: "https://www.gstatic.com/generate_204",
      interval: 300,
      tolerance: i === 3 ? 10000 : 50,
      lazy: false,
      "interrupt-exist-connections": false
    };
  });
  config["proxy-groups"] = groups.concat((config["proxy-groups"] || []).filter(function (g) {
    return names.indexOf(g.name) === -1;
  }));
  var providers = config["rule-providers"] || {};
  [
    ["personal-dsh", "personal-dsh.yaml"],
    ["personal-us", "shadowrocket-us.yaml"],
    ["personal-jp", "shadowrocket-jp.yaml"],
    ["personal-direct", "shadowrocket-direct.yaml"]
  ].forEach(function (entry) {
    providers[entry[0]] = {
      type: "http", behavior: "classical", format: "yaml",
      url: base + entry[1],
      path: "./ruleset/" + entry[0] + ".yaml",
      interval: 86400
    };
  });
  config["rule-providers"] = providers;
  var rules = [
    "RULE-SET,personal-dsh,Personal-DSH",
    "RULE-SET,personal-us,Personal-US",
    "RULE-SET,personal-jp,Personal-JP",
    "RULE-SET,personal-direct,DIRECT"
  ];
  config.rules = rules.concat((config.rules || []).filter(function (r) {
    return !/^RULE-SET,personal-(dsh|us|jp|direct),/.test(r);
  }));
  config.profile = config.profile || {};
  config.profile["store-selected"] = true;
  config.mode = "rule";
  return config;
}
