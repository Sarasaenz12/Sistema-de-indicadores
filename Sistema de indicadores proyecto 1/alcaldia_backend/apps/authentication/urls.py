from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    RegisterView,
    UserListView,
    UserDetailView,
    ProfileView,
    ChangePasswordView,
    logout_view,
    user_info_view,
    dashboard_stats_view
)

urlpatterns = [
    # Autenticación JWT
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout'),

    # Información del usuario
    path('user/', user_info_view, name='user_info'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # Gestión de usuarios (solo admins)
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/create/', RegisterView.as_view(), name='user_create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),

    # Estadísticas del dashboard
    path('dashboard/stats/', dashboard_stats_view, name='dashboard_stats'),
]