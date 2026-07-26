# accounting/admin.py
from django.contrib import admin
from .models import Account, AccountingPeriod, JournalEntry, JournalLine

class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('account_type',)

@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_closed')
    list_filter = ('is_closed',)

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'reference', 'status', 'period')
    list_filter = ('status', 'period')
    inlines = [JournalLineInline]