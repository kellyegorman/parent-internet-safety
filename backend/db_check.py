from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = "mysql+pymysql://root:ZNrabNeFJKmDjnbNgxoMJPjMiStFQcwH@trolley.proxy.rlwy.net:44931/railway"


def section(title):
    print(f"\n{'═' * 50}")
    print(f"  {title}")
    print(f"{'═' * 50}")


def safe_str(value):
    return "NULL" if value is None else str(value)


def truncate(value, length=60):
    if value is None:
        return "NULL"
    value = str(value)
    return value if len(value) <= length else value[:length] + "…"


def get_table_names(conn):
    rows = conn.execute(text("SHOW TABLES")).fetchall()
    return [row[0] for row in rows]


def get_columns(conn, table_name):
    rows = conn.execute(text(f"SHOW COLUMNS FROM `{table_name}`")).fetchall()
    return [row[0] for row in rows]


def has_columns(columns, required):
    return all(col in columns for col in required)


def print_tables(conn):
    section("TABLES IN DATABASE")
    tables = conn.execute(text("SHOW TABLES")).fetchall()
    if tables:
        for t in tables:
            print(f"  ✓ {t[0]}")
    else:
        print("  (no tables yet — run: python flagging_pipeline.py --setup)")
    return [t[0] for t in tables]


def print_users(conn, table_names):
    if "users" not in table_names:
        return

    section("USERS")
    columns = get_columns(conn, "users")

    wanted = ["userid", "username", "email", "join_date"]
    available = [c for c in wanted if c in columns]

    if not available:
        print("  (table exists, but expected columns were not found)")
        print(f"  Available columns: {', '.join(columns)}")
        return

    query = f"SELECT {', '.join(available)} FROM users"
    rows = conn.execute(text(query)).fetchall()

    if not rows:
        print("  (no users yet)")
        return

    for row in rows:
        data = dict(zip(available, row))
        userid = safe_str(data.get("userid", "?"))
        username = safe_str(data.get("username", "(no username)"))
        email = safe_str(data.get("email", "(no email)"))
        join_date = safe_str(data.get("join_date", "(unknown join date)"))
        print(f"  [{userid}] {username} <{email}> — joined {join_date}")


def print_devices(conn, table_names):
    if "devices" not in table_names:
        return

    section("DEVICES")
    columns = get_columns(conn, "devices")

    wanted = ["deviceid", "userid", "device_name", "paired_at"]
    available = [c for c in wanted if c in columns]

    if not available:
        print("  (table exists, but expected columns were not found)")
        print(f"  Available columns: {', '.join(columns)}")
        return

    query = f"SELECT {', '.join(available)} FROM devices"
    rows = conn.execute(text(query)).fetchall()

    if not rows:
        print("  (no devices yet)")
        return

    for row in rows:
        data = dict(zip(available, row))
        deviceid = safe_str(data.get("deviceid", "?"))
        userid = safe_str(data.get("userid", "?"))
        device_name = safe_str(data.get("device_name", "(unnamed device)"))
        paired_at = safe_str(data.get("paired_at", "(unknown time)"))
        print(f"  [{deviceid}] '{device_name}' owned by user {userid} — paired {paired_at}")


def print_searches(conn, table_names):
    if "searches" not in table_names:
        print("\n  ⚠️  'searches' table missing — run: python flagging_pipeline.py --setup")
        return

    section("RECENT SEARCHES (last 10)")
    columns = get_columns(conn, "searches")

    has_flagged = "flagged" in columns
    has_url = "url" in columns
    has_searchid = "searchid" in columns
    has_deviceid = "deviceid" in columns
    has_searched_at = "searched_at" in columns

    select_cols = []
    if has_searchid:
        select_cols.append("searchid")
    if has_deviceid:
        select_cols.append("deviceid")
    if has_url:
        select_cols.append("url")
    if has_flagged:
        select_cols.append("flagged")
    if has_searched_at:
        select_cols.append("searched_at")

    if not select_cols:
        print("  (table exists, but expected columns were not found)")
        print(f"  Available columns: {', '.join(columns)}")
        return

    order_clause = " ORDER BY searched_at DESC" if has_searched_at else ""
    query = f"""
        SELECT {', '.join(select_cols)}
        FROM searches
        {order_clause}
        LIMIT 10
    """
    rows = conn.execute(text(query)).fetchall()

    if not rows:
        print("  (no searches yet — browse on the monitored device first)")
    else:
        for row in rows:
            data = dict(zip(select_cols, row))
            searchid = safe_str(data.get("searchid", "?"))
            url = truncate(data.get("url", "(no url)"))
            searched_at = safe_str(data.get("searched_at", "(unknown time)"))

            if has_flagged:
                flagged = data.get("flagged")
                flag_label = "✓ flagged" if flagged else "⏳ pending"
                print(f"  [{searchid}] {flag_label} | {url} | {searched_at}")
            else:
                print(f"  [{searchid}] {url} | {searched_at}")

    if has_flagged and has_url:
        pending = conn.execute(text("""
            SELECT COUNT(*)
            FROM searches
            WHERE flagged = FALSE AND url IS NOT NULL
        """)).scalar()
        print(f"\n  Pending (unprocessed): {pending}")
    elif has_flagged:
        pending = conn.execute(text("""
            SELECT COUNT(*)
            FROM searches
            WHERE flagged = FALSE
        """)).scalar()
        print(f"\n  Pending (unprocessed): {pending}")
    else:
        print("\n  Pending (unprocessed): column 'flagged' not found in searches table")


