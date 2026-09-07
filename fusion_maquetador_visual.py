# ==============================================================================
# PROGRAMA: fusion_maquetador_visual.py | PARTE 1 DE 5
# MODULO: CONFIGURACIÓN GENERAL, ESTILOS E INICIALIZACIÓN CORE NEON
# ==============================================================================
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import math

# CONFIGURACIÓN DE METADATOS Y LIENZO WEB
_version_ = "5.0.0-FUSION"
st.set_page_config(
    page_title=f"Fusión Visual v{_version_}",
    layout="wide",
    page_icon="🖼️"
)

# Estilos CSS Pro para alta densidad visual oscura
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
if "cobertura_operador" not in st.session_state:
    st.session_state["cobertura_operador"] = "Sede Única"

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
# PROGRAMA: fusion_maquetador_visual.py | PARTE 2 DE 5
# MODULO: DESCARGA RELACIONAL 3FN Y SELECTORES DE CONTEXTO COMERCIAL
# ==============================================================================

try:
    # Descarga directa de PostgreSQL sin límites de paginación REST API
    ofertas_raw = ejecutar_consulta_neon("SELECT * FROM public.ofertas ORDER BY id_oferta DESC;") or []
    
    query_prod = """
        SELECT id_producto, nombre, marca, tamano, url_imagen,
               codigo_barras, id_cat, id_subcat, unidad AS unit 
        FROM public.productos;
    """
    productos_bd = ejecutar_consulta_neon(query_prod) or []
    supermercados_bd = ejecutar_consulta_neon("SELECT * FROM public.supermercados;") or []
    sucursales_bd = ejecutar_consulta_neon("SELECT * FROM public.sucursales;") or []
    campanas_bd = ejecutar_consulta_neon("SELECT id_campana, id_super, nombre_campana, fecha_inicio, fecha_fin FROM public.campanas;") or []
    categorias_bd = ejecutar_consulta_neon("SELECT id_cat, nombre FROM public.categorias ORDER BY nombre;") or []
    subcategorias_bd = ejecutar_consulta_neon("SELECT id_subcat, id_cat, nombre FROM public.subcategorias ORDER BY nombre;") or []

except Exception as e:
    st.error(f"❌ Error crítico de sincronización en red 3FN optimizada: {e}")
    st.stop()

st.title("🖼️ Panel de Carga Visual de Ofertas")
st.caption(f"Consola Híbrida de Inserción Unaria mediante Mosaico de Catálogo | Neon Build v{_version_}")

# Normalización de datos de supermercados heredados
for s in supermercados_bd:
    if 'nombre_supermercado' not in s or not s['nombre_supermercado']:
        s['nombre_supermercado'] = s.get('nombre_supermerkado', s.get('nombre', 'Supermercado'))

st.markdown("### 🔍 1. Contexto Geográfico y de Campaña")
col_p1, col_p2, col_p3, col_p4 = st.columns(4)

with col_p1:
    dict_supers = {s.get('id_super'): s.get('nombre_supermercado') for s in supermercados_bd if s.get('id_super')}
    super_fijo_box = st.selectbox("🏭 Cadena Objetivo *:", options=list(dict_supers.keys()), format_func=lambda x: dict_supers.get(x), index=0 if list(dict_supers.keys()) else None)
    if super_fijo_box: 
        st.session_state["id_super_operador"] = super_fijo_box

with col_p2:
    campanas_filtradas = [c for c in campanas_bd if int(c.get('id_super', 0)) == int(st.session_state["id_super_operador"])] if campanas_bd else []
    lista_ids_campanas = [c['id_campana'] for c in campanas_filtradas]
    dict_campanas = {c['id_campana']: f"ID: {c['id_campana']} | {c['nombre_campana'].upper()}" for c in campanas_filtradas}
    
    campana_fija_box = st.selectbox("📅 Campaña Destino *:", options=sorted(lista_ids_campanas), format_func=lambda x: dict_campanas.get(x, f"ID: {x}"), index=0 if lista_ids_campanas else None)
    if campana_fija_box: 
        st.session_state["id_campana_operador"] = campana_fija_box

