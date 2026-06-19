import os
import sqlite3
import hashlib
import secrets
from datetime import datetime


class AuthDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate_schema()
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                phone TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                id_card TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            '''
        )
        self.conn.commit()

    def _table_columns(self, table_name: str):
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row['name'] for row in cursor.fetchall()]

    def _migrate_schema(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            return

        cursor.execute("PRAGMA table_info(users)")
        existing_rows = cursor.fetchall()
        existing_columns = [row['name'] for row in existing_rows]
        existing_pk = [row['name'] for row in existing_rows if row['pk'] > 0]

        desired_columns = [
            'phone', 'password_hash', 'password_salt',
            'full_name', 'id_card', 'verification_code', 'created_at'
        ]

        if set(existing_columns) == set(desired_columns) and existing_pk == ['phone']:
            return

        cursor.execute('BEGIN')
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS users_new (
                phone TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                full_name TEXT NOT NULL,
                id_card TEXT NOT NULL,
                verification_code TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            '''
        )

        select_parts = []
        for col in desired_columns:
            if col in existing_columns:
                if col == 'created_at':
                    select_parts.append(f"COALESCE({col}, datetime('now')) AS {col}")
                else:
                    select_parts.append(f"COALESCE({col}, '') AS {col}")
            else:
                if col == 'created_at':
                    select_parts.append("datetime('now') AS created_at")
                else:
                    select_parts.append(f"'' AS {col}")

        select_clause = ', '.join(select_parts)
        cursor.execute(
            f"INSERT OR IGNORE INTO users_new ({', '.join(desired_columns)}) "
            f"SELECT {select_clause} FROM users GROUP BY phone"
        )
        cursor.execute('DROP TABLE users')
        cursor.execute('ALTER TABLE users_new RENAME TO users')
        cursor.execute('COMMIT')
        self.conn.commit()

    @staticmethod
    def _new_salt() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 150000
        ).hex()

    def create_user(self, phone: str, password: str,
                    full_name: str, id_card: str, verification_code: str) -> str:
        salt = self._new_salt()
        password_hash = self._hash_password(password, salt)
        created_at = datetime.utcnow().isoformat()
        cursor = self.conn.cursor()
        columns = self._table_columns('users')
        has_username = 'username' in columns
        if has_username:
            username_value = ''
        existing = self.get_user(phone)
        if existing:
            if has_username:
                cursor.execute(
                    '''
                    UPDATE users
                    SET password_hash = ?,
                        password_salt = ?,
                        full_name = ?,
                        id_card = ?,
                        verification_code = ?,
                        created_at = ?,
                        username = ?
                    WHERE phone = ?
                    ''',
                    (password_hash, salt, full_name, id_card, verification_code, created_at, username_value, phone)
                )
            else:
                cursor.execute(
                    '''
                    UPDATE users
                    SET password_hash = ?,
                        password_salt = ?,
                        full_name = ?,
                        id_card = ?,
                        verification_code = ?,
                        created_at = ?
                    WHERE phone = ?
                    ''',
                    (password_hash, salt, full_name, id_card, verification_code, created_at, phone)
                )
        else:
            if has_username:
                cursor.execute(
                    '''
                    INSERT INTO users (phone, password_hash, password_salt, full_name, id_card, verification_code, created_at, username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (phone, password_hash, salt, full_name, id_card, verification_code, created_at, username_value)
                )
            else:
                cursor.execute(
                    '''
                    INSERT INTO users (phone, password_hash, password_salt, full_name, id_card, verification_code, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (phone, password_hash, salt, full_name, id_card, verification_code, created_at)
                )
        self.conn.commit()
        return verification_code

    def get_user(self, phone: str):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def verify_password(self, phone: str, password: str) -> bool:
        user = self.get_user(phone)
        if not user:
            return False
        expected = self._hash_password(password, user['password_salt'])
        return secrets.compare_digest(expected, user['password_hash'])

    def verify_code(self, phone: str, code: str) -> bool:
        user = self.get_user(phone)
        if not user:
            return False
        return secrets.compare_digest(user.get('verification_code', ''), code)

    def get_verification_code(self, phone: str) -> str | None:
        user = self.get_user(phone)
        return user.get('verification_code') if user else None

    def clear_database(self):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM users')
        self.conn.commit()
        self.conn.execute('VACUUM')
