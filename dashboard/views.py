"""
Thin orchestration layer. Each view: parse_month_param → service call →
serialize → respond. All views require admin.
"""

from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import serializers, services


class _MonthScopedView(APIView):
    permission_classes = [IsAdminUser]
    output_serializer = None
    service_fn = None

    def get(self, request):
        month = services.parse_month_param(request)
        data = self.service_fn(month)
        return Response(self.output_serializer(data).data)


class KpisView(_MonthScopedView):
    output_serializer = serializers.KpisSerializer
    service_fn = staticmethod(services.get_kpis)


class SalesTimelineView(_MonthScopedView):
    output_serializer = serializers.SalesTimelineSerializer
    service_fn = staticmethod(services.get_sales_timeline)


class SalesOrdersStatusView(_MonthScopedView):
    output_serializer = serializers.SalesOrdersStatusSerializer
    service_fn = staticmethod(services.get_sales_orders_status)


class PurchaseOrdersStatusView(_MonthScopedView):
    output_serializer = serializers.PurchaseOrdersStatusSerializer
    service_fn = staticmethod(services.get_purchase_orders_status)


class ReservationsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Validate month for consistency with the rest of the dashboard, even
        # though reservations are global state. A bad ?month= still returns 400.
        services.parse_month_param(request)
        data = services.get_reservations()
        return Response(serializers.ReservationSerializer(data, many=True).data)


class ImportsExpensesView(_MonthScopedView):
    output_serializer = None  # custom many=True path

    def get(self, request):
        month = services.parse_month_param(request)
        data = services.get_imports_expenses(month)
        return Response(serializers.ImportsExpenseRowSerializer(data, many=True).data)
