#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 28 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used as part of the "condition_darkTargets.py" script. It is
the first script to be executed by "condition_darkTargets.py", followed by
"loadDarkTargets.py".

SUMMARY
Automates the creation of the file geodatabase structure for the yearly data
geodatabases, including the creation of the "dark_features", "feature_overlap",
and "feature_union" feature datasets.

INPUT
- Year Folder (automated input): Folder containing the desired year's shapefiles
 produced by the RADARSAT-2 dark target feature extraction process. The file
 geodatabase is created in this same folder.

- File GDB Name (automated input): String used to name the file geodatabase that
 is created. The name of the Year Folder is used to also name the file
 geodatabase.

- Spatial Reference (hardcoded input): Arcpy spatial reference object set to
"NAD 1983 Canada Atlas Lambert" as the standard projection used during
geoprocessing within the feature datasets.

OUTPUT
- Yearly Data File Geodatabase (automated output): A file geodatabase is
produced in the same folder of the input year folder and is also named the same
as the input year folder. (e.g. 2010.gdb) The FGDB contains the "dark_features",
 "feature_overlap" and "feature_union" feature datasets, but is otherwise empty."""

# Libraries
# =========
import arcpy
import os
import logging


class createGDBStruct(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "createGDBStruct"
        self.description = "Creates file GDB and feature datasets required to \
        load and manipulate dark targets data in input shapefiles."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [None]*2

        params[0] = arcpy.Parameter(
            displayName="Products Folder",
            name="working_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        params[1] = arcpy.Parameter(
            displayName="File Geodatabase Name",
            name="gdbName",
            datatype="GPString",
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
        arcpy.AddMessage("\nCreating File GDB...")
        logging.info("Starting createGDBStruct.py script...\n")
        # Define variables from parameters
        working_folder = parameters[0]
        gdbName = parameters[1]

        coord_sys = arcpy.SpatialReference("NAD 1983 Canada Atlas Lambert")
        logging.info("Spatial Reference set: NAD 1983 Canada Atlas Lambert")

        # Create file GDB and define path
        arcpy.CreateFileGDB_management(working_folder, gdbName, "CURRENT")
        logging.info("Create File GDB: '%s' created in %s", gdbName, working_folder)
        file_GDB = os.path.join(working_folder, gdbName) + ".gdb"

        # Create dark features dataset
        arcpy.AddMessage("Creating Dark Features Dataset...")
        dark_featDSstring = "dark_features"
        arcpy.CreateFeatureDataset_management(file_GDB, dark_featDSstring, coord_sys)
        logging.info("Create Feature Dataset: '%s' created in %s", dark_featDSstring, file_GDB)
        feat_DS = os.path.join(file_GDB, dark_featDSstring)

        # Create features union dataset
        arcpy.AddMessage("Creating Union Dataset...")
        unionDSstring = "feature_union"
        arcpy.CreateFeatureDataset_management(file_GDB, unionDSstring, coord_sys)
        logging.info("Create Feature Dataset: '%s' created in %s", unionDSstring, file_GDB)
        union_DS = os.path.join(file_GDB, unionDSstring)

        # Create features overlap dataset
        arcpy.AddMessage("Creating Overlap Dataset...")
        overlapDSstring = "feature_overlap"
        arcpy.CreateFeatureDataset_management(file_GDB, overlapDSstring, coord_sys)
        logging.info("Create Feature Dataset: '%s' created in %s", overlapDSstring, file_GDB)
        overlap_DS = os.path.join(file_GDB, overlapDSstring)
        logging.info("createGDBStruct.py script finished\n\n")

        return feat_DS, union_DS, overlap_DS, file_GDB