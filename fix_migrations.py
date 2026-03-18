#!/usr/bin/env python
"""
Script to fix migrations by clearing conflicting ones and re-running them.
Run via: railway run python fix_migrations.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.core.management import call_command

def fix_migrations():
    """Clear all migrations and re-run them from scratch."""
    print("=" * 60)
    print("FIXING MIGRATIONS ON RAILWAY DATABASE")
    print("=" * 60)

    try:
        # First, check if any tables exist
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            print(f"\nCurrent tables in database: {table_count}")

            if table_count > 0:
                print("\nDropping all tables to start fresh...")
                cursor.execute("DROP SCHEMA public CASCADE")
                cursor.execute("CREATE SCHEMA public")
                print("✅ Database schema reset complete\n")

        # Run migrations
        print("Running migrations...")
        call_command('migrate', verbosity=2)
        print("\n✅ Migrations completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    fix_migrations()
