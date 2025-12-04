from database import SessionLocal
from services.etl import import_goodreads_csv
with open("data/goodreads_library_export.csv","rb") as f:
    db = SessionLocal()
    try:
        print(import_goodreads_csv(f.read(), db))
    finally:
        db.close()
