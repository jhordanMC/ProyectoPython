# EndpointInstructores.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from Conexionsql import get_connection

app = FastAPI()

# ---------------------------
# FunciÃ³n genÃ©rica para ejecutar SP
# ---------------------------
def ejecutar_sp(sp_nombre: str, params: tuple = ()):
    """Ejecuta un SP con parÃ¡metros y devuelve resultados como lista de diccionarios."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(f"EXEC {sp_nombre} " + ",".join(["?"]*len(params)), params)
            else:
                cursor.execute(f"EXEC {sp_nombre}")
            
            if cursor.description:  # SP devuelve filas
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                resultados = [dict(zip(columns, row)) for row in rows]
                return resultados
            else:  # SP solo devuelve status / mensaje
                return [{"status": "SUCCESS", "mensaje": "SP ejecutado correctamente"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================
# ENDPOINT 1: OBTENER TODOS LOS INSTRUCTORES
# =============================================
@app.get("/instructores")
def obtener_todos_instructores():
    """
    Obtiene todos los instructores activos para mostrar en el grid de cards.
    """
    resultados = ejecutar_sp("SP_ObtenerTodosInstructores")
    return {"status": "SUCCESS", "instructores": resultados}

# =============================================
# ENDPOINT 2: OBTENER INSTRUCTOR POR ID
# =============================================
@app.get("/instructores/{id_instructor}")
def obtener_instructor_por_id(id_instructor: int):
    """
    Obtiene los datos de un instructor especÃ­fico para el modal de biografÃ­a.
    """
    resultados = ejecutar_sp("SP_ObtenerInstructorPorId", (id_instructor,))
    
    if not resultados:
        raise HTTPException(status_code=404, detail="Instructor no encontrado")
    
    return {"status": "SUCCESS", "instructor": resultados[0]}

# =============================================
# ENDPOINT 3: BUSCAR INSTRUCTORES
# =============================================
@app.get("/instructores/buscar/{termino}")
def buscar_instructores(termino: str):
    """
    Busca instructores por nombre, rango o certificaciones.
    Usado por la barra de bÃºsqueda del frontend.
    """
    resultados = ejecutar_sp("SP_BuscarInstructores", (termino,))
    return {"status": "SUCCESS", "instructores": resultados}

# =============================================
# ENDPOINT 4: FILTRAR POR ESPECIALIDAD
# =============================================
@app.get("/instructores/especialidad/{especialidad}")
def filtrar_por_especialidad(especialidad: str):
    """
    Filtra instructores por especialidad.
    Si especialidad = 'todos', devuelve todos los instructores.
    Usado por el sidebar de especialidades.
    """
    # Si piden "todos", pasar NULL al SP
    if especialidad.lower() == "todos":
        especialidad_param = None
    else:
        especialidad_param = especialidad
    
    resultados = ejecutar_sp("SP_FiltrarPorEspecialidad", (especialidad_param,))
    return {"status": "SUCCESS", "instructores": resultados}