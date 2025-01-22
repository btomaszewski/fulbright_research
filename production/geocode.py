import arcpy
import csv

# Set the environment workspace to a desired folder where the shapefile will be created
arcpy.env.workspace = "D:/Profiles/nec9907/Downloads/fulbright_research/production/"
output_shapefile = "points_shapefile.shp"

# Define the spatial reference (WGS 84, EPSG:4326) for Poland coordinates
spatial_ref = arcpy.SpatialReference(4326)

# Create a new point shapefile with necessary fields
arcpy.CreateFeatureclass_management(arcpy.env.workspace, output_shapefile, "POINT", spatial_reference=spatial_ref)

# Add fields to the shapefile based on CSV columns (excluding Latitude and Longitude)
field_names = ["Message_ID", "Text", "Country", "City", "Province", "County", "Communes"]
for field in field_names:
    arcpy.AddField_management(output_shapefile, field, "TEXT")

# Add Latitude and Longitude fields (Optional: You could also create numeric fields)
arcpy.AddField_management(output_shapefile, "Latitude", "DOUBLE")
arcpy.AddField_management(output_shapefile, "Longitude", "DOUBLE")

# Open the CSV file
csv_file = "D:/Profiles/nec9907/Downloads/fulbright_research/production/imagelocation.csv"

# Insert cursor to add points to the shapefile
with arcpy.da.InsertCursor(output_shapefile, ["SHAPE@", "Message_ID", "Text", "Country", "City", "Province", "County", "Communes", "Latitude", "Longitude"]) as cursor:
    with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Iterate through rows in the CSV
        for row in reader:
            # Extract latitude and longitude from CSV
            latitude = float(row['Latitude'])
            longitude = float(row['Longitude'])

            # Create a point geometry based on latitude and longitude
            point = arcpy.Point(longitude, latitude)
            geometry = arcpy.PointGeometry(point, spatial_ref)

            # Insert the point into the shapefile with the additional data from the CSV
            cursor.insertRow((geometry, row['Message_ID'], row['Text'], row['Country'], row['City'], row['Province'], row['County'], row['Communes'], latitude, longitude))

print("Shapefile created successfully!")
