import os
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

# Global variables for gspread connection
_client = None
_spreadsheet = None

def get_gsheet():
    global _client, _spreadsheet
    if _spreadsheet is not None:
        return _spreadsheet
        
    creds_json_str = os.getenv("GOOGLE_CREDS_JSON")
    creds_file = "google_creds.json"
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        if creds_json_str:
            creds_info = json.loads(creds_json_str)
            creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
        elif os.path.exists(creds_file):
            creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
        else:
            raise FileNotFoundError("Google credentials not found. Please provide 'google_creds.json' or set GOOGLE_CREDS_JSON env var.")
            
        _client = gspread.authorize(creds)
        
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Brand Tracker DB")
        if sheet_name.startswith("https://") or "docs.google.com/spreadsheets" in sheet_name:
            _spreadsheet = _client.open_by_url(sheet_name)
        else:
            _spreadsheet = _client.open(sheet_name)
            
        return _spreadsheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        raise e

def init_db():
    sh = get_gsheet()
    
    # 1. Verify/Create 'Companies' worksheet
    try:
        sh.worksheet("Companies")
    except gspread.exceptions.WorksheetNotFound:
        sh.add_worksheet(title="Companies", rows="100", cols="4")
        w = sh.worksheet("Companies")
        w.append_row(["id", "name", "region", "last_status"])
        
    # 2. Verify/Create 'Articles' worksheet (Only 4 core columns now)
    try:
        sh.worksheet("Articles")
    except gspread.exceptions.WorksheetNotFound:
        sh.add_worksheet(title="Articles", rows="2000", cols="4")
        w = sh.worksheet("Articles")
        w.append_row(["title", "link", "published_at", "source"])
        
    # 3. Verify/Create 'Status' worksheet
    try:
        sh.worksheet("Status")
    except gspread.exceptions.WorksheetNotFound:
        sh.add_worksheet(title="Status", rows="10", cols="2")
        w = sh.worksheet("Status")
        w.append_row(["key", "value"])

    print("Google Sheets database initialized successfully.")

def get_all_companies():
    try:
        sh = get_gsheet()
        w = sh.worksheet("Companies")
        rows = w.get_all_values()
        if len(rows) <= 1:
            return []
        
        companies = []
        for row in rows[1:]:
            if len(row) >= 3:
                comp_id = int(row[0]) if row[0].isdigit() else 0
                comp_name = row[1]
                region = row[2]
                last_status = row[3] if len(row) > 3 else "Pending first fetch"
                companies.append({
                    "id": comp_id,
                    "name": comp_name,
                    "region": region,
                    "last_status": last_status
                })
        return sorted(companies, key=lambda x: x["name"])
    except Exception as e:
        print(f"Error fetching companies: {e}")
        return []

def add_company(name: str, region: str = 'Global'):
    try:
        sh = get_gsheet()
        w = sh.worksheet("Companies")
        rows = w.get_all_values()
        
        for row in rows[1:]:
            if len(row) > 1 and row[1].strip().lower() == name.strip().lower():
                return False
                
        max_id = 0
        for row in rows[1:]:
            if row[0].isdigit():
                max_id = max(max_id, int(row[0]))
        new_id = max_id + 1
        
        w.append_row([new_id, name.strip(), region, "Pending first fetch"])
        return True
    except Exception as e:
        print(f"Error adding company: {e}")
        return False

def remove_company(name: str):
    try:
        sh = get_gsheet()
        w_comp = sh.worksheet("Companies")
        rows_comp = w_comp.get_all_values()
        
        row_idx_to_delete = -1
        for idx, row in enumerate(rows_comp):
            if idx > 0 and len(row) > 1 and row[1].strip().lower() == name.strip().lower():
                row_idx_to_delete = idx + 1
                break
                
        if row_idx_to_delete != -1:
            w_comp.delete_rows(row_idx_to_delete)
            
        # Note: Articles are stored globally now without company_name,
        # so we don't delete them from the Articles sheet to preserve history.
        return True
    except Exception as e:
        print(f"Error removing company: {e}")
        return False

def update_company_status(company_id: int, status: str):
    try:
        sh = get_gsheet()
        w = sh.worksheet("Companies")
        rows = w.get_all_values()
        
        for idx, row in enumerate(rows):
            if idx > 0 and row[0].isdigit() and int(row[0]) == company_id:
                w.update_cell(idx + 1, 4, status)
                break
    except Exception as e:
        print(f"Error updating company status: {e}")

def add_article(company_id: int, title: str, link: str, published_at: str, source: str, summary: str = None, sentiment: str = None, extraction_method: str = 'summary'):
    try:
        sh = get_gsheet()
        w_art = sh.worksheet("Articles")
        rows = w_art.get_all_values()
        
        # Check for duplicate links globally (Column 2 is link)
        for row in rows[1:]:
            if len(row) > 1 and row[1].strip() == link.strip():
                return False
                
        w_art.append_row([
            title,
            link,
            published_at,
            source
        ])
        return True
    except Exception as e:
        print(f"Error adding article: {e}")
        return False

def get_recent_articles(limit=50):
    try:
        sh = get_gsheet()
        w = sh.worksheet("Articles")
        rows = w.get_all_values()
        if len(rows) <= 1:
            return []
            
        articles = []
        for row in reversed(rows[1:]):
            if len(row) < 4:
                row = row + [""] * (4 - len(row))
            
            articles.append({
                "title": row[0],
                "link": row[1],
                "published_at": row[2],
                "source": row[3],
                "company_name": "Event Feed" # Unified fallback name
            })
            if len(articles) >= limit:
                break
        return articles
    except Exception as e:
        print(f"Error getting recent articles: {e}")
        return []

def get_articles_for_brand(company_name):
    # Since we store all articles together now, we return all articles
    try:
        sh = get_gsheet()
        w = sh.worksheet("Articles")
        rows = w.get_all_values()
        if len(rows) <= 1:
            return []
            
        articles = []
        for row in reversed(rows[1:]):
            if len(row) < 4:
                row = row + [""] * (4 - len(row))
                
            articles.append({
                "title": row[0],
                "link": row[1],
                "published_at": row[2],
                "source": row[3],
                "company_name": "Event Feed"
            })
        return articles
    except Exception as e:
        print(f"Error getting articles: {e}")
        return []

def set_last_fetch_time(timestamp_iso: str):
    try:
        sh = get_gsheet()
        w = sh.worksheet("Status")
        rows = w.get_all_values()
        
        found = False
        for idx, row in enumerate(rows):
            if idx > 0 and len(row) > 0 and row[0] == "last_fetch_time":
                w.update_cell(idx + 1, 2, timestamp_iso)
                found = True
                break
                
        if not found:
            w.append_row(["last_fetch_time", timestamp_iso])
    except Exception as e:
        print(f"Error setting last fetch time: {e}")

def get_last_fetch_time():
    try:
        sh = get_gsheet()
        w = sh.worksheet("Status")
        rows = w.get_all_values()
        
        for row in rows[1:]:
            if len(row) > 1 and row[0] == "last_fetch_time":
                return row[1]
        return None
    except Exception as e:
        print(f"Error getting last fetch time: {e}")
        return None

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
