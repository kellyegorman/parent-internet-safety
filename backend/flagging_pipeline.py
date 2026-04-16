
# step by step...
#   DB (searches table, flagged=FALSE)
#     -> profanity check
#     -> ML offensive/hate check
#     -> LDA topic extraction
#     -> DB (alerts table) + mark search as flagged
 
# running:
#   # one-time setup (creates tables + categories):
#   python flagging_pipeline.py --setup
 
#   # process any unprocessed searches once:
#   python flagging_pipeline.py

#   # run on loop every 30 seconds:
#   python flagging_pipeline.py --loop --interval 30
 
import os
import re
import uuid
import time
import logging
import argparse
from collections import Counter
from urllib.parse import urlparse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:ZNrabNeFJKmDjnbNgxoMJPjMiStFQcwH@trolley.proxy.rlwy.net:44931/railway"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

CAT_PROFANITY = "CAT_PROFANITY"
CAT_OFFENSIVE = "CAT_OFFENSIVE"
CAT_TOPICS = "CAT_TOPICS"


def setup_database():
    log.info("Running database setup…")
    with engine.begin() as conn:
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

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_category (
                categoryid           VARCHAR(15) NOT NULL,
                category_name        VARCHAR(50) NOT NULL,
                category_description TEXT,
                PRIMARY KEY (categoryid),
                UNIQUE (category_name)
            )
        """))

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

        for cid, name, desc in [
            (CAT_PROFANITY, "Profanity", "Page contains profane language"),
            (CAT_OFFENSIVE, "Offensive", "Page flagged by ML offensive/hate model"),
            (CAT_TOPICS, "Topics", "Top topics extracted from the page via LDA"),
        ]:
            conn.execute(text("""
                INSERT IGNORE INTO alert_category (categoryid, category_name, category_description)
                VALUES (:id, :name, :desc)
            """), {"id": cid, "name": name, "desc": desc})

    log.info("Database setup complete.")


def get_unflagged_searches(limit: int = 50) -> list:
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


def fetch_page_text(url: str) -> str:
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.content, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
        tag.decompose()
    text_content = soup.get_text(" ", strip=True)
    text_content = re.sub(r"\s+", " ", text_content)
    return text_content.strip()


def tokenize(text_content: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text_content.lower())


def profanity_stats(text_content: str) -> dict:
    try:
        from better_profanity import profanity as prof

        prof.load_censor_words()
        words = tokenize(text_content)
        if not words:
            return {"hits": 0, "ratio": 0.0}
        hits = sum(1 for word in words if prof.contains_profanity(word))
        return {"hits": hits, "ratio": hits / len(words)}
    except Exception as e:
        log.warning(f"  [profanity] Error: {e}")
        return {"hits": 0, "ratio": 0.0}


def run_profanity_check(url: str) -> bool:
    try:
        text_content = fetch_page_text(url)
        stats = profanity_stats(text_content)
        log.info(f"  [profanity] hits={stats['hits']} ratio={stats['ratio']:.4f}")
        return stats["hits"] >= 2 or stats["ratio"] >= 0.003
    except Exception as e:
        log.warning(f"  [profanity] Error checking {url}: {e}")
        return False


def run_offensive_check(url: str) -> str:
    try:
        text_content = fetch_page_text(url)
        words = text_content.split()
        if len(words) < 25:
            return "clean"

        prof = profanity_stats(text_content)
        profanity_hits = prof["hits"]
        profanity_ratio = prof["ratio"]

        predictor = None
        try:
            from content_flagging.offensive_flag import predict_offensive as predictor
        except Exception:
            try:
                from content_flagging.offensive_flag import predict_offensive_from_url
                result = predict_offensive_from_url(url)
                if result in {"severe", "moderate", "watch", "clean"}:
                    if result == "watch" and profanity_hits >= 6:
                        return "moderate"
                    return result
            except Exception:
                predictor = None

        ml_weight = 0.0
        hate_weight = 0.0
        offensive_weight = 0.0
        watch_weight = 0.0

        if predictor is not None:
            chunk_size = 80
            chunks = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
            labels = []
            for chunk in chunks:
                try:
                    label = predictor(chunk)
                except TypeError:
                    label = predictor(text=chunk)
                label = str(label).strip().upper()
                labels.append(label)

            counts = Counter(labels)
            total = max(len(labels), 1)
            hate_weight = counts.get("HATE_SPEECH", 0) / total
            offensive_weight = counts.get("OFFENSIVE", 0) / total
            watch_weight = (
                counts.get("WATCH", 0)
                + counts.get("TOXIC", 0)
                + counts.get("INSULT", 0)
                + counts.get("ABUSIVE", 0)
            ) / total
            ml_weight = min(1.0, hate_weight * 1.0 + offensive_weight * 0.65 + watch_weight * 0.35)
            log.info(
                f"  [offensive] ml={ml_weight:.3f} hate={hate_weight:.3f} off={offensive_weight:.3f} watch={watch_weight:.3f} profanity_hits={profanity_hits} profanity_ratio={profanity_ratio:.4f}"
            )
        else:
            log.info(
                f"  [offensive] ml unavailable profanity_hits={profanity_hits} profanity_ratio={profanity_ratio:.4f}"
            )

        combined = max(
            ml_weight,
            min(1.0, profanity_ratio * 25),
            0.45 if profanity_hits >= 8 else 0.0,
            0.25 if profanity_hits >= 4 else 0.0,
            0.12 if profanity_hits >= 2 else 0.0,
        )

        if hate_weight >= 0.18 or ml_weight >= 0.42 or profanity_ratio >= 0.03 or profanity_hits >= 12:
            return "severe"
        if hate_weight >= 0.05 or ml_weight >= 0.18 or profanity_ratio >= 0.008 or profanity_hits >= 4:
            return "moderate"
        if combined >= 0.08:
            return "watch"
        return "clean"
    except ImportError:
        return "clean"
    except Exception as e:
        log.warning(f"  [offensive] Error: {e}")
        return "clean"


def run_topic_extraction(url: str) -> list[str]:
    try:
        try:
            from content_summaries.url_summaries import top_3_topics_from_url
        except Exception:
            from content_summaries.url_summaries import top_3_topics_from_url
        topics = top_3_topics_from_url(url)
        return topics or []
    except Exception as e:
        log.warning(f"  [topics] Error: {e}")
        return []


def write_alert(deviceid: str, categoryid: str, severity: str, domain: str, reason_code: str, searchid: str):
    alertid = "A" + uuid.uuid4().hex[:14]
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO alerts (alertid, deviceid, categoryid, severity, domain, reason_code, searchid)
            VALUES (:aid, :did, :cid, :sev, :dom, :rc, "sid)
        """), {
            "aid": alertid,
            "did": deviceid,
            "cid": categoryid,
            "sev": severity,
            "dom": domain[:255] if domain else None,
            "rc": reason_code[:100] if reason_code else None,
            "sid": searchid
        })
    log.info(f"    → Alert {alertid}: [{severity.upper()}] {categoryid} — {reason_code}")


