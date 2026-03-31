import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Constantes de conversión
PT_TO_MM = 25.4 / 72.0
MM_TO_PT = 72.0 / 25.4

st.set_page_config(page_title="Herramienta de Reescalado PDF", layout="wide")

# ==========================================
# Funciones de Procesamiento
# ==========================================
def convert_rect_to_mm(rect):
    """Convierte un objeto fitz.Rect de puntos a milímetros y formatea la salida."""
    if rect.is_empty:
        return "Vacío/No definido"
    return f"Ancho: {rect.width * PT_TO_MM:.2f} mm | Alto: {rect.height * PT_TO_MM:.2f} mm"

def process_single_page_preview(doc, page_num, scale_axis, target_mm, margins_mm):
    """Procesa una sola página para la previsualización y devuelve el documento temporal."""
    page = doc[page_num]
    w_mm = page.rect.width * PT_TO_MM
    h_mm = page.rect.height * PT_TO_MM

    # Calcular factor de escala
    scale = 1.0
    if target_mm > 0:
        scale = target_mm / w_mm if scale_axis == "Ancho" else target_mm / h_mm

    scaled_w_pt = page.rect.width * scale
    scaled_h_pt = page.rect.height * scale

    # Márgenes en puntos
    ml, mt, mr, mb = [m * MM_TO_PT for m in margins_mm]

    final_w_pt = scaled_w_pt + ml + mr
    final_h_pt = scaled_h_pt + mt + mb

    temp_doc = fitz.open()
    new_page = temp_doc.new_page(width=final_w_pt, height=final_h_pt)
    target_rect = fitz.Rect(ml, mt, ml + scaled_w_pt, mt + scaled_h_pt)
    new_page.show_pdf_page(target_rect, doc, page_num)
    
    return temp_doc

def process_full_pdf(doc, scale_axis, target_mm, margins_mm):
    """Procesa todo el documento para la descarga final."""
    out_doc = fitz.open()
    for page_num in range(len(doc)):
        page = doc[page_num]
        w_mm = page.rect.width * PT_TO_MM
        h_mm = page.rect.height * PT_TO_MM

        scale = 1.0
        if target_mm > 0:
            scale = target_mm / w_mm if scale_axis == "Ancho" else target_mm / h_mm

        scaled_w_pt = page.rect.width * scale
        scaled_h_pt = page.rect.height * scale

        ml, mt, mr, mb = [m * MM_TO_PT for m in margins_mm]

        final_w_pt = scaled_w_pt + ml + mr
        final_h_pt = scaled_h_pt + mt + mb

        new_page = out_doc.new_page(width=final_w_pt, height=final_h_pt)
        target_rect = fitz.Rect(ml, mt, ml + scaled_w_pt, mt + scaled_h_pt)
        new_page.show_pdf_page(target_rect, doc, page_num)
        
    return out_doc

# ==========================================
# Interfaz de Usuario (UI) y Estado
# ==========================================
st.title("📄 Herramienta de Reescalado y Márgenes para PDF")

# Llave dinámica para poder resetear el uploader programáticamente
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

uploaded_file = st.file_uploader("Sube tu archivo PDF", type=["pdf"], key=f"pdf_uploader_{st.session_state.uploader_key}")

