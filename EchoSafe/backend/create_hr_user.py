#!/usr/bin/env python3
"""
Create or update an HR user in MongoDB.
Usage:
  python create_hr_user.py admin Admin@7038!
"""

import os
import sys
import sqlite3
from datetime import UTC, datetime

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python create_hr_user.py <username> <password>")
        return 1

    username = sys.argv[1].strip()
    password = sys.argv[2]
    if not username or len(password) < 8:
        print("Username required and password must be 8+ chars.")
        return 1

    database_url = os.getenv("DATABASE_URL", "echosafe.db")

    with sqlite3.connect(database_url) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT username FROM hr_users WHERE username = ?", (username,))
        existing = cursor.fetchone()
        pw_hash = hash_password(password)

        if existing:
            cursor.execute("UPDATE hr_users SET password_hash = ? WHERE username = ?", (pw_hash, username))
            print(f"Updated user: {username}")
        else:
            try:
                cursor.execute(
                    "INSERT INTO hr_users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, pw_hash, datetime.now(UTC).isoformat()),
                )
                print(f"Created user: {username}")
            except sqlite3.IntegrityError:
                # This case should be rare due to the check above, but is good practice
                print(f"Error: User {username} already exists.")
                return 1
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
