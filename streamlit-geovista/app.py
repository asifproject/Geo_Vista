import copy
import json
import streamlit as st
import streamlit_image_select
from pathlib import Path

from utils import (
    st_get_osm_geometries,
    st_plot_all,
    get_colors_from_style,
    plt_to_svg,
    slugify,
)
from prettymapp.geo import get_aoi
from prettymapp.settings import STYLES
from geopy.geocoders import Nominatim

st.set_page_config(
    page_title="GeoVista_Running",
    page_icon="🖼️",
    initial_sidebar_state="collapsed"
)

st.markdown("# GeoVista_Running")

_HERE = Path(__file__).resolve().parent

with (_HERE / "examples.json").open("r", encoding="utf8") as f:
    EXAMPLES = json.load(f)

# ---------------- SESSION INIT ----------------
if "initialized" not in st.session_state:
    st.session_state.update(EXAMPLES["Mecca"])
    lc_class_colors = get_colors_from_style("Peach")
    st.session_state.lc_classes = list(lc_class_colors.keys())
    st.session_state.update(lc_class_colors)
    st.session_state["previous_style"] = "Peach"
    st.session_state["previous_example_index"] = 0
    st.session_state["initialized"] = True

# ---------------- EXAMPLES ----------------
example_image_pattern = str(_HERE / "example_prints" / "{}_small.png")
example_image_fp = [
    example_image_pattern.format(name.lower()) for name in list(EXAMPLES.keys())[:4]
]

index_selected = streamlit_image_select.image_select(
    "",
    images=example_image_fp,
    captions=list(EXAMPLES.keys())[:4],
    index=0,
    return_value="index",
)

if index_selected != st.session_state["previous_example_index"]:
    name_selected = list(EXAMPLES.keys())[index_selected]
    st.session_state.update(EXAMPLES[name_selected].copy())
    st.session_state["previous_example_index"] = index_selected

st.write("")

# ---------------- FORM ----------------
with st.form("map_form"):

    col1, col2, col3 = st.columns([3, 1, 1])

    address = col1.text_input("Location address", value=st.session_state.get("address", ""))

    radius = col2.slider("Radius (meter)", 100, 1500, value=st.session_state.get("radius", 1100))

    style = col3.selectbox("Color theme", options=list(STYLES.keys()))

    # -------- STYLE SETTINGS --------
    expander = st.expander("Customize map style")

    col1style, col2style, _, col3style = expander.columns([2, 2, 0.1, 1])

    shape = col1style.radio("Map Shape", ["circle", "rectangle", "square"])

    bg_shape = col1style.radio("Background Shape", ["rectangle", "circle", "square"])

    bg_color = col1style.color_picker("Background Color", "#ffffff")

    bg_buffer = col1style.slider("Background Size", 0, 50, 4)

    col1style.markdown("---")

    contour_color = col1style.color_picker("Map contour color", "#000000")

    contour_width = col1style.slider("Map contour width", 0, 30, 2)

    name_on = col2style.checkbox("Display title", True)

    custom_title = col2style.text_input("Custom title (optional)", "")

    font_size = col2style.slider("Title font size", 1, 50, 26)

    font_color = col2style.color_picker("Title font color", "#000000")

    text_x = col2style.slider("Title left/right", -100, 100, 0)

    text_y = col2style.slider("Title top/bottom", -100, 100, -46)

    text_rotation = col2style.slider("Title rotation", -90, 90, 0)

    submit = st.form_submit_button("Generate Map")

# ---------------- MAP GENERATION ----------------
if submit:

    with st.spinner("Creating map... (may take up to a minute)"):

        # 🔥 FIX: square → rectangle for backend
        rectangular = shape != "circle"

        geolocator = Nominatim(user_agent="geomap_app")

        try:
            location = geolocator.geocode(address)

            if location is None:
                st.error("❌ Location not found. Try: Vellore, Tamil Nadu, India")
                st.stop()

            lat, lon = location.latitude, location.longitude

            st.success(f"📍 Coordinates: {lat}, {lon}")

            aoi = get_aoi(
                address=f"{lat}, {lon}",
                radius=radius,
                rectangular=rectangular
            )

        except Exception as e:
            st.error(f"❌ Geocoding failed: {str(e)}")
            st.stop()

        # -------- DRAW SETTINGS --------
        draw_settings = copy.deepcopy(STYLES[style])

        for lc_class in st.session_state.lc_classes:
            if lc_class in draw_settings:
                pass

        df = st_get_osm_geometries(aoi=aoi)

        config = {
            "aoi_bounds": aoi.bounds,
            "draw_settings": draw_settings,
            "name_on": name_on,
            "name": address if custom_title == "" else custom_title,
            "font_size": font_size,
            "font_color": font_color,
            "text_x": text_x,
            "text_y": text_y,
            "text_rotation": text_rotation,
            "shape": "rectangle" if shape == "square" else shape,
            "contour_width": contour_width,
            "contour_color": contour_color,
            "bg_shape": bg_shape,
            "bg_buffer": bg_buffer,
            "bg_color": bg_color,
        }

        fig = st_plot_all(_df=df, **config)

        st.pyplot(fig, pad_inches=0, bbox_inches="tight", transparent=True, dpi=300)

# ---------------- EXPORT ----------------
if "fig" in locals():

    st.markdown("---")

    with st.expander("Export image"):

        img_format = st.selectbox("File type", ["png", "svg"])

        fname_base = slugify(address) if str(address).strip() else "prettymapp"

        def _make_download_data():
            if img_format == "svg":
                return plt_to_svg(fig)

            import io
            buf = io.BytesIO()
            fig.savefig(buf, format=img_format, dpi=300)
            buf.seek(0)
            return buf.getvalue()

        st.download_button(
            label="Download",
            data=_make_download_data,
            file_name=f"{fname_base}.{img_format}",
        )