import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')  # Para usar matplotlib sin GUI
import seaborn as sns
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import base64
from typing import Dict, List, Any, Tuple
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
import os
import tempfile
from apps.archivos.models import ArchivoExcel, RegistroDato
from .models import ReporteGenerado


class GeneradorReportes:
    """
    Utilidad para generar reportes en diferentes formatos
    """

    def __init__(self, usuario, titulo: str = "Reporte"):
        self.usuario = usuario
        self.titulo = titulo
        self.filtros = {}
        self.datos = []

    def aplicar_filtros(self, filtros: Dict[str, Any]):
        """
        Aplica filtros a los datos
        """
        self.filtros = filtros
        queryset = RegistroDato.objects.all()

        if 'archivo_ids' in filtros and filtros['archivo_ids']:
            queryset = queryset.filter(archivo_id__in=filtros['archivo_ids'])

        if 'anio' in filtros and filtros['anio']:
            queryset = queryset.filter(anio=filtros['anio'])

        if 'dependencia' in filtros and filtros['dependencia']:
            queryset = queryset.filter(dependencia__icontains=filtros['dependencia'])

        if 'indicador' in filtros and filtros['indicador']:
            queryset = queryset.filter(indicador__icontains=filtros['indicador'])

        if 'fecha_desde' in filtros and filtros['fecha_desde']:
            queryset = queryset.filter(archivo__fecha_subida__date__gte=filtros['fecha_desde'])

        if 'fecha_hasta' in filtros and filtros['fecha_hasta']:
            queryset = queryset.filter(archivo__fecha_subida__date__lte=filtros['fecha_hasta'])

        self.datos = queryset.select_related('archivo', 'archivo__usuario_subida')

    def generar_pdf(self, incluir_graficos: bool = True) -> Tuple[bool, str, ContentFile]:
        """
        Genera un reporte en formato PDF
        """
        try:
            # Crear archivo temporal
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            story = []

            # Estilos
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER
            )

            # Título
            story.append(Paragraph(self.titulo, title_style))
            story.append(Spacer(1, 12))

            # Información del reporte
            info_data = [
                ['Generado por:', self.usuario.get_full_name()],
                ['Fecha:', timezone.now().strftime('%d/%m/%Y %H:%M')],
                ['Total registros:', str(len(self.datos))],
            ]

            if self.filtros:
                if 'anio' in self.filtros and self.filtros['anio']:
                    info_data.append(['Año:', str(self.filtros['anio'])])
                if 'dependencia' in self.filtros and self.filtros['dependencia']:
                    info_data.append(['Dependencia:', self.filtros['dependencia']])

            info_table = Table(info_data, colWidths=[2 * inch, 3 * inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(info_table)
            story.append(Spacer(1, 20))

            # Gráficos si se solicitan
            if incluir_graficos and len(self.datos) > 0:
                graficos = self._generar_graficos()
                for grafico in graficos:
                    story.append(grafico)
                    story.append(Spacer(1, 20))

            # Tabla de datos (primeros 100 registros)
            if len(self.datos) > 0:
                story.append(Paragraph("Datos del Reporte", styles['Heading2']))
                story.append(Spacer(1, 12))

                # Preparar datos para la tabla
                datos_limitados = self.datos[:100]  # Limitar para no sobrecargar el PDF

                if datos_limitados:
                    # Encabezados
                    headers = ['Archivo', 'Año', 'Dependencia', 'Indicador']
                    data = [headers]

                    # Datos
                    for registro in datos_limitados:
                        row = [
                            registro.archivo.nombre_archivo[:30] + '...' if len(
                                registro.archivo.nombre_archivo) > 30 else registro.archivo.nombre_archivo,
                            str(registro.anio) if registro.anio else '',
                            registro.dependencia[:30] + '...' if registro.dependencia and len(
                                registro.dependencia) > 30 else registro.dependencia or '',
                            registro.indicador[:40] + '...' if registro.indicador and len(
                                registro.indicador) > 40 else registro.indicador or ''
                        ]
                        data.append(row)

                    # Crear tabla
                    table = Table(data, colWidths=[2 * inch, 0.8 * inch, 1.5 * inch, 2 * inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))

                    story.append(table)

                    if len(self.datos) > 100:
                        story.append(Spacer(1, 12))
                        story.append(Paragraph(f"Mostrando los primeros 100 registros de {len(self.datos)} total.",
                                               styles['Normal']))

            # Construir PDF
            doc.build(story)
            buffer.seek(0)

            # Crear archivo Django
            pdf_file = ContentFile(buffer.read())
            filename = f"reporte_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"

            return True, "PDF generado exitosamente", pdf_file

        except Exception as e:
            return False, f"Error al generar PDF: {str(e)}", None

    def _generar_graficos(self) -> List[Image]:
        """
        Genera gráficos para incluir en el reporte
        """
        graficos = []

        try:
            # Configurar matplotlib
            plt.style.use('default')
            fig_size = (8, 6)

            # Gráfico por dependencia
            if len(self.datos) > 0:
                dependencias = {}
                for registro in self.datos:
                    dep = registro.dependencia or 'Sin dependencia'
                    dependencias[dep] = dependencias.get(dep, 0) + 1

                if dependencias:
                    plt.figure(figsize=fig_size)
                    plt.bar(dependencias.keys(), dependencias.values())
                    plt.title('Registros por Dependencia')
                    plt.xlabel('Dependencia')
                    plt.ylabel('Cantidad')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()

                    # Guardar en memoria
                    img_buffer = BytesIO()
                    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                    img_buffer.seek(0)

                    # Crear imagen para ReportLab
                    img = Image(img_buffer, width=6 * inch, height=4 * inch)
                    graficos.append(img)

                    plt.close()

            # Gráfico por año
            if len(self.datos) > 0:
                anos = {}
                for registro in self.datos:
                    ano = registro.anio or 'Sin año'
                    anos[ano] = anos.get(ano, 0) + 1

                if anos and len(anos) > 1:
                    plt.figure(figsize=fig_size)
                    plt.plot(list(anos.keys()), list(anos.values()), marker='o')
                    plt.title('Registros por Año')
                    plt.xlabel('Año')
                    plt.ylabel('Cantidad')
                    plt.grid(True)
                    plt.tight_layout()

                    # Guardar en memoria
                    img_buffer = BytesIO()
                    plt.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
                    img_buffer.seek(0)

                    # Crear imagen para ReportLab
                    img = Image(img_buffer, width=6 * inch, height=4 * inch)
                    graficos.append(img)

                    plt.close()

        except Exception as e:
            print(f"Error al generar gráficos: {str(e)}")

        return graficos

    def generar_excel(self) -> Tuple[bool, str, ContentFile]:
        """
        Genera un reporte en formato Excel
        """
        try:
            # Preparar datos
            datos_excel = []

            for registro in self.datos:
                fila = {
                    'Archivo': registro.archivo.nombre_archivo,
                    'Número Fila': registro.numero_fila,
                    'Año': registro.anio,
                    'Dependencia': registro.dependencia,
                    'Indicador': registro.indicador,
                    'Valor': registro.valor,
                    'Fecha Subida': registro.archivo.fecha_subida,
                    'Usuario Subida': registro.archivo.usuario_subida.get_full_name()
                }

                # Agregar datos JSON como columnas adicionales
                if registro.datos:
                    for key, value in registro.datos.items():
                        if key not in fila:
                            fila[f"Data_{key}"] = value

                datos_excel.append(fila)

            # Crear DataFrame
            df = pd.DataFrame(datos_excel)

            # Guardar en memoria
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Datos', index=False)

                # Agregar hoja de resumen
                resumen_data = {
                    'Métrica': ['Total Registros', 'Archivos Incluidos', 'Dependencias Únicas', 'Años Únicos'],
                    'Valor': [
                        len(self.datos),
                        len(set(r.archivo.id for r in self.datos)),
                        len(set(r.dependencia for r in self.datos if r.dependencia)),
                        len(set(r.anio for r in self.datos if r.anio))
                    ]
                }

                pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)

            buffer.seek(0)

            # Crear archivo Django
            excel_file = ContentFile(buffer.read())
            filename = f"reporte_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

            return True, "Excel generado exitosamente", excel_file

        except Exception as e:
            return False, f"Error al generar Excel: {str(e)}", None

    def guardar_reporte(self, tipo_reporte: str, archivo_generado: ContentFile) -> ReporteGenerado:
        """
        Guarda el reporte en la base de datos
        """
        reporte = ReporteGenerado.objects.create(
            titulo=self.titulo,
            tipo_reporte=tipo_reporte,
            filtros_aplicados=self.filtros,
            usuario_generador=self.usuario
        )

        # Guardar archivo
        filename = f"reporte_{reporte.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{tipo_reporte}"
        reporte.archivo_generado.save(filename, archivo_generado)

        # Relacionar archivos incluidos
        if 'archivo_ids' in self.filtros:
            archivos = ArchivoExcel.objects.filter(id__in=self.filtros['archivo_ids'])
            reporte.archivos_incluidos.set(archivos)

        return reporte


class GeneradorGraficos:
    """
    Utilidad para generar gráficos estadísticos
    """

    @staticmethod
    def generar_grafico_barras(datos: Dict[str, Any], titulo: str = "Gráfico") -> str:
        """
        Genera un gráfico de barras y retorna como base64
        """
        try:
            plt.figure(figsize=(10, 6))
            plt.bar(datos['labels'], datos['values'])
            plt.title(titulo)
            plt.xlabel('Categorías')
            plt.ylabel('Valores')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Convertir a base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)

            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()

            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            print(f"Error al generar gráfico: {str(e)}")
            return None

    @staticmethod
    def generar_grafico_lineas(datos: Dict[str, Any], titulo: str = "Gráfico") -> str:
        """
        Genera un gráfico de líneas y retorna como base64
        """
        try:
            plt.figure(figsize=(10, 6))
            plt.plot(datos['labels'], datos['values'], marker='o')
            plt.title(titulo)
            plt.xlabel('Categorías')
            plt.ylabel('Valores')
            plt.grid(True)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()

            # Convertir a base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)

            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()

            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            print(f"Error al generar gráfico: {str(e)}")
            return None

    @staticmethod
    def generar_grafico_circular(datos: Dict[str, Any], titulo: str = "Gráfico") -> str:
        """
        Genera un gráfico circular y retorna como base64
        """
        try:
            plt.figure(figsize=(8, 8))
            plt.pie(datos['values'], labels=datos['labels'], autopct='%1.1f%%')
            plt.title(titulo)
            plt.axis('equal')

            # Convertir a base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)

            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close()

            return f"data:image/png;base64,{image_base64}"

        except Exception as e:
            print(f"Error al generar gráfico: {str(e)}")
            return None