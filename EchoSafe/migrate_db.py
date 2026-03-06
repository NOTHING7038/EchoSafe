#!/usr/bin/env python3
"""
Migrate database schema to add new columns for enhanced security
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "backend", "echosafe.db")

def migrate():
    """Add missing columns to hr_users table"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(hr_users)")
        columns = {row[1] for row in cursor.fetchall()}
        
        migrations = [
            ("is_locked", "ALTER TABLE hr_users ADD COLUMN is_locked INTEGER DEFAULT 0"),
            ("locked_until", "ALTER TABLE hr_users ADD COLUMN locked_until TIMESTAMP"),
            ("failed_attempts", "ALTER TABLE hr_users ADD COLUMN failed_attempts INTEGER DEFAULT 0"),
            ("last_login", "ALTER TABLE hr_users ADD COLUMN last_login TIMESTAMP"),
        ]
        
        for col_name, sql in migrations:
            if col_name not in columns:
                try:
                    cursor.execute(sql)
                    print(f"✓ Added column: {col_name}")
                except sqlite3.OperationalError as e:
                    print(f"⚠️  Column {col_name} already exists or error: {e}")
        
        conn.commit()
        conn.close()
        print("✓ Database migration completed")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    migrate()
