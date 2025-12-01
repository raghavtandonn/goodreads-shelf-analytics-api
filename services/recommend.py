from sqlalchemy import func
from sqlalchemy.orm import Session
from models import Book, Reading

def _clamp01(x):
    return 0.0 if x is None else max(0.0, min(1.0, float(x)))

def _norm_pages(pages, max_pages=600):
    if pages is None:
        return 0.5  # neutral if unknown
    p = min(max_pages, max(0, int(pages)))
    return 1.0 - (p / max_pages)  # shorter → higher score

def _norm_year(year, lo=1900, hi=2025):
    if year is None:
        return 0.5
    y = max(lo, min(hi, int(year)))
    return (y - lo) / (hi - lo)

def _bayes(avg, n, prior_mean, k):
    # shrink sparse estimates toward your overall mean rating
    n = float(n or 0)
    avg = float(avg or prior_mean)
    denom = n + k
    return (avg * n + prior_mean * k) / denom if denom > 0 else prior_mean

def build_user_profile(db: Session, user_id: str = "me", k_author: float = 2.0, k_year: float = 2.0):
    # overall mean rating across your READ shelf
    global_mean = (
        db.query(func.avg(Reading.rating))
          .filter(Reading.user_id == user_id,
                  Reading.exclusive_shelf == "read",
                  Reading.rating.isnot(None))
          .scalar()
    ) or 0.0

    # author has a bayesian-smoothed mean rating so past ratings of an author affect current recs
    author_pref = {}
    rows = (
        db.query(Book.author,
                 func.count(Reading.id).label("n"),
                 func.avg(Reading.rating).label("avg"))
          .join(Reading, Reading.book_id == Book.id)
          .filter(Reading.user_id == user_id,
                  Reading.exclusive_shelf == "read",
                  Reading.rating.isnot(None),
                  Book.author.isnot(None))
          .group_by(Book.author)
          .all()
    )
    for author, n, avg in rows:
        bayes = _bayes(avg, n, global_mean, k_author)
        author_pref[author] = bayes / 5.0  # to [0,1]

    # year also has bayesian smoothed mean rating, then min-max to [0,1]
    year_bayes = {}
    rows = (
        db.query(Book.year,
                 func.count(Reading.id).label("n"),
                 func.avg(Reading.rating).label("avg"))
          .join(Reading, Reading.book_id == Book.id)
          .filter(Reading.user_id == user_id,
                  Reading.exclusive_shelf == "read",
                  Reading.rating.isnot(None),
                  Book.year.isnot(None))
          .group_by(Book.year)
          .all()
    )
    vals = []
    for year, n, avg in rows:
        bayes = _bayes(avg, n, global_mean, k_year)
        year_bayes[year] = bayes
        vals.append(bayes)
    mn, mx = (min(vals), max(vals)) if vals else (0.0, 0.0)

    year_pref = {}
    for year, bayes in year_bayes.items():
        if mx > mn:
            year_pref[year] = (bayes - mn) / (mx - mn)
        else:
            year_pref[year] = 0.5

    return {
        "global_mean_norm": (global_mean / 5.0) if global_mean else 0.6,
        "author_pref": author_pref,
        "year_pref": year_pref,
    }

def recommend_to_read(
    db: Session,
    user_id: str = "me",
    limit: int = 10,
    w_author: float = 0.35,  # lowered this var so it doesn’t dominate
    w_pages: float = 0.20,
    w_year: float = 0.25,
    k_author: float = 2.0,
    k_year: float = 2.0,
):
    profile = build_user_profile(db, user_id, k_author=k_author, k_year=k_year)
    aff = profile["author_pref"]
    year_pref = profile["year_pref"]
    global_mean_norm = profile["global_mean_norm"]  # fallback when author/year is unseen

    candidates = (
        db.query(Book.id, Book.title, Book.author, Book.pages, Book.year)
          .join(Reading, Reading.book_id == Book.id)
          .filter(Reading.user_id == user_id, Reading.exclusive_shelf == "to-read")
          .all()
    )

    scored = []
    for bid, title, author, pages, year in candidates:
        a = _clamp01(aff.get(author, global_mean_norm))
        y = _clamp01(year_pref.get(year, 0.5))
        p = _norm_pages(pages)

        score = w_author * a + w_year * y + w_pages * p

        scored.append({
            "book_id": bid,
            "title": title,
            "author": author,
            "score": round(score, 4),
            "explain": {
                "author_affinity": round(a, 3),
                "year_component": round(y, 3),
                "pages_component": round(p, 3),
                "weights": {"author": w_author, "year": w_year, "pages": w_pages},
            },
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return {"count": len(scored), "items": scored[:limit]}