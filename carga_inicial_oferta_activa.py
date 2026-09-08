# =====================================================================
# PROGRAMA: carga_inicial_activos.py
# MODULO: MIGRACIÓN RELACIONAL GENERAL - PIZARRA GLOBAL DE ACTIVOS
# ENTORNO: PYTHON 3.14 PRODUCTION PRO
# =====================================================================
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

st.set_page_config(
    page_title="Migrador Core - Ofertas Activas",
    layout="wide",
    page_icon="⚙️"
)

st.title("⚙️ Extractor & Carga Inicial de Ofertas Activas")
st.caption("Módulo de infraestructura general para auditar y poblar la pizarra global de últimos precios conocidos.")

# 1. VALIDACIÓN DE SECRETOS NEON
try:
    url_limpia = st.secrets["neon"]["url"]
except KeyError:
    st.error("❌ Error de configuración: Falta la variable ['neon']['url'] en los secrets.")
    st.stop()

st.markdown("##### 📊 Auditoría Global de Datos Históricos Disponibles")

# 2. CÁLCULO DE MÉTRICAS EN ENFOQUE GENERAL (SIN FILTRO DE SUPERMERCADO)
total_skus_unicos = 0
total_cadenas = 0
lote_neto_proyectado = 0

try:
    conn_stats = psycopg2.connect(url_limpia)
    cur_s = conn_stats.cursor(cursor_factory=RealDictCursor)
    
    # Descarga directa del pool mínimo necesario para las métricas globales
    cur_s.execute("SELECT TRIM(id_producto) as id_producto, id_super FROM public.ofertas;")
    res_ofertas = cur_s.fetchall()
    conn_stats.close()
    
    if res_ofertas:
        df_pool = pd.DataFrame(res_ofertas)
        
        # 1. Conteo de SKUs únicos totales en la historia
        total_skus_unicos = df_pool["id_producto"].nunique()
        
        # 2. Conteo de cadenas comerciales involucradas
        total_cadenas = df_pool["id_super"].nunique()
        
        # 3. Lote neto proyectado (combinaciones únicas de producto + súper)
        lote_neto_proyectado = len(df_pool.drop_duplicates(subset=["id_producto", "id_super"]))
        
except Exception as e_stats:
    st.error(f"❌ Error al calcular estadísticas globales: {e_stats}")

# Panel ejecutivo adaptado al enfoque general
m1, m2, m3 = st.columns(3)
m1.metric("SKUs Únicos Totales (Historial)", total_skus_unicos)
m2.metric("Cadenas Comerciales Activas", total_cadenas)
m3.metric("Lote Neto de Inserción Proyectado", lote_neto_proyectado)

st.write("---")

# 3. ALGORITMO ATÓMICO DE POBLADO GLOBAL
if st.button("🎬 Inicialización Completa de Catálogo Histórico General", use_container_width=True, type="primary"):
    if lote_neto_proyectado == 0:
        st.error("Alerta: No se registran ofertas históricas previas para poblar la nueva pizarra.")
    else:
        conn = None
        try:
            conn = psycopg2.connect(url_limpia)
            cur = conn.cursor()
            
            with st.spinner("Ejecutando consolidación atómica en el servidor de Neon..."):
                # La consulta analiza todo el historial ciegamente, extrae la última oferta
                # de cada producto en cada súper (posicion = 1) y hace el UPSERT
                query_migracion = """
                    INSERT INTO public.ofertas_activas (id_producto, id_super, precio_oferta_proyectado)
                    SELECT 
                        id_producto::VARCHAR as id_producto, -- Lo convertimos a texto al entrar a la nueva tabla
                        id_super, 
                        precio_oferta as precio_oferta_proyectado
                    FROM (
                        SELECT id_producto, id_super, precio_oferta, id_oferta,
                               ROW_NUMBER() OVER (
                                   PARTITION BY id_producto, id_super 
                                   ORDER BY id_oferta DESC
                               ) as posicion
                        FROM public.ofertas
                    ) subconsulta
                    WHERE subconsulta.posicion = 1
                    ON CONFLICT (id_producto, id_super) 
                    DO UPDATE SET 
                        precio_oferta_proyectado = EXCLUDED.precio_oferta_proyectado,
                        updated_at = CURRENT_TIMESTAMP;
                """

                cur.execute(query_migracion)
                filas_afectadas = cur.rowcount
                conn.commit()
                
            st.balloons()
            st.success(f"¡Pizarra Global de Activos poblada con éxito! Se procesaron {filas_afectadas} registros únicos en Neon.")
            st.rerun()
            
        except Exception as ex_v:
            if conn: conn.rollback()
            st.error(f"❌ Falla transaccional al inicializar lote general: {ex_v}")
        finally:
            if conn: conn.close()
