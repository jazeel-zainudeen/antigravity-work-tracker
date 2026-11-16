#!/usr/bin/env python3
"""
export_excel.py - Generates beautiful, merged-cell .xlsx timesheet spreadsheets.
100% Zero-dependency: Built using Python 3 standard library (zipfile + xml).
"""

import os
import sys
import json
import zipfile
import io
import html
import urllib.parse
import binascii
import re

def escape_xml(s):
    if s is None:
        return ""
    return html.escape(str(s))

def generate_xlsx_bytes(records_by_date, mappings):
    """
    Builds OpenXML (.xlsx) bytes with merged cells, professional header formatting,
    and automatic column auto-sizing.
    """
    # Build sheet XML rows and merge cell tags
    rows_xml = []
    merge_cells = []
    
    # 1. Header row
    current_row = 1
    header_cols = ["Date", "Server", "Project [Folder]", "Work done", "Hours", "Daily Total"]
    h_cells = []
    for idx, name in enumerate(header_cols):
        col_letter = chr(ord('A') + idx)
        cell_ref = f"{col_letter}{current_row}"
        h_cells.append(f'<c r="{cell_ref}" t="inlineStr" s="1"><is><t>{escape_xml(name)}</t></is></c>')
    rows_xml.append(f'<row r="{current_row}" ht="28" customHeight="1">{"".join(h_cells)}</row>')

    total_hours = 0.0

    for d in sorted(records_by_date.keys()):
        server_folder_map = records_by_date[d]
        row_count = len(server_folder_map)
        start_row = current_row + 1
        
        # Calculate daily total
        daily_total = 0.0
        for (srv, fld), items in server_folder_map.items():
            item_hours = min(4.0, max(0.5, len(items) * 0.5))
            daily_total += item_hours
        total_hours += daily_total

        first_in_date = True
        for (srv, fld), items in server_folder_map.items():
            current_row += 1
            item_hours = min(4.0, max(0.5, len(items) * 0.5))

            # Resolve project name
            proj_name = fld.rstrip("/").split("/")[-1] if fld and fld != "/" else "Root Workspace"
            display_name = mappings.get(proj_name, proj_name.replace("-", " ").replace("_", " ").title())
            proj_cell_text = f"{display_name}\n[{fld}]"

            # Tasks bullets
            bullets = []
            for item in items:
                title = item.get("title", "").strip()
                prev = item.get("preview", "").strip()
                t_str = title if title and title != "Interactive Session" else prev
                if t_str and t_str not in bullets:
                    t_clean = t_str.split("\n")[0][:120]
                    bullets.append(t_clean)
            task_desc = "\n• ".join(bullets)
            task_desc = ("• " + task_desc) if task_desc else "Development and active workspace updates."

            # Calculate height roughly based on text lines
            lines_count = max(task_desc.count("\n") + 1, proj_cell_text.count("\n") + 1)
            row_ht = max(24, lines_count * 18)

            row_cells = []
            # Date (Col A)
            if first_in_date:
                row_cells.append(f'<c r="A{current_row}" t="inlineStr" s="2"><is><t>{escape_xml(d)}</t></is></c>')
            else:
                row_cells.append(f'<c r="A{current_row}" s="2"/>')

            # Server (Col B)
            row_cells.append(f'<c r="B{current_row}" t="inlineStr" s="3"><is><t>{escape_xml(srv)}</t></is></c>')

            # Project [Folder] (Col C)
            row_cells.append(f'<c r="C{current_row}" t="inlineStr" s="4"><is><t>{escape_xml(proj_cell_text)}</t></is></c>')

            # Work done (Col D)
            row_cells.append(f'<c r="D{current_row}" t="inlineStr" s="5"><is><t>{escape_xml(task_desc)}</t></is></c>')

            # Hours (Col E)
            row_cells.append(f'<c r="E{current_row}" t="n" s="6"><v>{item_hours:.1f}</v></c>')

            # Daily Total (Col F)
            if first_in_date:
                row_cells.append(f'<c r="F{current_row}" t="n" s="7"><v>{daily_total:.2f}</v></c>')
                first_in_date = False
            else:
                row_cells.append(f'<c r="F{current_row}" s="7"/>')

            rows_xml.append(f'<row r="{current_row}" ht="{row_ht}" customHeight="1">{"".join(row_cells)}</row>')

        # Add cell merges if multi-row
        if row_count > 1:
            end_row = current_row
            merge_cells.append(f'<mergeCell ref="A{start_row}:A{end_row}"/>')
            merge_cells.append(f'<mergeCell ref="F{start_row}:F{end_row}"/>')

    # Total Row
    current_row += 1
    total_row_cells = [
        f'<c r="A{current_row}" s="8"/>',
        f'<c r="B{current_row}" s="8"/>',
        f'<c r="C{current_row}" s="8"/>',
        f'<c r="D{current_row}" s="8"/>',
        f'<c r="E{current_row}" t="inlineStr" s="8"><is><t>Grand Total:</t></is></c>',
        f'<c r="F{current_row}" t="n" s="9"><v>{total_hours:.2f}</v></c>'
    ]
    rows_xml.append(f'<row r="{current_row}" ht="26" customHeight="1">{"".join(total_row_cells)}</row>')

    merge_block = ""
    if merge_cells:
        merge_block = f'<mergeCells count="{len(merge_cells)}">{"".join(merge_cells)}</mergeCells>'

    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews>
    <sheetView tabSelected="1" workbookViewId="0">
      <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>
    </sheetView>
  </sheetViews>
  <cols>
    <col min="1" max="1" width="14" customWidth="1"/>
    <col min="2" max="2" width="18" customWidth="1"/>
    <col min="3" max="3" width="28" customWidth="1"/>
    <col min="4" max="4" width="55" customWidth="1"/>
    <col min="5" max="5" width="12" customWidth="1"/>
    <col min="6" max="6" width="14" customWidth="1"/>
  </cols>
  <sheetData>
    {"".join(rows_xml)}
  </sheetData>
  {merge_block}
