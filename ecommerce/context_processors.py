from .cart import Cart
from .permissions import marketplace_permission_context


def ecommerce_cart(request):
    """
    Make Ecommerce cart and Marketplace RBAC flags available
    in every Ecommerce template.
    """
    cart = Cart(request)

    context = {
        "cart": cart,
        "cart_count": cart.count,
    }

    context.update(
        marketplace_permission_context(
            request.user
        )
    )

    return context