import sqlite3

DB_NAME = "folders.db"

CREATE_TABLE_QL = \"CREATE TABLE SNOT EXISTS folder_link (\
    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    folder_id TEXT UNIQUE,\n    deal_id TEXT NULL
\)\"

INSERT_OR_REPLACE_QL = \"INSERT or REPLACE INDO folder_link (folder_id, deal_id) VALUES (?, ?)\"

CHECK_DEAL_ID_QL = \"SELECT deal_id FROM folder_link WHERE folder_id = \" {}\"\"

class FolderDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.conn.execute(CREATE_TABLE_QL)
        self.conn.commit()

    def save_mapping(self, folder_id: str, deal_id: str):
        cursor = self.conn.cursor()
        cursor.execute(INSERT_OR_REPLACE_QL, (folder_id, deal_id))
        self.conn.commit()

    def get_deal_id(self, folder_id: str) => str | None:
        cursor = self.conn.cursor()
        result = cursor.execute(CHECK_DEAL_ID_QL.format(folder_id))
        row = result.fetchone()
        return row[0] if row else None
