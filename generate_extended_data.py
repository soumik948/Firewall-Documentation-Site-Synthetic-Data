"""
Extended synthetic dataset — "looks like a real 10k+ device telecom network" layer for the
documentation-site demo. ADDITIVE to the existing engine-linked core dataset (hosts/rules/
objectgroups from test_sentrywall_core.estate2(), unchanged, still exactly what the 292 tests
run against) — this generator produces everything under NEW keys (networks/big_hosts/
big_groups/big_rules), seeded and deterministic, browsing-scale only. It is not run through
the pytest suite — that's a deliberate scope choice, not an oversight: FRVA's deterministic
engine needs a handful of TARGETED scenarios to prove its logic (estate()/estate2() already
give it that), not 2000 rules: this generator's job is realism for a human browsing the
documentation site and for the RAG lookup, not new engine test coverage.

Design mirrors how real firewall documentation actually looks: dominated by NETWORK/GROUP
references, not thousands of individually-named hosts — a handful of representative named
hosts per subnet (the ones an engineer would actually look up by name), the rest expressed as
ranges and groups, exactly like the source screenshots.
"""
import ipaddress
import random

R = random.Random(20260925)  # fixed seed -> reproducible from a fresh run

# ── topology: region -> (cidr, short name, env, category) ──────────────────
REGIONS = [
    ("10.10.0.0/16", "WEB-FRONTEND",    "PROD", "WEB"),
    ("10.20.0.0/16", "APP-BACKEND",     "PROD", "APP"),
    ("10.25.0.0/16", "MIDDLEWARE",      "PROD", "MW"),
    ("10.30.0.0/16", "DB-SQL",          "PROD", "DB"),
    ("10.35.0.0/16", "DB-NOSQL",        "PROD", "DB"),
    ("10.40.0.0/16", "CORE-NETWORK-FN", "PROD", "CNF"),
    ("10.50.0.0/16", "DMZ-PROXY",       "PROD", "DMZ"),
    ("10.60.0.0/16", "MONITORING-MGMT", "PROD", "MGMT"),
    ("10.70.0.0/16", "SHARED-SERVICES", "PROD", "SVC"),
    ("10.80.0.0/16", "DR-SITE",         "DR",   "DR"),
    ("10.90.0.0/16", "AWS-CLOUD-CONNECT",   "PROD", "CLOUD"),
    ("10.91.0.0/16", "AZURE-CLOUD-CONNECT", "PROD", "CLOUD"),
    ("10.99.0.0/16", "OOB-MGMT",        "MGMT", "MGMT"),
    ("172.16.0.0/16", "TEST-ENV",       "TEST", "MIXED"),
    ("172.20.0.0/16", "DEV-ENV",        "DEV",  "MIXED"),
    ("192.168.10.0/24", "PARTNER-EXTRANET", "PROD", "EXT"),
]

APPS = {
    "WEB": ["CRM-WEB", "SELFCARE-PORTAL", "ECOMM", "API-GW", "PARTNER-PORTAL", "STORE-WEB"],
    "APP": ["CRM-APP", "BILLING", "ORDER-MGMT", "MEDIATION", "RATING", "OCS-CHARGING",
            "PROVISIONING", "TICKETING", "WFM", "LOYALTY", "PAYMENT-GW", "NETWORK-INVENTORY",
            "FAULT-MGMT", "PERF-MGMT", "SERVICE-ASSURANCE", "CAPACITY-PLANNING"],
    "MW": ["KAFKA-CLUSTER", "MQ-BROKER", "ESB", "API-MEDIATION", "EVENT-BUS"],
    "DB": ["ORA-RAC", "MSSQL-CLUSTER", "MONGODB-RS", "REDIS-CACHE", "CASSANDRA-RING",
           "POSTGRES-HA", "ELASTICSEARCH"],
    "CNF": ["HLR", "HSS", "MME", "SGW", "PGW", "PCRF", "DIAMETER-ROUTER", "SMSC",
            "IN-PLATFORM", "VAS-PLATFORM", "IMS-CSCF", "VOLTE-PLATFORM"],
    "DMZ": ["REVERSE-PROXY", "WAF", "ALG-PROXY", "LOAD-BALANCER", "VPN-GW"],
    "MGMT": ["ZABBIX-NMS", "SIEM", "NAGIOS", "PROMETHEUS", "GRAFANA", "BACKUP-MGR"],
    "SVC": ["LDAP-AD", "RADIUS-AAA", "DNS", "NTP", "DHCP", "JUMP-HOST"],
    "DR": ["CRM-APP-DR", "BILLING-DR", "ORA-RAC-DR", "MSSQL-DR"],
    "CLOUD": ["ETL-PIPELINE", "DWH", "BIGDATA-CLUSTER", "ML-PLATFORM", "CI-CD", "K8S-INGRESS"],
    "EXT": ["EDI-GATEWAY", "ROAMING-PARTNER-GW", "INTERCONNECT-GW"],
    "MIXED": ["CRM-WEB", "CRM-APP", "BILLING", "ORA-RAC", "MSSQL-CLUSTER", "API-GW"],
}

