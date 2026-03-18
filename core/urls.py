from django.urls import path
from .views import TRMHistoryListView, TRMHistoryCreateView

app_name = 'core'

urlpatterns = [
    path('trm/list/', TRMHistoryListView.as_view(), name='trm-list'),
    path('trm/create/', TRMHistoryCreateView.as_view(), name='trm-create'),
]
