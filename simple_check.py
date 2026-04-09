import os
import sqlite3

# Connect to the database
db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== DATABASE COURSE CHECK ===")

# Check if courses table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses';")
table_exists = cursor.fetchone()

if table_exists:
    print("✅ Courses table exists")
    
    # Count courses
    cursor.execute("SELECT COUNT(*) FROM courses;")
    course_count = cursor.fetchone()[0]
    print(f"Total courses: {course_count}")
    
    if course_count > 0:
        print("\n=== COURSES FOUND ===")
        cursor.execute("""
            SELECT c.title, c.status, c.difficulty, c.duration_hours, c.price, o.name as org_name
            FROM courses c
            LEFT JOIN organizations o ON c.organization_id = o.id
            LIMIT 5
        """)
        
        courses = cursor.fetchall()
        for i, course in enumerate(courses, 1):
            title, status, difficulty, duration, price, org_name = course
            print(f"{i}. {title}")
            print(f"   Organization: {org_name or 'None'}")
            print(f"   Status: {status}")
            print(f"   Difficulty: {difficulty}")
            print(f"   Duration: {duration} hours")
            print(f"   Price: ${price}")
            print()
    else:
        print("❌ No courses found in database")
        print("\n📝 To create courses:")
        print("1. Navigate to: http://127.0.0.1:8000/courses/create/")
        print("2. Fill out the course creation form")
        print("3. Upload PDF documents")
        print("4. Click 'Publish Course'")
        
else:
    print("❌ Courses table does not exist")
    print("Run migrations first: python manage.py migrate")

# Check organizations table
cursor.execute("SELECT COUNT(*) FROM organizations;")
org_count = cursor.fetchone()[0]
print(f"\nTotal organizations: {org_count}")

if org_count > 0:
    cursor.execute("SELECT name FROM organizations LIMIT 3;")
    orgs = cursor.fetchall()
    print("Organizations found:")
    for org in orgs:
        print(f"- {org[0]}")

conn.close()
