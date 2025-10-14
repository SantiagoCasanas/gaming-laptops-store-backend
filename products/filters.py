from django_filters import rest_framework as filters
from .models import BaseProduct, ProductVariant


class BaseProductFilter(filters.FilterSet):
    """
    Advanced filter for BaseProduct with support for JSON field filtering.

    Available filters:
    - model_name: Partial match (case-insensitive)
    - slug: Exact match
    - brand: Brand ID
    - brand__name: Brand name (partial match, case-insensitive)
    - categories: Category ID (can filter by multiple)
    - active: Boolean

    JSON specs filtering (examples):
    - spec_processor_model: Filter by processor model (e.g., "Intel Core i5")
    - spec_screen_size: Filter by screen size (e.g., "15.6\"")
    - spec_memory_size: Filter by memory size (e.g., "16GB")
    - spec_graphics_model: Filter by graphics card model
    - spec_storage_size: Filter by storage size
    - spec_weight: Filter by weight

    The spec_ prefix allows filtering any nested JSON field using double underscores
    for nested keys (e.g., spec_processor__model, spec_screen__size)
    """

    # Basic field filters
    model_name = filters.CharFilter(lookup_expr='icontains')
    slug = filters.CharFilter(lookup_expr='exact')
    brand = filters.NumberFilter(field_name='brand__id')
    brand__name = filters.CharFilter(field_name='brand__name', lookup_expr='icontains')
    categories = filters.NumberFilter(field_name='categories__id')
    active = filters.BooleanFilter()

    # JSON field filters for common specs
    # These use JSONField lookups to filter within the specs JSON

    # Processor filters
    spec_processor_model = filters.CharFilter(
        field_name='specs__processor__model',
        lookup_expr='icontains',
        label='Processor Model'
    )
    spec_processor_cores = filters.NumberFilter(
        field_name='specs__processor__cores',
        lookup_expr='exact',
        label='Processor Cores'
    )

    # Screen filters
    spec_screen_size = filters.CharFilter(
        field_name='specs__screen__size',
        lookup_expr='icontains',
        label='Screen Size'
    )
    spec_screen_resolution = filters.CharFilter(
        field_name='specs__screen__resolution',
        lookup_expr='icontains',
        label='Screen Resolution'
    )
    spec_screen_refresh_rate = filters.CharFilter(
        field_name='specs__screen__refresh_rate',
        lookup_expr='icontains',
        label='Screen Refresh Rate'
    )

    # Memory filters
    spec_memory_size = filters.CharFilter(
        field_name='specs__memory__size',
        lookup_expr='icontains',
        label='Memory Size'
    )
    spec_memory_type = filters.CharFilter(
        field_name='specs__memory__type',
        lookup_expr='icontains',
        label='Memory Type'
    )

    # Graphics filters
    spec_graphics_model = filters.CharFilter(
        field_name='specs__graphics__model',
        lookup_expr='icontains',
        label='Graphics Card Model'
    )
    spec_graphics_vram = filters.CharFilter(
        field_name='specs__graphics__vram',
        lookup_expr='icontains',
        label='Graphics VRAM'
    )

    # Storage filters
    spec_storage_size = filters.CharFilter(
        field_name='specs__storage__size',
        lookup_expr='icontains',
        label='Storage Size'
    )
    spec_storage_type = filters.CharFilter(
        field_name='specs__storage__type',
        lookup_expr='icontains',
        label='Storage Type'
    )

    # Physical attributes
    spec_weight = filters.CharFilter(
        field_name='specs__weight',
        lookup_expr='icontains',
        label='Weight'
    )
    spec_battery = filters.CharFilter(
        field_name='specs__battery',
        lookup_expr='icontains',
        label='Battery'
    )

    class Meta:
        model = BaseProduct
        fields = [
            'model_name',
            'slug',
            'brand',
            'brand__name',
            'categories',
            'active',
            'spec_processor_model',
            'spec_processor_cores',
            'spec_screen_size',
            'spec_screen_resolution',
            'spec_screen_refresh_rate',
            'spec_memory_size',
            'spec_memory_type',
            'spec_graphics_model',
            'spec_graphics_vram',
            'spec_storage_size',
            'spec_storage_type',
            'spec_weight',
            'spec_battery'
        ]


class ProductVariantFilter(filters.FilterSet):
    """
    Advanced filter for ProductVariant.

    Available filters:
    - base_product: Base product ID
    - base_product__slug: Base product slug (partial match)
    - base_product__model_name: Base product model name (partial match)
    - condition: Condition (exact match: nuevo, open_box, refurbished, usado)
    - stock_status: Stock status (exact match: en_stock, en_camino, por_importacion, sin_stock)
    - is_published: Boolean (true/false)
    - active: Boolean (true/false)
    - price_min: Minimum price (greater than or equal)
    - price_max: Maximum price (less than or equal)
    """

    # Basic field filters
    base_product = filters.NumberFilter(field_name='base_product__id')
    base_product__slug = filters.CharFilter(field_name='base_product__slug', lookup_expr='icontains')
    base_product__model_name = filters.CharFilter(field_name='base_product__model_name', lookup_expr='icontains')

    condition = filters.ChoiceFilter(choices=ProductVariant.ConditionChoices.choices)
    stock_status = filters.ChoiceFilter(choices=ProductVariant.StatusStockChoices.choices)

    is_published = filters.BooleanFilter()
    active = filters.BooleanFilter()

    # Price range filters
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte', label='Minimum Price')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte', label='Maximum Price')

    class Meta:
        model = ProductVariant
        fields = [
            'base_product',
            'base_product__slug',
            'base_product__model_name',
            'condition',
            'stock_status',
            'is_published',
            'active',
            'price_min',
            'price_max'
        ]
