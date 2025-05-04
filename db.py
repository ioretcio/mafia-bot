import sqlite3

DB_NAME = 'assets/mafia.db'

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()

        # Користувачі
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            tg_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            photo TEXT,
            status TEXT DEFAULT 'Кандидат',
            games_played INTEGER DEFAULT 0,
            bonus_points INTEGER DEFAULT 0
        )
        ''')

        # Ігри
        c.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY,
            date TEXT,
            time TEXT,
            location TEXT,
            type TEXT,
            host TEXT
        )
        ''')

        # Запис на ігри
        c.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            game_id INTEGER,
            payment_type TEXT,
            present INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(game_id) REFERENCES games(id)
        )
        ''')

        # Оплати
        c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            game_id INTEGER, -- можна NULL
            date TEXT,
            amount INTEGER,
            payment_type TEXT, -- "cash", "online", "abonement", etc.
            comment TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(game_id) REFERENCES games(id)
        )
        ''')

        conn.commit()
