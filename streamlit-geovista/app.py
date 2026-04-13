import copy
import json
import io
import streamlit as st
from streamlit_image_select import image_select
from pathlib import Path

from utils import (
    st_get_osm_geometries,
    st_plot_all,
    get_colors_from_style,
    plt_to_svg,
    slugify,
)
from prettymapp.geo import GeoCodingError, get_aoi
from prettymapp.settings import STYLES


# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="GeoVista_Running",
    page_icon="🖼️",
    initial_sidebar_state="collapsed"
)

st.markdown("# GeoVista_Running")


# ---------------- LOAD EXAMPLES ----------------
_HERE = Path(__file__).resolve().parent

with (_HERE / "examples.json").open("r", encoding="utf8") as f:
    EXAMPLES = json.load(f)


# ---------------- SESSION INIT ----------------
if "initialized" not in st.session_state:

    default_example = list(EXAMPLES.keys())[0]

    st.session_state.update(EXAMPLES[default_example])

    default_style = EXAMPLES[default_example].get("style") or "Peach"

    if default_style not in STYLES:
        default_style = "Peach"

    lc_class_colors = get_colors_from_style(default_style)

    st.session_state.lc_classes = list(lc_class_colors.keys())
    st.session_state.update(lc_class_colors)

    st.session_state["previous_style"] = default_style
    st.session_state["previous_example_index"] = 0
    st.session_state["initialized"] = True


# ---------------- EXAMPLE IMAGES ----------------
example_image_pattern = str(_HERE / "example_prints" / "{}_small.png")

example_image_fp = [
    example_image_pattern.format(name.lower())
    for name in list(EXAMPLES.keys())[:4]
]

index_selected = image_select(
    "",
    images=example_image_fp,
    captions=list(EXAMPLES.keys())[:4],
    index=st.session_state.get("previous_example_index", 0),
    return_value="index",
)

if index_selected != st.session_state["previous_example_index"]:
    name_selected = list(EXAMPLES.keys())[index_selected]

    st.session_state.update(EXAMPLES[name_selected].copy())

    selected_style = EXAMPLES[name_selected].get("style") or "Peach"

    if selected_style not in STYLES:
        selected_style = "Peach"

    st.session_state.update(get_colors_from_style(selected_style))

    st.session_state["previous_style"] = selected_style
    st.session_state["previous_example_index"] = index_selected


st.write("")


