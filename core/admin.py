# core/admin.py
from django.contrib import admin
from .models import StoreDetail

@admin.register(StoreDetail)
class StoreDetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number')
    # Since there should only be one, disable the add permission
    # and potentially override has_change_permission if needed later

    def has_add_permission(self, request):
        # Prevent adding more than one StoreDetail instance via admin
        return not StoreDetail.objects.exists()

    def has_delete_permission(self, request, obj=None):
         # Optional: Prevent deleting the only instance via admin
         # return False
         return True # Allow deletion for now