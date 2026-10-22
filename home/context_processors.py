def cart_context(request):
    cart = request.session.get('cart', {})
    total_items = sum(cart.values())
    is_admin = False
    pending_orders_count = 0

    if request.user.is_authenticated:
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
            is_admin = True
            # Count pending orders for admin sidebar badge
            try:
                from home.models import Order
                pending_orders_count = Order.objects.filter(status='PENDING').count()
            except Exception:
                pass

    return {
        'cart_total_items': total_items,
        'is_admin': is_admin,
        'pending_orders_count': pending_orders_count,
    }
