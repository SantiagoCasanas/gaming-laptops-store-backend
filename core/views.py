from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import TRMHistory
from .serializers import TRMHistorySerializer, TRMHistoryCreateSerializer
from .services.trm_service import fetch_and_store_trm


class TRMHistoryListView(generics.ListAPIView):
    """
    List all TRM history records.
    Requires authentication.
    Auto-fetches TRM from external API if DB is empty.
    """
    queryset = TRMHistory.objects.all()
    serializer_class = TRMHistorySerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        from datetime import date
        # Auto-fetch from external API if no TRM record exists for today
        if not TRMHistory.objects.filter(fecha=date.today()).exists():
            fetch_and_store_trm()

        response = super().list(request, *args, **kwargs)
        return Response(
            {
                'message': 'TRM history retrieved successfully',
                'trm_history': response.data
            },
            status=status.HTTP_200_OK
        )


class TRMHistoryCreateView(generics.CreateAPIView):
    """
    Create a new TRM history record.
    Requires authentication.
    """
    queryset = TRMHistory.objects.all()
    serializer_class = TRMHistoryCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {
                'message': 'TRM history created successfully',
                'trm_history': response.data
            },
            status=status.HTTP_201_CREATED
        )
