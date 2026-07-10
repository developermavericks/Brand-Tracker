import feedparser
import requests
import urllib.parse
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from database import get_all_companies, add_article, update_company_status, init_db
import logging
from concurrent.futures import ThreadPoolExecutor
from googlenewsdecoder import gnewsdecoder
import time

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for Global and India regions
BASE_RSS_URL = "https://news.google.com/rss/search?q={query}+when:1d{suffix}"

def is_within_24_hours(published_at: str) -> bool:
    if published_at == 'Unknown Date':
        return False
    try:
        pub_dt = parsedate_to_datetime(published_at)
        now = datetime.now(timezone.utc)
        return (now - pub_dt) <= timedelta(hours=24)
    except Exception:
        return False

def fetch_rss_for_company(company_name: str, company_id: int, region: str = 'Global', sync_time=None):
    regions_to_fetch = []
    if region == 'Both':
        regions_to_fetch = ['Global', 'India']
    else:
        regions_to_fetch = [region]
        
    all_new_articles = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    }

    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    def process_entry(entry):
        title = getattr(entry, 'title', 'No Title')
        link = getattr(entry, 'link', '')
        published_at = getattr(entry, 'published', 'Unknown Date')
        source = getattr(entry, 'source', {}).get('title', 'Google News')
        
        # 1. Resolve redirect if it's a Google News link to get the original URL
        final_url = link
        if link and "news.google.com" in link:
            try:
                decoded = gnewsdecoder(link)
                if decoded.get("status"):
                    final_url = decoded["decoded_url"]
                    logger.debug(f"Decoded Google News URL → {final_url}")
                else:
                    logger.warning(f"gnewsdecoder failed: {decoded.get('message')}")
            except Exception as e:
                logger.error(f"Error using gnewsdecoder: {e}")
        
        # 2. Add to Google Sheets database (no summary/sentiment/extraction_method columns needed)
        if final_url:
            is_new = add_article(
                company_id=company_id,
                title=title,
                link=final_url,
                published_at=published_at,
                source=source
            )
            if is_new:
                logger.info(f"New article found & saved: {title}")
                return {
                    'title': title, 
                    'link': final_url, 
                    'published_at': published_at,
                    'source': source, 
                    'company_name': company_name
                }
        return None

    for r in regions_to_fetch:
        encoded_query = urllib.parse.quote(company_name)
        suffix = "&gl=IN&ceid=IN:en" if r == 'India' else ""
        rss_url = BASE_RSS_URL.format(query=encoded_query, suffix=suffix)
        
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            entries_to_process = [e for e in feed.entries if is_within_24_hours(getattr(e, 'published', 'Unknown Date'))]
            
            # Process in parallel
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(process_entry, entries_to_process))
                
            for art in results:
                if art:
                    all_new_articles.append(art)

        except Exception as e:
            print(f"Error fetching {r} RSS for {company_name}: {e}")

    session.close()

    ref_time = sync_time if sync_time else datetime.now(timezone.utc)
    ist_now = ref_time + timedelta(hours=5, minutes=30)
    now_str = ist_now.strftime("%H:%M:%S")
    status_msg = f"[{now_str}] Checked {region}: "
    if all_new_articles:
        status_msg += f"Found {len(all_new_articles)} new items"
    else:
        status_msg += "No new items found"
    
    update_company_status(company_id, status_msg)
    return all_new_articles

def fetch_all_companies():
    companies = get_all_companies()
    all_new_articles = []
    
    session_start_utc = datetime.now(timezone.utc)
    from database import set_last_fetch_time
    set_last_fetch_time(session_start_utc.isoformat())

    def fetch_comp(comp):
        return fetch_rss_for_company(comp['name'], comp['id'], comp.get('region', 'Global'), sync_time=session_start_utc)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(fetch_comp, companies))
        
    for res in results:
        all_new_articles.extend(res)
        
    return all_new_articles

if __name__ == "__main__":
    init_db()
    
    comp_added = add_company("Boston Consulting Group")
    new_docs = fetch_all_companies()
    print(f"Fetched {len(new_docs)} new articles.")
