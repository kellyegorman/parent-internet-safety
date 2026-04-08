"""
The full pipeline:
  DB (searches table, flagged=FALSE)
    -> profanity check
    -> ML offensive/hate check
    -> LDA topic extraction
    -> DB (alerts table) + mark search as flagged
 
runnign instructions:
  # One-time setup (creates tables + seeds categories):
  python flagging_pipeline.py --setup
 
  # Process any unprocessed searches once:
  python flagging_pipeline.py
 
  # Run continuously, checking every 30 seconds:
  python flagging_pipeline.py --loop --interval 30
 
requirements:
  pip install sqlalchemy pymysql python-dotenv better-profanity \
              requests beautifulsoup4
  (offensive_flag.py also needs keras, tensorflow, nltk, joblib)
"""
 
import os
import uuid
import time
import logging
import argparse
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
 
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
 
# database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:ZNrabNeFJKmDjnbNgxoMJPjMiStFQcwH@trolley.proxy.rlwy.net:44931/railway"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
 
# alert categories
CAT_PROFANITY = "CAT_PROFANITY"
CAT_OFFENSIVE = "CAT_OFFENSIVE"
CAT_TOPICS    = "CAT_TOPICS"
 
 
# database setup (run w/ --setup)
 
def setup_database():
    #create missing tables and seed alert categories. safe to run multiple times.
    log.info("Running database setup…")
    with engine.begin() as conn:
 
        # searches table (was missing from original schema)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS searches (
                searchid    VARCHAR(15)   NOT NULL,
                deviceid    VARCHAR(15)   NOT NULL,
                query_text  TEXT,
                url         VARCHAR(2048),
                searched_at TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                flagged     BOOLEAN       NOT NULL DEFAULT FALSE,
                PRIMARY KEY (searchid),
                FOREIGN KEY (deviceid) REFERENCES devices(deviceid)
            )
        """))
 
        # alert_category
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_category (
                categoryid           VARCHAR(15) NOT NULL,
                category_name        VARCHAR(50) NOT NULL,
                category_description TEXT,
                PRIMARY KEY (categoryid),
                UNIQUE (category_name)
            )
        """))
 
        # alerts
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                alertid     VARCHAR(15)  NOT NULL,
                deviceid    VARCHAR(15)  NOT NULL,
                categoryid  VARCHAR(15)  NOT NULL,
                severity    VARCHAR(10)  NOT NULL,
                domain      VARCHAR(255),
                reason_code VARCHAR(100),
                created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (alertid),
                FOREIGN KEY (deviceid)   REFERENCES devices(deviceid),
                FOREIGN KEY (categoryid) REFERENCES alert_category(categoryid)
            )
        """))
 
        # Seed categories
        for cid, name, desc in [
            (CAT_PROFANITY, "Profanity", "Page contains profane language"),
            (CAT_OFFENSIVE, "Offensive", "Page flagged by ML offensive/hate model"),
            (CAT_TOPICS,    "Topics",    "Top topics extracted from the page via LDA"),
        ]:
            conn.execute(text("""
                INSERT IGNORE INTO alert_category (categoryid, category_name, category_description)
                VALUES (:id, :name, :desc)
            """), {"id": cid, "name": name, "desc": desc})
 
    log.info("Database setup complete.")
 
 
# Read unprocessed searches from DB 
def get_unflagged_searches(limit: int = 50) -> list:
    """Return rows from searches where flagged=FALSE and url is not null."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT searchid, deviceid, url, query_text
            FROM searches
            WHERE flagged = FALSE
              AND url IS NOT NULL
              AND url != ''
            ORDER BY searched_at ASC
            LIMIT :lim
        """), {"lim": limit}).fetchall()
    return rows
 
 
# run flagging checks 
def run_profanity_check(url: str) -> bool:
    
    # if page has profanity -> true else -> false
    try:
        from better_profanity import profanity as prof
        import requests
        from bs4 import BeautifulSoup
 
        prof.load_censor_words()
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        text_content = BeautifulSoup(res.content, "html.parser").get_text(" ", strip=True)
        return prof.contains_profanity(text_content)
    except Exception as e:
        log.warning(f"  [profanity] Error checking {url}: {e}")
        return False
 
 
def run_offensive_check(url: str) -> str:
    """
    Returns:
      'FLAGGED'            – over 40% of text chunks are hate/offensive
      'CLEAN'              – below threshold
      'INSUFFICIENT_DATA'  – page too short to judge
      'ERROR'              – could not load model or page
    """
    try:
        # Import here so the pipeline still works even if keras isn't installed
        from content_flagging.offensive_flag import predict_offensive_from_url
        result = predict_offensive_from_url(url)
        return result or "ERROR"
    except ImportError:
        log.warning("  [offensive] keras/tensorflow not installed — skipping ML check")
        return "ERROR"
    except Exception as e:
        log.warning(f"  [offensive] Error: {e}")
        return "ERROR"
 
 
def run_topic_extraction(url: str) -> list[str]:
    """Returns a list of up to 3 topic words, or [] on error."""
    try:
        from content_flagging.url_summaries import top_3_topics_from_url
        topics = top_3_topics_from_url(url)
        return topics or []
    except ImportError:
        log.warning("  [topics] gensim/nltk not installed — skipping topic extraction")
        return []
    except Exception as e:
        log.warning(f"  [topics] Error: {e}")
        return []
 
 
# send results back to db 
def write_alert(deviceid: str, categoryid: str, severity: str,
                domain: str, reason_code: str):
    alertid = "A" + uuid.uuid4().hex[:14]
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO alerts (alertid, deviceid, categoryid, severity, domain, reason_code)
            VALUES (:aid, :did, :cid, :sev, :dom, :rc)
        """), {
            "aid": alertid, "did": deviceid,
            "cid": categoryid, "sev": severity,
            "dom": domain[:255] if domain else None,
            "rc":  reason_code[:100] if reason_code else None,
        })
    log.info(f"    → Alert {alertid}: [{severity.upper()}] {categoryid} — {reason_code}")
 
 
