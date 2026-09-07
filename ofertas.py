# ==============================================================================
# PROGRAMA: ofertas_app.py | PARTE 1 DE 4
# MODULO: CONFIGURACIÓN GENERAL, ESTILOS E INICIALIZACIÓN CORE NEON
# ==============================================================================
import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date

# METADATOS DE CONTROL DE VERSIONES Y CONFIGURACIÓN DE LIENZO WEB
_version_ = "4.5.5"
_last_update_ = "2026-07-24"
_author_ = "Control Víveres Pro Team"

st.set_page_config(
    page_title=f"Ofertas v{_version_}",
    layout="wide",
    page_icon="🛍️"
)

# Estilos CSS Pro para alta densidad visual
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
    """Ejecuta sentencias SQL en Neon administrando el ciclo de vida de la conexión."""
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
# PROGRAMA: ofertas_app.py | PARTE 2 DE 4
# MODULO: EXTRACCIÓN RELACIONAL 3FN Y SELECTORES DE CONTEXTO DE CARGA
# ==============================================================================

try:
    # Extracción masiva sin límites HTTP REST (Bypass innecesario en PostgreSQL nativo)
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
    subcategorias_bd = ejecutar_consulta_neon("SELECT id_subcat, nombre, id_cat FROM public.subcategorias ORDER BY nombre;") or []

except Exception as e:
    st.error(f"❌ Error crítico de sincronización en red 3FN optimizada: {e}")
    st.stop()

st.title("📝 Registro de Ofertas")
st.caption(f"Consola Transaccional por Campaña Sincronizada Neon | Build v{_version_}")

# Normalización tolerante de datos heredados
for s in supermercados_bd:
    if 'nombre_supermercado' not in s or not s['nombre_supermercado']:
        s['nombre_supermercado'] = s.get('nombre_supermerkado', s.get('nombre', 'Supermercado'))

st.markdown("### 🔍 Contexto de Carga de la Jornada")
col_p1, col_p2, col_p3 = st.columns(3)

with col_p1:
    dict_supers = {s.get('id_super'): s.get('nombre_supermercado') for s in supermercados_bd if s.get('id_super')}
    super_fijo_box = st.selectbox(
        "🏭 Cadena Objetivo *:", 
        options=list(dict_supers.keys()), 
        format_func=lambda x: dict_supers.get(x),
        index=0 if list(dict_supers.keys()) else None
    )
    if super_fijo_box:
        st.session_state["id_super_operador"] = super_fijo_box

with col_p2:
    campanas_filtradas = []
    if campanas_bd and st.session_state["id_super_operador"]:
        for c in campanas_bd:
            if int(c.get('id_super')) == int(st.session_state["id_super_operador"]):
                campanas_filtradas.append(c)
                
    lista_ids_campanas = [c['id_campana'] for c in campanas_filtradas]
    dict_campanas = {c['id_campana']: f"ID: {c['id_campana']} | {c['nombre_campana'].upper()} [{c['fecha_inicio']} al {c['fecha_fin']}]" for c in campanas_filtradas}
    
    campana_fija_box = st.selectbox(
        "📅 Campaña / Folleto Destino *:", 
        options=sorted(lista_ids_campanas), 
        format_func=lambda x: dict_campanas.get(x, f"ID: {x}"),
        index=0 if lista_ids_campanas else None
    )
    if campana_fija_box:
        st.session_state["id_campana_operador"] = campana_fija_box

with col_p3:
    sucursales_filtradas = [s for s in sucursales_bd if str(s.get('id_super', '')).strip() == str(st.session_state["id_super_operador"])]
    cobertura_box = st.selectbox(
        "📍 Cobertura Geográfica *:", 
        options=["Corporativo", "Por Ciudad", "Sede Única"], 
        index=["Corporativo", "Por Ciudad", "Sede Única"].index(st.session_state["cobertura_operador"])
    )
    if cobertura_box:
        st.session_state["cobertura_operador"] = cobertura_box

# FIJAMOS LA VARIABLE GLOBAL DURA (Mismo comportamiento inmune a fallos de scope del PDF original)
id_campana_activa = st.session_state["id_campana_operador"]

id_sucursal_insertar = None
ciudad_seleccionada = None

