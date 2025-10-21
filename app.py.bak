import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import Draw
from shapely.geometry import shape
from shapely.ops import unary_union
from streamlit_folium import st_folium
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook

# =====================
# ⚙️ Tải shapefile Nghệ An
# =====================
@st.cache_data
def load_shapefile():
    gdf = gpd.read_file("Xa_NA_chuan.shp")
    return gdf.to_crs(epsg=4326)

gdf = load_shapefile()

# =====================
# 🧭 Giao diện
# =====================
st.set_page_config(layout="wide")
st.title("🗺️ Chọn nhiều vùng để liệt kê các xã trong vùng")

# =====================
# 🗺️ Bản đồ nền
# =====================
center = [19.23, 104.8]
m = folium.Map(location=center, zoom_start=9, tiles="OpenStreetMap")

folium.GeoJson(
    gdf,
    name="📍 Các xã Nghệ An",
    style_function=lambda x: {"color": "gray", "weight": 1, "fillOpacity": 0.1},
    tooltip=folium.GeoJsonTooltip(fields=["Xa", "Diem"], aliases=["Xã:", "Huyện:"]),
).add_to(m)

Draw(
    export=False,
    draw_options={
        "polygon": {"allowIntersection": False, "showArea": True, "repeatMode": True},
        "rectangle": False,
        "circle": False,
        "circlemarker": False,
        "polyline": False,
        "marker": False,
    },
    edit_options={"edit": True, "remove": True},
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

st.markdown("### ✏️ Hướng dẫn:")
st.markdown("""
- Dùng công cụ **Polygon** để vẽ vùng (double-click để kết thúc).  
- Có thể vẽ **nhiều vùng**.  
- Khi hoàn tất, nhấn **[Lấy xã]** để liệt kê các xã trong tất cả vùng đã vẽ.
""")

# =====================
# 📍 Hiển thị bản đồ
# =====================
map_data = st_folium(m, height=600, width=950, returned_objects=["all_drawings"])

# =====================
# 💾 Lưu các polygon
# =====================
if "all_polygons" not in st.session_state:
    st.session_state.all_polygons = []

if map_data and "all_drawings" in map_data and map_data["all_drawings"]:
    st.session_state.all_polygons = [
        shape(feature["geometry"]) for feature in map_data["all_drawings"]
        if feature.get("geometry") is not None
    ]

st.info(f"📍 Hiện có **{len(st.session_state.all_polygons)}** vùng được vẽ.")

# =====================
# 🚀 Nút LẤY XÃ
# =====================
if st.button("📍 Lấy xã trong tất cả vùng đã vẽ"):
    if st.session_state.all_polygons:
        try:
            union_polygon = unary_union(st.session_state.all_polygons)
            selected_gdf = gdf[gdf.intersects(union_polygon)]

            if not selected_gdf.empty:
                st.success(f"✅ Tìm thấy {len(selected_gdf)} xã nằm trong các vùng đã vẽ.")

                # --- Gom xã theo huyện
                grouped_df = (
                    selected_gdf.groupby("Diem")["Xa"]
                    .apply(lambda x: ", ".join(sorted(set(x))))
                    .reset_index()
                )

                st.markdown("## 🗂️ Danh sách xã theo huyện")
                for diem, xa_list in grouped_df.values:
                    st.write(f"**{diem}**: {xa_list}")

                # --- Ghi dữ liệu vào file template.xlsx
                try:
                    wb = load_workbook("template.xlsx")
                    ws = wb.active

                    start_row = 3
                    for i, row in enumerate(grouped_df.itertuples(index=False), start=start_row):
                        ws.cell(row=i, column=1, value=row.Diem)
                        ws.cell(row=i, column=2, value=row.Xa)

                    output = BytesIO()
                    wb.save(output)
                    output.seek(0)

                    st.download_button(
                        label="📥 Tải file Excel (theo template)",
                        data=output,
                        file_name="xa_trong_vung_ve.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except FileNotFoundError:
                    st.error("❌ Không tìm thấy file 'template.xlsx' trong cùng thư mục.")
            else:
                st.warning("⚠️ Không có xã nào nằm trong các vùng đã vẽ.")
        except Exception as e:
            st.error(f"❌ Lỗi xử lý vùng vẽ: {e}")
    else:
        st.warning("⚠️ Bạn chưa vẽ vùng nào trên bản đồ.")
else:
    st.info("🖱️ Hãy vẽ vùng rồi nhấn **Lấy xã** để bắt đầu.")
