from .cart import Cart


def ecommerce_cart(request):
    """
    Make the session cart available in every template.

    The context processor keeps the navigation cart badge consistent across
    the shop, product, checkout, success, profile and Enterprise Order pages.
    """
    cart = Cart(request)

    return {
        "cart": cart,
        "cart_count": cart.count,
    }
