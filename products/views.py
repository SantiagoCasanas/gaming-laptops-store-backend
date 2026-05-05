from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Brand, TipoProducto, CampoProducto, Proveedor, Producto, Descuento, UnidadProducto, BajoPedido
from .serializers import (
    BrandSerializer,
    BrandCreateSerializer,
    BrandUpdateSerializer,
    TipoProductoSerializer,
    TipoProductoCreateSerializer,
    TipoProductoUpdateSerializer,
    TipoProductoDetailSerializer,
    CampoProductoSerializer,
    CampoProductoCreateSerializer,
    CampoProductoUpdateSerializer,
    ProveedorSerializer,
    ProveedorCreateSerializer,
    ProveedorUpdateSerializer,
    ProductoSerializer,
    ProductoCreateSerializer,
    ProductoUpdateSerializer,
    BajoPedidoSerializer,
    BajoPedidoDetailSerializer,
    BajoPedidoCreateSerializer,
    BajoPedidoUpdateSerializer,
    DescuentoSerializer,
    DescuentoCreateSerializer,
    DescuentoUpdateSerializer,
    UnidadProductoSerializer,
    UnidadProductoCreateSerializer,
    UnidadProductoUpdateSerializer,
    UnidadReparacionSerializer,
)



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


# Product Type Views

class TipoProductoListView(ListAPIView):
    """
    View to list all product types.

    GET: Returns a list of all product types with their information.
    Requires JWT authentication via Bearer token.
    """
    queryset = TipoProducto.objects.all()
    serializer_class = TipoProductoSerializer
    permission_classes = [IsAuthenticated]


class TipoProductoCreateView(CreateAPIView):
    """
    View to create a new product type.

    POST: Creates a new product type with the provided data.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = TipoProductoCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tipo_producto = serializer.save()

        return Response({
            'message': 'Product type created successfully',
            'tipo_producto': TipoProductoSerializer(tipo_producto).data
        }, status=status.HTTP_201_CREATED)


class TipoProductoUpdateView(UpdateAPIView):
    """
    View to update product type information.

    PATCH/PUT: Updates product type information (nombre, descripcion).
    Requires JWT authentication via Bearer token.
    """
    queryset = TipoProducto.objects.all()
    serializer_class = TipoProductoUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Product type updated successfully',
            'tipo_producto': TipoProductoSerializer(instance).data
        }, status=status.HTTP_200_OK)


class TipoProductoActivateView(APIView):
    """
    View to activate a product type.

    POST: Sets active=True for the specified product type.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tipo_producto = get_object_or_404(TipoProducto, pk=pk)

        if tipo_producto.active:
            return Response({
                'message': 'Product type is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        tipo_producto.active = True
        tipo_producto.save()

        return Response({
            'message': 'Product type activated successfully',
            'tipo_producto': TipoProductoSerializer(tipo_producto).data
        }, status=status.HTTP_200_OK)


class TipoProductoDeactivateView(APIView):
    """
    View to deactivate a product type.

    POST: Sets active=False for the specified product type.
    Cannot deactivate if there are associated active products.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        tipo_producto = get_object_or_404(TipoProducto, pk=pk)

        if not tipo_producto.active:
            return Response({
                'message': 'Product type is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Block deactivation when associated active products exist
        if tipo_producto.productos.filter(active=True).exists():
            return Response({
                'message': 'Cannot deactivate this product type because it has associated active products'
            }, status=status.HTTP_400_BAD_REQUEST)

        tipo_producto.active = False
        tipo_producto.save()

        return Response({
            'message': 'Product type deactivated successfully',
            'tipo_producto': TipoProductoSerializer(tipo_producto).data
        }, status=status.HTTP_200_OK)


# Product Field Views

class CampoProductoListView(ListAPIView):
    """
    View to list all product fields.

    GET: Returns a list of all fields with their information.
    Requires JWT authentication via Bearer token.
    """
    queryset = CampoProducto.objects.all()
    serializer_class = CampoProductoSerializer
    permission_classes = [IsAuthenticated]


class CampoProductoCreateView(CreateAPIView):
    """
    View to create a new product field.

    POST: Creates a new field with the provided data.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = CampoProductoCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campo = serializer.save()

        return Response({
            'message': 'Product field created successfully',
            'campo_producto': CampoProductoSerializer(campo).data
        }, status=status.HTTP_201_CREATED)


class CampoProductoUpdateView(UpdateAPIView):
    """
    View to update product field information.

    PATCH/PUT: Updates field information (nombre, tipo).
    Requires JWT authentication via Bearer token.
    """
    queryset = CampoProducto.objects.all()
    serializer_class = CampoProductoUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Product field updated successfully',
            'campo_producto': CampoProductoSerializer(instance).data
        }, status=status.HTTP_200_OK)


