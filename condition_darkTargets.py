#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 28 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used as the "1_Condition Yearly Dark Targets Data" script
tool in the "GEM2_Oil_Seep_Detection_Analysis" Python Toolbox.

SUMMARY
Imports and conditions dark targets shapefiles produced by the target feature
extraction process on RADARSAT-2 imagery. Organizes data as feature classes
in a file geodatabase by acquisition day.

INPUT
- Year Folder (user input): Folder containing the desired year's shapefiles produced by the
RADARSAT-2 dark target feature extraction process. File structure must meet the
agreed upon hierarchy in order for the script to find the shapefiles in the
appropriate locations. (shapefiles are located within the "Features" folder,
which are in turn located in its specific radar acquisition folder)

- Attribute Evaluation Criteria (user input): SQL expression which is used to determine
which set of attributes is selected and applied in those regions of overlapping
dark targets which contains two sets of attributes. A default value is entered,
however the parameter can be customized.

OUTPUT
- Yearly Data File Geodatabase (automated output): A file geodatabase is
produced in the same folder of the input year folder and is also named the same
as the input year folder. (e.g. 2010.gdb) The FGDB contains the feature classes
of all the dark targets per acquisition day, as well as the working files used
in the conditioning, which are placed in the "dark_features", "feature_overlap"
and "feature_union" feature datasets."""

# Libraries
# =========
import arcpy
import os
import logging

# Reload steps required to refresh memory if Catalog is open when changes are made
import createGDBStruct                      # get module reference for reload
reload(createGDBStruct)                     # reload step 1
from createGDBStruct import createGDBStruct # reload step 2

import loadDarkTargets                      # get module reference for reload
reload(loadDarkTargets)                     # reload step 1
from loadDarkTargets import loadDarkTargets # reload step 2

import parseOverlap                         # get module reference for reload
reload(parseOverlap)                        # reload step 1
from parseOverlap import parseOverlap       # reload step 2

import parseNoOverlap                       # get module reference for reload
reload(parseNoOverlap)                      # reload step 1
from parseNoOverlap import parseNoOverlap   # reload step 2

import evalAttributes                       # get module reference for reload
reload(evalAttributes)                      # reload step 1
from evalAttributes import evalAttributes   # reload step 2

import mergeAreas                           # get module reference for reload
reload(mergeAreas)                          # reload step 1
from mergeAreas import mergeAreas           # reload step 2


class condition_darkTargets(object):
    """
    Calls on a series of scripts to import the shapefiles produced by the
    dark targets feature extraction process. Conditions the data into one
    feature class per acquisition day, organized by year in feature
    datasets.
    """
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1_Condition Yearly Dark Targets Data"
        self.description = "Imports dark target shapefiles produced from a \
        specific year's radar acquisition imagery. The data is conditioned for \
        subsequent analysis and exported into a file geodatabase."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        params0 = arcpy.Parameter(
            displayName="Input: Year Folder",
            name="year_workspace",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input")

        params1 = arcpy.Parameter(
            displayName="Dark Features Dataset",
            name="dark_featDS",
            datatype="DEFeatureDataset",
            parameterType="Derived",
            direction="Output")

        params2 = arcpy.Parameter(
            displayName="Union Dataset",
            name="unionDS",
            datatype="DEFeatureDataset",
            parameterType="Derived",
            direction="Output")

        params3 = arcpy.Parameter(
            displayName="Overlap Dataset",
            name="overlapDS",
            datatype="DEFeatureDataset",
            parameterType="Derived",
            direction="Output")

        params4 = arcpy.Parameter(
            displayName="GDB Workspace",
            name="gdbWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Derived",
            direction="Output")

        params5 = arcpy.Parameter(
            displayName="Input: Attribute Evaluation Criteria",
            name="attrEvalSQL",
            datatype="GPSQLExpression",
            parameterType="Required",
            direction="Input")

        params5.value = "PcontrDb < PcontrDb_1"

        params = [params0, params1, params2, params3, params4, params5]

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
        logPath = os.path.join(os.path.dirname(parameters[0].valueAsText), "logs")
        if not os.path.exists(logPath):
            os.makedirs(logPath)
        logFile = os.path.join(logPath, "conditionData.log")
        logging.basicConfig(filename=logFile, format='%(asctime)s -- %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)
        logging.info("Starting condition_darkTargets.py script...\n")

        # ========================= #
        # Create File GDB Structure #
        # ========================= #

        createGDB = createGDBStruct()
        createGDBparams = createGDB.getParameterInfo()
        # Define products folder value (parent directory to year folder)
        createGDBparams[0] = os.path.dirname(parameters[0].valueAsText)
        # Define File GDB name value (based on year folder being processed)
        createGDBparams[1] = os.path.basename(parameters[0].valueAsText)
        # Execute Create File GDB script
        feat_DS, union_DS, overlap_DS, gdbWorkspace = createGDB.execute(createGDBparams, None)
        # Assign return dataset values to output parameters
        arcpy.SetParameterAsText(1, feat_DS)
        arcpy.SetParameterAsText(2, union_DS)
        arcpy.SetParameterAsText(3, overlap_DS)
        arcpy.SetParameterAsText(4, gdbWorkspace)

        # ============================ #
        # Load Dark Targets shapefiles #
        # ============================ #

        loadSHP = loadDarkTargets()
        loadSHPparams = loadSHP.getParameterInfo()
        # Define year workspace folder value
        loadSHPparams[0] = parameters[0]
        # Define dark features dataset value
        loadSHPparams[1] = parameters[1]
        # Execute Load Dark Targets script
        loadSHP.execute(loadSHPparams, None)

        # ========================= #
        # Parse overlapping targets #
        # ========================= #

        parseTargetOverlap = parseOverlap()
        parseTargetOverlapParams = parseTargetOverlap.getParameterInfo()
        # Define dark features dataset value
        parseTargetOverlapParams[0] = parameters[1]
        # Define features union dataset value
        parseTargetOverlapParams[1] = parameters[2]
        # Define features overlap dataset value
        parseTargetOverlapParams[2] = parameters[3]
        # Execute Parse Overlap script
        parseTargetOverlap.execute(parseTargetOverlapParams, None)

        # =========================================== #
        # Parse regions of targets that do no overlap #
        # =========================================== #

        parseTargetNoOverlap = parseNoOverlap()
        parseTargetNoOverlapParams = parseTargetNoOverlap.getParameterInfo()
        # Define dark features dataset value
        parseTargetNoOverlapParams[0] = parameters[1]
        # Define features overlap dataset value
        parseTargetNoOverlapParams[1] = parameters[3]
        # Execute Parse No Overlap script
        parseTargetNoOverlap.execute(parseTargetNoOverlapParams, None)

        # =============================== #
        # Evaluate conflicting attributes #
        # =============================== #

        evalAttr = evalAttributes()
        evalAttrParams = evalAttr.getParameterInfo()
        # Define features overlap dataset value
        evalAttrParams[0] = parameters[3]
        # Define attribute selection criteria value
        evalAttrParams[1] = parameters[5]
        # Execute Evaluate Attributes script
        evalAttr.execute(evalAttrParams, None)

        # =============================== #
        # Merge areas and finalize output #
        # =============================== #

        mergeTargetAreas = mergeAreas()
        mergeTargetsAreasParams = mergeTargetAreas.getParameterInfo()
        # Define features overlap dataset value
        mergeTargetsAreasParams[0] = parameters[3]
        # Define GDB workspace value
        mergeTargetsAreasParams[1] = parameters[4]
        # Define dark features dataset value
        mergeTargetsAreasParams[2] = parameters[1]
        #Execute Merge Areas script
        mergeTargetAreas.execute(mergeTargetsAreasParams, None)

        logging.info("condition_darkTargets.py script finished.\n\n")

        return