# ---------------- FORM ----------------
with st.form("map_form"):

    col1, col2, col3 = st.columns([3, 1, 1])

    address = col1.text_input(
        "Location address",
        value=st.session_state.get("address", "")
    )

    radius = col2.slider(
        "Radius (meter)",
        100,
        1500,
        value=st.session_state.get("radius", 1000)
    )

    style_options = list(STYLES.keys())

    current_style = st.session_state.get("previous_style", "Peach")

    if current_style not in style_options:
        current_style = "Peach"

    style = col3.selectbox(
        "Color theme",
        options=style_options,
        index=style_options.index(current_style)
    )


    # ---------------- CUSTOMIZE STYLE ----------------
    expander = st.expander("Customize map style")

    col1style, col2style, _, col3style = expander.columns([2, 2, 0.1, 1])

    shape = col1style.radio(
        "Map Shape",
        ["circle", "rectangle"],
        index=0 if st.session_state.get("shape", "circle") == "circle" else 1
    )

    bg_shape = col1style.radio(
        "Background Shape",
        ["rectangle", "circle", None],
        index=0
    )

    bg_color = col1style.color_picker(
        "Background Color",
        st.session_state.get("bg_color", "#ffffff")
    )

    bg_buffer = col1style.slider(
        "Background Size",
        0,
        50,
        st.session_state.get("bg_buffer", 4)
    )

    col1style.markdown("---")

    contour_color = col1style.color_picker(
        "Map contour color",
        st.session_state.get("contour_color", "#000000")
    )

    contour_width = col1style.slider(
        "Map contour width",
        0,
        30,
        st.session_state.get("contour_width", 2)
    )

    name_on = col2style.checkbox(
        "Display title",
        st.session_state.get("name_on", True)
    )

    custom_title = col2style.text_input(
        "Custom title (optional)",
        st.session_state.get("custom_title", "")
    )

    font_size = col2style.slider(
        "Title font size",
        1,
        50,
        st.session_state.get("font_size", 26)
    )

    font_color = col2style.color_picker(
        "Title font color",
        st.session_state.get("font_color", "#000000")
    )

    text_x = col2style.slider(
        "Title left/right",
        -100,
        100,
        st.session_state.get("text_x", 0)
    )

    text_y = col2style.slider(
        "Title top/bottom",
        -100,
        100,
        st.session_state.get("text_y", -46)
    )

    text_rotation = col2style.slider(
        "Title rotation",
        -90,
        90,
        st.session_state.get("text_rotation", 0)
    )


    # ---------------- STYLE COLOR UPDATE ----------------
    if style != st.session_state["previous_style"]:
        st.session_state.update(get_colors_from_style(style))

    draw_settings = copy.deepcopy(STYLES[style])

    for lc_class in st.session_state.lc_classes:
        picked_color = col3style.color_picker(
            lc_class,
            key=lc_class
        )

        if "_" in lc_class:
            lc_class_name, idx = lc_class.split("_")
            draw_settings[lc_class_name]["cmap"][int(idx)] = picked_color
        else:
            draw_settings[lc_class]["fc"] = picked_color

    submit = st.form_submit_button("Generate Map")


# ---------------- MAP GENERATION ----------------
if submit:

    with st.spinner("Creating map... (may take up to a minute)"):

        rectangular = shape != "circle"

        try:
            aoi = get_aoi(
                address=address,
                radius=radius,
                rectangular=rectangular
            )

        except GeoCodingError as e:
            st.error(f"ERROR: {str(e)}")
            st.stop()

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
            "shape": shape,
            "contour_width": contour_width,
            "contour_color": contour_color,
            "bg_shape": bg_shape,
            "bg_buffer": bg_buffer,
            "bg_color": bg_color,
        }

        fig = st_plot_all(_df=df, **config)

        st.pyplot(
            fig,
            pad_inches=0,
            bbox_inches="tight",
            transparent=True,
            dpi=300
        )


# ---------------- EXPORT IMAGE ----------------
if "fig" in locals():

    st.markdown("---")

    with st.expander("Export image"):

        img_format = st.selectbox(
            "File type",
            ["png", "svg"]
        )

        fname_base = slugify(address) if address else "prettymapp"

        def _make_download_data():
            if img_format == "svg":
                return plt_to_svg(fig)

            buf = io.BytesIO()
            fig.savefig(
                buf,
                format=img_format,
                dpi=300,
                pad_inches=0,
                bbox_inches="tight",
                transparent=True
            )
            buf.seek(0)
            return buf.getvalue()

        st.download_button(
            label="Download",
            data=_make_download_data,
            file_name=f"{fname_base}.{img_format}",
            mime="image/png" if img_format == "png" else "image/svg+xml"
        )


# ---------------- EXPORT GEOJSON ----------------
if submit:

    ex1, ex2 = st.columns(2)

    with ex1.expander("Export geometries as GeoJSON"):
        st.write(f"{df.shape[0]} geometries")

        geojson_fname_base = slugify(address) if address else "prettymapp"

        st.download_button(
            label="Download GeoJSON",
            data=lambda: df.to_json().encode("utf-8"),
            file_name=f"{geojson_fname_base}.geojson",
            mime="application/geo+json",
        )

    with ex2.expander("Export map configuration"):
        st.write(config)


# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown(
    "More infos and ⭐ at [github.com/asifproject/Geo_Vista](https://github.com/asifproject/Geo_Vista)"
)


# ---------------- SAVE STYLE ----------------
st.session_state["previous_style"] = style