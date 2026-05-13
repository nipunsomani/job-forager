"""Generate a dual-view HTML job board from JSON files.

Usage:
    python scripts/gen_job_board.py <all_jobs.json> <new_jobs.json> [output.html]

Generates a single HTML file with a toggle to switch between All Jobs and New Jobs views.
A single source filter row works with whichever view is active.
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
        f'<div class="job-card" data-source="{esc(source)}">'
        f'<div class="job-header">'
        f'<span class="source-badge" style="background:{color}">{esc(source)}</span>'
        f'<span class="posted">{posted}</span>'
        f'</div>'
        f'<div class="job-title">{title}</div>'
        f'<div class="job-company">{company}</div>'
        f'<div class="job-location">{location}</div>'
        f'<div class="job-actions">'
        f'<a href="{apply_url}" target="_blank" rel="noopener" class="apply-btn">Apply</a>'
        f'<a href="{job_url}" target="_blank" rel="noopener" class="view-link">View</a>'
        f'</div>'
        f'</div>'
    )


def build_all_source_tabs(jobs: list[dict]) -> str:
    sources: dict[str, int] = {}
    for j in jobs:
        src = j.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    sorted_sources = sorted(sources.items(), key=lambda x: -x[1])

    tabs = [f'<button class="tab active" data-source="all">All ({len(jobs)})</button>']
    for src, count in sorted_sources:
        color = SOURCE_COLORS.get(src, "#6b7280")
        tabs.append(
            f'<button class="tab" data-source="{esc(src)}" '
            f'style="--tab-color:{color}">{esc(src)} ({count})</button>'
        )
    return "".join(tabs)


def generate_html(all_jobs: list[dict], new_jobs: list[dict]) -> str:
    all_cards = "".join(render_job(j, i) for i, j in enumerate(all_jobs))
    new_cards = "".join(render_job(j, i) for i, j in enumerate(new_jobs))
    source_tabs = build_all_source_tabs(all_jobs)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Job Forager</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
.header{{background:#1e293b;padding:16px 24px;position:sticky;top:0;z-index:100;border-bottom:1px solid #334155}}
.header-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}
.header h1{{font-size:22px;font-weight:700;letter-spacing:-0.5px}}
.view-toggle{{display:flex;background:#0f172a;border-radius:8px;padding:3px;border:1px solid #334155}}
.view-btn{{padding:8px 20px;border-radius:6px;border:none;background:transparent;color:#94a3b8;cursor:pointer;font-size:14px;font-weight:600;transition:all .2s}}
.view-btn.active{{background:#3b82f6;color:#fff;box-shadow:0 2px 8px rgba(59,130,246,0.3)}}
.view-btn:hover:not(.active){{color:#e2e8f0;background:#1e293b}}
.view-btn .badge{{display:inline-block;min-width:20px;padding:1px 6px;border-radius:10px;font-size:11px;font-weight:700;margin-left:6px;background:rgba(255,255,255,0.15)}}
.view-btn.active .badge{{background:rgba(255,255,255,0.25)}}
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
.view-link{{display:inline-flex;align-items:center;padding:6px 16px;background:#334155;color:#94a3b8;border-radius:6px;font-size:13px;font-weight:500;text-decoration:none;transition:all .15s}}
.view-link:hover{{background:#475569;color:#e2e8f0}}
.hidden{{display:none!important}}
@media(max-width:640px){{
  .grid{{grid-template-columns:1fr;padding:12px}}
  .header-top{{flex-direction:column;gap:12px}}
}}
</style>
</head>
<body>
<div class="header">
  <div class="header-top">
    <h1>Job Forager</h1>
    <div class="view-toggle">
      <button class="view-btn active" data-view="all">All Jobs<span class="badge">{len(all_jobs)}</span></button>
      <button class="view-btn" data-view="new">New Jobs<span class="badge">{len(new_jobs)}</span></button>
    </div>
  </div>
  <div class="tabs" id="source-tabs">{source_tabs}</div>
</div>

<div class="grid" id="grid-all">{all_cards}</div>
<div class="grid hidden" id="grid-new">{new_cards}</div>

<script>
let currentView="all";
let currentSource="all";

// View toggle
document.querySelectorAll(".view-btn").forEach(btn=>{{
  btn.addEventListener("click",()=>{{
    document.querySelectorAll(".view-btn").forEach(b=>b.classList.remove("active"));
    btn.classList.add("active");
    currentView=btn.dataset.view;
    currentSource="all";
    // Reset source tabs
    document.querySelectorAll(".tab").forEach(t=>t.classList.toggle("active",t.dataset.source==="all"));
    // Show/hide grids
    document.getElementById("grid-all").classList.toggle("hidden",currentView!=="all");
    document.getElementById("grid-new").classList.toggle("hidden",currentView!=="new");
    filterCards();
  }});
}});

// Source tabs
document.querySelectorAll(".tab").forEach(tab=>{{
  tab.addEventListener("click",()=>{{
    document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
    tab.classList.add("active");
    currentSource=tab.dataset.source;
    filterCards();
  }});
}});

function filterCards(){{
  const grid=currentView==="all"?document.getElementById("grid-all"):document.getElementById("grid-new");
  grid.querySelectorAll(".job-card").forEach(card=>{{
    card.classList.toggle("hidden",currentSource!=="all"&&card.dataset.source!==currentSource);
  }});
}}
</script>
</body>
</html>'''


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/gen_job_board.py <all_jobs.json> <new_jobs.json> [output.html]")
        sys.exit(1)

    all_path = Path(sys.argv[1])
    new_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else all_path.with_name("job_board.html")

    with open(all_path, encoding="utf-8") as f:
        all_jobs = json.load(f)
    with open(new_path, encoding="utf-8") as f:
        new_jobs = json.load(f)

    html_content = generate_html(all_jobs, new_jobs)
    output_path.write_text(html_content, encoding="utf-8")

    all_sources: dict[str, int] = {}
    for j in all_jobs:
        src = j.get("source", "unknown")
        all_sources[src] = all_sources.get(src, 0) + 1

    new_sources: dict[str, int] = {}
    for j in new_jobs:
        src = j.get("source", "unknown")
        new_sources[src] = new_sources.get(src, 0) + 1

    print(f"Generated: {output_path}")
    print(f"All jobs: {len(all_jobs)}")
    for src, count in sorted(all_sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")
    print(f"New jobs: {len(new_jobs)}")
    for src, count in sorted(new_sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")


if __name__ == "__main__":
    main()
