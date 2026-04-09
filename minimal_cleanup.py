#!/usr/bin/env python
"""
Minimal Database Cleanup - Remove Only Fake Data
This script removes only the most obvious fake/test data.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

def minimal_cleanup():
    """
    Minimal cleanup of obvious fake data
    """
    print("🧹 Starting Minimal Database Cleanup...")
    print("=" * 50)
    
    # 1. Remove fake/test users only
    fake_users = User.objects.filter(
        Q(email__icontains='test') |
        Q(email__icontains='fake') |
        Q(email__icontains='demo') |
        Q(email__icontains='example') |
        Q(email__endswith='test.com')
    )
    
    print(f"🗑️  Deleting {fake_users.count()} fake/test users")
    fake_users.delete()
    
    print("\n✅ Minimal Database Cleanup Complete!")
    print("=" * 50)
    
    # Summary report
    print("\n📊 SUMMARY REPORT:")
    print(f"   Remaining Users: {User.objects.count()}")
    
    print("\n🎯 Database is now cleaned of obvious fake data!")
    print("🚀 Ready for production use!")
    
    return True

def show_stats():
    """Show current database statistics"""
    print("📊 Current Database Statistics:")
    print("=" * 40)
    
    print(f"Users: {User.objects.count()}")
    print("=" * 40)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--stats':
            show_stats()
        elif sys.argv[1] == '--cleanup':
            minimal_cleanup()
        else:
            print("Usage:")
            print("  python minimal_cleanup.py --stats     # Show database statistics")
            print("  python minimal_cleanup.py --cleanup   # Clean up fake data")
    else:
        print("Minimal Database Cleanup Script")
        print("Usage:")
        print("  python minimal_cleanup.py --stats     # Show database statistics")
        print("  python minimal_cleanup.py --cleanup   # Clean up fake data")
