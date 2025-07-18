from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer
)
from .models import CustomUser
from django.http import JsonResponse

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vista personalizada para login con JWT
    """
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    """
    Vista para registrar nuevos usuarios (solo para admins)
    """
    queryset = CustomUser.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Solo los admins pueden crear usuarios
        if not self.request.user.is_admin():
            raise permissions.PermissionDenied("Solo los administradores pueden crear usuarios")

        serializer.save()


class UserListView(generics.ListAPIView):
    """
    Vista para listar usuarios (solo para admins)
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_admin():
            raise permissions.PermissionDenied("Solo los administradores pueden ver la lista de usuarios")

        return CustomUser.objects.all().order_by('-date_joined')


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar y eliminar usuarios
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_admin():
            return CustomUser.objects.all()
        else:
            # Los funcionarios solo pueden ver su propio perfil
            return CustomUser.objects.filter(id=self.request.user.id)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_admin():
            return Response(
                {"error": "Solo los administradores pueden eliminar usuarios"},
                status=status.HTTP_403_FORBIDDEN
            )

        user = self.get_object()
        if user.id == request.user.id:
            return Response(
                {"error": "No puedes eliminar tu propia cuenta"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().destroy(request, *args, **kwargs)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Vista para ver y actualizar el perfil del usuario actual
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer


class ChangePasswordView(generics.UpdateAPIView):
    """
    Vista para cambiar contraseña
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({"message": "Contraseña actualizada exitosamente"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Vista para cerrar sesión (blacklist del token)
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        return Response({"message": "Sesión cerrada exitosamente"})
    except Exception as e:
        return Response(
            {"error": "Error al cerrar sesión"},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """
    Vista para obtener información del usuario actual
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats_view(request):
    """
    Vista para obtener estadísticas del dashboard
    """
    if not request.user.is_admin():
        return Response(
            {"error": "Solo los administradores pueden ver estadísticas"},
            status=status.HTTP_403_FORBIDDEN
        )

    stats = {
        'total_usuarios': CustomUser.objects.count(),
        'usuarios_activos': CustomUser.objects.filter(activo=True).count(),
        'administradores': CustomUser.objects.filter(role='admin').count(),
        'funcionarios': CustomUser.objects.filter(role='funcionario').count(),
        'dependencias': CustomUser.objects.values_list('dependencia', flat=True).distinct().count(),
    }

    return Response(stats)

def welcome_view(request):
    return JsonResponse({"message": "Bienvenido al sistema de indicadores de la Alcaldía."})