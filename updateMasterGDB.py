#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 31 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used as the "2_Populate Master GDB" script tool in the
"GEM2_Oil_Seep_Detection_Analysis" Python Toolbox.

SUMMARY
Consolidates the yearly dark targets data which has been previously
conditioned by the "1_Condition Yearly Dark Targets Data" script tool, placing
them in the GEM2 Data Master GDB.

INPUT
- Folder Location of Dark Targets GDBs (user input): Folder containing the geodatabases
produced by "1_Condition Yearly Dark Targets Data". The script will iterate through
the geodatabases and copy the feature classes that are not already present into
the master geodatabase.

- Location of GEM2 Data Master GDB (user input): Master geodatabase which will
consolidate the entire collection of acquisition day feature classes, organized
by year within feature datasets. This master geodatabase must manually be created
before running this tool, as the creation is not automated.

OUTPUT
- Acquisition day feature classes (automated output): Feature classes that are copied
from the yearly dark targets geodatabases to the master geodatabase."""

# Libraries
# =========
import arcpy
import os
import logging


class updateMasterGDB(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2_Populate Master GDB"
        self.description = "Consolidates the contents of the yearly dark targets\
         GDBs into the master GDB for follow-on analysis."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params0 = arcpy.Parameter(
            displayName="Input: Folder Location of Dark Targets GDBs",
            name="working_folder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input")

        params1 = arcpy.Parameter(
            displayName="Output: GEM2 Data Master GDB",
            name="masterGDB",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        params = [params0, params1]

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
        # Set log configuration
        logPath = os.path.join(os.path.dirname(parameters[1].valueAsText), "logs")
        if not os.path.exists(logPath):
            os.makedirs(logPath)
        logFile = os.path.join(logPath, "popGDB.log")
        logging.basicConfig(filename=logFile, format='%(asctime)s -- %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)
        logging.info("Starting updateMasterGDB.py script...\n")
        arcpy.AddMessage("\nUpdating Master GDB...")

        # Define variables from parameters
        working_folder = parameters[0].valueAsText
        masterGDB = parameters[1].valueAsText

        coord_sys = arcpy.SpatialReference("NAD 1983 Canada Atlas Lambert")
        logging.info("Spatial Reference set: NAD 1983 Canada Atlas Lambert")

        # Determine list of yearly GDBs in workspace
        arcpy.env.workspace = working_folder
        gdbList = arcpy.ListWorkspaces("*", "FileGDB")
        arcpy.AddMessage("Workspace contains the following " + str(len(gdbList)) + " GDBs: " + str(gdbList))

        # Determine contents of master GDB
        arcpy.env.workspace = masterGDB
        masterGDBList = arcpy.ListDatasets()
        arcpy.AddMessage("\nMaster GDB contains the following " + str(len(masterGDBList)) + " feature datasets: " + str(masterGDBList))

        # Iterate through yearly GDBs to copy feature classes to master GDB
        for gdb in gdbList:
            arcpy.AddMessage("\nProcessing " + str(gdb))
            logging.info("Processing '%s' geodatabase\n", gdb)

            # Determine feature dataset name and create if doesn't exist
            gdbDesc = arcpy.Describe(gdb)
            dsName = "dt_" + gdbDesc.baseName
            if dsName not in masterGDBList:
                arcpy.AddMessage("Dataset does not exist. Creating " + dsName + "...")
                arcpy.CreateFeatureDataset_management(masterGDB, dsName, coord_sys)
                logging.info("Create Feature Dataset: '%s' Feature Dataset created in '%s' geodatabase\n", dsName, masterGDB)

            # Determine list of feature classes in current yearly GDB
            arcpy.env.workspace = gdb
            fcList = arcpy.ListFeatureClasses()

            # Determine list of feature classes in corresponding dataset in master GDB
            dsWorkspace = os.path.join(masterGDB, dsName)
            arcpy.env.workspace = dsWorkspace
            masterFcList = arcpy.ListFeatureClasses()

            # Iterate through feature classes in current yearly GDB
            for fc in fcList:
                arcpy.AddMessage("Verifying for feature class " + fc + "...")
                logging.info("Processing '%s' feature class", fc)
                in_fc = os.path.join(gdb, fc)

                # Copy feature class to master GDB if doesn't exist
                if fc not in masterFcList:
                    arcpy.AddMessage("Feature class does not exist. Copying " + fc + "...")
                    arcpy.FeatureClassToGeodatabase_conversion(in_fc, dsWorkspace)
                    logging.info("Feature Class to Geodatabase: '%s' feature class copied to master GDB", fc)
                else:
                    arcpy.AddMessage("Feature class already present in master GDB. Continuing...")
                    logging.info("'%s' feature class already present in master GDB", fc)
                logging.info("Processing for '%s' feature class complete\n", fc)

            logging.info("Processing for '%s' geodatabase complete\n", gdb)

        logging.info("updateMasterGDB.py script finished\n\n")
        return