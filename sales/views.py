import io
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Invoice, Cliente, SolicitudBajoPedido, Separacion, Venta, ItemVenta, Departamento, Ciudad
from .serializers import (
    InvoiceSerializer, InvoiceUpdateSerializer, ClienteSerializer, ClienteCreateSerializer,
    ClienteUpdateSerializer, SolicitudBajoPedidoSerializer, SolicitudBajoPedidoCreateSerializer,
    SolicitudBajoPedidoUpdateSerializer, SeparacionSerializer, SeparacionCreateSerializer,
    SeparacionUpdateSerializer, DepartamentoSerializer, CiudadSerializer, CiudadByCiudadDepartamentoSerializer,
    VentaSerializer, VentaCreateSerializer, VentaUpdateSerializer, ItemVentaSerializer, ItemVentaCreateSerializer,
)
from .services.document_service import generate_invoice_document
from .services.storage_service import save_invoice, get_invoice_bytes
from .services.email_service import send_invoice_email


# ---------------------------------------------------------------------------
# Cliente Views
# ---------------------------------------------------------------------------

class ClienteListView(ListAPIView):
    """
    View to list all customers.
    GET: Returns a list of all customers with their information.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]


class ClienteCreateView(CreateAPIView):
    """
    View to create a new customer.
    POST: Creates a new customer with the provided data.
    """
    serializer_class = ClienteCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cliente = serializer.save()

        return Response({
            'message': 'Customer created successfully',
            'cliente': ClienteSerializer(cliente).data
        }, status=status.HTTP_201_CREATED)


class ClienteUpdateView(UpdateAPIView):
    """
    View to update customer information.
    PATCH/PUT: Updates customer information.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Customer updated successfully',
            'cliente': ClienteSerializer(instance).data
        }, status=status.HTTP_200_OK)


