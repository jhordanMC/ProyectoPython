# adminendpoints/admin_dashboard.py
"""
Endpoints del Panel Admin — DASHBOARD
KPIs, gráficos y actividad reciente
SP usados: SP_DS_KPI_PRINCIPAL, SP_DS_GRAFICO_*,
           SP_DS_ACTIVIDAD_RECIENTE
"""
from fastapi import APIRouter, HTTPException
from Conexionsql import get_connection

router = APIRouter()


# ------------------------------------------
# Utilidad: ejecutar SP → lista de dicts
# ------------------------------------------
def _sp(nombre: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(params))
            sql = f"EXEC {nombre} {placeholders}" if params else f"EXEC {nombre}"
            cursor.execute(sql, params)
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, row)) for row in cursor.fetchall()]
            return [{"status": "SUCCESS"}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# GET /  — KPIs principales (tarjetas del dashboard)
# =============================================
@router.get("/", tags=["Admin - Dashboard"])
def kpi_principal():
    rows = _sp("SP_DS_RESUMEN_RANGOS")
    return {"status": "SUCCESS", "data": rows[0] if rows else {}}


# =============================================
# GET /graficos/miembros-rango
# =============================================
@router.get("/graficos/miembros-rango", tags=["Admin - Dashboard"])
def grafico_miembros_por_rango():
    """
    Distribución de miembros por rango (para gráfico de barras/pie).
    
    SP: SP_DS_GRAFICO_MIEMBROS_RANGO
    Retorna: [{rango: str, cantidad: int}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_GRAFICO_MIEMBROS_RANGO")}


# =============================================
# GET /graficos/miembros-estado
# =============================================
@router.get("/graficos/miembros-estado", tags=["Admin - Dashboard"])
def grafico_miembros_por_estado():
    """
    Activo / Suspendido / Baja (para gráfico donut).
    
    SP: SP_DS_GRAFICO_MIEMBROS_ESTADO
    Retorna: [{estado: str, cantidad: int, porcentaje: decimal}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_GRAFICO_MIEMBROS_ESTADO")}


# =============================================
# GET /graficos/postulantes-mes
# =============================================
@router.get("/graficos/postulantes-mes", tags=["Admin - Dashboard"])
def grafico_postulantes_por_mes():
    """
    Postulantes registrados por mes — último año (gráfico de líneas).
    
    SP: SP_DS_GRAFICO_POSTULANTES_MES
    Retorna: [{anio: int, mes_num: int, mes_label: str, total: int}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_GRAFICO_POSTULANTES_MES")}


# =============================================
# GET /graficos/miembros-departamento
# =============================================
@router.get("/graficos/miembros-departamento", tags=["Admin - Dashboard"])
def grafico_miembros_por_departamento():
    """
    Miembros por departamento (gráfico de barras horizontales).
    
    SP: SP_DS_GRAFICO_MIEMBROS_DEPARTAMENTO
    Retorna: [{departamento: str, cantidad: int}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_GRAFICO_MIEMBROS_DEPARTAMENTO")}


# =============================================
# GET /graficos/edades-miembros
# =============================================
@router.get("/graficos/edades-miembros", tags=["Admin - Dashboard"])
def grafico_rango_edades():
    """
    Distribución por rangos de edad (18-25, 26-35, 36-45, 46-55, 56+).
    
    SP: SP_DS_GRAFICO_EDADES_MIEMBROS
    Retorna: [{rango_edad: str, cantidad: int}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_GRAFICO_EDADES_MIEMBROS")}


# =============================================
# GET /graficos/ocupacion-cursos
# =============================================
@router.get("/graficos/ocupacion-cursos", tags=["Admin - Dashboard"])
def grafico_ocupacion_cursos():
    """
    Ocupación de cursos activos (TOP 8 por porcentaje de ocupación).
    
    SP: SP_DS_GRAFICO_OCUPACION_CURSOS
    Retorna: [{titulo: str, inscritos: int, cupos: int, disponibles: int, pct_ocupacion: decimal}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_GRAFICO_OCUPACION_CURSOS")}


# =============================================
# GET /actividad-reciente?top=15
# =============================================
@router.get("/actividad-reciente", tags=["Admin - Dashboard"])
def actividad_reciente(top: int = 15):
    """
    Feed de los últimos cambios: postulantes, miembros, historial.
    
    SP: SP_DS_ACTIVIDAD_RECIENTE
    Parámetros:
        - top: cantidad de registros a retornar (default: 15)
    Retorna: [{tipo: str, descripcion: str, detalle: str, fecha: datetime}, ...]
    """
    return {"status": "SUCCESS", "data": _sp("SP_DS_ACTIVIDAD_RECIENTE", (top,))}