from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Brand, Category, BaseProduct, ProductVariant
from .serializers import (
    BrandSerializer,
    BrandCreateSerializer,
    BrandUpdateSerializer,
    CategorySerializer,
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
    BaseProductSerializer,
    BaseProductCreateSerializer,
    BaseProductUpdateSerializer,
    ProductVariantSerializer,
    ProductVariantCreateSerializer,
    ProductVariantUpdateSerializer
)
from .filters import BaseProductFilter, ProductVariantFilter


class BrandListView(ListAPIView):
    """
    View to list all brands.

    GET: Returns a list of all brands with their information.
    Requires JWT authentication via Bearer token.
    """
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated]


class BrandCreateView(CreateAPIView):
    """
    View to create a new brand.

    POST: Creates a new brand with the provided data.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = BrandCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        brand = serializer.save()

        return Response({
            'message': 'Brand created successfully',
            'brand': BrandSerializer(brand).data
        }, status=status.HTTP_201_CREATED)


class BrandUpdateView(UpdateAPIView):
    """
    View to update brand information.

    PATCH/PUT: Updates brand information (name).
    Requires JWT authentication via Bearer token.
    """
    queryset = Brand.objects.all()
    serializer_class = BrandUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Brand updated successfully',
            'brand': BrandSerializer(instance).data
        }, status=status.HTTP_200_OK)


class BrandActivateView(APIView):
    """
    View to activate a brand.

    POST: Sets active=True for the specified brand.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)

        if brand.active:
            return Response({
                'message': 'Brand is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        brand.active = True
        brand.save()

        return Response({
            'message': 'Brand activated successfully',
            'brand': BrandSerializer(brand).data
        }, status=status.HTTP_200_OK)


class BrandDeactivateView(APIView):
    """
    View to deactivate a brand.

    POST: Sets active=False for the specified brand.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        brand = get_object_or_404(Brand, pk=pk)

        if not brand.active:
            return Response({
                'message': 'Brand is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        brand.active = False
        brand.save()

        return Response({
            'message': 'Brand deactivated successfully',
            'brand': BrandSerializer(brand).data
        }, status=status.HTTP_200_OK)


# Category Views

class CategoryListView(ListAPIView):
    """
    View to list all categories.

    GET: Returns a list of all categories with their information.
    Requires JWT authentication via Bearer token.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryCreateView(CreateAPIView):
    """
    View to create a new category.

    POST: Creates a new category with the provided data.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = CategoryCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = serializer.save()

        return Response({
            'message': 'Category created successfully',
            'category': CategorySerializer(category).data
        }, status=status.HTTP_201_CREATED)


class CategoryUpdateView(UpdateAPIView):
    """
    View to update category information.

    PATCH/PUT: Updates category information (name, description).
    Requires JWT authentication via Bearer token.
    """
    queryset = Category.objects.all()
    serializer_class = CategoryUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Category updated successfully',
            'category': CategorySerializer(instance).data
        }, status=status.HTTP_200_OK)


class CategoryActivateView(APIView):
    """
    View to activate a category.

    POST: Sets active=True for the specified category.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)

        if category.active:
            return Response({
                'message': 'Category is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        category.active = True
        category.save()

        return Response({
            'message': 'Category activated successfully',
            'category': CategorySerializer(category).data
        }, status=status.HTTP_200_OK)


class CategoryDeactivateView(APIView):
    """
    View to deactivate a category.

    POST: Sets active=False for the specified category.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)

        if not category.active:
            return Response({
                'message': 'Category is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        category.active = False
        category.save()

        return Response({
            'message': 'Category deactivated successfully',
            'category': CategorySerializer(category).data
        }, status=status.HTTP_200_OK)


# BaseProduct Views

class BaseProductListView(ListAPIView):
    """
    View to list and filter BaseProducts.

    GET: Returns a list of products with advanced filtering capabilities.
    Requires JWT authentication via Bearer token.

    Available filters (via query parameters):

    Basic filters:
    - ?model_name=lenovo (partial match, case-insensitive)
    - ?slug=exact-slug
    - ?brand=1 (brand ID)
    - ?brand__name=asus (brand name, partial match)
    - ?categories=1 (category ID, can use multiple times)
    - ?active=true

    Specs filters (JSON field filtering):
    - ?spec_processor_model=i5 (processor model)
    - ?spec_processor_cores=10 (exact cores count)
    - ?spec_screen_size=15.6 (screen size)
    - ?spec_screen_resolution=fhd (screen resolution)
    - ?spec_screen_refresh_rate=144 (refresh rate)
    - ?spec_memory_size=16gb (memory size)
    - ?spec_memory_type=ddr5 (memory type)
    - ?spec_graphics_model=rtx (graphics card model)
    - ?spec_graphics_vram=8gb (graphics VRAM)
    - ?spec_storage_size=512 (storage size)
    - ?spec_storage_type=ssd (storage type)
    - ?spec_weight=2.4 (weight)
    - ?spec_battery=60wh (battery)

    Search (searches in model_name and long_description):
    - ?search=gaming laptop

    Ordering:
    - ?ordering=model_name (ascending)
    - ?ordering=-creation_date (descending by creation date)
    - Available fields: model_name, creation_date, update_date

    Example:
    /products/base-products/?brand__name=lenovo&spec_memory_size=16gb&spec_processor_model=i5&ordering=-creation_date
    """
    queryset = BaseProduct.objects.all().select_related('brand').prefetch_related('categories', 'images')
    serializer_class = BaseProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = BaseProductFilter
    search_fields = ['model_name', 'long_description']
    ordering_fields = ['model_name', 'creation_date', 'update_date']
    ordering = ['-creation_date']


class BaseProductDetailView(RetrieveAPIView):
    """
    View to retrieve a single BaseProduct by ID or slug.

    GET: Returns detailed information of a specific product including:
    - Product information (model name, description, specs)
    - Related brand information
    - Related categories
    - All associated images

    Requires JWT authentication via Bearer token.

    You can retrieve by:
    - ID: /products/base-products/1/
    - Slug: /products/base-products/lenovo-loq-156/
    """
    queryset = BaseProduct.objects.all().select_related('brand').prefetch_related('categories', 'images')
    serializer_class = BaseProductSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_object(self):
        """
        Override to allow lookup by both pk and slug.
        First tries pk, then falls back to slug if pk is not a number.
        """
        lookup_value = self.kwargs.get(self.lookup_field)

        # Try to get by pk first (if it's a number)
        if lookup_value.isdigit():
            return get_object_or_404(self.queryset, pk=lookup_value)

        # Otherwise, try to get by slug
        return get_object_or_404(self.queryset, slug=lookup_value)


class BaseProductCreateView(CreateAPIView):
    """
    View to create a new BaseProduct with images.

    POST: Creates a new product with up to 4 images and flexible specs JSON.
    Requires JWT authentication via Bearer token.
    Accepts multipart/form-data for image uploads.

    Expected fields:
    - model_name: Product model name (e.g., "Lenovo LOQ 15.6")
    - long_description: Detailed product description
    - brand: Brand ID
    - categories: List of category IDs (e.g., [1, 2])
    - specs: JSON object with product specifications (flexible structure)
    - image_1, image_2, image_3, image_4: Image files (optional)
    - alt_text_1, alt_text_2, alt_text_3, alt_text_4: Alt text for images (optional)

    Example specs for a laptop:
    {
        "screen": {"size": "15.6\"", "resolution": "FHD", "refresh_rate": "144 Hz"},
        "processor": {"model": "Intel Core i5 13450HX", "cores": 10, "threads": 16},
        "memory": {"size": "16GB", "type": "DDR5"},
        "graphics": {"model": "NVIDIA GeForce RTX 5050", "vram": "8GB"},
        "storage": {"size": "512GB", "type": "SSD"},
        "connectivity": ["WiFi 6", "Bluetooth 5.2", "USB-C", "HDMI 2.1"],
        "battery": "60Wh",
        "weight": "2.4 kg"
    }
    """
    serializer_class = BaseProductCreateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @transaction.atomic
    def create(self, request, *args, **kwargs):        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        base_product = serializer.save()

        return Response({
            'message': 'Product created successfully',
            'product': BaseProductSerializer(base_product).data
        }, status=status.HTTP_201_CREATED)


class BaseProductUpdateView(UpdateAPIView):
    """
    View to update BaseProduct information.

    PATCH/PUT: Updates product information, specs, categories, and images.
    Requires JWT authentication via Bearer token.
    Accepts multipart/form-data for image uploads.

    All fields are optional for partial updates.
    Use 'remove_images' with a list of image IDs to delete existing images.
    """
    queryset = BaseProduct.objects.all()
    serializer_class = BaseProductUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = 'pk'

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Product updated successfully',
            'product': BaseProductSerializer(instance).data
        }, status=status.HTTP_200_OK)


class BaseProductActivateView(APIView):
    """
    View to activate a BaseProduct.

    POST: Sets active=True for the specified product.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(BaseProduct, pk=pk)

        if product.active:
            return Response({
                'message': 'Product is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        product.active = True
        product.save()

        return Response({
            'message': 'Product activated successfully',
            'product': BaseProductSerializer(product).data
        }, status=status.HTTP_200_OK)


class BaseProductDeactivateView(APIView):
    """
    View to deactivate a BaseProduct.

    POST: Sets active=False for the specified product.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(BaseProduct, pk=pk)

        if not product.active:
            return Response({
                'message': 'Product is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        product.active = False
        product.save()

        return Response({
            'message': 'Product deactivated successfully',
            'product': BaseProductSerializer(product).data
        }, status=status.HTTP_200_OK)


# ProductVariant Views

class ProductVariantListView(ListAPIView):
    """
    View to list and filter ProductVariants.

    GET: Returns a list of product variants with advanced filtering capabilities.
    Requires JWT authentication via Bearer token.

    Available filters (via query parameters):
    - ?base_product=1 (base product ID)
    - ?base_product__slug=lenovo-loq (base product slug, partial match)
    - ?base_product__model_name=lenovo (base product model name, partial match)
    - ?condition=nuevo (condition: nuevo, open_box, refurbished, usado)
    - ?stock_status=en_stock (stock status: en_stock, en_camino, por_importacion, sin_stock)
    - ?is_published=true (published status)
    - ?active=true (active status)
    - ?price_min=500000 (minimum price)
    - ?price_max=2000000 (maximum price)

    Ordering:
    - ?ordering=price (ascending by price)
    - ?ordering=-price (descending by price)
    - Available fields: price, creation_date, update_date

    Example:
    /products/variants/?base_product=1&condition=nuevo&price_min=1000000&price_max=2000000&ordering=price
    """
    queryset = ProductVariant.objects.all().select_related('base_product__brand').prefetch_related('base_product__categories', 'base_product__images')
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProductVariantFilter
    ordering_fields = ['price', 'creation_date', 'update_date']
    ordering = ['price']


class ProductVariantDetailView(RetrieveAPIView):
    """
    View to retrieve a single ProductVariant by ID.

    GET: Returns detailed information of a specific product variant including:
    - Variant information (price, condition, stock status, published status)
    - Related base product information (with brand, categories, images)

    Requires JWT authentication via Bearer token.
    """
    queryset = ProductVariant.objects.all().select_related('base_product__brand').prefetch_related('base_product__categories', 'base_product__images')
    serializer_class = ProductVariantSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


class ProductVariantCreateView(CreateAPIView):
    """
    View to create a new ProductVariant.

    POST: Creates a new product variant with the provided data.
    Requires JWT authentication via Bearer token.

    Expected fields:
    - base_product: Base product ID (required)
    - price: Variant price (required, must be positive)
    - condition: Product condition (required, choices: nuevo, open_box, refurbished, usado)
    - stock_status: Stock status (required, choices: en_stock, en_camino, por_importacion, sin_stock)
    - is_published: Visibility status (required, boolean)

    Example:
    {
        "base_product": 1,
        "price": 1500000,
        "condition": "nuevo",
        "stock_status": "en_stock",
        "is_published": true
    }
    """
    serializer_class = ProductVariantCreateSerializer
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product_variant = serializer.save()

        return Response({
            'message': 'Product variant created successfully',
            'product_variant': ProductVariantSerializer(product_variant).data
        }, status=status.HTTP_201_CREATED)


class ProductVariantUpdateView(UpdateAPIView):
    """
    View to update ProductVariant information.

    PATCH/PUT: Updates product variant information.
    Requires JWT authentication via Bearer token.

    All fields are optional for partial updates:
    - base_product: Base product ID
    - price: Variant price (must be positive)
    - condition: Product condition (choices: nuevo, open_box, refurbished, usado)
    - stock_status: Stock status (choices: en_stock, en_camino, por_importacion, sin_stock)
    - is_published: Visibility status (boolean)
    """
    queryset = ProductVariant.objects.all()
    serializer_class = ProductVariantUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Product variant updated successfully',
            'product_variant': ProductVariantSerializer(instance).data
        }, status=status.HTTP_200_OK)


class ProductVariantActivateView(APIView):
    """
    View to activate a ProductVariant.

    POST: Sets active=True for the specified product variant.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)

        if variant.active:
            return Response({
                'message': 'Product variant is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        variant.active = True
        variant.save()

        return Response({
            'message': 'Product variant activated successfully',
            'product_variant': ProductVariantSerializer(variant).data
        }, status=status.HTTP_200_OK)


class ProductVariantDeactivateView(APIView):
    """
    View to deactivate a ProductVariant.

    POST: Sets active=False for the specified product variant.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)

        if not variant.active:
            return Response({
                'message': 'Product variant is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        variant.active = False
        variant.save()

        return Response({
            'message': 'Product variant deactivated successfully',
            'product_variant': ProductVariantSerializer(variant).data
        }, status=status.HTTP_200_OK)


class ProductVariantPublishView(APIView):
    """
    View to publish a ProductVariant (make it visible in the store).

    POST: Sets is_published=True for the specified product variant.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)

        if variant.is_published:
            return Response({
                'message': 'Product variant is already published'
            }, status=status.HTTP_400_BAD_REQUEST)

        variant.is_published = True
        variant.save()

        return Response({
            'message': 'Product variant published successfully',
            'product_variant': ProductVariantSerializer(variant).data
        }, status=status.HTTP_200_OK)


class ProductVariantUnpublishView(APIView):
    """
    View to unpublish a ProductVariant (hide it from the store).

    POST: Sets is_published=False for the specified product variant.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        variant = get_object_or_404(ProductVariant, pk=pk)

        if not variant.is_published:
            return Response({
                'message': 'Product variant is already unpublished'
            }, status=status.HTTP_400_BAD_REQUEST)

        variant.is_published = False
        variant.save()

        return Response({
            'message': 'Product variant unpublished successfully',
            'product_variant': ProductVariantSerializer(variant).data
        }, status=status.HTTP_200_OK)