SERVICES_BY_PAIR = {
    ("WEB", "APP"): [("tcp", 443), ("tcp", 8080), ("tcp", 8443)],
    ("APP", "MW"):  [("tcp", 9092), ("tcp", 5672), ("tcp", 61616)],
    ("APP", "DB"):  [("tcp", 1521), ("tcp", 1433), ("tcp", 3306), ("tcp", 5432),
                      ("tcp", 27017), ("tcp", 6379), ("tcp", 9042)],
    ("APP", "CNF"): [("tcp", 3868), ("udp", 1812), ("udp", 1813), ("tcp", 5060), ("udp", 2123)],
    ("CNF", "CNF"): [("tcp", 3868), ("udp", 2123), ("udp", 2152)],
    ("DMZ", "WEB"): [("tcp", 443), ("tcp", 80)],
    ("EXT", "DMZ"): [("tcp", 443), ("tcp", 22)],
    ("MGMT", "*"):  [("udp", 161), ("tcp", 22), ("tcp", 443), ("udp", 514)],
    ("SVC", "*"):   [("udp", 53), ("udp", 123), ("tcp", 389), ("tcp", 636)],
    ("*", "SVC"):   [("udp", 53), ("udp", 123), ("tcp", 389), ("tcp", 636)],
    ("CLOUD", "APP"): [("tcp", 443), ("tcp", 8443)],
    ("APP", "CLOUD"): [("tcp", 443), ("tcp", 9092)],
}
DEFAULT_SERVICE = [("tcp", 443)]

DOMAIN = "pri.btnl-demo.local"


def _svc_label(proto, lo, hi=None):
    hi = hi or lo
    label = {443: "https", 80: "http", 8080: "http-alt", 8443: "https-alt", 1521: "oracle",
              1433: "mssql", 3306: "mysql", 5432: "postgres", 27017: "mongodb", 6379: "redis",
              9042: "cassandra", 9092: "kafka", 5672: "amqp", 61616: "activemq", 3868: "diameter",
              1812: "radius", 1813: "radius-acct", 5060: "sip", 2123: "gtp-c", 2152: "gtp-u",
              161: "snmp", 22: "ssh", 514: "syslog", 53: "dns", 123: "ntp", 389: "ldap",
              636: "ldaps"}.get(lo, "")
    rng = f"{lo}-{hi}" if hi != lo else str(lo)
    return f"{proto}/{rng}" + (f" - {label}" if label else "")


