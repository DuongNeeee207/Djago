from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, F, Q, Count
from django.utils import timezone
from functools import wraps
from decimal import Decimal

from .models import (
    Brand, PhoneModel, Category, Supplier,
    Product, StockReceipt, StockReceiptItem,
    Order, OrderItem, UserProfile
)

# ========================================================
# HÀM PHÂN QUYỀN (CHỈ CÓ ADMIN VÀ USER)
# ========================================================
def is_admin_user(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'ADMIN')

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Vui lòng đăng nhập với tài khoản Quản trị viên (Admin)!")
            return redirect('login')
        if not is_admin_user(request.user):
            messages.error(request, "Bạn không có quyền truy cập trang quản trị Admin!")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped


# ========================================================
# XÁC THỰC: ĐĂNG NHẬP, ĐĂNG KÝ, ĐĂNG XUẤT
# ========================================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard' if is_admin_user(request.user) else 'home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            
            if is_admin_user(user):
                messages.success(request, f"Đăng nhập thành công! Chào mừng Quản trị viên {user.username}.")
                return redirect('admin_dashboard')
            else:
                messages.success(request, f"Đăng nhập thành công! Chúc quý khách mua sắm vui vẻ.")
                return redirect('home')
        else:
            messages.error(request, "Tên đăng nhập hoặc mật khẩu không chính xác!")

    return render(request, 'inventory/login.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        fullname = request.POST.get('fullname', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not username or not password:
            messages.error(request, "Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!")
        elif len(password) < 6:
            messages.error(request, "Mật khẩu phải có ít nhất 6 ký tự!")
        elif password != confirm_password:
            messages.error(request, "Mật khẩu xác nhận không khớp!")
        elif User.objects.filter(username=username).exists():
            messages.error(request, f"Tên đăng nhập '{username}' đã được sử dụng!")
        else:
            # Tạo tài khoản Khách hàng (User)
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=fullname
            )
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = 'USER'
            profile.phone = phone
            profile.address = address
            profile.save()

            login(request, user)
            messages.success(request, f"Đăng ký tài khoản thành công! Bạn có thể chọn sản phẩm và đặt mua ngay.")
            return redirect('home')

    return render(request, 'inventory/signup.html')


def logout_view(request):
    logout(request)
    messages.success(request, "Bạn đã đăng xuất tài khoản an toàn.")
    return redirect('home')


# ========================================================
# 1. DÀNH CHO KHÁCH HÀNG (USER / PUBLIC): MUA HÀNG
# ========================================================

# Trang chủ cửa hàng / Xem sản phẩm
def home_view(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    brand_id = request.GET.get('brand')
    model_id = request.GET.get('model')

    products = Product.objects.filter(stock_quantity__gt=0).select_related('category').prefetch_related('compatible_models__brand')

    if query:
        products = products.filter(
            Q(sku__icontains=query) |
            Q(name__icontains=query) |
            Q(compatible_models__name__icontains=query)
        ).distinct()

    if category_id:
        products = products.filter(category_id=category_id)

    if brand_id:
        products = products.filter(compatible_models__brand_id=brand_id).distinct()

    if model_id:
        products = products.filter(compatible_models__id=model_id).distinct()

    categories = Category.objects.all()
    brands = Brand.objects.all()
    phone_models = PhoneModel.objects.all()

    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        'brands': brands,
        'phone_models': phone_models,
        'query': query,
        'selected_category': category_id,
        'selected_brand': brand_id,
        'selected_model': model_id,
    })


# Chi tiết sản phẩm
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'related_products': related_products,
    })


# Tra cứu sản phẩm theo xuất xứ
def compatibility_search(request):
    selected_brand = request.GET.get('brand')
    selected_model = request.GET.get('model')
    keyword = request.GET.get('keyword', '').strip()

    brands = Brand.objects.all()
    models_list = PhoneModel.objects.all()
    if selected_brand:
        models_list = models_list.filter(brand_id=selected_brand)

    products = []
    current_model = None

    if selected_model:
        current_model = get_object_or_404(PhoneModel, pk=selected_model)
        products = Product.objects.filter(compatible_models=current_model, stock_quantity__gt=0).select_related('category')
    elif keyword:
        products = Product.objects.filter(
            Q(compatible_models__name__icontains=keyword) |
            Q(compatible_models__brand__name__icontains=keyword) |
            Q(name__icontains=keyword),
            stock_quantity__gt=0
        ).distinct().select_related('category')

    return render(request, 'shop/compatibility.html', {
        'brands': brands,
        'models_list': models_list,
        'selected_brand': int(selected_brand) if selected_brand else None,
        'selected_model': int(selected_model) if selected_model else None,
        'current_model': current_model,
        'products': products,
        'keyword': keyword,
    })


