# adminendpoints/admin_eventos.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import date, time

from Conexionsql import get_connection

# 🔥 SIN PREFIX - El prefix se define en main.py
router = APIRouter(tags=["Admin - Eventos"])


# ============================================================
# Helper para ejecutar SP
# ============================================================

def _sp(nombre: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(params))
            sql = f"EXEC {nombre} {placeholders}" if params else f"EXEC {nombre}"
            cursor.execute(sql, params)

            rows = []
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                rows = [dict(zip(cols, r)) for r in cursor.fetchall()]

            conn.commit()  # ✅ SIEMPRE

            return rows if rows else [{"status": "SUCCESS"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# LISTAR
# ============================================================

@router.get("/")
def listar_eventos(
    busqueda: Optional[str] = None,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    pagina: int = 1,
    por_pagina: int = 10,
):
    rows = _sp("SP_EV_LISTAR", (
        busqueda, tipo, estado, fecha_desde, fecha_hasta, pagina, por_pagina,
    ))

    total = _sp("SP_EV_CONTAR", (
        busqueda, tipo, estado, fecha_desde, fecha_hasta
    ))

    return {
        "status": "SUCCESS",
        "total": total[0]["total"] if total else 0,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "data": rows,
    }


# ============================================================
# DETALLE
# ============================================================

@router.get("/{id_evento}")
def detalle_evento(id_evento: int):
    rows = _sp("SP_EV_DETALLE", (id_evento,))
    if not rows:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return {"status": "SUCCESS", "data": rows[0]}


# ============================================================
# CREAR
# ============================================================

class EventoCrear(BaseModel):
    titulo: str
    tipo: str
    descripcion: Optional[str] = None
    fecha: date
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    ubicacion: Optional[str] = None
    id_instructor: Optional[int] = None
    admin_id: int


@router.post("/")
def crear_evento(body: EventoCrear):
    rows = _sp("SP_EV_CREAR", (
        body.titulo, body.tipo, body.descripcion,
        body.fecha, body.hora_inicio, body.hora_fin,
        body.ubicacion, body.id_instructor, body.admin_id,
    ))

    res = rows[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))
    
    return res


# ============================================================
# ACTUALIZAR
# ============================================================

class EventoActualizar(BaseModel):
    id_evento: int
    titulo: str
    tipo: str
    descripcion: Optional[str] = None
    fecha: date
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    ubicacion: Optional[str] = None
    id_instructor: Optional[int] = None
    estado: str
    admin_id: int


@router.put("/{id_evento}")
def actualizar_evento(id_evento: int, body: EventoActualizar):
    rows = _sp("SP_EV_ACTUALIZAR", (
        id_evento, body.titulo, body.tipo, body.descripcion,
        body.fecha, body.hora_inicio, body.hora_fin,
        body.ubicacion, body.id_instructor, body.estado, body.admin_id,
    ))

    res = rows[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))

    return res


# ============================================================
# CAMBIAR ESTADO
# ============================================================

class CambioEstadoEvento(BaseModel):
    nuevo_estado: str
    admin_id: int


@router.put("/{id_evento}/estado")
def cambiar_estado_evento(id_evento: int, body: CambioEstadoEvento):
    rows = _sp("SP_EV_CAMBIAR_ESTADO", (
        id_evento, body.nuevo_estado, body.admin_id
    ))

    res = rows[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))

    return res


# ============================================================
# ELIMINAR
# ============================================================

@router.delete("/{id_evento}")
def eliminar_evento(id_evento: int, admin_id: int):
    """
    Eliminar un evento
    - id_evento: ID del evento a eliminar (path parameter)
    - admin_id: ID del administrador que realiza la acción (query parameter)
    """
    rows = _sp("SP_EV_ELIMINAR", (id_evento, admin_id))

    res = rows[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))

    return res