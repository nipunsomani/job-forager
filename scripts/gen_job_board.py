"""Generate a fast apply-focused HTML job board from a JSON file.

Usage:
    python scripts/gen_job_board.py <input.json> [output.html]

If output is omitted, writes job_board.html next to the input file.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

SOURCE_COLORS = {
    "workday": "#1a73e8",
    "linkedin": "#0077b5",
    "greenhouse": "#25a162",
    "ashby": "#5c47d2",
    "smartrecruiters": "#ff6b00",
    "hiringcafe": "#e11d48",
    "lever": "#6366f1",
    "personio": "#0ea5e9",
    "remotive": "#10b981",
    "remoteok": "#f59e0b",
    "hackernews": "#ff6600",
    "pinpoint": "#6d28d9",
    "twosigma": "#1e3a5f",
    "adzuna": "#00a859",
    "weworkremotely": "#8b5cf6",
    "arbeitnow": "#2563eb",
}


def esc(s: str) -> str:
    return html.escape(str(s or ""))


def render_job(job: dict, idx: int) -> str:
    title = esc(job.get("title", "No title"))
    company = esc(job.get("company", "Unknown"))
    apply_url = esc(job.get("apply_url") or job.get("job_url", ""))
    job_url = esc(job.get("job_url", ""))
    location = esc(job.get("location", ""))
    source = job.get("source", "unknown")
    color = SOURCE_COLORS.get(source, "#6b7280")
    posted = esc((job.get("posted_at") or "")[:10])
    return (
        f'<div class="job-card" data-source="{esc(source)}">\n'
        f'  <div class="job-header">\n'
        f'    <span class="source-badge" style="background:{color}">{esc(source)}</span>\n'
        f'    <span class="posted">{posted}</span>\n'
        f'  </div>\n'
        f'  <div class="job-title">{title}</div>\n'
        f'  <div class="job-company">{company}</div>\n'
        f'  <div class="job-location">{location}</div>\n'
        f'  <div class="job-actions">\n'
        f'    <a href="{apply_url}" target="_blank" rel="noopener" class="apply-btn">Apply</a>\n'
        f'    <a href="{job_url}" target="_blank" rel="noopener" class="view-btn">View</a>\n'
        f'  </div>\n'
        f'</div>'
    )


def generate_html(jobs: list[dict]) -> str:
    # Group by source
    sources: dict[str, list[dict]] = {}
    for job in jobs:
        src = job.get("source", "unknown")
        sources.setdefault(src, []).append(job)
    sorted_sources = sorted(sources.items(), key=lambda x: -len(x[1]))

    # Tabs
    tabs = [f'<button class="tab active" data-source="all">All ({len(jobs)})</button>']
    for src, src_jobs in sorted_sources:
        color = SOURCE_COLORS.get(src, "#6b7280")
        tabs.append(
            f'<button class="tab" data-source="{esc(src)}" '
            f'style="--tab-color:{color}">{esc(src)} ({len(src_jobs)})</button>'
        )

    # Cards
    cards = [render_job(j, i) for i, j in enumerate(jobs)]

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Board - {len(jobs)} Jobs</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f172a;color:#e2e8f0}}
.header{{background:#1e293b;padding:16px 24px;position:sticky;top:0;z-index:100;border-bottom:1px solid #334155}}
.header h1{{font-size:20px;font-weight:600;margin-bottom:12px}}
.tabs{{display:flex;gap:6px;flex-wrap:wrap}}
.tab{{padding:6px 14px;border-radius:20px;border:1px solid #475569;background:#1e293b;color:#94a3b8;cursor:pointer;font-size:13px;font-weight:500;transition:all .15s}}
.tab:hover{{background:#334155;color:#e2e8f0}}
.tab.active{{background:#3b82f6;border-color:#3b82f6;color:#fff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:12px;padding:16px 24px}}
.job-card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px;transition:all .15s}}
.job-card:hover{{border-color:#3b82f6;transform:translateY(-2px);box-shadow:0 4px 12px rgba(0,0,0,.3)}}
.job-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.source-badge{{padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;color:#fff;text-transform:uppercase;letter-spacing:.5px}}
.posted{{font-size:11px;color:#64748b}}
.job-title{{font-size:15px;font-weight:600;color:#f1f5f9;margin-bottom:4px;line-height:1.3}}
.job-company{{font-size:13px;color:#94a3b8;margin-bottom:2px}}
.job-location{{font-size:12px;color:#64748b;margin-bottom:10px}}
.job-actions{{display:flex;gap:8px}}
.apply-btn{{display:inline-flex;align-items:center;padding:6px 16px;background:#3b82f6;color:#fff;border-radius:6px;font-size:13px;font-weight:500;text-decoration:none;transition:background .15s}}
.apply-btn:hover{{background:#2563eb}}
.view-btn{{display:inline-flex;align-items:center;padding:6px 16px;background:#334155;color:#94a3b8;border-radius:6px;font-size:13px;font-weight:500;text-decoration:none;transition:all .15s}}
.view-btn:hover{{background:#475569;color:#e2e8f0}}
.stats{{font-size:12px;color:#64748b;margin-bottom:12px}}
.hidden{{display:none!important}}
@media(max-width:640px){{.grid{{grid-template-columns:1fr;padding:12px}}}}
</style>
</head>
<body>
<div class="header">
  <h1>Job Board</h1>
  <div class="stats">{len(jobs)} jobs across {len(sorted_sources)} sources</div>
  <div class="tabs">{"".join(tabs)}</div>
</div>
<div class="grid">{"".join(cards)}</div>
<script>
const tabs=document.querySelectorAll(".tab");
const cards=document.querySelectorAll(".job-card");
tabs.forEach(t=>{{t.addEventListener("click",()=>{{tabs.forEach(x=>x.classList.remove("active"));t.classList.add("active");const s=t.dataset.source;cards.forEach(c=>c.classList.toggle("hidden",s!=="all"&&c.dataset.source!==s))}})}});
</script>
</body>
</html>'''


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/gen_job_board.py <input.json> [output.html]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_name("job_board.html")

    with open(input_path, encoding="utf-8") as f:
        jobs = json.load(f)

    html_content = generate_html(jobs)
    output_path.write_text(html_content, encoding="utf-8")

    # Summary
    sources: dict[str, int] = {}
    for j in jobs:
        src = j.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print(f"Generated: {output_path}")
    print(f"Total jobs: {len(jobs)}")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")


if __name__ == "__main__":
    main()
