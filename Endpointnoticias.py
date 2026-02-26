# Endpointnoticias.py - VERSIÓN CORREGIDA
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from typing import Optional
import pyodbc
from Conexionsql import get_connection

# -------------------------------
# INSTANCIA DE FASTAPI
# -------------------------------
app = FastAPI(title="API de Noticias - CGPVP2", version="1.0")

# -------------------------------
# FUNCIONES AUXILIARES PARA SP
# -------------------------------
def execute_sp(sp_name: str, params: dict = {}, fetch_one: bool = False, fetch_all: bool = True):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        param_list = ", ".join([f"@{k} = ?" for k in params.keys()])
        sql = f"EXEC {sp_name} {param_list}" if param_list else f"EXEC {sp_name}"
        cursor.execute(sql, tuple(params.values()))

        if fetch_one:
            row = cursor.fetchone()
            if row and cursor.description:
                return dict(zip([column[0] for column in cursor.description], row))
            return None
        elif fetch_all:
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
                # ✅ Quitar campo "foto" (bytes) para no romper JSON
                for r in rows:
                    r.pop("foto", None)
                return rows
            return []
        else:
            return None
    except Exception as e:
        print(f"❌ Error en execute_sp({sp_name}): {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


def execute_sp_raw(sp_name: str, params: dict = {}):
    """
    Igual que execute_sp pero devuelve las filas SIN quitar el campo foto (bytes).
    Usado exclusivamente por el endpoint /foto/{id}.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        param_list = ", ".join([f"@{k} = ?" for k in params.keys()])
        sql = f"EXEC {sp_name} {param_list}" if param_list else f"EXEC {sp_name}"
        cursor.execute(sql, tuple(params.values()))

        if cursor.description:
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []
    except Exception as e:
        print(f"❌ Error en execute_sp_raw({sp_name}): {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


# ================================
# ENDPOINTS
# ================================

# ✅ FOTO - debe ir ANTES de /{idpublicacion} para no ser capturado por ese route
@app.get("/foto/{idpublicacion}")
def obtener_foto(idpublicacion: str):
    """
    Retorna la foto de la publicación como imagen binaria.
    El frontend la consume directamente con <img src="...foto/ID">.
    """
    try:
        rows = execute_sp_raw("SP_OBTENER_PUBLICACION_POR_ID", {"idpublicacion": idpublicacion})

        if not rows:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")

        foto_bytes = rows[0].get("foto")

        if not foto_bytes:
            raise HTTPException(status_code=404, detail="Esta publicación no tiene foto")

        # Detectar tipo de imagen por magic bytes
        content_type = "image/jpeg"  # default
        if isinstance(foto_bytes, (bytes, bytearray)):
            b = bytes(foto_bytes)
            if b[:4] == b'\x89PNG':
                content_type = "image/png"
            elif b[:4] == b'GIF8':
                content_type = "image/gif"
            elif b[:2] == b'BM':
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


# SP1: LISTAR PUBLICACIONES CON FILTROS
@app.get("/")
def listar_publicaciones(
    pagina: int = Query(1, ge=1),
    cantidad_por_pagina: int = Query(9, ge=1, le=100),
    solo_destacadas: int = Query(0, ge=0, le=1),
    solo_activas: int = Query(1, ge=0, le=1),
    busqueda: Optional[str] = Query(None),
    ordenar_por: str = Query("reciente")
):
    try:
        params = {
            "Pagina": pagina,
            "CantidadPorPagina": cantidad_por_pagina,
            "SoloDestacadas": solo_destacadas,
            "SoloActivas": solo_activas,
            "busqueda": busqueda if busqueda else "",
            "ordenar_por": ordenar_por
        }

        publicaciones = execute_sp("SP_LISTAR_PUBLICACIONES_CON_FILTROS", params)

        # Obtener total desde el segundo resultset del SP
        total = len(publicaciones)
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "EXEC SP_LISTAR_PUBLICACIONES_CON_FILTROS @Pagina=?, @CantidadPorPagina=?, @SoloDestacadas=?, @SoloActivas=?, @busqueda=?, @ordenar_por=?",
                pagina, cantidad_por_pagina, solo_destacadas, solo_activas,
                busqueda if busqueda else "", ordenar_por
            )
            cursor.nextset()
            total_row = cursor.fetchone()
            if total_row:
                total = total_row[0]
            cursor.close()
            conn.close()
        except:
            pass  # Fallback: usar len()

        return {"total": total, "publicaciones": publicaciones}

    except Exception as e:
        print(f"❌ Error en listar_publicaciones: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# SP2: PUBLICACIÓN DESTACADA
@app.get("/destacada")
def obtener_publicacion_destacada():
    try:
        resultado = execute_sp("SP_OBTENER_PUBLICACION_DESTACADA")
        return resultado if resultado else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# SP4: PUBLICACIONES RECIENTES
@app.get("/recientes")
def obtener_publicaciones_recientes(cantidad: int = Query(5, ge=1, le=50)):
    try:
        resultado = execute_sp("SP_OBTENER_PUBLICACIONES_RECIENTES", {"cantidad": cantidad})
        return resultado if resultado else []
    except Exception as e:
        return []  # No romper el frontend si falla


# SP8: BUSCAR PUBLICACIONES
@app.get("/buscar")
def buscar_publicaciones(termino_busqueda: str = Query(..., min_length=1)):
    try:
        resultado = execute_sp("SP_BUSCAR_PUBLICACIONES", {"termino_busqueda": termino_busqueda})
        return resultado if resultado else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# HEALTH CHECK - también debe ir antes de /{idpublicacion}
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "noticias", "version": "1.0"}


# Endpoints de rutas estáticas adicionales (antes del wildcard)
@app.get("/estadisticas")
def estadisticas_publicaciones():
    try:
        resultado = execute_sp("SP_ESTADISTICAS_PUBLICACIONES")
        return resultado if resultado else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rango")
def publicaciones_por_rango(fecha_inicio: str, fecha_fin: str):
    try:
        return execute_sp("SP_OBTENER_PUBLICACIONES_POR_FECHAS", {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/origen")
def contar_publicaciones_por_origen():
    try:
        return execute_sp("SP_CONTAR_PUBLICACIONES_POR_ORIGEN")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/por_mes")
def publicaciones_por_mes(anio: Optional[int] = None):
    try:
        return execute_sp("SP_PUBLICACIONES_POR_MES", {"anio": anio})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/facebook/sincronizar")
def sincronizar_publicacion_facebook(
    idpublicacion: str,
    titulo: str,
    contenido: str,
    foto: str,
    fecha: str
):
    try:
        params = {
            "idpublicacion": idpublicacion,
            "titulo": titulo,
            "contenido": contenido,
            "foto": foto,
            "fecha": fecha
        }
        return execute_sp("SP_SINCRONIZAR_PUBLICACION_FACEBOOK", params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/crear")
def crear_publicacion_manual(
    titulo: str,
    contenido: str,
    foto: Optional[str] = None,
    fecha: Optional[str] = None,
    destacada: int = 0
):
    try:
        params = {
            "titulo": titulo,
            "contenido": contenido,
            "foto": foto,
            "fecha": fecha,
            "destacada": destacada
        }
        return execute_sp("SP_CREAR_PUBLICACION_MANUAL", params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ⚠️ WILDCARD - debe ir SIEMPRE AL FINAL para no capturar rutas estáticas
@app.get("/{idpublicacion}")
def obtener_publicacion_por_id(idpublicacion: str):
    try:
        pub = execute_sp("SP_OBTENER_PUBLICACION_POR_ID", {"idpublicacion": idpublicacion}, fetch_one=True)
        if not pub:
            raise HTTPException(status_code=404, detail="Publicación no encontrada")
        return pub
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/{idpublicacion}/destacada")
def marcar_publicacion_destacada(idpublicacion: str, destacada: int = Query(..., ge=0, le=1)):
    try:
        return execute_sp("SP_MARCAR_PUBLICACION_DESTACADA", {
            "idpublicacion": idpublicacion,
            "destacada": destacada
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/{idpublicacion}/activar")
def activar_desactivar_publicacion(idpublicacion: str, activa: int = Query(..., ge=0, le=1)):
    try:
        return execute_sp("SP_ACTIVAR_DESACTIVAR_PUBLICACION", {
            "idpublicacion": idpublicacion,
            "activa": activa
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/{idpublicacion}")
def eliminar_publicacion(idpublicacion: str):
    try:
        return execute_sp("SP_ELIMINAR_PUBLICACION", {"idpublicacion": idpublicacion})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/{idpublicacion}")
def actualizar_publicacion_manual(
    idpublicacion: str,
    titulo: str,
    contenido: str,
    foto: Optional[str] = None,
    fecha: Optional[str] = None,
    destacada: int = 0
):
    try:
        params = {
            "idpublicacion": idpublicacion,
            "titulo": titulo,
            "contenido": contenido,
            "foto": foto,
            "fecha": fecha,
            "destacada": destacada
        }
        return execute_sp("SP_ACTUALIZAR_PUBLICACION_MANUAL", params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))