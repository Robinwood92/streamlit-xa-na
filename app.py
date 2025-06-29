import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import shape
from io import BytesIO
import pandas as pd

# --- Tải shapefile
@st.cache_data
def load_shapefile():
    gdf = gpd.read_file("Xa_NA_chuan.shp")
    return gdf.to_crs(epsg=4326)  # Chuyển về WGS84
gdf = load_shapefile()

# --- Tiêu đề
st.title("🎯 Chọn vùng trên bản đồ để lấy danh sách xã")

# --- Tạo bản đồ với folium
center = [19.23, 104.8]
m = folium.Map(location=center, zoom_start=9, tiles="OpenStreetMap")

# --- Thêm layer xã
folium.GeoJson(gdf, name="Các xã").add_to(m)

# --- Thêm công cụ vẽ
from folium.plugins import Draw
draw = Draw(export=True)
draw.add_to(m)

# --- Hiển thị bản đồ tương tác
st.markdown("### 🗺️ Vẽ vùng trên bản đồ")
output = st_folium(m, width=700, height=500, returned_objects=["last_active_drawing"])

# --- Xử lý vùng vẽ
if output and output.get("last_active_drawing"):
    try:
        # Chuyển vùng vẽ sang shapely polygon
        polygon_geom = shape(output["last_active_drawing"]["geometry"])

        # Chọn các xã giao với vùng vẽ
        selected_gdf = gdf[gdf.intersects(polygon_geom)]

        if not selected_gdf.empty:
            st.success(f"✅ Tìm thấy {len(selected_gdf)} xã nằm trong vùng vẽ.")

            # --- Hiển thị nhóm theo huyện
            st.markdown("## 📌 Danh sách xã theo từng huyện:")
            grouped = selected_gdf.groupby("Diem")["Xa"].unique()
            for huyen, xa_list in grouped.items():
                st.write(huyen+": "+", ".join(sorted(xa_list)))

            # --- Tạo DataFrame nhóm huyện - xã (dạng 1 dòng)
            grouped_df = (
                selected_gdf.groupby("Diem")["Xa"]
                .apply(lambda x: ", ".join(sorted(set(x))))
                .reset_index()
            )

            # --- Xuất Excel
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                grouped_df.to_excel(writer, index=False, sheet_name="Xa_chon")
            output_excel.seek(0)

            st.download_button(
                label="📥 Tải danh sách xã theo huyện (Excel)",
                data=output_excel,
                file_name="xa_nhom_theo_huyen.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Không có xã nào nằm trong vùng bạn đã vẽ.")
    except Exception as e:
        st.error(f"❌ Lỗi xử lý vùng vẽ: {e}")
else:
    st.info("🖌️ Vui lòng vẽ một vùng trên bản đồ để bắt đầu.")
