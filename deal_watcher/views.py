"""
Deal Watcher views: admin CRUD + Telegram webhook.

The Telegram webhook receives Update objects, validates the secret in the URL,
and dispatches text commands and callback queries. Everything else is the
standard DRF admin API used by the React frontend.
"""
from __future__ import annotations

import hmac
import logging
from datetime import timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    RetrieveAPIView,
    UpdateAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from deal_watcher.models import (
    MonitoredProduct,
    NotificationPause,
    PriceCheck,
    TelegramSubscriber,
    TrustedSeller,
)
from deal_watcher.serializers import (
    GlobalPauseCreateSerializer,
    GlobalPauseStatusSerializer,
    MonitoredProductCreateSerializer,
    MonitoredProductSerializer,
    MonitoredProductUpdateSerializer,
    NotificationPauseSerializer,
    PriceCheckSerializer,
    TelegramSubscriberSerializer,
    TrustedSellerCreateSerializer,
    TrustedSellerSerializer,
    TrustedSellerUpdateSerializer,
)
from deal_watcher.services import pause_service
from deal_watcher.services.notifiers import telegram as tg

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TrustedSeller CRUD
# ---------------------------------------------------------------------------

class TrustedSellerListView(ListAPIView):
    queryset = TrustedSeller.objects.all()
    serializer_class = TrustedSellerSerializer
    permission_classes = [IsAuthenticated]


class TrustedSellerCreateView(CreateAPIView):
    serializer_class = TrustedSellerCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        seller = serializer.save()
        return Response({
            'message': 'Trusted seller created successfully',
            'trusted_seller': TrustedSellerSerializer(seller).data,
        }, status=status.HTTP_201_CREATED)


class TrustedSellerUpdateView(UpdateAPIView):
    queryset = TrustedSeller.objects.all()
    serializer_class = TrustedSellerUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'message': 'Trusted seller updated successfully',
            'trusted_seller': TrustedSellerSerializer(instance).data,
        }, status=status.HTTP_200_OK)


class TrustedSellerActivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        seller = get_object_or_404(TrustedSeller, pk=pk)
        if seller.active:
            return Response({'message': 'Trusted seller is already active'}, status=status.HTTP_400_BAD_REQUEST)
        seller.active = True
        seller.save()
        return Response({
            'message': 'Trusted seller activated successfully',
            'trusted_seller': TrustedSellerSerializer(seller).data,
        }, status=status.HTTP_200_OK)


class TrustedSellerDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        seller = get_object_or_404(TrustedSeller, pk=pk)
        if not seller.active:
            return Response({'message': 'Trusted seller is already inactive'}, status=status.HTTP_400_BAD_REQUEST)
        seller.active = False
        seller.save()
        return Response({
            'message': 'Trusted seller deactivated successfully',
            'trusted_seller': TrustedSellerSerializer(seller).data,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# MonitoredProduct CRUD
# ---------------------------------------------------------------------------

class MonitoredProductListView(ListAPIView):
    queryset = MonitoredProduct.objects.all().select_related('producto_catalogo')
    serializer_class = MonitoredProductSerializer
    permission_classes = [IsAuthenticated]


class MonitoredProductDetailView(RetrieveAPIView):
    queryset = MonitoredProduct.objects.all().select_related('producto_catalogo')
    serializer_class = MonitoredProductSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'


class MonitoredProductCreateView(CreateAPIView):
    serializer_class = MonitoredProductCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response({
            'message': 'Monitored product created successfully',
            'monitored_product': MonitoredProductSerializer(product).data,
        }, status=status.HTTP_201_CREATED)


class MonitoredProductUpdateView(UpdateAPIView):
    queryset = MonitoredProduct.objects.all()
    serializer_class = MonitoredProductUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'message': 'Monitored product updated successfully',
            'monitored_product': MonitoredProductSerializer(instance).data,
        }, status=status.HTTP_200_OK)


class MonitoredProductActivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(MonitoredProduct, pk=pk)
        if product.active:
            return Response({'message': 'Monitored product is already active'}, status=status.HTTP_400_BAD_REQUEST)
        product.active = True
        product.save()
        return Response({
            'message': 'Monitored product activated successfully',
            'monitored_product': MonitoredProductSerializer(product).data,
        }, status=status.HTTP_200_OK)


class MonitoredProductDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        product = get_object_or_404(MonitoredProduct, pk=pk)
        if not product.active:
            return Response({'message': 'Monitored product is already inactive'}, status=status.HTTP_400_BAD_REQUEST)
        product.active = False
        product.save()
        return Response({
            'message': 'Monitored product deactivated successfully',
            'monitored_product': MonitoredProductSerializer(product).data,
        }, status=status.HTTP_200_OK)


