#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

from django.contrib.auth import get_user_model
from organizations.models import Organization

User = get_user_model()

def create_superuser():
    print("Creating superuser...")
    
    # Get or create an organization for the superuser
    org, created = Organization.objects.get_or_create(
        name='AgoraProf System',
        defaults={
            'slug': 'agoraprof-system',
            'description': 'System administration organization',
            'user_limit': 1000,
            'subscription_tier': 'ENTERPRISE',
            'is_active': True
        }
    )
    
    if created:
        print(f"Created organization: {org.name}")
    else:
        print(f"Using existing organization: {org.name}")
    
    # Create superuser directly without validation
    superuser = User(
        email='fmngolaonyango@gmail.com',
        first_name='Felix',
        last_name='Onyango',
        is_staff=True,
        is_superuser=True,
        is_active=True,
        organization=org,
        role='SUPERADMIN'
    )
    superuser.set_password('admin123')
    superuser.save(skip_validation=True)  # Skip validation
    
    print(f"✅ Superuser created successfully!")
    print(f"📧 Email: fmngolaonyango@gmail.com")
    print(f"👤 Name: Felix Onyango")
    print(f"🔑 Password: admin123")
    print(f"🏢 Organization: {org.name}")
    print(f"\n⚠️  Please change the password after first login!")
    print(f"🌐 Login URL: http://127.0.0.1:8000/admin/")

if __name__ == '__main__':
    create_superuser()
