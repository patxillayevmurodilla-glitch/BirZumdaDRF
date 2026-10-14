from app.models import Product, Category
from django.contrib import admin
from .models import Blog

admin.site.register(Blog)
admin.site.register(Product)
admin.site.register(Category)