class MonitoredProductHistoryView(ListAPIView):
    """GET /monitored-products/<pk>/history/?limit=200 — newest first."""
    serializer_class = PriceCheckSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        product = get_object_or_404(MonitoredProduct, pk=self.kwargs['pk'])
        qs = PriceCheck.objects.filter(monitored_product=product).order_by('-checked_at')
        try:
            limit = int(self.request.query_params.get('limit', '200'))
        except (TypeError, ValueError):
            limit = 200
        limit = max(1, min(limit, 2000))
        return qs[:limit]


# ---------------------------------------------------------------------------
# Pause endpoints
# ---------------------------------------------------------------------------

class GlobalPauseStatusView(APIView):
    """GET /pauses/global/status/ — current state of the global pause."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pause = pause_service.get_active_global_pause()
        if pause is None:
            payload = {
                'is_paused': False,
                'paused_until': None,
                'reason': '',
                'created_via': '',
            }
        else:
            payload = {
                'is_paused': True,
                'paused_until': pause.paused_until,
                'reason': pause.reason,
                'created_via': pause.created_via,
            }
        return Response(GlobalPauseStatusSerializer(payload).data)


class GlobalPauseCreateView(APIView):
    """POST /pauses/global/create/ — create a global pause."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GlobalPauseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        paused_until = data.get('paused_until')
        if paused_until is None and data.get('duration_minutes'):
            paused_until = timezone.now() + timedelta(minutes=data['duration_minutes'])

        pause = pause_service.create_global_pause(
            paused_until=paused_until,
            reason=data.get('reason', ''),
            created_via=NotificationPause.CREATED_VIA_UI,
        )
        return Response({
            'message': 'Global pause created successfully',
            'pause': NotificationPauseSerializer(pause).data,
        }, status=status.HTTP_201_CREATED)