# Giỏ hàng (Session-based Cart)
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_amount = Decimal(0)

    for p_id_str, qty in list(cart.items()):
        try:
            product = Product.objects.get(id=int(p_id_str))
            subtotal = product.retail_price * qty
            total_amount += subtotal
            cart_items.append({
                'product': product,
                'quantity': qty,
                'subtotal': subtotal,
            })
        except Product.DoesNotExist:
            del cart[p_id_str]
            request.session['cart'] = cart

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total_amount': total_amount,
    })


def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    qty = int(request.POST.get('quantity', 1))

    cart = request.session.get('cart', {})
    current_qty = cart.get(str(product_id), 0)

    if current_qty + qty > product.stock_quantity:
        messages.error(request, f"Sản phẩm [{product.sku}] chỉ còn {product.stock_quantity} phần trong kho!")
    else:
        cart[str(product_id)] = current_qty + qty
        request.session['cart'] = cart
        messages.success(request, f"Đã thêm '{product.name}' vào giỏ hàng!")

    if request.POST.get('buy_now'):
        return redirect('cart_view')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


def cart_update(request, product_id):
    if request.method == 'POST':
        action = request.POST.get('action')
        cart = request.session.get('cart', {})
        p_id_str = str(product_id)
        
        if p_id_str in cart:
            product = get_object_or_404(Product, id=product_id)
            if action == 'increase':
                if cart[p_id_str] + 1 <= product.stock_quantity:
                    cart[p_id_str] += 1
                else:
                    messages.error(request, f"Chỉ còn {product.stock_quantity} phần trong kho!")
            elif action == 'decrease':
                cart[p_id_str] -= 1
                if cart[p_id_str] <= 0:
                    del cart[p_id_str]
            elif action == 'remove':
                del cart[p_id_str]
            request.session['cart'] = cart

    return redirect('cart_view')


# Khách hàng Đặt hàng (Checkout)
@login_required
@transaction.atomic
def checkout_view(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Giỏ hàng của bạn đang trống!")
        return redirect('home')

    cart_items = []
    total_amount = Decimal(0)
    total_cost = Decimal(0)

    for p_id_str, qty in cart.items():
        product = get_object_or_404(Product, id=int(p_id_str))
        if product.stock_quantity < qty:
            messages.error(request, f"Sản phẩm '{product.name}' hiện chỉ còn {product.stock_quantity} phần. Vui lòng cập nhật giỏ hàng!")
            return redirect('cart_view')
        
        line_price = product.retail_price * qty
        line_cost = product.cost_price * qty
        total_amount += line_price
        total_cost += line_cost
        cart_items.append({'product': product, 'quantity': qty, 'unit_price': product.retail_price, 'unit_cost': product.cost_price})

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        shipping_address = request.POST.get('shipping_address', '').strip()
        note = request.POST.get('note', '').strip()

        if not customer_name or not customer_phone or not shipping_address:
            messages.error(request, "Vui lòng điền đầy đủ Họ tên, Số điện thoại và Địa chỉ giao hàng!")
        else:
            profit = total_amount - total_cost
            order_code = f"DH{timezone.now().strftime('%Y%m%d%H%M%S')}"

            order = Order.objects.create(
                order_code=order_code,
                customer_user=request.user,
                customer_name=customer_name,
                customer_phone=customer_phone,
                shipping_address=shipping_address,
                status='PENDING',
                total_amount=total_amount,
                total_cost=total_cost,
                profit=profit,
                note=note
            )

            # Tạo chi tiết đơn hàng & trừ tồn kho
            for item in cart_items:
                product = item['product']
                product.stock_quantity -= item['quantity']
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    unit_cost=item['unit_cost']
                )

            # Xóa giỏ hàng
            request.session['cart'] = {}
            messages.success(request, f"Đặt hàng thành công! Mã đơn của bạn là {order.order_code}. Chúng tôi sẽ giao hàng sớm nhất.")
            return redirect('my_order_detail', pk=order.pk)

    user_profile = getattr(request.user, 'profile', None)
    return render(request, 'shop/checkout.html', {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'user_profile': user_profile,
    })


