from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

User = get_user_model()


class ArchivoExcel(models.Model):
    """
    Modelo para almacenar metadatos de archivos Excel subidos
    """
    nombre_archivo = models.CharField(max_length=255)
    archivo = models.FileField(
        upload_to='archivos_excel/',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])]
    )
    descripcion = models.TextField(blank=True, null=True)
    usuario_subida = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='archivos_subidos'
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    # Metadatos del archivo procesado
    total_filas = models.IntegerField(default=0)
    total_columnas = models.IntegerField(default=0)
    columnas_disponibles = models.JSONField(default=list, blank=True)
    procesado = models.BooleanField(default=False)

    # Campos para filtros comunes (si existen en el archivo)
    anio = models.IntegerField(blank=True, null=True)
    dependencia = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        verbose_name = 'Archivo Excel'
        verbose_name_plural = 'Archivos Excel'
        db_table = 'archivos_excel'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.nombre_archivo} - {self.usuario_subida.get_full_name()}"


class RegistroDato(models.Model):
    """
    Modelo flexible para almacenar cada fila del Excel como JSON
    """
    archivo = models.ForeignKey(
        ArchivoExcel,
        on_delete=models.CASCADE,
        related_name='registros'
    )
    numero_fila = models.IntegerField()
    datos = models.JSONField()  # Aquí se almacena toda la fila como JSON

    # Campos extraídos comúnmente para facilitar filtros
    # Estos se llenan automáticamente si existen en el JSON
    anio = models.IntegerField(blank=True, null=True)
    dependencia = models.CharField(max_length=200, blank=True, null=True)
    indicador = models.CharField(max_length=300, blank=True, null=True)
    valor = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de Dato'
        verbose_name_plural = 'Registros de Datos'
        db_table = 'registros_datos'
        ordering = ['archivo', 'numero_fila']
        indexes = [
            models.Index(fields=['archivo', 'numero_fila']),
            models.Index(fields=['anio']),
            models.Index(fields=['dependencia']),
            models.Index(fields=['indicador']),
        ]

    def __str__(self):
        return f"Fila {self.numero_fila} - {self.archivo.nombre_archivo}"

    def save(self, *args, **kwargs):
        """
        Extrae automáticamente campos comunes del JSON para facilitar filtros
        """
        if self.datos:
            # Buscar campos comunes en el JSON (case-insensitive)
            datos_lower = {k.lower(): v for k, v in self.datos.items()}

            # Extraer año
            for key in ['año', 'anio', 'year', 'fecha']:
                if key in datos_lower:
                    try:
                        self.anio = int(datos_lower[key])
                        break
                    except (ValueError, TypeError):
                        pass

            # Extraer dependencia
            for key in ['dependencia', 'area', 'secretaria', 'oficina']:
                if key in datos_lower:
                    self.dependencia = str(datos_lower[key])[:200]
                    break

            # Extraer indicador
            for key in ['indicador', 'nombre_indicador', 'descripcion']:
                if key in datos_lower:
                    self.indicador = str(datos_lower[key])[:300]
                    break

            # Extraer valor numérico
            for key in ['valor', 'cantidad', 'total', 'resultado']:
                if key in datos_lower:
                    try:
                        self.valor = float(datos_lower[key])
                        break
                    except (ValueError, TypeError):
                        pass

        super().save(*args, **kwargs)