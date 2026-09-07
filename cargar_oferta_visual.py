# ==============================================================================
# PROGRAMA: registro_ofertas_corporativo.py | PARTE 1 DE 5
# MODULO: CONFIGURACIÓN GENERAL, ESTILOS E INICIALIZACIÓN CORE NEON
# ==============================================================================
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import math

# CONFIGURACIÓN DE METADATOS Y LIENZO WEB
_version_ = "5.5.0-EXPRESS"
st.set_page_config(
    page_title=f"Registro Express v{_version_}",
    layout="wide",
    page_icon="🖼️"
)

# Estilos CSS Pro para alta densidad visual oscura (Idéntico a Central de Carga)
st.markdown("""
<style>
.stApp { background-color: #0f111a; color: #cdd6f4; }
div[data-testid="stMetric"] { background-color: #1e1e2e; border: 1px solid #313244; padding: 15px; border-radius: 8px; }
div[data-testid="stMetricValue"] { color: #f9e2af; font-size: 2rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# INICIALIZACIÓN DE VARIABLES STICKY DE SESIÓN OPERADOR
if "id_super_operador" not in st.session_state:
    st.session_state["id_super_operador"] = None
if "id_campana_operador" not in st.session_state:
    st.session_state["id_campana_operador"] = None

# --- VALIDACIÓN DE SECRETOS NEON ---
try:
    url_limpia = st.secrets["neon"]["url"]
except KeyError:
    st.error("❌ Error de configuración: Falta la variable ['neon']['url'] en los secrets.")
    st.stop()

def ejecutar_consulta_neon(query, parametros=(), fetch=True, commit=False):
    """Ejecuta sentencias SQL en Neon administrando de forma segura la conexión."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, parametros)
        if commit:
            conn.commit()
        if fetch:
            return cur.fetchall()
        return True
    except Exception as e:
        st.error(f"❌ Fallo crítico en motor relacional Neon: {e}")
        if conn and commit:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()
# ==============================================================================
# PROGRAMA: registro_ofertas_corporativo.py | PARTE 2 DE 5
# MODULO: DESCARGA RELACIONAL 3FN Y SELECTORES DE CONTEXTO CORPORATIVO
# ==============================================================================

try:
    # Descarga directa de PostgreSQL en un solo viaje
    ofertas_raw = ejecutar_consulta_neon("SELECT * FROM public.ofertas ORDER BY id_oferta DESC;") or []
    
    query_prod = """
        SELECT id_producto, nombre, marca, tamano, unidad, url_imagen, codigo_barras, id_cat, id_subcat 
        FROM public.productos;
    """
    productos_bd = ejecutar_consulta_neon(query_prod) or []
    supermercados_bd = ejecutar_consulta_neon("SELECT id_super, nombre_supermercado FROM public.supermercados;") or []
    campanas_bd = ejecutar_consulta_neon("SELECT id_campana, id_super, nombre_campana, fecha_inicio, fecha_fin FROM public.campanas;") or []
    categorias_bd = ejecutar_consulta_neon("SELECT id_cat, nombre FROM public.categorias ORDER BY nombre;") or []
    subcategorias_bd = ejecutar_consulta_neon("SELECT id_subcat, id_cat, nombre FROM public.subcategorias ORDER BY nombre;") or []

except Exception as e:
    st.error(f"❌ Error crítico de sincronización en red 3FN optimizada: {e}")
    st.stop()

st.title("🖼️ Central de Carga del Golpe - Nivel Corporativo")
st.caption(f"Copia Fiel del Mosaico Visual Original adaptado a Carga de Precios Pura | Neon Build v{_version_}")

# Normalización de datos de supermercados
mapa_supers_ram = {int(s["id_super"]): s["nombre_supermercado"] for s in supermercados_bd} if supermercados_bd else {}

st.markdown("#### 1. Coordenadas de Entrada Comercial")
col_s1, col_s2, col_s5 = st.columns([1.5, 2.0, 1.5])

with col_s1:
    ids_supers_activos = sorted(list(set([int(c["id_super"]) for c in campanas_bd if c.get("id_super") is not None])))
    id_super_contexto = st.selectbox("Supermercado Objetivo:", options=ids_supers_activos, format_func=lambda x: mapa_supers_ram.get(x, f"Super #{x}"))
    if id_super_contexto:
        st.session_state["id_super_operador"] = id_super_contexto
    campanas_filtradas = [c for c in campanas_bd if int(c.get("id_super", 0)) == id_super_contexto]

with col_s2:
    if not campanas_filtradas:
        st.error("No hay campañas configuradas para esta cadena.")
        st.stop()
    campana_destino_sel = st.selectbox(
        "Campaña Contenedora:",
        options=campanas_filtradas,
        format_func=lambda x: f"ID: {x['id_campana']} | {x['nombre_campana']}"
    )
    id_campana_activa = int(campana_destino_sel["id_campana"])

with col_s5:
    # Densidad expandida de 6 a 15 columnas por fila igual a la central original
    columnas_elegidas = st.slider("Columnas por Fila (Densidad):", min_value=6, max_value=15, value=9, step=3)
    config_zoom = {
        6: {"altura_px": 85, "font_b": "0.72rem", "font_span": "0.62rem", "trim": 20},
        9: {"altura_px": 65, "font_b": "0.65rem", "font_span": "0.58rem", "trim": 14},
        12: {"altura_px": 50, "font_b": "0.58rem", "font_span": "0.52rem", "trim": 10},
        15: {"altura_px": 42, "font_b": "0.52rem", "font_span": "0.48rem", "trim": 8}
    }
    layout_dinamico = config_zoom.get(columnas_elegidas, config_zoom[9])
# ==============================================================================
# PROGRAMA: registro_ofertas_corporativo.py | PARTE 3 DE 5
# MODULO: FILTRADO DE PASILLOS Y SISTEMA DE EXCLUSIÓN EN TIEMPO REAL (RAM)
# ==============================================================================

if "formulario_imagenes_dict" not in st.session_state:
    st.session_state["formulario_imagenes_dict"] = {}

st.markdown("---")
st.markdown("### 📥 2. Catálogo de Artículos Disponibles por Pasillo")

if not st.session_state.get("id_super_operador") or not id_campana_activa:
    st.warning("⚠️ Configure arriba la Cadena y la Campaña Destino para abrir la galería visual.")
else:
    nombres_pestanas = [cat["nombre"].upper() for cat in categorias_bd]
    pestanas_ui = st.tabs(nombres_pestanas)
    
    # Set de exclusión instantánea: Si ya se registró en esta campaña, no se muestra en el catálogo pendiente
    ids_productos_ya_publicados = set([
        int(o["id_producto"]) for o in ofertas_raw 
        if o.get("id_campana") is not None and int(o["id_campana"]) == int(id_campana_activa) and o.get("id_producto") is not None
    ])
    
    for index_tab, cat_info in enumerate(categorias_bd):
        id_categoria_actual = cat_info["id_cat"]
        
        with pestanas_ui[index_tab]:
            items_del_pasillo = [
                p for p in productos_bd 
                if p.get("id_cat") is not None and int(p["id_cat"]) == int(id_categoria_actual)
                and int(p["id_producto"]) not in ids_productos_ya_publicados
            ]
            
            sub_filtradas = [s for s in subcategorias_bd if s.get("id_cat") is not None and int(s["id_cat"]) == int(id_categoria_actual)]
            opciones_sub = [{"id_subcat": None, "nombre": "--- VER TODO EL PASILLO ---"}] + sub_filtradas
            
            sub_seleccionada = st.selectbox(
                "Refinar surtido por subcategoría:",
                options=opciones_sub,
                format_func=lambda x: x["nombre"].upper(),
                key=f"sub_fuse_{id_categoria_actual}"
            )
            
            if sub_seleccionada["id_subcat"] is not None:
                items_finales_mosaico = [item for item in items_del_pasillo if item.get("id_subcat") is not None and int(item["id_subcat"]) == int(sub_seleccionada["id_subcat"])]
            else:
                items_finales_mosaico = items_del_pasillo
# ==============================================================================
# PROGRAMA: registro_ofertas_corporativo.py | PARTE 4 DE 5
# MODULO: RENDERIZADO FIEL DE REJILLA VERTICAL (ESTILO MOSAICO ORIGINAL)
# ==============================================================================

            # (Bloque anidado dentro del contexto de la pestaña activa de la Parte 3)
            if items_finales_mosaico:
                st.caption(f"Mostrando {len(items_finales_mosaico)} artículos listos para registro corporativo")
                
                # Iteración espacial basada en la densidad elegida (6 a 15)
                for i in range(0, len(items_finales_mosaico), columnas_elegidas):
                    bloque_items = items_finales_mosaico[i:i + columnas_elegidas]
                    columnas_ui = st.columns(columnas_elegidas)
                    
                    for idx, prod in enumerate(bloque_items):
                        with columnas_ui[idx]:
                            id_p_raw = int(prod["id_producto"])
                            
                            # Aplicamos exactamente el truncado y escalado de fuentes dinámicas original
                            limite_caracteres = layout_dinamico["trim"]
                            nombre_lbl = str(prod.get("nombre", "")).strip().upper()[:limite_caracteres]
                            marca_lbl = str(prod.get("marca", "Sin Marca")).strip()[:10]
                            formato_empaque = f"{prod.get('tamano', '')} {prod.get('unidad', '')}".strip()
                            
                            html_especificacion = f"""
                            <div style='line-height:1.1; margin-bottom:4px; height: 42px; overflow: hidden;'>
                                <b style='font-size: {layout_dinamico["font_b"]}; color:#cdd6f4;'>{nombre_lbl}</b><br>
                                <span style='font-size: {layout_dinamico["font_span"]}; color: #a6adc8;'>{marca_lbl} | {formato_empaque}</span>
                            </div>
                            """
                            
                            url_foto_render = prod.get("url_imagen") or "https://picsum.photos"
                            
                            # Renderizado en contenedor vertical idéntico al Mosaico original
                            with st.container(border=True):
                                st.image(url_foto_render, use_container_width=True)
                                st.markdown(html_especificacion, unsafe_allow_html=True)
                                
                                p_key_string = f"num_pvp_{id_p_raw}_{id_campana_activa}"
                                m_key_string = f"chk_load_{id_p_raw}_{id_campana_activa}"
                                
                                # Inputs puros de captura
                                st.number_input("PVP ($):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=p_key_string)
                                st.checkbox("Incluir", value=False, key=m_key_string)
                                
                                # Guardamos los punteros de los widgets en el diccionario global
                                st.session_state["formulario_imagenes_dict"][id_p_raw] = {
                                    "id_producto": id_p_raw,
                                    "precio_key": p_key_string,
                                    "marcado_key": m_key_string
                                }
            else:
                st.info("🍃 No quedan productos pendientes por registrar en este pasillo.")
# ==============================================================================
# PROGRAMA: registro_ofertas_corporativo.py | PARTE 5 DE 5
# MODULO: INYECCIÓN EXPRESS MASIVA (SQL LOTE), RESETEO Y BITÁCORA INFERIOR
# ==============================================================================

# PANEL DE ACCIONES COMERCIALES (Ubicado fuera de los tabs, al pie del catálogo)
st.write("---")
col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if st.button("🔥 Disparar Inyección Express de Todo lo Seleccionado", use_container_width=True, type="primary"):
        payload_rafaga = []
        
        # Escaneamos el mapa de memoria de las tarjetas
        for id_prod, referencias in st.session_state.get("formulario_imagenes_dict", {}).items():
            marcado_final = st.session_state.get(referencias["marcado_key"], False)
            precio_final = st.session_state.get(referencias["precio_key"], 0.0)
            
            # Solo guardamos los elementos que el operador marcó manualmente en pantalla
            if marcado_final and precio_final > 0.0:
                payload_rafaga.append({
                    "id_producto": int(id_prod),
                    "precio": float(precio_final)
                })
                
        if payload_rafaga:
            with st.spinner("Inyectando ofertas corporativas en lote masivo a Neon..."):
                conn = None
                try:
                    conn = psycopg2.connect(url_limpia)
                    cur = conn.cursor()
                    
                    for registro in payload_rafaga:
                        # Inserción limpia con id_sucursal, pagina y slot forzados a NULL
                        query_insert = """
                            INSERT INTO public.ofertas (
                                id_producto, id_super, precio_oferta, id_campana, id_sucursal,
                                numero_pagina, posicion_slot, alineacion, es_favorita, en_lista_compras, oferta_comprada
                            ) VALUES (%s, %s, %s, %s, NULL, NULL, NULL, 'C', False, False, False);
                        """
                        valores = (registro["id_producto"], int(st.session_state["id_super_operador"]), registro["precio"], id_campana_activa)
                        cur.execute(query_insert, valores)
                        
                    conn.commit()
                    st.toast(f"🚀 ¡Sincronización Exitosa! {len(payload_rafaga)} ofertas guardadas.", icon="✅")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as err_sql:
                    st.error(f"❌ Error de persistencia en Neon: {err_sql}")
                    if conn: conn.rollback()
                finally:
                    if conn: conn.close()
        else:
            st.warning("⚠️ No se ha detectado ningún elemento marcado con precio válido en la galería.")

with col_btn2:
    if st.button("🗑️ Vaciar / Resetear Ofertas de Campaña", use_container_width=True, type="secondary"):
        if id_campana_activa > 0:
            query_delete = "DELETE FROM public.ofertas WHERE id_campana = %s;"
            if ejecutar_consulta_neon(query_delete, (id_campana_activa,), fetch=False, commit=True):
                st.session_state["formulario_imagenes_dict"] = {}
                st.toast("¡Campaña reseteada con éxito!", icon="🧹")
                st.cache_data.clear()
                st.rerun()

# --- BITÁCORA DE CONTROL INFERIOR ---
st.write("---")
st.markdown(f"#### 📋 3. Monitoreo de Ofertas Publicadas (Historial Corporativo)")

df_o_grid = pd.DataFrame(ofertas_raw) if ofertas_raw else pd.DataFrame()
if not df_o_grid.empty:
    df_o_grid = df_o_grid[df_o_grid["id_campana"].fillna(0).astype(int) == int(id_campana_activa)]

if df_o_grid.empty:
    st.info("🍃 No se registran ofertas guardadas aún en esta campaña.")
else:
    df_p_grid = pd.DataFrame(productos_bd) if productos_bd else pd.DataFrame()
    if not df_p_grid.empty:
        df_o_grid["id_producto"] = df_o_grid["id_producto"].astype(int)
        df_p_grid["id_producto"] = df_p_grid["id_producto"].astype(int)
        
        df_merged = pd.merge(df_o_grid, df_p_grid, on="id_producto", how="inner")
        
        if not df_merged.empty:
            df_render_final = pd.DataFrame({
                "ID Oferta": df_merged["id_oferta"],
                "Marca": df_merged["marca"].fillna("Sin Marca"),
                "Artículo": df_merged["nombre"],
                "Presentación": df_merged["tamano"].astype(str) + " " + df_merged["unidad"].astype(str),
                "Precio Registrado ($)": df_merged["precio_oferta"].astype(float),
                "Ámbito": "CORPORATIVO (Nacional)"
            }).sort_values(by=["Artículo", "ID Oferta"], ascending=[True, False])
            
            st.dataframe(
                df_render_final,
                column_config={"Precio Registrado ($)": st.column_config.NumberColumn(format="$ %.2f")},
                hide_index=True,
                use_container_width=True,
                key=f"grilla_audit_corp_{id_campana_activa}_{len(df_render_final)}"
            )

with st.sidebar:
    st.markdown("### ⚙️ Control")
    st.info(f"**Ámbito:** Corporativo\n\n**Carga:** Ráfaga Masiva\n\n**Neon Status:** Conectado")
