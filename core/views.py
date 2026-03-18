from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import TRMHistory
from .serializers import TRMHistorySerializer, TRMHistoryCreateSerializer


class TRMHistoryListView(generics.ListAPIView):
    """
    List all TRM history records.
    Requires authentication.
    """
    queryset = TRMHistory.objects.all()
    serializer_class = TRMHistorySerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
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
