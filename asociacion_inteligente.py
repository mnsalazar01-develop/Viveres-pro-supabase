import re
from difflib import SequenceMatcher
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import streamlit as st

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.title("🔄 Vinculación Inteligente de Imágenes (Neon)")
st.write("Este módulo busca coincidencias entre los nombres de tus productos y los enlaces que subiste a ImgBB.")

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
    texto = re.sub(r'\.(jpg|jpeg|png|webp|gif|bmp)', '', texto)
    texto = re.sub(r'[^a-z0-9áéíóúñ\s]', ' ', texto)
    return " ".join(texto.split())

# Contenedor para evitar que se ejecute automáticamente al cargar la página
if st.button("🔍 Analizar y Buscar Coincidencias"):
    try:
        # 2. Leer y extraer URLs de ImgBB desde el archivo local
        with open("enlaces_imgbb.txt", "r", encoding="utf-8") as f:
            texto_imgbb = f.read()

        urls_imgbb = re.findall(r'https://[^\s"\'>]+\.(?:jpg|jpeg|png|webp)', texto_imgbb)

        lista_imgbb = []
        for url in urls_imgbb:
            nombre_archivo = url.split("/")[-1]
            lista_imgbb.append({
                "url": url,
                "nombre_limpio": limpiar_texto(nombre_archivo)
            })

        st.info(f"📦 Se detectaron **{len(lista_imgbb)}** enlaces de imágenes en tu archivo local.")

        # 3. Conectar a Neon y descargar productos actuales
        st.write("🔌 Conectando a la base de datos de Neon...")
        conn = psycopg2.connect(CONN_STRING)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT id_producto, nombre FROM public.productos;")
        productos = cursor.fetchall()

        # 4. Procesar y buscar el mejor Match (Coincidencia Difusa)
        actualizaciones = []
        
        for prod in productos:
            nombre_prod_limpio = limpiar_texto(prod["nombre"])
            mejor_similitud = 0.0
            mejor_url = None
            mejor_nombre_img = ""
            
            for img in lista_imgbb:
                similitud = SequenceMatcher(None, nombre_prod_limpio, img["nombre_limpio"]).ratio()
                
                if similitud > mejor_similitud:
                    mejor_similitud = similitud
                    mejor_url = img["url"]
                    mejor_nombre_img = img["nombre_limpio"]
                    
            # Si el parecido es mayor al 60% lo consideramos válido
            if mejor_similitud >= 0.60:
                actualizaciones.append({
                    "id_producto": prod["id_producto"],
                    "nombre": prod["nombre"],
                    "imagen_detectada": mejor_nombre_img,
                    "url_nueva": mejor_url,
                    "confianza": mejor_similitud
                })

        if not actualizaciones:
            st.warning("⚠️ No se encontraron coincidencias automáticas. Intenta bajando el umbral de confianza en el código.")
            cursor.close()
            conn.close()
        else:
            # Guardamos las sugerencias en el estado de Streamlit para no perderlas al hacer clic en guardar
            df_resumen = pd.DataFrame(actualizaciones)
            df_resumen["confianza_porcentaje"] = df_resumen["confianza"].apply(lambda x: f"{x * 100:.1f}%")
            
            st.write("### --- RESUMEN DE COINCIDENCIAS DETECTADAS ---")
            st.dataframe(df_resumen[["nombre", "imagen_detectada", "confianza_porcentaje"]])
            
            st.session_state["pendientes_actualizar"] = actualizaciones
            
            cursor.close()
            conn.close()

    except Exception as e:
        st.error(f"❌ Ocurrió un error en el análisis: {e}")

# 5. Botón definitivo para aplicar los cambios si existen datos listos
if "pendientes_actualizar" in st.session_state and st.session_state["pendientes_actualizar"]:
    st.write("---")
    st.warning("⚠️ Confirmación: Al presionar el botón de abajo se sobreescribirán las URLs antiguas en tu base de datos de Neon.")
    
    if st.button("💾 Guardar URLs en Base de Datos (Neon)"):
        try:
            conn = psycopg2.connect(CONN_STRING)
            cursor = conn.cursor()
            
            query_update = "UPDATE public.productos SET url_imagen = %s WHERE id_producto = %s;"
            
            for cambio in st.session_state["pendientes_actualizar"]:
                cursor.execute(query_update, (cambio["url_nueva"], cambio["id_producto"]))
                
            conn.commit()
            st.success(f"✅ ¡Éxito! Se actualizaron {len(st.session_state['pendientes_actualizar'])} productos en Neon.")
            
            # Limpiamos el estado
            st.session_state["pendientes_actualizar"] = []
            
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"❌ Error al guardar datos: {e}")


