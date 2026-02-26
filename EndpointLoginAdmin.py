from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from Conexionsql import get_connection

from dotenv import load_dotenv
import os
import smtplib
import random
from datetime import date, datetime, timedelta, timezone
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

app = FastAPI()

def ejecutar_sp(sp_nombre: str, params: tuple = ()):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"EXEC {sp_nombre} " + ",".join(["?"] * len(params)),
                params
            )

            rows = []
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # ✅ CLAVE: commit siempre
            conn.commit()

            return rows if rows else [{"status": "SUCCESS"}]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def enviar_codigo_email(destinatario: str, codigo: str):
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")

    if not SMTP_USER or not SMTP_PASS:
        raise HTTPException(
            status_code=500,
            detail="Faltan SMTP_USER o SMTP_PASS en el archivo .env"
        )

    asunto = "Código de verificación"
    cuerpo = f"""Hola,

Tu código de verificación es: {codigo}

Este código expira en 5 minutos.
Si no fuiste tú, ignora este mensaje.
"""

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, destinatario, msg.as_string())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando correo: {str(e)}")

class LoginAdmin(BaseModel):
    email: str
    password: str

@app.post("/login")
def login_admin(data: LoginAdmin):
    res = ejecutar_sp("SP_VALIDAR_LOGIN_ADMIN", (data.email, data.password))[0]

    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    admin_id = res.get("admin_id") or res.get("id")

    codigo = str(random.randint(100000, 999999))
    expira_en = datetime.now(timezone.utc) + timedelta(minutes=5)

    # 🔍 AGREGA ESTO:
    print(f"🔑 OTP generado: {codigo}")
    print(f"⏰ Expira en (UTC): {expira_en}")
    print(f"⏰ SYSUTCDATETIME en Python sería: {datetime.now(timezone.utc)}")

    ejecutar_sp("SP_GUARDAR_OTP_ADMIN", (admin_id, codigo, expira_en))
    enviar_codigo_email(data.email, codigo)

    return {
        "status": "2FA_REQUIRED",
        "admin_id": admin_id,
        "message": "Se envió un código a tu correo"
    }


class VerificarOTP(BaseModel):
    admin_id: int
    codigo: str  # "123456"

@app.post("/login/verify-otp")
def verificar_otp(data: VerificarOTP):
    res = ejecutar_sp("SP_VALIDAR_OTP_ADMIN", (data.admin_id, data.codigo))[0]

    if res.get("status") != "SUCCESS":
        raise HTTPException(status_code=401, detail="Código inválido o expirado")

    # ✅ OTP válido → traer datos completos del admin para el frontend
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id         AS admin_id,
                       username,
                       nombre_completo,
                       email,
                       rol,
                       foto_perfil,
                       activo,
                       ultimo_login
                FROM admin_users
                WHERE id = ?
            """, (data.admin_id,))

            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Admin no encontrado")

            admin = dict(zip(columns, row))

            # Serializar foto_perfil (VARBINARY → data URI) si está en BD como bytes
            if isinstance(admin.get("foto_perfil"), (bytes, bytearray)):
                val = admin["foto_perfil"]
                if val[:4] == b'\x89PNG':
                    mime = 'image/png'
                elif val[:2] == b'\xff\xd8':
                    mime = 'image/jpeg'
                else:
                    mime = 'image/jpeg'
                b64 = base64.b64encode(val).decode('utf-8')
                admin["foto_perfil"] = f"data:{mime};base64,{b64}"

            # Serializar fechas
            for k, v in admin.items():
                if isinstance(v, (date, datetime)):
                    admin[k] = v.isoformat()

            return {
                "status": "LOGIN_SUCCESS",
                "admin": admin
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================================
# 3️⃣ CREAR ADMIN
# ================================
class CrearAdmin(BaseModel):
    username: str
    password: str
    nombre_completo: str
    email: str
    rol: str = "Editor"
    foto_perfil: str | None = None
    creado_por: int | None = None

@app.post("/crear")
def crear_admin(admin: CrearAdmin):
    return ejecutar_sp("SP_CREAR_ADMIN", (
        admin.username,
        admin.password,
        admin.nombre_completo,
        admin.email,
        admin.rol,
        admin.foto_perfil,
        admin.creado_por
    ))[0]

class ActualizarPerfilAdmin(BaseModel):
    admin_id: int
    nombre_completo: str | None = None
    email: str | None = None
    foto_perfil: str | None = None
    password_actual: str | None = None
    password_nuevo: str | None = None

@app.put("/perfil")
def actualizar_perfil(data: ActualizarPerfilAdmin):
    return ejecutar_sp("SP_ACTUALIZAR_PERFIL_ADMIN", (
        data.admin_id,
        data.nombre_completo,
        data.email,
        data.foto_perfil,
        data.password_actual,
        data.password_nuevo
    ))[0]

# ================================
# 5️⃣ CAMBIAR PASSWORD (SUPER ADMIN)
# ================================
class CambiarPasswordAdmin(BaseModel):
    admin_id: int
    password_nuevo: str
    modificado_por: int

@app.put("/cambiar_password")
def cambiar_password(data: CambiarPasswordAdmin):
    return ejecutar_sp("SP_CAMBIAR_PASSWORD_ADMIN", (
        data.admin_id,
        data.password_nuevo,
        data.modificado_por
    ))[0]

# ================================
# 6️⃣ LISTAR ADMINS
# ================================
@app.get("/listar")
def listar_admins(solo_activos: bool = True):
    resultado = ejecutar_sp("SP_LISTAR_ADMINS", (solo_activos,))
    return {"status": "SUCCESS", "resultados": resultado}

# ================================
# 7️⃣ ACTIVAR / DESACTIVAR ADMIN
# ================================
class CambiarEstadoAdmin(BaseModel):
    admin_id: int
    activar: bool
    modificado_por: int

@app.put("/estado")
def cambiar_estado_admin(data: CambiarEstadoAdmin):
    return ejecutar_sp("SP_CAMBIAR_ESTADO_ADMIN", (
        data.admin_id,
        data.activar,
        data.modificado_por
    ))[0]

# ================================
# 8️⃣ VERIFICAR SESIÓN
# ================================
class VerificarSesion(BaseModel):
    admin_id: int

@app.post("/verificar_sesion")
def verificar_sesion(data: VerificarSesion):
    return ejecutar_sp("SP_VERIFICAR_SESION_ADMIN", (data.admin_id,))[0]