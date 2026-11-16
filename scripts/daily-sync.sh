#!/bin/bash
# daily-sync.sh - Automated daily runner for Antigravity Work Tracker
# Runs silently via user cron or manual CLI trigger.

DATE_ARG="${1:-today}"
REPORTS_DIR="$HOME/Documents/WorkLogs"
SKILL_DIR="$HOME/.gemini/antigravity/skills/daily-work-tracker/scripts"

mkdir -p "$REPORTS_DIR"

TODAY_STR=$(date +%Y-%m-%d)
JSON_OUTPUT="$REPORTS_DIR/${TODAY_STR}.json"
MD_OUTPUT="$REPORTS_DIR/${TODAY_STR}.md"

# 1. Harvest logs
python3 "$SKILL_DIR/harvest.py" --date "$DATE_ARG" --output "$JSON_OUTPUT" > /dev/null 2>&1

# 2. Render merged-cell table report
if [ -f "$JSON_OUTPUT" ]; then
    python3 "$SKILL_DIR/render_report.py" --input "$JSON_OUTPUT" --output "$MD_OUTPUT" > /dev/null 2>&1
    echo "Daily work report generated: $MD_OUTPUT"
fi
