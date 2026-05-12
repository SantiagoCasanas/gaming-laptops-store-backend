"""
Deal Watcher domain models.

Tracks eBay listings the operator wants to buy at a target price, the trusted
sellers we accept, the history of price checks, pause windows that silence
notifications, and Telegram subscribers that receive alerts.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

from core.models import BaseModel


class TrustedSeller(BaseModel):
    """
    eBay seller usernames we accept as trustworthy sources.

    Distinct from `products.Proveedor` (which represents broad supplier
    entities like 'eBay' or 'Amazon'): TrustedSeller models the specific
    `seller.username` returned by the Browse API (antonline, vipoutlet, etc.).
    Comparison is always lowercase.
    """
    username = models.CharField(
        max_length=100,
        unique=True,
        help_text="eBay seller username, lowercased on save",
    )
    display_name = models.CharField(
        max_length=120,
        blank=True,
        default='',
        help_text="Optional pretty name for the UI",
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Operator notes about this seller",
    )

    class Meta:
        verbose_name = "Trusted Seller"
        verbose_name_plural = "Trusted Sellers"
        ordering = ['username']

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class MonitoredProduct(BaseModel):
    """
    An eBay listing the operator is watching for a target COP price.

    `max_price_cop` is the all-in ceiling (already includes shipping, taxes,
    4x1000 and commissions in the operator's mental model).
    """
    nickname = models.CharField(
        max_length=160,
        help_text="Operator-friendly label, e.g. 'Acer Nitro V 5050'",
    )
    ebay_url = models.URLField(
        max_length=2048,
        help_text="Full eBay listing URL",
    )
    ebay_item_id = models.CharField(
        max_length=32,
        db_index=True,
        blank=True,
        help_text="Auto-extracted from ebay_url on save",
    )
    max_price_cop = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="All-in price ceiling in COP",
    )
    producto_catalogo = models.ForeignKey(
        'products.Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitored_deals',
        help_text="Optional link to the catalog product, when the deal restocks an existing SKU",
    )
    last_seen_available_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the listing was seen with stock",
    )
    last_notified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time we sent a notification for this product",
    )
    last_notified_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="USD price quoted in the last notification",
    )
    last_known_price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Most recent USD price observed",
    )
    last_known_seller = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Most recent seller.username observed",
    )
    usuario_ultima_modificacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='monitored_products_modificados',
        help_text="Last user who modified this monitored product",
    )

    class Meta:
        verbose_name = "Monitored Product"
        verbose_name_plural = "Monitored Products"
        ordering = ['-id']

    def clean(self):
        super().clean()
        # Pre-validate the URL so the admin shows a friendly form error.
        if self.ebay_url:
            from products.services.ebay_service import extract_legacy_id_from_url
            try:
                self.ebay_item_id = extract_legacy_id_from_url(self.ebay_url)
            except ValueError as exc:
                raise ValidationError({'ebay_url': str(exc)})

    def save(self, *args, **kwargs):
        # Authoritative auto-fill: the item id always derives from the URL.
        from products.services.ebay_service import extract_legacy_id_from_url
        if self.ebay_url:
            try:
                self.ebay_item_id = extract_legacy_id_from_url(self.ebay_url)
            except ValueError as exc:
                raise ValidationError({'ebay_url': str(exc)})
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nickname} ({self.ebay_item_id})"


class PriceCheck(BaseModel):
    """
    Audit log: one row per check performed against eBay for a monitored product.

    Even failed checks are recorded (with `error_message`) so the operator can
    diagnose silent breakages.
    """
    monitored_product = models.ForeignKey(
        MonitoredProduct,
        on_delete=models.CASCADE,
        related_name='price_checks',
    )
    checked_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    was_available = models.BooleanField(default=False)
    price_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    trm_used = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    price_cop_calculated = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    seller_username = models.CharField(max_length=100, blank=True, default='')
    seller_is_trusted = models.BooleanField(default=False)
    triggered_notification = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = "Price Check"
        verbose_name_plural = "Price Checks"
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['monitored_product', '-checked_at']),
        ]

    def __str__(self):
        return f"PriceCheck#{self.pk} {self.monitored_product_id} @ {self.checked_at:%Y-%m-%d %H:%M}"


class NotificationPause(BaseModel):
    """
    Pause window for notifications. Either global or per-monitored-product.

    A null `paused_until` means the pause is indefinite (only lifted by
    deactivating the row). The pause is considered active while
    `active=True AND (paused_until IS NULL OR paused_until > now())`.
    """
    SCOPE_GLOBAL = 'global'
    SCOPE_PRODUCT = 'product'
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, 'Global'),
        (SCOPE_PRODUCT, 'Product'),
    ]

    CREATED_VIA_UI = 'ui'
    CREATED_VIA_TELEGRAM = 'telegram'
    CREATED_VIA_ADMIN = 'admin'
    CREATED_VIA_CHOICES = [
        (CREATED_VIA_UI, 'UI'),
        (CREATED_VIA_TELEGRAM, 'Telegram'),
        (CREATED_VIA_ADMIN, 'Admin'),
    ]

    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES)
    monitored_product = models.ForeignKey(
        MonitoredProduct,
        on_delete=models.CASCADE,
        related_name='pauses',
        null=True,
        blank=True,
        help_text="Required when scope='product', null when scope='global'",
    )
    paused_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the pause expires; null means indefinite",
    )
    reason = models.CharField(max_length=255, blank=True, default='')
    created_via = models.CharField(
        max_length=20,
        choices=CREATED_VIA_CHOICES,
        default=CREATED_VIA_UI,
    )

    class Meta:
        verbose_name = "Notification Pause"
        verbose_name_plural = "Notification Pauses"
        ordering = ['-created_at']

    def __str__(self):
        target = self.monitored_product_id if self.scope == self.SCOPE_PRODUCT else 'GLOBAL'
        until = self.paused_until.isoformat() if self.paused_until else 'indefinite'
        return f"Pause[{self.scope}:{target}] until {until}"


class TelegramSubscriber(BaseModel):
    """
    A Telegram chat that receives deal alerts.

    Subscribers are created when they message the bot for the first time
    (handled in the webhook), not via the admin API.
    """
    chat_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="Telegram chat_id (string to keep precision)",
    )
    telegram_username = models.CharField(
        max_length=120,
        blank=True,
        default='',
        help_text="@handle of the user who subscribed (may be empty)",
    )
    first_seen_at = models.DateTimeField(
        auto_now_add=True,
        help_text="First time we saw this chat",
    )

    class Meta:
        verbose_name = "Telegram Subscriber"
        verbose_name_plural = "Telegram Subscribers"
        ordering = ['-first_seen_at']

    def __str__(self):
        return f"{self.telegram_username or self.chat_id}"
