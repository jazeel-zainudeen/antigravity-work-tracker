#!/bin/bash
# install.sh - Single-step installer for Antigravity Work Tracker
# Installs to user's Antigravity skills and sets up optional user crontab.

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_TARGET_IDE="$HOME/.gemini/antigravity/skills/daily-work-tracker"
SKILL_TARGET_CLI="$HOME/.gemini/antigravity-cli/skills/daily-work-tracker"
SKILL_TARGET_GLOBAL="$HOME/.gemini/skills/daily-work-tracker"
REPORTS_DIR="$HOME/Documents/WorkLogs"

echo "=== Installing Antigravity Work Tracker ==="

# 1. Create directories
mkdir -p "$SKILL_TARGET_IDE"
mkdir -p "$SKILL_TARGET_CLI"
mkdir -p "$REPORTS_DIR"

# 2. Setup local project mappings if not present
if [ ! -f "$REPO_DIR/config/project_mappings.local.json" ]; then
    echo "Creating config/project_mappings.local.json from example template..."
    cp "$REPO_DIR/config/project_mappings.example.json" "$REPO_DIR/config/project_mappings.local.json"
fi

# 3. Copy files to skill directories
echo "Installing skill files to ~/.gemini/..."
cp -r "$REPO_DIR/scripts" "$SKILL_TARGET_IDE/"
cp -r "$REPO_DIR/config" "$SKILL_TARGET_IDE/"
cp "$REPO_DIR/SKILL.md" "$SKILL_TARGET_IDE/"

# Mirror to CLI & Global roots
cp -r "$SKILL_TARGET_IDE"/* "$SKILL_TARGET_CLI/" 2>/dev/null || true
mkdir -p "$SKILL_TARGET_GLOBAL" 2>/dev/null && cp -r "$SKILL_TARGET_IDE"/* "$SKILL_TARGET_GLOBAL/" 2>/dev/null || true

# Make scripts executable
chmod +x "$SKILL_TARGET_IDE/scripts/"*.py
chmod +x "$SKILL_TARGET_IDE/scripts/"*.sh

echo "Skill installed successfully!"

# 4. Prompt / setup optional user cron
CRON_CMD="0 19 * * 1-5 $SKILL_TARGET_IDE/scripts/daily-sync.sh today >> $REPORTS_DIR/cron.log 2>&1"
if crontab -l 2>/dev/null | grep -Fq "daily-sync.sh"; then
    echo "User cron schedule already configured."
else
    echo "Setting up daily user crontab (Mon-Fri at 19:00)..."
    (crontab -l 2>/dev/null || true; echo "$CRON_CMD") | crontab -
    echo "Crontab installed!"
fi

echo ""
echo "=== Installation Complete ==="
echo "You can now ask Antigravity IDE or CLI:"
echo "  • 'Summarize my work today'"
echo "  • 'Generate my timesheet for last week'"
echo "  • Or run: $SKILL_TARGET_IDE/scripts/daily-sync.sh today"
echo "Reports directory: $REPORTS_DIR"
