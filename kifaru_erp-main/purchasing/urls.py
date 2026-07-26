# purchasing/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('orders/', views.po_list, name='po_list'),
    path('orders/new/', views.po_create, name='po_create'),
    path('orders/<int:po_id>/receive/', views.po_receive, name='po_receive'),
]