# Đơn mua của tôi (Dành cho User)
@login_required
def my_orders(request):
    orders = Order.objects.filter(customer_user=request.user).order_by('-created_at')
    return render(request, 'shop/my_orders.html', {'orders': orders})


@login_required
def my_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, customer_user=request.user)
    return render(request, 'shop/my_order_detail.html', {'order': order})


# ========================================================
# 2. DÀNH CHO QUẢN TRỊ VIÊN (ADMIN PANEL): TOÀN QUYỀN
# ========================================================

# Dashboard Quản Trị
@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    today_orders = Order.objects.filter(created_at__date=today)
    
    today_revenue = today_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    today_profit = today_orders.aggregate(total=Sum('profit'))['total'] or 0
    pending_orders_count = Order.objects.filter(status='PENDING').count()

    total_sku = Product.objects.count()
    low_stock_products = Product.objects.filter(stock_quantity__lte=F('min_stock_alert'), stock_quantity__gt=0)
    out_of_stock_products = Product.objects.filter(stock_quantity__lte=0)
    
    all_products = Product.objects.all()
    total_inventory_cost = sum(p.stock_quantity * p.cost_price for p in all_products if p.stock_quantity > 0)
    total_inventory_retail = sum(p.stock_quantity * p.retail_price for p in all_products if p.stock_quantity > 0)

    recent_orders = Order.objects.all()[:6]

    return render(request, 'admin_panel/dashboard.html', {
        'today_revenue': today_revenue,
        'today_profit': today_profit,
        'pending_orders_count': pending_orders_count,
        'total_sku': total_sku,
        'low_stock_count': low_stock_products.count(),
        'out_of_stock_count': out_of_stock_products.count(),
        'total_inventory_cost': total_inventory_cost,
        'total_inventory_retail': total_inventory_retail,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products[:5],
    })