</worksheet>'''

    # Styles definition
    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="5">
    <font><sz val="10"/><name val="Segoe UI"/><color rgb="FF333333"/></font>
    <font><b/><sz val="10"/><name val="Segoe UI"/><color rgb="FFFFFFFF"/></font>
    <font><b/><sz val="10"/><name val="Segoe UI"/><color rgb="FF1F2937"/></font>
    <font><sz val="9.5"/><name val="Consolas"/><color rgb="FF2563EB"/></font>
    <font><b/><sz val="10.5"/><name val="Segoe UI"/><color rgb="FF15803D"/></font>
  </fonts>
  <fills count="5">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E293B"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF1F5F9"/></patternFill></fill>
  </fills>
  <borders count="3">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFE2E8F0"/></left>
      <right style="thin"><color rgb="FFE2E8F0"/></right>
      <top style="thin"><color rgb="FFE2E8F0"/></top>
      <bottom style="thin"><color rgb="FFE2E8F0"/></bottom>
    </border>
    <border>
      <left/><right/>
      <top style="thin"><color rgb="FF94A3B8"/></top>
      <bottom style="double"><color rgb="FF1E293B"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="10">
    <!-- 0: Default -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <!-- 1: Header (Dark Blue, Bold White) -->
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <!-- 2: Date Cell (Centered Bold) -->
    <xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <!-- 3: Server (Monospace) -->
    <xf numFmtId="0" fontId="3" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="top" wrapText="1"/>
    </xf>
    <!-- 4: Project [Folder] -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="top" wrapText="1"/>
    </xf>
    <!-- 5: Work Done -->
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="top" wrapText="1"/>
    </xf>
    <!-- 6: Hours (Centered Right) -->
    <xf numFmtId="2" fontId="0" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="right" vertical="top"/>
    </xf>
    <!-- 7: Daily Total (Centered Green Bold) -->
    <xf numFmtId="2" fontId="4" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <!-- 8: Total Label -->
    <xf numFmtId="0" fontId="2" fillId="4" borderId="2" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="right" vertical="center"/>
    </xf>
    <!-- 9: Grand Total Value -->
    <xf numFmtId="2" fontId="4" fillId="4" borderId="2" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
  </cellXfs>
</styleSheet>'''

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>''')

        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')

        z.writestr('xl/_rels/workbook.xml.rels', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''')

        z.writestr('xl/workbook.xml', '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Timesheet" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>''')

        z.writestr('xl/styles.xml', styles_xml)
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml)

    return buf.getvalue()

def group_records(records):
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
    return by_date

def export_excel(json_path, output_dir, mappings):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    if not records:
        print("No records found to export to Excel.")
        return []

    by_date = group_records(records)
    os.makedirs(output_dir, exist_ok=True)
    
    generated_files = []
    
    # Generate per-day Excel spreadsheet
    for d, server_folder_map in by_date.items():
        daily_dict = {d: server_folder_map}
        xlsx_bytes = generate_xlsx_bytes(daily_dict, mappings)
        daily_file = os.path.join(output_dir, f"{d}.xlsx")
        with open(daily_file, "wb") as f:
            f.write(xlsx_bytes)
        print(f"Generated Excel spreadsheet: {daily_file}")
        generated_files.append(daily_file)

    # If multiple dates exist (e.g. range / weekly), also generate a consolidated multi-day sheet
    if len(by_date) > 1:
        consolidated_bytes = generate_xlsx_bytes(by_date, mappings)
        dates_sorted = sorted(by_date.keys())
        summary_name = f"{dates_sorted[0]}_to_{dates_sorted[-1]}_summary.xlsx"
        summary_file = os.path.join(output_dir, summary_name)
        with open(summary_file, "wb") as f:
            f.write(consolidated_bytes)
        print(f"Generated Range Summary Excel: {summary_file}")
        generated_files.append(summary_file)

    return generated_files

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export harvested timesheets to Excel (.xlsx)")
    parser.add_argument("--input", required=True, help="Input JSON file from harvest.py")
    parser.add_argument("--output-dir", required=True, help="Directory to save Excel spreadsheets")
    parser.add_argument("--config-dir", help="Configuration directory for project mappings")
    args = parser.parse_args()

    # Load mappings
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_dir = args.config_dir or os.path.join(base_dir, "config")
    
    mappings = {}
    ex_cfg = os.path.join(cfg_dir, "project_mappings.example.json")
    loc_cfg = os.path.join(cfg_dir, "project_mappings.local.json")
    if os.path.exists(ex_cfg):
        with open(ex_cfg, "r", encoding="utf-8") as f:
            mappings.update(json.load(f))
    if os.path.exists(loc_cfg):
        with open(loc_cfg, "r", encoding="utf-8") as f:
            mappings.update(json.load(f))

    export_excel(args.input, args.output_dir, mappings)
