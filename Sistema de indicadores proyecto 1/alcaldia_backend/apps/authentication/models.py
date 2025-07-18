from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Modelo de usuario personalizado con roles para la alcaldía
    """
    ROLE_CHOICES = [
        ('admin', 'Súper Usuario'),
        ('funcionario', 'Funcionario'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='funcionario'
    )
    dependencia = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # Usar email como campo de login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def is_admin(self):
        return self.role == 'admin'

    def is_funcionario(self):
        return self.role == 'funcionario'

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        db_table = 'auth_usuarios'

    def has_perm(self, perm, obj=None):
        if self.is_admin():
            return True
        return super().has_perm(perm, obj)