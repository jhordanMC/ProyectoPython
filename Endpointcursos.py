# Endpointcursos.py
"""
Endpoints Públicos para la Web – CURSOS Y EVENTOS
Lista cursos activos, eventos y detalles para usuarios finales

✅ Usa los mismos SPs del panel admin
✅ Solo muestra cursos con estado 'Activo'
✅ Datos simplificados para el frontend público
"""
from fastapi import FastAPI, HTTPException, Path, Query
from typing import Optional
from Conexionsql import get_connection

app = FastAPI()

# =============================================
# Función genérica para ejecutar SP
# =============================================
def _sp(nombre: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(params))
            sql = f"EXEC {nombre} {placeholders}" if params else f"EXEC {nombre}"
            cursor.execute(sql, params)
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                rows = cursor.fetchall()
                
                # Convertir filas a diccionarios con tipos JSON serializables
                result = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(cols):
                        value = row[i]
                        # Convertir tipos no serializables
                        if value is not None:
                            # Datetime a string ISO
                            if hasattr(value, 'isoformat'):
                                value = value.isoformat()
                            # Decimal a float
                            elif hasattr(value, '__float__'):
                                value = float(value)
                        row_dict[col] = value
                    result.append(row_dict)
                
                return result
            conn.commit()
            return [{"status": "SUCCESS"}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# ENDPOINTS PÚBLICOS PARA CURSOS
# =============================================

@app.get("/activos", tags=["Web - Cursos"])
def listar_cursos_activos(
    categoria: Optional[str] = None,
    modalidad: Optional[str] = None,
    busqueda: Optional[str] = None
):
    """
    Lista todos los cursos ACTIVOS para mostrar en la web pública.
    
    📋 Campos devueltos:
    - id_curso (o id)
    - titulo
    - categoria
    - duracion
    - modalidad
    - fecha_inicio
    - fecha_fin
    - instructor (nombre completo)
    
    🔍 Filtros opcionales:
    - categoria: Básico, Intermedio, Avanzado, Especializado
    - modalidad: Virtual, Presencial, Semipresencial
    - busqueda: Búsqueda por texto en título
    
    🔥 Usa: SP_LISTAR_CURSOSWEB con estado='Activo'
    
    📍 URL final: GET /api/cursos/activos
    """
    # Siempre filtramos por estado='Activo' para mostrar solo cursos públicos
    resultados = _sp("SP_LISTAR_CURSOSWEB", (
        categoria,
        modalidad,
        "Activo",  # Solo cursos activos
        busqueda
    ))
    
    # Ordenar por fecha de inicio (más próximos primero)
    if resultados:
        try:
            # Función segura para obtener fecha
            def get_fecha_segura(curso):
                fecha = curso.get('fecha_inicio')
                if fecha is None:
                    return '9999-12-31'
                # Si es datetime, convertir a string
                if hasattr(fecha, 'strftime'):
                    return fecha.strftime('%Y-%m-%d')
                # Si ya es string, retornar
                return str(fecha)
            
            resultados.sort(key=get_fecha_segura)
        except Exception as e:
            print(f"⚠️ No se pudo ordenar por fecha: {e}")
            # Continuar sin ordenar
    
    return {
        "status": "SUCCESS",
        "total": len(resultados),
        "cursos": resultados
    }


@app.get("/proximo", tags=["Web - Cursos"])
def obtener_curso_mas_proximo():
    """
    Obtiene el curso más próximo a iniciar (para destacar en el frontend).
    
    📋 Devuelve el curso con la fecha_inicio más cercana a hoy.
    
    🔥 Usa: SP_LISTAR_CURSOSWEB y selecciona el más próximo
    
    📍 URL final: GET /api/cursos/proximo
    """
    from datetime import datetime
    
    # Obtener todos los cursos activos
    resultados = _sp("SP_LISTAR_CURSOSWEB", (None, None, "Activo", None))
    
    if not resultados:
        return {
            "status": "SUCCESS",
            "curso_proximo": None,
            "mensaje": "No hay cursos programados"
        }
    
    # Filtrar solo cursos futuros y ordenar por fecha
    hoy = datetime.now().date()
    cursos_futuros = []
    
    for curso in resultados:
        fecha_inicio_str = curso.get('fecha_inicio')
        if fecha_inicio_str:
            try:
                # Intentar parsear la fecha en diferentes formatos
                if isinstance(fecha_inicio_str, str):
                    # Formato ISO: 2025-01-10
                    fecha_inicio = datetime.strptime(fecha_inicio_str[:10], '%Y-%m-%d').date()
                else:
                    # Si ya es datetime
                    fecha_inicio = fecha_inicio_str.date() if hasattr(fecha_inicio_str, 'date') else fecha_inicio_str
                
                if fecha_inicio >= hoy:
                    curso['_fecha_inicio_date'] = fecha_inicio
                    cursos_futuros.append(curso)
            except:
                continue
    
    if not cursos_futuros:
        return {
            "status": "SUCCESS",
            "curso_proximo": None,
            "mensaje": "No hay cursos programados próximamente"
        }
    
    # Ordenar por fecha y tomar el más próximo
    curso_proximo = sorted(cursos_futuros, key=lambda x: x['_fecha_inicio_date'])[0]
    
    # Limpiar el campo temporal
    del curso_proximo['_fecha_inicio_date']
    
    return {
        "status": "SUCCESS",
        "curso_proximo": curso_proximo
    }


@app.get("/categorias", tags=["Web - Cursos"])
def obtener_categorias():
    """
    Lista todas las categorías disponibles con el conteo de cursos activos.
    
    📋 Devuelve:
    - categorias: Lista de categorías con su conteo
    
    Útil para filtros dinámicos en el frontend.
    
    📍 URL final: GET /api/cursos/categorias
    """
    # Obtener todos los cursos activos
    resultados = _sp("SP_LISTAR_CURSOSWEB", (None, None, "Activo", None))
    
    # Contar por categoría
    categorias_count = {}
    for curso in resultados:
        cat = curso.get('categoria', 'Sin categoría')
        categorias_count[cat] = categorias_count.get(cat, 0) + 1
    
    categorias = [
        {"nombre": cat, "total": count}
        for cat, count in sorted(categorias_count.items())
    ]
    
    return {
        "status": "SUCCESS",
        "categorias": categorias
    }


@app.get("/modalidades", tags=["Web - Cursos"])
def obtener_modalidades():
    """
    Lista todas las modalidades disponibles con el conteo de cursos activos.
    
    📋 Devuelve:
    - modalidades: Lista de modalidades con su conteo
    
    Útil para filtros dinámicos en el frontend.
    
    📍 URL final: GET /api/cursos/modalidades
    """
    # Obtener todos los cursos activos
    resultados = _sp("SP_LISTAR_CURSOSWEB", (None, None, "Activo", None))
    
    # Contar por modalidad
    modalidades_count = {}
    for curso in resultados:
        mod = curso.get('modalidad', 'Sin modalidad')
        modalidades_count[mod] = modalidades_count.get(mod, 0) + 1
    
    modalidades = [
        {"nombre": mod, "total": count}
        for mod, count in sorted(modalidades_count.items())
    ]
    
    return {
        "status": "SUCCESS",
        "modalidades": modalidades
    }


@app.get("/{id_curso}", tags=["Web - Cursos"])
def obtener_detalle_curso(
    id_curso: int = Path(..., description="ID del curso", gt=0)
):
    """
    Obtiene los detalles completos de un curso específico.
    
    📋 Campos devueltos:
    - id_curso
    - titulo
    - categoria
    - duracion
    - modalidad
    - fecha_inicio
    - fecha_fin
    - descripcion
    - requisitos
    - instructor (nombre completo)
    - direccion (si es presencial)
    - enlace (si es virtual)
    
    🔥 Usa: SP_OBTENER_CURSOWEB
    
    📍 URL final: GET /api/cursos/{id_curso}
    """
    resultados = _sp("SP_OBTENER_CURSOWEB", (id_curso,))
    
    if not resultados or len(resultados) == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Curso con ID {id_curso} no encontrado"
        )
    
    curso = resultados[0]
    
    # Verificar que el curso esté activo (seguridad adicional)
    if curso.get('estado') != 'Activo':
        raise HTTPException(
            status_code=404,
            detail="Curso no disponible"
        )
    
    return {
        "status": "SUCCESS",
        "curso": curso
    }


# =============================================
# ENDPOINTS PARA EVENTOS/TALLERES
# =============================================

@app.get("/eventos/proximos", tags=["Web - Eventos"])
def obtener_proximos_eventos(
    limite: Optional[int] = Query(default=3, ge=1, le=10, description="Número de eventos a mostrar")
):
    """
    Obtiene los próximos eventos/talleres para mostrar en el sidebar.
    
    📋 Campos devueltos:
    - id, titulo, tipo, descripcion
    - fecha, hora_inicio, hora_fin, ubicacion
    - instructor, capacidad, inscritos, cupos_disponibles
    - estado, imagen, icono, modalidad
    
    🔍 Filtros aplicados automáticamente:
    - Solo eventos futuros (fecha >= hoy)
    - Solo estados: 'Programado' o 'En Curso'
    - Solo con cupos disponibles
    
    📥 Usa: SP_PROXIMOS_EVENTOS_WEB
    
    📍 URL final: GET /api/cursos/eventos/proximos?limite=3
    """
    resultados = _sp("SP_PROXIMOS_EVENTOS_WEB", (limite,))
    
    return {
        "status": "SUCCESS",
        "total": len(resultados),
        "eventos": resultados
    }