if st.session_state["id_super_operador"] and id_campana_activa:
    with st.container():
        if "Corporativo" in st.session_state["cobertura_operador"]:
            st.info("ℹ️ Cobertura Nacional heredada automáticamente en cada producto.")
            id_sucursal_insertar = None
        elif "Por Ciudad" in st.session_state["cobertura_operador"]:
            lista_ciudades = sorted(list(set([str(s['ciudad']).strip() for s in sucursales_filtradas if s.get('ciudad')])))
            if lista_ciudades:
                ciudad_seleccionada = st.selectbox("🏙️ Seleccione Ciudad *:", options=lista_ciudades, index=None, placeholder="Filtrar por ciudad")
                if ciudad_seleccionada: id_sucursal_insertar = 0
            else: 
                st.warning("⚠️ Sin ciudades configuradas para esta cadena.")
        elif "Sede Única" in st.session_state["cobertura_operador"]:
            if sucursales_filtradas:
                dict_sucursales = {s['id_sucursal']: f"{s.get('nombre_sucursal', 'Sucursal')} ({s.get('ciudad', 'N/A')})" for s in sucursales_filtradas}
                suc_individual = st.selectbox("🏪 Seleccione Sede Única *:", options=list(dict_sucursales.keys()), format_func=lambda x: dict_sucursales.get(x))
                if ...: id_sucursal_insertar = int(suc_individual)
# ==============================================================================
# PROGRAMA: ofertas_app.py | PARTE 3 DE 4
# MODULO: FORMULARIO LINEAL EN CASCADA DIRECTA SOBRE PRODUCTOS Y GUARDADO SQL
# ==============================================================================

st.markdown("### 📥 Inserción Rápida de SKUs")
if not st.session_state.get("id_super_operador") or not id_campana_activa:
    st.warning("⚠️ Configure arriba la Cadena y la Campaña Destino para abrir la carrilera de carga.")
