from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date, datetime
import base64
import hashlib
from Conexionsql import get_connection

app = FastAPI()


def serializar_fila(columns, row) -> dict:
    """
    Convierte una fila de pyodbc a dict JSON-serializable.
    - bytes/bytearray (VARBINARY) → data URI Base64
    - date / datetime             → string ISO
    - El resto                    → sin cambios
    """
    resultado = {}
    for col, val in zip(columns, row):
        if isinstance(val, (bytes, bytearray)):
            if val[:4] == b'\x89PNG':
                mime = 'image/png'
            elif val[:2] == b'\xff\xd8':
                mime = 'image/jpeg'
            elif val[:4] == b'GIF8':
                mime = 'image/gif'
            elif val[:4] == b'RIFF':
                mime = 'image/webp'
            else:
                mime = 'image/jpeg'
            b64 = base64.b64encode(val).decode('utf-8')
            resultado[col] = f"data:{mime};base64,{b64}"
        elif isinstance(val, (date, datetime)):
            resultado[col] = val.isoformat()
        else:
            resultado[col] = val
    return resultado


def generar_hash_id(id: int) -> str:
    """
    Replica exactamente lo que hace SQL Server:
    LOWER(CONVERT(VARCHAR(32), HASHBYTES('MD5', CONVERT(NVARCHAR(50), id)), 2))
    
    SQL Server HASHBYTES con NVARCHAR usa UTF-16 LE.
    CONVERT(..., 2) produce hex en mayúsculas → LOWER lo pasa a minúsculas.
    """
    id_str = str(id)
    id_utf16 = id_str.encode('utf-16-le')   # NVARCHAR en SQL Server = UTF-16 LE
    hash_bytes = hashlib.md5(id_utf16).digest()
    return hash_bytes.hex()                  # hex en minúsculas = equivale a LOWER(CONVERT(...,2))


class CriterioBusqueda(BaseModel):
    criterio: str


@app.post("/buscar")
def buscar_miembro(data: CriterioBusqueda):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                EXEC SP_BUSCAR_MIEMBRO @criterio_busqueda=?
            """, (data.criterio,))

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            if not rows:
                return {"status": "No se encontraron miembros", "resultados": []}

            resultados = [serializar_fila(columns, row) for row in rows]
            
            # ✅ Agregar el hash de cada miembro para que el JS pueda armar la URL
            for r in resultados:
                if r.get('id'):
                    r['hash'] = generar_hash_id(r['id'])
            
            return {"status": "SUCCESS", "resultados": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BusquedaPorHash(BaseModel):
    hash: str


@app.post("/buscar-por-hash")
def buscar_miembro_por_hash(data: BusquedaPorHash):
    try:
        print(f"🔍 Buscando por hash: {data.hash}")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                EXEC SP_BUSCAR_MIEMBRO_POR_HASH @hash=?
            """, (data.hash,))

            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()

            if not row:
                print(f"❌ No se encontró miembro con hash: {data.hash}")
                raise HTTPException(status_code=404, detail="Miembro no encontrado")

            miembro = serializar_fila(columns, row)
            
            # Agregar el hash al resultado también
            if miembro.get('id'):
                miembro['hash'] = generar_hash_id(miembro['id'])
            
            print(f"✅ Miembro encontrado: {miembro.get('nombre_completo') or miembro.get('nombre')}")
            return {"status": "SUCCESS", "miembro": miembro}

    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Error en buscar-por-hash: {e}")
        raise HTTPException(status_code=500, detail=str(e))