import streamlit as st
import pandas as pd

# 1. RECUPERAR CONEXIÓN COMPARTIDA
if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("📊 Panel de Consultas Estadísticas")

# 2. CARGAR DICCIONARIOS MAESTROS COMPLETOS (Para evitar exclusiones)
try:
    res_cat = supabase.table("categorias").select("*").order("id_cat").execute()
    c_inv = {c['id_cat']: c['nombre'] for c in res_cat.data} if res_cat.data else {}
    
    # Consultamos TODOS los productos del catálogo maestro para capturar el 100% de las marcas
    res_todos_p = supabase.table("productos").select("marca").execute()
    lista_todas_marcas = sorted(list(set([p['marca'] for p in res_todos_p.data if p.get('marca') and p['marca'].strip() != ""]))) if res_todos_p.data else []
except:
    c_inv = {}
    lista_todas_marcas = []

# 3. EXTRAER Y PROCESAR DATOS DE OFERTAS
try:
    res = supabase.table("ofertas").select("""
        precio_oferta, fecha_inicio, fecha_fin, 
        productos(nombre, marca, id_cat), 
        supermercados(nombre_supermercado), 
        sucursales(nombre_sucursal)
    """).execute()
    
    lista_limpia = []
    if res.data:
        for o in res.data:
            prod = o.get("productos") or {}
            sup = o.get("supermercados") or {}
            suc = o.get("sucursales") or {}
            
            fila = {
                "nombre": prod.get("nombre", "N/A"),
                "marca": prod.get("marca", "Sin Marca"),
                "categoria": c_inv.get(prod.get("id_cat"), "Sin Categoría"),
                "supermercado": sup.get("nombre_supermercado", "N/A"),
                "sucursal": suc.get("nombre_sucursal") or "Todas",
                "precio_oferta": float(o.get("precio_oferta", 0)),
                "fecha_inicio": o.get("fecha_inicio", "N/A"),
                "fecha_fin": o.get("fecha_fin", "N/A")
            }
            lista_limpia.append(fila)
    df = pd.DataFrame(lista_limpia)
except:
    df = pd.DataFrame()

# 4. INTERFAZ DE CONSULTA BLINDADA (TEXTO PURO, SIN GRÁFICOS)
if not df.empty:
    rep = st.sidebar.radio("Filtrar Análisis por:", ["Por Producto", "Por Marca", "Por Supermercado", "Por Categoría"])
    
    if rep == "Por Producto":
        lista_opciones = sorted(list(df['nombre'].unique()))
        sel = st.selectbox("Selecciona un Producto para ver su historial de ofertas:", lista_opciones)
        df_v = df[df['nombre'] == sel]
        
    elif rep == "Por Marca":
        # Usamos la lista maestra global de marcas para que salgan las >5 registradas, no solo las que tienen ofertas
        sel = st.selectbox("Selecciona una Marca registrada para auditar:", lista_todas_marcas)
        df_v = df[df['marca'] == sel]
        
    elif rep == "Por Supermercado":
        lista_opciones = sorted(list(df['supermercado'].unique()))
        sel = st.selectbox("Selecciona un Supermercado:", lista_opciones)
        df_v = df[df['supermercado'] == sel]
        
    elif rep == "Por Categoría":
        lista_opciones = sorted(list(df['categoria'].unique()))
        sel = st.selectbox("Selecciona una Categoría:", lista_opciones)
        df_v = df[df['categoria'] == sel]

    st.subheader(f"🔍 Resultados de búsqueda analítica para: {sel}")
    
    if not df_v.empty:
        # Formatear la tabla final de manera estética
        df_mostrar = df_v.copy()
        df_mostrar['precio_oferta'] = df_mostrar['precio_oferta'].map(lambda x: f"${x:.2f}")
        
        # Invertimos el orden de las fechas si es necesario o aplicamos formato local si se requiere
        st.dataframe(
            df_mostrar[['nombre', 'marca', 'categoria', 'supermercado', 'sucursal', 'precio_oferta', 'fecha_inicio', 'fecha_fin']], 
            use_container_width=True
        )
    else:
        st.warning(f"El elemento '{sel}' está registrado en el catálogo, pero actualmente no tiene ninguna oferta asociada en el mercado.")
else:
    st.info("No hay ofertas registradas en el sistema. Publica una oferta desde el menú correspondiente para activar las consultas.")
