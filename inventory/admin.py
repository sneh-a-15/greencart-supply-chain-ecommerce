from django.contrib import admin
from . import models
# Register your models here.
admin.site.register(models.Product)
admin.site.register(models.ProductCategories)
admin.site.register(models.Supplier)
admin.site.register(models.Notification)
admin.site.register(models.RestockRequest)