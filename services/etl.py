import io
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session

from models import User, Book, Reading

# columns Goodreads puts in the standard export
REQUIRED = [
    "Title", "Author", "My Rating", "Number of Pages",
    "Original Publication Year", "Exclusive Shelf", "Bookshelves", "Date Read"
]

def _to_int(x):
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            if pd.isna(x):
                return None
            v = int(float(x))
            return v if v != 0 else None
        # strings like "384.0" or "1,024"
        s = str(x).strip()
        if not s or s.lower() == "nan":
            return None
        s = s.replace(",", "")
        v = int(float(s))
        return v if v != 0 else None
    except Exception:
        return None

def _to_rating(x):
    # Goodreads 'My Rating' where 0 means unrated = None factor
    v = _to_int(x)
    return v if (v is not None and v > 0) else None

def _to_float(x):
    try:
        s = str(x).strip()
        return float(s) if s and s.lower() != "nan" else None
    except Exception:
        return None

def _to_date(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    for fmt in ("%Y/%m/%d", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def import_goodreads_csv(file_bytes: bytes, db: Session) -> dict:
    # Read the Goodreads export CSV and upsert into User, Book, Reading
    df = pd.read_csv(io.BytesIO(file_bytes))
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return {"ok": False, "error": f"missing columns: {missing}"}

    # attach readings to a single local user for now
    user_id = "me"
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id, name="Me")
        db.add(user)
        db.flush()

    books_upserted = 0
    readings_upserted = 0
    skipped = 0

    for _, row in df.iterrows():
        title  = str(row["Title"]).strip() if pd.notna(row["Title"]) else None
        author = str(row["Author"]).strip() if pd.notna(row["Author"]) else None
        if not title or not author:
            skipped += 1
            continue

        pages   = _to_int(row["Number of Pages"])
        year    = _to_int(row["Original Publication Year"])
        rating  = _to_rating(row["My Rating"])
        shelf   = str(row["Exclusive Shelf"]).strip() if pd.notna(row["Exclusive Shelf"]) else ""
        shelves = str(row["Bookshelves"]).strip() if pd.notna(row["Bookshelves"]) else ""
        date_read = _to_date(row.get("Date Read"))

        # get-or-create book on (title, author)
        book = db.query(Book).filter_by(title=title, author=author).first()
        if not book:
            book = Book(title=title, author=author, pages=pages, year=year, shelves=shelves)
            db.add(book)
            books_upserted += 1
        else:
            if pages and not book.pages:
                book.pages = pages
            if year and not book.year:
                book.year = year
            if shelves and shelves not in (book.shelves or ""):
                book.shelves = (book.shelves + "," if book.shelves else "") + shelves

        db.flush()  # ensure book.id exists

        reading = db.query(Reading).filter_by(user_id=user_id, book_id=book.id).first()
        if not reading:
            reading = Reading(user_id=user_id, book_id=book.id)
            db.add(reading)
            readings_upserted += 1

        # update fields if present
        if shelf:
            reading.exclusive_shelf = shelf
        if rating is not None:
            reading.rating = rating
        if date_read:
            reading.date_read = date_read

    db.commit()
    return {
        "ok": True,
        "books_upserted": books_upserted,
        "readings_upserted": readings_upserted,
        "skipped": skipped,
        "total_rows": int(len(df)),
    }