import streamlit as st
import pandas as pd

if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("🏪 Administración de Tiendas")

t1, t2 = st.tabs(["🏢 Cadenas (Supermercados)", "📍 Sucursales"])
try:
    supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
    df_s = pd.DataFrame(supers.data) if supers.data else pd.DataFrame()
    sucs = supabase.table("sucursales").select("*, supermercados(nombre_supermercado)").execute()
    df_suc = pd.json_normalize(sucs.data) if sucs.data else pd.DataFrame()
except: df_s, df_suc = pd.DataFrame(), pd.DataFrame()

with t1:
    st.subheader("Gestión de Cadenas")
    sub_t1, sub_t2 = st.columns(2)
    with sub_t1:
        with st.form("super_add", clear_on_submit=True):
            nom = st.text_input("Nombre de la Cadena")
            if st.form_submit_button("Guardar Cadena"):
                if nom: supabase.table("supermercados").insert({"nombre_supermercado": nom}).execute(); st.success("Registrado."); st.rerun()
    with sub_t2:
        if not df_s.empty:
            super_map = {r['nombre_supermercado']: r for r in supers.data}
            sel_super = st.selectbox("Modificar Cadena:", list(super_map.keys()))
            s_data = super_map[sel_super]
            with st.form("super_edit"):
                enom = st.text_input("Editar Nombre", value=s_data['nombre_supermercado'])
                b1, b2 = st.columns(2)
                if b1.form_submit_button("💾 Guardar"): supabase.table("supermercados").update({"nombre_supermercado": enom}).eq("id_super", s_data['id_super']).execute(); st.success("Actualizado."); st.rerun()
                if b2.form_submit_button("🗑️ Eliminar"): supabase.table("supermercados").delete().eq("id_super", s_data['id_super']).execute(); st.warning("Eliminado."); st.rerun()

with t2:
    if not df_s.empty:
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        c_add, c_edit = st.columns(2)
        with c_add:
            with st.form("suc_add", clear_on_submit=True):
                s_sel = st.selectbox("Cadena perteneciente:", list(super_dict.keys()))
                n_suc = st.text_input("Nombre de Sucursal")
                ciu = st.text_input("Ciudad")
                if st.form_submit_button("Guardar Sucursal"):
                    if n_suc and ciu: supabase.table("sucursales").insert({"id_super": super_dict[s_sel], "nombre_sucursal": n_suc, "ciudad": ciu}).execute(); st.success("Guardado."); st.rerun()
        with c_edit:
            if not df_suc.empty:
                suc_map = {f"{r['supermercados.nombre_supermercado']} - {r['nombre_sucursal']}": r for _, r in df_suc.iterrows()}
                sel_suc_edit = st.selectbox("Selecciona Sucursal:", list(suc_map.keys()))
                suc_data = suc_map[sel_suc_edit]
                with st.form("suc_edit_form"):
                    esuc_name = st.text_input("Nombre", value=suc_data['nombre_sucursal'] if 'nombre_sucursal' in suc_data else "")
                    eciu = st.text_input("Ciudad", value=suc_data['ciudad'] if 'ciudad' in suc_data else "")
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Actualizar"): supabase.table("sucursales").update({"nombre_sucursal": esuc_name, "ciudad": eciu}).eq("id_sucursal", suc_data['id_sucursal']).execute(); st.success("Actualizado."); st.rerun()
                    if b2.form_submit_button("🗑️ Borrar"): supabase.table("sucursales").delete().eq("id_sucursal", suc_data['id_sucursal']).execute(); st.warning("Borrado."); st.rerun()
