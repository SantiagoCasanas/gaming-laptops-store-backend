from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import OrdenCompra
from .serializers import OrdenCompraSerializer, OrdenCompraCreateSerializer, OrdenCompraUpdateSerializer


class OrdenCompraListView(ListAPIView):
    """
    View to list all purchase orders.
    GET: Returns a list of all purchase orders with their information.
    """
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrdenCompra.objects.select_related(
            'producto', 'producto__marca', 'proveedor', 'unidad_producto'
        ).all()


class OrdenCompraCreateView(CreateAPIView):
    """
    View to create a new purchase order.
    POST: Creates a new purchase order with the provided data.
    """
    serializer_class = OrdenCompraCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        orden = serializer.save()

        return Response({
            'message': 'Purchase order created successfully',
            'orden_compra': OrdenCompraSerializer(
                OrdenCompra.objects.select_related(
                    'producto', 'producto__marca', 'proveedor', 'unidad_producto'
                ).get(pk=orden.pk)
            ).data
        }, status=status.HTTP_201_CREATED)


class OrdenCompraUpdateView(UpdateAPIView):
    """
    View to update purchase order information.
    PATCH/PUT: Updates purchase order information.
    """
    serializer_class = OrdenCompraUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return OrdenCompra.objects.select_related(
            'producto', 'producto__marca', 'proveedor', 'unidad_producto'
        ).all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        return Response({
            'message': 'Purchase order updated successfully',
            'orden_compra': OrdenCompraSerializer(
                OrdenCompra.objects.select_related(
                    'producto', 'producto__marca', 'proveedor', 'unidad_producto'
                ).get(pk=updated_instance.pk)
            ).data
        }, status=status.HTTP_200_OK)


class OrdenCompraDetailView(RetrieveAPIView):
    """
    View to retrieve purchase order details.
    GET: Returns detailed information about a specific purchase order.
    """
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return OrdenCompra.objects.select_related(
            'producto', 'producto__marca', 'proveedor', 'unidad_producto'
        ).all()


class OrdenCompraActivateView(APIView):
    """
    View to activate a purchase order.
    POST: Sets active=True for the specified purchase order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)

        if orden.active:
            return Response({
                'message': 'Purchase order is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        orden.active = True
        orden.save()

        return Response({
            'message': 'Purchase order activated successfully',
            'orden_compra': OrdenCompraSerializer(orden).data
        }, status=status.HTTP_200_OK)


class OrdenCompraDeactivateView(APIView):
    """
    View to deactivate a purchase order.
    POST: Sets active=False for the specified purchase order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)

        if not orden.active:
            return Response({
                'message': 'Purchase order is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        orden.active = False
        orden.save()

        return Response({
            'message': 'Purchase order deactivated successfully',
            'orden_compra': OrdenCompraSerializer(orden).data
        }, status=status.HTTP_200_OK)


# ============================================================================
# Importaciones — bulk update of OrdenCompra logistic state and costo_importacion
# from an Excel file. Mirrors the products bulk upload UX: download template,
# upload + dry-run preview, then commit. See
# purchases/services/importacion_carga.py for the parsing/validation logic.
# ============================================================================
from django.http import HttpResponse
from io import BytesIO as _BytesIO
from .services.importacion_carga import build_template_workbook, parse_and_validate


class PlantillaImportacionView(APIView):
    """
    GET /purchases/importaciones/plantilla/
    Returns the Excel template with the columns required to upload an
    importacion (numero_tracking, descripcion, valor_importacion_cop).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wb = build_template_workbook()
        buffer = _BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.read(),
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = 'attachment; filename="Plantilla_Importaciones.xlsx"'
        return response


class CargarImportacionView(APIView):
    """
    POST /purchases/importaciones/cargar/
    multipart/form-data: archivo (xlsx), dry_run (bool, default true). Returns
    the preview dict with `matched`, `no_mapeado`, `fallidos`.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        archivo = request.FILES.get("archivo")
        dry_run_raw = str(request.data.get("dry_run", "true")).strip().lower()
        dry_run = dry_run_raw not in ("false", "0", "no")

        if not archivo:
            return Response(
                {"error": "archivo es obligatorio"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = parse_and_validate(archivo, dry_run=dry_run, usuario=request.user)
        return Response(result, status=status.HTTP_200_OK)