class ClienteDetailView(RetrieveAPIView):
    """
    View to retrieve customer details.
    GET: Returns detailed information about a specific customer.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


class ClienteActivateView(APIView):
    """
    View to activate a customer.
    POST: Sets active=True for the specified customer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)

        if cliente.active:
            return Response({
                'message': 'Customer is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        cliente.active = True
        cliente.save()

        return Response({
            'message': 'Customer activated successfully',
            'cliente': ClienteSerializer(cliente).data
        }, status=status.HTTP_200_OK)


class ClienteDeactivateView(APIView):
    """
    View to deactivate a customer.
    POST: Sets active=False for the specified customer.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)

        if not cliente.active:
            return Response({
                'message': 'Customer is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        cliente.active = False
        cliente.save()

        return Response({
            'message': 'Customer deactivated successfully',
            'cliente': ClienteSerializer(cliente).data
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# SolicitudBajoPedido Views
# ---------------------------------------------------------------------------

class SolicitudBajoPedidoListView(ListAPIView):
    """
    View to list all back orders.
    GET: Returns a list of all back orders with their information.
    """
    queryset = SolicitudBajoPedido.objects.all()
    serializer_class = SolicitudBajoPedidoSerializer
    permission_classes = [IsAuthenticated]


class SolicitudBajoPedidoCreateView(CreateAPIView):
    """
    View to create a new back order.
    POST: Creates a new back order with the provided data.
    """
    serializer_class = SolicitudBajoPedidoCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pbp = serializer.save()

        return Response({
            'message': 'Back order created successfully',
            'producto_bajo_pedido': SolicitudBajoPedidoSerializer(pbp).data
        }, status=status.HTTP_201_CREATED)


class SolicitudBajoPedidoUpdateView(UpdateAPIView):
    """
    View to update back order information.
    PATCH/PUT: Updates back order information.
    """
    queryset = SolicitudBajoPedido.objects.all()
    serializer_class = SolicitudBajoPedidoUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Back order updated successfully',
            'producto_bajo_pedido': SolicitudBajoPedidoSerializer(instance).data
        }, status=status.HTTP_200_OK)


class SolicitudBajoPedidoDetailView(RetrieveAPIView):
    """
    View to retrieve back order details.
    GET: Returns detailed information about a specific back order.
    """
    queryset = SolicitudBajoPedido.objects.all()
    serializer_class = SolicitudBajoPedidoSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


class SolicitudBajoPedidoActivateView(APIView):
    """
    View to activate a back order.
    POST: Sets active=True for the specified back order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        pbp = get_object_or_404(SolicitudBajoPedido, pk=pk)

        if pbp.active:
            return Response({
                'message': 'Back order is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        pbp.active = True
        pbp.save()

        return Response({
            'message': 'Back order activated successfully',
            'producto_bajo_pedido': SolicitudBajoPedidoSerializer(pbp).data
        }, status=status.HTTP_200_OK)


class SolicitudBajoPedidoDeactivateView(APIView):
    """
    View to deactivate a back order.
    POST: Sets active=False for the specified back order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        pbp = get_object_or_404(SolicitudBajoPedido, pk=pk)

        if not pbp.active:
            return Response({
                'message': 'Back order is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        pbp.active = False
        pbp.save()

        return Response({
            'message': 'Back order deactivated successfully',
            'producto_bajo_pedido': SolicitudBajoPedidoSerializer(pbp).data
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Separacion Views
# ---------------------------------------------------------------------------

class SeparacionListView(ListAPIView):
    """
    View to list all holds/separations.
    GET: Returns a list of all holds with their information.
    """
    queryset = Separacion.objects.select_related('unidad_producto__producto', 'cliente').all()
    serializer_class = SeparacionSerializer
    permission_classes = [IsAuthenticated]


class SeparacionCreateView(CreateAPIView):
    """
    View to create a new hold/separation.
    POST: Creates a new hold with the provided data.
    """
    serializer_class = SeparacionCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sep = serializer.save()

        return Response({
            'message': 'Hold created successfully',
            'separacion': SeparacionSerializer(sep).data
        }, status=status.HTTP_201_CREATED)


class SeparacionUpdateView(UpdateAPIView):
    """
    View to update hold/separation information.
    PATCH/PUT: Updates hold information.
    """
    queryset = Separacion.objects.all()
    serializer_class = SeparacionUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': 'Hold updated successfully',
            'separacion': SeparacionSerializer(instance).data
        }, status=status.HTTP_200_OK)


class SeparacionDetailView(RetrieveAPIView):
    """
    View to retrieve hold/separation details.
    GET: Returns detailed information about a specific hold.
    """
    queryset = Separacion.objects.all()
    serializer_class = SeparacionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


class SeparacionActivateView(APIView):
    """
    View to activate a hold/separation.
    POST: Sets active=True for the specified hold.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sep = get_object_or_404(Separacion, pk=pk)

        if sep.active:
            return Response({
                'message': 'Hold is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        sep.active = True
        sep.save()

        return Response({
            'message': 'Hold activated successfully',
            'separacion': SeparacionSerializer(sep).data
        }, status=status.HTTP_200_OK)


class SeparacionDeactivateView(APIView):
    """
    View to deactivate a hold/separation.
    POST: Sets active=False and restores unit estado_venta to 'sin_vender'.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sep = get_object_or_404(Separacion, pk=pk)

        if not sep.active:
            return Response({
                'message': 'Hold is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        sep.active = False
        sep.save()

        # Restore unit estado_venta
        unidad = sep.unidad_producto
        unidad.estado_venta = 'sin_vender'
        unidad.save(update_fields=['estado_venta'])

        return Response({
            'message': 'Hold deactivated successfully',
            'separacion': SeparacionSerializer(sep).data
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Departamento & Ciudad Views
# ---------------------------------------------------------------------------

class DepartamentoListView(ListAPIView):
    """List all departments."""
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    permission_classes = [IsAuthenticated]


class CiudadListView(ListAPIView):
    """List all cities, optionally filtered by department."""
    serializer_class = CiudadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Ciudad.objects.all()
        departamento_id = self.request.query_params.get('departamento_id')
        if departamento_id:
            queryset = queryset.filter(departamento_id=departamento_id)
        return queryset


# ---------------------------------------------------------------------------
# Venta Views
# ---------------------------------------------------------------------------

class VentaListView(ListAPIView):
    """List all sales."""
    queryset = Venta.objects.prefetch_related('items')
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]


class VentaCreateView(CreateAPIView):
    """Create a new sale with items."""
    serializer_class = VentaCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        venta = serializer.save()

        return Response({
            'message': 'Sale created successfully',
            'venta': VentaSerializer(venta).data
        }, status=status.HTTP_201_CREATED)


class VentaDetailView(RetrieveAPIView):
    """Get sale details with items."""
    queryset = Venta.objects.prefetch_related('items')
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


class VentaUpdateView(UpdateAPIView):
    """Update a sale's cliente and notas."""
    queryset = Venta.objects.all()
    serializer_class = VentaUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'message': 'Sale updated successfully',
            'venta': VentaSerializer(instance).data
        }, status=status.HTTP_200_OK)


class VentaDeleteView(APIView):
    """Hard delete a sale and restore unit estado_venta to 'sin_vender'."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)
        for item in venta.items.select_related('unidad_producto').all():
            unidad = item.unidad_producto
            unidad.estado_venta = 'sin_vender'
            unidad.save(update_fields=['estado_venta'])
        venta.delete()
        return Response({'message': 'Sale deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


class VentaDeactivateView(APIView):
    """
    Deactivate a sale and restore unit estado_venta to 'sin_vender'.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        venta = get_object_or_404(Venta, pk=pk)

        if not venta.active:
            return Response({
                'message': 'Sale is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        venta.active = False
        venta.save()

        # Restore estado_venta for all units in this sale
        for item in venta.items.select_related('unidad_producto').all():
            unidad = item.unidad_producto
            unidad.estado_venta = 'sin_vender'
            unidad.save(update_fields=['estado_venta'])

        return Response({
            'message': 'Sale deactivated successfully',
            'venta': VentaSerializer(venta).data
        }, status=status.HTTP_200_OK)


class InvoiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.select_related('cliente', 'venta', 'separacion').all()
        serializer = InvoiceSerializer(invoices, many=True)
        return Response({'message': 'Facturas obtenidas exitosamente.', 'invoices': serializer.data})


class InvoiceCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data

        # Auto-infer item (tipo_producto) from serial_item if not provided
        if not validated.get('item'):
            serial_raw = validated.get('serial_item', '').strip()
            first_serial = serial_raw.split(',')[0].strip()
            if first_serial:
                try:
                    from products.models import UnidadProducto
                    unidad = UnidadProducto.objects.select_related(
                        'producto__tipo_producto'
                    ).get(serial=first_serial)
                    validated['item'] = unidad.producto.tipo_producto.nombre
                except UnidadProducto.DoesNotExist:
                    return Response(
                        {'serial_item': 'No se encontró una unidad con el serial proporcionado.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        # Pre-compute bill_id to check for duplicates before saving
        date_str = validated['due_date'].strftime('%Y%m%d')
        serial_clean = validated['serial_item'].upper().replace(' ', '')
        bill_id = f"{date_str}-{serial_clean}"

        if Invoice.objects.filter(bill_id=bill_id).exists():
            return Response(
                {'error': 'An invoice with this bill_id already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build a temporary Invoice object (unsaved) for document generation
        temp_invoice = Invoice(**validated)
        temp_invoice.bill_id = bill_id

        # 1. Generate .docx document
        try:
            doc_buffer = generate_invoice_document(temp_invoice)
        except Exception as exc:
            return Response(
                {'error': f'Error al generar el documento: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        doc_bytes = doc_buffer.read()

        # 2. Save file (local in DEBUG, R2 in production) — if this fails, do NOT save the record
        try:
            file_key = save_invoice(io.BytesIO(doc_bytes), bill_id)
        except Exception as exc:
            return Response(
                {'error': f'Error al guardar el archivo: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 3. Send email (failure is non-blocking)
        email_ok = send_invoice_email(temp_invoice, doc_bytes)

        # 4. Save to DB
        invoice = Invoice(**validated)
        invoice.file_path = file_key
        invoice.email_sent = email_ok
        invoice.save()

        response_serializer = InvoiceSerializer(invoice)
        return Response(
            {'message': 'Factura creada exitosamente.', 'invoice': response_serializer.data},
            status=status.HTTP_201_CREATED,
        )


class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            invoice = Invoice.objects.select_related('cliente', 'venta', 'separacion').get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = InvoiceSerializer(invoice)
        return Response({'message': 'Factura obtenida exitosamente.', 'invoice': serializer.data})


class InvoiceUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        try:
            invoice = Invoice.objects.select_related('cliente', 'venta', 'separacion').get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = InvoiceUpdateSerializer(invoice, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        response_serializer = InvoiceSerializer(invoice)
        return Response({'message': 'Factura actualizada exitosamente.', 'invoice': response_serializer.data})


class InvoiceDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        invoice.delete()
        return Response({'message': 'Factura eliminada exitosamente.'}, status=status.HTTP_204_NO_CONTENT)


class InvoiceDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            invoice = Invoice.objects.select_related('cliente', 'venta', 'separacion').get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if not invoice.file_path:
            return Response({'error': 'El archivo de la factura no está disponible.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_bytes = get_invoice_bytes(invoice.file_path)
        except Exception as exc:
            return Response(
                {'error': f'Error al obtener el archivo: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(
            file_bytes,
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="factura_{invoice.bill_id}.docx"'
        return response


class InvoiceResendEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            invoice = Invoice.objects.select_related('cliente', 'venta', 'separacion').get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({'error': 'Factura no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        if not invoice.file_path:
            return Response({'error': 'El archivo de la factura no está disponible.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_bytes = get_invoice_bytes(invoice.file_path)
        except Exception as exc:
            return Response(
                {'error': f'Error al obtener el archivo: {str(exc)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        email_ok = send_invoice_email(invoice, file_bytes)
        if email_ok:
            invoice.email_sent = True
            invoice.save(update_fields=['email_sent'])
            return Response({'message': 'Correo reenviado exitosamente.'})
        else:
            return Response(
                {'error': 'No se pudo enviar el correo. Intenta nuevamente.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InvoiceParseNaturalLanguageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {'message': 'Funcionalidad no implementada aún.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
