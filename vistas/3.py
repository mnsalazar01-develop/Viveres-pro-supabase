import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONTROL DE VERSIONES SUB-NUMÉRICO MAESTRO ---
VERSION_MODULO = "v3.8.1 - Caja Única Inteligente POS (Corregido)"

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

# Desplegamos el título oficial
st.title("📦 Administración de Productos")
st.caption(f"Motor de Clasificación: **{VERSION_MODULO}**")

# 2. CARGA SEGURA DE DICCIONARIOS MAESTROS DESDE EL SERVIDOR
try:
    res_p = supabase.table("productos").select("*").order("nombre").execute()
    lista_productos_maestra = res_p.data if res_p.data else []
    
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    # Cargamos subcategorías completas una sola vez para evitar consultas repetitivas
    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    lista_subcat_maestra = res_sc.data if res_sc.data else []
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in lista_subcat_maestra} if lista_subcat_maestra else {}
    
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    lista_productos_maestra = []
    cat_dict, cat_inv_dict, lista_cat, subcat_inv_dict, lista_subcat_maestra = {}, {}, [], {}, []

# --- FUNCIÓN PARA SUBIR IMÁGENES ---
def subir_a_storage(archivo):
    if archivo:
        try:
            nombre_archivo = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_("imagenes").upload(path=nombre_archivo, file=archivo.getvalue(), file_options={"content-type": archivo.type})
            return supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
        except Exception as e: 
            st.warning(f"No se pudo subir la imagen: {e}")
            return None
    return None

# --- FUNCIÓN DE VALIDACIÓN ANTI-DUPLICADOS ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras and str(barras).strip() != "":
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir: query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data: return "barras", res_barras.data[0]

    if lista_productos_maestra:
        nom_norm = "".join((nombre or "").lower().split())
        mar_norm = "".join((marca or "").lower().split())
        tam_norm = float(tamano if tamano is not None else 0)
        uni_norm = (unidad or "").lower()
        
        for p in lista_productos_maestra:
            if id_excluir and p.get('id_producto') == id_excluir:
                continue
            p_nom = "".join((p.get('nombre') or "").lower().split())
            p_mar = "".join((p.get('marca') or "").lower().split())
            p_tam = float(p.get('tamano') or 0)
            p_uni = (p.get('unidad') or "").lower()
            
            if nom_norm == p_nom and mar_norm == p_mar and tam_norm == p_tam and uni_norm == p_uni:
                return "atributos", p
    return None, None

# 3. INTERFAZ ORGANIZADA POR PESTAÑAS
t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])

# --- PESTAÑA 1: VER CATÁLOGO ---
with t1:
    if lista_productos_maestra:
        lista_tabla_limpia = []
        for p in lista_productos_maestra:
            lista_tabla_limpia.append({
                "ID": p.get("id_producto"), "Nombre": p.get("nombre"), "Marca": p.get("marca") or "Sin Marca",
                "Código Barras": p.get("codigo_barras") or "N/A", "Tamaño": p.get("tamano"), "Unidad": p.get("unidad"),
                "Categoría": cat_inv_dict.get(p.get("id_cat"), "Sin Categoría"),
                "Subcategoría": subcat_inv_dict.get(p.get("id_subcat"), "Sin Subcategoría"), "url_imagen": p.get("url_imagen") or ""
            })
        df_mostrar = pd.DataFrame(lista_tabla_limpia)
        st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
    else: 
        st.info("El catálogo de productos está vacío.")
        
