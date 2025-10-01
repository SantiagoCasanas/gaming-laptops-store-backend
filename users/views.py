from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from .serializers import LoginSerializer


class LoginView(GenericAPIView):
    """
    Vista para autenticación de usuarios.

    POST: Autentica un usuario y retorna tokens JWT (access y refresh).
    Los tokens expiran según la configuración de SIMPLE_JWT en settings.
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
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_200_OK)
