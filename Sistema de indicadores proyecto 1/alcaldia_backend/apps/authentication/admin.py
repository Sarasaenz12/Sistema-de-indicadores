from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import CustomUser


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'username')


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'dependencia', 'activo', 'date_joined')
    list_filter = ('role', 'activo', 'date_joined', 'dependencia')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'dependencia')
    ordering = ('email',)

    fieldsets = (
        (None, {
            'fields': ('email', 'username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'telefono', 'dependencia')
        }),
        ('Permisos', {
            'fields': ('role', 'activo', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas Importantes', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role', 'dependencia', 'first_name', 'last_name'),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando un usuario existente
            return ('date_joined', 'last_login')
        return ()

    def save_model(self, request, obj, form, change):
        if not change:  # Creando nuevo usuario
            obj.set_password(obj.password)
        super().save_model(request, obj, form, change)