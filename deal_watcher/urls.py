from django.urls import path

from .views import (
    GlobalPauseCreateView,
    GlobalPauseLiftView,
    GlobalPauseStatusView,
    MonitoredProductActivateView,
    MonitoredProductCreateView,
    MonitoredProductDeactivateView,
    MonitoredProductDetailView,
    MonitoredProductHistoryView,
    MonitoredProductListView,
    MonitoredProductUpdateView,
    NotificadorConfigDetailView,
    NotificadorConfigUpdateView,
    NotificadorStatusView,
    NotificationPauseListView,
    RunChecksNowView,
    TelegramSubscriberDeactivateView,
    TelegramSubscriberListView,
    TelegramWebhookView,
    TrustedSellerActivateView,
    TrustedSellerCreateView,
    TrustedSellerDeactivateView,
    TrustedSellerListView,
    TrustedSellerUpdateView,
)


urlpatterns = [
    # MonitoredProduct CRUD + history
    path('monitored-products/list/', MonitoredProductListView.as_view(), name='dw-monitored-list'),
    path('monitored-products/create/', MonitoredProductCreateView.as_view(), name='dw-monitored-create'),
    path('monitored-products/update/<int:pk>/', MonitoredProductUpdateView.as_view(), name='dw-monitored-update'),
    path('monitored-products/activate/<int:pk>/', MonitoredProductActivateView.as_view(), name='dw-monitored-activate'),
    path('monitored-products/deactivate/<int:pk>/', MonitoredProductDeactivateView.as_view(), name='dw-monitored-deactivate'),
    path('monitored-products/detail/<int:pk>/', MonitoredProductDetailView.as_view(), name='dw-monitored-detail'),
    path('monitored-products/history/<int:pk>/', MonitoredProductHistoryView.as_view(), name='dw-monitored-history'),

    # TrustedSeller CRUD
    path('trusted-sellers/list/', TrustedSellerListView.as_view(), name='dw-seller-list'),
    path('trusted-sellers/create/', TrustedSellerCreateView.as_view(), name='dw-seller-create'),
    path('trusted-sellers/update/<int:pk>/', TrustedSellerUpdateView.as_view(), name='dw-seller-update'),
    path('trusted-sellers/activate/<int:pk>/', TrustedSellerActivateView.as_view(), name='dw-seller-activate'),
    path('trusted-sellers/deactivate/<int:pk>/', TrustedSellerDeactivateView.as_view(), name='dw-seller-deactivate'),

    # Pauses
    path('pauses/list/', NotificationPauseListView.as_view(), name='dw-pause-list'),
    path('pauses/global/status/', GlobalPauseStatusView.as_view(), name='dw-pause-status'),
    path('pauses/global/create/', GlobalPauseCreateView.as_view(), name='dw-pause-create'),
    path('pauses/global/lift/', GlobalPauseLiftView.as_view(), name='dw-pause-lift'),

    # Configuración del notificador (franja + presupuesto)
    path('config/detail/', NotificadorConfigDetailView.as_view(), name='dw-config-detail'),
    path('config/update/', NotificadorConfigUpdateView.as_view(), name='dw-config-update'),
    path('config/status/', NotificadorStatusView.as_view(), name='dw-config-status'),

    # On-demand check (botón de pruebas)
    path('run-now/', RunChecksNowView.as_view(), name='dw-run-now'),

    # Telegram subscribers
    path('telegram-subscribers/list/', TelegramSubscriberListView.as_view(), name='dw-tg-subs-list'),
    path('telegram-subscribers/deactivate/<int:pk>/', TelegramSubscriberDeactivateView.as_view(), name='dw-tg-subs-deactivate'),

    # Telegram webhook (kept last; uses str path component for the secret)
    path('telegram/webhook/<str:secret>/', TelegramWebhookView.as_view(), name='deal-watcher-telegram-webhook'),
]