# Quản lý kho sản phẩm (Admin)
@admin_required
def admin_product_list(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    stock_status = request.GET.get('stock')

    products = Product.objects.all().select_related('category').prefetch_related('compatible_models')

    if query:
        products = products.filter(Q(sku__icontains=query) | Q(name__icontains=query) | Q(compatible_models__name__icontains=query)).distinct()
    if category_id:
        products = products.filter(category_id=category_id)
    if stock_status == 'out':
        products = products.filter(stock_quantity__lte=0)
    elif stock_status == 'low':
        products = products.filter(stock_quantity__lte=F('min_stock_alert'), stock_quantity__gt=0)

    categories = Category.objects.all()
    return render(request, 'admin_panel/product_list.html', {
        'products': products,
        'categories': categories,
        'query': query,
    })


@admin_required
def admin_product_create(request):
    categories = Category.objects.all()
    phone_models = PhoneModel.objects.all().select_related('brand')

    if request.method == 'POST':
        sku = request.POST.get('sku', '').strip().upper()
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category')
        grade = request.POST.get('grade', 'LK1')
        cost_price = Decimal(request.POST.get('cost_price') or 0)
        retail_price = Decimal(request.POST.get('retail_price') or 0)
        stock_quantity = int(request.POST.get('stock_quantity') or 0)
        min_stock_alert = int(request.POST.get('min_stock_alert') or 3)
        location = request.POST.get('location', '').strip()
        model_ids = request.POST.getlist('compatible_models')

        if Product.objects.filter(sku=sku).exists():
            messages.error(request, f"Mã SKU '{sku}' đã tồn tại!")
        else:
            p = Product.objects.create(
                sku=sku, name=name, category_id=category_id, grade=grade,
                cost_price=cost_price, retail_price=retail_price,
                stock_quantity=stock_quantity, min_stock_alert=min_stock_alert, location=location
            )
            if model_ids:
                p.compatible_models.set(model_ids)
            messages.success(request, f"Đã thêm sản phẩm [{p.sku}] thành công!")
            return redirect('admin_product_list')

    return render(request, 'admin_panel/product_form.html', {
        'categories': categories,
        'phone_models': phone_models,
        'action': 'Thêm mới',
    })


@admin_required
def admin_product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    categories = Category.objects.all()
    phone_models = PhoneModel.objects.all().select_related('brand')

    if request.method == 'POST':
        product.name = request.POST.get('name', '').strip()
        product.category_id = request.POST.get('category')
        product.grade = request.POST.get('grade')
        product.cost_price = Decimal(request.POST.get('cost_price') or 0)
        product.retail_price = Decimal(request.POST.get('retail_price') or 0)
        product.stock_quantity = int(request.POST.get('stock_quantity') or 0)
        product.min_stock_alert = int(request.POST.get('min_stock_alert') or 3)
        product.location = request.POST.get('location', '').strip()
        product.save()

        model_ids = request.POST.getlist('compatible_models')
        product.compatible_models.set(model_ids)
        messages.success(request, f"Đã cập nhật sản phẩm [{product.sku}] thành công!")
        return redirect('admin_product_list')

    selected_model_ids = list(product.compatible_models.values_list('id', flat=True))
    return render(request, 'admin_panel/product_form.html', {
        'product': product,
        'categories': categories,
        'phone_models': phone_models,
        'selected_model_ids': selected_model_ids,
        'action': 'Chỉnh sửa',
    })


# Quản lý đơn hàng đặt mua (Admin duyệt đơn)
@admin_required
def admin_order_list(request):
    status_filter = request.GET.get('status')
    orders = Order.objects.all().prefetch_related('items__product')

    if status_filter:
        orders = orders.filter(status=status_filter)

    total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_profit = orders.aggregate(total=Sum('profit'))['total'] or 0

    return render(request, 'admin_panel/order_list.html', {
        'orders': orders,
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'status_filter': status_filter,
    })


@admin_required
@transaction.atomic
def admin_order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            if old_status != 'CANCELLED' and new_status == 'CANCELLED':
                # Hoàn trả lại số lượng tồn kho khi đơn bị hủy
                for item in order.items.all():
                    item.product.stock_quantity += item.quantity
                    item.product.save()
            elif old_status == 'CANCELLED' and new_status != 'CANCELLED':
                # Trừ lại tồn kho nếu mở lại đơn từ trạng thái đã hủy
                for item in order.items.all():
                    item.product.stock_quantity = max(0, item.product.stock_quantity - item.quantity)
                    item.product.save()

            order.status = new_status
            order.created_by = request.user
            order.save()
            messages.success(request, f"Đã cập nhật trạng thái đơn thành: {order.get_status_display()}!")
            return redirect('admin_order_detail', pk=order.pk)

    return render(request, 'admin_panel/order_detail.html', {'order': order})


# Quản lý Nhập kho (Admin)
@admin_required
def admin_receipt_list(request):
    receipts = StockReceipt.objects.all().select_related('supplier', 'created_by')
    return render(request, 'admin_panel/receipt_list.html', {'receipts': receipts})


@admin_required
@transaction.atomic
def admin_receipt_create(request):
    suppliers = Supplier.objects.all()
    products = Product.objects.all().order_by('name')

    if request.method == 'POST':
        supplier_id = request.POST.get('supplier')
        note = request.POST.get('note', '').strip()
        p_ids = request.POST.getlist('product_ids[]')
        quantities = request.POST.getlist('quantities[]')
        import_prices = request.POST.getlist('import_prices[]')

        if not p_ids:
            messages.error(request, "Vui lòng thêm ít nhất 1 sản phẩm vào phiếu nhập!")
            return redirect('admin_receipt_create')

        receipt_code = f"PNK{timezone.now().strftime('%Y%m%d%H%M%S')}"
        receipt = StockReceipt.objects.create(
            receipt_code=receipt_code,
            supplier_id=supplier_id if supplier_id else None,
            note=note,
            created_by=request.user
        )

        total_amount = Decimal(0)

        for p_id, qty_str, price_str in zip(p_ids, quantities, import_prices):
            qty = int(qty_str)
            price = Decimal(price_str)
            if qty <= 0:
                continue

            product = Product.objects.select_for_update().get(id=p_id)

            # Cập nhật giá vốn bình quân
            current_stock = max(0, product.stock_quantity)
            current_cost = product.cost_price
            new_stock = current_stock + qty
            if new_stock > 0:
                new_cost = ((current_stock * current_cost) + (qty * price)) / new_stock
                product.cost_price = round(new_cost)

            product.stock_quantity += qty
            product.save()

            StockReceiptItem.objects.create(
                receipt=receipt,
                product=product,
                quantity=qty,
                import_price=price
            )
            total_amount += (qty * price)

        receipt.total_amount = total_amount
        receipt.save()

        messages.success(request, f"Đã nhập kho thành công phiếu {receipt.receipt_code}! Giá vốn và tồn kho đã cập nhật.")
        return redirect('admin_receipt_list')

    return render(request, 'admin_panel/receipt_form.html', {
        'suppliers': suppliers,
        'products': products,
    })


# Quản lý tài khoản (Admin)
@admin_required
def admin_user_management(request):
    users = User.objects.all().select_related('profile').order_by('id')

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')
        target_user = get_object_or_404(User, id=user_id)
        profile, _ = UserProfile.objects.get_or_create(user=target_user)
        profile.role = new_role
        profile.save()

        if new_role == 'ADMIN':
            target_user.is_staff = True
            target_user.is_superuser = True
        else:
            target_user.is_superuser = False
        target_user.save()

        messages.success(request, f"Đã cập nhật quyền của '{target_user.username}' thành: {profile.get_role_display()}!")
        return redirect('admin_user_management')

    return render(request, 'admin_panel/user_management.html', {'users': users})


# Tiện ích tạo dữ liệu mẫu - RAU CỦ QUẢ kiểu Bách Hóa Xanh
@admin_required
def seed_sample_data(request):
    # Xuất xứ / Nguồn gốc
    dalat, _ = Brand.objects.get_or_create(name="Đà Lạt")
    vinhlong, _ = Brand.objects.get_or_create(name="Vĩnh Long")
    longan, _ = Brand.objects.get_or_create(name="Long An")
    nhapkhau, _ = Brand.objects.get_or_create(name="Nhập khẩu")

    # Giống loại cụ thể
    cachua_beef, _ = PhoneModel.objects.get_or_create(brand=dalat, name="Cà chua beef")
    rau_muong, _ = PhoneModel.objects.get_or_create(brand=vinhlong, name="Rau muống nước")
    xoai_cat, _ = PhoneModel.objects.get_or_create(brand=vinhlong, name="Xoài cát Hòa Lộc")
    khoai_lang_nhat, _ = PhoneModel.objects.get_or_create(brand=dalat, name="Khoai lang Nhật")
    buoi_da_xanh, _ = PhoneModel.objects.get_or_create(brand=longan, name="Bưởi da xanh")
    
    tao_fuji, _ = PhoneModel.objects.get_or_create(brand=nhapkhau, name="Táo Fuji (Nhật)")
    nho_my, _ = PhoneModel.objects.get_or_create(brand=nhapkhau, name="Nho đỏ (Mỹ)")
    cherry_my, _ = PhoneModel.objects.get_or_create(brand=nhapkhau, name="Cherry (Mỹ)")

    # Danh mục sản phẩm
    cat_raula, _ = Category.objects.get_or_create(name="Rau lá & Rau gia vị")
    cat_cu, _ = Category.objects.get_or_create(name="Củ & Khoai")
    cat_traicay, _ = Category.objects.get_or_create(name="Trái cây")
    cat_nam, _ = Category.objects.get_or_create(name="Nấm & Rau mầm")
    cat_giavi, _ = Category.objects.get_or_create(name="Gia vị tươi")

    # Nhà cung cấp
    Supplier.objects.get_or_create(
        name="Trang trại Rau Sạch Đà Lạt",
        defaults={
            'phone': "0988123456",
            'address': "123 Trần Phú, TP. Đà Lạt, Lâm Đồng"
        }
    )
    Supplier.objects.get_or_create(
        name="Hợp tác xã Nông sản Vĩnh Long",
        defaults={
            'phone': "0912345678",
            'address': "45 Quốc Lộ 1A, Vĩnh Long"
        }
    )

    # Thêm xuất xứ & giống loại bổ sung
    daklak, _ = Brand.objects.get_or_create(name='Đắk Lắk')
    lyson, _ = Brand.objects.get_or_create(name='Lý Sơn (Quảng Ngãi)')
    tiengiang, _ = Brand.objects.get_or_create(name='Tiền Giang')

    bo_sap, _ = PhoneModel.objects.get_or_create(brand=daklak, name='Bơ sáp 034')
    chuoi_nammy, _ = PhoneModel.objects.get_or_create(brand=tiengiang, name='Chuối già Nam Mỹ')
    toi_lyson, _ = PhoneModel.objects.get_or_create(brand=lyson, name='Tỏi cô đơn Lý Sơn')
    cai_thia, _ = PhoneModel.objects.get_or_create(brand=dalat, name='Cải thìa Đà Lạt')
    bap_cai, _ = PhoneModel.objects.get_or_create(brand=dalat, name='Bắp cải trắng')
    dua_leo, _ = PhoneModel.objects.get_or_create(brand=vinhlong, name='Dưa leo baby')
    nam_kimcham, _ = PhoneModel.objects.get_or_create(brand=nhapkhau, name='Nấm kim châm (Hàn Quốc)')

    sample_products = [
        {
            'sku': 'RAU-MUONG-01',
            'name': 'Rau muống nước (bó 300g)',
            'category': cat_raula,
            'grade': 'LK1',
            'cost_price': Decimal(5000),
            'retail_price': Decimal(8000),
            'stock_quantity': 50,
            'min_stock_alert': 10,
            'location': 'Kệ A1 - Rau lá',
            'models': [rau_muong],
        },
        {
            'sku': 'CACHUA-BEEF-DL',
            'name': 'Cà chua beef Đà Lạt (kg)',
            'category': cat_raula,
            'grade': 'ZIN',
            'cost_price': Decimal(25000),
            'retail_price': Decimal(39000),
            'stock_quantity': 30,
            'min_stock_alert': 5,
            'location': 'Kệ A2 - Cà chua',
            'models': [cachua_beef],
        },
        {
            'sku': 'CAI-THIA-DL',
            'name': 'Cải thìa Đà Lạt sạch (túi 500g)',
            'category': cat_raula,
            'grade': 'ZIN',
            'cost_price': Decimal(9000),
            'retail_price': Decimal(15000),
            'stock_quantity': 45,
            'min_stock_alert': 10,
            'location': 'Kệ A1 - Rau xanh',
            'models': [cai_thia],
        },
        {
            'sku': 'BAP-CAI-TRANG',
            'name': 'Bắp cải trắng Đà Lạt (bắp ~1kg)',
            'category': cat_raula,
            'grade': 'LK1',
            'cost_price': Decimal(11000),
            'retail_price': Decimal(18000),
            'stock_quantity': 30,
            'min_stock_alert': 5,
            'location': 'Kệ A2 - Bắp cải & Củ',
            'models': [bap_cai],
        },
        {
            'sku': 'DUA-LEO-BABY',
            'name': 'Dưa leo baby Vĩnh Long (túi 500g)',
            'category': cat_raula,
            'grade': 'LK1',
            'cost_price': Decimal(8000),
            'retail_price': Decimal(14000),
            'stock_quantity': 50,
            'min_stock_alert': 10,
            'location': 'Kệ A3 - Dưa leo',
            'models': [dua_leo],
        },
        {
            'sku': 'KHOAILANG-NHAT',
            'name': 'Khoai lang Nhật Đà Lạt (kg)',
            'category': cat_cu,
            'grade': 'LK1',
            'cost_price': Decimal(18000),
            'retail_price': Decimal(29000),
            'stock_quantity': 25,
            'min_stock_alert': 5,
            'location': 'Kệ B1 - Củ khoai',
            'models': [khoai_lang_nhat],
        },
        {
            'sku': 'XOAI-CAT-HL',
            'name': 'Xoài cát Hòa Lộc (kg)',
            'category': cat_traicay,
            'grade': 'LK1',
            'cost_price': Decimal(45000),
            'retail_price': Decimal(69000),
            'stock_quantity': 20,
            'min_stock_alert': 5,
            'location': 'Kệ C1 - Trái cây',
            'models': [xoai_cat],
        },
        {
            'sku': 'BO-SAP-034',
            'name': 'Bơ sáp 034 Đắk Lắk (kg)',
            'category': cat_traicay,
            'grade': 'LK1',
            'cost_price': Decimal(35000),
            'retail_price': Decimal(55000),
            'stock_quantity': 35,
            'min_stock_alert': 5,
            'location': 'Kệ C1 - Trái cây tươi',
            'models': [bo_sap],
        },
        {
            'sku': 'CHUOI-NAMMY',
            'name': 'Chuối già Nam Mỹ Tiền Giang (nải)',
            'category': cat_traicay,
            'grade': 'LK1',
            'cost_price': Decimal(18000),
            'retail_price': Decimal(28000),
            'stock_quantity': 40,
            'min_stock_alert': 8,
            'location': 'Kệ C2 - Chuối & Trái cây',
            'models': [chuoi_nammy],
        },
        {
            'sku': 'BUOI-DAXANH-LA',
            'name': 'Bưởi da xanh Long An (trái)',
            'category': cat_traicay,
            'grade': 'LK1',
            'cost_price': Decimal(30000),
            'retail_price': Decimal(45000),
            'stock_quantity': 15,
            'min_stock_alert': 5,
            'location': 'Kệ C2 - Trái cây',
            'models': [buoi_da_xanh],
        },
        {
            'sku': 'TAO-FUJI-NK',
            'name': 'Táo Fuji nhập khẩu Nhật (kg)',
            'category': cat_traicay,
            'grade': 'DLC',
            'cost_price': Decimal(95000),
            'retail_price': Decimal(149000),
            'stock_quantity': 10,
            'min_stock_alert': 3,
            'location': 'Kệ C3 - NK cao cấp',
            'models': [tao_fuji],
        },
        {
            'sku': 'NHO-DO-MY',
            'name': 'Nho đỏ không hạt nhập Mỹ (kg)',
            'category': cat_traicay,
            'grade': 'DLC',
            'cost_price': Decimal(120000),
            'retail_price': Decimal(189000),
            'stock_quantity': 8,
            'min_stock_alert': 3,
            'location': 'Kệ C3 - NK cao cấp',
            'models': [nho_my],
        },
        {
            'sku': 'CHERRY-MY-01',
            'name': 'Cherry Mỹ (hộp 500g)',
            'category': cat_traicay,
            'grade': 'DLC',
            'cost_price': Decimal(180000),
            'retail_price': Decimal(279000),
            'stock_quantity': 5,
            'min_stock_alert': 3,
            'location': 'Kệ C3 - NK cao cấp',
            'models': [cherry_my],
        },
        {
            'sku': 'NAM-BAO-NGU',
            'name': 'Nấm bào ngư tươi (gói 200g)',
            'category': cat_nam,
            'grade': 'LK1',
            'cost_price': Decimal(12000),
            'retail_price': Decimal(19000),
            'stock_quantity': 40,
            'min_stock_alert': 8,
            'location': 'Kệ D1 - Nấm',
            'models': [],
        },
        {
            'sku': 'NAM-KIM-CHAM',
            'name': 'Nấm kim châm Hàn Quốc (gói 150g)',
            'category': cat_nam,
            'grade': 'DLC',
            'cost_price': Decimal(7000),
            'retail_price': Decimal(12000),
            'stock_quantity': 60,
            'min_stock_alert': 12,
            'location': 'Kệ D1 - Nấm lạnh',
            'models': [nam_kimcham],
        },
        {
            'sku': 'OT-HIEM-DL',
            'name': 'Ớt hiểm Đà Lạt (100g)',
            'category': cat_giavi,
            'grade': 'LK1',
            'cost_price': Decimal(5000),
            'retail_price': Decimal(8000),
            'stock_quantity': 60,
            'min_stock_alert': 15,
            'location': 'Kệ E1 - Gia vị',
            'models': [],
        },
        {
            'sku': 'TOI-CO-DON-LYSON',
            'name': 'Tỏi cô đơn Lý Sơn chính hiệu (gói 250g)',
            'category': cat_giavi,
            'grade': 'ZIN',
            'cost_price': Decimal(45000),
            'retail_price': Decimal(75000),
            'stock_quantity': 25,
            'min_stock_alert': 5,
            'location': 'Kệ E1 - Gia vị đặc sản',
            'models': [toi_lyson],
        },
    ]

    for data in sample_products:
        models_rel = data.pop('models')
        p, created = Product.objects.get_or_create(sku=data['sku'], defaults=data)
        if created:
            p.compatible_models.set(models_rel)

    messages.success(request, "Đã khởi tạo dữ liệu mẫu rau củ quả thành công!")
    return redirect('admin_product_list')
