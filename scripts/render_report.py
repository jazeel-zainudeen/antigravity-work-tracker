#!/usr/bin/env python3
"""
render_report.py - Reads harvested JSON and outputs a standalone Markdown + HTML report.
Loads project name mappings from external config files (local overrides supported).
"""

import os
import sys
import json
import argparse
import urllib.parse
import binascii
import re
from datetime import datetime

def load_project_mappings(config_dir=None):
    """
    Loads project mappings from config files.
    Priority:
    1. config/project_mappings.local.json (User's private git-ignored file)
    2. config/project_mappings.example.json (Default fallback template)
    """
    mappings = {}
    if not config_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_dir = os.path.join(base_dir, "config")

    example_cfg = os.path.join(config_dir, "project_mappings.example.json")
    local_cfg = os.path.join(config_dir, "project_mappings.local.json")

    # Load defaults
    if os.path.exists(example_cfg):
        try:
            with open(example_cfg, "r", encoding="utf-8") as f:
                mappings.update(json.load(f))
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load {example_cfg}: {e}\n")

    # Load user local overrides
    if os.path.exists(local_cfg):
        try:
            with open(local_cfg, "r", encoding="utf-8") as f:
                mappings.update(json.load(f))
        except Exception as e:
            sys.stderr.write(f"Warning: Failed to load {local_cfg}: {e}\n")

    return mappings

def format_project_name(folder, mappings):
    if not folder or folder == "/":
        return "System / Server Tools", "[/root]"
    folder = folder.rstrip("/")
    base = os.path.basename(folder)

    # Check mapping or fallback to humanized name
    display_name = mappings.get(base, base.replace("-", " ").replace("_", " ").title())
    return display_name, f"[{folder}]"

def render_table(harvested_data, mappings):
    records = harvested_data.get("records", [])
    if not records:
        return "<p>No recorded activity found for the requested date(s).</p>"

    # Group by Date -> (Server, Folder)
    by_date = {}
    for r in records:
        d = r.get("date")
        if not d:
            continue
        if d not in by_date:
            by_date[d] = {}
        
        server = r.get("server", "localhost")
        folders = r.get("folders", ["/"])
        folder = folders[0] if folders else "/"
        if "vscode-remote" in folder:
            parsed = urllib.parse.unquote(folder)
            if "7b22686f73744e616d65223a22" in parsed:
                try:
                    m = re.search(r"ssh-remote\+([0-9a-fA-F]+)(/.*)", parsed)
                    if m:
                        server = json.loads(binascii.unhexlify(m.group(1)).decode())["hostName"]
                        folder = m.group(2)
                except:
                    pass

        key = (server, folder)
        if key not in by_date[d]:
            by_date[d][key] = []
        by_date[d][key].append(r)

    # Build HTML rows
    table_rows = []
    total_week_hours = 0.0

    for d in sorted(by_date.keys()):
        server_folder_map = by_date[d]
        row_count = len(server_folder_map)
        daily_total = 0.0
        
        # Calculate daily total first
        for (srv, fld), items in server_folder_map.items():
            item_hours = min(4.0, max(0.5, len(items) * 0.5))
            daily_total += item_hours
        total_week_hours += daily_total

        first_row = True
        for (srv, fld), items in server_folder_map.items():
            proj_name, folder_tag = format_project_name(fld, mappings)
            item_hours = min(4.0, max(0.5, len(items) * 0.5))
            
            # Synthesize tasks
            bullets = []
            for item in items:
                title = item.get("title", "").strip()
                prev = item.get("preview", "").strip()
                t_str = title if title and title != "Interactive Session" else prev
                if t_str and t_str not in bullets:
                    t_clean = t_str.split("\n")[0][:120]
                    bullets.append(t_clean)
            
            task_desc = "<br>• ".join(bullets)
            if not task_desc:
                task_desc = "Development and active workspace updates."
            else:
                task_desc = "• " + task_desc

            # Format row
            if first_row:
                row_html = f"""    <tr>
      <td rowspan="{row_count}" align="center"><b>{d}</b></td>
      <td><code>{srv}</code></td>
      <td>{proj_name}<br><code>{folder_tag}</code></td>
      <td>{task_desc}</td>
      <td align="center">{item_hours:.1f} hrs</td>
      <td rowspan="{row_count}" align="center"><b>{daily_total:.2f} hrs</b></td>
    </tr>"""
                first_row = False
            else:
                row_html = f"""    <tr>
      <td><code>{srv}</code></td>
      <td>{proj_name}<br><code>{folder_tag}</code></td>
      <td>{task_desc}</td>
      <td align="center">{item_hours:.1f} hrs</td>
    </tr>"""
            table_rows.append(row_html)

    table_content = "\n".join(table_rows)
    html = f"""<table>
  <thead>
    <tr>
      <th style="text-align: center;">Date</th>
      <th style="text-align: left;">Server</th>
      <th style="text-align: left;">Project(s) [Folder]</th>
      <th style="text-align: left;">Work done</th>
      <th style="text-align: center;">Hours</th>
      <th style="text-align: center;">Daily Total</th>
    </tr>
  </thead>
  <tbody>
{table_content}
  </tbody>
  <tfoot>
    <tr>
      <td colspan="5" align="right"><b>Total Hours</b></td>
      <td align="center"><b>~{total_week_hours:.2f} hrs</b></td>
    </tr>
  </tfoot>
</table>"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Render Work Tracker Report")
    parser.add_argument("--input", required=True, help="Input JSON file from harvest.py")
    parser.add_argument("--output", help="Output Markdown/HTML file")
    parser.add_argument("--config-dir", help="Custom configuration directory")
    args = parser.parse_args()

    mappings = load_project_mappings(args.config_dir)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    html_table = render_table(data, mappings)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_table + "\n")
        print(f"Report written to {args.output}")
    else:
        print(html_table)

if __name__ == "__main__":
    main()
