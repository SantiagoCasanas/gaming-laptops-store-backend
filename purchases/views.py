from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView, UpdateAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import OrdenCompra
from .serializers import OrdenCompraSerializer, OrdenCompraCreateSerializer, OrdenCompraUpdateSerializer


class OrdenCompraListView(ListAPIView):
    """
    View to list all purchase orders.
    GET: Returns a list of all purchase orders with their information.
    """
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrdenCompra.objects.select_related(
            'producto', 'producto__marca', 'proveedor', 'cliente', 'unidad_producto'
        ).all()


class OrdenCompraCreateView(CreateAPIView):
    """
    View to create a new purchase order.
    POST: Creates a new purchase order with the provided data.
    """
    serializer_class = OrdenCompraCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        orden = serializer.save()

        return Response({
            'message': 'Purchase order created successfully',
            'orden_compra': OrdenCompraSerializer(
                OrdenCompra.objects.select_related(
                    'producto', 'producto__marca', 'proveedor', 'cliente', 'unidad_producto'
                ).get(pk=orden.pk)
            ).data
        }, status=status.HTTP_201_CREATED)


class OrdenCompraUpdateView(UpdateAPIView):
    """
    View to update purchase order information.
    PATCH/PUT: Updates purchase order information.
    """
    serializer_class = OrdenCompraUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return OrdenCompra.objects.select_related(
            'producto', 'producto__marca', 'proveedor', 'cliente', 'unidad_producto'
        ).all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        return Response({
            'message': 'Purchase order updated successfully',
            'orden_compra': OrdenCompraSerializer(
                OrdenCompra.objects.select_related(
                    'producto', 'producto__marca', 'proveedor', 'cliente', 'unidad_producto'
                ).get(pk=updated_instance.pk)
            ).data
        }, status=status.HTTP_200_OK)


class OrdenCompraDetailView(RetrieveAPIView):
    """
    View to retrieve purchase order details.
    GET: Returns detailed information about a specific purchase order.
    """
    serializer_class = OrdenCompraSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return OrdenCompra.objects.select_related(
            'producto', 'producto__marca', 'proveedor', 'cliente', 'unidad_producto'
        ).all()


class OrdenCompraActivateView(APIView):
    """
    View to activate a purchase order.
    POST: Sets active=True for the specified purchase order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)

        if orden.active:
            return Response({
                'message': 'Purchase order is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        orden.active = True
        orden.save()

        return Response({
            'message': 'Purchase order activated successfully',
            'orden_compra': OrdenCompraSerializer(orden).data
        }, status=status.HTTP_200_OK)


class OrdenCompraDeactivateView(APIView):
    """
    View to deactivate a purchase order.
    POST: Sets active=False for the specified purchase order.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        orden = get_object_or_404(OrdenCompra, pk=pk)

        if not orden.active:
            return Response({
                'message': 'Purchase order is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        orden.active = False
        orden.save()

        return Response({
            'message': 'Purchase order deactivated successfully',
            'orden_compra': OrdenCompraSerializer(orden).data
        }, status=status.HTTP_200_OK)
