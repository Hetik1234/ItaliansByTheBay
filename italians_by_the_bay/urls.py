from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('menu.urls')),
    path('accounts/', include('django.contrib.auth.urls')), 
    path('orders/', include('orders.urls')),
    path('users/', include('users.urls')),
]

# serve media in development
