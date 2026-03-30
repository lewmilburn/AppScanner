"""
as_report.py — Generates an HTML report from scan results.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def generate_html(reports: list, output_path: Path, version: str) -> None:
    data_json = json.dumps(reports, indent=2)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_apps = len(reports)
    total_findings = sum(r.get("total_findings", 0) for r in reports)
    verified_count = sum(1 for r in reports for f in r.get("findings", []) if f.get("Verified"))
    clean_count = sum(1 for r in reports if r.get("total_findings", 0) == 0)

    from collections import Counter
    global_counts = Counter(
        f.get("DetectorName", "Unknown")
        for r in reports
        for f in r.get("findings", [])
    )
    global_summary_html = "".join(
        f'<span class="summary-item"><span class="summary-name">{name}</span>'
        f'<span class="summary-count">{count}</span></span>'
        for name, count in global_counts.most_common()
    )

    global_summary_section = (
        f'<div class="summary-bar" style="margin-bottom:15px">{global_summary_html}</div>'
        if global_counts else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>AppScanner Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: oklch(14.5% 0 0); color: white; font-size:1rem; }}

    .stat {{ padding: 15px 20px; font-size: 4rem; text-align:center; font-weight: bold; }}
    .stat-label {{ font-size: 1rem; }}

    button {{ color: white; padding: 5px 12px; border: 1px solid black; background-color: oklch(20.5% 0 0); cursor: pointer; border-radius: 3px; font-size: 0.85rem; }}
    button.active {{ background-color: oklch(37.1% 0 0); border-color: black; }}
    input {{ margin-left: auto; padding: 5px 10px; border: 1px solid black; background-color: oklch(20.5% 0 0); border-radius: 3px; font-size: 0.85rem; width: 200px; outline: none; color:white; }}

    .badge {{ font-size: 0.7rem; padding: 2px 7px; border-radius: 3px; font-weight: bold; cursor: default; }}
    .b-red   {{ background-color: oklch(63.7% 0.237 25.331); color: oklch(25.8% 0.092 26.042); }}
    .b-green {{ background-color: oklch(72.3% 0.219 149.579); color: oklch(26.6% 0.065 152.934); }}
    .b-amber {{ background-color: oklch(76.9% 0.188 70.08); color: oklch(41.4% 0.112 45.904); }}

    .card {{ background-color: oklch(26.9% 0 0); border: 1px solid black; border-radius: 4px; margin-bottom: 10px; }}
    .card-head {{ padding: 12px 15px; cursor: pointer; display: flex; align-items: center; gap: 10px; }}
    .card-head:hover {{ background-color: oklch(37.1% 0 0); }}
    .card-name {{ font-family: 'Courier New', monospace; font-size: 0.9rem; flex: 1; }}
    .chevron {{ font-size: 0.7rem; color: oklch(55.6% 0 0); transition: transform 0.15s; }}
    .card.open .chevron {{ transform: rotate(180deg); }}

    .findings {{ display: none; border-top: 1px solid oklch(20.5% 0 0); }}
    .card.open .findings {{ display: block; }}

    .summary-bar {{ display:flex; flex-wrap:wrap; gap:6px 20px; padding:10px 15px; border-bottom:1px solid oklch(20.5% 0 0); align-items:baseline; background-color: oklch(22% 0 0); }}
    .summary-item {{ display:flex; gap:6px; align-items:baseline; }}
    .summary-name {{ font-family:'Courier New',monospace; font-size:0.8rem; color:oklch(70.8% 0 0); }}
    .summary-count {{ font-size:0.85rem; color:oklch(76.9% 0.188 70.08); font-weight:bold; }}

    .finding {{ padding: 12px 15px; border-bottom: 1px solid oklch(20.5% 0 0); display: grid; grid-template-columns: 150px 1fr auto; gap: 10px; align-items: start; }}
    .finding:last-child {{ border-bottom: none; }}
    .f-raw {{ font-family: 'Courier New', monospace; background-color: black; padding: 6px 8px; border-radius: 3px; word-break: break-all; line-height: 1.5; }}
  </style>
</head>
<body>

<div style="display:flex">
  <div style="flex-grow:1">
    <h1 style="font-size:4rem;margin:0;font-weight:bold;"><span style="color:oklch(63.7% 0.237 25.331)">App</span><span style="color:oklch(76.9% 0.188 70.08)">Scanner</span></h1>
    <p style="margin:0">Report for scan at {generated_at}.</p>
  </div>
  <p style="color:oklch(55.6% 0 0); font-size:0.8rem; margin:5px 0 20px 0">AppScanner v{version}</p>
</div>

<div style="display:grid; grid-template-columns:repeat(4,1fr); gap:15px; margin:20px 0">
  <div class="stat" style="border: solid 5px oklch(62.3% 0.214 259.815)">{total_apps}<br><div class="stat-label">APKs Scanned</div></div>
  <div class="stat" style="border: solid 5px oklch(76.9% 0.188 70.08)">{total_findings}<br><div class="stat-label">Findings</div></div>
  <div class="stat" style="border: solid 5px oklch(63.7% 0.237 25.331)">{verified_count}<br><div class="stat-label">Verified</div></div>
  <div class="stat" style="border: solid 5px oklch(72.3% 0.219 149.579)">{clean_count}<br><div class="stat-label">Clean</div></div>
</div>

{global_summary_section}<div style="display:flex; gap:8px; align-items:center; margin-bottom:15px">
  <button class="active" data-filter="all">All</button>
  <button data-filter="findings">Has Findings</button>
  <button data-filter="verified">Verified</button>
  <button data-filter="clean">Clean</button>
  <input type="text" id="search" placeholder="Search..." />
</div>

<div id="apps"></div>

<script>
const DATA = {data_json};

const getRaw = f => f.Redacted || f.RawV2 || f.Raw || "Error loading, please check report.json";
const getFile = f => f.SourceMetadata?.Data?.Filesystem?.file || '';
const getLine = f => f.SourceMetadata?.Data?.Filesystem?.line ?? null;
const fmtTime = t => {{ try {{ return new Date(t).toLocaleString(); }} catch {{ return t; }} }};

function renderApp(r) {{
  const hasF = r.total_findings > 0;
  const verif = (r.findings || []).filter(f => f.Verified).length;
  const fBadge = hasF ? `<span class="badge b-amber">${{r.total_findings}} finding${{r.total_findings > 1 ? 's' : ''}}</span>` : '<span class="badge b-green">Clean</span>';
  const vBadge = verif > 0 ? `<span class="badge b-red">${{verif}} verified</span>` : '';

  const summaryHtml = (() => {{
    if (!hasF) return '';
    const counts = {{}};
    (r.findings || []).forEach(f => {{
      const name = f.DetectorName || 'Unknown';
      counts[name] = (counts[name] || 0) + 1;
    }});
    const items = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => `<span class="summary-item"><span class="summary-name">${{name}}</span><span class="summary-count">${{count}}</span></span>`)
      .join('');
    return `<div class="summary-bar">${{items}}</div>`;
  }})();

  const findingsHtml = hasF
    ? summaryHtml + (r.findings || []).map(f => {{
        const file = getFile(f);
        const line = getLine(f);
        const fileMeta = file ? `<div style="font-family:'Courier New',monospace; color:oklch(70.8% 0 0); margin-bottom:4px">${{file}}${{line !== null ? `:${{line}}` : ''}}</div>` : '';
        const verifError = f.VerificationError || '';
        const badge = f.Verified
          ? '<span class="badge b-red">Verified</span>'
          : `<span class="badge b-amber" title="${{verifError}}">Unverified</span>`;
        return `
          <div class="finding">
            <div style="font-family:'Courier New',monospace; color:oklch(70.8% 0 0)" title="${{f.DetectorDescription || ''}}">${{f.DetectorName || 'Unknown'}}</div>
            <div>
              ${{fileMeta}}
              <div class="f-raw">${{getRaw(f)}}</div>
            </div>
            ${{badge}}
          </div>`;
      }}).join('')
    : '<div style="padding:15px; color:oklch(76.8% 0.233 130.85)">✓ No secrets detected</div>';

  return `
    <div class="card" data-apk="${{r.apk}}" data-findings="${{r.total_findings}}" data-verified="${{verif}}">
      <div class="card-head" onclick="this.closest('.card').classList.toggle('open')">
        <span class="card-name">${{r.apk}}</span>
        ${{vBadge}} ${{fBadge}}
        <span class="chevron">▼</span>
      </div>
      <div class="findings">${{findingsHtml}}</div>
    </div>`;
}}

function render(data) {{
  document.getElementById('apps').innerHTML = data.length
    ? data.map(renderApp).join('')
    : '<div style="padding:40px; text-align:center; color:oklch(55.6% 0 0)">No results match current filters.</div>';
}}

let filter = 'all', search = '';
function apply() {{
  let d = DATA;
  if (filter === 'findings') d = d.filter(r => r.total_findings > 0);
  if (filter === 'verified') d = d.filter(r => (r.findings||[]).some(f => f.Verified));
  if (filter === 'clean')    d = d.filter(r => r.total_findings === 0);
  if (search) {{
    const q = search.toLowerCase();
    d = d.filter(r => r.apk.toLowerCase().includes(q) || (r.findings||[]).some(f => (f.DetectorName||'').toLowerCase().includes(q)));
  }}
  render(d);
}}

document.querySelectorAll('button[data-filter]').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('button[data-filter]').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  filter = b.dataset.filter;
  apply();
}}));
document.getElementById('search').addEventListener('input', e => {{ search = e.target.value; apply(); }});

render(DATA);
</script>
</body>
</html>"""

    output_path.write_text(html, encoding="utf-8")
    print(f"[INFO] HTML report saved to: {output_path}")