def mark_search_flagged(searchid: str):
    with engine.begin() as conn:
        conn.execute(text("UPDATE searches SET flagged = TRUE WHERE searchid = :sid"), {"sid": searchid})


def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc or url.split("//")[-1].split("/")[0]
    except Exception:
        return url[:255]


def process_search(searchid: str, deviceid: str, url: str, query_text: str):
    log.info(f"Processing [{searchid}] {url}")
    domain = extract_domain(url)
    alerts_written = 0

    has_profanity = run_profanity_check(url)
    log.info(f"  Profanity: {'YES' if has_profanity else 'no'}")
    if has_profanity:
        write_alert(deviceid, CAT_PROFANITY, "watch", domain, "PROFANITY_DETECTED", searchid)
        alerts_written += 1

    offensive_result = run_offensive_check(url)
    log.info(f"  Offensive: {offensive_result}")
    if offensive_result in ("severe", "moderate", "watch"):
        write_alert(deviceid, CAT_OFFENSIVE, offensive_result, domain, f"OFFENSIVE_{offensive_result.upper()}", searchid)
        alerts_written += 1

    topics = []
    if offensive_result in ("severe", "moderate", "watch") or has_profanity:
        topics = run_topic_extraction(url)
    log.info(f"  Topics: {topics}")
    if topics:
        topic_severity = offensive_result if offensive_result in ("severe", "moderate") else "watch"
        reason = "TOPICS:" + "|".join(topics[:3])
        write_alert(deviceid, CAT_TOPICS, topic_severity, domain, reason, searchid)
        alerts_written += 1

    mark_search_flagged(searchid)
    log.info(f"  Done — {alerts_written} alert(s) written\n")


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
    parser.add_argument("--setup", action="store_true", help="Create tables and seed categories, then exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between loop runs (default: 30)")
    args = parser.parse_args()

    if args.setup:
        setup_database()
    elif args.loop:
        run_loop(args.interval)
    else:
        run_once()
