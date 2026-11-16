# Antigravity Work Tracker 🚀

An automated, multi-host daily work tracking and timesheet generation system built natively for **Antigravity CLI** and **Antigravity IDE**.

Automatically inspects local and remote SSH development logs, calculates active hours, and generates clean, merged-cell HTML/Markdown timesheet tables with daily sum totals.

---

## Features

- 🔒 **Lightweight & Portable**: Runs entirely in user-space (`~/.gemini/` and standard user `crontab`). No root permissions or daemons needed.
- 🌐 **Multi-Host Auto-Discovery**: Automatically parses your `~/.ssh/config` and inspects work on remote staging/production servers.
- 📁 **Project & Folder Differentiation**: Distinguishes work done across different project directories on the same or different servers.
- 🎯 **Privacy-First Custom Mappings**: Custom project names and internal folder aliases are kept in `config/project_mappings.local.json` which is ignored by Git.
- 🔄 **IDE & CLI Native**: Use interactively in chat or let it run automatically in the background even when IDE/CLI are closed.

---

## Project Structure

```
antigravity-work-tracker/
├── install.sh                          # 1-step installer
├── SKILL.md                            # Antigravity skill instructions
├── .gitignore                          # Ignores logs, reports, and local config
├── config/
│   ├── project_mappings.example.json   # Template for project name display mappings
│   └── project_mappings.local.json     # [Git Ignored] Your private local overrides
├── scripts/
│   ├── harvest.py                      # Zero-dependency local/remote log harvester
│   ├── render_report.py                # Merged-cell HTML/Markdown table renderer
│   └── daily-sync.sh                   # Cron/manual background runner
└── README.md
```

---

## Quick Installation

Clone the repository and run the single-step installer:

```bash
git clone https://github.com/<your-username>/antigravity-work-tracker.git
cd antigravity-work-tracker
./install.sh
```

The installer will:
1. Copy the skill into your Antigravity skills directories (`~/.gemini/antigravity/skills/` and `~/.gemini/antigravity-cli/skills/`).
2. Generate your local mapping configuration at `config/project_mappings.local.json`.
3. Set up a daily user crontab running Monday through Friday at 19:00 (saved to `~/Documents/WorkLogs/`).

---

## Configuration & Custom Project Names

To customize how folder paths map to human-friendly project names in your timesheet:

1. Edit your local mapping file:
   ```bash
   nano config/project_mappings.local.json
   ```
2. Add your folder basenames and display names:
   ```json
   {
     "my-frontend-app": "Customer Portal",
     "api-backend": "Core REST API",
     "supportboard": "Support Board Chat"
   }
   ```
*(This file is git-ignored so your internal names and servers are never committed).*

---

## Usage

### 1. Interactive in Antigravity (IDE or CLI)
In any chat session, simply ask:
- *"Summarize my work today"*
- *"What work did I do on Friday?"*
- *"Generate my timesheet for last week"*
- *"Show work done between 2026-11-09 and 2026-11-13"*

### 2. Manual CLI Generation
To retroactively generate reports for any specific date or range:
```bash
# Today
./scripts/daily-sync.sh today

# Specific date
./scripts/daily-sync.sh 2026-11-13

# Date range
python3 ./scripts/harvest.py --date 2026-11-09:2026-11-13 --output /tmp/range.json
python3 ./scripts/render_report.py --input /tmp/range.json --output ~/Documents/WorkLogs/weekly.md
```

### 3. Automated Evening Runs
A user cron job runs automatically every weekday at 19:00:
```cron
0 19 * * 1-5 ~/.gemini/antigravity/skills/daily-work-tracker/scripts/daily-sync.sh today >> ~/Documents/WorkLogs/cron.log 2>&1
```
Reports are saved in `~/Documents/WorkLogs/YYYY-MM-DD.md`.

---

## License
MIT License. Feel free to use, share, and adapt across your team.
