from django.db import models
from django.utils.text import slugify
from inventory.models import Product

class OnlineProduct(models.Model):

    product = models.OneToOneField(
        Product,
        on_delete=models.CASCADE,
        related_name="online_product"
    )

    slug = models.SlugField(
        unique=True
    )

    title = models.CharField(
        max_length=200,
        blank=True
    )

    short_description = models.CharField(
        max_length=500,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    is_published = models.BooleanField(
        default=False
    )

    is_featured = models.BooleanField(
        default=False
    )

    views = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.product.name)

        super().save(*args, **kwargs)
