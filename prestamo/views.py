"""
Vistas DRF de la app `prestamo`. Prefijo: /api/prestamo/.

Todas requieren autenticación. Ambos usuarios (dueño y amigo) pueden registrar
y editar. Cada mutación de Movimiento dispara `services.recalcular()` y deja
rastro en `AuditLog`.
"""

import uuid

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import AuditLog, Movimiento
from .serializers import (
    AuditLogSerializer,
    ConfiguracionSerializer,
    MovimientoSerializer,
    MovimientoWriteSerializer,
)


class ResumenView(APIView):
    """GET /resumen/ — saldos actuales, próxima cuota, próximo 2%, mes en curso."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"resumen": services.get_resumen()})


class ProyeccionView(APIView):
    """GET /proyeccion/ — tabla mes a mes hasta el plazo."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"proyeccion": services.get_proyeccion()})


class MovimientoListCreateView(APIView):
    """GET /movimientos/ (lista) y POST /movimientos/ (crear)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Movimiento.objects.all()
        tipo = request.query_params.get("tipo")
        tramo = request.query_params.get("tramo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        if tramo:
            qs = qs.filter(tramo=tramo)
        return Response({"movimientos": MovimientoSerializer(qs, many=True).data})

    def post(self, request):
        serializer = MovimientoWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mov = serializer.save(autor=request.user)

        services.registrar_auditoria(
            request.user, AuditLog.CREAR, mov,
            antes=None, despues=services.movimiento_snapshot(mov),
        )
        services.recalcular()

        return Response(
            {"message": "Movimiento creado", "movimiento": MovimientoSerializer(mov).data},
            status=status.HTTP_201_CREATED,
        )


class MovimientoDetailView(APIView):
    """GET / PATCH / DELETE /movimientos/{id}/."""

    permission_classes = [IsAuthenticated]

    def _get_object(self, pk):
        return Movimiento.objects.filter(pk=pk).first()

    def get(self, request, pk):
        mov = self._get_object(pk)
        if mov is None:
            return Response({"message": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"movimiento": MovimientoSerializer(mov).data})

    def patch(self, request, pk):
        mov = self._get_object(pk)
        if mov is None:
            return Response({"message": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)

        antes = services.movimiento_snapshot(mov)
        serializer = MovimientoWriteSerializer(mov, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        mov = serializer.save()

        services.registrar_auditoria(
            request.user, AuditLog.EDITAR, mov,
            antes=antes, despues=services.movimiento_snapshot(mov),
        )
        services.recalcular()

        return Response(
            {"message": "Movimiento actualizado", "movimiento": MovimientoSerializer(mov).data}
        )

    def delete(self, request, pk):
        mov = self._get_object(pk)
        if mov is None:
            return Response({"message": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)

        antes = services.movimiento_snapshot(mov)
        services.registrar_auditoria(
            request.user, AuditLog.BORRAR, mov, antes=antes, despues=None,
        )
        mov.delete()
        services.recalcular()

        return Response({"message": "Movimiento eliminado"}, status=status.HTTP_200_OK)


class PagoRegularView(APIView):
    """GET /pago-regular/  -> preview (montos del corte vigente).
    POST /pago-regular/ -> registra de una sola vez las 3 líneas del día 11.

    Acepta `mes` opcional (query param en GET, body en POST); por defecto usa
    el período de cobro vigente."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        mes = request.query_params.get("mes")
        preview = services.preview_pago_regular(mes=int(mes) if mes else None)
        return Response({"pago_regular": preview})

    def post(self, request):
        mes = request.data.get("mes")
        comprobante_url = request.data.get("comprobante_url", "") or ""
        try:
            result = services.registrar_pago_regular(
                request.user,
                mes=int(mes) if mes else None,
                comprobante_url=comprobante_url,
            )
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Pago regular registrado",
                "mes": result["mes"],
                "fecha": result["fecha"],
                "movimientos": MovimientoSerializer(result["movimientos"], many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ComprobanteUploadView(APIView):
    """POST /comprobantes/ — sube un comprobante a R2 (o media en dev) y
    devuelve la URL pública."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archivo = request.FILES.get("archivo") or request.FILES.get("file")
        if archivo is None:
            return Response(
                {"message": "No se envió ningún archivo (campo 'archivo')."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ext = (archivo.name.rsplit(".", 1)[-1] if "." in archivo.name else "bin")
        nombre = f"prestamo/comprobantes/{uuid.uuid4().hex}.{ext}"
        ruta = default_storage.save(nombre, ContentFile(archivo.read()))
        url = default_storage.url(ruta)
        if request and url.startswith("/"):
            url = request.build_absolute_uri(url)

        return Response(
            {"message": "Comprobante subido", "comprobante_url": url},
            status=status.HTTP_201_CREATED,
        )


class AuditoriaListView(APIView):
    """GET /auditoria/ — historial inmutable de cambios."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AuditLog.objects.all()[:500]
        return Response({"auditoria": AuditLogSerializer(qs, many=True).data})


class ConfiguracionView(APIView):
    """GET / PUT /configuracion/ — leer y editar los parámetros del préstamo."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = services.get_config()
        if config is None:
            return Response({"configuracion": None})
        return Response({"configuracion": ConfiguracionSerializer(config).data})

    def put(self, request):
        config = services.get_config()
        if config is None:
            return Response(
                {"message": "No hay configuración sembrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        antes = ConfiguracionSerializer(config).data
        serializer = ConfiguracionSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        config = serializer.save()

        services.registrar_auditoria(
            request.user, AuditLog.EDITAR, config,
            antes=antes, despues=ConfiguracionSerializer(config).data,
        )
        services.recalcular(config)

        return Response(
            {"message": "Configuración actualizada",
             "configuracion": ConfiguracionSerializer(config).data}
        )
