from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 1. Xuất xứ / Nguồn gốc (Đà Lạt, Vĩnh Long, Nhập khẩu Úc, Nhập khẩu Mỹ...)
class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Xuất xứ / Nguồn gốc")

    class Meta:
        verbose_name = "Xuất xứ"
        verbose_name_plural = "Xuất xứ"
        ordering = ['name']

    def __str__(self):
        return self.name


# 2. Giống / Loại cụ thể (Cà chua beef, Rau muống nước, Xoài cát Hòa Lộc...)
class PhoneModel(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name="models", verbose_name="Xuất xứ")
    name = models.CharField(max_length=100, verbose_name="Tên giống / loại cụ thể")

    class Meta:
        verbose_name = "Giống loại"
        verbose_name_plural = "Giống loại"
        unique_together = ('brand', 'name')
        ordering = ['brand__name', 'name']

    def __str__(self):
        return f"{self.brand.name} - {self.name}"


# 3. Danh mục sản phẩm (Rau lá, Củ/Khoai, Trái cây, Gia vị, Nấm...)
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên danh mục")

    class Meta:
        verbose_name = "Danh mục sản phẩm"
        verbose_name_plural = "Danh mục sản phẩm"
        ordering = ['name']

    def __str__(self):
        return self.name


# 4. Nhà cung cấp
class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="Tên nhà cung cấp")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ")

    class Meta:
        verbose_name = "Nhà cung cấp"
        verbose_name_plural = "Nhà cung cấp"

    def __str__(self):
        return self.name


# 5. Sản phẩm Rau Củ Quả
class Product(models.Model):
    GRADE_CHOICES = [
        ('ZIN', 'Hữu cơ (Organic)'),
        ('LK1', 'Sạch (VietGAP)'),
        ('OEM', 'Thường'),
        ('DLC', 'Nhập khẩu (Import)'),
    ]

    sku = models.CharField(max_length=50, unique=True, verbose_name="Mã SKU")
    name = models.CharField(max_length=255, verbose_name="Tên sản phẩm")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="Danh mục")
    grade = models.CharField(max_length=10, choices=GRADE_CHOICES, default='LK1', verbose_name="Phân loại chất lượng")
    
    # Quan hệ nhiều-nhiều: 1 sản phẩm có thể có nhiều nguồn gốc/giống loại
    compatible_models = models.ManyToManyField(
        PhoneModel,
        related_name="compatible_parts",
        blank=True,
        verbose_name="Giống loại / Nguồn gốc cụ thể"
    )
    
    cost_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Giá vốn (VNĐ)")
    retail_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name="Giá bán lẻ (VNĐ)")
    stock_quantity = models.IntegerField(default=0, verbose_name="Số lượng tồn kho")
    min_stock_alert = models.IntegerField(default=3, verbose_name="Mức cảnh báo tồn tối thiểu")
    location = models.CharField(max_length=100, blank=True, verbose_name="Vị trí kệ / quầy")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật cuối")

    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Danh mục Sản phẩm"
        ordering = ['category', 'name']

    def __str__(self):
        return f"[{self.sku}] {self.name}"

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_alert

    @property
    def is_out_of_stock(self):
        return self.stock_quantity <= 0


# 6. Phiếu nhập kho
class StockReceipt(models.Model):
    receipt_code = models.CharField(max_length=50, unique=True, verbose_name="Mã phiếu nhập")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Nhà cung cấp")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời gian nhập")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Người lập phiếu")
    total_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Tổng tiền nhập (VNĐ)")
    note = models.TextField(blank=True, verbose_name="Ghi chú nhập hàng")

    class Meta:
        verbose_name = "Phiếu nhập kho"
        verbose_name_plural = "Phiếu nhập kho"
        ordering = ['-created_at']

    def __str__(self):
        return self.receipt_code


class StockReceiptItem(models.Model):
    receipt = models.ForeignKey(StockReceipt, on_delete=models.CASCADE, related_name="items", verbose_name="Phiếu nhập")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="receipt_items", verbose_name="Sản phẩm")
    quantity = models.PositiveIntegerField(verbose_name="Số lượng nhập")
    import_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Đơn giá nhập (VNĐ)")

    class Meta:
        verbose_name = "Chi tiết nhập kho"
        verbose_name_plural = "Chi tiết nhập kho"

    @property
    def subtotal(self):
        return self.quantity * self.import_price


# 7. Đơn đặt hàng / Bán lẻ
class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Chờ xác nhận'),
        ('CONFIRMED', 'Đã xác nhận & Chuẩn bị hàng'),
        ('SHIPPING', 'Đang giao hàng'),
        ('COMPLETED', 'Hoàn thành / Đã nhận hàng'),
        ('CANCELLED', 'Đã hủy đơn'),
    ]

    order_code = models.CharField(max_length=50, unique=True, verbose_name="Mã đơn hàng")
    customer_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="customer_orders", verbose_name="Tài khoản đặt hàng")
    customer_name = models.CharField(max_length=100, default="Khách lẻ", verbose_name="Tên người nhận")
    customer_phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    shipping_address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ giao hàng")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Trạng thái đơn")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Thời gian đặt")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="processed_orders", verbose_name="Nhân viên xử lý")
    total_amount = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Tổng tiền đơn hàng (VNĐ)")
    total_cost = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Tổng giá vốn (VNĐ)")
    profit = models.DecimalField(max_digits=14, decimal_places=0, default=0, verbose_name="Lợi nhuận gộp (VNĐ)")
    note = models.TextField(blank=True, verbose_name="Ghi chú đơn hàng")

    class Meta:
        verbose_name = "Đơn đặt hàng"
        verbose_name_plural = "Đơn đặt hàng"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_code} - {self.customer_name} ({self.get_status_display()})"

    @property
    def customer(self):
        return self.customer_user

    @property
    def gross_profit(self):
        return self.profit


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Đơn hàng")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items", verbose_name="Sản phẩm")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Số lượng")
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Giá bán lúc mua")
    unit_cost = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Giá vốn lúc xuất")

    class Meta:
        verbose_name = "Chi tiết đơn hàng"
        verbose_name_plural = "Chi tiết đơn hàng"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def item_profit(self):
        return (self.unit_price - self.unit_cost) * self.quantity


# 8. Phân quyền người dùng (Chỉ có ADMIN và USER)
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Quản trị viên (Admin)'),
        ('USER', 'Khách hàng (User)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER', verbose_name="Vai trò")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Số điện thoại")
    address = models.CharField(max_length=255, blank=True, verbose_name="Địa chỉ mặc định")

    class Meta:
        verbose_name = "Hồ sơ người dùng"
        verbose_name_plural = "Hồ sơ người dùng"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == 'ADMIN' or self.user.is_superuser


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'ADMIN' if instance.is_superuser else 'USER'
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        if not hasattr(instance, 'profile'):
            role = 'ADMIN' if instance.is_superuser else 'USER'
            UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
