import time
import requests
import hashlib
import pyodbc
from datetime import datetime
from Conexionsql import get_connection
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# =============================================
# HELPER: Descargar imagen como bytes
# =============================================
def descargar_foto_bytes(url: str) -> bytes | None:
    """
    Descarga la imagen desde la URL de Facebook y retorna los bytes.
    Retorna None si falla o si la URL no es válida.
    """
    if not url or url == "Sin imagen" or not url.startswith("http"):
        print("ℹ️ No hay imagen válida para descargar.")
        return None

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        foto_bytes = response.content
        print(f"✅ Imagen descargada: {len(foto_bytes)} bytes")
        return foto_bytes

    except Exception as e:
        print(f"⚠️ No se pudo descargar la imagen: {e}")
        return None


# =============================================
# FUNCIÓN PRINCIPAL
# =============================================
def escanear_y_guardar_db():
    print(f"🚀 [{datetime.now()}] Iniciando extracción reforzada...")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")

    driver = None
    conn = None

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("https://www.facebook.com/paramedicos.pe")
        print("⏳ Esperando carga inicial (10s)...")
        time.sleep(10)

        # --- EXPANDIR 'VER MÁS' ---
        try:
            print("🔍 Expandiendo contenido...")
            boton = driver.find_element(By.XPATH, "//div[contains(text(), 'Ver más')]")
            driver.execute_script("arguments[0].click();", boton)
            time.sleep(3)
        except:
            print("ℹ️ Post corto o ya expandido.")

        # --- CAPTURA DE DATOS ---
        posts = driver.find_elements(By.XPATH, "//div[@role='article']")
        
        if posts:
            post = posts[0]
            try:
                # Extraer texto
                texto_raw = post.find_element(By.XPATH, ".//div[@data-ad-comet-preview='message']").text
                contenido = texto_raw.strip()

                # Extraer URL de foto
                foto_url = None
                try:
                    img_elem = post.find_element(By.XPATH, ".//img[contains(@src, 'scontent')]")
                    foto_url = img_elem.get_attribute('src')
                    print(f"🖼️ URL de imagen encontrada: {foto_url[:80]}...")
                except:
                    print("ℹ️ No se encontró imagen en el post.")

                # ✅ Descargar imagen como bytes (antes se guardaba la URL como texto)
                foto_bytes = descargar_foto_bytes(foto_url)
                foto_varbinary = pyodbc.Binary(foto_bytes) if foto_bytes else None

                # Metadatos
                id_pub = hashlib.md5(contenido.encode('utf-8')).hexdigest()
                titulo_auto = contenido[:80] + ('...' if len(contenido) > 80 else '')
                fecha_recolecta = datetime.now()

                # --- GUARDAR EN BASE DE DATOS ---
                print(f"📡 Conectando a SQL Server...")
                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    EXEC SP_INSERTAR_ACTUALIZAR_PUBLICACION 
                        @idpublicacion = ?, 
                        @titulo = ?, 
                        @contenido = ?, 
                        @foto = ?, 
                        @fecha = ?,
                        @creado_por = 'Facebook'
                """, (id_pub, titulo_auto, contenido, foto_varbinary, fecha_recolecta))
                
                conn.commit()
                print(f"✅ Éxito: Post '{id_pub[:8]}' guardado con {'foto' if foto_varbinary else 'sin foto'}.")

            except Exception as e:
                print(f"⚠️ Error al extraer datos del post: {e}")
        else:
            print("❌ No se encontraron publicaciones.")

    except Exception as e:
        print(f"❌ Error crítico: {e}")
    
    finally:
        if conn:
            conn.close()
        if driver:
            driver.quit()
        print("🏁 Navegador y conexiones cerradas correctamente.")


if __name__ == "__main__":
    escanear_y_guardar_db()