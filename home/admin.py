from django.contrib import admin
from .models import (
    Brand, PhoneModel, Category, Supplier,
    Product, StockReceipt, StockReceiptItem,
    Order, OrderItem
)

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(PhoneModel)
class PhoneModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand')
    list_filter = ('brand',)
    search_fields = ('name', 'brand__name')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address')
    search_fields = ('name', 'phone')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('sku', 'name', 'category', 'grade', 'stock_quantity', 'retail_price', 'cost_price', 'location')
    list_filter = ('category', 'grade', 'compatible_models__brand')
    search_fields = ('sku', 'name', 'compatible_models__name')
    filter_horizontal = ('compatible_models',)
    list_editable = ('retail_price', 'location')

class StockReceiptItemInline(admin.TabularInline):
    model = StockReceiptItem
    extra = 1

@admin.register(StockReceipt)
class StockReceiptAdmin(admin.ModelAdmin):
    list_display = ('receipt_code', 'supplier', 'created_at', 'total_amount', 'created_by')
    inlines = [StockReceiptItemInline]
    search_fields = ('receipt_code', 'supplier__name')
    list_filter = ('created_at',)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'unit_cost', 'subtotal')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'customer_name', 'customer_phone', 'created_at', 'total_amount', 'profit')
    inlines = [OrderItemInline]
    search_fields = ('order_code', 'customer_name', 'customer_phone')
    list_filter = ('created_at',)
    readonly_fields = ('total_amount', 'total_cost', 'profit', 'created_at')

from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'phone')
