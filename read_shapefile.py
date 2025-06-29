import geopandas as gpd

# Replace 'your_shapefile.shp' with the path to your shapefile
shapefile_path = 'Xa_NA_chuan.shp'
gdf = gpd.read_file(shapefile_path)

# Print the 10th row (index 9)
print(gdf.iloc[9])