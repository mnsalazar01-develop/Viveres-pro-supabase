import streamlit as st
import pandas as pd

# 1. RECUPERAR CONEXIÓN COMPARTIDA
if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]

st.title("📁 Estructura de Clasificación Jerárquica")

# 2. CARGAR DATOS EN TIEMPO REAL
try:
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    res_sc = supabase.table("subcategorias").select("*, categorias(nombre, id_cat)").execute()
    df_sc = pd.json_normalize(res_sc.data) if res_sc.data else pd.DataFrame()
except:
    df_c, df_sc, cat_dict, lista_cat = pd.DataFrame(), pd.DataFrame(), {}, []

# 3. INTERFAZ ORGANIZADA POR PESTAÑAS HOMOLOGADAS
t1, t2 = st.tabs(["📁 Categorías Principales", "🌿 Subcategorías (Hijos)"])

# --- TABLA DE CATEGORÍAS ---
with t1:
    st.subheader("Módulo de Categorías")
    tc1, tc2, tc3 = st.tabs(["📋 Ver Categorías", "➕ Nueva Categoría", "✏️ Editar/Borrar"])
    
    with tc1:
        if not df_c.empty:
            st.write("Listado maestro ordenado por número de Categoría:")
            st.dataframe(df_c[['id_cat', 'nombre']], use_container_width=True)
        else:
            st.info("No hay categorías principales registradas.")
            
    with tc2:
        n_cat = st.text_input("Nombre de la Nueva Categoría Principal", key="add_cat_input")
        if st.button("🚀 Guardar Categoría", type="primary"):
            if n_cat:
                try:
                    supabase.table("categorias").insert({"nombre": n_cat}).execute()
                    st.success(f"Categoría '{n_cat}' registrada con éxito.")
                    st.rerun()
                except Exception as e: st.error(f"Error al guardar: {e}")
            else: st.warning("El nombre es obligatorio.")
            
    with tc3:
        if not df_c.empty:
            c_map = {c['nombre']: c for c in res_c.data}
            s_c = st.selectbox("Selecciona la Categoría Principal a gestionar:", list(c_map.keys()), key="s_c_e")
            c_d = c_map[s_c]
            un_c = st.text_input("Editar Nombre de la Categoría", value=c_d['nombre'], key="u_c_n")
            
            bc1, bc2 = st.columns(2)
            if bc1.button("💾 Actualizar Nombre de Categoría"):
                try:
                    supabase.table("categorias").update({"nombre": un_c}).eq("id_cat", c_d['id_cat']).execute()
                    st.success("Categoría actualizada."); st.rerun()
                except Exception as e: st.error(f"Error: {e}")
                
            if bc2.button("🗑️ Eliminar Categoría Definitivamente"):
                try:
                    supabase.table("categorias").delete().eq("id_cat", c_d['id_cat']).execute()
                    st.warning("Categoría eliminada del sistema."); st.rerun()
                except Exception as e: st.error(f"No se puede eliminar. Verifica si tiene subcategorías vinculadas: {e}")

# --- TABLA DE SUBCATEGORÍAS ---
with t2:
    st.subheader("Módulo de Subcategorías")
    tsc1, tsc2, tsc3 = st.tabs(["📋 Ver Subcategorías", "➕ Nueva Subcategoría", "✏️ Editar/Borrar"])
    
    with tsc1:
        if not df_sc.empty:
            df_ord = df_sc.sort_values(by='categorias.id_cat')
            st.dataframe(
                df_ord.rename(columns={'nombre': 'Subcategoría', 'categorias.nombre': 'Categoría Padre', 'categorias.id_cat': 'N° Cat'})[['N° Cat', 'Categoría Padre', 'Subcategoría']], 
                use_container_width=True
            )
        else:
            st.info("No hay subcategorías registradas aún.")
            
    with tsc2:
        if lista_cat:
            c_padre = st.selectbox("Selecciona la Categoría Padre (Orden Numérico):", lista_cat, key="sc_p")
            n_sub = st.text_input("Nombre de la Nueva Subcategoría", key="add_sub_input")
            if st.button("🚀 Guardar Subcategoría", type="primary"):
                if n_sub:
                    try:
                        supabase.table("subcategorias").insert({"nombre": n_sub, "id_cat": cat_dict[c_padre]}).execute()
                        st.success(f"Subcategoría '{n_sub}' guardada con éxito.")
                        st.rerun()
                    except Exception as e: st.error(f"Error al guardar: {e}")
                else: st.warning("El nombre de la subcategoría es obligatorio.")
        else:
            st.warning("Debes crear al menos una Categoría Principal antes de ingresar subcategorías.")
            
    with tsc3:
        if not df_sc.empty:
            sc_map = {f"[{r['categorias.nombre']}] ➔ {r['nombre']}": r for _, r in df_sc.iterrows()}
            s_sc = st.selectbox("Selecciona la Subcategoría a gestionar:", list(sc_map.keys()), key="s_sc_e")
            sc_d = sc_map[s_sc]
            
            un_sc = st.text_input("Editar Nombre de la Subcategoría", value=sc_d['nombre'], key="u_sc_n")
            
            bsc1, bsc2 = st.columns(2)
            # CORRECCIÓN DE LA LÍNEA DE ACTUALIZACIÓN (Asignación explícita del ID)
            if bsc1.button("💾 Actualizar Nombre de Subcategoría"):
                try:
                    supabase.table("subcategorias").update({"nombre": un_sc}).eq("id_subcat", sc_d['id_subcat']).execute()
                    st.success("Subcategoría actualizada exitosamente."); st.rerun()
                except Exception as e: st.error(f"Error al actualizar: {e}")
                
            # CORRECCIÓN DE LA LÍNEA DE BORRADO (Asignación explícita del ID)
            if bsc2.button("🗑️ Eliminar Subcategoría Definitivamente"):
                try:
                    supabase.table("subcategorias").delete().eq("id_subcat", sc_d['id_subcat']).execute()
                    st.warning("Subcategoría eliminada."); st.rerun()
                except Exception as e: st.error(f"No se pudo eliminar: {e}")
