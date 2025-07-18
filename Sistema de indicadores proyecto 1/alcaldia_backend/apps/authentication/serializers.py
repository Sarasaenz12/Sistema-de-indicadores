from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from .models import CustomUser


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para obtener tokens JWT
    """
    username_field = 'email'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        self.fields['password'] = serializers.CharField()
        # Remover el campo username
        del self.fields['username']

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Agregar información personalizada al token
        token['email'] = user.email
        token['role'] = user.role
        token['dependencia'] = user.dependencia
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )

            if not user:
                raise serializers.ValidationError('Credenciales inválidas')

            if not user.is_active:
                raise serializers.ValidationError('Cuenta desactivada')

            if not user.activo:
                raise serializers.ValidationError('Usuario inactivo')

        else:
            raise serializers.ValidationError('Debe proporcionar email y contraseña')

        refresh = self.get_token(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo de usuario
    """

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'role', 'dependencia', 'telefono', 'activo', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear usuarios (solo para admins)
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'dependencia', 'telefono'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este email ya está registrado")
        return value

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nombre de usuario ya está registrado")
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        user = CustomUser.objects.create(**validated_data)
        user.set_password(password)
        user.save()

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar usuarios
    """

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'telefono', 'dependencia', 'activo'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambiar contraseña
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Contraseña actual incorrecta")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("La contraseña debe contener al menos un número")
        return value