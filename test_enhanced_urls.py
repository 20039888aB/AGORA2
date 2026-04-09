#!/usr/bin/env python
"""
Test Enhanced Course URLs
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agoraprof.settings')
django.setup()

def test_enhanced_urls():
    """Test enhanced course URLs"""
    
    print("🔗 Testing Enhanced Course URLs")
    print("=" * 50)
    
    try:
        from django.urls import reverse
        
        # Test enhanced course URLs
        urls_to_test = [
            'enhanced_courses_list',
            'enhanced_course_create',
            'enhanced_course_detail',
            'enhanced_course_edit',
            'enhanced_course_update',
            'enhanced_course_delete',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(f'content:{url_name}')
                print(f"   ✅ {url_name}: {url}")
            except Exception as e:
                print(f"   ❌ {url_name}: {str(e)}")
        
        # Test with parameters
        try:
            detail_url = reverse('content:enhanced_course_detail', kwargs={'course_id': '12345678-1234-5678-1234-5678-12345678'})
            print(f"   ✅ enhanced_course_detail (with params): {detail_url}")
        except Exception as e:
            print(f"   ❌ enhanced_course_detail (with params): {str(e)}")
        
        print("\n✅ Enhanced URL tests completed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ URL test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_enhanced_urls()
    sys.exit(0 if success else 1)
