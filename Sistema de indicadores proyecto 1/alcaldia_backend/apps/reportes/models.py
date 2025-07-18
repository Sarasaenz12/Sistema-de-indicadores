from django.db import models
from django.contrib.auth import get_user_model
from apps.archivos.models import ArchivoExcel

User = get_user_model()


class ReporteGenerado(models.Model):
    """
    Modelo para rastrear los reportes generados
    """
    TIPO_REPORTE_CHOICES = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('grafico', 'Gráfico'),
    ]

    titulo = models.CharField(max_length=300)
    descripcion = models.TextField(blank=True, null=True)
    tipo_reporte = models.CharField(
        max_length=20,
        choices=TIPO_REPORTE_CHOICES,
        default='pdf'
    )

    # Filtros aplicados (almacenados como JSON)
    filtros_aplicados = models.JSONField(default=dict, blank=True)

    # Archivos relacionados
    archivos_incluidos = models.ManyToManyField(
        ArchivoExcel,
        blank=True,
        related_name='reportes_relacionados'
    )

    # Usuario que generó el reporte
    usuario_generador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reportes_generados'
    )

    # Archivo del reporte generado
    archivo_generado = models.FileField(
        upload_to='reportes_generados/',
        blank=True,
        null=True
    )

    fecha_generacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reporte Generado'
        verbose_name_plural = 'Reportes Generados'
        db_table = 'reportes_generados'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"{self.titulo} - {self.usuario_generador.get_full_name()}"


class ConfiguracionGrafico(models.Model):
    """
    Modelo para almacenar configuraciones de gráficos personalizados
    """
    TIPO_GRAFICO_CHOICES = [
        ('bar', 'Barras'),
        ('line', 'Líneas'),
        ('pie', 'Circular'),
        ('scatter', 'Dispersión'),
    ]

    nombre = models.CharField(max_length=200)
    tipo_grafico = models.CharField(
        max_length=20,
        choices=TIPO_GRAFICO_CHOICES,
        default='bar'
    )
    configuracion = models.JSONField(default=dict)  # Configuración del gráfico

    usuario_creador = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='configuraciones_graficos'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración de Gráfico'
        verbose_name_plural = 'Configuraciones de Gráficos'
        db_table = 'configuraciones_graficos'
        ordering = ['-fecha_creacion']
        permissions = [
            ("puede_generar_reportes", "Puede generar reportes"),
            ("puede_exportar_datos", "Puede exportar datos"),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_grafico_display()})"