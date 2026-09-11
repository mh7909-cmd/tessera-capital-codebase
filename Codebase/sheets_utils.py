import gspread
import gspread_formatting as gs_fmt
import os
import re
import time
import functools
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def quota_safe(func):
    """Decorator to catch Google Sheets 429 Errors and retry with backoff."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for i in range(5): # 5 retry attempts
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err_msg = str(e).lower()
                if '429' in err_msg or 'quota' in err_msg or 'rate limit' in err_msg:
                    wait_time = (i + 1) * 10 # 10, 20, 30, 40, 50 seconds
                    # Institutional Silence: Removed terminal quota alerts
                    time.sleep(wait_time)
                else:
                    raise e
        # Final safety attempt if loop finishes without 429
        return func(*args, **kwargs)
    return wrapper

# Color Palette (Institutional Aesthetic)
COLORS = {
    'INDIGO': gs_fmt.Color(0.1, 0.1, 0.3),    
    'ORANGE': gs_fmt.Color(0.8, 0.4, 0.1),    
    'PURPLE': gs_fmt.Color(0.3, 0.1, 0.4),    
    'GOLD':   gs_fmt.Color(0.7, 0.5, 0.1),    
    'SLATE':  gs_fmt.Color(0.2, 0.2, 0.25),   
    'WHITE':  gs_fmt.Color(1.0, 1.0, 1.0),
    'OFF_WHITE': gs_fmt.Color(0.96, 0.97, 0.98),
    'STRIPE': gs_fmt.Color(0.93, 0.94, 0.96)
}

# New coordinated layout with 'Vertical Spanning' for asymmetrical HUD density
BLOCK_CONFIGS = {
    'MASTER FINANCIALS': {'header_color': COLORS['INDIGO'], 'start_row': 1, 'start_col': 1, 'default_span': 1},
    'SEC':               {'header_color': COLORS['ORANGE'], 'start_row': 1, 'start_col': 4, 'default_span': 1},
    'EC':                {'header_color': COLORS['PURPLE'], 'start_row': 1, 'start_col': 7, 'default_span': 2},
    'THINKER':           {'header_color': COLORS['SLATE'],  'start_row': 'dynamic', 'start_col': 7, 'default_span': 3},
    'SENTIMENT':         {'header_color': COLORS['GOLD'],   'start_row': 'dynamic', 'start_col': 7, 'default_span': 1}
}

# Granular row spans for specific institutional-grade sections (Spacious Kinetic Layout)
CUSTOM_SPANS = {
    'Primary Risks': 4,
    'Growth Catalysts': 4,
    'Management Sentiment': 2,
    'SEC Health Verdict': 5,
    'Social Summary': 5,
    'Strategic Rationale': 6,
    'Full Reasoning Log': 10,
    'Diligence Objective': 4,
    'EC 1 Summary': 4,
    'EC 2 Summary': 4,
    'EC 3 Summary': 4,
    'EC 4 Summary': 4
}

class DiligenceSheetsUtils:
    def __init__(self, gc):
        self.gc = gc
        self.diligence_sheet_id = os.getenv("DILIGENCE_SHEET_ID")
        self._heartbeat_cache = {} # Ticker -> Last Heartbeat Timestamp
        
    @quota_safe
    def get_ticker_tab(self, ticker, apply_branding=False):
        sh = self.gc.open_by_key(self.diligence_sheet_id)
        try:
            ws = sh.worksheet(ticker)
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=ticker, rows="200", cols="20")
            if apply_branding:
                self._apply_global_formatting(ws)
        
        gid = str(ws.id)
        
        # Audit Heartbeat logic (Throttled to once per 60s per ticker)
        last_beat = self._heartbeat_cache.get(ticker, 0)
        now = time.time()
        if now - last_beat > 60:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ws.update_acell("P1", f"Audit Heartbeat: {now_str}")
            gs_fmt.format_cell_range(ws, "P1", gs_fmt.CellFormat(
                textFormat=gs_fmt.TextFormat(fontSize=8, italic=True, foregroundColor=gs_fmt.Color(0.5, 0.5, 0.5)),
                horizontalAlignment="RIGHT"
            ))
            self._heartbeat_cache[ticker] = now

        # Machine-readable signal for the Command Center UI
        sheet_id = self.diligence_sheet_id or os.getenv("DILIGENCE_SHEET_ID", "")
        print(f"::UI_SIGNAL:: {{\"type\": \"TAB_FOCUS\", \"ticker\": \"{ticker}\", \"sheet_id\": \"{sheet_id}\", \"gid\": \"{gid}\"}}")
        return ws, gid

    def _apply_global_formatting(self, ws):
        """Apply institutional branding once and for all."""
        try:
            # Create a single batched payload to bypass Rate Limits (14 API calls -> 1 API call per tab)
            sheet_id = int(ws.id)
            requests = []
            
            # --- 1. COLUMN WIDTHS ---
            col_widths = [160, 220, 30, 180, 350, 30, 210, 700, 30, 140, 300, 30]
            for i, width in enumerate(col_widths):
                requests.append({
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": i,
                            "endIndex": i + 1
                        },
                        "properties": {"pixelSize": width},
                        "fields": "pixelSize"
                    }
                })
                
            # --- 2. ROW HEIGHTS ---
            requests.append({
                "updateDimensionProperties": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": 0,
                        "endIndex": 200
                    },
                    "properties": {"pixelSize": 28},
                    "fields": "pixelSize"
                }
            })
            
            # --- 3. GLOBAL TEXT FORMATTING ---
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 200,
                        "startColumnIndex": 0,
                        "endColumnIndex": 26
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "fontFamily": "Lexend",
                                "fontSize": 10
                            },
                            "verticalAlignment": "TOP",
                            "wrapStrategy": "WRAP"
                        }
                    },
                    "fields": "userEnteredFormat(textFormat,verticalAlignment,wrapStrategy)"
                }
            })
            
            # Dispatch massive batch payload
            ws.spreadsheet.batch_update({"requests": requests})

            print(f"   ✨ Premium institutional branding applied.")
        except Exception:
            pass

    def clear_sheet(self, ws):
        """Wipe the sheet to ensure a fresh institutional dose of data."""
        try:
            # Clear all data but keep formatting (or mostly clear it)
            ws.clear()
            # Re-apply global formatting after clear
            self._apply_global_formatting(ws)
            print(f"   🧹 Sheet '{ws.title}' cleared for fresh analysis.")
        except Exception as e:
            if "429" not in str(e):
                print(f"   ⚠️ Could not clear sheet: {e}")

    def promote_tickers(self, tickers):
        """Move the specific tickers to the front of the Google Sheet."""
        try:
            sh = self.gc.open_by_key(self.diligence_sheet_id)
            all_worksheets = sh.worksheets()
            title_to_ws = {ws.title: ws for ws in all_worksheets}
            
            new_order = []
            # 1. Add requested tickers first
            for t in tickers:
                if t in title_to_ws:
                    new_order.append(title_to_ws[t])
            
            # 2. Add the rest
            remaining = [ws for ws in all_worksheets if ws.title not in tickers]
            new_order.extend(remaining)
            
            sh.reorder_worksheets(new_order)
            print(f"   📈 Promoted {len(tickers)} tickers to front of dossier.")
        except Exception as e:
            print(f"   ⚠️ Tab reordering failed: {e}")

    def clean_text(self, text):
        """Strip Markdown artifacts and noise for clean sheet presentation."""
        if not text: return ""
        t = str(text)
        t = t.replace("**", "") # Remove bold
        t = t.replace("###", "") # Remove H3
        t = t.replace("##", "") # Remove H2
        t = t.replace("#", "") # Remove H1
        t = re.sub(r'[_*~`>]', '', t) # Remove misc markdown
        return t.strip()

    def format_institutional_value(self, val):
        """Convert raw metrics into Bloomberg-grade human-readable strings."""
        if val is None or val == "N/A": return "N/A"
        try:
            # Handle list/bullets (don't format)
            if "\n•" in str(val) or str(val).startswith("•"): return val
            
            fval = float(str(val).replace(",", "").replace("$", "").replace("%", ""))
            
            # 1. Handle Percentages (if specifically flagged or small decimals)
            # (Context: Roe/Roic are already formatted as % strings in analyzer, but let's be safe)
            if "%" in str(val): return val
            
            # 2. Large Number Formatting ($B, $M)
            if abs(fval) >= 1_000_000_000:
                return f"${fval / 1_000_000_000:.2f}B"
            elif abs(fval) >= 1_000_000:
                return f"${fval / 1_000_000:.2f}M"
            elif 0 < abs(fval) < 100 and "." in str(val): # Small ratios/scores
                return f"{fval:.2f}"
            
            return str(val)
        except:
            return str(val)

    @quota_safe
    def write_block(self, ws, block_name, title, data_dict):
        config = BLOCK_CONFIGS.get(block_name.upper())
        if not config: return
        
        # Safety: Ensure we never try to write an invalid/empty range
        if not data_dict:
            data_dict = {"Data Pulse": "Awaiting Telemetry / No Data Found"}

        start_row = config['start_row']
        start_col = config['start_col']
        header_color = config['header_color']

        # Determine true start_row if dynamic to perfectly stack blocks vertically
        if start_row == "dynamic":
            try:
                try:
                    # Robust search for the exact block header to support overwriting (Zero-Dupe Protocol)
                    existing_cell = ws.find(title)
                    if existing_cell:
                        start_row = existing_cell.row
                    else:
                        raise Exception("Header not found")
                except:
                    # Find bottom while considering vertical merges
                    all_vals = ws.get_all_values()
                    last_row = 0
                    
                    # Robust scan for text content
                    for i, r_vals in enumerate(all_vals):
                        curr_row = i + 1
                        if len(r_vals) >= start_col:
                            # Check if the cell has text (key or value column)
                            if r_vals[start_col-1].strip() or (len(r_vals) >= start_col + 1 and r_vals[start_col].strip()):
                                last_row = max(last_row, curr_row)
                                
                    # Scan sheet formatting for merges that extend deeper than text (Physical footprint)
                    try:
                        sh = ws.spreadsheet
                        metadata = sh.fetch_sheet_metadata()
                        sheet_metadata = next(s for s in metadata['sheets'] if s['properties']['title'] == ws.title)
                        merges = sheet_metadata.get('merges', [])
                        
                        for m in merges:
                            # Check if merge overlaps with our target columns
                            m_start_col = m.get('startColumnIndex', 0)
                            m_end_col = m.get('endColumnIndex', 0)
                            if m_start_col <= (start_col - 1) and m_end_col >= (start_col):
                                last_row = max(last_row, m.get('endRowIndex', 0))
                    except: pass 
                            
                    start_row = last_row + 2 if last_row > 0 else 1
            except Exception as e:
                print(f"   ⚠️ Could not compute dynamic row: {e}")
                start_row = 1

        # LLM Fallback Interceptor (DISABLED FOR DEMO STABILITY)
        """
        has_na = any(is_na(v) for v in data_dict.values())
        if has_na:
            ... (LLM logic) ...
        """

        # 1. Prepare Batch Collections
        formats_to_apply = []
        merge_requests = []
        
        # Surgical Unmerge Protocol: Resolve existing merges to avoid API selection errors
        try:
            sh = ws.spreadsheet
            metadata = sh.fetch_sheet_metadata()
            sheet_metadata = next(s for s in metadata['sheets'] if s['properties']['title'] == ws.title)
            existing_merges = sheet_metadata.get('merges', [])
            
            # Target range for this specific block write
            total_rows = 1 + sum(CUSTOM_SPANS.get(k, config.get('default_span', 1)) for k in data_dict.keys())
            target_start_ri = start_row - 1
            target_end_ri = start_row + total_rows - 1
            target_start_ci = start_col - 1
            target_end_ci = start_col + 1
            
            for em in existing_merges:
                em_start_ri = em.get('startRowIndex', 0)
                em_end_ri = em.get('endRowIndex', 0)
                em_start_ci = em.get('startColumnIndex', 0)
                em_end_ci = em.get('endColumnIndex', 0)
                
                # Check for physical overlap with our target cluster
                overlap_v = not (em_end_ri <= target_start_ri or em_start_ri >= target_end_ri)
                overlap_h = not (em_end_ci <= target_start_ci or em_start_ci >= target_end_ci)
                
                if overlap_v and overlap_h:
                    # Dissolve THIS EXACT merge to satisfy Google API selectivity precision
                    merge_requests.append({"unmergeCells": {"range": em}})
        except Exception as e:
            print(f"   ⚠️ Surgical unmerge lookup failed: {e}")
            # Fallback (though risky if merges exist)
            pass
        
        # Header Data & Merge Request
        ws.update_acell(gspread.utils.rowcol_to_a1(start_row, start_col), title)
        merge_requests.append({
            "mergeCells": {
                "range": {
                    "sheetId": int(ws.id),
                    "startRowIndex": start_row - 1,
                    "endRowIndex": start_row,
                    "startColumnIndex": start_col - 1,
                    "endColumnIndex": start_col + 1
                },
                "mergeType": "MERGE_ALL"
            }
        })
        
        # Header Format
        header_range_a1 = gspread.utils.rowcol_to_a1(start_row, start_col) + ":" + \
                          gspread.utils.rowcol_to_a1(start_row, start_col + 1)
        formats_to_apply.append((header_range_a1, gs_fmt.CellFormat(
            backgroundColor=header_color,
            textFormat=gs_fmt.TextFormat(foregroundColor=COLORS['WHITE'], bold=True),
            horizontalAlignment="CENTER",
            verticalAlignment="MIDDLE"
        )))

        # 2. Structure the Physical Matrix and Merge Requests
        current_phys_row = start_row + 1
        default_span = config.get('default_span', 1)
        
        # Prepare a matrix for the entire block text
        # (This avoids calling update_cell in a loop)
        matrix_rows = []
        
        for idx, (k, v) in enumerate(data_dict.items()):
            span = CUSTOM_SPANS.get(k, default_span)
            
            # Add text row (top of the merge) and empty filler rows
            clean_val = self.clean_text(self.format_institutional_value(v))
            matrix_rows.append([k, clean_val])
            for _ in range(span - 1):
                matrix_rows.append(["", ""]) # Empty filler rows physically covered by the merge
                
            # Ranges for Formatting & Merging
            r_start = current_phys_row - 1
            r_end = current_phys_row + span - 1
            
            k_range_a1 = gspread.utils.rowcol_to_a1(current_phys_row, start_col) + ":" + \
                         gspread.utils.rowcol_to_a1(r_end, start_col)
            v_range_a1 = gspread.utils.rowcol_to_a1(current_phys_row, start_col + 1) + ":" + \
                         gspread.utils.rowcol_to_a1(r_end, start_col + 1)
            full_span_a1 = gspread.utils.rowcol_to_a1(current_phys_row, start_col) + ":" + \
                           gspread.utils.rowcol_to_a1(r_end, start_col + 1)

            if span > 1:
                # Key Merge
                merge_requests.append({"mergeCells": {"range": {
                    "sheetId": int(ws.id), "startRowIndex": r_start, "endRowIndex": r_end,
                    "startColumnIndex": start_col - 1, "endColumnIndex": start_col
                }, "mergeType": "MERGE_ALL"}})
                # Value Merge
                merge_requests.append({"mergeCells": {"range": {
                    "sheetId": int(ws.id), "startRowIndex": r_start, "endRowIndex": r_end,
                    "startColumnIndex": start_col, "endColumnIndex": start_col + 1
                }, "mergeType": "MERGE_ALL"}})

            # Styles for this entry
            formats_to_apply.append((k_range_a1, gs_fmt.CellFormat(
                textFormat=gs_fmt.TextFormat(bold=True), backgroundColor=COLORS['OFF_WHITE'], verticalAlignment="TOP"
            )))
            formats_to_apply.append((v_range_a1, gs_fmt.CellFormat(verticalAlignment="TOP", wrapStrategy="WRAP")))

            if idx % 2 == 1:
                formats_to_apply.append((full_span_a1, gs_fmt.CellFormat(backgroundColor=COLORS['STRIPE'])))
                
            current_phys_row += span

        # 3. DISPATCH ALL BATCHES
        # A. Physical Text Matrix (Single Call)
        matrix_range = gspread.utils.rowcol_to_a1(start_row + 1, start_col) + ":" + \
                       gspread.utils.rowcol_to_a1(start_row + len(matrix_rows), start_col + 1)
        ws.update(matrix_range, matrix_rows)
        
        # B. All Merges/Unmerges (Single Call)
        ws.spreadsheet.batch_update({"requests": merge_requests})
        
        # C. All Formats (Single Call)
        gs_fmt.format_cell_ranges(ws, formats_to_apply)
        
        print(f"   ✅ Block '{title}' written [BATCH_MODE].")

    def update_cell_kinetic(self, ws, block_name, key, text_chunk, finalize=False):
        """
        Dynamically updates a specific cell within a block to simulate live typing.
        Used primarily for the 'Thinker' synthesis to show AI reasoning emerging.
        """
        try:
            config = BLOCK_CONFIGS.get(block_name.upper())
            if not config: return
            
            start_row = config['start_row']
            start_col = config['start_col']
            
            # 1. Find the row for this key within the block
            # In our high-density layout, blocks start at start_row and go down.
            # Header is start_row. Data starts at start_row + 1.
            # We need to find the specific row index for the 'key'.
            # Optimization: since blocks are small, we can just search the column.
            cells = ws.col_values(start_col)
            row_idx = -1
            for i, val in enumerate(cells):
                if val == key:
                    row_idx = i + 1
                    break
            
            if row_idx == -1:
                return # Key not found, couldn't stream
                
            # 2. Update the value cell (start_col + 1)
            # Add a subtle blinking cursor or ellipsis while finalizing? 
            val_cell = gspread.utils.rowcol_to_a1(row_idx, start_col + 1)
            display_text = self.clean_text(text_chunk)
            if not finalize:
                display_text += "... [ANALYZING]"
            
            ws.update_acell(val_cell, display_text)
            
            # If finalizing, ensure wrapping and clean formatting
            if finalize:
                gs_fmt.format_cell_range(ws, val_cell, gs_fmt.CellFormat(
                    wrapStrategy="WRAP",
                    verticalAlignment="TOP"
                ))
        except:
            pass # Silent fail to prevent breaking the orchestrator

    def reorder_tabs(self, tickers):
        """
        Force-moves the specified tickers to the front of the spreadsheet (indices 0, 1, 2, 3...).
        Creates a high-focus 'Conviction HUD' for the demo.
        """
        try:
            sh = self.gc.open_by_key(self.diligence_sheet_id)
            all_ws = sh.worksheets()
            
            # Map of ticker to worksheet object
            ws_map = {ws.title: ws for ws in all_ws}
            
            # 1. Identify the 'Target' worksheets
            target_ws = []
            for t in tickers:
                if str(t).upper() in ws_map:
                    target_ws.append(ws_map[str(t).upper()])
            
            # 2. Identify the 'Remainder' and separate 'SheetX' tabs
            remainder_ws = []
            junk_ws = []
            for ws in all_ws:
                if ws in target_ws:
                    continue
                if re.match(r'^Sheet\d+$', ws.title) or ws.title == "Sheet1":
                    junk_ws.append(ws)
                else:
                    remainder_ws.append(ws)
            
            # 3. Concatenate: Targets first, then normal tabs, then junk (Sheet6, etc.) at absolute end
            new_order = target_ws + remainder_ws + junk_ws
            
            # 4. Apply reorder [BATCH_MODE]
            sh.reorder_worksheets(new_order)
            # sh.reorder_worksheets(new_order) # Keep logic but silence the debug print
            sh.reorder_worksheets(new_order)
        except Exception:
            pass

    def sanitize_workspace(self):
        """
        No longer deletes SheetX tabs — just a placeholder for any other workspace cleanup.
        Tab reordering now handles moving Sheet6 to the end.
        """
        pass