class GlobalPauseLiftView(APIView):
    """POST /pauses/global/lift/ — deactivate every active global pause."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        n = pause_service.deactivate_active_pauses(scope=NotificationPause.SCOPE_GLOBAL)
        return Response({
            'message': f'Lifted {n} active global pause(s)',
            'lifted': n,
        }, status=status.HTTP_200_OK)


class NotificationPauseListView(ListAPIView):
    """GET /pauses/list/ — recent pauses (any scope)."""
    serializer_class = NotificationPauseSerializer
    permission_classes = [IsAuthenticated]
    queryset = NotificationPause.objects.all().order_by('-created_at')[:50]


# ---------------------------------------------------------------------------
# TelegramSubscriber (read-only listing)
# ---------------------------------------------------------------------------

class TelegramSubscriberListView(ListAPIView):
    queryset = TelegramSubscriber.objects.all()
    serializer_class = TelegramSubscriberSerializer
    permission_classes = [IsAuthenticated]


class TelegramSubscriberDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        sub = get_object_or_404(TelegramSubscriber, pk=pk)
        if not sub.active:
            return Response({'message': 'Subscriber already inactive'}, status=status.HTTP_400_BAD_REQUEST)
        sub.active = False
        sub.save()
        return Response({
            'message': 'Subscriber deactivated successfully',
            'subscriber': TelegramSubscriberSerializer(sub).data,
        }, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

class TelegramWebhookView(APIView):
    """POST /deal-watcher/telegram/webhook/<secret>/"""
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request, secret: str):
        configured = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if not configured:
            logger.error("TELEGRAM_WEBHOOK_SECRET not configured — rejecting webhook")
            return Response({'detail': 'webhook not configured'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if not hmac.compare_digest(secret, configured):
            logger.warning("Telegram webhook called with bad secret")
            return Response({'detail': 'invalid secret'}, status=status.HTTP_403_FORBIDDEN)

        update = request.data or {}
        try:
            if 'callback_query' in update:
                _handle_callback_query(update['callback_query'])
            elif 'message' in update:
                _handle_message(update['message'])
            else:
                logger.debug("Telegram update with no message/callback: %s", list(update.keys()))
        except Exception as exc:
            logger.exception("Error handling Telegram update: %s", exc)
        # Always 200 to stop Telegram from retrying.
        return Response({'ok': True}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

_COMMANDS_HELP = (
    "🤖 <b>Deal Watcher</b>\n"
    "Comandos disponibles:\n"
    "• /start — activar alertas en este chat\n"
    "• /stop — desactivar alertas en este chat\n"
    "• /estado — ver estado de pausas\n"
    "• /reanudar — quitar pausa global"
)


def _handle_message(message: dict) -> None:
    chat = message.get('chat') or {}
    chat_id = str(chat.get('id') or '')
    if not chat_id:
        logger.warning("Telegram message without chat.id: %s", message)
        return

    text = (message.get('text') or '').strip()
    if not text.startswith('/'):
        # Free-form messages: ignore for now.
        return

    # Commands may include a bot mention: '/start@MyBot' → '/start'
    command = text.split()[0].split('@')[0].lower()
    user = message.get('from') or {}
    username = user.get('username') or ''

    if command == '/start':
        _cmd_start(chat_id, username)
    elif command == '/stop':
        _cmd_stop(chat_id)
    elif command == '/estado':
        _cmd_estado(chat_id)
    elif command == '/reanudar':
        _cmd_reanudar(chat_id)
    elif command == '/help':
        tg.send_plain_message(chat_id, _COMMANDS_HELP)
    else:
        tg.send_plain_message(
            chat_id,
            f"Comando no reconocido: <code>{command}</code>\n\n{_COMMANDS_HELP}",
        )


def _cmd_start(chat_id: str, username: str) -> None:
    sub, created = TelegramSubscriber.objects.get_or_create(
        chat_id=chat_id,
        defaults={'telegram_username': username, 'active': True},
    )
    if not created:
        # Refresh username and reactivate if previously stopped.
        sub.telegram_username = username or sub.telegram_username
        sub.active = True
        sub.save(update_fields=['telegram_username', 'active', 'updated_at'])
    tg.send_plain_message(
        chat_id,
        "✅ Listo. Empezarás a recibir alertas de Deal Watcher en este chat.\n\n"
        + _COMMANDS_HELP,
    )


def _cmd_stop(chat_id: str) -> None:
    updated = TelegramSubscriber.objects.filter(chat_id=chat_id, active=True).update(active=False)
    if updated:
        tg.send_plain_message(chat_id, "🛑 Alertas desactivadas en este chat. Usa /start para volver a activarlas.")
    else:
        tg.send_plain_message(chat_id, "Este chat no estaba recibiendo alertas.")


def _cmd_estado(chat_id: str) -> None:
    pause = pause_service.get_active_global_pause()
    if pause is None:
        tg.send_plain_message(chat_id, "🟢 No hay pausa global activa.")
        return
    if pause.paused_until is None:
        tg.send_plain_message(chat_id, "🔴 Pausa global activa: <b>indefinida</b>. Usa /reanudar para levantarla.")
    else:
        until = timezone.localtime(pause.paused_until).strftime('%Y-%m-%d %H:%M')
        tg.send_plain_message(chat_id, f"🔴 Pausa global activa hasta <b>{until}</b>. Usa /reanudar para levantarla.")


def _cmd_reanudar(chat_id: str) -> None:
    n = pause_service.deactivate_active_pauses(scope=NotificationPause.SCOPE_GLOBAL)
    if n:
        tg.send_plain_message(chat_id, f"🟢 Pausa global levantada ({n} registro{'s' if n != 1 else ''} desactivado{'s' if n != 1 else ''}).")
    else:
        tg.send_plain_message(chat_id, "No había pausa global activa.")


# ---------------------------------------------------------------------------
# Callback queries (inline pause buttons)
# ---------------------------------------------------------------------------

def _handle_callback_query(callback: dict) -> None:
    callback_id = callback.get('id') or ''
    data = callback.get('data') or ''
    chat_id = str(((callback.get('message') or {}).get('chat') or {}).get('id') or '')
    user = callback.get('from') or {}
    username = user.get('username') or ''

    if not tg.is_pause_callback(data):
        tg.answer_callback_query(callback_id, text="Acción desconocida")
        return

    try:
        delta = tg.parse_pause_callback(data)
    except ValueError:
        tg.answer_callback_query(callback_id, text="Acción desconocida")
        return

    paused_until = (timezone.now() + delta) if delta is not None else None
    pause_service.create_global_pause(
        paused_until=paused_until,
        reason=f"telegram:{username or chat_id}",
        created_via=NotificationPause.CREATED_VIA_TELEGRAM,
    )

    label = _human_label_for_delta(delta)
    tg.answer_callback_query(callback_id, text=f"⏸ Pausa global activada: {label}")
    if chat_id:
        tg.send_plain_message(chat_id, f"⏸ Pausa global activada: <b>{label}</b>. Usa /reanudar para levantarla.")


def _human_label_for_delta(delta: timedelta | None) -> str:
    if delta is None:
        return 'indefinida'
    total_seconds = int(delta.total_seconds())
    if total_seconds < 3600:
        return f"{total_seconds // 60} min"
    if total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} h"
    days = total_seconds // 86400
    return f"{days} día{'s' if days != 1 else ''}"