else:
    r1_c1, r1_c2 = st.columns(2)
    dict_categorias = {int(c['id_cat']): str(c['nombre']).strip() for c in categorias_bd if c.get('id_cat') is not None}
    dict_subcategorias = {int(s['id_subcat']): str(s['nombre']).strip() for s in subcategorias_bd if s.get('id_subcat') is not None}
    
    lista_categorias = sorted(dict_categorias.keys(), key=lambda x: dict_categorias[x].lower())
    id_cat_seleccionada = r1_c1.selectbox("1. Categoría:", options=lista_categorias, index=None, format_func=lambda x: dict_categorias.get(x))
    
    subcats_disponibles = [s for s in subcategorias_bd if id_cat_seleccionada is not None and s.get('id_cat') is not None and int(s['id_cat']) == int(id_cat_seleccionada)]
    lista_subcategorias = sorted([int(s['id_subcat']) for s in subcats_disponibles], key=lambda x: dict_subcategorias.get(x, "").lower())
    id_subcat_seleccionada = r1_c2.selectbox("2. Subcategoría:", options=lista_subcategorias, index=None, format_func=lambda x: dict_subcategorias.get(x))
    
    # Filtrado directo en la RAM
    productos_filtrados = []
    for p in productos_bd:
        if id_cat_seleccionada is not None and int(p.get('id_cat') or 0) != int(id_cat_seleccionada): continue
        if id_subcat_seleccionada is not None and int(p.get('id_subcat') or 0) != int(id_subcat_seleccionada): continue
        productos_filtrados.append(p)
        
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    
    # Descripciones extraídas directamente de productos (Evitamos tabla catalogo)
    nombres_unicos = sorted(list(set([str(p['nombre']).strip() for p in productos_filtrados if p.get('nombre')])))
    buscar_nombre = r2_c1.selectbox("3. Descripción (Producto) *:", options=nombres_unicos, index=None, placeholder="Buscar artículo...")
    
    # Marcas extraídas directo de productos (Evitamos tabla marcas)
    marcas_unicas = set()
    if buscar_nombre:
        for p in productos_filtrados:
            if str(p.get('nombre', '')).strip().lower() == buscar_nombre.strip().lower():
                if p.get('marca'): marcas_unicas.add(str(p['marca']).strip())
                
    lista_marcas_filtradas = sorted(list(marcas_unicas))
    buscar_marca = r2_c2.selectbox("4. Marca (Fabricante) *:", options=lista_marcas_filtradas, index=None, placeholder="Seleccionar marca")
    
    lista_presentaciones_filtradas = []
    mapa_opciones_productos = {}
    
    if buscar_nombre and buscar_marca:
        for p in productos_filtrados:
            p_nom_check = str(p.get('nombre', '')).strip().lower()
            p_mar_check = str(p.get('marca', '')).strip().lower()
            
            if p_nom_check == buscar_nombre.strip().lower() and p_mar_check == buscar_marca.strip().lower():
                tamano_val = float(p['tamano']) if p['tamano'] else 0.0
                unidad_val = str(p.get('unit', 'unidad')).strip()
                sku_val = str(p['codigo_barras'] or 'Sin SKU').strip()
                
                etiqueta_presentacion = f"{tamano_val} {unidad_val} [SKU: {sku_val}]"
                id_actual = int(p['id_producto'])
                mapa_opciones_productos[id_actual] = {"label": etiqueta_presentacion, "objeto": p}
                lista_presentaciones_filtradas.append(id_actual)
                
    prod_id_seleccionado = r2_c3.selectbox(
        "5. Presentación Específica *:", 
        options=lista_presentaciones_filtradas, 
        index=None, 
        format_func=lambda x: mapa_opciones_productos[x]["label"] if x in mapa_opciones_productos else ""
    )
    
    id_producto_final = None
    sku_autodetectado = "N/A"
    if prod_id_seleccionado and prod_id_seleccionado in mapa_opciones_productos:
        producto_objeto = mapa_opciones_productos[prod_id_seleccionado]["objeto"]
        id_producto_final = int(producto_objeto.get('id_producto'))
        sku_autodetectado = producto_objeto.get('codigo_barras') or "Sin SKU"
        
    rf_c1, rf_c2, rf_c3, rf_c4, rf_c5 = st.columns(5)
    rf_c1.text_input("SKU Detectado:", value=sku_autodetectado, disabled=True, key="ofr_sku_auto")
    precio_txt = rf_c2.text_input("Precio Oferta *:", placeholder="Ej: 3.45", key="ofr_precio_input")
    pag_insertar = rf_c3.selectbox("Página Revista *:", options=list(range(1, 16)), index=None, placeholder="1 al 15")
    slot_insertar = rf_c4.selectbox("Posición Slot *:", options=list(range(1, 13)), index=None, placeholder="1 al 12")
    align_insertar = rf_c5.selectbox("Alineación *:", options=["I", "C", "D"], index=1, help="I=Izquierda, C=Centro, D=Derecha")
    
    st.write("<br>", unsafe_allow_html=True)
    key_dinamica_boton = f"btn_save_oferta_neon_{id_campana_activa}"
    
    if st.button("🚀 Publicar Oferta Activa", use_container_width=True, key=key_dinamica_boton, type="primary"):
        if id_producto_final is None or not precio_txt.strip() or pag_insertar is None or slot_insertar is None:
            st.error("❌ Campos obligatorios incompletos. Seleccione un artículo, fije el precio y asigne Página/Slot.")
        elif "Por Ciudad" in st.session_state.get("cobertura_operador", "") and ciudad_seleccionada is None:
            st.error("❌ Contexto incompleto: Seleccione la ciudad fija arriba.")
        elif "Sede Única" in st.session_state.get("cobertura_operador", "") and id_sucursal_insertar is None:
            st.error("❌ Contexto incompleto: Seleccione la sucursal fija arriba.")
        else:
            try: 
                precio_float = float(precio_txt.strip())
            except ValueError: 
                st.error("❌ Precio inválido.")
                st.stop()
                
            char_align_final = str(align_insertar).strip().upper()
            if char_align_final not in ["I", "C", "D"]: char_align_final = "C"
            
            cobertura = st.session_state.get("cobertura_operador", "")
            sucursal_final_val = None
            if "Por Ciudad" in cobertura: sucursal_final_val = 0
            elif "Sede Única" in cobertura: sucursal_final_val = int(id_sucursal_insertar)
            
            query_insert = """
                INSERT INTO public.ofertas (
                    id_producto, id_super, precio_oferta, id_campana, 
                    numero_pagina, posicion_slot, alineacion, id_sucursal,
                    es_favorita, en_lista_compras, oferta_comprada
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, False, False, False);
            """
            valores = (int(id_producto_final), int(st.session_state["id_super_operador"]), float(precio_float), 
                       int(id_campana_activa), int(pag_insertar), int(slot_insertar), char_align_final, sucursal_final_val)
            
            if ejecutar_consulta_neon(query_insert, valores, fetch=False, commit=True):
                st.balloons()
                st.success(f"🎉 ¡CONSOLIDACIÓN EXITOSA! Guardado unario en Neon '{char_align_final}'.")
                if "ofertas" in st.session_state: del st.session_state.ofertas
                st.rerun()
# ==============================================================================
# PROGRAMA: ofertas_app.py | PARTE 4 DE 4
# MODULO: CLONACIÓN ATÓMICA EN SERVIDOR, RENDERS DE DATAFRAMES Y SIDEBAR
# ==============================================================================

# --- MONITOR DE CLONACIÓN DE JORNADAS DE PRUEBAS ---
st.markdown("---")
col_btn1, col_btn2 = st.columns(2)

