from nicegui import ui
import iconocentral  # Tu conexión a Supabase

# Arreglo de control acotado en la memoria RAM
nombres_existentes = ['Aceite', 'Harina', 'Arroz', 'Mantequilla']

ui.label('📦 Administración de Productos - Motor POS Web Pro')

with ui.row():
    # El Combobox Real en una sola caja que acepta texto nuevo al dar TAB
    nombre_combo = ui.select(
        options=nombres_existentes, 
        with_input=True, 
        label='Nombre del Producto*'
    ).props('new-value-mode="add" clearable')  # <- Esta propiedad de Quasar hace la magia

    marca_input = ui.input(label='Marca del Producto')

with ui.row():
    tamano = ui.number(label='Tamaño / Peso', value=None, placeholder='Ej: 500')
    unidad = ui.select(options=['gr', 'kg', 'ml', 'lt', 'unidad'], value='gr')

# El botón recolecta el valor congelado del combo, sea viejo o nuevo
ui.button('🚀 Guardar Producto', on_click=lambda: ui.notify(f'Guardando: {nombre_combo.value}'))

ui.run()
