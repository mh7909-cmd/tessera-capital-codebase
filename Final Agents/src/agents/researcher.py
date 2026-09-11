import json
from src.graph.state import AgentState
from src.tools.gdrive_engine import (
    get_research_context, 
    get_latest_report_content,
    get_company_data_from_latest_tab,
    get_company_data_from_matching_tab,
    get_company_data_from_tab_gid
)
from src.utils.progress import progress

# Approved Data Sources (User-specified)
SENTIMENT_SHEET_ID = "1HN7Fm3zoK6EsuGmzaLd4Hrj_fKJYMbZsCrmMJcrjRr8"
SENTIMENT_TAB_GID = 643967464  # Exact tab: gid=643967464
REPORT_FOLDER_ID = "1kE4OmpQOGTheULpGOY2ZD4YE62hVH6jj"

def research_agent(state: AgentState):
    """
    Fetches research context from specific Google Sheets and Drive folders.
    Uses ticker and company name to search for relevant rows.
    """
    ticker = state["data"]["tickers"][0] if state["data"].get("tickers") else None
    company_name = state.get("metadata", {}).get("company_name", "")
    
    if not ticker:
        progress.update_status("research_agent", None, "Skipping: No ticker provided.")
        state["data"]["research_context"] = "No ticker provided for research."
        return state

    progress.update_status("research_agent", ticker, "Fetching institutional research context")

    research_pieces = []

    # Pre-seeded context (Google Sheets dossier + expert transcript from miro_bridge)
    # injected via --context-file flag — prepend so agents see it first
    pre_seeded = state["data"].get("pre_seeded_context", "")
    if pre_seeded:
        research_pieces.append(f"--- PRE-LOADED INSTITUTIONAL DOSSIER (GSheets + Expert Transcript) ---\n{pre_seeded}")
        progress.update_status("research_agent", ticker, "Pre-seeded dossier loaded. Fetching additional signals...")

    try:
        # 1. Master EC Sheet — DISABLED for YC Demo
        # Only the 3 approved sources are used: Sentiment GSheet, expert dossier, GDrive report.
        pass

        # 2. Fetch from exact Diligence Sheet tab (GID: 643967464)
        # URL: https://docs.google.com/spreadsheets/d/1HN7Fm3.../edit?gid=643967464
        progress.update_status("research_agent", ticker, "Fetching Diligence Sheet (FLY tab)...")
        diligence_rows = get_company_data_from_tab_gid(SENTIMENT_SHEET_ID, SENTIMENT_TAB_GID)
        if diligence_rows:
            formatted_diligence = "\n".join([json.dumps(row, indent=2) for row in diligence_rows])
            research_pieces.append(f"--- INSTITUTIONAL DILIGENCE SHEET (FLY) ---\n{formatted_diligence}")

        # 3. Email + Call Thread Sheet — DISABLED for YC Demo
        # Expert call intelligence is pre-seeded via the dossier (--context-file flag).
        pass

        # 4. Fetch Latest Report from Folder
        progress.update_status("research_agent", ticker, "Fetching latest institutional report")
        latest_report = get_latest_report_content(REPORT_FOLDER_ID)
        if latest_report:
            research_pieces.append(latest_report)
            
        # Combine everything
        if research_pieces:
            state["data"]["research_context"] = "\n\n".join(research_pieces)
            progress.update_status("research_agent", ticker, "Research context loaded successfully.")
        else:
            state["data"]["research_context"] = "No matching institutional research found."
            progress.update_status("research_agent", ticker, "No matching research metadata found.")
            
    except Exception as e:
        progress.update_status("research_agent", ticker, f"Error fetching research: {str(e)}")
        state["data"]["research_context"] = f"Error loading institutional research: {str(e)}"

    return state