# --- PESTAÑA 2: NUEVO PRODUCTO ---
with t2:
    st.subheader("Formulario de Carga")
    
    # Listas para sugerencias de autocompletado nativo
    lista_nombres_existentes = sorted(list(set([p['nombre'] for p in lista_productos_maestra if p.get('nombre')]))) if lista_productos_maestra else []
    lista_marcas_existentes = sorted(list(set([p['marca'] for p in lista_productos_maestra if p.get('marca') and p['marca'].strip() != ""]))) if lista_productos_maestra else []
    
    # --- FILA 1: NOMBRE Y MARCA (CORREGIDO: texto libre con sugerencias) ---
    f1_c1, f1_c2 = st.columns(2)
    nombre_final = f1_c1.text_input("Nombre del Producto*", autocomplete="on", placeholder="Escribe el nombre (ej: Harina Pan)...", key="w_nombre")
    if lista_nombres_existentes:
        f1_c1.caption(f"Sugerencias comunes: {', '.join(lista_nombres_existentes[:3])}")
        
    marca_final = f1_c2.text_input("Marca del Producto", autocomplete="on", placeholder="Escribe la marca comercial...", key="w_marca")
    if lista_marcas_existentes:
        f1_c2.caption(f"Marcas comunes: {', '.join(lista_marcas_existentes[:3])}")

    # --- FILA 2: TAMAÑO Y UNIDAD DE MEDIDA ---
    f2_c1, f2_c2 = st.columns(2)
    tam = f2_c1.number_input("Tamaño / Peso", min_value=0.0, step=1.0, value=0.0, key="n_tam")
    uni = f2_c2.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_uni")
    
    # --- FILA 3: CLASIFICACIÓN JERÁRQUICA (CORREGIDO: Filtrado en memoria) ---
    f3_c1, f3_c2 = st.columns(2)
    categoria_sel = f3_c1.selectbox("Categoría Principal", ["--- Seleccionar ---"] + lista_cat, key="n_cat")
    
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict[categoria_sel]
        # Filtramos localmente del arreglo maestro sin saturar la red
        subcat_filtradas = [s for s in lista_subcat_maestra if s.get('id_cat') == id_cat_actual]
        subcat_opciones += [s['nombre'] for s in subcat_filtradas]
        
    subcategoria_sel = f3_c2.selectbox("Subcategoría", subcat_opciones, key="n_sub")
    
    # --- FILA 4: SKU (CÓDIGO DE BARRAS) Y FOTO ---
    f4_c1, f4_c2 = st.columns(2)
    barras = f4_c1.text_input("Código de Barras (SKU)", key="n_bar", value="", placeholder="Escribe o escanea el código...").strip()
    foto = f4_c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    if foto:
        f4_c2.image(foto, caption="Miniatura cargada", width=140)

    st.write("---")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Omitir alertas de similitud)", key="n_forzar")

    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        if not nombre_final or str(nombre_final).strip() == "":
            st.error("El nombre del producto es obligatorio.")
        else:
            tipo_error, clon = validar_producto_existente(nombre_final, marca_final, barras, tam, uni)
            
            if tipo_error and not forzar_guardado:
                st.error(f"🚨 CLON DETECTADO: Ya existe un registro coincidente para '{clon['nombre']}' marca '{clon['marca']}'.")
            else:
                with st.spinner("Guardando registro e imagen..."):
                    url_img = subir_a_storage(foto) if foto else None
                    id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                    
                    # CORREGIDO: Búsqueda segura del ID de subcategoría en memoria externa
                    id_subcat_val = None
                    if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                        match_sub = [s for s in lista_subcat_maestra if s['nombre'] == subcategoria_sel and s['id_cat'] == id_cat_val]
                        if match_sub:
                            id_subcat_val = match_sub[0]['id_subcat']

                    # --- INSERCIÓN REAL EN SUPABASE ---
                    nuevo_producto = {
                        "nombre": nombre_final.strip(),
                        "marca": marca_final.strip() if marca_final else "Sin Marca",
                        "codigo_barras": barras if barras else None,
                        "tamano": tam,
                        "unidad": uni,
                        "id_cat": id_cat_val,
                        "id_subcat": id_subcat_val,
                        "url_imagen": url_img
                    }
                    
                    try:
                        supabase.table("productos").insert(nuevo_producto).execute()
                        st.success(f"🎉 Producto '{nombre_final}' registrado con éxito.")
                        st.rerun() # Recarga la aplicación para actualizar la tabla del catálogo instantáneamente
                    except Exception as ins_err:
                        st.error(f"Error al insertar en la base de datos: {ins_err}")

# --- PESTAÑA 3: EDITAR / BORRAR (Estructura base lista para tu desarrollo) ---
with t3:
    st.subheader("Modificar Inventario")
    if lista_productos_maestra:
        prod_nombres = {f"{p.get('nombre')} - {p.get('marca', '')} ({p.get('tamano')}{p.get('unidad')})": p for p in lista_productos_maestra}
        prod_seleccionado = st.selectbox("Selecciona el producto a gestionar", options=list(prod_nombres.keys()), index=None)
        
        if prod_seleccionado:
            p_datos = prod_nombres[prod_seleccionado]
            st.info(f"Has seleccionado el ID: {p_datos.get('id_producto')}. Aquí puedes implementar tus consultas de actualización (`.update()`) o borrado (`.delete()`).")
    else:
        st.info("No hay productos disponibles para editar.")
