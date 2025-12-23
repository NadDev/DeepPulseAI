#!/usr/bin/env python
"""Script to inspect the SQLite database structure"""
import sqlite3
import os

# Find the database
db_paths = [
    "crbot.db",
    "../crbot.db",
]

db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("❌ Database not found!")
    exit(1)

print(f"📁 Database: {os.path.abspath(db_path)}")
print(f"📊 Size: {os.path.getsize(db_path) / 1024:.1f} KB")
print()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("=" * 60)
print("TABLES IN DATABASE")
print("=" * 60)

for (table_name,) in tables:
    print(f"\n📋 {table_name}")
    print("-" * 40)
    
    # Get columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        col_id, name, col_type, not_null, default, pk = col
        pk_marker = " 🔑" if pk else ""
        print(f"   {name} ({col_type}){pk_marker}")
    
    # Count rows
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"   → {count} rows")

conn.close()
print("\n" + "=" * 60)
