


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


# Cambiamos el archivo de texto por una caja de entrada en la misma aplicación web
texto_imgbb = st.text_area(
    "https://ibb.co/SXDmMy8p
https://ibb.co/VYf40TKP
https://ibb.co/205CxQMj
https://ibb.co/HpL5K2Vr
https://ibb.co/Q35WvxLc
https://ibb.co/KMk38nY
https://ibb.co/fzN7LyKq
https://ibb.co/Xkz8D6LV
https://ibb.co/ynfygBP3
https://ibb.co/Pvfgq63q
https://ibb.co/wr2yVwZj
https://ibb.co/6c6PsS9N
https://ibb.co/vMd8kyt
https://ibb.co/bMFWTTXK
https://ibb.co/B1Vn2zy
https://ibb.co/HLL57J4F
https://ibb.co/Y4zqSGYs
https://ibb.co/JwVfw3xf
https://ibb.co/C3qXRqCZ
https://ibb.co/ndfjTpB
https://ibb.co/svq4FTCD
https://ibb.co/cXxqm0hd
https://ibb.co/Jwy6Gtq6
https://ibb.co/whmp9v6N
https://ibb.co/Xx8W7y3H
https://ibb.co/j9bLP9mv
https://ibb.co/tpNQXSgj
https://ibb.co/DDfHp5yX
https://ibb.co/21sJT61C
https://ibb.co/tprSKnQh
https://ibb.co/XZFvQZ7D
https://ibb.co/Y7j3zVzk
https://ibb.co/mCkNvB0x
https://ibb.co/Vct3NKJv
https://ibb.co/Hp4cC8Rh
https://ibb.co/KxXY3VwM
https://ibb.co/GjXNcMw
https://ibb.co/XfZ8CzVS
https://ibb.co/Xf0CjwqN
https://ibb.co/9mwbxfwV
https://ibb.co/GQrcqRmr
https://ibb.co/gMB1F2C6
https://ibb.co/vxZSKcgx
https://ibb.co/rRmCB0V2
https://ibb.co/TxDRb3JX
https://ibb.co/Jwvk0rZV
https://ibb.co/Z5hMGgc
https://ibb.co/qM4CQvdm
https://ibb.co/PZH8kXZt
https://ibb.co/ks5RH7HM
https://ibb.co/Y4qk1RFL
https://ibb.co/RTF3B8kX
https://ibb.co/Z1K18Mvh
https://ibb.co/QFMF1GSj
https://ibb.co/v6w13XLk
https://ibb.co/KMpkZkz
https://ibb.co/G42hBZ8j
https://ibb.co/27tSZ8zP
https://ibb.co/v6sqsLpq
https://ibb.co/JWYpzyMN", 
    height=200, 
    placeholder="https://ibb.co\nhttps://ibb.co..."
)

# Función para limpiar texto y facilitar la comparación
def limpiar_texto(texto):
    if not texto:
        return ""
    texto = str(texto).lower()
    texto = re.sub(r'\.(jpg|jpeg|png|webp|gif|bmp)', '', texto)
    texto = re.sub(r'[^a-z0-9áéíóúñ\s]', ' ', texto)
    return " ".join(texto.split())

# 1. ANALIZAR Y BUSCAR COINCIDENCIAS
if st.button("🔍 Analizar y Buscar Coincidencias"):
    if not texto_imgbb.strip():
        st.warning("⚠️ Por favor, pega los enlaces de ImgBB antes de continuar.")
    else:
        try:
            # Extraer URLs válidas del texto pegado
            urls_imgbb = re.findall(r'https://[^\s"\'>]+\.(?:jpg|jpeg|png|webp)', texto_imgbb)

            lista_imgbb = []
            for url in urls_imgbb:
                nombre_archivo = url.split("/")[-1]
                lista_imgbb.append({
                    "url": url,
                    "nombre_limpio": limpiar_texto(nombre_archivo)
                })

            st.info(f"📦 Se detectaron **{len(lista_imgbb)}** enlaces válidos de imágenes en el cuadro de texto.")

            if len(lista_imgbb) == 0:
                st.error("❌ No se encontraron URLs que terminen en formatos de imagen (.jpg, .png, etc.). Revisa los códigos copiados.")
            else:
                st.write("🔌 Conectando a la base de datos de Neon...")
                conn = psycopg2.connect(CONN_STRING)
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("SELECT id_producto, nombre FROM public.productos;")
                productos = cursor.fetchall()

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
                            
                    # Si el parecido es mayor al 60%
                    if mejor_similitud >= 0.60:
                        actualizaciones.append({
                            "id_producto": prod["id_producto"],
                            "nombre": prod["nombre"],
                            "imagen_detectada": mejor_nombre_img,
                            "url_nueva": mejor_url,
                            "confianza": mejor_similitud
                        })

                if not actualizaciones:
                    st.warning("⚠️ No se encontraron coincidencias. Prueba subiendo fotos cuyos nombres se parezcan más a los productos.")
                else:
                    df_resumen = pd.DataFrame(actualizaciones)
                    df_resumen["confianza_porcentaje"] = df_resumen["confianza"].apply(lambda x: f"{x * 100:.1f}%")
                    
                    st.write("### --- RESUMEN DE COINCIDENCIAS DETECTADAS ---")
                    st.dataframe(df_resumen[["nombre", "imagen_detectada", "confianza_porcentaje"]])
                    
                    st.session_state["pendientes_actualizar"] = actualizaciones
                
                cursor.close()
                conn.close()

        except Exception as e:
            st.error(f"❌ Ocurrió un error en el análisis: {e}")

# 2. APLICAR CAMBIOS EN LA BASE DE DATOS
if "pendientes_actualizar" in st.session_state and st.session_state["pendientes_actualizar"]:
    st.write("---")
    st.warning("⚠️ Confirmación: Al presionar el botón de abajo se guardarán definitivamente las nuevas URLs en Neon.")
    
    if st.button("💾 Guardar URLs en Base de Datos (Neon)"):
        try:
            conn = psycopg2.connect(CONN_STRING)
            cursor = conn.cursor()
            
            query_update = "UPDATE public.productos SET url_imagen = %s WHERE id_producto = %s;"
            
            for cambio in st.session_state["pendientes_actualizar"]:
                cursor.execute(query_update, (cambio["url_nueva"], cambio["id_producto"]))
                
            conn.commit()
            st.success(f"✅ ¡Éxito! Se vincularon {len(st.session_state['pendientes_actualizar'])} imágenes en tu base de datos de Neon.")
            
            st.session_state["pendientes_actualizar"] = []
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"❌ Error al guardar datos: {e}")
