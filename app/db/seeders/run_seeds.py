from app.core.db import SessionLocal
from app.db.seeders.seed_offices import seed_offices
from app.db.seeders.seed_managers import seed_managers


def run():
    db = SessionLocal()
    try:
        seed_offices(db)
        seed_managers(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()