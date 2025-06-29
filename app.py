import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import Draw
from shapely.geometry import shape
from streamlit_folium import st_folium
import pandas as pd
from io import BytesIO

# Tải shapefile vào cache
@st.cache_data
def load_shapefile():
    gdf = gpd.read_file("Xa_NA_chuan.shp")
    return gdf.to_crs(epsg=4326)
gdf = load_shapefile()

# Giao diện
st.set_page_config(layout="wide")
st.title("🗺️ Chọn vùng để liệt kê danh sách xã (Nghệ An)")

# Tạo bản đồ
center = [19.23, 104.8]
m = folium.Map(location=center, zoom_start=9, tiles="OpenStreetMap")

# Lớp các xã có thể bật/tắt
xa_layer = folium.FeatureGroup(name="📍 Lớp các xã", show=True)
folium.GeoJson(gdf, name="Các xã").add_to(xa_layer)
xa_layer.add_to(m)

# Công cụ vẽ
Draw(export=True).add_to(m)

# Điều khiển layer
folium.LayerControl(collapsed=False).add_to(m)

# Hiển thị bản đồ tương tác
st.markdown("### 👉 Hãy vẽ một vùng trên bản đồ:")
output = st_folium(m, height=550, width=950, returned_objects=["last_active_drawing"])

# Xử lý polygon
if output and output.get("last_active_drawing"):
    try:
        # Đọc polygon shapely
        polygon_geom = shape(output["last_active_drawing"]["geometry"])

        # Lọc các xã giao cắt vùng vẽ
        selected_gdf = gdf[gdf.intersects(polygon_geom)]

        if not selected_gdf.empty:
            st.success(f"✅ Tìm thấy {len(selected_gdf)} xã nằm trong vùng được vẽ.")

            # Hiển thị nhóm xã theo huyện
            st.markdown("## 🗂️ Danh sách xã theo huyện")
            grouped = selected_gdf.groupby("Huyen")["Diem"].unique()
            for huyen, xa_list in grouped.items():
                st.markdown(f"**📍 Huyện: {huyen}**")
                st.write(", ".join(sorted(xa_list)))

            # Chuẩn bị dữ liệu Excel
            grouped_df = (
                selected_gdf.groupby("Huyen")["Diem"]
                .apply(lambda x: ", ".join(sorted(set(x))))
                .reset_index()
                .rename(columns={"Diem": "Xa"})
            )

            # Ghi ra file Excel
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                grouped_df.to_excel(writer, index=False, sheet_name="Xa_chon")
            output_excel.seek(0)

            # Nút tải
            st.download_button(
                label="📥 Tải danh sách xã (Excel)",
                data=output_excel,
                file_name="xa_nhom_theo_huyen.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Không có xã nào nằm trong vùng được vẽ.")
    except Exception as e:
        st.error(f"❌ Lỗi xử lý vùng vẽ: {e}")
else:
    st.info("✏️ Vui lòng vẽ một vùng trên bản đồ để bắt đầu.")
