import re
import streamlit as st
import requests
import base64
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="Asociador Pro", page_icon="📸", layout="centered")
st.title("📸 Administrador de Imágenes de Productos (Neon + ImgBB)")
st.write("Selecciona un producto y elige el método para asignarle su imagen.")

# Cargar secretos de forma segura desde Streamlit Cloud
try:
    url_limpia = st.secrets["neon"]["url"]
    IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
    IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]
except KeyError as e:
    st.error(f"❌ Error: Falta configurar la variable {e} en los Secrets de Streamlit.")
    st.stop()

# Función para limpiar texto y facilitar la comparación
def limpiar_texto(texto):
    if not texto:
        return ""
    texto = str(texto).lower()
    # Quitamos extensiones comunes y caracteres extraños
    texto = re.sub(r'\.(jpg|jpeg|png|webp|gif|bmp)', '', texto)
    texto = re.sub(r'[^a-z0-9áéíóúñ\s]', ' ', texto)
    return " ".join(texto.split())

# 2. Leer y extraer URLs de ImgBB
with open("enlaces_imgbb.txt", "r", encoding="utf-8") as f:
    texto_imgbb = f.read()

urls_imgbb = re.findall(r'https://[^\s"\'>]+\.(?:jpg|jpeg|png|webp)', texto_imgbb)

# Creamos una lista de diccionarios con la URL y su nombre limpio
lista_imgbb = []
for url in urls_imgbb:
    nombre_archivo = url.split("/")[-1]
    lista_imgbb.append({
        "url": url,
        "nombre_limpio": limpiar_texto(nombre_archivo)
    })

print(f" Se cargaron {len(lista_imgbb)} imágenes desde ImgBB.")

# 3. Descargar productos de Supabase
print(" Descargando catálogo de Supabase...")
respuesta = supabase.table("productos").select("id_producto", "nombre").execute()
productos = respuesta.data

# 4. Procesar y buscar el mejor Match
actualizaciones = []
print("\n Buscando coincidencias inteligentes (Fuzzy Match)...")

for prod in productos:
    nombre_prod_limpio = limpiar_texto(prod["nombre"])
    mejor_similitud = 0.0
    mejor_url = None
    mejor_nombre_img = ""
    
    # Comparamos el nombre del producto contra todas las fotos de ImgBB
    for img in lista_imgbb:
        # SequenceMatcher mide el porcentaje de parecido entre dos textos (0.0 a 1.0)
        similitud = SequenceMatcher(None, nombre_prod_limpio, img["nombre_limpio"]).ratio()
        
        if similitud > mejor_similitud:
            mejor_similitud = similitud
            mejor_url = img["url"]
            mejor_nombre_img = img["nombre_limpio"]
            
    # Si la similitud es mayor al 60%, lo tomamos como válido
    # Puedes subir o bajar este número (0.60 = 60%) según veas los resultados
    if mejor_similitud >= 0.60:
        actualizaciones.append({
            "id_producto": prod["id_producto"],
            "nombre": prod["nombre"],
            "imagen_detectada": mejor_nombre_img,
            "url_nueva": mejor_url,
            "confianza": f"{mejor_similitud * 100:.1f}%"
        })

# Convertimos a DataFrame para mostrarte un resumen antes de aplicar cambios
df_resumen = pd.DataFrame(actualizaciones)
print("\n--- RESUMEN DE COINCIDENCIAS ENCONTRADAS ---")
print(df_resumen[["nombre", "imagen_detectada", "confianza"]].head(20))
print(f"\n Se encontraron {len(df_resumen)} coincidencias viables.")

# 5. Aplicar cambios en la Base de Datos
confirmacion = input("\n¿Deseas aplicar estos cambios en Supabase? (si/no): ")

if confirmacion.lower() == 'si':
    print(" Actualizando Supabase... Por favor espera.")
    for cambio in actualizaciones:
        supabase.table("productos")\
            .update({"url_imagen": cambio["url_nueva"]})\
            .eq("id_producto", cambio["id_producto"])\
            .execute()
    print(" ¡Base de datos actualizada con éxito!")
else:
    print(" Operación cancelada. No se modificó nada.")
