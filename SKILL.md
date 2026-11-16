---
name: daily-work-tracker
description: Automatically compiles and generates daily or date-range work summaries, projects, folders, tasks, and hours worked across local and remote SSH servers for Antigravity IDE and CLI. Formats output into a clean merged-cell HTML/Markdown table with daily sum totals.
---

# Daily Work Tracker & Timesheet Skill

When the user asks questions such as:
- *"what work did I do today?"*
- *"what work did I do yesterday?"*
- *"summarize my work for last week / [date]"*
- *"give me my timesheet for [date range]"*
- or triggers `/timesheet`

Follow this process:

## Step 1: Run Harvester Script
Execute the zero-dependency harvester script using `run_command`:
```bash
python3 ~/.gemini/antigravity/skills/daily-work-tracker/scripts/harvest.py --date <DATE_SPEC>
```
Where `<DATE_SPEC>` can be:
- `today` (default)
- `yesterday`
- `last_week` (Monday through Friday of last week)
- `this_week`
- A specific date: `YYYY-MM-DD` (e.g. `2026-11-13`)
- A date range: `YYYY-MM-DD:YYYY-MM-DD` (e.g. `2026-11-09:2026-11-13`)

## Step 2: Parse and Synthesize the Results
From the harvested JSON records:
1. **Differentiate Folders & Projects**:
   - Extract the specific project folder path for each server.
   - If multiple folders were touched on the same server, separate them into distinct rows.
2. **Rephrase & Group Tasks**:
   - Consolidate raw conversational prompts, tool executions, and file edits into clean, professional bullet points.
   - Deduplicate repeated questions or retried commands.
   - Highlight key features built, bugs resolved, and commits made.
3. **Calculate Hours**:
   - Estimate active session duration based on timestamps and task complexity (minimum 15–30 mins per interactive task).
   - Sum the hours per day to compute the **Daily Total**.

## Step 3: Present in Merged-Cell HTML Table & Excel
Always render the results in an HTML table with merged rows (`rowspan`) for identical dates and daily sum totals.

In addition, an Excel file (`.xlsx`) is generated automatically for each day inside `~/Documents/WorkLogs/excel/`:
```bash
python3 ~/.gemini/antigravity/skills/daily-work-tracker/scripts/export_excel.py --input <JSON_FILE> --output-dir ~/Documents/WorkLogs/excel/
```

```html
<table>
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
    <tr>
      <td rowspan="N" align="center"><b>Date</b></td>
      <td><code>server-name</code></td>
      <td>Project Name<br><code>[/folder/path]</code></td>
      <td>Task description bullet points.</td>
      <td align="center">X.X hrs</td>
      <td rowspan="N" align="center"><b>Y.Y hrs</b></td>
    </tr>
  </tbody>
  <tfoot>
    <tr>
      <td colspan="5" align="right"><b>Total Hours</b></td>
      <td align="center"><b>Z.Z hrs</b></td>
    </tr>
  </tfoot>
</table>
```
