import streamlit as st  # 👈 ¡ESTA LÍNEA ES LA QUE FALTA!
import requests
import base64
import psycopg2
from psycopg2.extras import RealDictCursor

# Cargar secretos de Neon
url = st.secrets["neon"]["DATABASE_URL"]

# Cargar secretos de ImgBB
IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]

# Ya puedes usar las variables en tus funciones de conexión y subida...

def subir_imagen_a_album(ruta_imagen_local, nombre_producto):
    """Sube la imagen a ImgBB dentro del álbum especificado y devuelve la URL."""
    url_api = "https://imgbb.com"  # URL oficial de la API v1
    
    try:
        with open(ruta_imagen_local, "rb") as file:
            imagen_base64 = base64.b64encode(file.read())
        
        datos = {
            "key": IMGBB_API_KEY,
            "image": imagen_base64,
            "album_id": IMGBB_ALBUM_ID,
            "name": f"prod_{nombre_producto.replace(' ', '_').lower()}"
        }
        
        respuesta = requests.post(url_api, data=datos)
        resultado = respuesta.json()
        
        if resultado.get("status") == 200:
            return resultado["data"]["url"]  # Enlace directo (.jpg / .png)
        else:
            print(f"❌ Error ImgBB: {resultado.get('error', {}).get('message')}")
            return None
            
    except FileNotFoundError:
        print(f"❌ Archivo local no encontrado: {ruta_imagen_local}")
        return None
    except Exception as e:
        print(f"❌ Error en la subida: {e}")
        return None


def asociar_imagen_a_producto_existente(id_producto, ruta_imagen_local):
    """
    Busca el producto por ID, sube su foto al álbum privado 
    y actualiza el campo url_imagen en la base de datos.
    """
    conn = None
    try:
        # Conectarse a tu base de datos Neon
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Verificar si el producto existe y obtener su nombre
        cur.execute("SELECT nombre FROM public.productos WHERE id_producto = %s;", (id_producto,))
        producto = cur.fetchone()
        
        if not producto:
            print(f"❌ El producto con ID {id_producto} no existe en la base de datos.")
            return False
        
        nombre_prod = producto['nombre']
        print(f"📦 Producto encontrado: '{nombre_prod}' (ID: {id_producto})")
        
        # 2. Subir la imagen al álbum de ImgBB
        url_publica_imagen = subir_imagen_a_album(ruta_imagen_local, nombre_prod)
        
        if not url_publica_imagen:
            print("❌ No se pudo procesar la imagen. Cancelando operación.")
            return False
        
        # 3. Actualizar la columna 'url_imagen' en la tabla 'productos'
        query_update = """
            UPDATE public.productos 
            SET url_imagen = %s 
            WHERE id_producto = %s;
        """
        cur.execute(query_update, (url_publica_imagen, id_producto))
        conn.commit()  # Guardar cambios permanentemente
        
        print(f"✅ ¡Éxito! Imagen asociada correctamente.")
        print(f"🔗 Enlace guardado en la BD: {url_publica_imagen}\n")
        return True

    except Exception as error:
        print(f"❌ Error de Base de Datos: {error}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            cur.close()
            conn.close()

# --- PRUEBA DEL PROGRAMA ---
# Reemplaza con un ID real de tu tabla y una ruta de foto válida en tu PC
id_a_procesar = 10123049102  # Ejemplo de ID bigint
foto_local = "imagenes_productos/leche_entera.jpg"

asociar_imagen_a_producto_existente(id_producto=id_a_procesar, ruta_imagen_local=foto_local)
