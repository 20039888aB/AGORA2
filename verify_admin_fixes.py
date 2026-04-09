"""
Script to verify all admin fixes are in place
"""

import os
import sys

def check_file_content(filepath, expected_content):
    """Check if file contains expected content"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return expected_content in content
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

def main():
    print("🔍 Verifying Admin Fixes...")
    print("=" * 50)
    
    checks = [
        {
            'file': 'assignments/admin.py',
            'description': 'AssignmentSubmissionAdmin list_filter fixed',
            'expected': "list_filter = [\n        'status', 'submitted_at', 'graded_at'\n    ]"
        },
        {
            'file': 'courses/admin.py',
            'description': 'LessonAdmin get_course_title method added',
            'expected': "def get_course_title(self, obj):"
        },
        {
            'file': 'enrollments/admin.py',
            'description': 'EnrollmentCertificateAdmin get_user/get_course methods added',
            'expected': "def get_user(self, obj):"
        },
        {
            'file': 'permissions/admin.py',
            'description': 'RolePermissionAdmin permissions_display method added',
            'expected': "def permissions_display(self, obj):"
        },
        {
            'file': 'permissions/models.py',
            'description': 'UserPermission related_name fixed',
            'expected': "related_name='custom_permissions'"
        }
    ]
    
    all_good = True
    for check in checks:
        filepath = os.path.join(os.getcwd(), check['file'])
        if os.path.exists(filepath):
            if check_file_content(filepath, check['expected']):
                print(f"✅ {check['description']}")
            else:
                print(f"❌ {check['description']} - NOT FOUND")
                all_good = False
        else:
            print(f"❌ File not found: {check['file']}")
            all_good = False
    
    print("=" * 50)
    if all_good:
        print("🎉 All admin fixes are in place!")
        print("🚀 You can now run: python manage.py runserver")
    else:
        print("⚠️ Some fixes are missing. Please check the files above.")
    
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
