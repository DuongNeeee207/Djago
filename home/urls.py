from django.urls import path
from . import views

urlpatterns = [
    # ==========================
    # KHÁCH HÀNG (USER / PUBLIC)
    # ==========================
    path('', views.home_view, name='home'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('compatibility/', views.compatibility_search, name='compatibility_search'),
    
    # Giỏ hàng & Mua sắm
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/<int:pk>/', views.my_order_detail, name='my_order_detail'),

    # Đăng nhập, Đăng ký, Đăng xuất
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # ==========================
    # QUẢN TRỊ VIÊN (ADMIN PANEL)
    # ==========================
    path('manage/', views.admin_dashboard, name='admin_dashboard'),
    path('manage/products/', views.admin_product_list, name='admin_product_list'),
    path('manage/products/create/', views.admin_product_create, name='admin_product_create'),
    path('manage/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    
    path('manage/orders/', views.admin_order_list, name='admin_order_list'),
    path('manage/orders/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),

    path('manage/receipts/', views.admin_receipt_list, name='admin_receipt_list'),
    path('manage/receipts/create/', views.admin_receipt_create, name='admin_receipt_create'),

    path('manage/users/', views.admin_user_management, name='admin_user_management'),
    path('manage/seed-data/', views.seed_sample_data, name='seed_sample_data'),
]
