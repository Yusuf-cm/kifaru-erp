# sales/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('pos/', views.pos_dashboard, name='pos_dashboard'), # The POS screen
    path('api/checkout/', views.api_checkout, name='api_checkout'), # The API
]