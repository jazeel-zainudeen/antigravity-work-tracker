#!/usr/bin/env python3
"""
harvest.py - Zero-dependency data harvester for Antigravity Work Tracker.
Collects conversation summaries, tool execution logs, and open workspace history
from local machine and configured remote SSH servers.
"""

import os
import sys
import json
import sqlite3
import argparse
import subprocess
from datetime import datetime, timedelta

def get_target_dates(date_arg):
    today = datetime.now().date()
    if not date_arg or date_arg == "today":
        return [today.strftime("%Y-%m-%d")]
    elif date_arg == "yesterday":
        return [(today - timedelta(days=1)).strftime("%Y-%m-%d")]
    elif date_arg in ["last_week", "lastweek"]:
        # Last week Monday to Friday
        monday = today - timedelta(days=today.weekday() + 7)
        return [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    elif date_arg in ["this_week", "thisweek"]:
        # This week Monday to today
        monday = today - timedelta(days=today.weekday())
        days_count = min(5, (today - monday).days + 1)
        return [(monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_count)]
    elif ":" in date_arg or ".." in date_arg:
        sep = ":" if ":" in date_arg else ".."
        start_s, end_s = date_arg.split(sep)
        d_start = datetime.strptime(start_s.strip(), "%Y-%m-%d").date()
        d_end = datetime.strptime(end_s.strip(), "%Y-%m-%d").date()
        days = []
        curr = d_start
        while curr <= d_end:
            days.append(curr.strftime("%Y-%m-%d"))
            curr += timedelta(days=1)
        return days
    else:
        # specific single date YYYY-MM-DD
        return [date_arg.strip()]

def get_ssh_hosts():
    ssh_config = os.path.expanduser("~/.ssh/config")
    hosts = []
    if os.path.exists(ssh_config):
        with open(ssh_config, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.lower().startswith("host "):
                    parts = line.split()[1:]
                    for p in parts:
                        if not any(c in p for c in ["*", "?", "!"]) and p not in ["github.com", "gitlab.com"]:
                            hosts.append(p)
    return list(dict.fromkeys(hosts))

def harvest_local(target_dates):
    results = []
    # 1. Check conversation_summaries.db
    db_paths = [
        os.path.expanduser("~/.gemini/antigravity/conversation_summaries.db"),
        os.path.expanduser("~/.gemini/antigravity-cli/conversation_summaries.db")
    ]
    seen_convs = set()
    for db in db_paths:
        if not os.path.exists(db):
            continue
        try:
            conn = sqlite3.connect(db)
            c = conn.cursor()
            for t_date in target_dates:
                query = """
                    SELECT conversation_id, title, preview, last_modified_time, last_user_input_time, workspace_uris 
                    FROM conversation_summaries 
                    WHERE last_modified_time LIKE ? OR last_user_input_time LIKE ?
                """
                c.execute(query, (f"{t_date}%", f"{t_date}%"))
                for row in c.fetchall():
                    cid, title, prev, lm, lu, ws = row
                    if cid in seen_convs:
                        continue
                    seen_convs.add(cid)
                    # parse workspace
                    folders = []
                    if ws:
                        try:
                            f_list = json.loads(ws)
                            folders = [f.replace("file://", "") for f in f_list]
                        except:
                            folders = [ws.replace("file://", "")]
                    results.append({
                        "date": t_date,
                        "server": "localhost",
                        "conversation_id": cid,
                        "title": title or "Interactive Session",
                        "preview": prev or "",
                        "folders": folders or [os.path.expanduser("~")],
                        "last_modified": lm,
                        "source": "CLI/IDE Local"
                    })
        except Exception as e:
            pass

    # 2. Check local IDE workspace storage
    ws_dir = os.path.expanduser("~/.config/Antigravity IDE/User/workspaceStorage")
    if os.path.exists(ws_dir):
        for root, dirs, files in os.walk(ws_dir):
            if "state.vscdb" in files:
                p = os.path.join(root, "state.vscdb")
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(p))
                    m_date = mtime.strftime("%Y-%m-%d")
                    if m_date in target_dates:
                        ws_json = os.path.join(root, "workspace.json")
                        ws_uri = ""
                        if os.path.exists(ws_json):
                            try:
                                with open(ws_json) as f:
                                    ws_uri = json.load(f).get("folder", "")
                            except:
                                pass
                        
                        # read active files
                        conn = sqlite3.connect(p)
                        c = conn.cursor()
                        c.execute("SELECT value FROM ItemTable WHERE key = 'history.entries';")
                        row = c.fetchone()
                        active_files = []
                        if row and row[0]:
                            v = row[0]
                            if isinstance(v, bytes): v = v.decode("utf-8", errors="ignore")
                            try:
                                for item in json.loads(v):
                                    res = item.get("editor", {}).get("resource", "")
                                    if res: active_files.append(res)
                            except:
                                pass
                        if ws_uri or active_files:
                            results.append({
                                "date": m_date,
                                "server": "localhost" if "vscode-remote" not in ws_uri else "remote-ide",
                                "conversation_id": "",
                                "title": "IDE Workspace Active",
                                "preview": f"Files: {', '.join([os.path.basename(f) for f in active_files[:5]])}",
                                "folders": [ws_uri],
                                "last_modified": str(mtime),
                                "source": "IDE Workspace"
                            })
                except:
                    pass
    return results

def harvest_remote_host(host, target_dates):
    dates_str = json.dumps(target_dates)
    remote_script = f"""
import os, sys, json, sqlite3
from datetime import datetime

target_dates = {dates_str}
results = []
seen_convs = set()

# Search DBs
roots = ["/root/.gemini", "/home"]
dbs = []
for r in roots:
    for dirpath, dirs, files in os.walk(r):
        if "conversation_summaries.db" in files:
            dbs.append(os.path.join(dirpath, "conversation_summaries.db"))

for db in set(dbs):
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        for t_date in target_dates:
            query = "SELECT conversation_id, title, preview, last_modified_time, last_user_input_time, workspace_uris FROM conversation_summaries WHERE last_modified_time LIKE ? OR last_user_input_time LIKE ?"
            c.execute(query, (f"{{t_date}}%", f"{{t_date}}%"))
            for row in c.fetchall():
                cid, title, prev, lm, lu, ws = row
                if cid in seen_convs: continue
                seen_convs.add(cid)
                folders = []
                if ws:
                    try:
                        f_list = json.loads(ws)
                        folders = [f.replace("file://", "") for f in f_list]
                    except:
                        folders = [ws.replace("file://", "")]
                results.append({{
                    "date": t_date,
                    "server": "{host}",
                    "conversation_id": cid,
                    "title": title or "Interactive Session",
                    "preview": prev or "",
                    "folders": folders or ["/"],
                    "last_modified": lm,
                    "source": "Remote Antigravity"
                }})
    except Exception as e:
        pass

print("JSON_START" + json.dumps(results) + "JSON_END")
"""
    cmd = ["ssh", "-o", "ConnectTimeout=3", "-o", "BatchMode=yes", host, "python3", "-"]
    try:
        proc = subprocess.run(cmd, input=remote_script, capture_output=True, text=True, timeout=10)
        out = proc.stdout
        if "JSON_START" in out and "JSON_END" in out:
            json_str = out.split("JSON_START")[1].split("JSON_END")[0]
            return json.loads(json_str)
    except:
        pass
    return []

def main():
    parser = argparse.ArgumentParser(description="Antigravity Work Harvester")
    parser.add_argument("--date", default="today", help="Date: today, yesterday, last_week, this_week, YYYY-MM-DD, or range YYYY-MM-DD:YYYY-MM-DD")
    parser.add_argument("--output", help="Save output JSON path")
    args = parser.parse_args()

    target_dates = get_target_dates(args.date)
    hosts = get_ssh_hosts()

    all_data = []
    # 1. Harvest local
    local_data = harvest_local(target_dates)
    all_data.extend(local_data)

    # 2. Harvest remotes
    for h in hosts:
        remote_data = harvest_remote_host(h, target_dates)
        all_data.extend(remote_data)

    payload = {
        "target_dates": target_dates,
        "scanned_hosts": hosts,
        "total_records": len(all_data),
        "records": all_data
    }

    if args.output:
        with open(args.output, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"Saved {len(all_data)} records to {args.output}")
    else:
        print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    main()
