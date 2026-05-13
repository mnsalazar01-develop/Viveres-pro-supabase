import streamlit as st
import pandas as pd

# 1. RECUPERAR CONEXIÓN COMPARTIDA
if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]

st.title("📊 Panel de Consultas Estadísticas")

# 2. CARGAR DICCIONARIOS MAESTROS
try:
    res_cat = supabase.table("categorias").select("*").order("id_cat").execute()
    c_inv = {c['id_cat']: c['nombre'] for c in res_cat.data} if res_cat.data else {}
except:
    c_inv = {}

# 3. EXTRAER Y PROCESAR DATOS DE MERCADO
try:
    res = supabase.table("ofertas").select("""
        precio_oferta, fecha_inicio, fecha_fin, 
        productos(nombre, marca, id_cat), 
        supermercados(nombre_supermercado), 
        sucursales(nombre_sucursal)
    """).execute()
    df = pd.json_normalize(res.data) if res.data else pd.DataFrame()
except:
    df = pd.DataFrame()

if not df.empty:
    # Formatear nombres de columnas para que sean limpios en pantalla
    df['productos.categoria'] = df['productos.id_cat'].map(c_inv).fillna("Sin Categoría")
    cols_f = {
        'productos.nombre': 'nombre', 
        'productos.marca': 'marca', 
        'supermercados.nombre_supermercado': 'supermercado', 
        'sucursales.nombre_sucursal': 'sucursal', 
        'precio_oferta': 'precio_oferta', 
        'fecha_inicio': 'fecha_inicio', 
        'fecha_fin': 'fecha_fin', 
        'productos.categoria': 'categoria'
    }
    df = df.rename(columns=cols_f)
    
    # Rellenar datos vacíos de forma segura
    for col in cols_f.values(): 
        if col not in df.columns: 
            df[col] = "N/A"
        df[col] = df[col].fillna("Todas") if col == "sucursal" else df[col].fillna("N/A")

    # Menu de Reportes interactivo en el panel izquierdo (barra lateral interna)
    rep = st.sidebar.radio("Filtrar Análisis por:", ["Por Producto", "Por Marca", "Por Supermercado", "Por Categoría"])
    
    # 4. LÓGICA DE BÚSQUEDA INTERACTIVA POR CRITERIO
    if rep == "Por Producto":
        sel = st.selectbox("Selecciona un Producto para ver dónde está en oferta:", sorted(list(df['nombre'].unique())))
        df_v = df[df['nombre'] == sel]
    elif rep == "Por Marca":
        sel = st.selectbox("Selecciona una Marca:", sorted(list(df['marca'].unique())))
        df_v = df[df['marca'] == sel]
    elif rep == "Por Supermercado":
        sel = st.selectbox("Selecciona un Supermercado:", sorted(list(df['supermercado'].unique())))
        df_v = df[df['supermercado'] == sel]
    elif rep == "Por Categoría":
        sel = st.selectbox("Selecciona una Categoría:", sorted(list(df['categoria'].unique())))
        df_v = df[df['categoria'] == sel]

    st.subheader(f"🔍 Resultados de búsqueda para: {sel}")
    
    # Tabla final limpia para el usuario con formato de precios de dos decimales
    df_v = df_v.copy()
    df_v['precio_oferta'] = df_v['precio_oferta'].map(lambda x: f"${x:.2f}")
    
    st.dataframe(
        df_v[['nombre', 'marca', 'categoria', 'supermercado', 'sucursal', 'precio_oferta', 'fecha_inicio', 'fecha_fin']], 
        use_container_width=True
    )
else:
    st.info("No hay ofertas registradas actualmente en el sistema para generar consultas.")
