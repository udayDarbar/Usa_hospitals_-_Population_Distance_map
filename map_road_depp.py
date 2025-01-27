import os
import math
import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
from selenium.webdriver.support.ui import WebDriverWait
import time
from geopy.distance import geodesic
from tqdm import tqdm  # For progress bar
import time  # For tracking time


def save_folium_map_to_png(m, file_name="map.png", width=1200, height=800):
    # Save a Folium map object as a PNG by rendering it in a headless browser via Selenium.
    map_html = "temp_map.html"
    m.save(map_html)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--window-size={width}x{height}")
    chrome_options.add_argument("--high-dpi-support=1")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("file://" + os.path.join(os.getcwd(), map_html))
    time.sleep(1)

    driver.save_screenshot(file_name)
    driver.quit()

    image = Image.open(file_name)
    cropped_image = image.crop((0, 0, width, height))
    cropped_image.save(file_name)

    os.remove(map_html)


def fit_map_by_radius(m, center_lat, center_lon):
    # Approximate a bounding box in degrees for a circle of 'radius_miles' around (center_lat, center_lon).
    radius_miles_s = 415
    Add_ = 0  # Additional
    base_lat_offset = (radius_miles_s / 69.9)
    cos_lat = math.cos(math.radians(center_lat))
    if abs(cos_lat) < 1e-5:
        cos_lat = 1e-5

    base_lon_offset = radius_miles_s / (69.9 * cos_lat)
    lat_fudge_factor = 1.00
    lon_fudge_factor = 1.00

    lat_offset = base_lat_offset * lat_fudge_factor
    lon_offset = base_lon_offset * lon_fudge_factor

    sw_corner = ((center_lat - lat_offset) - Add_, (center_lon - lon_offset) - Add_)
    ne_corner = ((center_lat + lat_offset) + Add_, (center_lon + lon_offset) + Add_)

    m.fit_bounds([sw_corner, ne_corner])


def create_map_for_centroid(row, hospitals_gdf, idx=0, radius_miles=500):
    # Create a map for a single centroid and save it as PNG.
    centroid = row.geometry
    geoid = row['GEOID']

    radius_km = radius_miles * 1.60934

    m = folium.Map(location=[centroid.y, centroid.x], tiles="OpenStreetMap")

    folium.CircleMarker(
        location=[centroid.y, centroid.x],
        radius=5,
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=1.0,
        tooltip=f"Centroid {idx}"
    ).add_to(m)

    hospitals_in_radius = hospitals_gdf[hospitals_gdf.apply(
        lambda row: geodesic((centroid.y, centroid.x), (row.geometry.y, row.geometry.x)).miles <= radius_miles,
        axis=1
    )]

    for _, hospital in hospitals_in_radius.iterrows():
        folium.CircleMarker(
            location=[hospital.geometry.y, hospital.geometry.x],
            radius=1,
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=1.0,
            tooltip=f"Hospital: {hospital.get('name', 'Unknown')}"
        ).add_to(m)

    fit_map_by_radius(m, centroid.y, centroid.x)

    out_png = f"map_of_{geoid}.png"
    save_folium_map_to_png(m, file_name=out_png, width=900, height=800)
    print(f"Saved {out_png}")


def main():
    # Load CSV files
    centroids = pd.read_csv("center_us_with_centroid.csv")
    hospitals = pd.read_csv("output (2).csv")

    centroids_gdf = gpd.GeoDataFrame(
        centroids,
        geometry=gpd.points_from_xy(centroids['centroid_lon'], centroids['centroid_lat'])
    )
    hospitals_gdf = gpd.GeoDataFrame(
        hospitals,
        geometry=gpd.points_from_xy(hospitals['longitude'], hospitals['latitude'])
    )

    # Use tqdm for progress bar
    for idx, row in tqdm(centroids_gdf.iterrows(), total=len(centroids_gdf), desc="Processing centroids"):
        start_time = time.time()  # Start timer for this centroid
        create_map_for_centroid(row, hospitals_gdf, idx=idx, radius_miles=500)
        end_time = time.time()  # End timer for this centroid
        elapsed_time = end_time - start_time
        print(f"Centroid {idx} processed in {elapsed_time:.2f} seconds.")


if __name__ == "__main__":
    main()
