from django.urls import path
from .views import (
    InvoiceListView,
    InvoiceCreateView,
    InvoiceDetailView,
    InvoiceUpdateView,
    InvoiceDeleteView,
    InvoiceDownloadView,
    InvoiceResendEmailView,
    InvoiceParseNaturalLanguageView,
)

urlpatterns = [
    path('invoices/list/', InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/detail/<int:pk>/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/update/<int:pk>/', InvoiceUpdateView.as_view(), name='invoice_update'),
    path('invoices/delete/<int:pk>/', InvoiceDeleteView.as_view(), name='invoice_delete'),
    path('invoices/<int:pk>/download/', InvoiceDownloadView.as_view(), name='invoice_download'),
    path('invoices/<int:pk>/resend_email/', InvoiceResendEmailView.as_view(), name='invoice_resend_email'),
    path('invoices/parse_natural_language/', InvoiceParseNaturalLanguageView.as_view(), name='invoice_parse_nl'),
]
