
import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(
        field_name="title",
        lookup_expr="icontains"
    )

    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="gte"
    )

    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr="lte"
    )

    category = django_filters.NumberFilter(
        field_name="category__id"
    )

    class Meta:
        model = Product
        fields = ["title", "category", "min_price", "max_price"]
