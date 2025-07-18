from django.urls import path  # Corregido
from .views import (
    ReporteGeneradoListView,
    ReporteGeneradoDetailView,
    generar_reporte_pdf_view,
    generar_reporte_excel_view,
    descargar_reporte_view,
    generar_grafico_view,
    ConfiguracionGraficoListCreateView,
    ConfiguracionGraficoDetailView,
    exportar_datos_view,
    estadisticas_reportes_view
)

app_name = 'reportes'

urlpatterns = [
    # Gestión de reportes
    path('reportes/', ReporteGeneradoListView.as_view(), name='reporte_list'),
    path('reportes/<int:pk>/', ReporteGeneradoDetailView.as_view(), name='reporte_detail'),
    path('reportes/<int:reporte_id>/descargar/', descargar_reporte_view, name='reporte_descargar'),

    # Generación de reportes
    path('generar-pdf/', generar_reporte_pdf_view, name='generar_pdf'),
    path('generar-excel/', generar_reporte_excel_view, name='generar_excel'),
    path('exportar-datos/', exportar_datos_view, name='exportar_datos'),

    # Gráficos
    path('generar-grafico/', generar_grafico_view, name='generar_grafico'),
    path('configuraciones-graficos/', ConfiguracionGraficoListCreateView.as_view(), name='config_grafico_list'),
    path('configuraciones-graficos/<int:pk>/', ConfiguracionGraficoDetailView.as_view(), name='config_grafico_detail'),

    # Estadísticas
    path('estadisticas/', estadisticas_reportes_view, name='estadisticas_reportes'),
]