with col_p3:
    sucursales_filtradas = [s for s in sucursales_bd if str(s.get('id_super', '')).strip() == str(st.session_state["id_super_operador"])]
    cobertura_box = st.selectbox("📍 Cobertura Geográfica *:", options=["Corporativo", "Por Ciudad", "Sede Única"], index=["Corporativo", "Por Ciudad", "Sede Única"].index(st.session_state["cobertura_operador"]))
    if cobertura_box: 
        st.session_state["cobertura_operador"] = cobertura_box

with col_p4:
    columnas_elegidas = st.slider("Columnas Grid:", min_value=3, max_value=6, value=4, step=1)

id_campana_activa = st.session_state["id_campana_operador"]
id_sucursal_insertar = None
ciudad_seleccionada = None

if st.session_state["id_super_operador"] and id_campana_activa:
    with st.container():
        if "Por Ciudad" in st.session_state["cobertura_operador"]:
            lista_ciudades = sorted(list(set([str(s['ciudad']).strip() for s in sucursales_filtradas if s.get('ciudad')])))
            if lista_ciudades:
                ciudad_seleccionada = st.selectbox("🏙️ Ciudad Fija:", options=lista_ciudades, index=None, placeholder="Selecciona la ciudad")
                if ciudad_seleccionada: 
                    id_sucursal_insertar = 0
        elif "Sede Única" in st.session_state["cobertura_operador"]:
            if sucursales_filtradas:
                dict_sucursales = {s['id_sucursal']: f"{s.get('nombre_sucursal', 'Sucursal')} ({s.get('ciudad', 'N/A')})" for s in sucursales_filtradas}
                suc_individual = st.selectbox("🏪 Sede Única Fija:", options=list(dict_sucursales.keys()), format_func=lambda x: dict_sucursales.get(x))
                if suc_individual: 
                    id_sucursal_insertar = int(suc_individual)
# ==============================================================================
# PROGRAMA: fusion_maquetador_visual.py | PARTE 3 DE 5
# MODULO: GENERACIÓN DE PESTAÑAS Y EXCLUSIÓN DE OFERTAS PUBLICADAS (RAM)
# ==============================================================================

st.markdown("---")
st.markdown("### 📥 2. Catálogo de Artículos Disponibles por Pasillo")

if not st.session_state.get("id_super_operador") or not id_campana_activa:
    st.warning("⚠️ Configure arriba la Cadena y la Campaña Destino para abrir la galería visual.")
