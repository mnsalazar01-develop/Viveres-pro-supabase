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

# Caja de entrada en la aplicación web
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
https://i.ibb.co/5xJTmnXw/jamon-cocido-pierna-don-diego.jpg
https://i.ibb.co/HLmzgywX/jamon-de-espalda-l-prado-250-gr-450.jpg
https://i.ibb.co/t125Djd/Jamon-de-Pierna-56-Kg.webp
https://i.ibb.co/rR37YYHw/JAMON-DE-PIERNA-ESTANDAR-MILLENIUM-768x768-jpg.webp
https://i.ibb.co/MXDBk2c/Jamon-de-Pierna-Mauro-56-Kg.webp
https://i.ibb.co/wZZ5yvg0/JAMON-DE-PIERNA-PLUMROSE-PLU110-jpg.webp
https://i.ibb.co/CpkTyFNG/jamon-ricci-400g-pierna.jpg
https://i.ibb.co/21xD1Z8D/mallorca-jamon.png
https://i.ibb.co/Hf0M50ws/pechuga-de-pavo-punta-de-monte-250gr-450.jpg
https://i.ibb.co/TjRtZy1/Pechuga-de-Pavo-44-Kg.webp
https://i.ibb.co/mC4KHn0Y/300-Wx300-H-1200-base-Format-1200-base-Format-27001673-4-27001673.jpg
https://i.ibb.co/k6MZdj2F/300-Wx300-H-1200-base-Format-1200-base-Format-27001003-24-27001003.jpg
https://i.ibb.co/bM2wCmFw/0021650-queso-mozzarella-el-paraparo-250-gr-450.jpg
https://i.ibb.co/gZKt5ngM/0021658-queso-mozzarella-el-tablon-250gr-450.jpg
https://i.ibb.co/CK2wbJML/200974.jpg
https://i.ibb.co/JWmzwWVR/images.jpg
https://i.ibb.co/ZzwGm354/images1.jpg
https://i.ibb.co/tMpTX8tf/images2.jpg
https://i.ibb.co/YFygxWF1/IMG-20221106-142351-800x800.jpg
https://i.ibb.co/234whRW6/Img-Thumb.jpg
https://i.ibb.co/pv497vfQ/MICM0028.png
https://i.ibb.co/Lzp8LsLt/mozzarella-generico.jpg
https://i.ibb.co/hRbYXMcq/napolitana-queso-mozzarella-pieza.webp
https://i.ibb.co/hJyCMqLK/Negocios-frigorificoweekend-Productos-Queso-Santa-Barbara-500g-1721831654883.webp
https://i.ibb.co/tPK0zrnL/Queso-Guoda-Montesano.jpg
https://i.ibb.co/YB36qfZz/Queso-Mozzarella-Montesano.jpg
https://i.ibb.co/XT9MS5B/Queso-Palmi-Zulia.jpg
https://i.ibb.co/FkbVDBng/queso-amarillo-calicanto.jpg
https://i.ibb.co/kVbS5dtk/queso-amarillo-cheddys.jpg
https://i.ibb.co/My8czj8G/queso-amarillo-fundido-del-campo.jpg
https://i.ibb.co/jkjgSDtj/queso-amarillo-san-juan.png
https://i.ibb.co/TBFXqf5r/queso-blanco-pasteurizado-san-juan.jpg
https://i.ibb.co/wNMfxd3N/queso-blanco-pasteurizado-san-juan.png
https://i.ibb.co/tT470K9p/queso-bufala-freskito.jpg
https://i.ibb.co/hJxHZzr5/queso-crema.jpg
https://i.ibb.co/rRxyT59Y/Queso-Guayanes.jpg
https://i.ibb.co/7PG1jpr/Queso-Llanero.jpg
https://i.ibb.co/VWhx4stM/Queso-Meride-o.jpg
https://i.ibb.co/SXCpSYXJ/Queso-mozarella-el-paraiso.png
https://i.ibb.co/S45hsjsJ/Queso-mozarella.jpg
https://i.ibb.co/nq5cYgNL/Queso-Mozarella-Santa-Mar-a.png
https://i.ibb.co/KxP2Lnpt/queso-mozzarella-campanario.jpg
https://i.ibb.co/n8f8cL4D/queso-mozzarella-san-juan.jpg
https://i.ibb.co/hRVRtvQ1/Queso-Palmita.jpg
https://i.ibb.co/B5zLynTB/queso-pizza-rica.jpg
https://i.ibb.co/V7cZyZp/queso-requeson.png
https://i.ibb.co/Zp8ZtQFC/Queso-Ricotta.jpg
https://i.ibb.co/Gv29HsZk/queso-Telita.jpg
https://i.ibb.co/ychPhgtP/Sin-t-tulo.png
https://i.ibb.co/6cKt41f2/Zadeno-1-768x768-png.webp"
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
            # EXPRESIÓN REGULAR MEJORADA: Detecta enlaces directos (.jpg) y enlaces de página (ibb.co/código)
            urls_imgbb = re.findall(r'https://(?:i\.)?ibb\.co/[^\s"\'>]+', texto_imgbb)

            lista_imgbb = []
            for url in urls_imgbb:
                # Extraemos el último fragmento para usarlo como nombre de comparación
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
                # CORREGIDO: Ahora usa url_limpia proveniente de los secretos
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
                    st.dataframe(df_resumen[["nombre", "imagen_detected", "confianza_porcentaje"]])
                    
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
            # CORREGIDO: Ahora usa url_limpia proveniente de los secretos
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