def subnets_for_region(cidr, count, new_prefix):
    net = ipaddress.ip_network(cidr)
    gen = net.subnets(new_prefix=new_prefix)
    out = []
    step = max(1, (2 ** (new_prefix - net.prefixlen)) // max(count, 1))
    i = 0
    for idx, s in enumerate(gen):
        if idx % step == 0 and len(out) < count:
            out.append(s)
    return out[:count]


def build_extended():
    networks, hosts, groups, rules = [], [], [], []
    firewalls = {"DC": [], "DMZ": [], "Cloud": [], "OLD": [], "AWS": [], "Azure": []}
    interfaces, routing = {}, {}

    app_registry = {}   # app_name -> list of (ip, subnet_cidr, category, env)
    region_apps = {}    # region name -> [app_name,...]  (for rule generation)

    fw_pool_by_cat = {}
    for cat, n in [("DC", 22), ("DMZ", 6), ("Cloud", 10), ("OLD", 4), ("AWS", 5), ("Azure", 5)]:
        names = []
        for i in range(1, n + 1):
            # 'x' prefix -> guaranteed no collision with the original 11 hand-authored core devices
            base = {"DC": "xfwd", "DMZ": "xfwz", "Cloud": "xfwc", "OLD": "xfwo", "AWS": "xfwa", "Azure": "xfwr"}[cat]
            names.append(f"{base}{i}")
        fw_pool_by_cat[cat] = names
        firewalls[cat] = [{"id": nm, "rules": 0, "zones": []} for nm in names]

    CAT_TO_POOL = {"WEB": "DMZ", "DMZ": "DMZ", "APP": "DC", "MW": "DC", "DB": "DC", "CNF": "DC",
                   "MGMT": "DC", "SVC": "DC", "DR": "DC", "EXT": "DMZ", "MIXED": "DC"}

    def pick_fw(category):
        if category == "CLOUD":
            pool_name = R.choice(["AWS", "Azure"])
        else:
            pool_name = CAT_TO_POOL.get(category, "DC")
        return R.choice(fw_pool_by_cat[pool_name]), pool_name

    # ── networks + hosts ────────────────────────────────────────────────
    for cidr, region_name, env, category in REGIONS:
        net = ipaddress.ip_network(cidr)
        networks.append({"cidr": cidr, "name": region_name, "zone": category, "env": env,
                          "category": category, "firewall": "", "interface": "", "comment": "",
                          "tier": "extended", "level": "region"})
        app_list = APPS.get(category, APPS["MIXED"])
        n_subnets = 6 if net.prefixlen >= 20 else (28 if category != "EXT" else 1)
        new_prefix = min(24, net.max_prefixlen) if net.prefixlen < 24 else net.prefixlen + 2
        subs = subnets_for_region(cidr, n_subnets, new_prefix) if net.prefixlen < new_prefix else [net]
        region_apps[region_name] = []
        for i, sub in enumerate(subs):
            app = app_list[i % len(app_list)]
            suffix = "" if i < len(app_list) else f"-{i // len(app_list) + 1}"
            app_name = f"{app}{suffix}"
            fw, pool_name = pick_fw(category)
            iface_num = 400 + i
            net_name = f"DCN-{app_name}-{env}-01"
            networks.append({"cidr": str(sub), "name": net_name, "zone": category, "env": env,
                              "category": category, "firewall": fw, "interface": f"bond1.{iface_num}",
                              "comment": f"#{100000 + R.randint(1, 89999)}", "tier": "extended",
                              "level": "subnet"})
            hosts_in_sub = []
            usable = list(sub.hosts())
            n_hosts = min(len(usable), R.randint(2, 6))
            for h_i in range(n_hosts):
                ip = str(usable[h_i])
                nn = f"{app_name.lower()}{h_i + 1:02d}.{DOMAIN}"
                comment = f"#{100000 + R.randint(1, 89999)}"
                rec = {"ip": ip, "name": nn, "app": app_name, "zone": category, "env": env,
                       "tier": "extended", "comment": comment,
                       "cluster": app_name if R.random() < 0.35 else ""}
                hosts.append(rec)
                hosts_in_sub.append(ip)
            if hosts_in_sub:
                app_registry.setdefault(app_name, []).append((hosts_in_sub, str(sub), category, env))
                region_apps[region_name].append(app_name)
            fw_entry = next(f for f in firewalls[pool_name] if f["id"] == fw)
            fw_entry["rules"] += R.randint(3, 12)
            if category not in fw_entry["zones"]:
                fw_entry["zones"].append(category)

    # ── groups: one per app (members = its host IPs), plus a few multi-app external groups ──
    for app_name, entries in app_registry.items():
        members = [ip for ips, *_ in entries for ip in ips]
        groups.append({"name": f"G-{app_name}", "members": members,
                        "comment": f"#{100000 + R.randint(1, 89999)} {app_name} tier group"})
    ext_apps = list(app_registry.keys())
    for i in range(30):
        pick = R.sample(ext_apps, k=min(3, len(ext_apps)))
        members = [f"{a.lower()}-vip.{DOMAIN}" for a in pick]
        groups.append({"name": f"g-{pick[0][:12]}-shared{i}", "members": members,
                        "comment": f"#{100000 + R.randint(1, 89999)} shared external group"})

    # ── interfaces & routing for EVERY firewall (fixes the reported gap) ──
    all_networks_by_fw = {}
    for n in networks:
        if n["level"] == "subnet" and n["firewall"]:
            all_networks_by_fw.setdefault(n["firewall"], []).append(n)
    for cat, fws in firewalls.items():
        for fw in fws:
            nets = all_networks_by_fw.get(fw["id"], [])
            if not nets:
                nets = [R.choice([n for n in networks if n["level"] == "subnet"])]
            interfaces[fw["id"]] = [
                {"iface": "Mgmt", "subnet": "10.99.0.0/24", "zone": "MGMT",
                 "description": f"DCN-MGMT-{fw['id']}", "responsible": "netops@btnl-demo.local",
                 "comment": f"#{100000 + R.randint(1, 89999)}"},
            ] + [
                {"iface": n["interface"] or f"bond1.{500 + i}", "subnet": n["cidr"], "zone": n["zone"],
                 "description": n["name"], "responsible": "netops@btnl-demo.local", "comment": n["comment"]}
                for i, n in enumerate(nets[:5])
            ]
            routing[fw["id"]] = [
                {"destination": n["cidr"], "gateway": "direct", "interface": n["interface"] or "bond1.500"}
                for n in nets[:5]
            ] + [{"destination": "0.0.0.0/0", "gateway": f"10.99.0.{R.randint(2, 250)}", "interface": "bond1.410"}]

    # ── rules: connect tiers realistically, ~1600-2000 of them ─────────
    def svc_for(cat_a, cat_b):
        for key in [(cat_a, cat_b), (cat_a, "*"), ("*", cat_b)]:
            if key in SERVICES_BY_PAIR:
                proto, port = R.choice(SERVICES_BY_PAIR[key])
                return _svc_label(proto, port)
        proto, port = R.choice(DEFAULT_SERVICE)
        return _svc_label(proto, port)

    flows = [("WEB", "APP"), ("APP", "MW"), ("APP", "DB"), ("APP", "CNF"), ("CNF", "CNF"),
             ("DMZ", "WEB"), ("EXT", "DMZ"), ("MGMT", "APP"), ("MGMT", "DB"), ("MGMT", "CNF"),
             ("SVC", "APP"), ("CLOUD", "APP"), ("APP", "CLOUD"), ("APP", "DR")]
    apps_by_cat = {}
    for app_name, entries in app_registry.items():
        for ips, cidr, cat, env in entries:
            apps_by_cat.setdefault(cat, []).append((app_name, ips, cidr, env))

    rid = 1000
    target_rules = 1750
    while len(rules) < target_rules:
        cat_a, cat_b = R.choice(flows)
        pool_a, pool_b = apps_by_cat.get(cat_a), apps_by_cat.get(cat_b if cat_b != "DR" else "DR")
        if not pool_a or not pool_b:
            continue
        app_a_name, ips_a, cidr_a, env_a = R.choice(pool_a)
        app_b_name, ips_b, cidr_b, env_b = R.choice(pool_b)
        if app_a_name == app_b_name:
            continue
        rid += 1
        fw, _ = pick_fw(cat_a)
        big = R.random() < 0.12   # ~12% of rules are the big multi-token ones, like the real screenshots
        if big:
            src_pool = [ip for a in R.sample(pool_a, k=min(4, len(pool_a))) for ip in a[1]]
            src = R.sample(src_pool, k=min(len(src_pool), R.randint(8, 22)))
        else:
            src = R.sample(ips_a, k=min(len(ips_a), R.randint(1, 2))) if R.random() < 0.6 else [cidr_a]
        dst = [f"G-{app_b_name}"] if R.random() < 0.5 else R.sample(ips_b, k=min(len(ips_b), 2))
        action = "DENY" if R.random() < 0.04 else "ALLOW"
        svc = "any" if action == "DENY" else svc_for(cat_a, cat_b)
        rules.append({"rule_id": f"XR{rid}", "firewall": fw, "action": action,
                       "source_zone": cat_a, "source": src, "destination_zone": cat_b,
                       "destination": dst, "service": svc,
                       "comment": f"#{100000 + R.randint(1, 99999)} CRQ{R.randint(100000, 999999)}",
                       "tier": "extended"})

    return {"networks": networks, "big_hosts": hosts, "big_groups": groups, "big_rules": rules,
            "big_firewalls": firewalls, "big_interfaces": interfaces, "big_routing": routing}


if __name__ == "__main__":
    import json
    ext = build_extended()
    print(f"networks={len(ext['networks'])} hosts={len(ext['big_hosts'])} "
          f"groups={len(ext['big_groups'])} rules={len(ext['big_rules'])} "
          f"firewalls={sum(len(v) for v in ext['big_firewalls'].values())}")
