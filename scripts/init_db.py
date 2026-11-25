"""One-off helper: `python scripts/init_db.py` creates all tables without starting the server."""
from app.database import init_db

if __name__ == "__main__":
    init_db()
    print("Database tables created.")