else:
    nombres_pestanas = [cat["nombre"].upper() for cat in categorias_bd]
    pestanas_ui = st.tabs(nombres_pestanas)
    
    # Creamos un set de exclusión en tiempo real con lo que ya está maquetado en Neon
    ids_productos_ya_publicados = set([
        int(o["id_producto"]) for o in ofertas_raw 
        if o.get("id_campana") is not None and int(o["id_campana"]) == int(id_campana_activa) and o.get("id_producto") is not None
    ])
    
    for index_tab, cat_info in enumerate(categorias_bd):
        id_categoria_actual = cat_info["id_cat"]
        
        with pestanas_ui[index_tab]:
            # Extraemos artículos que correspondan al pasillo actual y que NO estén en el set de exclusión
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
# PROGRAMA: fusion_maquetador_visual.py | PARTE 4 DE 5
# MODULO: MATRIZ DE PRODUCTOS COMPACTOS E INSERCIÓN DIRECTA A POSTGRESQL (NEON)
# ==============================================================================

            # (Bloque anidado dentro del contexto de la pestaña activa de la Parte 3)
            if items_finales_mosaico:
                st.caption(f"Mostrando {len(items_finales_mosaico)} artículos disponibles para publicar en este segmento")
                
                for i in range(0, len(items_finales_mosaico), columnas_elegidas):
                    bloque_items = items_finales_mosaico[i:i + columnas_elegidas]
                    columnas_ui = st.columns(columnas_elegidas)
                    
                    for idx, prod in enumerate(bloque_items):
                        with columnas_ui[idx]:
                            id_p_raw = int(prod["id_producto"])
                            nombre_lbl = str(prod.get("nombre", "")).strip().upper()
                            marca_lbl = str(prod.get("marca", "Sin Marca")).strip()[:10]
                            formato_empaque = f"{prod.get('tamano', '')} {prod.get('unit', '')}".strip()
                            url_foto = prod.get("url_imagen") or "https://picsum.photos"
                            
                            # Renderizado de Micro-Tarjeta de alta densidad (idéntico al programa anterior)
                            st.markdown(
                                f"""
                                <div style="display: flex; align-items: center; background-color: #1e1e2e; padding: 8px; border-radius: 6px; border-left: 5px solid #0d6efd; box-shadow: 0 1px 3px rgba(0,0,0,0.2); margin-bottom: 8px;">
                                    <div style="flex-shrink: 0; margin-right: 10px;">
                                        <img src="{url_foto}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 4px; border: 1px solid #313244; background-color: #fff;"/>
                                    </div>
                                    <div style="flex-grow: 1; min-width: 0;">
                                        <strong style="color: #cdd6f4; font-size: 0.75rem; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{nombre_lbl}</strong>
                                        <span style="color: #a6adc8; font-size: 0.65rem; display: block;">{marca_lbl} | {formato_empaque}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True
                            )
                            
                            # Contenedor de inputs proporcionales para optimizar el espacio vertical
                            with st.container(border=True):
                                pvp_input = st.number_input("PVP ($):", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"pvp_{id_p_raw}_{id_campana_activa}")
                                
                                c_sel1, c_sel2, c_sel3 = st.columns([1, 1, 1])
                                with c_sel1:
                                    pag_input = st.selectbox("Pág:", options=list(range(1, 16)), index=0, key=f"pag_{id_p_raw}_{id_campana_activa}")
                                with c_sel2:
                                    slot_input = st.selectbox("Slot:", options=list(range(1, 13)), index=0, key=f"slot_{id_p_raw}_{id_campana_activa}")
                                with c_sel3:
                                    aln_input = st.selectbox("Alm:", options=["I", "C", "D"], index=1, key=f"aln_{id_p_raw}_{id_campana_activa}")
                                
                                # Botón transaccional unaria integrado en el pie
                                if st.button("🚀 Publicar", use_container_width=True, key=f"btn_pub_{id_p_raw}_{id_campana_activa}"):
                                    if pvp_input <= 0.0:
                                        st.error("Fije precio > 0.")
                                    elif "Por Ciudad" in st.session_state.get("cobertura_operador", "") and ciudad_seleccionada is None:
                                        st.error("Falta Ciudad.")
                                    elif "Sede Única" in st.session_state.get("cobertura_operador", "") and id_sucursal_insertar is None:
                                        st.error("Falta Sede.")
                                    else:
                                        sucursal_final_val = None
                                        if "Por Ciudad" in st.session_state["cobertura_operador"]: 
                                            sucursal_final_val = 0
                                        elif "Sede Única" in st.session_state["cobertura_operador"]: 
                                            sucursal_final_val = int(id_sucursal_insertar)
                                        
                                        query_insert = """
                                            INSERT INTO public.ofertas (
                                                id_producto, id_super, precio_oferta, id_campana, 
                                                numero_pagina, posicion_slot, alineacion, id_sucursal,
                                                es_favorita, en_lista_compras, oferta_comprada
                                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, False, False, False);
                                        """
                                        valores = (id_p_raw, int(st.session_state["id_super_operador"]), float(pvp_input), 
                                                   int(id_campana_activa), int(pag_input), int(slot_input), str(aln_input), sucursal_final_val)
                                        
                                        if ejecutar_consulta_neon(query_insert, valores, fetch=False, commit=True):
                                            st.toast(f"¡{nombre_lbl} publicado!", icon="✅")
                                            st.cache_data.clear()
                                            st.rerun()
            else:
                st.info("🍃 No quedan productos pendientes por maquetar en este pasillo.")

# ==============================================================================
# PROGRAMA: fusion_maquetador_visual.py | PARTE 5 DE 5
# MODULO: BITÁCORA DE CONTROL DE OFERTAS PUBLICADAS Y SIDEBAR
# ==============================================================================

# --- GRILLA HISTÓRICA IN SITU ---
st.markdown("---")
nombre_campana_cabecera = dict_campanas.get(id_campana_activa, "NINGUNA")
st.markdown(f"### 📊 3. Monitoreo de Ofertas Publicadas en: <span style='color: #f9e2af;'>{nombre_campana_cabecera}</span>", unsafe_allow_html=True)

if ofertas_raw:
    df_o_grid = pd.DataFrame(ofertas_raw)
    df_o_grid = df_o_grid[df_o_grid["id_campana"].fillna(0).astype(int) == int(id_campana_activa)]
    
    if df_o_grid.empty: 
        st.info(f"🍃 Aún no se registran ofertas publicadas para la campaña '{nombre_campana_cabecera}'.")
    else:
        df_p_grid = pd.DataFrame(productos_bd) if productos_bd else pd.DataFrame()
        df_s_grid = pd.DataFrame(supermercados_bd) if supermercados_bd else pd.DataFrame()
        
        if not df_p_grid.empty:
            df_o_grid["id_producto"] = df_o_grid["id_producto"].astype(int)
            df_p_grid["id_producto"] = df_p_grid["id_producto"].astype(int)
            
            # Formateamos los registros uniendo las columnas nativas de productos
            df_p_grid["Artículo Maestro"] = df_p_grid["nombre"].fillna("").astype(str) + " | " + df_p_grid["marca"].fillna("").astype(str)
            df_merged = pd.merge(df_o_grid, df_p_grid[["id_producto", "Artículo Maestro"]], on="id_producto", how="inner")
            
            if not df_merged.empty and not df_s_grid.empty:
                df_merged["id_super"] = df_merged["id_super"].astype(int)
                df_s_grid["id_super"] = df_s_grid["id_super"].astype(int)
                df_merged = pd.merge(df_merged, df_s_grid[["id_super", "nombre_supermercado"]], on="id_super", how="inner")
                
            if not df_merged.empty:
                df_render_final = pd.DataFrame({
                    "ID Oferta": df_merged["id_oferta"],
                    "Página": df_merged.get("numero_pagina", 0).fillna(0).astype(int),
                    "Slot Pos": df_merged.get("posicion_slot", 0).fillna(0).astype(int),
                    "Alineación": df_merged.get("alineacion", "C"),
                    "Cadena Retail": df_merged["nombre_supermercado"],
                    "Artículo Publicado": df_merged["Artículo Maestro"],
                    "PVP Oferta ($)": df_merged["precio_oferta"].fillna(0.0).astype(float)
                }).sort_values(by=["Página", "Slot Pos", "ID Oferta"], ascending=[True, True, False])
                
                st.dataframe(
                    df_render_final,
                    column_config={
                        "ID Oferta": st.column_config.NumberColumn("ID Oferta", width="small"),
                        "Página": st.column_config.NumberColumn("Pág", format="%d", width="small"),
                        "Slot Pos": st.column_config.NumberColumn("Slot", format="%d", width="small"),
                        "Alineación": st.column_config.TextColumn("Alm.", width="small"),
                        "Cadena Retail": st.column_config.TextColumn("Cadena Comercial", width="medium"),
                        "Artículo Publicado": st.column_config.TextColumn("Artículo Maestro", width="large"),
                        "PVP Oferta ($)": st.column_config.NumberColumn("Precio ($)", format="$ %.2f", width="small"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"grilla_fusion_historica_{id_campana_activa}_{len(df_render_final)}"
                )

with st.sidebar:
    st.markdown("### ⚙️ Control")
    st.info(f"**Modo:** Fusión Visual Híbrida\n\n**Inserción:** Unaria por Tarjeta (Neon)\n\n**Foliado:** Revista v{_version_}")
