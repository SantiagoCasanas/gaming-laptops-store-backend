import io
from django.http import HttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Invoice
from .serializers import InvoiceSerializer, InvoiceUpdateSerializer
from .services.document_service import generate_invoice_document
from .services.storage_service import save_invoice, get_invoice_bytes
from .services.email_service import send_invoice_email


class InvoiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        invoices = Invoice.objects.all()
        serializer = InvoiceSerializer(invoices, many=True)
        return Response({'message': 'Facturas obtenidas exitosamente.', 'invoices': serializer.data})


class InvoiceCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = InvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data

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
            invoice = Invoice.objects.get(pk=pk)
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
            invoice = Invoice.objects.get(pk=pk)
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
            invoice = Invoice.objects.get(pk=pk)
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
            invoice = Invoice.objects.get(pk=pk)
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
