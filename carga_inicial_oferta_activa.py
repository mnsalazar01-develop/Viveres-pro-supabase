# =====================================================================
# PROGRAMA: carga_inicial_activos.py
# MODULO: MIGRACIÓN RELACIONAL CON PANEL DE ESTADÍSTICAS PREVIAS
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
st.caption("Módulo de infraestructura corporativa para auditar y poblar la pizarra de últimos precios conocidos.")

# 1. VALIDACIÓN DE SECRETOS NEON
try:
    url_limpia = st.secrets["neon"]["url"]
except KeyError:
    st.error("❌ Error de configuración: Falta la variable ['neon']['url'] en los secrets.")
    st.stop()

# 2. SELECTOR DE CONTEXTO PARA AUDITORÍA
# Para calcular la Fase 1 y Fase 2, necesitamos saber cuál es el Súper Líder/Objetivo actual
try:
    conn_maestros = psycopg2.connect(url_limpia)
    cur_m = conn_maestros.cursor(cursor_factory=RealDictCursor)
    cur_m.execute("SELECT id_super, nombre_supermercado FROM public.supermercados ORDER BY nombre_supermercado;")
    res_supers = cur_m.fetchall()
    conn_maestros.close()
except Exception as e:
    st.error(f"Error al cargar maestros: {e}")
    st.stop()

dict_supers = {int(s["id_super"]): s["nombre_supermercado"] for s in res_supers}
id_super_contexto = st.selectbox("Seleccione el Supermercado Objetivo (Líder) para calcular las Fases:", options=list(dict_supers.keys()), format_func=lambda x: dict_supers[x])

# 3. CÁLCULO EN VIVO DE ESTADÍSTICAS PREVIAS
if id_super_contexto:
    st.markdown("##### 📊 Análisis y Auditoría de Datos Históricos Disponibles")
    
    total_f1_unicos = 0
    total_f2_rescatados = 0
    
    try:
        conn_stats = psycopg2.connect(url_limpia)
        cur_s = conn_stats.cursor(cursor_factory=RealDictCursor)
        
        # Extraemos el pool histórico simplificado directamente de public.ofertas
        cur_s.execute("SELECT TRIM(id_producto) as id_producto, id_super, id_oferta FROM public.ofertas;")
        res_ofertas = cur_s.fetchall()
        conn_stats.close()
        
        if res_ofertas:
            df_pool = pd.DataFrame(res_ofertas)
            
            # Fase 1: Productos únicos del Supermercado Objetivo
            df_f1 = df_pool[df_pool["id_super"] == id_super_contexto].copy()
            if not df_f1.empty:
                df_f1_unicos = df_f1.drop_duplicates(subset=["id_producto"], keep="first")
                set_productos_lider = set(df_f1_unicos["id_producto"].tolist())
                total_f1_unicos = len(df_f1_unicos)
            else:
                set_productos_lider = set()
                
            # Fase 2: Productos de la Competencia que NO están en el Súper Objetivo
            df_f2 = df_pool[df_pool["id_super"] != id_super_contexto].copy()
            if not df_f2.empty:
                df_f2_filtrado = df_f2[~df_f2["id_producto"].isin(set_productos_lider)]
                df_f2_unicos = df_f2_filtrado.drop_duplicates(subset=["id_producto"], keep="first")
                total_f2_rescatados = len(df_f2_unicos)
                
    except Exception as e_stats:
        st.error(f"Error al calcular estadísticas previas: {e_stats}")

    # Render de Métricas idéntico al Mosaico original
    m1, m2, m3 = st.columns(3)
    m1.metric("SKUs Súper Líder (Fase 1)", total_f1_unicos)
    m2.metric("SKUs Rescatados Competencia (Fase 2)", total_f2_rescatados)
    m3.metric("Lote Total Neto Proyectado", total_f1_unicos + total_f2_rescatados)

    st.write("---")

    # 4. ALGORITMO ATÓMICO DE POBLADO
    if st.button("🎬 Inicialización Completa de Catálogo Histórico Cruzado", use_container_width=True, type="primary"):
        if total_f1_unicos == 0 and total_f2_rescatados == 0:
            st.error("Alerta: No se registran ofertas históricas previas para poblar este contenedor.")
        else:
            conn = None
            try:
                conn = psycopg2.connect(url_limpia)
                cur = conn.cursor()
                
                with st.spinner("Ejecutando UPSERT masivo en el servidor de Neon..."):
                    # El query extrae la oferta más reciente (posicion = 1) por combinación exacta
                    query_migracion = """
                        INSERT INTO public.ofertas_activas (id_producto, id_super, precio_oferta_proyectado)
                        SELECT 
                            TRIM(id_producto) as id_producto, 
                            id_super, 
                            precio_oferta as precio_oferta_proyectado
                        FROM (
                            SELECT id_producto, id_super, precio_oferta, id_oferta,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY TRIM(id_producto), id_super 
                                       ORDER BY id_oferta DESC
                                   ) as posicion
                            FROM public.ofertas
                        ) subconsulta
                        WHERE subconsulta.posicion = 1
                        ON CONFLICT (TRIM(id_producto), id_super) 
                        DO UPDATE SET 
                            precio_oferta_proyectado = EXCLUDED.precio_oferta_proyectado,
                            updated_at = CURRENT_TIMESTAMP;
                    """
                    cur.execute(query_migracion)
                    filas_afectadas = cur.rowcount
                    conn.commit()
                    
                st.balloons()
                st.success(f"¡Laboratorio poblado con éxito en Neon! Se procesaron {filas_afectadas} registros únicos.")
                st.rerun()
                
            except Exception as ex_v:
                if conn: conn.rollback()
                st.error(f"Falla transaccional al inicializar lote: {ex_v}")
            finally:
                if conn: conn.close()
