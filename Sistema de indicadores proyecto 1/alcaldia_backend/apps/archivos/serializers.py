from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from .models import ArchivoExcel, RegistroDato
from .utils import ExcelProcessor


class ArchivoExcelSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo ArchivoExcel
    """
    usuario_subida_nombre = serializers.CharField(
        source='usuario_subida.get_full_name',
        read_only=True
    )
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoExcel
        fields = [
            'id', 'nombre_archivo', 'archivo', 'archivo_url', 'descripcion',
            'usuario_subida', 'usuario_subida_nombre', 'fecha_subida',
            'fecha_actualizacion', 'total_filas', 'total_columnas',
            'columnas_disponibles', 'procesado', 'anio', 'dependencia'
        ]
        read_only_fields = [
            'id', 'usuario_subida', 'fecha_subida', 'fecha_actualizacion',
            'total_filas', 'total_columnas', 'columnas_disponibles',
            'procesado', 'anio', 'dependencia'
        ]

    def get_archivo_url(self, obj):
        if obj.archivo:
            return obj.archivo.url
        return None

    def validate_archivo(self, value):
        """
        Valida el archivo Excel subido
        """
        if not isinstance(value, UploadedFile):
            raise serializers.ValidationError("Debe proporcionar un archivo válido")

        # Crear un procesador temporal para validar
        processor = ExcelProcessor(None)
        is_valid, message = processor.validar_archivo(value)

        if not is_valid:
            raise serializers.ValidationError(message)

        return value

    def create(self, validated_data):
        """
        Crea el archivo y lo procesa automáticamente
        """
        # Establecer el usuario actual
        validated_data['usuario_subida'] = self.context['request'].user

        # Crear el archivo
        archivo = super().create(validated_data)

        # Procesar el archivo automáticamente
        processor = ExcelProcessor(archivo)
        success, message = processor.procesar_excel()

        if success:
            # Guardar los registros en la base de datos
            processor.guardar_registros()
        else:
            # Si falla el procesamiento, eliminar el archivo
            archivo.delete()
            raise serializers.ValidationError(f"Error al procesar el archivo: {message}")

        return archivo


class ArchivoExcelListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar archivos
    """
    usuario_subida_nombre = serializers.CharField(
        source='usuario_subida.get_full_name',
        read_only=True
    )

    class Meta:
        model = ArchivoExcel
        fields = [
            'id', 'nombre_archivo', 'descripcion', 'usuario_subida_nombre',
            'fecha_subida', 'total_filas', 'total_columnas', 'procesado',
            'anio', 'dependencia'
        ]


class RegistroDatoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo RegistroDato
    """
    archivo_nombre = serializers.CharField(
        source='archivo.nombre_archivo',
        read_only=True
    )

    class Meta:
        model = RegistroDato
        fields = [
            'id', 'archivo', 'archivo_nombre', 'numero_fila', 'datos',
            'anio', 'dependencia', 'indicador', 'valor', 'fecha_creacion'
        ]
        read_only_fields = ['id', 'fecha_creacion']


class FiltroSerializer(serializers.Serializer):
    """
    Serializer para filtros de búsqueda
    """
    archivo_id = serializers.IntegerField(required=False)
    anio = serializers.IntegerField(required=False)
    dependencia = serializers.CharField(required=False, allow_blank=True)
    indicador = serializers.CharField(required=False, allow_blank=True)
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)

    # Filtros adicionales en JSON
    campo_personalizado = serializers.CharField(required=False, allow_blank=True)
    valor_personalizado = serializers.CharField(required=False, allow_blank=True)


class EstadisticasSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de archivos
    """
    total_archivos = serializers.IntegerField()
    total_registros = serializers.IntegerField()
    archivos_procesados = serializers.IntegerField()
    dependencias_unicas = serializers.IntegerField()
    anos_disponibles = serializers.ListField(child=serializers.IntegerField())
    dependencias_disponibles = serializers.ListField(child=serializers.CharField())


class GraficoSerializer(serializers.Serializer):
    """
    Serializer para datos de gráficos
    """
    tipo_grafico = serializers.ChoiceField(
        choices=['bar', 'line', 'pie', 'scatter'],
        default='bar'
    )
    titulo = serializers.CharField(max_length=200)
    labels = serializers.ListField(child=serializers.CharField())
    values = serializers.ListField(child=serializers.FloatField())

    # Configuración adicional
    color = serializers.CharField(required=False, allow_blank=True)
    mostrar_leyenda = serializers.BooleanField(default=True)


class ExportarDatosSerializer(serializers.Serializer):
    """
    Serializer para exportar datos
    """
    formato = serializers.ChoiceField(
        choices=['excel', 'csv', 'json'],
        default='excel'
    )
    incluir_metadatos = serializers.BooleanField(default=True)
    filtros = FiltroSerializer(required=False)

    # Campos específicos a exportar
    campos_incluir = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de campos a incluir en la exportación"
    )


class CargaMasivaSerializer(serializers.Serializer):
    """
    Serializer para carga masiva de archivos
    """
    archivos = serializers.ListField(
        child=serializers.FileField(),
        min_length=1,
        max_length=10,
        help_text="Lista de archivos Excel para procesar"
    )
    descripcion_general = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Descripción que se aplicará a todos los archivos"
    )
    procesar_asincrono = serializers.BooleanField(
        default=True,
        help_text="Si procesar los archivos de forma asíncrona"
    )

    def validate_archivos(self, value):
        """
        Valida que todos los archivos sean Excel válidos
        """
        processor = ExcelProcessor(None)

        for archivo in value:
            is_valid, message = processor.validar_archivo(archivo)
            if not is_valid:
                raise serializers.ValidationError(
                    f"Archivo '{archivo.name}': {message}"
                )

        return value