#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 28 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used as part of the condition_darkTargets.py script. It is
executed after "createGDBStruct.py" and is followed by "parseOverlap.py".

SUMMARY
Imports all the dark target shapefiles located in the Year Folder and converts
them to feature classes in the output file geodatabase previously created by
"createGDBStruct.py". Some data clean-up occurs, and a datetime field and
targetID field are added to the feature class.

INPUT
- Dark Targets Shapefiles (automated input): Shapefiles located in the Year Folder
 produced by the RADARSAT-2 dark target feature extraction process. Every shapefile
 in the Year Folder is detected and imported by the script, as long as they are
 located inside the "Features" folder under each radar acquisition folder.

- Dark Feature Dataset (automated input): Feature dataset in the output file
geodatabase in which the shapefiles are directly converted to feature classes.

OUTPUT
- Dark Targets Feature Classes (automated output): Feature classes converted
from the input shapefiles. Each feature class is projected and placed in the
"dark_features" feature dataset. Pixel artifacts are dissolved and the background
ocean polygon is removed. A datetime field is added, with its value parsed
from the "RSatID value". A targetID field is added, with its value determined as
a concatenation of each target's "Pid" and datetime stamp."""

# Libraries
# =========
import arcpy
import os
import logging


class loadDarkTargets(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "loadDarkTargets"
        self.description = "Imports dark targets shapefiles, converts them to \
        feature classes and places them in the dark_features dataset."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [None]*2

        params[0] = arcpy.Parameter(
            displayName="Year Folder",
            name="year_workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        params[1] = arcpy.Parameter(
            displayName="Dark Features Dataset",
            name="dark_featDS",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.AddMessage("\nLoading dark target shapefiles...")
        logging.info("Starting loadDarkTargets.py script...\n")
        # Define variables from parameters
        arcpy.env.workspace = parameters[0].valueAsText
        featWorkspace = parameters[1].valueAsText

        # Determine list of RADARSAT-2 image folder workspaces
        image_list = arcpy.ListWorkspaces()
        arcpy.AddMessage("Workspace contains " + str(len(image_list)) + " image folders to import.")

        # Iterate through image folders
        for image in image_list:
            logging.info("Processing '%s' source image", image)
            # Set workspace to "Features" folder inside current image folder
            arcpy.env.workspace = os.path.join(image,"Features")

            # Detect shapefile to import
            fcList = arcpy.ListFeatureClasses()
            fc = fcList[0]
            path_split = image.split("\\")
            imageName = path_split[len(path_split)-1]
            arcpy.AddMessage("\nProcessing " + imageName + " -- " + fc)

            # Create feature layer from shapefile, excluding ocean polygon
            # ============================================================== #
            # Attribute assumption: Background ocean polygon's "Pid" = 1     #
            # ============================================================== #
            tempLayer = "darkTargetsLyr"
            arcpy.MakeFeatureLayer_management(fc, tempLayer, "NOT \"Pid\" = 1")
            logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", tempLayer, fc)

            # Parse datetime from folder name
            folder_split = imageName.split("_")
            fcName = folder_split[0] + "_" + folder_split[5] + "_" + folder_split[6]
            outFeatureClass = os.path.join(featWorkspace, fcName)

            # Dissolve feature layer to collapse polygons with identical attributes together
            arcpy.AddMessage("Dissolving...")
            fieldList = arcpy.ListFields(fc)
            statsFields = []
            for field in fieldList:
                if "FID" in field.name or "Shape" in field.name or "Pid" in field.name or field.name == "ID":
                    continue
                statsField = [field.name,"FIRST"]
                statsFields.append(statsField)
            arcpy.Dissolve_management(tempLayer, outFeatureClass, "Pid", statsFields)
            logging.info("Dissolve: '%s' feature class created from '%s' layer dissolve", outFeatureClass, tempLayer)

            # Rename attribute fields to revert to original field names
            arcpy.AddMessage("Renaming attribute fields...")
            fieldList = arcpy.ListFields(outFeatureClass)
            for field in fieldList:
                if field.name.startswith("FIRST_"):
                    newName = field.name[6:]
                    arcpy.AlterField_management(outFeatureClass, field.name, newName)

            # Add Date field
            arcpy.AddMessage("Adding datetime field...")
            arcpy.AddField_management(outFeatureClass, "DateTime", "DATE")
            logging.info("Add Field: 'DateTime' field (date data type) added to '%s' feature class", outFeatureClass)
            year = folder_split[5][:4]
            month = folder_split[5][4:6].lstrip("0")
            day = folder_split[5][-2:].lstrip("0")
            hour = folder_split[6][:2].lstrip("0")
            minute = folder_split[6][2:4].lstrip("0")
            if minute == "":
                minute = "0"
            second = folder_split[6][-2:].lstrip("0")
            if second == "" :
                second = "0"
            expression = "datetime.datetime(" + year + "," + month + "," + day + "," + hour + "," + minute + "," + second + ")"
            arcpy.CalculateField_management(outFeatureClass, "DateTime", expression, "PYTHON_9.3")
            logging.info("Calculate Field: 'DateTime' field value calculated for '%s' feature class", outFeatureClass)

            # Add target ID field to uniquely identify dark targets
            arcpy.AddMessage("Adding targetID field...")
            arcpy.AddField_management(outFeatureClass, "targetID", "TEXT")
            logging.info("Add Field: 'targetID' field (string data type) added to '%s' feature class", outFeatureClass)
            expression = "str(!Pid!)[:-2] + '_' + str(" + folder_split[5] + ") + '_' + str(" + folder_split[6] + ")"
            arcpy.CalculateField_management(outFeatureClass, "targetID", expression, "PYTHON_9.3")
            logging.info("Calculate Field: 'targetID' field value calculated for '%s' feature class", outFeatureClass)

            logging.info("Processing for '%s' source image complete\n", image)

        logging.info("loadDarkTargets.py script finished\n\n")

        return