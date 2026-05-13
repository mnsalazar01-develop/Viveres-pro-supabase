import streamlit as st
import pandas as pd
from datetime import datetime

if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("📦 Administración de Productos")

try:
    res_p = supabase.table("productos").select("*").order("nombre").execute()
    df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []
    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
except: df_p, cat_dict, cat_inv_dict, lista_cat, subcat_inv_dict = pd.DataFrame(), {}, {}, [], {}

def subir_a_storage(archivo):
    if archivo:
        try:
            nombre_archivo = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_("imagenes").upload(path=nombre_archivo, file=archivo.getvalue(), file_options={"content-type": archivo.type})
            return supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
        except: return None
    return None

def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras:
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir: query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data: return "barras", res_barras.data
    query_textos = supabase.table("productos").select("*")
    if id_excluir: query_textos = query_textos.neq("id_producto", id_excluir)
    res_textos = query_textos.execute()
    if res_textos.data:
        nom_norm, mar_norm = "".join(nombre.lower().split()), "".join((marca or "").lower().split())
        tam_norm, uni_norm = float(tamano), unidad.lower()
        for p in res_textos.data:
            if nom_norm == "".join(p['nombre'].lower().split()) and mar_norm == "".join((p['marca'] or "").lower().split()) and tam_norm == float(p['tamano'] or 0) and uni_norm == (p['unidad'] or "").lower():
                return "atributos", p
    return None, None

t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])

with t1:
    if not df_p.empty:
        df_mostrar = df_p.copy()
        if 'id_cat' in df_mostrar.columns: df_mostrar['categoria'] = df_mostrar['id_cat'].map(cat_inv_dict)
        if 'id_subcat' in df_mostrar.columns: df_mostrar['subcategoria'] = df_mostrar['id_subcat'].map(subcat_inv_dict)
        st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
    else: st.info("El catálogo está vacío.")
        
with t2:
    st.subheader("Formulario de Carga")
    c1, c2 = st.columns(2)
    nombre = c1.text_input("Nombre del Producto*", key="n_nom")
    marca = c2.text_input("Marca", key="n_mar")
    barras = c1.text_input("Código de Barras", key="n_bar").strip()
    tam = c2.number_input("Tamaño / Peso", min_value=0.0, step=0.1, key="n_tam")
    uni = c1.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_uni")
    foto = c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    categoria_sel = c1.selectbox("Categoría Principal", ["--- Seleccionar ---"] + lista_cat, key="n_cat")
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", cat_dict[categoria_sel]).order("nombre").execute()
        if res_sub_filtradas.data: subcat_opciones += [s['nombre'] for s in res_sub_filtradas.data]
    subcategoria_sel = c2.selectbox("Subcategoría", subcat_opciones, key="n_sub")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro", key="n_forzar")

    if st.button("🚀 Guardar Nuevo Producto", type="primary"):
        if nombre:
            tipo_error, clon = validar_producto_existente(nombre, marca, barras, tam, uni)
            if tipo_error and not forzar_guardado: st.error(f"🚨 DUPLICADO: Coincide con {clon['nombre']}")
            else:
                url_img = subir_a_storage(foto)
                id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                id_subcat_val = None
                if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                    sub_buscar = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                    if sub_buscar.data: id_subcat_val = sub_buscar.data['id_subcat']
                supabase.table("productos").insert({"nombre": nombre, "marca": marca, "codigo_barras": barras if barras else None, "tamano": tam, "unidad": uni, "url_imagen": url_img, "id_cat": id_cat_val, "id_subcat": id_subcat_val}).execute()
                st.success("¡Producto guardado!"); st.rerun()
        else: st.warning("El campo 'Nombre' es obligatorio.")

with t3:
    if not df_p.empty:
        prod_dict = {f"{p['nombre']} - {p['marca']} ({p['tamano']}{p['unidad']})": p for p in res_p.data}
        sel_e = st.selectbox("Selecciona un producto específico:", list(prod_dict.keys()), key="s_e_p")
        p_e = prod_dict[sel_e]
        st.write("---")
        ec1, ec2 = st.columns(2)
        en = ec1.text_input("Modificar Nombre", p_e['nombre'])
        em = ec2.text_input("Modificar Marca", p_e['marca'])
        eb = ec1.text_input("Modificar Código de Barras", p_e['codigo_barras'] or "").strip()
        et = ec2.number_input("Modificar Tamaño", value=float(p_e['tamano']) if p_e['tamano'] else 0.0)
        eu = ec1.selectbox("Modificar Unidad", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(p_e['unidad']) if p_e['unidad'] in ["gr", "kg", "ml", "lt", "unidad"] else 0)
        ef = ec2.file_uploader("Cambiar Imagen", type=['jpg', 'png', 'jpeg', 'webp'])
        c_act = c_inv_dict.get(p_e['id_cat'], "--- Seleccionar ---")
        l_cat_e = ["--- Seleccionar ---"] + lista_cat
        ecat = ec1.selectbox("Modificar Categoría Principal", l_cat_e, index=l_cat_e.index(c_act) if c_act in l_cat_e else 0, key="e_c")
        l_sub_e = ["--- Seleccionar ---"]
        if ecat != "--- Seleccionar ---":
            r_se = supabase.table("subcategorias").select("*").eq("id_cat", cat_dict[ecat]).order("nombre").execute()
            if r_se.data: l_sub_e += [s['nombre'] for s in r_se.data]
        s_act = subcat_inv_dict.get(p_e['id_subcat'], "--- Seleccionar ---")
        esub = ec2.selectbox("Modificar Subcategoría", l_sub_e, index=l_sub_e.index(s_act) if s_act in l_sub_e else 0, key="e_s")
        f_ed = st.checkbox("⚠️ Forzar cambios en edición", key="e_forzar")
        b_del, b_upd = st.columns(2)
        if b_upd.button("💾 Guardar Cambios del Producto", type="primary"):
            err, clon = validar_producto_existente(en, em, eb, et, eu, id_excluir=p_e['id_producto'])
            if err and not f_ed: st.error(f"🚨 DUPLICADO: Conflicto con {clon['nombre']}")
            else:
                n_url = subir_a_storage(ef) if ef else p_e['url_imagen']
                v_c = cat_dict[ecat] if ecat != "--- Seleccionar ---" else None
                v_s = None
                if esub != "--- Seleccionar ---" and v_c:
                    r_be = supabase.table("subcategorias").select("id_subcat").eq("nombre", esub).eq("id_cat", v_c).execute()
                    if r_be.data: v_s = r_be.data['id_subcat']
                supabase.table("productos").update({"nombre": en, "marca": em, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": n_url, "id_cat": v_c, "id_subcat": v_s}).eq("id_producto", p_e['id_producto']).execute()
                st.success("¡Cambios guardados!"); st.rerun()
        if b_del.button("🗑️ Eliminar Producto Definitivamente"):
            supabase.table("productos").delete().eq("id_producto", p_e['id_producto']).execute()
            st.warning("Producto borrado."); st.rerun()
