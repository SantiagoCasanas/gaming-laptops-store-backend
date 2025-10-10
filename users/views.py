from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView, ListAPIView, UpdateAPIView, CreateAPIView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from .serializers import LoginSerializer, UserSerializer, UserUpdateSerializer, UserCreateSerializer
from .models import User


class LoginView(GenericAPIView):
    """
    View that allows users to log in and receive JWT tokens.

    POST: Returns access and refresh tokens upon successful authentication.
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        tokens = serializer.get_tokens(user)

        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_200_OK)


class UserCreateView(CreateAPIView):
    """
    View to register a new user.

    POST: Creates a new user with the provided data.
    Does not require authentication (public endpoint).
    """
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_201_CREATED)


class UserListView(ListAPIView):
    """
    View to list all users.

    GET: Returns a list of all users with their information.
    Requires JWT authentication via Bearer token.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class UserUpdateView(UpdateAPIView):
    """
    View to update user information.

    PATCH/PUT: Updates user information (first_name, last_name, email, password).
    Requires JWT authentication via Bearer token.
    """
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Return updated user data with UserSerializer
        user_serializer = UserSerializer(instance)
        return Response({
            'message': 'User updated successfully',
            'user': user_serializer.data
        }, status=status.HTTP_200_OK)


class UserActivateView(APIView):
    """
    View to activate a user account.

    POST: Sets is_active=True for the specified user.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if user.is_active:
            return Response({
                'message': 'User is already active'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()

        return Response({
            'message': 'User activated successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class UserDeactivateView(APIView):
    """
    View to deactivate a user account.

    POST: Sets is_active=False for the specified user.
    Requires JWT authentication via Bearer token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)

        if not user.is_active:
            return Response({
                'message': 'User is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = False
        user.save()

        return Response({
            'message': 'User deactivated successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
