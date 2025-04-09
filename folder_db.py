import sqlite3

DB_NAME = "folders.db"

class FolderDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS folder_link (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id TEXT UNIQUE,
                deal_id TEXT
            )
            """
        )
        self.conn.commit()

    def save_mapping(self, folder_id: str, deal_id: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO folder_link (folder_id, deal_id) VALUES (?, ?)",
            (folder_id, deal_id)
        )
        self.conn.commit()

    def get_deal_id(self, folder_id: str) -> str | None:
        cursor = self.conn.cursor()
        result = cursor.execute(
            "SELECT deal_id FROM folder_link WHERE folder_id = ?",
            (folder_id,)
        )
        row = result.fetchone()
        return row[0] if row else None