with col_btn1:
    if st.button("🔏 Clonar Campaña Actual a Test", use_container_width=True, type="primary"):
        if not id_campana_activa:
            st.error("❌ Primero debes seleccionar una campaña en el combo de arriba.")
        else:
            with st.spinner("Duplicando ofertas en espejo Neon de forma atómica..."):
                query_clonar = """
                    INSERT INTO public.ofertas_campana_test (
                        id_producto, id_super, precio_oferta, id_campana, 
                        numero_pagina, posicion_slot, alineacion, id_sucursal,
                        es_favorita, en_lista_compras, oferta_comprada
                    ) 
                    SELECT id_producto, id_super, precio_oferta, id_campana, 
                           numero_pagina, posicion_slot, alineacion, id_sucursal,
                           es_favorita, en_lista_compras, oferta_comprada
                    FROM public.ofertas WHERE id_campana = %s;
                """
                conn = None
                try:
                    conn = psycopg2.connect(url_limpia)
                    cur = conn.cursor()
                    cur.execute(query_clonar, (int(id_campana_activa),))
                    filas_copiadas = cur.rowcount
                    conn.commit()
                    
                    if filas_copiadas > 0:
                        st.success(f"¡Brillante! {filas_copiadas} ofertas copiadas a 'ofertas_campana_test'.")
                        st.balloons()
                    else:
                        st.warning(f"La campaña {id_campana_activa} no tiene ofertas registradas.")
                except Exception as err_clon:
                    st.error(f"Error en servidor al clonar: {err_clon}")
                    if conn: conn.rollback()
                finally:
                    if conn: conn.close()

with col_btn2:
    st.info(f"💡 **Modo Prototipo:** Al pulsar el botón izquierdo, se duplicarán las ofertas de la campaña **{id_campana_activa}** directo en el entorno aislado de simulación.")

# --- GRILLA HISTÓRICA IN SITU ---
nombre_campana_cabecera = dict_campanas.get(id_campana_activa, "NINGUNA")
st.markdown(f"### 📊 Ofertas Cargadas en: {nombre_campana_cabecera}", unsafe_allow_html=True)

if ofertas_raw:
    df_o_grid = pd.DataFrame(ofertas_raw)
    df_o_grid = df_o_grid[df_o_grid["id_campana"].fillna(0).astype(int) == int(id_campana_activa)]
    
    if df_o_grid.empty: 
        st.info(f"🍃 Esta campaña se encuentra limpia en '{nombre_campana_cabecera}'.")
    else:
        df_p_grid = pd.DataFrame(productos_bd) if productos_bd else pd.DataFrame()
        df_s_grid = pd.DataFrame(supermercados_bd) if supermercados_bd else pd.DataFrame()
        
        if not df_p_grid.empty:
            df_o_grid["id_producto"] = df_o_grid["id_producto"].astype(int)
            df_p_grid["id_producto"] = df_p_grid["id_producto"].astype(int)
            
            # Construcción del Artículo Maestro directo desde los datos de productos
            df_p_grid["Artículo Maestro"] = df_p_grid["nombre"].fillna("").astype(str) + " | " + df_p_grid["marca"].fillna("").astype(str)
            df_merged = pd.merge(df_o_grid, df_p_grid[["id_producto", "Artículo Maestro"]], on="id_producto", how="inner")
            
            if not df_merged.empty and not df_s_grid.empty:
                df_merged["id_super"] = df_merged["id_super"].astype(int)
                df_s_grid["id_super"] = df_s_grid["id_super"].astype(int)
                df_merged = pd.merge(df_merged, df_s_grid[["id_super", "nombre_supermercado"]], on="id_super", how="inner")
                
            if not df_merged.empty:
                if "alineacion" in df_merged.columns:
                    df_merged["raw_align_clean"] = df_merged["alineacion"].fillna("centro").astype(str).str.lower().str.strip()
                    mapa_tolerante = {"izquierda": "I", "izq": "I", "i": "I", "centro": "C", "cen": "C", "c": "C", "derecha": "D", "der": "D", "d": "D"}
                    df_merged["Alineación"] = df_merged["raw_align_clean"].map(mapa_tolerante).fillna("C")
                else: 
                    df_merged["Alineación"] = "C"
                    
                df_render_final = pd.DataFrame({
                    "ID Oferta": df_merged["id_oferta"],
                    "Página": df_merged.get("numero_pagina", 0).fillna(0).astype(int),
                    "Slot Pos": df_merged.get("posicion_slot", 0).fillna(0).astype(int),
                    "Alineación": df_merged["Alineación"],
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
                    key=f"grilla_historico_neon_{id_campana_activa}_{len(df_render_final)}"
                )

with st.sidebar:
    st.markdown("### ⚙️ Control")
    st.info(f"**Modo:** Cobertura Zonal\n\n**Inserción:** Unaria Estricta (Neon)\n\n**Foliado:** Revista v{_version_}")
