from django.urls import path
from . import views

urlpatterns = [
    # Root URL
    path('', views.home, name='home'),
    
    # Auth URLs
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Feed URLs
    path('feed/', views.feed, name='feed'),
    path('feed/list/', views.feed_list_view, name='feed_list'),
    path('feed/<int:id>/', views.feed_detail_view, name='feed_detail'),
    
    # Profile URLs
    path('profiles/', views.profiles, name='profiles'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile/<str:username>/follow/', views.follow, name='follow'),
    path('profile/<str:username>/unfollow/', views.unfollow, name='unfollow'),
    path('profile/<int:id>/edit/', views.profile_edit, name='profile_edit'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    path('profile/change-username/', views.change_username_view, name='change_username'),
    
    # Wall URLs
    path('wall/post/create/', views.post_create_view, name='post_create'),
    path('wall/post/<int:id>/', views.post_detail_view, name='post_detail'),
    path('wall/post/<int:id>/edit/', views.post_edit_view, name='post_edit'),
    path('wall/post/<int:id>/delete/', views.post_delete_view, name='post_delete'),
    
    # Comment URLs
    path('wall/comment/create/', views.comment_create_view, name='comment_create'),
    path('wall/comment/<int:id>/edit/', views.comment_edit_view, name='comment_edit'),
    path('wall/comment/<int:id>/delete/', views.comment_delete_view, name='comment_delete'),
]