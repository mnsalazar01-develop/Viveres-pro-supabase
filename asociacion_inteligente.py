import re
from difflib import SequenceMatcher
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import streamlit as st

# Cargar secretos de forma segura desde Streamlit Cloud
try:
    url_limpia = st.secrets["neon"]["url"]
    IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
    IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]
except KeyError as e:
    st.error(f"❌ Error: Falta configurar la variable {e} en los Secrets de Streamlit.")
    st.stop()

st.title("🔄 Vinculación Inteligente de Imágenes (Neon)")
st.write("Pega aquí los códigos o enlaces de ImgBB para asociarlos con tu catálogo de Neon.")

# Caja de entrada en la aplicación web con tus enlaces reales cargados por defecto
texto_imgbb = st.text_area(
    "Pega aquí tus códigos de inserción de ImgBB:", 
    height=250, 
    placeholder="https://i.ibb.co/jv9wQf2F/carne-molida.jpg
https://i.ibb.co/CKRGpQrT/Bistec-de-Res.jpg
https://i.ibb.co/WNsMZwzc/0021165-jamon-cocido-superior-purolomo-250gr-450.jpg
https://i.ibb.co/S7DF6xPK/05-2.jpg
https://i.ibb.co/0Rw0yzTX/0021179-jamon-de-pierna-l-prado-250-gr-450.jpg
https://i.ibb.co/BXxSYkm/0021946-jamon-de-pierna-charvenca-250-gr-450.jpg
https://i.ibb.co/ZpgC7FwG/images4.jpg
https://i.ibb.co/qFR5Chjx/jamon-arichuna-pierna-coc-300g.jpg
https://i.ibb.co/VWjSMp9K/jamon-lapiroca-pierna.jpg
https://i.ibb.co/cS7Q4rM4/jamon-cocido-estandar-alibal-250gr-450.jpg
"
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
            # EXPRESIÓN REGULAR: Detecta enlaces directos (.jpg) y formatos con o sin subdominio 'i.'
            urls_imgbb = re.findall(r'https://(?:i\.)?ibb\.co/[^\s"\'>]+', texto_imgbb)

            lista_imgbb = []
            for url in urls_imgbb:
                nombre_archivo = url.split("/")[-1]
                lista_imgbb.append({
                    "url": url,
                    "nombre_limpio": limpiar_texto(nombre_archivo)
                })

            st.info(f"📦 Se detectaron **{len(lista_imgbb)}** enlaces de ImgBB en el cuadro de texto.")

            if len(lista_imgbb) == 0:
                st.error("❌ No se encontraron enlaces válidos de ImgBB. Revisa el texto copiado.")
            else:
                st.write("🔌 Conectando a la base de datos de Neon...")
                conn = psycopg2.connect(url_limpia)
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
                            
                    # Si el parecido es igual o mayor al 60%
                    if mejor_similitud >= 0.60:
                        actualizaciones.append({
                            "id_producto": prod["id_producto"],
                            "nombre": prod["nombre"],
                            "imagen_detectada": mejor_nombre_img,
                            "url_nueva": mejor_url,
                            "confianza": mejor_similitud
                        })

                if not actualizaciones:
                    st.warning("⚠️ No se encontraron coincidencias con un umbral del 60%.")
                else:
                    df_resumen = pd.DataFrame(actualizaciones)
                    df_resumen["confianza_porcentaje"] = df_resumen["confianza"].apply(lambda x: f"{x * 100:.1f}%")
                    
                    st.write("### --- RESUMEN DE COINCIDENCIAS DETECTADAS ---")
                    # CORREGIDO: "imagen_detected" cambiado a "imagen_detectada" para que coincida con el diccionario
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
            conn = psycopg2.connect(url_limpia)
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
