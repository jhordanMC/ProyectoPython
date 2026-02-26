import os
import pyodbc
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

DB_SERVER = os.getenv("DB_SERVER", "127.0.0.1")
DB_NAME   = os.getenv("DB_NAME", "DB_CGPVP2")
DB_USER   = os.getenv("DB_USER")        # ejemplo: sa o tu usuario
DB_PASS   = os.getenv("DB_PASS")        # tu password
DB_PORT   = os.getenv("DB_PORT", "1433")

def _crear_conexion():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={DB_SERVER},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASS};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )

_pool = QueuePool(
    _crear_conexion,
    pool_size=10,
    max_overflow=20,
    timeout=30,
    recycle=1800,
)

class _ConexionPool:
    def __init__(self):
        self._fairy = _pool.connect()

    def __getattr__(self, name):
        return getattr(self._fairy, name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._fairy.close()
        return False

    def close(self):
        self._fairy.close()

def get_connection():
    return _ConexionPool()