# accounting/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('accounts/', views.chart_of_accounts, name='chart_of_accounts'),
    path('accounts/<int:account_id>/ledger/', views.general_ledger, name='general_ledger'),
    path('trial-balance/', views.trial_balance, name='trial_balance'),
    path('profit-loss/', views.profit_loss, name='profit_loss'),
    path('balance-sheet/', views.balance_sheet, name='balance_sheet'),
    path('journals/', views.journal_list, name='journal_list'),
]
