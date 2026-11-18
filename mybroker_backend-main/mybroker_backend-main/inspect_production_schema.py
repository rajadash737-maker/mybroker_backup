import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])

if url.database != "mybroker_db":
    raise RuntimeError("Wrong database. Stopped.")

engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    print("DATABASE:", conn.execute(text("SELECT DATABASE()")).scalar())

    print("\nPAYMENT ORDER COLUMNS:")
    for row in conn.execute(text("SHOW COLUMNS FROM razorpay_payment_orders")):
        print(row)

    exists = conn.execute(text("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'site_visit_requests'
    """)).scalar()

    print("\nSITE VISIT TABLE EXISTS:", exists)

engine.dispose()
