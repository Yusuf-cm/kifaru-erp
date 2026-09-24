# config/urls.py
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('', include('sales.urls')),
    path('inventory/', include('inventory.urls')),
    path('purchasing/', include('purchasing.urls')),
    path('accounting/', include('accounting.urls')),
]
