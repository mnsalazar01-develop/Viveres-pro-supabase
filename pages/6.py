import streamlit as st
import pandas as pd

if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("🏷️ Cargar Ofertas por Catálogo")

try:
    res_c = supabase.table("categorias").select("id_cat, nombre").order("id_cat").execute()
    c_inv = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
except: supers, c_inv = None, {}

if supers and supers.data:
    df_s = pd.DataFrame(supers.data)
    super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
    super_sel = st.selectbox("¿De qué Supermercado es el volante?", list(super_dict.keys()))
    
    try: sucs = supabase.table("sucursales").select("*").eq("id_super", super_dict[super_sel]).execute()
    except: sucs = None

    suc_dict = {"--- TODAS LAS SUCURSALES ---": None}
    if sucs and sucs.data:
        for s in sucs.data: suc_dict[s['nombre_sucursal']] = s['id_sucursal']
    suc_sel = st.selectbox("¿Aplica a una sucursal específica?", list(suc_dict.keys()))
    
    try: prods = supabase.table("productos").select("id_producto, nombre, marca, id_cat").execute()
    except: prods = None

    if prods and prods.data:
        p_df = pd.DataFrame(prods.data)
        p_df['cat_nombre'] = p_df['id_cat'].map(c_inv).fillna("Sin Categoría")
        p_df['label_visual'] = "[" + p_df['cat_nombre'] + "] " + p_df['nombre'] + " (" + p_df['marca'] + ")"
        p_dict = dict(zip(p_df['label_visual'], p_df['id_producto']))
        lista_prods_ordenada = sorted(list(p_dict.keys()))
        
        with st.form("form_of"):
            p_sel = st.selectbox("Producto en oferta", lista_prods_ordenada)
            precio = st.number_input("Precio Oferta", min_value=0.0, format="%.2f")
            vence = st.date_input("¿Cuándo termina la promoción?", format="DD/MM/YYYY")
            if st.form_submit_button("Publicar Oferta"):
                try:
                    supabase.table("ofertas").insert({"id_producto": p_dict[p_sel], "id_super": super_dict[super_sel], "id_sucursal": suc_dict[suc_sel], "precio_oferta": precio, "fecha_fin": str(vence)}).execute()
                    st.success("¡Oferta publicada exitosamente!"); st.balloons()
                except Exception as e: st.error(f"Error: {e}")
