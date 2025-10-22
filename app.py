import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import Draw, FloatImage
from shapely.geometry import shape
from shapely.ops import unary_union
from streamlit_folium import st_folium
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook
import requests
from datetime import datetime, timedelta, timezone
import os
import base64
from PIL import Image

# =====================
# 🛰️ HÀM LẤY URL ẢNH RADAR
# =====================
def get_vin_radar_urls():
    """Lấy 2 URL ảnh radar mới nhất từ trạm VIN"""
    base_url = "http://hymetnet.gov.vn/dataout_web/VIN"
    
    # Lấy thời gian UTC, trừ 10 phút để đảm bảo ảnh đã có
    t1 = datetime.now(timezone.utc) - timedelta(minutes=10)
    t1 = t1.replace(minute=(t1.minute // 10) * 10, second=0, microsecond=0)
    
    # Ảnh trước đó 10 phút
    t0 = t1 - timedelta(minutes=10)
    t0 = t0.replace(minute=(t0.minute // 10) * 10, second=0, microsecond=0)
    
    def fmt(dt):
        ymd = dt.strftime("%Y%m%d")
        ymdhm = dt.strftime("%Y%m%d%H%M")
        # Chuyển sang UTC+7 để hiển thị
        dt_utc7 = dt + timedelta(hours=7)
        display_time = dt_utc7.strftime("%H:%M")
        return ymd, ymdhm, display_time, dt
    
    ymd0, ymdhm0, display0, dt0 = fmt(t0)
    ymd1, ymdhm1, display1, dt1 = fmt(t1)
    
    url0 = f"{base_url}/{ymd0}/VIN_{ymdhm0}_CMAX00.png"
    url1 = f"{base_url}/{ymd1}/VIN_{ymdhm1}_CMAX00.png"
    
    return [(ymdhm0, url0, display0, dt0), (ymdhm1, url1, display1, dt1)]

# =====================
# 🌧️ TẢI VÀ CHUYỂN ẢNH RADAR SANG BASE64
# =====================
@st.cache_data(ttl=600)  # Cache 10 phút
def download_radar_as_base64(url):
    """Tải ảnh radar và chuyển sang base64 để nhúng vào Folium"""
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            # Chuyển sang base64
            img_base64 = base64.b64encode(r.content).decode()
            return f"data:image/png;base64,{img_base64}"
        return None
    except Exception as e:
        return None

@st.cache_data(ttl=600)  # Cache 10 phút
def load_all_radars():
    """Tải tất cả ảnh radar khả dụng"""
    urls = get_vin_radar_urls()
    loaded_radars = []
    
    for timecode, url, display_time, dt in urls:
        try:
            radar_base64 = download_radar_as_base64(url)
            if radar_base64:
                loaded_radars.append((timecode, radar_base64, display_time, dt))
        except:
            pass
    
    return loaded_radars

# =====================
# 🎨 TẢI LEGEND RADAR
# =====================
@st.cache_data
def load_legend_base64():
    """Tải ảnh legend và chuyển sang base64"""
    try:
        # Đọc file legend
        with open("legend_radar.jpg", "rb") as f:
            legend_data = f.read()
        legend_base64 = base64.b64encode(legend_data).decode()
        return f"data:image/jpg;base64,{legend_base64}"
    except FileNotFoundError:
        st.warning("⚠️ Không tìm thấy file 'legend_radar.jpg'")
        return None

# =====================
# ⚙️ Tải shapefile Nghệ An
# =====================
@st.cache_data
def load_shapefile():
    # Đọc GeoJSON thay vì shapefile để tránh lỗi fiona
    gdf = gpd.read_file("Xa_NA_chuan.geojson")
    return gdf.to_crs(epsg=4326)

gdf = load_shapefile()

# =====================
# 🧭 Giao diện
# =====================
st.set_page_config(layout="wide")
st.title("🗺️ Bản đồ Nghệ An với Radar và chọn vùng")

# =====================
# 📡 Sidebar - Cài đặt Radar
# =====================
with st.sidebar:
    st.header("📡 Cài đặt lớp Radar")
    show_radar = st.checkbox("Hiển thị ảnh Radar", value=True)
    
    if show_radar:
        radar_opacity = st.slider("Độ trong suốt Radar", 0.0, 1.0, 0.6, 0.1)
        
        # Tải tất cả ảnh radar
        with st.spinner("Đang tải ảnh radar..."):
            loaded_radars = load_all_radars()
        
        if loaded_radars:
            st.success(f"✅ Đã tải {len(loaded_radars)} ảnh radar")
            
            # Slider để chọn ảnh radar
            if len(loaded_radars) > 1:
                radar_idx = st.slider(
                    "Chọn thời điểm radar:",
                    0, 
                    len(loaded_radars) - 1,
                    len(loaded_radars) - 1,  # Mặc định chọn ảnh mới nhất
                    format=""
                )
                timecode, radar_base64, display_time, dt = loaded_radars[radar_idx]
                st.info(f"🕐 {display_time} (UTC+7)")
            else:
                timecode, radar_base64, display_time, dt = loaded_radars[0]
                st.info(f"🕐 {display_time} (UTC+7)")
        else:
            st.warning("⚠️ Không tìm thấy ảnh radar khả dụng")
            show_radar = False

# =====================
# 🗺️ Bản đồ nền
# =====================
center = [19.23, 104.8]
m = folium.Map(location=center, zoom_start=9, tiles="OpenStreetMap")

# Thêm shapefile Nghệ An
folium.GeoJson(
    gdf,
    name="📍 Các xã Nghệ An",
    style_function=lambda x: {"color": "gray", "weight": 1, "fillOpacity": 0.1},
    tooltip=folium.GeoJsonTooltip(fields=["Xa", "Diem"], aliases=["Xã:", "Huyện:"]),
).add_to(m)

# =====================
# 🛰️ Thêm 1 lớp Radar vào bản đồ
# =====================
if show_radar and loaded_radars:
    # Tọa độ radar VIN (trung tâm: Vinh, Nghệ An)
    center_lat, center_lon = 18.656, 105.71083
    radius_deg = 2.8  # ~250km bán kính
    
    # Giới hạn ảnh radar
    bounds = [
        [center_lat - radius_deg, center_lon - radius_deg],  # Southwest
        [center_lat + radius_deg, center_lon + radius_deg]   # Northeast
    ]
    
    # Thêm ảnh radar đã chọn từ slider
    folium.raster_layers.ImageOverlay(
        image=radar_base64,
        bounds=bounds,
        opacity=radar_opacity,
        name=f"🌧️ Radar {display_time}",
        interactive=False,
        cross_origin=False,
        zindex=1
    ).add_to(m)
    
    # Thêm legend vào góc dưới bên trái
    legend_base64 = load_legend_base64()
    if legend_base64:
        # Tạo HTML cho legend với CSS để điều chỉnh vị trí và kích thước
        legend_html = f'''
        <div style="
            position: fixed;
            bottom: 30px;
            left: 10px;
            width: 60px;
            height: auto;
            z-index: 9999;
            background-color: rgba(255, 255, 255, 0.9);
            border: 2px solid grey;
            border-radius: 5px;
            padding: 5px;
        ">
            <img src="{legend_base64}" style="width: 100%; height: auto;">
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

# =====================
# ✏️ Công cụ vẽ
# =====================
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

# =====================
# 📝 Hướng dẫn
# =====================
st.markdown("### ✏️ Hướng dẫn:")
st.markdown("""
- ☑️ Bật/tắt lớp **Radar** trong sidebar bên trái
- 🎨 Điều chỉnh độ trong suốt của ảnh radar
- ✏️ Dùng công cụ **Polygon** để vẽ vùng (double-click để kết thúc)
- 📍 Có thể vẽ **nhiều vùng**
- 🔄 Khi hoàn tất, nhấn **[Lấy xã]** để liệt kê các xã trong tất cả vùng đã vẽ
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