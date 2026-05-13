import streamlit as st
import pandas as pd

if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("📁 Estructura de Clasificación Jerárquica")

try:
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []
    res_sc = supabase.table("subcategorias").select("*, categorias(nombre, id_cat)").execute()
    df_sc = pd.json_normalize(res_sc.data) if res_sc.data else pd.DataFrame()
except: df_c, df_sc, cat_dict, lista_cat = pd.DataFrame(), pd.DataFrame(), {}, []

t1, t2 = st.tabs(["📁 Categorías Principales", "🌿 Subcategorías (Hijos)"])

with t1:
    st.subheader("Módulo de Categorías")
    tc1, tc2, tc3 = st.tabs(["📋 Ver Categorías", "➕ Nueva Categoría", "✏️ Editar/Borrar"])
    with tc1: st.dataframe(df_c[['id_cat', 'nombre']], use_container_width=True) if not df_c.empty else st.info("No hay categorías.")
    with tc2:
        n_cat = st.text_input("Nombre de la Nueva Categoría Principal")
        if st.button("🚀 Guardar Categoría"):
            if n_cat:
                supabase.table("categorias").insert({"nombre": n_cat}).execute()
                st.success("Guardada."); st.rerun()
    with tc3:
        if not df_c.empty:
            c_map = {c['nombre']: c for c in res_c.data}
            s_c = st.selectbox("Selecciona Categoría:", list(c_map.keys()), key="s_c_e")
            c_d = c_map[s_c]
            un_c = st.text_input("Nombre", c_d['nombre'], key="u_c_n")
            bc1, bc2 = st.columns(2)
            if bc1.button("💾 Actualizar Categoría"):
                supabase.table("categorias").update({"nombre": un_c}).eq("id_cat", c_d['id_cat']).execute()
                st.success("Listo."); st.rerun()
            if bc2.button("🗑️ Eliminar Categoría"):
                supabase.table("categorias").delete().eq("id_cat", c_d['id_cat']).execute()
                st.warning("Borrada."); st.rerun()

with t2:
    st.subheader("Módulo de Subcategorías")
    tsc1, tsc2, tsc3 = st.tabs(["📋 Ver Subcategorías", "➕ Nueva Subcategoría", "✏️ Editar/Borrar"])
    with tsc1:
        if not df_sc.empty:
            df_ord = df_sc.sort_values(by='categorias.id_cat')
            st.dataframe(df_ord.rename(columns={'nombre': 'Subcategoría', 'categorias.nombre': 'Categoría Padre', 'categorias.id_cat': 'N° Cat'})[['N° Cat', 'Categoría Padre', 'Subcategoría']], use_container_width=True)
        else: st.info("No hay subcategorías.")
    with tsc2:
        if lista_cat:
            c_padre = st.selectbox("Selecciona Categoría Padre (Orden Numérico):", lista_cat, key="sc_p")
            n_sub = st.text_input("Nombre de Subcategoría")
            if st.button("🚀 Guardar Subcategoría"):
                if n_sub:
                    supabase.table("subcategorias").insert({"nombre": n_sub, "id_cat": cat_dict[c_padre]}).execute()
                    st.success("Guardada."); st.rerun()
    with tsc3:
        if not df_sc.empty:
            sc_map = {f"{r['categorias.nombre']} -> {r['nombre']}": r for _, r in df_sc.iterrows()}
            s_sc = st.selectbox("Selecciona Subcategoría:", list(sc_map.keys()), key="s_sc_e")
            sc_d = sc_map[s_sc]
            un_sc = st.text_input("Nombre", sc_d['nombre'], key="u_sc_n")
            bsc1, bsc2 = st.columns(2)
            if bsc1.button("💾 Actualizar Subcategoría"):
                supabase.table("subcategorias").update({"nombre": un_sc}).eq("id_subcat", sc_d['id_subcat']).execute()
                st.success("Listo."); st.rerun()
            if bsc2.button("🗑️ Eliminar Subcategoría"):
                supabase.table("subcategorias").delete().eq("id_subcat", sc_d['id_subcat']).execute()
                st.warning("Borrada."); st.rerun()
