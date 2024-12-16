""" Write me a script using esri arcpy python Library that can accomplish the following.
Define the workspace to be the location where the script is running. 
 create a new shapefile feature class called Orange. First check if the shape file orange exists. if it does delete it.
 open a CSV file called density.csv, Provide a full path to open density.csv using the workspace variable.
from density.csv, Read the contents of the column Geo that contain Latitude longitude coordinate pairs that define a polygon. Use those latitude longitude coordinate pairs to create polygon features inside the shapefile feature class called Orange. This is an example of what the contents of the geo look like
POLYGON((16.8905353737373 52.4370627922433, 16.8903206754077 52.4415562341257, 16.8829676308127 52.4414247868882, 16.8831830760886 52.4369313662029, 16.8905353737373 52.4370627922433))

Note that POLYGON((" and ")) Will be at different lengths within the content so adjust the script to account for variable lengths as opposed to hard coding. Use a regular expression.
Note as well that the contents of Geo column contain commas. these commas will cause problems when trying to read the CSV file line by line. Therefore do not use fields = line.strip().split(',') This will cause problem. rather convert the commas inside of the Geo column to some other type of deliminator that can be used to parse the coordinate pairs.
Determine the number of significant digits inside of a coordinate pair. Generate a print statement indicating what you found the number of significant digits to be.
if need be, update the Environment settings so that the XY resolution is set to the number of  significant digits you found to ensure that the polygon coordinates are entered correctly.

The density.csv file also has a columns called  day_type, bigger_id, and c_users.  day_type is an string, bigger_id is a string, and C_users is an int string.
Add the contents from each of these column to each record you also create a polygon in the shapefile feature class orange.  The order of the columns in density.csv is day_type, bigger_id, c_users, and geo.
Include some type of error handling in case an unknown problem occurs and document what the specific error is along with the line number of where the error occurred  with a print statement once the error is trapped. 


 """

import arcpy
import os
import re

#DATASET_NAME = "density"
DATASET_NAME = "visitors"

try:
    # Define workspace to be the location where the script is running
    workspace = os.path.dirname(os.path.abspath(__file__))
    arcpy.env.workspace = workspace

    # Define input CSV file
    csv_file = os.path.join(workspace, DATASET_NAME + ".csv")

    # Define output shapefile
    output_shapefile = DATASET_NAME + ".shp"

    # Check if  shapefile exists and delete it if it does
    if arcpy.Exists(output_shapefile):
        arcpy.Delete_management(output_shapefile)

    # Open CSV file and read data
    with open(csv_file, 'r') as f:
        header = next(f).strip().split(',')
        geo_index = header.index('geo')  # Find the index of the 'geo' column

        # Find the number of significant digits in the first coordinate pair
        first_geo = re.search(r'POLYGON\(\((.*?)\)\)', f.readline()).group(1)
        first_coordinates = [tuple(map(float, point.split())) for point in first_geo.split(',')]
        significant_digits = len(str(first_coordinates[0][0]).split('.')[1])

    # Set environment settings to ensure correct XY resolution
    #arcpy.env.XYResolution = str(significant_digits)
    arcpy.env.XYResolution = "0.00000000001 Meters"    

    # Create a new shapefile feature class
    spatial_reference = arcpy.SpatialReference(4326)  # Assuming WGS 1984 coordinate system
    arcpy.CreateFeatureclass_management(workspace, output_shapefile, "POLYGON", spatial_reference=spatial_reference)

    # Add fields to the shapefile
    #arcpy.AddField_management(output_shapefile, "day_type", "TEXT", field_length=50)
    arcpy.AddField_management(output_shapefile, "bigger_id", "TEXT", field_length=50)
    arcpy.AddField_management(output_shapefile, "c_users", "LONG")

    # Open CSV file again and read data
    with open(csv_file, 'r') as f:
        next(f)  # Skip the header line
        line_number = 2  # Start from line 2 (data starts from line 2)
        for line in f:
            try:
                fields = line.strip().split(',')
                
                #day_type = fields[0]
                #bigger_id = fields[1]
                #c_users = int(fields[2])

                #day_type = fields[0]
                bigger_id = fields[0]
                c_users = int(fields[1])

                # Extract polygon coordinates using regular expression
                geo = re.search(r'POLYGON\(\((.*?)\)\)', line).group(1)
                geo = geo.replace(',', ';')  # Replace commas with semicolons

                coordinates = [tuple(map(float, point.split())) for point in geo.split(';')]

                # Create polygon geometry
                array = arcpy.Array([arcpy.Point(coord[0], coord[1]) for coord in coordinates])
                polygon = arcpy.Polygon(array)

                # Insert a new row into the shapefile
                #with arcpy.da.InsertCursor(output_shapefile, ["SHAPE@", "day_type", "bigger_id", "c_users"]) as cursor:
                with arcpy.da.InsertCursor(output_shapefile, ["SHAPE@", "bigger_id", "c_users"]) as cursor:
                    #cursor.insertRow([polygon, day_type, bigger_id, c_users])
                    cursor.insertRow([polygon, bigger_id, c_users])

            except Exception as e:
                print(f"Error on line {line_number}: {e}")

            line_number += 1

    print("Shapefile creation complete.")

except Exception as e:
    print(f"An error occurred: {e}")

