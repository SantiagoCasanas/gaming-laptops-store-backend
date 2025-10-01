from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken


class LoginSerializer(serializers.Serializer):
    """
    Serializer para el login de usuarios.
    Valida las credenciales y genera tokens JWT.
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)

            if not user:
                raise serializers.ValidationError(
                    'Credenciales inválidas. Por favor, verifica tu usuario y contraseña.'
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    'Esta cuenta está desactivada.'
                )

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Debes proporcionar usuario y contraseña.'
            )

    def get_tokens(self, user):
        """
        Genera tokens de acceso y refresh para el usuario autenticado.
        """
        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