def print_alerts(conn, table_names):
    if "alerts" not in table_names:
        print("\n  ⚠️  'alerts' table missing — run: python flagging_pipeline.py --setup")
        return

    section("RECENT ALERTS (last 10)")
    alert_columns = get_columns(conn, "alerts")

    required_alert_cols = ["alertid", "severity", "domain", "reason_code", "created_at"]
    alerts_ok = has_columns(alert_columns, required_alert_cols)

    if "alert_category" in table_names:
        category_columns = get_columns(conn, "alert_category")
        category_ok = has_columns(category_columns, ["categoryid", "category_name"])
    else:
        category_ok = False

    if alerts_ok and category_ok and "categoryid" in alert_columns:
        rows = conn.execute(text("""
            SELECT a.alertid, a.severity, ac.category_name, a.domain, a.reason_code, a.created_at
            FROM alerts a
            JOIN alert_category ac ON a.categoryid = ac.categoryid
            ORDER BY a.created_at DESC
            LIMIT 10
        """)).fetchall()

        if rows:
            for r in rows:
                alertid, severity, category_name, domain, reason_code, created_at = r
                print(
                    f"  [{safe_str(alertid)}] "
                    f"{safe_str(severity).upper():8s} | "
                    f"{safe_str(category_name):12s} | "
                    f"{safe_str(domain)} | "
                    f"{safe_str(reason_code)} | "
                    f"{safe_str(created_at)}"
                )
        else:
            print("  (no alerts yet — run the flagging pipeline first)")
    else:
        available = ", ".join(alert_columns)
        print("  (alerts table exists, but expected columns for joined display were not found)")
        print(f"  Available alert columns: {available}")


def print_alert_categories(conn, table_names):
    if "alert_category" not in table_names:
        return

    section("ALERT CATEGORIES")
    columns = get_columns(conn, "alert_category")

    wanted = ["categoryid", "category_name", "category_description"]
    available = [c for c in wanted if c in columns]

    if not available:
        print("  (table exists, but expected columns were not found)")
        print(f"  Available columns: {', '.join(columns)}")
        return

    query = f"SELECT {', '.join(available)} FROM alert_category"
    rows = conn.execute(text(query)).fetchall()

    if not rows:
        print("  (empty — run: python flagging_pipeline.py --setup)")
        return

    for row in rows:
        data = dict(zip(available, row))
        categoryid = safe_str(data.get("categoryid", "?"))
        category_name = safe_str(data.get("category_name", "(no name)"))
        category_description = safe_str(data.get("category_description", "(no description)"))
        print(f"  [{categoryid}] {category_name} — {category_description}")


def print_alert_settings(conn, table_names):
    if "alert_settings" not in table_names:
        return

    section("ALERT SETTINGS")
    columns = get_columns(conn, "alert_settings")

    # Print a few recent rows generically since schema may vary
    select_cols = columns[:8] if len(columns) > 8 else columns
    if not select_cols:
        print("  (table exists, but has no visible columns)")
        return

    order_clause = ""
    if "updated_at" in columns:
        order_clause = " ORDER BY updated_at DESC"
    elif "created_at" in columns:
        order_clause = " ORDER BY created_at DESC"

    query = f"""
        SELECT {', '.join(select_cols)}
        FROM alert_settings
        {order_clause}
        LIMIT 10
    """
    rows = conn.execute(text(query)).fetchall()

    if not rows:
        print("  (no alert settings found)")
        return

    for row in rows:
        pairs = [f"{col}={safe_str(val)}" for col, val in zip(select_cols, row)]
        print("  " + " | ".join(pairs))


def main():
    print("\n🔌 Connecting to database…")

    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Connected successfully!\n")
    except SQLAlchemyError as e:
        print(f"Connection FAILED: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your internet connection")
        print("  2. Verify the DATABASE_URL is correct")
        print("  3. Make sure your Railway project is running")
        return

    try:
        with engine.connect() as conn:
            table_names = print_tables(conn)
            print_users(conn, table_names)
            print_devices(conn, table_names)
            print_searches(conn, table_names)
            print_alerts(conn, table_names)
            print_alert_categories(conn, table_names)
            print_alert_settings(conn, table_names)

    except SQLAlchemyError as e:
        print(f"\n❌ Database query FAILED: {e}")
        print("   The connection worked, but one of the queries did not match the current schema.")
        print("   Check table columns with: SHOW COLUMNS FROM <table_name>;")
        return

    print(f"\n{'═' * 50}")
    print("  Done!")
    print(f"{'═' * 50}\n")


if __name__ == "__main__":
    main()