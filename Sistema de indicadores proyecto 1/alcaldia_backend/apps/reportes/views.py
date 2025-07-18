import os

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse, JsonResponse
from django.core.files.base import ContentFile
from django.utils import timezone
from .models import ReporteGenerado, ConfiguracionGrafico
from .serializers import (
    ReporteGeneradoSerializer,
    ConfiguracionGraficoSerializer,
    GenerarReporteSerializer,
    ExportarDatosSerializer
)
from .utils import GeneradorReportes, GeneradorGraficos
from apps.archivos.models import RegistroDato
from apps.archivos.utils import FiltrosExcel
import json
from django.core.exceptions import ValidationError


class ReporteGeneradoListView(generics.ListAPIView):
    """
    Vista para listar reportes generados
    """
    serializer_class = ReporteGeneradoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ReporteGenerado.objects.all()

        # Filtrar por usuario si no es admin
        if not self.request.user.is_admin():
            queryset = queryset.filter(usuario_generador=self.request.user)

        # Filtros opcionales
        tipo_reporte = self.request.query_params.get('tipo_reporte')
        if tipo_reporte:
            queryset = queryset.filter(tipo_reporte=tipo_reporte)

        return queryset.order_by('-fecha_generacion')


class ReporteGeneradoDetailView(generics.RetrieveDestroyAPIView):
    """
    Vista para ver y eliminar reportes específicos
    """
    serializer_class = ReporteGeneradoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ReporteGenerado.objects.all()

        # Filtrar por usuario si no es admin
        if not self.request.user.is_admin():
            queryset = queryset.filter(usuario_generador=self.request.user)

        return queryset


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_reporte_pdf_view(request):
    """
    Vista para generar reporte en PDF
    """
    try:
        # Validar datos
        serializer = GenerarReporteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Obtener parámetros
        titulo = serializer.validated_data.get('titulo', 'Reporte de Indicadores')
        filtros = serializer.validated_data.get('filtros', {})
        incluir_graficos = serializer.validated_data.get('incluir_graficos', True)

        # Crear generador de reportes
        generador = GeneradorReportes(request.user, titulo)
        generador.aplicar_filtros(filtros)

        # Generar PDF
        success, mensaje, pdf_file = generador.generar_pdf(incluir_graficos)

        if success:
            # Guardar en base de datos
            reporte = generador.guardar_reporte('pdf', pdf_file)

            # Serializar respuesta
            reporte_serializer = ReporteGeneradoSerializer(reporte)

            return Response({
                'success': True,
                'mensaje': mensaje,
                'reporte': reporte_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': mensaje
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error al generar reporte: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_reporte_excel_view(request):
    """
    Vista para generar reporte en Excel
    """
    try:
        # Validar datos
        serializer = GenerarReporteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Obtener parámetros
        titulo = serializer.validated_data.get('titulo', 'Reporte de Indicadores')
        filtros = serializer.validated_data.get('filtros', {})

        # Crear generador de reportes
        generador = GeneradorReportes(request.user, titulo)
        generador.aplicar_filtros(filtros)

        # Generar Excel
        success, mensaje, excel_file = generador.generar_excel()

        if success:
            # Guardar en base de datos
            reporte = generador.guardar_reporte('excel', excel_file)

            # Serializar respuesta
            reporte_serializer = ReporteGeneradoSerializer(reporte)

            return Response({
                'success': True,
                'mensaje': mensaje,
                'reporte': reporte_serializer.data
            })
        else:
            return Response({
                'success': False,
                'error': mensaje
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error al generar reporte: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def descargar_reporte_view(request, reporte_id):
    """
    Vista para descargar un reporte generado
    """
    try:
        # Obtener reporte
        queryset = ReporteGenerado.objects.all()
        if not request.user.is_admin():
            queryset = queryset.filter(usuario_generador=request.user)

        reporte = queryset.get(id=reporte_id)

        if not reporte.archivo_generado:
            return Response({'error': 'Archivo no disponible'}, status=404)

        # VALIDACIÓN NUEVA:
        if not os.path.exists(reporte.archivo_generado.path):
            return Response({'error': 'El archivo ya no existe en el sistema'}, status=410)


        # Determinar content type
        content_type = 'application/octet-stream'
        if reporte.tipo_reporte == 'pdf':
            content_type = 'application/pdf'
        elif reporte.tipo_reporte == 'excel':
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # Preparar respuesta
        response = HttpResponse(
            reporte.archivo_generado.read(),
            content_type=content_type
        )

        filename = f"{reporte.titulo}_{timezone.now().strftime('%Y%m%d')}.{reporte.tipo_reporte}"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except ReporteGenerado.DoesNotExist:
        return Response({
            'error': 'Reporte no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except ReporteGenerado.DoesNotExist:
        return Response({'error': 'Reporte no encontrado'}, status=status.HTTP_404_NOT_FOUND)

    except ValidationError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({'error': f'Ocurrió un error inesperado: {str(e)}'},status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_grafico_view(request):
    """
    Vista para generar gráficos
    """
    try:
        tipo_grafico = request.data.get('tipo_grafico', 'bar')
        titulo = request.data.get('titulo', 'Gráfico')
        filtros = request.data.get('filtros', {})

        # Obtener datos filtrados
        registros = FiltrosExcel.filtrar_registros(filtros)

        # Preparar datos según el tipo de gráfico
        if tipo_grafico == 'dependencia':
            datos = {}
            for registro in registros:
                dep = registro.dependencia or 'Sin dependencia'
                datos[dep] = datos.get(dep, 0) + 1

        elif tipo_grafico == 'anio':
            datos = {}
            for registro in registros:
                anio = str(registro.anio) if registro.anio else 'Sin año'
                datos[anio] = datos.get(anio, 0) + 1

        elif tipo_grafico == 'indicador':
            datos = {}
            for registro in registros[:20]:  # Limitar a 20 para legibilidad
                ind = registro.indicador or 'Sin indicador'
                datos[ind] = datos.get(ind, 0) + 1
        else:
            return Response({
                'error': 'Tipo de gráfico no válido'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Preparar datos para el gráfico
        datos_grafico = {
            'labels': list(datos.keys()),
            'values': list(datos.values())
        }

        # Generar gráfico
        if request.data.get('formato') == 'base64':
            if tipo_grafico in ['dependencia', 'anio', 'indicador']:
                grafico_base64 = GeneradorGraficos.generar_grafico_barras(datos_grafico, titulo)
            else:
                grafico_base64 = GeneradorGraficos.generar_grafico_barras(datos_grafico, titulo)

            return Response({
                'success': True,
                'grafico': grafico_base64,
                'datos': datos_grafico
            })
        else:
            return Response({
                'success': True,
                'datos': datos_grafico,
                'titulo': titulo
            })

    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error al generar gráfico: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfiguracionGraficoListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear configuraciones de gráficos
    """
    serializer_class = ConfiguracionGraficoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConfiguracionGrafico.objects.filter(
            usuario_creador=self.request.user
        ).order_by('-fecha_creacion')

    def perform_create(self, serializer):
        serializer.save(usuario_creador=self.request.user)


class ConfiguracionGraficoDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar y eliminar configuraciones de gráficos
    """
    serializer_class = ConfiguracionGraficoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConfiguracionGrafico.objects.filter(
            usuario_creador=self.request.user
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def exportar_datos_view(request):
    """
    Vista para exportar datos filtrados
    """
    try:
        serializer = ExportarDatosSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        formato = serializer.validated_data.get('formato', 'excel')
        filtros = serializer.validated_data.get('filtros', {})
        incluir_metadatos = serializer.validated_data.get('incluir_metadatos', True)

        # Crear generador
        generador = GeneradorReportes(request.user, 'Exportación de Datos')
        generador.aplicar_filtros(filtros)

        if formato == 'excel':
            success, mensaje, archivo = generador.generar_excel()
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            extension = 'xlsx'
        else:
            return Response({
                'error': 'Formato no soportado'
            }, status=status.HTTP_400_BAD_REQUEST)

        if success:
            response = HttpResponse(
                archivo.read(),
                content_type=content_type
            )
            filename = f"exportacion_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response
        else:
            return Response({
                'error': mensaje
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({
            'error': f'Error al exportar datos: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estadisticas_reportes_view(request):
    """
    Vista para obtener estadísticas de reportes
    """
    try:
        queryset = ReporteGenerado.objects.all()

        if not request.user.is_admin():
            queryset = queryset.filter(usuario_generador=request.user)

        estadisticas = {
            'total_reportes': queryset.count(),
            'reportes_pdf': queryset.filter(tipo_reporte='pdf').count(),
            'reportes_excel': queryset.filter(tipo_reporte='excel').count(),
            'reportes_ultimo_mes': queryset.filter(
                fecha_generacion__gte=timezone.now() - timezone.timedelta(days=30)
            ).count(),
            'usuarios_activos': queryset.values(
                'usuario_generador').distinct().count() if request.user.is_admin() else 1
        }

        return Response(estadisticas)

    except Exception as e:
        return Response({
            'error': f'Error al obtener estadísticas: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)