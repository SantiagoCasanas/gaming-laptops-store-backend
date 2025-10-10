from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginView,
    UserCreateView,
    UserListView,
    UserUpdateView,
    UserActivateView,
    UserDeactivateView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', UserCreateView.as_view(), name='user_register'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('list/', UserListView.as_view(), name='user_list'),
    path('update/<int:pk>/', UserUpdateView.as_view(), name='user_update'),
    path('activate/<int:pk>/', UserActivateView.as_view(), name='user_activate'),
    path('deactivate/<int:pk>/', UserDeactivateView.as_view(), name='user_deactivate'),
]
