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
def save_folium_map_to_png(m, file_name="map.png", width=1200, height=800):
    """
    Save a Folium map object as a PNG by rendering it in a headless browser via Selenium.
    """
    # Save map as temporary HTML
    map_html = "temp_map.html"
    m.save(map_html)

    # Configure Selenium (headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--window-size={width}x{height}")
    chrome_options.add_argument("--high-dpi-support=1")
    

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("file://" + os.path.join(os.getcwd(), map_html))
    time.sleep(1)



    # Take a screenshot
    driver.save_screenshot(file_name)
    driver.quit()

    image = Image.open(file_name)
    cropped_image = image.crop((0, 0, width, height))
    cropped_image.save(file_name)

    os.remove(map_html)

def fit_map_by_radius(m, center_lat, center_lon):
    """
    Approximate a bounding box in degrees for a circle of 'radius_miles' around (center_lat, center_lon).
    Then apply folium's fit_bounds to make sure that circle is fully in view.
    """
    radius_miles_s = 415
    Add_= 0#Additional
    # Approx. 1° of latitude ~ 69 miles
    base_lat_offset = (radius_miles_s / 69.9) 

    # For longitude, factor in the cosine of the latitude to adjust degree size
    # (1° of longitude is 69 * cos(latitude) miles at mid-latitudes)
    cos_lat = math.cos(math.radians(center_lat))
    # Avoid dividing by zero near the poles
    if abs(cos_lat) < 1e-5:  
        cos_lat = 1e-5

    base_lon_offset = radius_miles_s / (69.9 * cos_lat) 
    lat_fudge_factor = 1.00
    lon_fudge_factor = 1.00

    
    lat_offset = base_lat_offset * lat_fudge_factor
    lon_offset = base_lon_offset * lon_fudge_factor

    # The southwestern corner of the bounding box
    sw_corner = ((center_lat - lat_offset)-Add_, (center_lon - lon_offset)-Add_)
    # The northeastern corner of the bounding box
    ne_corner = ((center_lat + lat_offset)+Add_, (center_lon + lon_offset)+Add_)

    # Tell Folium to auto‐zoom & pan so this bounding box is in view
    m.fit_bounds([sw_corner, ne_corner])
def create_map_for_centroid(row, hospitals_gdf, idx=0, radius_miles=500):
    """
    Create a map for a single centroid and save it as PNG.
    """
    centroid = row.geometry  # Extract the Point geometry
    geoid = row['GEOID']     # Extract the GEOID or other attributes as needed

    radius_km = radius_miles * 1.60934  # Convert miles to kilometers

    # Create the map centered at the centroid
    m = folium.Map(location=[centroid.y, centroid.x], tiles="OpenStreetMap")

    # Add the centroid as a red marker
    folium.CircleMarker(
        location=[centroid.y, centroid.x],
        radius=5,                # Slightly larger for visibility
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=1.0,
        tooltip=f"Centroid {idx}"  # Tooltip for the centroid
    ).add_to(m)

    # Filter hospitals within the radius using geodesic distance
    hospitals_in_radius = hospitals_gdf[hospitals_gdf.apply(
        lambda row: geodesic((centroid.y, centroid.x), (row.geometry.y, row.geometry.x)).miles <= radius_miles,
        axis=1
    )]

    # Add hospitals as blue markers
    for _, hospital in hospitals_in_radius.iterrows():
        folium.CircleMarker(
            location=[hospital.geometry.y, hospital.geometry.x],
            radius=1,  # Small marker for hospitals
            color='blue',
            fill=True,
            fill_color='blue',
            fill_opacity=1.0,
            tooltip=f"Hospital: {hospital.get('name', 'Unknown')}"
        ).add_to(m)

    # Fit the map to the bounding box
    fit_map_by_radius(m, centroid.y, centroid.x)

    # Save the map as PNG
    out_png = f"map_of_{geoid}.png"
    save_folium_map_to_png(m, file_name=out_png, width=1200, height=800)
    print(f"Saved {out_png}")


def main():
    # Load CSV files
    centroids = pd.read_csv("center_us_with_centroid.csv")
    hospitals = pd.read_csv("output (2).csv")

    # Convert to GeoDataFrames
    centroids_gdf = gpd.GeoDataFrame(
        centroids,
        geometry=gpd.points_from_xy(centroids['centroid_lon'], centroids['centroid_lat'])
    )
    hospitals_gdf = gpd.GeoDataFrame(
        hospitals,
        geometry=gpd.points_from_xy(hospitals['longitude'], hospitals['latitude'])
    )

    # Generate maps for all centroids
    for idx, row in centroids_gdf.iterrows():  # Iterate over rows, not just geometry
        create_map_for_centroid(row, hospitals_gdf, idx=idx, radius_miles=500)
        if idx >= 1:  # Limit for testing
            break


if __name__ == "__main__":
    main()