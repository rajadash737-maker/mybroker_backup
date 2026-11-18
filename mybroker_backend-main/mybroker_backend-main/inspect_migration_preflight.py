import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
assert url.database == "mybroker_db"

engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    print("PROCESSING FEE SETTINGS:")
    for row in conn.execute(text("SELECT * FROM processing_fee_settings")):
        print(row)

    print("\nWEBHOOK LOG COUNT:")
    print(conn.execute(
        text("SELECT COUNT(*) FROM razorpay_webhook_logs")
    ).scalar())

    print("\nALEMBIC REVISION:")
    print(conn.execute(
        text("SELECT version_num FROM alembic_version")
    ).all())

engine.dispose()
