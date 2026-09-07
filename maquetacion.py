import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import math
import pandas as pd

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.set_page_config(layout="wide", page_title="Maquetador Profesional de Ofertas (Neon)")
st.title("📖 Maquetador de Ofertas - Integrado con Neon")

# --- 1. CONEXIÓN A NEON ---
try:
    url_limpia = st.secrets["neon"]["url"]
except KeyError:
    st.error("❌ Error: Falta configurar la variable ['neon']['url'] en los Secrets de Streamlit.")
    st.stop()

def ejecutar_consulta_neon(query, parametros=(), fetch=True, commit=False):
    """Función helper para abrir y cerrar conexiones seguras con Neon."""
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
        st.error(f"❌ Error de Base de Datos (Neon): {e}")
        if conn and commit:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

# --- 2. ESTADOS ---
if "pagina_actual" not in st.session_state:
    st.session_state.pagina_actual = 1
if "config_paginas" not in st.session_state:
    st.session_state.config_paginas = {}

# --- 3. CAMPANAS (EXTRACCIÓN DE CAMPAÑAS CON OFERTAS ACTIVAS) ---
# Traemos las campañas que actualmente tienen al menos una oferta vinculada
query_campanas = """
    SELECT DISTINCT c.id_campana, c.nombre_campana 
    FROM public.campanas c
    INNER JOIN public.ofertas o ON c.id_campana = o.id_campana
    ORDER BY c.id_campana DESC;
"""
lista_campanas = ejecutar_consulta_neon(query_campanas)

if not lista_campanas:
    st.warning("⚠️ No se encontraron campañas con ofertas registradas en Neon.")
    st.stop()

# Mapeo de etiqueta visual -> ID numérico
dict_campanas_opciones = {f"{c['id_campana']} - {c['nombre_campana']}": c["id_campana"] for c in lista_campanas}

# --- 4. SELECTOR DE CAMPAÑA (INMUNE A RERUNS) ---
st.markdown("### 🎯 Selección de Campaña de Trabajo")
lista_opciones_campanas = list(dict_campanas_opciones.keys())

if "id_campana_maestro" not in st.session_state and lista_opciones_campanas:
    st.session_state["id_campana_maestro"] = int(dict_campanas_opciones[lista_opciones_campanas[0]])

indice_congelado = 0
if st.session_state.get("id_campana_maestro") is not None:
    for idx, label in enumerate(lista_opciones_campanas):
        if int(dict_campanas_opciones[label]) == st.session_state["id_campana_maestro"]:
            indice_congelado = idx
            break

def cambiar_campana_callback():
    etiqueta_nueva = st.session_state["selector_campana_estatico"]
    st.session_state["id_campana_maestro"] = int(dict_campanas_opciones[etiqueta_nueva])
    if "ofertas" in st.session_state:
        del st.session_state.ofertas

st.selectbox(
    "Campañas con ofertas disponibles en Neon:",
    options=lista_opciones_campanas,
    index=indice_congelado,
    key="selector_campana_estatico",
    on_change=cambiar_campana_callback
)

id_campana_activa = st.session_state["id_campana_maestro"]

with st.container(border=True):
    st.success(f"✅ Campaña activa protegida en RAM ID: **{id_campana_activa}**")

# --- 5. HELPERS GENERALES ---
def safe_int(val, default=None):
    try:
        if val is None or str(val).lower() in ("null", "", "none") or str(val) == "0":
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default

def calcular_num_cols(num_slots):
    if num_slots == 1: return 1
    if num_slots == 2: return 2
    if num_slots in (3, 4): return 2
    if num_slots in (5, 6): return 3
    return 4

# --- 6. CARGA DE OFERTAS (FILTRO ANTI-REFRESCO) ---
if "ofertas" not in st.session_state or st.session_state.get("campana_id_verificada") != id_campana_activa:
    st.session_state["campana_id_verificada"] = id_campana_activa
    
    # Traemos las ofertas de la campaña actual uniendo los datos del producto (nombre e imagen) con un LEFT JOIN
    query_ofertas_full = """
        SELECT 
            o.id_oferta, o.id_producto, o.precio_oferta, o.numero_pagina, o.posicion_slot, o.posicion_mix,
            p.nombre AS nombre_producto, p.url_imagen
        FROM public.ofertas o
        LEFT JOIN public.productos p ON o.id_producto = p.id_producto
        WHERE o.id_campana = %s;
    """
    datos_ofertas = ejecutar_consulta_neon(query_ofertas_full, (id_campana_activa,))
    
    ofertas_procesadas = []
    if datos_ofertas:
        for o in datos_ofertas:
            # Homologamos campos nulos o flotantes
            o["numero_pagina"] = safe_int(o.get("numero_pagina"))
            o["posicion_slot"] = safe_int(o.get("posicion_slot"))
            
            # Formateamos datos visuales de la tarjeta
            o["nombre"] = o.get("nombre_producto") or f"Producto #{o['id_producto']}"
            o["img"] = o.get("url_imagen") or "https://picsum.photos"
            ofertas_procesadas.append(o)
            
    st.session_state.ofertas = ofertas_procesadas

