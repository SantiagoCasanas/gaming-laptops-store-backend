from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, UserListView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('list/', UserListView.as_view(), name='user_list'),
]
