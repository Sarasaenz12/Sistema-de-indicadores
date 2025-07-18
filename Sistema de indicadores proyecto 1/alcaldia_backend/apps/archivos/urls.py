from django.urls import path
from .views import (
    ArchivoExcelListCreateView,
    ArchivoExcelDetailView,
    RegistroDatoListView,
    estadisticas_view,
    resumen_archivo_view,
    valores_unicos_view,
    generar_grafico_view,
    carga_masiva_view,
    columnas_disponibles_view,
    buscar_registros_view
)

app_name = 'archivos'

urlpatterns = [
    # Gestión de archivos Excel
    path('archivos/', ArchivoExcelListCreateView.as_view(), name='archivo_list_create'),
    path('archivos/<int:pk>/', ArchivoExcelDetailView.as_view(), name='archivo_detail'),
    path('archivos/<int:archivo_id>/columnas/', columnas_disponibles_view, name='archivo_columnas'),
    path('archivos/<int:archivo_id>/resumen/', resumen_archivo_view, name='archivo_resumen'),

    # Gestión de registros
    path('registros/', RegistroDatoListView.as_view(), name='registro_list'),
    path('registros/buscar/', buscar_registros_view, name='registro_buscar'),

    # Estadísticas y análisis
    path('estadisticas/', estadisticas_view, name='estadisticas'),
    path('valores-unicos/', valores_unicos_view, name='valores_unicos'),
    path('generar-grafico/', generar_grafico_view, name='generar_grafico'),

    # Carga masiva
    path('carga-masiva/', carga_masiva_view, name='carga_masiva'),
]