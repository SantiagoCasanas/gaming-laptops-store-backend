from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User


class LoginSerializer(serializers.Serializer):
    """
    Serializer that handles user login and JWT token generation.
    """
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Since we use email as username, we need to pass it as username to authenticate
            user = authenticate(username=email, password=password)

            if not user:
                raise serializers.ValidationError(
                    'Invalid credentials. Please check your email and password.'
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    'This account is disabled.'
                )

            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Email and password are required.'
            )

    def get_tokens(self, user):
        """
        Create and return JWT tokens for the authenticated user.
        """
        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    Used for listing and retrieving user information.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'last_access', 'is_active']
        read_only_fields = ['email', 'last_access']
