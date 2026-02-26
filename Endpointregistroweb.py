from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr, field_validator
from datetime import date
import pyodbc
from Conexionsql import get_connection

router = APIRouter()

# ===============================
# MODELO POSTULANTE
# ===============================
class PostulanteWeb(BaseModel):
    nombre: str
    apellido: str
    dni: str
    fecha_nacimiento: date
    genero: str
    email: EmailStr
    telefono: str
    direccion: str
    departamento: str
    distrito: str
    nivel_educativo: str
    profesion: str
    motivacion: str
    experiencia: bool = False
    experiencia_detalle: str | None = None

    @field_validator("genero")
    def genero_valido(cls, v):
        if v.lower() not in ("masculino", "femenino", "otro"):
            raise ValueError("El género debe ser: masculino, femenino u otro")
        return v.lower()

    @field_validator("nivel_educativo")
    def nivel_educativo_valido(cls, v):
        validos = ("sin estudios", "secundaria", "tecnico", "universitario", "postgrado")
        if v.lower() not in validos:
            raise ValueError(f"Nivel educativo inválido, debe ser uno de: {', '.join(validos)}")
        return v.lower()

    @field_validator("experiencia_detalle", mode="before")
    def experiencia_detalle_valida(cls, v, info):
        experiencia = info.data.get("experiencia")
        if experiencia and (v is None or len(v.strip()) < 10):
            raise ValueError("Si tienes experiencia, debes describirla (mínimo 10 caracteres)")
        return v

# ===============================
# ENDPOINT CON SP
# ===============================
@router.post("/registrar", tags=["Registro Web"])
def registrar_postulante(postulante: PostulanteWeb):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Ejecutar SP
        cursor.execute("""
            EXEC SP_REGISTRAR_POSTULANTE_WEB 
                @nombre=?, @apellido=?, @dni=?, @fecha_nacimiento=?, @genero=?,
                @email=?, @telefono=?, @direccion=?, @departamento=?, @distrito=?,
                @nivel_educativo=?, @profesion=?, @motivacion=?, @experiencia=?, @experiencia_detalle=?
        """,
        postulante.nombre.strip(),
        postulante.apellido.strip(),
        postulante.dni.strip(),
        postulante.fecha_nacimiento,
        postulante.genero,
        postulante.email.lower().strip(),
        postulante.telefono.strip(),
        postulante.direccion.strip(),
        postulante.departamento.strip(),
        postulante.distrito.strip(),
        postulante.nivel_educativo,
        postulante.profesion.strip(),
        postulante.motivacion.strip(),
        int(postulante.experiencia),
        postulante.experiencia_detalle.strip() if postulante.experiencia_detalle else None
        )
        
        # Obtener resultado del SP
        row = cursor.fetchone()
        cursor.commit()
        conn.close()

        if row and row[0] == "SUCCESS":
            return {
                "status": row[0],
                "id_postulante": row[1],
                "nombre_completo": row[2],
                "dni": row[3],
                "email": row[4],
                "fecha_registro": row[5],
                "edad": row[6],
                "mensaje": row[7]
            }
        else:
            # Si SP devuelve ERROR, row[2] es el mensaje
            return {
                "status": "ERROR",
                "mensaje": row[2] if row and len(row) > 2 else "No se pudo registrar el postulante"
            }
    
    except pyodbc.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
