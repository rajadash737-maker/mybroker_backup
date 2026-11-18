import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
assert url.database == "mybroker_db"

engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    print("TOTAL PAYMENT ORDERS:",
          conn.execute(text("SELECT COUNT(*) FROM razorpay_payment_orders")).scalar())

    print("PAYMENT STATUS COUNTS:")
    for row in conn.execute(text("""
        SELECT status, COUNT(*)
        FROM razorpay_payment_orders
        GROUP BY status
    """)):
        print(row)

    print("WEBHOOK LOG TABLE EXISTS:",
          conn.execute(text("""
              SELECT COUNT(*)
              FROM information_schema.tables
              WHERE table_schema = DATABASE()
              AND table_name = 'razorpay_webhook_logs'
          """)).scalar())

engine.dispose()
