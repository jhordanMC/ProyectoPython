# main.py
"""
API Principal del Sistema CGPVP2
Consolida todos los endpoints de la aplicación
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from Cargadatosfacebook import escanear_y_guardar_db
from datetime import datetime

# ── Módulos públicos / existentes ──────────────────────────────────────────────
from Endpointcursos       import app as cursos_app
from Endpointnoticias     import app as noticias_app
from Endpointregistroweb  import router as registro_router
from EnpointInstructores  import app as instructores_app
from Endpoint             import app as miembros_app
from EndpointLoginAdmin   import app as login_admin_app

# ── Módulos del Panel Admin (carpeta adminendpoints) ───────────────────────────
from adminendpoints.admin_dashboard    import router as admin_dashboard_router
from adminendpoints.admin_usuarios     import app as admin_usuarios_app
from adminendpoints.admin_instructores import app as admin_instructores_app
from adminendpoints.admin_cursos       import app as admin_cursos_app
from adminendpoints.admin_eventos      import router as admin_eventos_router  # 🔥 ROUTER, no app
from adminendpoints.admin_noticias     import router  as admin_noticias_router
from adminendpoints.admin_reportes     import app as admin_reportes_app
from adminendpoints.admin_perfil       import router as admin_perfil_router

# =============================================
# CONFIGURACIÓN DE LA APLICACIÓN PRINCIPAL
# =============================================
app = FastAPI(
    title="API CGPVP2 - Sistema Integral",
    description="API REST para gestión de Cursos, Noticias, Instructores, Miembros, Registro Web y Panel Admin",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================
# CORS
# =============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================
# ENDPOINTS RAÍZ / HEALTHCHECK
# =============================================
@app.get("/", tags=["Sistema"])
def home():
    return {
        "status": "online",
        "message": "🔥 API CGPVP2 funcionando correctamente, Rey!",
        "version": "2.0.0",
        "endpoints_publicos": {
            "cursos":        "/api/cursos",
            "noticias":      "/api/noticias",
            "instructores":  "/api/instructores",
            "miembros":      "/api/miembros",
            "registro_web":  "/api/registro",
        },
        "endpoints_admin": {
            "login":         "/api/admin",
            "dashboard":     "/api/admin/dashboard",
            "usuarios":      "/api/admin/usuarios",
            "instructores":  "/api/admin/instructores",
            "cursos":        "/api/admin/cursos",
            "eventos":       "/api/admin/eventos",
            "noticias":      "/api/admin/noticias",
            "reportes":      "/api/admin/reportes",
        },
        "documentacion": {
            "swagger": "/docs",
            "redoc":   "/redoc",
        },
    }


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "healthy", "database": "connected"}


# =============================================
# MÓDULOS PÚBLICOS / EXISTENTES
# =============================================
app.mount("/api/cursos",       cursos_app)
app.mount("/api/noticias",     noticias_app)
app.mount("/api/instructores", instructores_app)
app.mount("/api/miembros",     miembros_app)
app.include_router(registro_router, prefix="/api/registro", tags=["Registro Web"])


# =============================================
# PANEL ADMIN — ¡ORDEN CRÍTICO!
# Las rutas MÁS ESPECÍFICAS deben ir PRIMERO
# =============================================

# 🔥 IMPORTANTE: include_router con prefix ANTES de mount
# Estas rutas usan APIRouter y necesitan prefix explícito

app.include_router(admin_dashboard_router, prefix="/api/admin/dashboard", tags=["Admin - Dashboard"])
app.include_router(admin_perfil_router, prefix="/api/admin/perfil", tags=["Admin - Perfil"])
app.include_router(admin_eventos_router, prefix="/api/admin/eventos")  # 🔥 EVENTOS CON PREFIX
app.include_router(admin_noticias_router, prefix="/api/admin/noticias", tags=["Admin - Noticias"])
# Ahora las sub-aplicaciones con mount
app.mount("/api/admin/usuarios",     admin_usuarios_app)
app.mount("/api/admin/instructores", admin_instructores_app)
app.mount("/api/admin/cursos",       admin_cursos_app)
app.mount("/api/admin/reportes",     admin_reportes_app)

# 🔥 CRÍTICO: Esta DEBE ser la ÚLTIMA ruta /api/admin
# Porque captura CUALQUIER cosa que empiece con /api/admin
app.mount("/api/admin", login_admin_app)


# =============================================
# MANEJADORES DE ERROR GLOBALES
# =============================================
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "status": "ERROR",
            "mensaje": "Endpoint no encontrado. Revisa la documentación en /docs",
        },
    )
@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "ERROR",
            "mensaje": "Error interno del servidor. Contacta al administrador.",
        },
    )

# =============================================
# PROGRAMADOR DE TAREAS (MODO SEGURO)
# =============================================
async def reloj_programador_fb():
    """Reloj que chequea la hora cada minuto"""
    print("⏰ Reloj de Facebook activado en segundo plano...")
    while True:
        ahora = datetime.now()
        # Si es la 1:00 AM
        if ahora.hour == 00 and ahora.minute == 26:
            print(f"🔥 {ahora} - ¡Es la hora, Rey! Iniciando bot...")
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, escanear_y_guardar_db)
                print("✅ Tarea completada con éxito.")
            except Exception as e:
                print(f"❌ Error en la tarea programada: {e}")
            
            await asyncio.sleep(61)
        
        await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(reloj_programador_fb())
    print("🚀 Programador iniciado: El bot correrá a la 01:00 AM diariamente.")

# =============================================
# ARRANQUE DEL SERVIDOR
# =============================================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║          🔥 API CGPVP2  v2.0  INICIADA 🔥               ║
    ║                                                          ║
    ║  📍 Servidor:       http://localhost:8000               ║
    ║  📚 Documentación:  http://localhost:8000/docs          ║
    ║  🔧 ReDoc:          http://localhost:8000/redoc         ║
    ║                                                          ║
    ║  Endpoints públicos:                                     ║
    ║  • /api/cursos           /api/noticias                  ║
    ║  • /api/instructores     /api/miembros                  ║
    ║  • /api/registro                                        ║
    ║                                                          ║
    ║  Panel Admin  →  /api/admin/...                         ║
    ║  • dashboard  • usuarios  • instructores                ║
    ║  • cursos     • eventos   • noticias  • reportes        ║
    ║                                                          ║
    ║  ¡Todo listo, Rey! 🚀                                   ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )