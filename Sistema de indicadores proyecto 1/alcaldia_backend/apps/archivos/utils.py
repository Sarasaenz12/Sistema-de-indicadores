import pandas as pd
import openpyxl
from typing import Dict, List, Any, Tuple
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
import os
import magic
from .models import ArchivoExcel, RegistroDato


class ExcelProcessor:
    """
    Utilidad para procesar archivos Excel y extraer datos
    """

    def __init__(self, archivo_excel: ArchivoExcel):
        self.archivo_excel = archivo_excel
        self.df = None

    def validar_archivo(self, archivo: UploadedFile) -> Tuple[bool, str]:
        """
        Valida que el archivo sea un Excel válido
        """
        try:
            # Verificar tamaño
            if archivo.size > settings.MAX_UPLOAD_SIZE:
                return False, f"El archivo es demasiado grande. Máximo permitido: {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.1f}MB"

            # Verificar extensión
            ext = os.path.splitext(archivo.name)[1].lower()
            if ext not in settings.ALLOWED_EXTENSIONS:
                return False, f"Extensión no permitida. Extensiones válidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"

            # Verificar tipo MIME
            mime_type = magic.from_buffer(archivo.read(), mime=True)
            archivo.seek(0)  # Resetear el puntero del archivo

            valid_mime_types = [
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel'
            ]

            if mime_type not in valid_mime_types:
                return False, "El archivo no es un Excel válido"

            return True, "Archivo válido"

        except Exception as e:
            return False, f"Error al validar archivo: {str(e)}"

    def procesar_excel(self) -> Tuple[bool, str]:
        """
        Procesa el archivo Excel y extrae los datos
        """
        try:
            # Leer el archivo Excel
            archivo_path = self.archivo_excel.archivo.path

            # Intentar leer con pandas
            try:
                self.df = pd.read_excel(archivo_path, engine='openpyxl')
            except Exception:
                # Si falla, intentar con xlrd para archivos .xls
                self.df = pd.read_excel(archivo_path, engine='xlrd')

            # Limpiar nombres de columnas
            self.df.columns = [str(col).strip() for col in self.df.columns]

            # Remover filas completamente vacías
            self.df = self.df.dropna(how='all')

            # Actualizar metadatos del archivo
            self.archivo_excel.total_filas = len(self.df)
            self.archivo_excel.total_columnas = len(self.df.columns)
            self.archivo_excel.columnas_disponibles = list(self.df.columns)

            # Extraer información común si existe
            self._extraer_metadatos_comunes()

            self.archivo_excel.procesado = True
            self.archivo_excel.save()

            return True, "Archivo procesado exitosamente"

        except Exception as e:
            return False, f"Error al procesar archivo: {str(e)}"

    def _extraer_metadatos_comunes(self):
        """
        Extrae metadatos comunes del DataFrame para facilitar filtros
        """
        columnas_lower = [col.lower() for col in self.df.columns]

        # Buscar columna de año
        for col_name in ['año', 'anio', 'year', 'fecha']:
            if col_name in columnas_lower:
                idx = columnas_lower.index(col_name)
                col_original = self.df.columns[idx]
                try:
                    # Intentar extraer el año más común
                    year_values = pd.to_numeric(self.df[col_original], errors='coerce').dropna()
                    if not year_values.empty:
                        self.archivo_excel.anio = int(year_values.mode().iloc[0])
                        break
                except:
                    pass

        # Buscar columna de dependencia
        for col_name in ['dependencia', 'area', 'secretaria', 'oficina']:
            if col_name in columnas_lower:
                idx = columnas_lower.index(col_name)
                col_original = self.df.columns[idx]
                try:
                    # Usar la dependencia más común
                    dep_values = self.df[col_original].dropna()
                    if not dep_values.empty:
                        self.archivo_excel.dependencia = str(dep_values.mode().iloc[0])[:200]
                        break
                except:
                    pass

    def guardar_registros(self) -> Tuple[bool, str]:
        """
        Guarda cada fila del Excel como un registro en la base de datos
        """
        try:
            if self.df is None:
                return False, "No hay datos para guardar. Procese el archivo primero."

            registros_creados = 0

            # Eliminar registros anteriores si existen
            RegistroDato.objects.filter(archivo=self.archivo_excel).delete()

            for index, row in self.df.iterrows():
                # Convertir la fila a diccionario, manejando valores NaN
                datos_fila = {}
                for col in self.df.columns:
                    value = row[col]
                    if pd.isna(value):
                        datos_fila[col] = None
                    elif isinstance(value, (int, float)):
                        datos_fila[col] = value
                    else:
                        datos_fila[col] = str(value)

                # Crear el registro
                RegistroDato.objects.create(
                    archivo=self.archivo_excel,
                    numero_fila=index + 1,  # +1 para que coincida con Excel
                    datos=datos_fila
                )
                registros_creados += 1

            return True, f"Se crearon {registros_creados} registros exitosamente"

        except Exception as e:
            return False, f"Error al guardar registros: {str(e)}"


