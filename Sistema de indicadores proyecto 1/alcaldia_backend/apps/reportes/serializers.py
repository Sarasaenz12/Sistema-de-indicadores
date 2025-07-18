from rest_framework import serializers
from .models import ReporteGenerado, ConfiguracionGrafico
from apps.authentication.serializers import UserSerializer
from apps.archivos.serializers import ArchivoExcelListSerializer


class GenerarReporteSerializer(serializers.Serializer):
    """
    Serializer para generar reportes
    """
    titulo = serializers.CharField(max_length=300, required=False, default="Reporte")
    filtros = serializers.JSONField(required=False, default=dict)
    incluir_graficos = serializers.BooleanField(required=False, default=True)
    campos_incluir = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de campos a incluir en el reporte"
    )


class ReporteGeneradoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo ReporteGenerado
    """
    usuario_generador = UserSerializer(read_only=True)
    archivos_incluidos = ArchivoExcelListSerializer(many=True, read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = ReporteGenerado
        fields = [
            'id', 'titulo', 'descripcion', 'tipo_reporte', 'filtros_aplicados',
            'archivos_incluidos', 'usuario_generador', 'archivo_generado',
            'archivo_url', 'fecha_generacion'
        ]
        read_only_fields = [
            'id', 'usuario_generador', 'archivo_generado', 'fecha_generacion'
        ]

    def get_archivo_url(self, obj):
        if obj.archivo_generado:
            return obj.archivo_generado.url
        return None


class ConfiguracionGraficoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo ConfiguracionGrafico
    """
    usuario_creador = UserSerializer(read_only=True)

    class Meta:
        model = ConfiguracionGrafico
        fields = [
            'id', 'nombre', 'tipo_grafico', 'configuracion',
            'usuario_creador', 'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = [
            'id', 'usuario_creador', 'fecha_creacion', 'fecha_actualizacion'
        ]

    def validate_configuracion(self, value):
        """
        Validar que la configuración sea un JSON válido
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("La configuración debe ser un objeto JSON válido")
        return value


class ExportarDatosSerializer(serializers.Serializer):
    """
    Serializer para exportar datos
    """
    formato = serializers.ChoiceField(
        choices=['excel', 'csv', 'json'],
        default='excel'
    )
    filtros = serializers.JSONField(required=False, default=dict)
    incluir_metadatos = serializers.BooleanField(default=True)
    campos_incluir = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de campos a incluir en la exportación"
    )

    def validate_filtros(self, value):
        """
        Validar que los filtros sean un JSON válido
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Los filtros deben ser un objeto JSON válido")
        return value