# --- 7. NAVEGACIÓN Y CONFIGURACIÓN DE LA HOJA ---
st.markdown("### 🛠️ Configuración de la Hoja del Folleto")
pag_act = safe_int(st.session_state.pagina_actual, 1)

def avanzar_pagina(): st.session_state.pagina_actual += 1
def retroceder_pagina():
    if st.session_state.pagina_actual > 1: st.session_state.pagina_actual -= 1

slots_usados = [
    safe_int(o["posicion_slot"]) for o in st.session_state.get("ofertas", [])
    if safe_int(o.get("numero_pagina")) == pag_act and safe_int(o.get("posicion_slot")) is not None
]
slot_maximo_detectado = max(slots_usados) if slots_usados else 4

if pag_act not in st.session_state.config_paginas:
    st.session_state.config_paginas[pag_act] = {"slots": slot_maximo_detectado, "distribucion": "Equilibrado", "estilo": "Estándar"}
elif slot_maximo_detectado > int(st.session_state.config_paginas[pag_act]["slots"]):
    st.session_state.config_paginas[pag_act]["slots"] = slot_maximo_detectado

cfg = st.session_state.config_paginas[pag_act]

with st.container(border=True):
    nav_cols = st.columns(6)
    with nav_cols[0]: st.button("⬅️ Anterior", use_container_width=True, on_click=retroceder_pagina, disabled=(st.session_state.pagina_actual == 1))
    with nav_cols[1]: st.markdown(f"<h3 style='text-align: center; margin:0; color:#0d6efd;'>Pág. {st.session_state.pagina_actual}</h3>", unsafe_allow_html=True)
    with nav_cols[2]: st.button("Siguiente ➡️", use_container_width=True, on_click=avanzar_pagina, key="btn_nav_sig")
    with nav_cols[3]: 
        slots_deseados = st.slider("Slots asignados:", min_value=1, max_value=8, value=int(cfg["slots"]), key=f"sld_p{pag_act}")
        st.session_state.config_paginas[pag_act]["slots"] = slots_deseados
    with nav_cols[4]: st.session_state.config_paginas[pag_act]["distribucion"] = st.selectbox("Distribución:", ["Equilibrado", "Banner Superior"], key=f"dist_{pag_act}")
    with nav_cols[5]: st.session_state.config_paginas[pag_act]["estilo"] = st.selectbox("Estilo:", ["Estándar", "Destacado", "Compacto"], key=f"est_{pag_act}")

num_cols_reales = calcular_num_cols(slots_deseados)

# --- 8. BANCO DE OFERTAS INTERACTIVO ---
st.markdown("### 📥 Banco de Ofertas y Asignación Inmediata")
ofertas_actuales = st.session_state.get("ofertas", [])

# Productos que no tienen página ni slot asignado todavía
banco_ofertas = [o for o in ofertas_actuales if o.get("numero_pagina") is None or o.get("posicion_slot") is None]
conteo_banco = len(banco_ofertas)

