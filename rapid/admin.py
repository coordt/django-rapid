from django.contrib import admin
from models import Account, Container

class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', )

class ContainerAdmin(admin.ModelAdmin):
    fields = ('name', 'path', 'account')
    list_display = ('name', 'path', 'account')
    list_filter = ('account',)
    search_fields = ('name', )

admin.site.register(Container, ContainerAdmin)
admin.site.register(Account, AccountAdmin)

