from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('kpis/', views.KpisView.as_view(), name='kpis'),
    path('sales-timeline/', views.SalesTimelineView.as_view(), name='sales-timeline'),
    path('sales-orders-status/', views.SalesOrdersStatusView.as_view(), name='sales-orders-status'),
    path('purchase-orders-status/', views.PurchaseOrdersStatusView.as_view(), name='purchase-orders-status'),
    path('reservations/', views.ReservationsView.as_view(), name='reservations'),
    path('imports-expenses/', views.ImportsExpensesView.as_view(), name='imports-expenses'),
]
