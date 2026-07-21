from ecommerce.models import OnlineProduct


class Cart:

    def __init__(self, request):

        self.session = request.session

        cart = self.session.get("cart")

        if not cart:
            cart = self.session["cart"] = {}

        self.cart = cart


    def add(self, product_id, quantity=1):

        product_id = str(product_id)

        product = OnlineProduct.objects.get(id=product_id)

        if product_id in self.cart:

            self.cart[product_id]["quantity"] += int(quantity)

        else:

            self.cart[product_id] = {
                "quantity": int(quantity),
                "price": str(product.selling_price)
            }

        self.save()


    def remove(self, product_id):

        product_id = str(product_id)

        if product_id in self.cart:

            del self.cart[product_id]

            self.save()


    def save(self):

        self.session.modified = True


    def clear(self):

        self.session["cart"] = {}

        self.save()

def update(self, product_id, quantity):

    product_id = str(product_id)

    quantity = int(quantity)

    if product_id in self.cart:

        if quantity <= 0:

            del self.cart[product_id]

        else:

            self.cart[product_id]["quantity"] = quantity

    self.save()