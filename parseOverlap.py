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
executed after "loadDarkTargets.py" and is followed by "parseNoOverlap.py".

SUMMARY
Isolates regions of overlapping polygons within an acquisition swathe and
preserves both sets of attribute values by executing the Union tool.

INPUT
- Dark Targets Feature Classes (automated input): Feature classes previously
converted from the input shapefiles by the "loadDarkTargets.py" script.

- Union Dataset (automated input): Feature dataset in the output file
geodatabase in which the results of the Union geoprocessing are output.

- Overlap Dataset (automated input): Feature dataset in the output file
geodatabase in which the overlap geoprocessing and results are stored.

OUTPUT
- Union Feature Classes (automated output): Output feature classes resulting
from the Union from those input Dark Targets feature classes that have
overlapping polygons. As a result of the Union geoprocessing, new polygons with
two sets of attributes are created for those regions of overlap. These feature
classes are stored in the "features_union" feature dataset.

- Overlap Feature Classes (automated output): Output feature classes containing
overlapping polygons from two adjacent image acquisitions. These feature classes
are created by selecting and exporting those polygons with two sets of attribute
values from a Union feature class. These feature classes are stored in the
"features_overlap" feature dataset.

- Total Overlap Feature Classes (automated output): Output feature classes
containing all Overlap Feature Classes merged from a single acquisition day.
These feature classes are stored in the "features_overlap" dataset."""

# Libraries
# =========
import arcpy
import os
import logging


class parseOverlap(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "parseOverlap"
        self.description = "Isolates overlapping polygons within an acquisition\
         swathe and executes Union on affected feature classes to isolate \
         regions of overlap and preserve both sets of attribute values."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [None]*3

        params[0] = arcpy.Parameter(
            displayName="Dark Features Dataset",
            name="dark_featDS",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Input")

        params[1] = arcpy.Parameter(
            displayName="Union Dataset",
            name="unionDS",
            datatype="DEFeatureDataset",
            parameterType="Required",
            direction="Input")

        params[2] = arcpy.Parameter(
            displayName="Overlap Dataset",
            name="overlapDS",
            datatype="DEFeatureDataset",
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
        arcpy.AddMessage("\nParsing overlapping targets...")
        logging.info("Starting parseOverlap.py script...\n")
        # Define variables from parameters
        featWorkspace = parameters[0].valueAsText
        unionWorkspace = parameters[1].valueAsText
        overlapWorkspace = parameters[2].valueAsText

        # Initialize noUnion list (to contain pairs of feature classes that no longer require Union)
        noUnion = []

        # Determine list of feature classes in dark_features dataset
        arcpy.env.workspace = featWorkspace
        fcList = arcpy.ListFeatureClasses()
        arcpy.AddMessage("Workspace contains the following " + str(len(fcList)) + " feature classes: " + str(fcList))

        # Organize dark targets feature classes by date
        fcDictByDate = {}
        for fc in fcList:
            fcSplit = fc.split("_")
            if fcSplit[1] in fcDictByDate:
                fcDictByDate[fcSplit[1]].append(fc)
            else:
                fcDictByDate[fcSplit[1]] = [fc]

        # Iterate through dark targets acquisition dates
        for key in fcDictByDate:
            arcpy.env.workspace = featWorkspace

            # Iterate through feature classes within acquisition date
            for fc in fcDictByDate[key]:
                arcpy.AddMessage("\nProcessing " + fc)
                logging.info("Processing '%s' feature class", fc)

                # Check for multiple dark targets feature classes within acquisition date
                if len(fcDictByDate[key]) == 1:
                    arcpy.AddMessage("Only one feature class for this date, no Union necessary!")
                else:
                    # Create feature layer from feature class for subsequent geoprocessing
                    arcpy.MakeFeatureLayer_management(fc,'fc_lyr')
                    logging.info("Make Feature Layer: 'fc_lyr' layer created from '%s' feature class", fc)

                    # Second iteration through feature classes for pairing within acquisition date
                    for fc2 in fcDictByDate[key]:
                        # Check to skip pairing of same dark targets feature class
                        if fc2 != fc:
                            # Compare paired feature classes to detect spatial intersection of dark targets
                            arcpy.SelectLayerByLocation_management('fc_lyr','intersect',fc2)
                            logging.info("Select Layer by Location: Selected features from 'fc_lyr' which intersect with '%s'", fc2)
                            selectioncount = int(arcpy.GetCount_management('fc_lyr')[0])
                            logging.info("Get Count: Counted '%d' features in selection from 'fc_lyr'", selectioncount)
                            arcpy.AddMessage(str(selectioncount) + " features intersect between " + fc + " and " + fc2)

                            # Check selection count (at least 1 selection) to detect overlap between paired feature classes
                            if selectioncount != 0:
                                # Check noUnion list to determine if paired feature classes have already performed Union on a previous iteration
                                if fc2 in noUnion:
                                    arcpy.AddMessage("Already performed Union for these feature classes!")
                                else:
                                    # Perform Union on paired feature classes
                                    arcpy.AddMessage("Performing Union for " + fc + " and " + fc2)
                                    unionOutputString = fc + "_" + fc2 + "_Union"
                                    unionOutput = os.path.join(unionWorkspace, unionOutputString)
                                    arcpy.Union_analysis([fc, fc2], unionOutput)
                                    logging.info("Union: Created '%s' feature class from union of '%s' and '%s' feature classes", unionOutput, fc, fc2)

                                    # Append overlapping paired feature class to noUnion list to skip on subsequent iterations
                                    noUnion.append(fc)

                                    # Select polygons in Union feature class that have two sets of attribute values (overlapping regions of dark targets)
                                    selectOutputString = fc + "_" + fc2 + "_Select"
                                    selectOutput = os.path.join(overlapWorkspace, selectOutputString)
                                    where_clause = 'NOT FID_' + fc + ' = -1 AND NOT FID_' + fc2 + ' = -1'
                                    arcpy.Select_analysis(unionOutput, selectOutput, where_clause)
                                    logging.info("Select: '%s' feature class created from '%s' selection", selectOutput, unionOutput)

                                    # Dissolve selected polygons to remove attribute value duplicates
                                    arcpy.AddMessage("Dissolving " + selectOutputString)
                                    selectLayer = "selectLyr"
                                    overlapOutputString = fc + "_" + fc2 + "_Overlap"
                                    overlapOutput = os.path.join(overlapWorkspace, overlapOutputString)
                                    dissolveFields = ["Pid", "Pid_1"]
                                    fieldList = arcpy.ListFields(selectOutput)
                                    statsFields = []
                                    for field in fieldList:
                                        if "OBJECTID" in field.name or "FID" in field.name or "Shape" in field.name or "Pid" in field.name or "targetID_1" in field.name:
                                            continue
                                        statsField = [field.name,"FIRST"]
                                        statsFields.append(statsField)
                                    arcpy.MakeFeatureLayer_management(selectOutput, selectLayer)
                                    logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", selectLayer, selectOutput)
                                    arcpy.Dissolve_management(selectLayer, overlapOutput, dissolveFields, statsFields)
                                    logging.info("Dissolve: '%s' feature class created from '%s' layer dissolve", overlapOutput, selectLayer)

                                    # Delete selection output feature class
                                    arcpy.Delete_management(selectOutput)
                                    logging.info("Delete: '%s' feature class deleted", selectOutput)

                                    # Rename attribute fields to revert to original field names
                                    arcpy.AddMessage("Renaming attribute fields...")
                                    fieldList = arcpy.ListFields(overlapOutput)
                                    for field in fieldList:
                                        if field.name.startswith("FIRST_"):
                                            newName = field.name[6:]
                                            arcpy.AlterField_management(overlapOutput, field.name, newName)

                                    # Modify and update targetID of overlapping dark targets to a common targetID for overlapping targets
                                    expression = "calcTargetID(str(!Pid!)[:-2],str(!Pid_1!)[:-2],!RsatID!,!RsatID_1!)"
                                    codeblock = """def calcTargetID(pid,pid1,rsat,rsat1):
                                        rsatSplit = rsat.split('_')
                                        rsatSplit1 = rsat1.split('_')
                                        date = rsatSplit[5] + '_' + rsatSplit[6] + '_' + rsatSplit1[6]
                                        targetID = pid + '_' + pid1 + '_' + date
                                        return targetID"""
                                    arcpy.CalculateField_management(overlapOutput, "targetID", expression, "PYTHON_9.3", codeblock)
                                    logging.info("Calculate Field: 'targetID' field value calculated for '%s' feature class", overlapOutput)

                logging.info("Processing for '%s' feature class complete\n", fc)

            # Merge all overlap feature classes from the acquisition swathe into a single total overlap feature class
            arcpy.env.workspace = overlapWorkspace
            overlapList = arcpy.ListFeatureClasses("*_Overlap")
            currentOverlap = []
            for overlapFC in overlapList:
                if overlapFC.split("_")[1] == key:
                    currentOverlap.append(overlapFC)
            if len(currentOverlap) > 0:
                arcpy.AddMessage("\nWorkspace contains the following " + str(len(currentOverlap)) + " Overlap feature classes: " + str(currentOverlap))
                overlapStringOutput = "RS2_" + currentOverlap[0].split("_")[1] + "_TotalOverlap"
                arcpy.Merge_management(currentOverlap, overlapStringOutput)
                logging.info("Merge: '%s' created from merging the following feature classes: '%s'\n", overlapStringOutput, str(currentOverlap))
                arcpy.AddMessage("Workspace contents merged")

        logging.info("parseOverlap.py script finished\n\n")

        return