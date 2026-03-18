from django.urls import path
from .views import (
    OrdenCompraListView,
    OrdenCompraCreateView,
    OrdenCompraUpdateView,
    OrdenCompraDetailView,
    OrdenCompraActivateView,
    OrdenCompraDeactivateView,
)

urlpatterns = [
    path('ordenes-compra/list/', OrdenCompraListView.as_view(), name='orden_compra_list'),
    path('ordenes-compra/create/', OrdenCompraCreateView.as_view(), name='orden_compra_create'),
    path('ordenes-compra/update/<int:pk>/', OrdenCompraUpdateView.as_view(), name='orden_compra_update'),
    path('ordenes-compra/detail/<int:pk>/', OrdenCompraDetailView.as_view(), name='orden_compra_detail'),
    path('ordenes-compra/activate/<int:pk>/', OrdenCompraActivateView.as_view(), name='orden_compra_activate'),
    path('ordenes-compra/deactivate/<int:pk>/', OrdenCompraDeactivateView.as_view(), name='orden_compra_deactivate'),
]
