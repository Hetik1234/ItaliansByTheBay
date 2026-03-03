from django.contrib.auth import views as auth_views
from django.urls import path
from . import views 

app_name = 'users'

urlpatterns = [
    path('register_view/', views.register_view, name='register'),
    path('login/', views.custom_login_view, name='login'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile_view, name='profile'),
]