from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
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
            'producto', 'producto__marca'
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
            'producto', 'producto__marca'
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
