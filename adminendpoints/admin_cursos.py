# adminendpoints/admin_cursos.py
"""
Endpoints del Panel Admin – CURSOS
CRUD de cursos + gestión de inscripciones

✅ CORREGIDO: 
- Encoding UTF-8
- Nombres de campos consistentes con el frontend
- Manejo de valores NULL
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

            results = []
            if cursor.description:
                cols = [c[0] for c in cursor.description]
                results = [dict(zip(cols, row)) for row in cursor.fetchall()]

            # ✅ CLAVE: commit siempre
            conn.commit()

            return results if results else [{"status": "SUCCESS"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
# CRUD DE CURSOS
# =============================================

# POST /listar – listar cursos con filtros
class FiltroCursos(BaseModel):
    busqueda: Optional[str] = None
    categoria: Optional[str] = None
    modalidad: Optional[str] = None
    estado: Optional[str] = None

@app.post("/listar", tags=["Admin - Cursos"])
def listar_cursos(filtro: FiltroCursos):
    """
    Lista cursos con filtros opcionales.
    
    🔥 IMPORTANTE: Tu SP_LISTAR_CURSOS debe devolver estos campos:
    - id_curso (o id)
    - titulo
    - categoria
    - duracion
    - modalidad
    - instructor (o nombre_instructor)
    - cupos
    - cupos_disponibles
    - estado
    - fecha_inicio
    - fecha_fin
    """
    resultados = _sp("SP_LISTAR_CURSOS", (
        filtro.categoria,
        filtro.modalidad,
        filtro.estado,
        filtro.busqueda
    ))
    return {"status": "SUCCESS", "resultados": resultados}


# POST /detalle – obtener curso por id
class CursoID(BaseModel):
    id_curso: int

@app.post("/detalle", tags=["Admin - Cursos"])
def obtener_curso_por_id(curso: CursoID):
    """
    Obtiene un curso específico por su ID.
    
    🔥 IMPORTANTE: Tu SP_OBTENER_CURSO debe devolver TODOS los campos:
    - id_curso, titulo, categoria, duracion, modalidad
    - id_instructor, instructor (nombre completo)
    - descripcion, requisitos, cupos, cupos_disponibles
    - direccion, enlace, imagen
    - estado, fecha_inicio, fecha_fin
    """
    resultados = _sp("SP_OBTENER_CURSO", (curso.id_curso,))
    return {"status": "SUCCESS", "resultados": resultados}


# POST / – crear curso
class CursoCrear(BaseModel):
    titulo: str
    categoria: str
    duracion: Optional[str] = None
    modalidad: str = "Presencial"
    id_instructor: Optional[int] = None
    descripcion: Optional[str] = None
    requisitos: Optional[str] = None
    cupos: int = 30
    direccion: Optional[str] = None
    enlace: Optional[str] = None
    imagen: Optional[str] = None
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    admin_id: int

@app.post("/", tags=["Admin - Cursos"])
def crear_curso(curso: CursoCrear):
    """
    Crea un nuevo curso.
    
    🔥 Tu SP_REGISTRAR_CURSO debe:
    1. Insertar el curso en la tabla
    2. Devolver {"status": "SUCCESS", "mensaje": "Curso creado", "id_curso": X}
    """
    resultados = _sp("SP_REGISTRAR_CURSO", (
        curso.titulo,
        curso.categoria,
        curso.duracion,
        curso.modalidad,
        curso.id_instructor,
        curso.descripcion,
        curso.requisitos,
        curso.cupos,
        curso.direccion,
        curso.enlace,
        curso.imagen,
        curso.fecha_inicio,
        curso.fecha_fin,
        curso.admin_id
    ))
    return resultados[0]


# PUT / – actualizar curso
class CursoActualizar(BaseModel):
    id_curso: int
    titulo: str
    categoria: str
    duracion: Optional[str] = None
    modalidad: str
    id_instructor: Optional[int] = None
    descripcion: Optional[str] = None
    requisitos: Optional[str] = None
    cupos: int
    direccion: Optional[str] = None
    enlace: Optional[str] = None
    imagen: Optional[str] = None
    estado: str
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    admin_id: int

@app.put("/", tags=["Admin - Cursos"])
def actualizar_curso(curso: CursoActualizar):
    """
    Actualiza un curso existente.
    
    🔥 Tu SP_ACTUALIZAR_CURSO debe:
    1. Actualizar todos los campos del curso
    2. Devolver {"status": "SUCCESS", "mensaje": "Curso actualizado"}
    """
    resultados = _sp("SP_ACTUALIZAR_CURSO", (
        curso.id_curso,
        curso.titulo,
        curso.categoria,
        curso.duracion,
        curso.modalidad,
        curso.id_instructor,
        curso.descripcion,
        curso.requisitos,
        curso.cupos,
        curso.direccion,
        curso.enlace,
        curso.imagen,
        curso.estado,
        curso.fecha_inicio,
        curso.fecha_fin,
        curso.admin_id
    ))
    return resultados[0]


# DELETE / – eliminar curso
class EliminarCurso(BaseModel):
    id_curso: int
    admin_id: int

@app.delete("/", tags=["Admin - Cursos"])
def eliminar_curso(curso: EliminarCurso):
    """
    Elimina un curso (soft delete o hard delete según tu lógica).
    
    🔥 Tu SP_ELIMINAR_CURSO debe:
    1. Marcar el curso como eliminado o borrarlo
    2. Devolver {"status": "SUCCESS", "mensaje": "Curso eliminado"}
    """
    resultados = _sp("SP_ELIMINAR_CURSO", (
        curso.id_curso,
        curso.admin_id
    ))
    return resultados[0]


# PUT /estado – cambiar estado de curso
class CambioEstadoCurso(BaseModel):
    id_curso: int
    nuevo_estado: str
    admin_id: int

@app.put("/estado", tags=["Admin - Cursos"])
def cambiar_estado_curso(data: CambioEstadoCurso):
    """
    Cambia el estado de un curso (Activo, Programado, Finalizado, Cancelado).
    
    🔥 Tu SP_CAMBIAR_ESTADO_CURSO debe:
    1. Actualizar solo el campo estado
    2. Devolver {"status": "SUCCESS", "mensaje": "Estado actualizado"}
    """
    resultados = _sp("SP_CAMBIAR_ESTADO_CURSO", (
        data.id_curso,
        data.nuevo_estado,
        data.admin_id
    ))
    return resultados[0]