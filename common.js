// Shared utilities for the Firewall Documentation System synthetic demo site.

const ZONE_COLORS = {
  MGMT: '#c9c9c9', DMZ: '#7fe6e6', WEB: '#7fe6e6', APP: '#9fe08a', DB: '#3fae4a', CORE: '#3fae4a',
  MW: '#f4c95d', CNF: '#e79a5e', SVC: '#b7d8f0', DR: '#d6b3f0', CLOUD: '#8fd6c9', EXT: '#f0a3a3',
};
function zoneChip(z) {
  if (!z) return '';
  const c = ZONE_COLORS[z] || '#eeeeee';
  return `<span class="zone-chip" style="background:${c}">${z}</span>`;
}
function tierBadge(t) {
  return t === 'extended' ? '<span class="tier-badge tier-extended">extended</span>'
                           : '<span class="tier-badge tier-core">core</span>';
}

// ── IPv4 / CIDR math ────────────────────────────────────────────────────
function isValidIPv4(s) {
  if (!/^(\d{1,3}\.){3}\d{1,3}$/.test(s)) return false;
  return s.split('.').every(o => +o >= 0 && +o <= 255);
}
function ip2int(ip) {
  const p = ip.split('.').map(Number);
  return ((p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3]) >>> 0;
}
function prefixLen(cidr) { return parseInt(cidr.split('/')[1], 10); }
function cidrContainsIp(cidr, ipInt) {
  const [base, plenStr] = cidr.split('/');
  const p = parseInt(plenStr, 10);
  const mask = p === 0 ? 0 : (0xFFFFFFFF << (32 - p)) >>> 0;
  return (ip2int(base) & mask) === (ipInt & mask);
}

// ── data access (call after fetch('data.json')) ────────────────────────
function allNetworks(d) { return d.networks || []; }
function allHosts(d) {
  return [...(d.hosts || []).map(h => ({ ...h, tier: 'core' })),
          ...(d.big_hosts || [])];
}
function allGroups(d) {
  return [...(d.objectgroups || []).map(g => ({ ...g, tier: 'core' })),
          ...(d.big_groups || [])];
}
function allRules(d) {
  const core = (d.rules || []).map(r => ({
    ...r, tier: 'core',
    source_tokens: String(r.source).split(', ').filter(Boolean),
    destination_tokens: String(r.destination).split(', ').filter(Boolean),
  }));
  const ext = (d.big_rules || []).map(r => ({
    ...r, source: r.source.join(', '), destination: r.destination.join(', '),
    source_tokens: r.source, destination_tokens: r.destination,
  }));
  return [...core, ...ext];
}

// networks whose CIDR contains this ip, most-specific (largest prefix) first
function findContainingNetworks(d, ip) {
  const ipInt = ip2int(ip);
  return allNetworks(d).filter(n => cidrContainsIp(n.cidr, ipInt))
                        .sort((a, b) => prefixLen(b.cidr) - prefixLen(a.cidr));
}

// does token (an IP, a CIDR, or a group name) resolve to include this ip? groups resolved
// recursively; a bare DNS-style name resolves only if some exact host record has that name
// AND that ip (mirrors how a real IPAM/doc system can't resolve an arbitrary external FQDN).
function tokenMatchesIp(d, token, ip, _seenGroups) {
  _seenGroups = _seenGroups || new Set();
  token = String(token).trim();
  if (token === ip) return true;
  if (token.includes('/')) {
    try { return cidrContainsIp(token, ip2int(ip)); } catch (e) { return false; }
  }
  if (/^[gG]-/.test(token)) {
    if (_seenGroups.has(token)) return false;   // guard against a cyclic group
    _seenGroups.add(token);
    const g = allGroups(d).find(g => g.name === token);
    if (!g) return false;
    return (g.members || []).some(m => tokenMatchesIp(d, m, ip, _seenGroups));
  }
  if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(token)) return false;  // a different literal IP
  const h = allHosts(d).find(h => h.name === token || h.ip === ip && h.name === token);
  return !!(h && h.ip === ip);
}

function accessRulesFor(d, ip, side) {
  // side: 'source' -> rules where ip appears in the source tokens ("to other systems")
  //       'destination' -> rules where ip appears in the destination tokens ("from other systems")
  const key = side === 'source' ? 'source_tokens' : 'destination_tokens';
  return allRules(d).filter(r => (r[key] || []).some(tok => tokenMatchesIp(d, tok, ip)));
}

function groupsContaining(d, ip) {
  return allGroups(d).filter(g => (g.members || []).some(m => tokenMatchesIp(d, m, ip)));
}
