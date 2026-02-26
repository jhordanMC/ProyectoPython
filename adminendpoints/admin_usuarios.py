from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from datetime import date
from Conexionsql import get_connection
import base64

app = FastAPI()

# ══════════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════════
def ejecutar_sp(nombre_sp: str, params: tuple = ()):
    """
    Ejecuta un Stored Procedure con parámetros posicionales.
    FIX: Siempre hace COMMIT (incluso si el SP devuelve SELECT),
    porque varios SP hacen INSERT/UPDATE y devuelven un SELECT con status.
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            placeholders = ",".join(["?"] * len(params))
            sql = f"EXEC {nombre_sp} {placeholders}" if params else f"EXEC {nombre_sp}"

            cursor.execute(sql, params)

            rows = []
            if cursor.description:
                columnas = [col[0] for col in cursor.description]
                rows = [dict(zip(columnas, fila)) for fila in cursor.fetchall()]

            # ✅ COMMIT SIEMPRE (clave)
            conn.commit()

            return rows if rows else [{"status": "SUCCESS"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
# MODELOS
# ══════════════════════════════════════════════════════════════════
class NuevoMiembro(BaseModel):
    nombre: str
    apellido: str
    dni: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None   # ✅ ahora date
    genero: Optional[str] = None
    departamento: Optional[str] = None
    distrito: Optional[str] = None
    direccion: Optional[str] = None
    profesion: Optional[str] = None
    jefatura: Optional[str] = ""
    rango: Optional[str] = "Aspirante"
    estado: Optional[str] = "Activo"
    admin_id: int


class EditarMiembro(BaseModel):
    # ✅ quitamos id_miembro del body (se usa el del path)
    nombre: str
    apellido: str
    dni: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    fecha_nacimiento: Optional[date] = None  # ✅ ahora date
    genero: str
    departamento: Optional[str] = None
    distrito: Optional[str] = None
    direccion: Optional[str] = None
    profesion: Optional[str] = None
    rango: str
    jefatura: str
    estado: str
    admin_id: int


class CambioEstado(BaseModel):
    id_miembro: int
    nuevo_estado: str
    motivo: str
    admin_id: int


class CambioRango(BaseModel):
    id_miembro: int
    nuevo_rango: str
    motivo: Optional[str] = None
    admin_id: int


class EliminarMiembroFisico(BaseModel):
    confirmacion: bool


class ActualizarCursos(BaseModel):
    cursos_certificaciones: Optional[str] = None  # "BLS, ACLS, Primeros Auxilios"
    admin_id: int


# ══════════════════════════════════════════════════════════════════
# POSTULANTES
# ══════════════════════════════════════════════════════════════════
@app.get("/postulantes")
def listar_postulantes(
    busqueda: Optional[str] = None,
    departamento: Optional[str] = None,
    solo_pendientes: bool = False,
    pagina: int = 1,
    por_pagina: int = 10
):
    data = ejecutar_sp("SP_GU_LISTAR_POSTULANTES",
        (busqueda, departamento, int(solo_pendientes), pagina, por_pagina))
    total = ejecutar_sp("SP_GU_CONTAR_POSTULANTES",
        (busqueda, departamento, int(solo_pendientes)))
    return {
        "status": "SUCCESS",
        "total": total[0]["total"] if total else 0,
        "data": data
    }


@app.get("/postulantes/{id_postulante}")
def detalle_postulante(id_postulante: int):
    data = ejecutar_sp("SP_GU_DETALLE_POSTULANTE", (id_postulante,))
    if not data:
        raise HTTPException(status_code=404, detail="Postulante no encontrado")
    return {"status": "SUCCESS", "data": data[0]}


# ══════════════════════════════════════════════════════════════════
# MIEMBROS — rutas estáticas primero
# ══════════════════════════════════════════════════════════════════
@app.get("/miembros")
def listar_miembros(
    busqueda: Optional[str] = None,
    estado: Optional[str] = None,
    rango: Optional[str] = None,
    departamento: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 10
):
    busqueda     = busqueda     or None
    estado       = estado       or None
    rango        = rango        or None
    departamento = departamento or None

    data = ejecutar_sp(
        "SP_GU_LISTAR_MIEMBROS",
        (busqueda, estado, rango, departamento, pagina, por_pagina)
    )
    total = ejecutar_sp(
        "SP_GU_CONTAR_MIEMBROS",
        (busqueda, estado, rango, departamento)
    )
    return {
        "status": "SUCCESS",
        "total": total[0]["total"] if total else 0,
        "data": data
    }


@app.post("/miembros")
def crear_miembro(body: NuevoMiembro):
    resultado = ejecutar_sp("SP_GU_CREAR_MIEMBRO", (
        body.nombre, body.apellido, body.dni,
        body.email, body.telefono, body.fecha_nacimiento, body.genero,
        body.departamento, body.distrito, body.direccion, body.profesion,
        body.rango, body.jefatura, body.estado, body.admin_id,
    ))

    if not resultado:
        raise HTTPException(status_code=500, detail="Sin respuesta del servidor")

    res = resultado[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje", "Error al crear el miembro"))

    return {
        "status": "SUCCESS",
        "mensaje": res.get("mensaje"),
        "id_miembro": res.get("id_miembro"),
        "legajo": res.get("legajo"),
    }


# ── PUT estáticos ────────────────────────────────────────────────
@app.put("/miembros/estado")
def cambiar_estado(body: CambioEstado):
    return ejecutar_sp("SP_GU_CAMBIAR_ESTADO_MIEMBRO",
        (body.id_miembro, body.nuevo_estado, body.motivo, body.admin_id))[0]


@app.put("/miembros/rango")
def cambiar_rango(body: CambioRango):
    return ejecutar_sp("SP_GU_CAMBIAR_RANGO_MIEMBRO",
        (body.id_miembro, body.nuevo_rango, body.motivo, body.admin_id))[0]


@app.get("/miembros/exportar/csv")
def exportar_miembros(
    estado: Optional[str] = None,
    rango: Optional[str] = None,
    departamento: Optional[str] = None
):
    data = ejecutar_sp("SP_GU_EXPORTAR_MIEMBROS", (estado, rango, departamento))
    return {"status": "SUCCESS", "total": len(data), "data": data}


# ══════════════════════════════════════════════════════════════════
# MIEMBROS — rutas dinámicas /{id_miembro} y subrutas
# ══════════════════════════════════════════════════════════════════
@app.get("/miembros/{id_miembro}")
def detalle_miembro(id_miembro: int):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("EXEC SP_GU_DETALLE_MIEMBRO ?", (id_miembro,))

            cols1 = [c[0] for c in cursor.description]
            row1 = cursor.fetchone()
            if not row1:
                raise HTTPException(status_code=404, detail="Miembro no encontrado")
            miembro = dict(zip(cols1, row1))

            # Convertir foto_perfil bytes → base64
            foto_bytes = miembro.pop("foto_perfil", None)
            miembro["foto_base64"] = base64.b64encode(foto_bytes).decode("utf-8") if foto_bytes else None

            cursor.nextset()
            cursos = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            cursor.nextset()
            eventos = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]

            # ✅ commit por consistencia (aunque sea solo lectura, no estorba)
            conn.commit()

        return {"status": "SUCCESS", "miembro": miembro, "cursos": cursos, "eventos": eventos}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/miembros/{id_miembro}")
def editar_miembro(id_miembro: int, body: EditarMiembro):
    resultado = ejecutar_sp("SP_GU_EDITAR_MIEMBRO", (
        id_miembro,
        body.nombre, body.apellido, body.dni,
        body.email, body.telefono, body.fecha_nacimiento, body.genero,
        body.departamento, body.distrito, body.direccion, body.profesion,
        body.rango, body.jefatura, body.estado, body.admin_id,
    ))

    if not resultado:
        raise HTTPException(status_code=500, detail="Sin respuesta del servidor")

    res = resultado[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje", "Error al editar el miembro"))

    return {
        "status": "SUCCESS",
        "mensaje": res.get("mensaje"),
        "id_miembro": res.get("id_miembro"),
    }


@app.get("/miembros/{id_miembro}/historial")
def historial_miembro(id_miembro: int):
    data = ejecutar_sp("SP_GU_HISTORIAL_MIEMBRO", (id_miembro,))
    return {"status": "SUCCESS", "data": data}


@app.delete("/miembros/{id_miembro}/eliminar-fisico")
def eliminar_miembro_fisico(id_miembro: int, body: EliminarMiembroFisico):
    if not body.confirmacion:
        raise HTTPException(status_code=400, detail="Debe confirmar explícitamente la eliminación física")

    resultado = ejecutar_sp("sp_EliminarMiembroFisico", (id_miembro, int(body.confirmacion)))

    if not resultado:
        raise HTTPException(status_code=404, detail="El miembro no existe o no fue eliminado")

    return {"status": "SUCCESS", "data": resultado[0]}


# ── Foto ──────────────────────────────────────────────────────────
@app.get("/miembros/{id_miembro}/foto")
def obtener_foto(id_miembro: int):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT foto_perfil FROM miembros WHERE id = ?", (id_miembro,))
            row = cursor.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        foto_bytes = row[0]
        if foto_bytes is None:
            return {"status": "SUCCESS", "foto_base64": None, "tiene_foto": False}

        return {
            "status": "SUCCESS",
            "foto_base64": base64.b64encode(foto_bytes).decode("utf-8"),
            "tiene_foto": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/miembros/{id_miembro}/foto")
async def actualizar_foto(
    id_miembro: int,
    foto: UploadFile = File(...),
    admin_id: int = 1
):
    TIPOS_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
    TAMANO_MAXIMO = 2 * 1024 * 1024  # 2 MB

    if foto.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes JPG, PNG o WEBP")

    contenido = await foto.read()

    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(status_code=400, detail="La imagen supera el tamaño máximo de 2 MB")

    resultado = ejecutar_sp("SP_GU_ACTUALIZAR_FOTO_MIEMBRO", (id_miembro, contenido, admin_id))

    if not resultado:
        raise HTTPException(status_code=500, detail="Sin respuesta del servidor")

    res = resultado[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))

    return {"status": "SUCCESS", "mensaje": "Foto actualizada correctamente"}


@app.delete("/miembros/{id_miembro}/foto")
def eliminar_foto(id_miembro: int, admin_id: int = 1):
    resultado = ejecutar_sp("SP_GU_ELIMINAR_FOTO_MIEMBRO", (id_miembro, admin_id))

    if not resultado:
        raise HTTPException(status_code=500, detail="Sin respuesta del servidor")

    res = resultado[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))

    return {"status": "SUCCESS", "mensaje": "Foto eliminada correctamente"}


# ── Cursos / Certificaciones ──────────────────────────────────────
@app.get("/miembros/{id_miembro}/cursos")
def obtener_cursos(id_miembro: int):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT cursos_certificaciones FROM miembros WHERE id = ?", (id_miembro,))
            row = cursor.fetchone()
            conn.commit()

        if not row:
            raise HTTPException(status_code=404, detail="Miembro no encontrado")

        return {"status": "SUCCESS", "cursos_certificaciones": row[0] or ""}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/miembros/{id_miembro}/cursos")
def actualizar_cursos(id_miembro: int, body: ActualizarCursos):
    resultado = ejecutar_sp(
        "SP_GU_ACTUALIZAR_CURSOS_MIEMBRO",
        (id_miembro, body.cursos_certificaciones or None, body.admin_id)
    )
    if not resultado:
        raise HTTPException(status_code=500, detail="Sin respuesta del servidor")

    res = resultado[0]
    if res.get("status") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("mensaje"))

    return {"status": "SUCCESS", "mensaje": "Certificaciones actualizadas correctamente"}