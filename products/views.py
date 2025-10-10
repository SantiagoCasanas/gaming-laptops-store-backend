from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import get_object_or_404
from .models import Brand, Category, BaseProduct
from .serializers import (
    BrandSerializer,
    BrandCreateSerializer,
    BrandUpdateSerializer,
    CategorySerializer,
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
    BaseProductSerializer,
    BaseProductCreateSerializer,
    BaseProductUpdateSerializer
)
from .filters import BaseProductFilter


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
