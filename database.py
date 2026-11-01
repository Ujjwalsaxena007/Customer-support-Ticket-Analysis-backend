import sqlite3

DATABASE_NAME = "tickets.db"


def get_connection():
    connection = sqlite3.connect(
        DATABASE_NAME,
        timeout=10
    )

    connection.row_factory = sqlite3.Row
    return connection


def create_table():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Open'
            )
        """)

        # Existing database migration
        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(tickets)"
            ).fetchall()
        }

        new_columns = {
            "category": "TEXT DEFAULT 'General'",
            "sentiment": "TEXT DEFAULT 'Neutral'",
            "sentiment_score": "REAL DEFAULT 0",
            "device_id": "TEXT",
            "temperature": "REAL",
            "source": "TEXT DEFAULT 'Manual'",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT"
        }

        for column, definition in new_columns.items():
            if column not in existing_columns:
                connection.execute(
                    f"ALTER TABLE tickets ADD COLUMN "
                    f"{column} {definition}"
                )

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_status
            ON tickets(status)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_priority
            ON tickets(priority)
        """)

        connection.commit()

    finally:
        connection.close()