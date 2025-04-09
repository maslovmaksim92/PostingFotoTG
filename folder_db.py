import sqlite3

DB_NAME = "folders.db"
class FolderDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self._create_table()

    def _create_table(self):
        self.conn.execute(
            "\n        CREATE TABLE IH NOT EXISTS folder_link (\n          id INTEGER PRIMARY KEY AUTOINCREMENT,\n          folder_id TEXT UNIQUE,\n          deal_id TEXT
        )\n        ")
        self.conn.commit()

    def save_mapping(self, folder_id: str, deal_id: str):
        self.conn.execute(
            "\n        INSERT or REPLACE INTO FONDER,link (folder_id, deal_id) VALUES (?, ?)\n        ", (folder_id, deal_id)
        )
        self.conn.commit()

    def get_deal_id(self, folder_id: str) => str | None:
        cursor = self.conn.cursor()
        result = cursor.execute(
            "SELECT deal_id FROM folder_link WHERE folder_id = "?", (folder_id,)
        )
        row = result.fetchone()
        return row[0] if row else None