with st.expander(f"🛒 Productos Disponibles en el Banco ({conteo_banco} SKUs)", expanded=(conteo_banco > 0)):
    if banco_ofertas:
        cols_banco = st.columns(3)
        for idx, o in enumerate(banco_ofertas):
            with cols_banco[idx % 3]:
                # Renderizado HTML de la tarjeta
                st.markdown(
                    f"""
                    <div style="display: flex; align-items: center; background-color: #f8f9fa; padding: 10px; border-radius: 6px; border-left: 5px solid #0d6efd; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 10px;">
                        <div style="flex-shrink: 0; margin-right: 12px;">
                            <img src="{o['img']}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px; border: 1px solid #dee2e6; background-color: #fff;"/>
                        </div>
                        <div style="flex-grow: 1; min-width: 0;">
                            <strong style="color: #212529; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{o['nombre']}</strong>
                            <span style="color: #198754; font-weight: 600; font-size: 0.8rem; display: block;">${o['precio_oferta']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True
                )
                col_sel, col_go = st.columns([2, 1])
                with col_sel:
                    opciones_slots = [f"Enviar al Slot {i}" for i in range(1, slots_deseados + 1)]
                    slot_elegido_str = st.selectbox("Destino", options=opciones_slots, label_visibility="collapsed", key=f"sel_{o['id_oferta']}_{idx}")
                with col_go:
                    if st.button("+ Asignar", key=f"btn_{o['id_oferta']}_{idx}", use_container_width=True):
                        o["numero_pagina"] = pag_act
                        o["posicion_slot"] = int(slot_elegido_str.split("Slot ")[1])
                        st.rerun()
    else:
        st.success("🎉 ¡Banco vacío! Todas las ofertas han sido distribuidas en las hojas.")

# --- 9. VISTA DE LA MATRIZ DE SLOTS ---
st.markdown("### 📊 Distribución Actual en la Hoja")
num_filas_visuales = math.ceil(slots_deseados / num_cols_reales)
slot_actual = 1

for f in range(num_filas_visuales):
    cols_grilla = st.columns(num_cols_reales)
    for c in range(num_cols_reales):
        if slot_actual <= slots_deseados:
            with cols_grilla[c]:
                # Buscamos qué ofertas están ocupando este slot en este momento
                ofertas_en_este_slot = [
                    o for o in ofertas_actuales
                    if safe_int(o.get("numero_pagina")) == pag_act and safe_int(o.get("posicion_slot")) == slot_actual
                ]
                cant_items = len(ofertas_en_este_slot)
                
                # Contenedor visual del Slot físico
                with st.container(border=True):
                    st.markdown(f"**Slot {slot_actual}** <span style='color:#6c757d;'>({cant_items} Prod.)</span>", unsafe_allow_html=True)
                    
                    if ofertas_en_este_slot:
                        for idx, item in enumerate(ofertas_en_este_slot):
                            c_txt, c_btn = st.columns([4, 1])
                            with c_txt:
                                st.markdown(f"<p style='font-size:0.85rem; margin:0; padding-top:4px;'>🔹 Mix {idx+1}: {item['nombre']}</p>", unsafe_allow_html=True)
                            with c_btn:
                                if st.button("X", key=f"quitar_{item['id_oferta']}_{slot_actual}_{idx}", help="Quitar de este slot"):
                                    # Limpiamos las coordenadas espaciales en la RAM locales
                                    item["numero_pagina"] = None
                                    item["posicion_slot"] = None
                                    item["posicion_mix"] = None
                                    st.rerun()
                    else:
                        st.caption("Vacío / Disponible")
            slot_actual += 1

# Variable de compatibilidad para desactivar lógica de arrastre obsoleta
sorted_data = None
# --- 10. TABLA DE ASIGNADAS (CALCULO DE FILAS Y MIX EN CALIENTE) ---
st.markdown(f"### 📋 Ofertas Asignadas en la Página ({pag_act})")
filas_tabla_ofertas = []
rastreador_mix_local = {}
ofertas_en_memoria = st.session_state.get("ofertas", [])

for o in ofertas_en_memoria:
    num_pag = safe_int(o.get("numero_pagina"))
    pos_slot = safe_int(o.get("posicion_slot"))
    
    if num_pag == pag_act and pos_slot is not None:
        # Calculamos la posición correlativa en caliente del Mix (1, 2, 3...)
        rastreador_mix_local[pos_slot] = rastreador_mix_local.get(pos_slot, 0) + 1
        posicion_en_el_mix = rastreador_mix_local[pos_slot]
        
        # Sincronizamos el valor en el objeto real de la memoria RAM
        o["posicion_mix"] = posicion_en_el_mix
        
        # Cuadrícula espacial basada en helpers de columnas reales
        fila_calculada = ((pos_slot - 1) // num_cols_reales) + 1
        columna_calculated = ((pos_slot - 1) % num_cols_reales) + 1
        id_oferta_seguro = safe_int(o.get("id_oferta")) or 0
        
        filas_tabla_ofertas.append({
            "ID Oferta": id_oferta_seguro,
            "Producto": str(o.get("nombre", "Sin Nombre")),
            "Precio": float(o.get("precio_oferta", 0.0)),
            "Slot Físico": int(pos_slot),
            "Fila Matriz": int(fila_calculada),
            "Columna Matriz": int(columna_calculated),
            "Estructura Mix": f"Sub-Producto {posicion_en_el_mix}",
            "Estilo Visual": str(cfg.get("estilo", "Estándar"))
        })

if filas_tabla_ofertas:
    df_ofertas = pd.DataFrame(filas_tabla_ofertas)
    st.dataframe(
        df_ofertas,
        use_container_width=True,
        hide_index=True
    )
    st.caption(f"📊 Total de elementos maquetados en esta hoja: {len(filas_tabla_ofertas)} ofertas.")
else:
    st.info("Ninguna oferta asignada en esta hoja todavía.")


# --- 11. ACCIÓN: GUARDAR CONFIGURACIÓN COMPLETA EN NEON (PERSISTENCIA DE MIX REAL) ---
if st.button("💾 Guardar Configuración Completa del Folleto", type="primary", use_container_width=True):
    lote_para_guardar = []
    ofertas_actuales = st.session_state.get("ofertas", [])
    
    if ofertas_actuales:
        with st.spinner("Sincronizando cambios con tu Base de Datos Neon..."):
            conn = None
            try:
                conn = psycopg2.connect(url_limpia)
                cur = conn.cursor()
                
                asignadas_count = 0
                desasignadas_count = 0
                
                for o in ofertas_actuales:
                    num_pag = safe_int(o.get("numero_pagina"))
                    pos_slot = safe_int(o.get("posicion_slot"))
                    
                    if num_pag is not None and pos_slot is not None:
                        config_pag = st.session_state.config_paginas.get(num_pag, {})
                        num_cols_pag = calcular_num_cols(config_pag.get("slots", slots_deseados))
                        
                        fila = ((pos_slot - 1) // num_cols_pag) + 1
                        columna = ((pos_slot - 1) % num_cols_pag) + 1
                        mix = safe_int(o.get("posicion_mix", 1))
                        estilo = config_pag.get("estilo", "Estándar")
                        
                        query_update = """
                            UPDATE public.ofertas
                            SET numero_pagina = %s, posicion_slot = %s, posicion_mix = %s,
                                numero_fila = %s, numero_columna = %s, sub_molde_estilo = %s
                            WHERE id_oferta = %s;
                        """
                        cur.execute(query_update, (num_pag, pos_slot, mix, fila, columna, estilo, o["id_oferta"]))
                        asignadas_count += 1
                    else:
                        query_clear = """
                            UPDATE public.ofertas
                            SET numero_pagina = NULL, posicion_slot = NULL, posicion_mix = NULL,
                                numero_fila = NULL, numero_columna = NULL, sub_molde_estilo = NULL
                            WHERE id_oferta = %s;
                        """
                        cur.execute(query_clear, (o["id_oferta"],))
                        desasignadas_count += 1
                
                # Confirmamos la transacción en lote
                conn.commit()
                
                st.success(f"🎉 ¡Sincronización Exitosa! {len(ofertas_actuales)} registros procesados.")
                st.info(f"🔹 {asignadas_count} ofertas maquetadas | 🔸 {desasignadas_count} ofertas en banco")
                st.toast("Base de datos actualizada correctamente", icon="🚀")
                
                # Limpiamos caché de sesión para forzar la recarga desde Neon
                if "ofertas" in st.session_state:
                    del st.session_state.ofertas
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error al guardar en Neon: {str(e)}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()
    else:
        st.warning("No hay elementos para persistir.")


# --- 12. MAPA GENERAL DEL FOLLETO (FLATPLAN) ---
st.divider()
st.markdown("### 🗺️ Mapa General del Folleto (Flatplan)")
st.caption("Los botones resaltados indican la página que estás visualizando actualmente. Haz clic en cualquier hoja para saltar directamente.")

# Aseguramos que existan las variables de control en tu script
pag_act = int(st.session_state.get("pagina_actual", 1))

# Calculamos el conteo real de ofertas por página desde st.session_state.ofertas
mapa_aforos_visor_local = {}
for o in st.session_state.get("ofertas", []):
    p_num = safe_int(o.get("numero_pagina"))
    if p_num is not None:
        mapa_aforos_visor_local[p_num] = mapa_aforos_visor_local.get(p_num, 0) + 1

conteo_por_pagina = dict(mapa_aforos_visor_local)

# Renderizado de la matriz de 20 páginas (Bloques de 4 columnas)
for fila_bloque in range(1, 21, 4):
    columnas_flatplan = st.columns(4)
    for sub_col_idx in range(4):
        id_p_bucle = fila_bloque + sub_col_idx
        
        if id_p_bucle <= 20:
            # Extraemos la cantidad de productos asignados a esta hoja (0 por defecto)
            skus_conteo = conteo_por_pagina.get(id_p_bucle, 0)
            
            # Resaltamos con color llamativo (primary) la página en la que el usuario está parado
            tipo_color = "primary" if id_p_bucle == pag_act else "secondary"
            etiqueta_bucle = f"📄 HOJA {id_p_bucle} [{skus_conteo} Items]"
            
            with columnas_flatplan[sub_col_idx]:
                if st.button(
                    etiqueta_bucle,
                    use_container_width=True,
                    type=tipo_color,
                    key=f"btn_nav_visor_p_{id_p_bucle}"
                ):
                    # Sincronización de navegación rápida y recarga limpia
                    st.session_state["pagina_actual"] = int(id_p_bucle)
                    st.rerun()