class FiltrosExcel:
    """
    Utilidad para aplicar filtros a los datos de Excel
    """

    @staticmethod
    def obtener_valores_unicos(campo: str, archivo_id: int = None) -> List[str]:
        """
        Obtiene valores únicos de un campo específico
        """
        queryset = RegistroDato.objects.all()

        if archivo_id:
            queryset = queryset.filter(archivo_id=archivo_id)

        if campo in ['anio', 'dependencia', 'indicador']:
            # Campos extraídos directamente
            valores = queryset.values_list(campo, flat=True).distinct()
            return [str(v) for v in valores if v is not None]
        else:
            # Buscar en el campo JSON
            registros = queryset.values_list('datos', flat=True)
            valores_unicos = set()

            for datos in registros:
                if isinstance(datos, dict) and campo in datos:
                    valor = datos[campo]
                    if valor is not None:
                        valores_unicos.add(str(valor))

            return sorted(list(valores_unicos))

    @staticmethod
    def filtrar_registros(filtros: Dict[str, Any]) -> List[RegistroDato]:
        """
        Filtra registros según los criterios especificados
        """
        queryset = RegistroDato.objects.all()

        # Filtros básicos
        if 'archivo_id' in filtros:
            queryset = queryset.filter(archivo_id=filtros['archivo_id'])

        if 'anio' in filtros:
            queryset = queryset.filter(anio=filtros['anio'])

        if 'dependencia' in filtros:
            queryset = queryset.filter(dependencia__icontains=filtros['dependencia'])

        if 'indicador' in filtros:
            queryset = queryset.filter(indicador__icontains=filtros['indicador'])

        # Filtros avanzados en JSON
        if 'filtros_json' in filtros:
            for campo, valor in filtros['filtros_json'].items():
                if valor:
                    queryset = queryset.filter(datos__has_key=campo)
                    if isinstance(valor, str):
                        queryset = queryset.filter(datos__contains={campo: valor})

        return queryset.select_related('archivo')


class EstadisticasExcel:
    """
    Utilidad para generar estadísticas de los datos de Excel
    """

    @staticmethod
    def resumen_archivo(archivo_id: int) -> Dict[str, Any]:
        """
        Genera un resumen estadístico de un archivo específico
        """
        archivo = ArchivoExcel.objects.get(id=archivo_id)
        registros = RegistroDato.objects.filter(archivo=archivo)

        resumen = {
            'nombre_archivo': archivo.nombre_archivo,
            'total_registros': registros.count(),
            'fecha_subida': archivo.fecha_subida,
            'columnas_disponibles': archivo.columnas_disponibles,
            'anos_disponibles': list(registros.values_list('anio', flat=True).distinct()),
            'dependencias_disponibles': list(registros.values_list('dependencia', flat=True).distinct()),
            'indicadores_disponibles': list(registros.values_list('indicador', flat=True).distinct()),
        }

        # Limpiar valores None
        for key in ['anos_disponibles', 'dependencias_disponibles', 'indicadores_disponibles']:
            resumen[key] = [item for item in resumen[key] if item is not None]

        return resumen

    @staticmethod
    def datos_para_grafico(tipo_grafico: str, filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara datos para generar gráficos
        """
        registros = FiltrosExcel.filtrar_registros(filtros)

        if tipo_grafico == 'por_dependencia':
            datos = {}
            for registro in registros:
                dep = registro.dependencia or 'Sin dependencia'
                if dep not in datos:
                    datos[dep] = 0
                datos[dep] += 1

            return {
                'labels': list(datos.keys()),
                'values': list(datos.values()),
                'title': 'Registros por Dependencia'
            }

        elif tipo_grafico == 'por_ano':
            datos = {}
            for registro in registros:
                ano = registro.anio or 'Sin año'
                if ano not in datos:
                    datos[ano] = 0
                datos[ano] += 1

            return {
                'labels': list(datos.keys()),
                'values': list(datos.values()),
                'title': 'Registros por Año'
            }

        # Más tipos de gráficos se pueden agregar aquí
        return {'labels': [], 'values': [], 'title': 'Sin datos'}