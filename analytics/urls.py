from django.urls import path
from . import views

urlpatterns = [
    # Platform analytics (SuperAdmin)
    path('platform/', views.platform_analytics, name='platform_analytics'),
    
    # Organization analytics (Admin+)
    path('organization/', views.organization_analytics, name='organization_analytics'),
    
    # Team analytics (Manager+)
    path('team/', views.team_analytics, name='team_analytics'),
    
    # Student analytics (Student)
    path('student/', views.student_analytics, name='student_analytics'),
    
    # Learning paths
    path('learning-paths/', views.learning_paths, name='learning_paths'),
    path('learning-paths/<uuid:path_id>/enroll/', views.enroll_learning_path, name='enroll_learning_path'),
    
    # Achievements
    path('achievements/', views.user_achievements, name='user_achievements'),
    
    # System metrics (SuperAdmin)
    path('system/', views.system_metrics, name='system_metrics'),
]
