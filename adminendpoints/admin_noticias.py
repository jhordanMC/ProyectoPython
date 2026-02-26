# adminendpoints/admin_noticias.py
"""
Endpoints del Panel Admin — NOTICIAS / PUBLICACIONES
CRUD de publicaciones (creadas desde admin o sincronizadas desde Facebook)
Tabla: publicaciones
SP usados: SP_NOT_LISTAR, SP_NOT_CONTAR, SP_NOT_DETALLE, SP_NOT_CREAR,
           SP_NOT_EDITAR, SP_NOT_TOGGLE_DESTACADA, SP_NOT_TOGGLE_ACTIVA,
           SP_NOT_ELIMINAR, SP_NOT_ESTADISTICAS

✅ FOTO:
- El frontend envía multipart/form-data con el archivo binario directamente.
- Backend lee los bytes del archivo y los pasa como pyodbc.Binary a los SP.
- En LISTAR: se elimina "foto" del result para no romper JSON (bytes no serializa).
- En DETALLE: se devuelve foto_base64 y se elimina "foto" (bytes).
- GET /foto/{id}: endpoint dedicado para servir la imagen como respuesta binaria.
"""

from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from fastapi.responses import Response
from typing import Optional, Any, Dict, List
from datetime import datetime
from Conexionsql import get_connection
import base64
import pyodbc

router = APIRouter()


# ============================================================
# HELPERS
# ============================================================

def _bytes_to_b64(b: Optional[bytes]) -> Optional[str]:
    """Convierte bytes a base64 (sin dataURL)."""
    if b is None:
        return None
    return base64.b64encode(b).decode("utf-8")


def _parse_fecha(fecha_str: Optional[str]) -> Optional[datetime]:
    """Parsea 'YYYY-MM-DD' o ISO 8601 a datetime. Si falla, retorna None."""
    if not fecha_str:
        return None
    try:
        if "T" in fecha_str:
            return datetime.fromisoformat(fecha_str.replace("Z", "+00:00"))
        return datetime.strptime(fecha_str, "%Y-%m-%d")
    except Exception:
        return None


