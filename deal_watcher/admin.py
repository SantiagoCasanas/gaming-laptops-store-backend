from django.contrib import admin

from .models import (
    TrustedSeller,
    MonitoredProduct,
    PriceCheck,
    NotificationPause,
    TelegramSubscriber,
)


@admin.register(TrustedSeller)
class TrustedSellerAdmin(admin.ModelAdmin):
    list_display = ('username', 'display_name', 'active', 'created_at')
    list_filter = ('active',)
    search_fields = ('username', 'display_name', 'notes')
    ordering = ('username',)


@admin.register(MonitoredProduct)
class MonitoredProductAdmin(admin.ModelAdmin):
    list_display = (
        'nickname',
        'ebay_item_id',
        'max_price_cop',
        'last_known_price_usd',
        'last_known_seller',
        'last_seen_available_at',
        'active',
    )
    list_filter = ('active',)
    search_fields = ('nickname', 'ebay_item_id', 'ebay_url', 'last_known_seller')
    raw_id_fields = ('producto_catalogo', 'usuario_ultima_modificacion')
    readonly_fields = (
        'ebay_item_id',
        'last_seen_available_at',
        'last_notified_at',
        'last_notified_price_usd',
        'last_known_price_usd',
        'last_known_seller',
        'created_at',
        'updated_at',
    )


@admin.register(PriceCheck)
class PriceCheckAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'monitored_product',
        'checked_at',
        'was_available',
        'price_usd',
        'price_cop_calculated',
        'seller_username',
        'seller_is_trusted',
        'triggered_notification',
    )
    list_filter = (
        'was_available',
        'seller_is_trusted',
        'triggered_notification',
    )
    search_fields = (
        'monitored_product__nickname',
        'monitored_product__ebay_item_id',
        'seller_username',
        'error_message',
    )
    raw_id_fields = ('monitored_product',)
    date_hierarchy = 'checked_at'
    readonly_fields = ('checked_at',)


@admin.register(NotificationPause)
class NotificationPauseAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'scope',
        'monitored_product',
        'paused_until',
        'created_via',
        'active',
        'created_at',
    )
    list_filter = ('scope', 'created_via', 'active')
    raw_id_fields = ('monitored_product',)
    search_fields = ('reason',)


@admin.register(TelegramSubscriber)
class TelegramSubscriberAdmin(admin.ModelAdmin):
    list_display = ('chat_id', 'telegram_username', 'active', 'first_seen_at')
    list_filter = ('active',)
    search_fields = ('chat_id', 'telegram_username')