def mark_search_flagged(searchid: str):
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE searches SET flagged = TRUE WHERE searchid = :sid"),
            {"sid": searchid}
        )
 
 
def extract_domain(url: str) -> str:
    try:
        return url.split("//")[-1].split("/")[0]
    except Exception:
        return url[:255]
 
 
# Process a single search row (Steps 1,2,3 for 1 URL) 
def process_search(searchid: str, deviceid: str, url: str, query_text: str):
    log.info(f"Processing [{searchid}] {url}")
    domain = extract_domain(url)
    alerts_written = 0
 
    #  Profanity 
    has_profanity = run_profanity_check(url)
    log.info(f"  Profanity: {'YES' if has_profanity else 'no'}")
    if has_profanity:
        write_alert(deviceid, CAT_PROFANITY, "watch", domain, "PROFANITY_DETECTED")
        alerts_written += 1
 
    #  Offensive  ML 
    offensive_result = run_offensive_check(url)
    log.info(f"  Offensive: {offensive_result}")
    if offensive_result == "FLAGGED":
        write_alert(deviceid, CAT_OFFENSIVE, "moderate", domain, "OFFENSIVE_CONTENT")
        alerts_written += 1
 
    #  Topic 
    topics = run_topic_extraction(url)
    log.info(f"  Topics: {topics}")
    if topics:
        reason = "TOPICS:" + "|".join(topics[:3])
        write_alert(deviceid, CAT_TOPICS, "watch", domain, reason)
        alerts_written += 1
 
    # Mark as processed so  don't re-check it next time
    mark_search_flagged(searchid)
    log.info(f"  ✓ Done — {alerts_written} alert(s) written\n")
 
 
# MAIN — run once or in a loop 
def run_once():
    rows = get_unflagged_searches()
    if not rows:
        log.info("No unprocessed searches found.")
        return 0
    log.info(f"Found {len(rows)} search(es) to process.")
    for row in rows:
        try:
            process_search(row[0], row[1], row[2], row[3] or "")
        except Exception as e:
            log.error(f"Unhandled error for {row[0]}: {e}")
    return len(rows)
 
 
def run_loop(interval: int):
    log.info(f"Loop mode: checking every {interval}s. Ctrl-C to stop.")
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Loop error: {e}")
        time.sleep(interval)
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Content flagging pipeline")
    parser.add_argument("--setup",    action="store_true", help="Create tables and seed categories, then exit")
    parser.add_argument("--loop",     action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between loop runs (default: 30)")
    args = parser.parse_args()
 
    if args.setup:
        setup_database()
    elif args.loop:
        run_loop(args.interval)
    else:
        run_once()
 