"""factory_boy factories for deal_watcher tests."""
from datetime import time
from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from deal_watcher.models import (
    ConfiguracionNotificador,
    MonitoredProduct,
    NotificationPause,
    PriceCheck,
    TelegramSubscriber,
    TrustedSeller,
)


class TrustedSellerFactory(DjangoModelFactory):
    class Meta:
        model = TrustedSeller
        django_get_or_create = ('username',)

    username = factory.Sequence(lambda n: f"seller{n}")
    display_name = ''


class MonitoredProductFactory(DjangoModelFactory):
    class Meta:
        model = MonitoredProduct

    nickname = factory.Sequence(lambda n: f"Product {n}")
    # ebay_item_id is auto-filled from ebay_url on save() — don't set it here.
    ebay_url = factory.Sequence(lambda n: f"https://www.ebay.com/itm/1234560{n:05d}")
    max_price_cop = Decimal('2500000.00')


class PriceCheckFactory(DjangoModelFactory):
    class Meta:
        model = PriceCheck

    monitored_product = factory.SubFactory(MonitoredProductFactory)
    was_available = True


class NotificationPauseFactory(DjangoModelFactory):
    class Meta:
        model = NotificationPause

    scope = NotificationPause.SCOPE_GLOBAL
    monitored_product = None
    paused_until = None


class TelegramSubscriberFactory(DjangoModelFactory):
    class Meta:
        model = TelegramSubscriber

    chat_id = factory.Sequence(lambda n: f"100{n:06d}")
    telegram_username = factory.Sequence(lambda n: f"user{n}")


class ConfiguracionNotificadorFactory(DjangoModelFactory):
    class Meta:
        model = ConfiguracionNotificador

    hora_inicio_activa = time(7, 0)
    hora_fin_activa = time(1, 0)
    llamados_diarios_objetivo = 5000
    reserva_otros_llamados = 200