def _sp(nombre: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Ejecuta SP con parámetros posicionales (?)."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(params))
            sql = f"EXEC {nombre} {placeholders}" if params else f"EXEC {nombre}"
            cursor.execute(sql, params)

            results: List[Dict[str, Any]] = []
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                results = [dict(zip(cols, row)) for row in cursor.fetchall()]

            conn.commit()
            return results if results else [{"status": "SUCCESS"}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def ejecutar_sp_con_foto(sp_nombre: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ejecuta SP usando parámetros nombrados: {'@param': valor, ...}
    Se ejecuta como: EXEC SP @a=?, @b=?, ...
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            param_names = list(params.keys())
            param_placeholders = ", ".join([f"{name}=?" for name in param_names])
            sql = f"EXEC {sp_nombre} {param_placeholders}"

            valores = [params[name] for name in param_names]
            cursor.execute(sql, valores)

            results: List[Dict[str, Any]] = []
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                results = [dict(zip(cols, row)) for row in cursor.fetchall()]

            conn.commit()
            return results if results else [{"status": "SUCCESS", "mensaje": "SP ejecutado correctamente"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GET /listar — Listar publicaciones con filtros y paginación
# SP: SP_NOT_LISTAR + SP_NOT_CONTAR
# ============================================================
@router.get("/listar", tags=["Admin - Noticias"])
def listar_publicaciones(
    busqueda: Optional[str] = None,
    creado_por: Optional[str] = None,
    solo_activas: bool = True,
    solo_destacadas: bool = False,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 10
):
    try:
        rows = _sp("SP_NOT_LISTAR", (
            busqueda,
            creado_por,
            int(solo_activas),
            int(solo_destacadas),
            desde,
            hasta,
            pagina,
            por_pagina
        ))

        # ✅ Quitar bytes de foto para no romper JSON
        for r in rows:
            r.pop("foto", None)

        total_rows = _sp("SP_NOT_CONTAR", (
            busqueda,
            creado_por,
            int(solo_activas),
            int(solo_destacadas),
            desde,
            hasta
        ))

        total = int(total_rows[0].get("total", 0)) if total_rows else 0
        total_paginas = (total + por_pagina - 1) // por_pagina

        return {
            "status": "SUCCESS",
            "data": rows,
            "pagination": {
                "pagina_actual": pagina,
                "por_pagina": por_pagina,
                "total_registros": total,
                "total_paginas": total_paginas,
                "tiene_siguiente": pagina < total_paginas,
                "tiene_anterior": pagina > 1
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar publicaciones: {str(e)}")


# ============================================================
# GET /detalle/{idpublicacion} — Ver publicación completa
# SP: SP_NOT_DETALLE
# ============================================================
@router.get("/detalle/{idpublicacion}", tags=["Admin - Noticias"])
def detalle_publicacion(idpublicacion: str):
    try:
        rows = _sp("SP_NOT_DETALLE", (idpublicacion,))
        if not rows:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        row = rows[0]

        # ✅ Convertir bytes -> base64 para JSON
        row["foto_base64"] = _bytes_to_b64(row.get("foto"))
        row.pop("foto", None)

        return {"status": "SUCCESS", "data": row}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener detalle: {str(e)}")


# ============================================================
# GET /foto/{idpublicacion} — Servir imagen binaria directamente
# ============================================================
@router.get("/foto/{idpublicacion}", tags=["Admin - Noticias"])
def obtener_foto(idpublicacion: str):
    """
    Retorna la foto de la publicación como respuesta binaria (image/jpeg).
    Usado por el frontend con <img src="..."> directamente.
    """
    try:
        rows = _sp("SP_NOT_DETALLE", (idpublicacion,))
        if not rows:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        foto_bytes = rows[0].get("foto")

        if not foto_bytes:
            raise HTTPException(status_code=404, detail="Esta publicación no tiene foto")

        # Detectar tipo de imagen por magic bytes
        content_type = "image/jpeg"  # default
        if isinstance(foto_bytes, (bytes, bytearray)):
            if foto_bytes[:4] == b'\x89PNG':
                content_type = "image/png"
            elif foto_bytes[:4] == b'GIF8':
                content_type = "image/gif"
            elif foto_bytes[:2] == b'BM':
                content_type = "image/bmp"

        return Response(
            content=bytes(foto_bytes),
            media_type=content_type,
            headers={"Cache-Control": "max-age=3600"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener foto: {str(e)}")


# ============================================================
# POST /crear — Crear publicación manual (multipart/form-data)
# SP: SP_NOT_CREAR
# ============================================================
@router.post("/crear", tags=["Admin - Noticias"])
async def crear_publicacion(
    contenido:  str           = Form(...),
    admin_id:   int           = Form(...),
    fecha:      Optional[str] = Form(None),
    destacada:  Optional[str] = Form("false"),   # Form llega como string
    foto:       Optional[UploadFile] = File(None)
):
    try:
        # Normalizar booleano (Form envía "true"/"false"/"on"/"1")
        destacada_bool = str(destacada).lower() in ("true", "1", "on", "yes")

        # Título desde contenido
        titulo = contenido[:200] if len(contenido) > 200 else contenido

        fecha_dt = _parse_fecha(fecha)

        # Leer bytes del archivo si se envió foto
        foto_varbinary = None
        if foto and foto.filename:
            foto_bytes = await foto.read()
            if foto_bytes:
                foto_varbinary = pyodbc.Binary(foto_bytes)

        params = {
            "@titulo":    titulo,
            "@contenido": contenido,
            "@foto":      foto_varbinary,
            "@fecha":     fecha_dt,
            "@destacada": int(destacada_bool),
            "@admin_id":  admin_id
        }

        result = ejecutar_sp_con_foto("SP_NOT_CREAR", params)

        if result and result[0].get("status") == "ERROR":
            raise HTTPException(
                status_code=400,
                detail=result[0].get("mensaje", "Error al crear publicación")
            )

        return {
            "status": "SUCCESS",
            "mensaje": result[0].get("mensaje", "Publicación creada correctamente"),
            "idpublicacion": result[0].get("idpublicacion")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear publicación: {str(e)}")


# ============================================================
# PUT /editar — Editar publicación existente (multipart/form-data)
# SP: SP_NOT_EDITAR
# ============================================================
@router.put("/editar", tags=["Admin - Noticias"])
async def editar_publicacion(
    idpublicacion: str            = Form(...),
    contenido:     str            = Form(...),
    admin_id:      int            = Form(...),
    fecha:         Optional[str]  = Form(None),
    destacada:     Optional[str]  = Form("false"),
    foto:          Optional[UploadFile] = File(None)   # None = mantener imagen actual
):
    try:
        destacada_bool = str(destacada).lower() in ("true", "1", "on", "yes")

        titulo = contenido[:200] if len(contenido) > 200 else contenido
        fecha_dt = _parse_fecha(fecha)

        # Solo leer bytes si se envió un archivo real
        foto_varbinary = None
        if foto and foto.filename:
            foto_bytes = await foto.read()
            if foto_bytes:
                foto_varbinary = pyodbc.Binary(foto_bytes)
        # Si foto_varbinary queda None → el SP hace ISNULL(@foto, foto) = mantiene la imagen

        params = {
            "@idpublicacion": idpublicacion,
            "@titulo":        titulo,
            "@contenido":     contenido,
            "@foto":          foto_varbinary,
            "@fecha":         fecha_dt,
            "@destacada":     int(destacada_bool),
            "@admin_id":      admin_id
        }

        result = ejecutar_sp_con_foto("SP_NOT_EDITAR", params)

        if result and result[0].get("status") == "ERROR":
            raise HTTPException(
                status_code=400,
                detail=result[0].get("mensaje", "Error al editar publicación")
            )

        return {
            "status": "SUCCESS",
            "mensaje": result[0].get("mensaje", "Publicación actualizada correctamente")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al editar publicación: {str(e)}")


# ============================================================
# PUT /toggle-destacada — Marcar/desmarcar como destacada
# SP: SP_NOT_TOGGLE_DESTACADA
# ============================================================
@router.put("/toggle-destacada", tags=["Admin - Noticias"])
def toggle_destacada(body: dict):
    try:
        idpublicacion = body.get("idpublicacion")
        if not idpublicacion:
            raise HTTPException(status_code=400, detail="idpublicacion requerido")

        result = _sp("SP_NOT_TOGGLE_DESTACADA", (idpublicacion,))
        if result and result[0].get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result[0].get("mensaje"))

        return {"status": "SUCCESS", "mensaje": result[0].get("mensaje", "Estado de destacada actualizado")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar destacada: {str(e)}")


# ============================================================
# PUT /toggle-activa — Activar/desactivar publicación
# SP: SP_NOT_TOGGLE_ACTIVA
# ============================================================
@router.put("/toggle-activa", tags=["Admin - Noticias"])
def toggle_activa(body: dict):
    try:
        idpublicacion = body.get("idpublicacion")
        if not idpublicacion:
            raise HTTPException(status_code=400, detail="idpublicacion requerido")

        result = _sp("SP_NOT_TOGGLE_ACTIVA", (idpublicacion,))
        if result and result[0].get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result[0].get("mensaje"))

        return {"status": "SUCCESS", "mensaje": result[0].get("mensaje", "Estado actualizado")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cambiar estado: {str(e)}")


# ============================================================
# DELETE /eliminar — Eliminar definitivo (JSON body)
# SP: SP_NOT_ELIMINAR
# ============================================================
@router.delete("/eliminar", tags=["Admin - Noticias"])
def eliminar_publicacion(body: dict):
    try:
        idpublicacion = body.get("idpublicacion")
        if not idpublicacion:
            raise HTTPException(status_code=400, detail="idpublicacion requerido")

        result = _sp("SP_NOT_ELIMINAR", (idpublicacion,))
        if result and result[0].get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result[0].get("mensaje"))

        return {"status": "SUCCESS", "mensaje": result[0].get("mensaje", "Publicación eliminada definitivamente")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar publicación: {str(e)}")


# ============================================================
# GET /estadisticas — Estadísticas del módulo
# SP: SP_NOT_ESTADISTICAS
# ============================================================
@router.get("/estadisticas", tags=["Admin - Noticias"])
def estadisticas_noticias():
    try:
        result = _sp("SP_NOT_ESTADISTICAS")
        if not result:
            return {
                "status": "SUCCESS",
                "data": {
                    "total_publicaciones": 0,
                    "activas": 0,
                    "archivadas": 0,
                    "destacadas": 0,
                    "desde_facebook": 0,
                    "desde_admin": 0,
                    "este_mes": 0,
                    "ultima_publicacion": None
                }
            }
        return {"status": "SUCCESS", "data": result[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")