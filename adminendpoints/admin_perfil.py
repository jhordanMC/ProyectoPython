# adminendpoints/admin_perfil.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from Conexionsql import get_connection

router = APIRouter()


# =============================================
# MODELOS
# =============================================
class FotoUpdate(BaseModel):
    admin_id: int
    foto_perfil: str | None = None


class EmailValidation(BaseModel):
    email: str
    admin_id: int | None = None


class UsernameValidation(BaseModel):
    username: str
    admin_id: int | None = None


# =============================================
# 1️⃣ OBTENER PERFIL
# GET /api/admin/perfil/{admin_id}
# =============================================
@router.get("/{admin_id}")
def obtener_perfil(admin_id: int):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("EXEC SP_OBTENER_PERFIL_ADMIN ?", admin_id)
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Administrador no encontrado")

        columns = [column[0] for column in cursor.description]
        result = dict(zip(columns, row))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


# =============================================
# 2️⃣ ACTUALIZAR FOTO
# PUT /api/admin/perfil/foto
# =============================================
@router.put("/foto")
def actualizar_foto(data: FotoUpdate):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "EXEC SP_ACTUALIZAR_FOTO_ADMIN ?, ?",
            data.admin_id,
            data.foto_perfil,
        )

        row = cursor.fetchone()
        conn.commit()

        columns = [column[0] for column in cursor.description]
        result = dict(zip(columns, row))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


# =============================================
# 3️⃣ VALIDAR EMAIL
# POST /api/admin/perfil/validar-email
# =============================================
@router.post("/validar-email")
def validar_email(data: EmailValidation):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "EXEC SP_VALIDAR_EMAIL_DISPONIBLE ?, ?",
            data.email,
            data.admin_id,
        )

        row = cursor.fetchone()
        columns = [column[0] for column in cursor.description]
        result = dict(zip(columns, row))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


# =============================================
# 4️⃣ VALIDAR USERNAME
# POST /api/admin/perfil/validar-username
# =============================================
@router.post("/validar-username")
def validar_username(data: UsernameValidation):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "EXEC SP_VALIDAR_USERNAME_DISPONIBLE ?, ?",
            data.username,
            data.admin_id,
        )

        row = cursor.fetchone()
        columns = [column[0] for column in cursor.description]
        result = dict(zip(columns, row))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()
