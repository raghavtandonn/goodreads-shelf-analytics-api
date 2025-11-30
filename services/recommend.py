from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Book, Reading

def _clamp01(x):
    return 0.0 if x is None else max(0.0, min(1.0, float(x)))

def _norm_pages(pages, max_pages=600):
    if pages is None:
        return 0.5 
    p = min(max_pages, max(0, int(pages)))
    return 1.0 - (p / max_pages) # shorter has a higher score

def _norm_year(year, lo=1900, hi=2025):
    if year is None:
        return 0.5
    y = max(lo, min(hi, int(year)))
    return (y - lo) / (hi - lo)

def build_user_profile(db: Session, user_id: str = "me"):
    rows = (
        db.query(Book.author, func.count(Reading.id))
          .join(Reading, Reading.book_id == Book.id)
          .filter(Reading.user_id == user_id, Reading.exclusive_shelf == "read")
          .group_by(Book.author)
          .all()
    )
    counts = {a: c for a, c in rows}
    max_c = max(counts.values()) if counts else 1
    author_affinity = {a: c / max_c for a, c in counts.items()}
    return {"author_affinity": author_affinity}

def recommend_to_read(db: Session, user_id: str = "me", limit: int = 10,
                      w_author: float = 0.6, w_pages: float = 0.2, w_year: float = 0.2):
    profile = build_user_profile(db, user_id)
    aff = profile["author_affinity"]

    candidates = (
        db.query(Book.id, Book.title, Book.author, Book.pages, Book.year)
          .join(Reading, Reading.book_id == Book.id)
          .filter(Reading.user_id == user_id, Reading.exclusive_shelf == "to-read")
          .all()
    )

    scored = []
    for bid, title, author, pages, year in candidates:
        a = _clamp01(aff.get(author, 0.0))
        p = _norm_pages(pages)
        y = _norm_year(year)
        score = w_author * a + w_pages * p + w_year * y
        scored.append({
            "book_id": bid,
            "title": title,
            "author": author,
            "score": round(score, 4),
            "explain": {
                "author_affinity": round(a, 3),
                "pages_component": round(p, 3),
                "year_component": round(y, 3),
                "weights": {"author": w_author, "pages": w_pages, "year": w_year},
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"count": len(scored), "items": scored[:limit]}