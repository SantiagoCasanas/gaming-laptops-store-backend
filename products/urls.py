from django.urls import path
from .views import (
    BrandListView,
    BrandCreateView,
    BrandUpdateView,
    BrandActivateView,
    BrandDeactivateView,
    CategoryListView,
    CategoryCreateView,
    CategoryUpdateView,
    CategoryActivateView,
    CategoryDeactivateView,
    BaseProductListView,
    BaseProductCreateView,
    BaseProductUpdateView,
    BaseProductActivateView,
    BaseProductDeactivateView
)

urlpatterns = [
    # Brand endpoints
    path('brands/', BrandListView.as_view(), name='brand_list'),
    path('brands/create/', BrandCreateView.as_view(), name='brand_create'),
    path('brands/update/<int:pk>/', BrandUpdateView.as_view(), name='brand_update'),
    path('brands/activate/<int:pk>/', BrandActivateView.as_view(), name='brand_activate'),
    path('brands/deactivate/<int:pk>/', BrandDeactivateView.as_view(), name='brand_deactivate'),

    # Category endpoints
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/create/', CategoryCreateView.as_view(), name='category_create'),
    path('categories/update/<int:pk>/', CategoryUpdateView.as_view(), name='category_update'),
    path('categories/activate/<int:pk>/', CategoryActivateView.as_view(), name='category_activate'),
    path('categories/deactivate/<int:pk>/', CategoryDeactivateView.as_view(), name='category_deactivate'),

    # BaseProduct endpoints
    path('base-products/', BaseProductListView.as_view(), name='baseproduct_list'),
    path('base-products/create/', BaseProductCreateView.as_view(), name='baseproduct_create'),
    path('base-products/update/<int:pk>/', BaseProductUpdateView.as_view(), name='baseproduct_update'),
    path('base-products/activate/<int:pk>/', BaseProductActivateView.as_view(), name='baseproduct_activate'),
    path('base-products/deactivate/<int:pk>/', BaseProductDeactivateView.as_view(), name='baseproduct_deactivate'),
]
