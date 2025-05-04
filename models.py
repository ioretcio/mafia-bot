from db import get_connection

class User:
    @staticmethod
    def get_or_create(tg_id, username, full_name):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        user = c.fetchone()
        if not user:
            c.execute("INSERT INTO users (tg_id, username, full_name) VALUES (?, ?, ?)",
                      (tg_id, username, full_name))
            conn.commit()
        conn.close()

    @staticmethod
    def get_by_tg_id(tg_id):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        user = c.fetchone()
        conn.close()
        return user