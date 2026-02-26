# adminendpoints/admin_reportes.py
"""
Endpoints del Panel Admin — REPORTES
Genera datos listos para exportar a CSV desde el frontend
Cubre: miembros, postulantes, cursos, instructores, eventos, inscripciones
SP usados: SP_GU_EXPORTAR_MIEMBROS_CSV, SP_REP_*
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from Conexionsql import get_connection

app = FastAPI()


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
            conn.commit()
            return [{"status": "SUCCESS"}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# GET /miembros  — reporte completo de miembros
# =============================================
@app.get("/miembros", tags=["Admin - Reportes"])
def reporte_miembros(
    estado: Optional[str] = None,
    rango: Optional[str] = None,
    departamento: Optional[str] = None,
):
    """
    Todos los campos para exportar a CSV:
    nombre, apellido, dni, edad, genero, email, teléfono,
    departamento, profesión, legajo, rango, jefatura, estado, fecha_ingreso.
    """
    rows = _sp("SP_GU_EXPORTAR_MIEMBROS_CSV", (estado, rango, departamento))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /postulantes  — reporte de postulantes
# =============================================
@app.get("/postulantes", tags=["Admin - Reportes"])
def reporte_postulantes(
    departamento: Optional[str] = None,
    solo_pendientes: bool = False,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    rows = _sp("SP_REP_EXPORTAR_POSTULANTES", (
        departamento, int(solo_pendientes), fecha_desde, fecha_hasta,
    ))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /instructores  — reporte de instructores
# =============================================
@app.get("/instructores", tags=["Admin - Reportes"])
def reporte_instructores(
    especialidad: Optional[str] = None,
    estado: Optional[str] = None,
):
    rows = _sp("SP_REP_EXPORTAR_INSTRUCTORES", (especialidad, estado))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /cursos  — reporte de cursos
# =============================================
@app.get("/cursos", tags=["Admin - Reportes"])
def reporte_cursos(
    categoria: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    rows = _sp("SP_REP_EXPORTAR_CURSOS", (categoria, estado, fecha_desde, fecha_hasta))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /inscripciones-cursos  — reporte de inscripciones a cursos
# =============================================
@app.get("/inscripciones-cursos", tags=["Admin - Reportes"])
def reporte_inscripciones_cursos(
    id_curso: Optional[int] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    rows = _sp("SP_REP_EXPORTAR_INSCRIPCIONES_CURSOS", (
        id_curso, estado, fecha_desde, fecha_hasta,
    ))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /eventos  — reporte de eventos
# =============================================
@app.get("/eventos", tags=["Admin - Reportes"])
def reporte_eventos(
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    rows = _sp("SP_REP_EXPORTAR_EVENTOS", (tipo, estado, fecha_desde, fecha_hasta))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /inscripciones-eventos  — reporte de inscripciones a eventos
# =============================================
@app.get("/inscripciones-eventos", tags=["Admin - Reportes"])
def reporte_inscripciones_eventos(
    id_evento: Optional[int] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    rows = _sp("SP_REP_EXPORTAR_INSCRIPCIONES_EVENTOS", (
        id_evento, estado, fecha_desde, fecha_hasta,
    ))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /departamentos  — reporte por departamento
# =============================================
@app.get("/departamentos", tags=["Admin - Reportes"])
def reporte_departamentos():
    """Distribución de miembros y postulantes por departamento."""
    rows = _sp("SP_REP_MIEMBROS_POR_DEPARTAMENTO")
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /resumen-general  — un solo endpoint con todos los KPIs para imprimir
# =============================================
@app.get("/resumen-general", tags=["Admin - Reportes"])
def resumen_general():
    """
    Consolidado completo del sistema:
    totales de miembros, cursos, eventos, inscripciones, etc.
    Ideal para la página de impresión / exportar PDF del dashboard.
    """
    rows = _sp("SP_DASHBOARD_KPI_PRINCIPAL")
    return {"status": "SUCCESS", "data": rows[0] if rows else {}}