if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    num_pages = len(doc)
    
    # --- INICIALIZACIÓN SEGURA DE VARIABLES ---
    if "widget_ml" not in st.session_state:
        st.session_state.widget_axis = "Ancho"
        st.session_state.widget_target = float(doc[0].rect.width * PT_TO_MM)
        st.session_state.widget_mt = 0.0
        st.session_state.widget_ml = 0.0
        st.session_state.widget_mr = 0.0
        st.session_state.widget_mb = 0.0
        st.session_state.widget_suffix = "_reescalado"
        st.session_state.last_uploaded = ""
    
    # --- GESTIÓN DE ESTADO Y PRESETS ---
    if uploaded_file.name != st.session_state.get("last_uploaded", ""):
        st.session_state.last_uploaded = uploaded_file.name
        st.session_state.pdf_ready = False 
        
        if st.session_state.get("preset_active", False):
            st.session_state.widget_axis = st.session_state.preset_axis
            st.session_state.widget_target = st.session_state.preset_target
            st.session_state.widget_mt = st.session_state.preset_mt
            st.session_state.widget_ml = st.session_state.preset_ml
            st.session_state.widget_mr = st.session_state.preset_mr
            st.session_state.widget_mb = st.session_state.preset_mb
            st.session_state.widget_suffix = st.session_state.preset_suffix
        else:
            st.session_state.widget_axis = "Ancho"
            st.session_state.widget_target = float(doc[0].rect.width * PT_TO_MM)
            st.session_state.widget_mt = 0.0
            st.session_state.widget_ml = 0.0
            st.session_state.widget_mr = 0.0
            st.session_state.widget_mb = 0.0
            st.session_state.widget_suffix = "_reescalado"

    # ==========================================
    # SIDEBAR (SIEMPRE VISIBLE)
    # ==========================================
    first_page_rect = doc[0].rect
    consistent_sizes = all(abs(doc[i].rect.width - first_page_rect.width) < 1 and 
                           abs(doc[i].rect.height - first_page_rect.height) < 1 
                           for i in range(1, num_pages))
    
    st.sidebar.header("📊 Información del PDF")
    st.sidebar.write(f"**Total de páginas:** {num_pages}")
    
    if consistent_sizes:
        st.sidebar.success("✅ Todas las páginas miden lo mismo.")
    else:
        st.sidebar.warning("⚠️ Las páginas tienen tamaños diferentes.")

    st.sidebar.divider()
    
    # --- SISTEMA DE PRESETS ---
    st.sidebar.header("💾 Ajustes Preestablecidos")
    if st.sidebar.button("Guardar Configuración Actual", use_container_width=True):
        st.session_state.preset_active = True
        st.session_state.preset_axis = st.session_state.widget_axis
        st.session_state.preset_target = st.session_state.widget_target
        st.session_state.preset_mt = st.session_state.widget_mt
        st.session_state.preset_ml = st.session_state.widget_ml
        st.session_state.preset_mr = st.session_state.widget_mr
        st.session_state.preset_mb = st.session_state.widget_mb
        st.session_state.preset_suffix = st.session_state.widget_suffix
        st.sidebar.success("✅ Preset guardado.")
        
    if st.session_state.get("preset_active", False):
        st.sidebar.info("📌 Preset activo para futuros archivos.")
        if st.sidebar.button("Limpiar Preset", use_container_width=True):
            st.session_state.preset_active = False
            st.rerun()

    st.sidebar.divider()

    # --- BARRA DE EXPORTACIÓN (NATIVA) ---
    st.sidebar.header("🚀 Exportar PDF")
    
    st.sidebar.text_input("Sufijo del archivo:", key="widget_suffix")
    original_name = uploaded_file.name.rsplit('.', 1)[0]
    final_filename = f"{original_name}{st.session_state.widget_suffix}.pdf"
    
    current_margins = (
        st.session_state.get("widget_ml", 0.0), 
        st.session_state.get("widget_mt", 0.0), 
        st.session_state.get("widget_mr", 0.0), 
        st.session_state.get("widget_mb", 0.0)
    )
    
    if st.sidebar.button("⚙️ Procesar PDF", use_container_width=True):
        with st.spinner("Preparando documento..."):
            final_pdf = process_full_pdf(
                doc, 
                st.session_state.get("widget_axis", "Ancho"), 
                st.session_state.get("widget_target", 0.0), 
                current_margins
            )
            st.session_state.pdf_bytes = final_pdf.write()
            final_pdf.close()
            st.session_state.pdf_ready = True 
            
    if st.session_state.get("pdf_ready", False):
        st.sidebar.download_button(
            label="⬇️ Descargar PDF Final",
            data=st.session_state.pdf_bytes,
            file_name=final_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    else:
        st.sidebar.button("⬇️ Descargar PDF Final", disabled=True, use_container_width=True)

    st.sidebar.divider()

    # --- PURGAR DATOS ---
    st.sidebar.header("🗑️ Limpieza")
    if st.sidebar.button("Eliminar PDF Actual", use_container_width=True):
        st.session_state.confirm_delete = True
        
    if st.session_state.get("confirm_delete", False):
        st.sidebar.warning("¿Estás seguro? Se borrará todo rastro de este PDF.")
        col_del1, col_del2 = st.sidebar.columns(2)
        
        if col_del1.button("✔️ Sí, eliminar", use_container_width=True):
            # Incrementar la llave fuerza la recarga limpia del uploader
            st.session_state.uploader_key += 1
            st.session_state.confirm_delete = False
            st.session_state.pdf_ready = False
            st.session_state.last_uploaded = ""
            if "pdf_bytes" in st.session_state:
                del st.session_state["pdf_bytes"]
            st.rerun()
            
        if col_del2.button("✖️ Cancelar", use_container_width=True):
            st.session_state.confirm_delete = False
            st.rerun()

    # ==========================================
    # ÁREA PRINCIPAL (CONTROLES Y PREVIEW)
    # ==========================================
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ Configuración")
        
        preview_page = st.number_input("Página a analizar", min_value=1, max_value=num_pages, value=1) - 1
        page = doc[preview_page]
        
        with st.expander("Ver Medidas Actuales (mm)"):
            st.write(f"- **MediaBox:** {convert_rect_to_mm(page.mediabox)}")
            st.write(f"- **CropBox:** {convert_rect_to_mm(page.cropbox)}")
            st.write(f"- **BleedBox:** {convert_rect_to_mm(page.bleedbox)}")
            st.write(f"- **TrimBox:** {convert_rect_to_mm(page.trimbox)}")
            st.write(f"- **ArtBox:** {convert_rect_to_mm(page.artbox)}")
        
        st.markdown("### Opciones de Reescalado")
        st.radio("Escalar en base a:", ["Ancho", "Alto"], key="widget_axis")
        st.number_input(f"Nueva medida deseada en mm:", min_value=0.0, step=1.0, key="widget_target")
        
        st.markdown("### Espacio en Blanco (mm)")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.number_input("Arriba", min_value=0.0, step=1.0, key="widget_mt")
            st.number_input("Izquierda", min_value=0.0, step=1.0, key="widget_ml")
        with col_m2:
            st.number_input("Abajo", min_value=0.0, step=1.0, key="widget_mb")
            st.number_input("Derecha", min_value=0.0, step=1.0, key="widget_mr")

    with col2:
        st.subheader("👁️ Previsualización")
        
        col_v1, col_v2 = st.columns([2, 1])
        with col_v1:
            prev_ppi = st.slider("Calidad de render (PPI)", min_value=36, max_value=300, value=100, step=10)
        with col_v2:
            st.write("") 
            st.write("")
            show_grid = st.checkbox("Mostrar cuadrícula", value=True)
        
        rt_axis = st.session_state.widget_axis
        rt_target = st.session_state.widget_target
        rt_margins = (st.session_state.widget_ml, st.session_state.widget_mt, st.session_state.widget_mr, st.session_state.widget_mb)
        
        temp_doc = process_single_page_preview(doc, preview_page, rt_axis, rt_target, rt_margins)
        
        pix = temp_doc[0].get_pixmap(dpi=prev_ppi)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        
        final_w_mm = temp_doc[0].rect.width * PT_TO_MM
        final_h_mm = temp_doc[0].rect.height * PT_TO_MM
        st.info(f"**Medida final de esta página:** {final_w_mm:.2f} mm de Ancho x {final_h_mm:.2f} mm de Alto")
        
        fig, ax = plt.subplots(figsize=(6, 6 * (final_h_mm / final_w_mm)))
        ax.imshow(image, extent=[0, final_w_mm, final_h_mm, 0])
        
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        
        ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(1))
        
        ax.tick_params(axis='both', which='major', labelsize=8, colors='#333333', length=6, width=1.2)
        ax.tick_params(axis='both', which='minor', length=3, width=0.8, colors='#999999')
        
        if show_grid:
            ax.grid(which='major', color='#555555', linestyle='-', linewidth=0.6, alpha=0.4)
            ax.grid(which='minor', color='#aaaaaa', linestyle='-', linewidth=0.3, alpha=0.15)
        
        for spine in ax.spines.values():
            spine.set_edgecolor('#cccccc')

        st.pyplot(fig)
        temp_doc.close()
