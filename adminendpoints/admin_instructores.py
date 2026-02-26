# adminendpoints/admin_instructores.py
"""
Endpoints del Panel Admin — INSTRUCTORES
CRUD completo + asignación a cursos/eventos

SP usados (según tu SP real):
- SP_INS_LISTAR
- SP_INS_DETALLE
- SP_REGISTRAR_INSTRUCTOR
- SP_ACTUALIZAR_INSTRUCTOR
- SP_INS_ELIMINAR
- SP_ASIGNAR_INSTRUCTOR_A_CURSO
- SP_ASIGNAR_INSTRUCTOR_A_EVENTO
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from Conexionsql import get_connection

app = FastAPI()


# ============================================================
# HELPER: SP posicional simple (FIX: COMMIT SIEMPRE)
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
                rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

            # ✅ clave
            conn.commit()

            return rows if rows else [{"status": "SUCCESS"}]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# HELPER: SP con parámetros nombrados (FIX: COMMIT SIEMPRE)
# ============================================================
def ejecutar_sp_parametros_nombrados(sp_nombre: str, params: dict):
    """
    Ejecuta SP usando parámetros nombrados:
    params ejemplo:
      {
        "@nombre_completo": "Juan Perez",
        "@foto": "data:image/png;base64,...."  # o solo base64
      }
    """
    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Mantener orden estable
            param_names = list(params.keys())
            param_placeholders = ", ".join([f"{name}=?" for name in param_names])
            sql = f"EXEC {sp_nombre} {param_placeholders}"

            valores = [params[name] for name in param_names]
            cursor.execute(sql, valores)

            rows = []
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

            # ✅ clave
            conn.commit()

            return rows if rows else [{"status": "SUCCESS", "mensaje": "SP ejecutado correctamente"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# GET /  — listar instructores con filtros
# =============================================
@app.get("/", tags=["Admin - Instructores"])
def listar_instructores(
    busqueda: Optional[str] = None,
    especialidad: Optional[str] = None,
    estado: Optional[str] = None,
):
    rows = _sp("SP_INS_LISTAR", (busqueda, especialidad, estado))
    return {"status": "SUCCESS", "total": len(rows), "data": rows}


# =============================================
# GET /{id}  — ficha + cursos y eventos asignados
# =============================================
@app.get("/{id_instructor}", tags=["Admin - Instructores"])
def detalle_instructor(id_instructor: int):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("EXEC SP_INS_DETALLE ?", (id_instructor,))

            # Result set 1
            if not cursor.description:
                raise HTTPException(status_code=404, detail="Instructor no encontrado")
            cols = [c[0] for c in cursor.description]
            rows1 = cursor.fetchall()
            if not rows1:
                raise HTTPException(status_code=404, detail="Instructor no encontrado")
            instructor = dict(zip(cols, rows1[0]))

            # Result set 2
            cursor.nextset()
            cursos = []
            if cursor.description:
                cols2 = [c[0] for c in cursor.description]
                cursos = [dict(zip(cols2, r)) for r in cursor.fetchall()]

            # Result set 3
            cursor.nextset()
            eventos = []
            if cursor.description:
                cols3 = [c[0] for c in cursor.description]
                eventos = [dict(zip(cols3, r)) for r in cursor.fetchall()]

            conn.commit()

        return {"status": "SUCCESS", "data": instructor, "cursos": cursos, "eventos": eventos}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# POST /  — REGISTRAR NUEVO INSTRUCTOR
# =============================================
class InstructorCrear(BaseModel):
    nombre_completo: str
    especialidad: str
    rango: Optional[str] = None
    experiencia_anios: int = 0
    certificaciones: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    foto: Optional[str] = None  # base64 (NVARCHAR(MAX))
    bio: Optional[str] = None
    admin_id: int


@app.post("/", tags=["Admin - Instructores"])
def registrar_instructor(instructor: InstructorCrear):
    params = {
        "@nombre_completo": instructor.nombre_completo,
        "@especialidad": instructor.especialidad,
        "@rango": instructor.rango,
        "@experiencia_anios": instructor.experiencia_anios,
        "@certificaciones": instructor.certificaciones,
        "@email": instructor.email,
        "@telefono": instructor.telefono,
        "@foto": instructor.foto,
        "@bio": instructor.bio,
        "@admin_id": instructor.admin_id
    }
    resultados = ejecutar_sp_parametros_nombrados("SP_REGISTRAR_INSTRUCTOR", params)
    return resultados[0] if resultados else {"status": "SUCCESS"}


# =============================================
# PUT /  — ACTUALIZAR INSTRUCTOR
# =============================================
class InstructorActualizar(BaseModel):
    id_instructor: int
    nombre_completo: str
    especialidad: str
    rango: Optional[str] = None
    experiencia_anios: int = 0
    certificaciones: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    foto: Optional[str] = None  # base64 (NVARCHAR(MAX))
    bio: Optional[str] = None
    estado: str = "Activo"
    admin_id: int


@app.put("/", tags=["Admin - Instructores"])
def actualizar_instructor(instr: InstructorActualizar):
    params = {
        "@id_instructor": instr.id_instructor,
        "@nombre_completo": instr.nombre_completo,
        "@especialidad": instr.especialidad,
        "@rango": instr.rango,
        "@experiencia_anios": instr.experiencia_anios,
        "@certificaciones": instr.certificaciones,
        "@email": instr.email,
        "@telefono": instr.telefono,
        "@foto": instr.foto,
        "@bio": instr.bio,
        "@estado": instr.estado,
        "@admin_id": instr.admin_id
    }
    resultados = ejecutar_sp_parametros_nombrados("SP_ACTUALIZAR_INSTRUCTOR", params)
    return resultados[0] if resultados else {"status": "SUCCESS"}


# =============================================
# DELETE /  — baja / eliminar
# =============================================
class EliminarInstructor(BaseModel):
    id_instructor: int
    admin_id: int


@app.delete("/", tags=["Admin - Instructores"])
def eliminar_instructor(body: EliminarInstructor):
    rows = _sp("SP_INS_ELIMINAR", (body.id_instructor, body.admin_id))
    return rows[0] if rows else {"status": "SUCCESS"}


# =============================================
# POST /asignar-curso
# =============================================
class AsignarCurso(BaseModel):
    id_curso: int
    id_instructor: int
    admin_id: int


@app.post("/asignar-curso", tags=["Admin - Instructores"])
def asignar_a_curso(body: AsignarCurso):
    rows = _sp("SP_ASIGNAR_INSTRUCTOR_A_CURSO", (body.id_curso, body.id_instructor, body.admin_id))
    return rows[0] if rows else {"status": "SUCCESS"}


# =============================================
# POST /asignar-evento
# =============================================
class AsignarEvento(BaseModel):
    id_evento: int
    id_instructor: int
    admin_id: int


@app.post("/asignar-evento", tags=["Admin - Instructores"])
def asignar_a_evento(body: AsignarEvento):
    rows = _sp("SP_ASIGNAR_INSTRUCTOR_A_EVENTO", (body.id_evento, body.id_instructor, body.admin_id))
    return rows[0] if rows else {"status": "SUCCESS"}