class CampoProductoActivateView(APIView):
    """
    View to activate a product field.

    POST: Sets active=True for the specified field.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campo = get_object_or_404(CampoProducto, pk=pk)

        if campo.active:
            return Response({
                'message': 'Product field is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        campo.active = True
        campo.save()

        return Response({
            'message': 'Product field activated successfully',
            'campo_producto': CampoProductoSerializer(campo).data
        }, status=status.HTTP_200_OK)


class CampoProductoDeactivateView(APIView):
    """
    View to deactivate a product field.

    POST: Sets active=False for the specified field.
    Cannot deactivate if there are associated product types.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campo = get_object_or_404(CampoProducto, pk=pk)

        if not campo.active:
            return Response({
                'message': 'Product field is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Block deactivation when associated product types exist (via TipoProductoCampo)
        if campo.tipo_producto_campos.exists():
            return Response({
                'message': 'Cannot deactivate this product field because it is associated with one or more product types'
            }, status=status.HTTP_400_BAD_REQUEST)

        campo.active = False
        campo.save()

        return Response({
            'message': 'Product field deactivated successfully',
            'campo_producto': CampoProductoSerializer(campo).data
        }, status=status.HTTP_200_OK)


# Product Type — Field Association Views

class TipoProductoDetailView(RetrieveAPIView):
    """
    Retrieve a single product type with its ordered list of associated fields.

    GET /products/product-types/<pk>/detail/
    Returns id, nombre, descripcion, active, and a 'campos' array ordered by TipoProductoCampo.orden.
    Requires JWT authentication via Bearer token.
    """
    queryset = TipoProducto.objects.prefetch_related(
        'tipo_producto_campos__campo_producto'
    ).all()
    serializer_class = TipoProductoDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


# Proveedor Views

class ProveedorListView(ListAPIView):
    """
    View to list all suppliers.

    GET: Returns a list of all suppliers with their information.
    Requires JWT authentication via Bearer token.
    """
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated]


class ProveedorCreateView(CreateAPIView):
    """
    View to create a new supplier.

    POST: Creates a new supplier with the provided nombre.
    Slug is auto-generated from nombre on save.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = ProveedorCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proveedor = serializer.save()

        return Response({
            'message': 'Supplier created successfully',
            'proveedor': ProveedorSerializer(proveedor).data
        }, status=status.HTTP_201_CREATED)


class ProveedorUpdateView(UpdateAPIView):
    """
    View to update supplier information.

    PATCH/PUT: Updates supplier nombre. Slug is not regenerated on update.
    Requires JWT authentication via Bearer token.
    """
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Supplier updated successfully',
            'proveedor': ProveedorSerializer(instance).data
        }, status=status.HTTP_200_OK)


class ProveedorActivateView(APIView):
    """
    View to activate a supplier.

    POST: Sets active=True for the specified supplier.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk)

        if proveedor.active:
            return Response({
                'message': 'Supplier is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        proveedor.active = True
        proveedor.save()

        return Response({
            'message': 'Supplier activated successfully',
            'proveedor': ProveedorSerializer(proveedor).data
        }, status=status.HTTP_200_OK)


class ProveedorDeactivateView(APIView):
    """
    View to deactivate a supplier.

    POST: Sets active=False for the specified supplier.
    Cannot deactivate if there are active variants currently linked to this supplier.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk)

        if not proveedor.active:
            return Response({
                'message': 'Supplier is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Guard: block deactivation when active variants reference this supplier
        active_variants_count = proveedor.variantes.filter(active=True).count()
        if active_variants_count > 0:
            return Response({
                'message': (
                    f'Cannot deactivate this supplier because it has '
                    f'{active_variants_count} active variant(s) associated with it.'
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        proveedor.active = False
        proveedor.save()

        return Response({
            'message': 'Supplier deactivated successfully',
            'proveedor': ProveedorSerializer(proveedor).data
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Producto Views
# ---------------------------------------------------------------------------

class ProductoListView(ListAPIView):
    """
    View to list all products.

    GET /products/productos/list/
    Returns a list of all Producto records with nested marca, tipo_producto,
    categorias, campo_valores, and imagenes.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Producto.objects.select_related(
            'marca', 'tipo_producto'
        ).prefetch_related(
            'campo_valores__campo_producto',
            'imagenes',
        ).all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductoDetailView(RetrieveAPIView):
    """
    Retrieve a single Producto with all nested data.

    GET /products/productos/<pk>/detail/
    Requires JWT authentication via Bearer token.
    """
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Producto.objects.select_related(
            'marca', 'tipo_producto'
        ).prefetch_related(
            'campo_valores__campo_producto',
            'imagenes',
        ).all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ProductoCreateView(APIView):
    """
    Create a new Producto with images (multipart/form-data).

    POST /products/productos/create/
    Accepts: nombre, descripcion, marca, tipo_producto, categorias (multiple),
             campo_valores (JSON string), image_0…image_9 files.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import json

        # Parse campo_valores from JSON string (multipart does not support nested JSON natively)
        campo_valores_raw = request.data.get('campo_valores', '[]')
        try:
            campo_valores = json.loads(campo_valores_raw) if isinstance(campo_valores_raw, str) else campo_valores_raw
        except (json.JSONDecodeError, TypeError):
            campo_valores = []

        data = {
            'nombre': request.data.get('nombre', ''),
            'descripcion': request.data.get('descripcion', ''),
            'marca': request.data.get('marca'),
            'tipo_producto': request.data.get('tipo_producto'),
            'campo_valores': campo_valores,
        }

        serializer = ProductoCreateSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()

        return Response({
            'message': 'Product created successfully',
            'producto': ProductoSerializer(
                producto,
                context={'request': request}
            ).data,
        }, status=status.HTTP_201_CREATED)


class ProductoUpdateView(APIView):
    """
    Update an existing Producto (multipart/form-data).

    PUT /products/productos/update/<pk>/
    All base fields are optional. Providing campo_valores replaces or upserts
    the existing values. Changing tipo_producto deletes all existing campo_valores.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        import json

        producto = get_object_or_404(
            Producto.objects.select_related('marca', 'tipo_producto').prefetch_related(
                'campo_valores__campo_producto',
                'imagenes',
            ),
            pk=pk,
        )

        campo_valores_raw = request.data.get('campo_valores', None)
        campo_valores = None
        if campo_valores_raw is not None:
            try:
                campo_valores = json.loads(campo_valores_raw) if isinstance(campo_valores_raw, str) else campo_valores_raw
            except (json.JSONDecodeError, TypeError):
                campo_valores = []

        data = {}
        if request.data.get('nombre'):
            data['nombre'] = request.data.get('nombre')
        if request.data.get('descripcion'):
            data['descripcion'] = request.data.get('descripcion')
        if request.data.get('marca'):
            data['marca'] = request.data.get('marca')
        if request.data.get('tipo_producto'):
            data['tipo_producto'] = request.data.get('tipo_producto')
        if campo_valores is not None:
            data['campo_valores'] = campo_valores
        if request.data.getlist('remove_images'):
            data['remove_images'] = [int(i) for i in request.data.getlist('remove_images')]
        if request.data.get('reorder_data'):
            data['reorder_data'] = request.data.get('reorder_data')

        serializer = ProductoUpdateSerializer(
            instance=producto,
            data=data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        updated_producto = serializer.save()

        return Response({
            'message': 'Product updated successfully',
            'producto': ProductoSerializer(
                updated_producto,
                context={'request': request}
            ).data,
        }, status=status.HTTP_200_OK)


class ProductoActivateView(APIView):
    """
    Activate a product.

    POST /products/productos/activate/<pk>/
    Sets active=True. Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)

        if producto.active:
            return Response(
                {'message': 'Product is already active'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        producto.active = True
        producto.save()

        return Response({
            'message': 'Product activated successfully',
            'producto': ProductoSerializer(producto, context={'request': request}).data,
        }, status=status.HTTP_200_OK)


class ProductoDeactivateView(APIView):
    """
    Deactivate a product.

    POST /products/productos/deactivate/<pk>/
    Sets active=False. Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)

        if not producto.active:
            return Response(
                {'message': 'Product is already inactive'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        producto.active = False
        producto.save()

        return Response({
            'message': 'Product deactivated successfully',
            'producto': ProductoSerializer(producto, context={'request': request}).data,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# BajoPedido Views
# ---------------------------------------------------------------------------

class BajoPedidoListView(ListAPIView):
    """
    List all product variants.

    GET /products/variantes/list/
    Accepts an optional query parameter ?producto_id=<int> to filter by product.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = BajoPedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = BajoPedido.objects.select_related(
            'producto__marca', 'proveedor'
        ).all()
        producto_id = self.request.query_params.get('producto_id')
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        return queryset


class BajoPedidoDetailView(RetrieveAPIView):
    """
    Retrieve a single BajoPedido with nested Descuento.

    GET /products/variantes/<pk>/detail/
    Requires JWT authentication via Bearer token.
    """
    serializer_class = BajoPedidoDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return BajoPedido.objects.select_related(
            'producto__marca', 'proveedor'
        ).all()


class BajoPedidoCreateView(CreateAPIView):
    """
    Create a new product variant.

    POST /products/variantes/create/
    Required fields: producto_id, precio, condicion, estado.
    Optional fields: proveedor, enlace_proveedor, descuento (nested).
    Requires JWT authentication via Bearer token.
    """
    serializer_class = BajoPedidoCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        variante = serializer.save()

        return Response({
            'message': 'Product variant created successfully',
            'variante': BajoPedidoDetailSerializer(
                BajoPedido.objects.select_related(
                    'producto__marca', 'proveedor'
                ).get(pk=variante.pk)
            ).data,
        }, status=status.HTTP_201_CREATED)


class BajoPedidoUpdateView(UpdateAPIView):
    """
    Update an existing product variant.

    PATCH/PUT /products/variantes/update/<pk>/
    All fields are optional. Providing a nested descuento creates or replaces
    the existing discount for this variant.
    Requires JWT authentication via Bearer token.
    """
    queryset = BajoPedido.objects.select_related('producto__marca', 'proveedor').all()
    serializer_class = BajoPedidoUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        variante = serializer.save()

        return Response({
            'message': 'Product variant updated successfully',
            'variante': BajoPedidoDetailSerializer(
                BajoPedido.objects.select_related(
                    'producto__marca', 'proveedor'
                ).get(pk=variante.pk)
            ).data,
        }, status=status.HTTP_200_OK)


class BajoPedidoActivateView(APIView):
    """
    Activate a product variant.

    POST /products/variantes/activate/<pk>/
    Sets active=True. Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        variante = get_object_or_404(BajoPedido, pk=pk)

        if variante.active:
            return Response(
                {'message': 'Product variant is already active'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variante.active = True
        variante.save()

        return Response({
            'message': 'Product variant activated successfully',
            'variante': BajoPedidoSerializer(variante).data,
        }, status=status.HTTP_200_OK)


class BajoPedidoDeactivateView(APIView):
    """
    Deactivate a product variant.

    POST /products/variantes/deactivate/<pk>/
    Sets active=False. Also deactivates the linked Descuento if one exists.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        variante = get_object_or_404(BajoPedido, pk=pk)

        if not variante.active:
            return Response(
                {'message': 'Product variant is already inactive'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variante.active = False
        variante.save()

        # Also deactivate the linked discount if it exists and is active
        try:
            descuento = variante.descuento
            if descuento.active:
                descuento.active = False
                descuento.save()
        except Descuento.DoesNotExist:
            pass

        return Response({
            'message': 'Product variant deactivated successfully',
            'variante': BajoPedidoSerializer(variante).data,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Descuento Views (standalone — for activate/deactivate of existing discounts)
# ---------------------------------------------------------------------------

class DescuentoActivateView(APIView):
    """
    Activate a discount.

    POST /products/descuentos/activate/<pk>/
    Sets active=True on the Descuento.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        descuento = get_object_or_404(Descuento, pk=pk)

        if descuento.active:
            return Response(
                {'message': 'Discount is already active'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        descuento.active = True
        descuento.save()

        return Response({
            'message': 'Discount activated successfully',
            'descuento': DescuentoSerializer(descuento).data,
        }, status=status.HTTP_200_OK)


class DescuentoDeactivateView(APIView):
    """
    Deactivate a discount.

    POST /products/descuentos/deactivate/<pk>/
    Sets active=False on the Descuento.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        descuento = get_object_or_404(Descuento, pk=pk)

        if not descuento.active:
            return Response(
                {'message': 'Discount is already inactive'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        descuento.active = False
        descuento.save()

        return Response({
            'message': 'Discount deactivated successfully',
            'descuento': DescuentoSerializer(descuento).data,
        }, status=status.HTTP_200_OK)


class DescuentoDeleteView(APIView):
    """
    Delete a discount (Descuento).

    DELETE /products/descuentos/delete/<pk>/
    Deletes the Descuento record.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        descuento = get_object_or_404(Descuento, pk=pk)
        descuento.delete()

        return Response({
            'message': 'Discount deleted successfully',
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# UnidadProducto Views
# ---------------------------------------------------------------------------

class UnidadProductoListView(ListAPIView):
    """
    List all product units.

    GET /products/unidades/list/
    Accepts an optional query parameter ?producto_id=<uuid> to filter units by product.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = UnidadProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = UnidadProducto.objects.select_related(
            'producto', 'producto__marca', 'producto__tipo_producto',
            'cliente_garantia', 'cliente_metodo_aliado', 'ciudad_envio_metodo_aliado',
        ).all()
        producto_id = self.request.query_params.get('producto_id')
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        return queryset


class UnidadProductoDetailView(RetrieveAPIView):
    """
    Retrieve a single UnidadProducto.

    GET /products/unidades/<pk>/detail/
    Requires JWT authentication via Bearer token.
    """
    serializer_class = UnidadProductoSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return UnidadProducto.objects.select_related(
            'producto', 'producto__marca', 'producto__tipo_producto',
            'cliente_garantia', 'cliente_metodo_aliado', 'ciudad_envio_metodo_aliado',
        ).all()


class UnidadProductoCreateView(CreateAPIView):
    """
    Create a new product unit.

    POST /products/unidades/create/
    Required fields: producto_id, condicion, serial, estado_venta, estado_producto, precio.
    Requires JWT authentication via Bearer token.
    """
    serializer_class = UnidadProductoCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        unidad = serializer.save()

        return Response({
            'message': 'Product unit created successfully',
            'unidad': UnidadProductoSerializer(
                UnidadProducto.objects.select_related(
                    'producto', 'producto__marca'
                ).get(pk=unidad.pk)
            ).data,
        }, status=status.HTTP_201_CREATED)


class UnidadProductoUpdateView(UpdateAPIView):
    """
    Update an existing product unit.

    PATCH/PUT /products/unidades/update/<pk>/
    All fields are optional (partial updates). Serial, condicion, and precio are editable.
    Requires JWT authentication via Bearer token.
    """
    queryset = UnidadProducto.objects.select_related(
        'producto', 'producto__marca'
    ).all()
    serializer_class = UnidadProductoUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        unidad = serializer.save()

        return Response({
            'message': 'Product unit updated successfully',
            'unidad': UnidadProductoSerializer(
                UnidadProducto.objects.select_related(
                    'producto', 'producto__marca'
                ).get(pk=unidad.pk)
            ).data,
        }, status=status.HTTP_200_OK)


class UnidadProductoActivateView(APIView):
    """
    Activate a product unit.

    POST /products/unidades/activate/<pk>/
    Sets active=True.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.active:
            return Response(
                {'message': 'Product unit is already active'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidad.active = True
        unidad.save()

        return Response({
            'message': 'Product unit activated successfully',
            'unidad': UnidadProductoSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


class UnidadProductoDeactivateView(APIView):
    """
    Deactivate a product unit.

    POST /products/unidades/deactivate/<pk>/
    Sets active=False.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if not unidad.active:
            return Response(
                {'message': 'Product unit is already inactive'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidad.active = False
        unidad.save()

        return Response({
            'message': 'Product unit deactivated successfully',
            'unidad': UnidadProductoSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Repair pipeline views
# ---------------------------------------------------------------------------

REPAIR_STATES = ('por_reparar', 'en_reparacion')


def _derive_origen(unidad):
    """Return ('stock'|'venta'|'separacion'|'metodo_aliado', related_object_or_None)."""
    item = unidad.items_venta.filter(active=True).order_by('-id').first()
    if item:
        return 'venta', item
    sep = unidad.separaciones.filter(active=True).exclude(estado='cancelada').order_by('-id').first()
    if sep:
        return 'separacion', sep
    if unidad.cliente_metodo_aliado_id and not unidad.fecha_entrega_metodo_aliado:
        return 'metodo_aliado', unidad.cliente_metodo_aliado
    return 'stock', None


class ReparacionesListView(ListAPIView):
    """
    GET /products/reparaciones/list/
    Lists units currently in the repair pipeline (por_reparar | en_reparacion).
    """
    serializer_class = UnidadReparacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            UnidadProducto.objects
            .filter(estado_producto__in=REPAIR_STATES, active=True)
            .select_related('producto', 'producto__marca')
            .prefetch_related('items_venta__venta__cliente', 'separaciones__cliente')
            .order_by('-fecha_reporte_dano', '-id')
        )


class ReportarDanoView(APIView):
    """
    POST /products/unidades/<pk>/reportar-dano/
    Body: { "descripcion_dano": "..." }
    Marks the unit as damaged and places it in the repair pipeline. If the unit
    belongs to an active sale, the parent Venta is sent back to 'por_entregar'.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.estado_producto in REPAIR_STATES:
            return Response(
                {'error': 'Esta unidad ya está en el flujo de reparación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        origen, related = _derive_origen(unidad)

        unidad.estado_venta = 'danado'
        unidad.estado_producto = 'por_reparar'
        unidad.descripcion_dano = request.data.get('descripcion_dano', '') or ''
        unidad.fecha_reporte_dano = timezone.now()
        unidad.usuario_ultima_modificacion = request.user
        unidad.save()

        if origen == 'venta' and related is not None:
            venta = related.venta
            if venta.estado_entrega != 'por_entregar':
                venta.estado_entrega = 'por_entregar'
                venta.fecha_entrega = None
                venta.usuario_ultima_modificacion = request.user
                venta.save()

        return Response({
            'message': 'Unidad reportada como dañada',
            'unidad': UnidadReparacionSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


class IniciarReparacionView(APIView):
    """
    POST /products/unidades/<pk>/iniciar-reparacion/
    Moves the unit from por_reparar to en_reparacion.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.estado_producto != 'por_reparar':
            return Response(
                {'error': 'Solo se puede iniciar la reparación de unidades en estado "por_reparar".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidad.estado_producto = 'en_reparacion'
        unidad.usuario_ultima_modificacion = request.user
        unidad.save()

        return Response({
            'message': 'Reparación iniciada',
            'unidad': UnidadReparacionSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


class CompletarReparacionView(APIView):
    """
    POST /products/unidades/<pk>/completar-reparacion/
    Restores unit state based on the derived origin (stock/venta/separacion).
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.estado_producto not in REPAIR_STATES:
            return Response(
                {'error': 'Solo se pueden completar unidades en "por_reparar" o "en_reparacion".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        origen, _ = _derive_origen(unidad)

        if origen == 'venta':
            unidad.estado_venta = 'vendido'
            unidad.estado_producto = 'por_entregar'
        elif origen == 'separacion':
            unidad.estado_venta = 'separado'
            unidad.estado_producto = 'en_stock'
        elif origen == 'metodo_aliado':
            unidad.estado_venta = 'solicitud_metodo_aliado'
            unidad.estado_producto = 'en_stock'
        else:
            unidad.estado_venta = 'sin_vender'
            unidad.estado_producto = 'en_stock'

        unidad.descripcion_dano = ''
        unidad.fecha_reporte_dano = None
        unidad.usuario_ultima_modificacion = request.user
        unidad.save()

        return Response({
            'message': 'Reparación completada',
            'origen': origen,
            'unidad': UnidadReparacionSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Método Aliado Views
# ---------------------------------------------------------------------------

class MetodoAliadoListView(ListAPIView):
    """
    GET /products/metodo-aliado/list/
    Lists units currently in the método aliado workflow (not yet delivered).
    """
    serializer_class = UnidadProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            UnidadProducto.objects
            .filter(estado_venta='solicitud_metodo_aliado', active=True)
            .select_related(
                'producto', 'producto__marca', 'producto__tipo_producto',
                'cliente_metodo_aliado', 'ciudad_envio_metodo_aliado',
            )
            .order_by('-fecha_solicitud_metodo_aliado', '-id')
        )


class MarcarEnviadaMetodoAliadoView(APIView):
    """
    POST /products/unidades/<pk>/metodo-aliado/marcar-enviada/
    Body: { "numero_guia_metodo_aliado": "...", "transportadora_metodo_aliado": "..." }
    Records shipment of a método aliado unit — stamps fecha_envio_metodo_aliado
    and optionally updates tracking data.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.estado_venta != 'solicitud_metodo_aliado':
            return Response(
                {'error': 'Esta unidad no está en el flujo de método aliado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        numero_guia = request.data.get('numero_guia_metodo_aliado')
        transportadora = request.data.get('transportadora_metodo_aliado')
        if numero_guia is not None:
            unidad.numero_guia_metodo_aliado = numero_guia
        if transportadora is not None:
            unidad.transportadora_metodo_aliado = transportadora

        unidad.fecha_envio_metodo_aliado = timezone.now()
        unidad.usuario_ultima_modificacion = request.user
        unidad.save()

        return Response({
            'message': 'Unidad marcada como enviada',
            'unidad': UnidadProductoSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


class MarcarEntregadaMetodoAliadoView(APIView):
    """
    POST /products/unidades/<pk>/metodo-aliado/marcar-entregada/
    Finalizes a método aliado delivery — stamps fecha_entrega and sets the
    unit to estado_producto=entregado.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.estado_venta != 'solicitud_metodo_aliado':
            return Response(
                {'error': 'Esta unidad no está en el flujo de método aliado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidad.estado_producto = 'entregado'
        unidad.fecha_entrega_metodo_aliado = timezone.now()
        unidad.usuario_ultima_modificacion = request.user
        unidad.save()

        return Response({
            'message': 'Entrega registrada',
            'unidad': UnidadProductoSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


class CancelarMetodoAliadoView(APIView):
    """
    POST /products/unidades/<pk>/metodo-aliado/cancelar/
    Reverts a método aliado request — returns the unit to sin_vender / en_stock
    and clears all método aliado fields.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        unidad = get_object_or_404(UnidadProducto, pk=pk)

        if unidad.estado_venta != 'solicitud_metodo_aliado':
            return Response(
                {'error': 'Esta unidad no está en el flujo de método aliado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        unidad.estado_venta = 'sin_vender'
        unidad.estado_producto = 'en_stock'
        unidad.cliente_metodo_aliado = None
        unidad.ciudad_envio_metodo_aliado = None
        unidad.fecha_solicitud_metodo_aliado = None
        unidad.fecha_envio_metodo_aliado = None
        unidad.fecha_entrega_metodo_aliado = None
        unidad.numero_guia_metodo_aliado = ''
        unidad.transportadora_metodo_aliado = ''
        unidad.notas_metodo_aliado = ''
        unidad.usuario_ultima_modificacion = request.user
        unidad.save()

        return Response({
            'message': 'Solicitud de método aliado cancelada',
            'unidad': UnidadProductoSerializer(unidad).data,
        }, status=status.HTTP_200_OK)


# ============================================================================
# Bulk product upload (cargue masivo) — template download + dry-run preview +
# commit. See products/services/bulk_upload.py for the parsing/validation
# logic; the views are thin wrappers around it.
# ============================================================================
from django.http import HttpResponse
from io import BytesIO as _BytesIO
from .services.bulk_upload import build_template_workbook, parse_and_validate


class PlantillaCargueMasivoView(APIView):
    """
    GET /products/cargue-masivo/plantilla/<int:tipo_producto_id>/
    Returns an .xlsx template with one column per CampoProducto associated to
    the given TipoProducto. The user fills it in and uploads it back via
    POST /products/cargue-masivo/.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, tipo_producto_id):
        tipo = get_object_or_404(TipoProducto, pk=tipo_producto_id)
        wb = build_template_workbook(tipo)
        buffer = _BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"Plantilla_{tipo.nombre.replace(chr(32), chr(95))}.xlsx"
        response = HttpResponse(
            buffer.read(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        return response


class CargueMasivoView(APIView):
    """
    POST /products/cargue-masivo/
    multipart/form-data: tipo_producto (id), archivo (xlsx), dry_run (bool).
    Default dry_run=true. Returns the preview dict with creados/ignorados/fallidos.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tipo_producto_id = request.data.get("tipo_producto")
        archivo = request.FILES.get("archivo")
        dry_run_raw = str(request.data.get("dry_run", "true")).strip().lower()
        dry_run = dry_run_raw not in ("false", "0", "no")

        if not tipo_producto_id:
            return Response(
                {"error": "tipo_producto es obligatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not archivo:
            return Response(
                {"error": "archivo es obligatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tipo = get_object_or_404(TipoProducto, pk=tipo_producto_id)
        result = parse_and_validate(tipo, archivo, dry_run=dry_run, usuario=request.user)
        return Response(result, status=status.HTTP_200_OK)



class ConfirmarCargueMasivoView(APIView):
    """
    POST /products/cargue-masivo/confirmar/
    Body JSON: { "tipo_producto": <id>, "rows": [{ "data": {...}, "fila": n }, ...] }
    Persists each row after re-validation. Returns a dict with creados/ignorados/fallidos
    where creados include the new producto id and the marca name.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tipo_producto_id = request.data.get("tipo_producto")
        rows = request.data.get("rows") or []

        if not tipo_producto_id:
            return Response(
                {"error": "tipo_producto es obligatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(rows, list):
            return Response(
                {"error": "rows debe ser una lista"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tipo = get_object_or_404(TipoProducto, pk=tipo_producto_id)
        from .services.bulk_upload import confirm_edited_rows
        result = confirm_edited_rows(tipo, rows, usuario=request.user)
        return Response(result, status=status.HTTP_200_OK)


class ProductoUploadImagenesView(APIView):
    """
    POST /products/productos/<int:pk>/imagenes/upload/
    multipart/form-data with `image_0`, `image_1`, ... up to 10 files. Caps at
    10 total images per producto (existing + new). Returns the producto with
    its updated imagenes list.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        from .models import ImagenProducto
        from .serializers import ImagenProductoSerializer

        producto = get_object_or_404(Producto, pk=pk)

        MAX_IMAGES = 10
        current_count = producto.imagenes.count()
        remaining = MAX_IMAGES - current_count

        if remaining <= 0:
            return Response(
                {"error": f"Este producto ya tiene {MAX_IMAGES} imágenes (máximo)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        for i in range(MAX_IMAGES):
            img_file = request.FILES.get(f"image_{i}")
            if not img_file:
                continue
            if len(created) >= remaining:
                break
            imagen = ImagenProducto.objects.create(
                producto=producto,
                url=img_file,
                orden=current_count + len(created),
            )
            created.append(imagen)

        return Response(
            {
                "message": f"{len(created)} imagen{'es' if len(created) != 1 else ''} subida{'s' if len(created) != 1 else ''}",
                "imagenes_count": producto.imagenes.count(),
                "imagenes": ImagenProductoSerializer(
                    producto.imagenes.all(), many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )
