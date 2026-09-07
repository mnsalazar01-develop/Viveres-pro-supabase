import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

st.title("📦 Importador de Datos a Neon")
st.write("Sube un archivo CSV desde tu computadora para crear o reemplazar tu tabla en la base de datos relacional.")

# 1. Componente visual para arrastrar y soltar el archivo CSV
archivo_subido = st.file_uploader("Elige tu archivo CSV", type=["csv"])

# 2. Configura el nombre que tendrá la tabla en tu base de datos de Neon
NOMBRE_TABLA = "pre_ofertas" 

# El proceso solo inicia cuando el usuario sube un archivo
if archivo_subido is not None:
    # Botón para confirmar la migración y evitar que se ejecute sola al cargar la página
    if st.button("🚀 Iniciar migración a Neon"):
        try:
            with st.spinner("Procesando... Por favor espera."):
                st.write("⏳ Leyendo el archivo CSV...")
                # Streamlit lee el archivo directamente desde la memoria
                df = pd.read_csv(archivo_subido)
                
                st.write("🔐 Obteniendo la cadena de conexión desde los Secrets...")
                cadena_conexion = st.secrets["neon"]["url"]
                
                st.write("🔄 Conectando con Neon (con límite de tiempo de 5s)...")
                engine = create_engine(
                    cadena_conexion, 
                    connect_args={"connect_timeout": 5}
                )
                
                st.write(f"📤 Creando la tabla '{NOMBRE_TABLA}' y subiendo las filas...")
                # Sube los datos. Si la tabla ya existe, la reemplaza por completo
                df.to_sql(NOMBRE_TABLA, con=engine, if_exists="replace", index=False)
                
                st.success(f"¡Todo listo! Tu tabla '{NOMBRE_TABLA}' se ha creado en Neon con éxito. 🎉")
                st.balloons() # Animación de celebración

        except KeyError:
            st.error("❌ Error: No se encontró la clave ['neon']['url'] en los Secrets de tu aplicación.")
        except Exception as e:
            st.error(f"❌ Ocurrió un error durante la migración: {e}")
else:
    st.info("💡 Por favor, sube un archivo CSV arriba para habilitar el botón de migración.")
