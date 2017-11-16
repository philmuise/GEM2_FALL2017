#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 31 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used as part of the condition_darkTargets.py script. It is
executed after "parseOverlap.py" and is followed by "evalAttributes.py".

SUMMARY
Isolates regions of from overlapping polygons that were not overlapping within
an acquisition swathe.

INPUT
- Dark Targets Feature Classes (automated input): Feature classes previously
converted from the input shapefiles by the "loadDarkTargets.py" script.

- Total Overlap Feature Classes (automated input): Feature classes containing all
overlapping polygons with two sets of attributes.

OUTPUT
- noOverlap Feature Classes (automated output): Output feature classes resulting
from the Erase tool performed on the Dark Targets feature classes with the
corresponding Total Overlap feature classes. These noOverlap feature classes are
used in the final step of the conditioning process when merging every polygon
from an acquisition swathe together in the same feature class."""

# Libraries
# =========
import arcpy
import os
import logging


class parseNoOverlap(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "parseNoOverlap"
        self.description = "Isolates regions that do not overlap within an \
        acquisition swathe, determined by performing Erase on each feature \
        class with its corresponding total overlap feature class."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [None]*2

        params[0] = arcpy.Parameter(
            displayName="Dark Features Dataset",
            name="dark_featWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        params[1] = arcpy.Parameter(
            displayName="Overlap Dataset",
            name="overlapWorkspace",
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
        arcpy.AddMessage("\nParsing targets that do not overlap...")
        logging.info("Starting parseNoOverlap.py script...\n")
        # Define variables from parameters
        featWorkspace = parameters[0].valueAsText
        overlapWorkspace = parameters[1].valueAsText

        # Determine list of total overlap feature classes to process
        arcpy.env.workspace = overlapWorkspace
        totalOverlapList = arcpy.ListFeatureClasses("*_TotalOverlap")

        # Check for presence of total overlap feature classes
        if len(totalOverlapList) > 0:
            arcpy.AddMessage("Workspace contains the following " + str(len(totalOverlapList)) + " total overlap feature classes: " + str(totalOverlapList))

            # Organize dark targets feature classes by date
            arcpy.env.workspace = featWorkspace
            fcList = arcpy.ListFeatureClasses()
            fcDictByDate = {}
            for fc in fcList:
                fcSplit = fc.split("_")
                if fcSplit[1] in fcDictByDate:
                    fcDictByDate[fcSplit[1]].append(fc)
                else:
                    fcDictByDate[fcSplit[1]] = [fc]

            # Iterate through dark targets acquisition dates
            for key in fcDictByDate:
                # Check for dates which contain more than one feature class (for possible overlaps within the acquisition day)
                if len(fcDictByDate[key]) > 1:

                    # Iterate through feature classes within acquisition date
                    for fc in fcDictByDate[key]:
                        arcpy.AddMessage("\nProcessing " + fc)
                        logging.info("Processing '%s' feature class", fc)
                        overlapFC = ''
                        arcpy.env.workspace = overlapWorkspace

                        # For each feature class, iterate through total overlap feature classes to check for acquisition day match
                        for totalOverlapFC in totalOverlapList:
                            # Define total overlap feature class to use for Erase
                            if totalOverlapFC.split("_")[1] == key:
                                overlapFC = os.path.join(overlapWorkspace, totalOverlapFC)

                        # Check for total overlap feature class match and perform Erase to isolate dark target regions that do not overlap
                        if overlapFC != '':
                            eraseOutputString = fc + "_noOverlap"
                            eraseOutput = os.path.join(overlapWorkspace, eraseOutputString)
                            arcpy.AddMessage("Erasing regions of overlap...")
                            arcpy.env.workspace = featWorkspace
                            arcpy.Erase_analysis(fc, overlapFC, eraseOutput)
                            logging.info("Erase: '%s' feature class created from remaining portions of '%s' feature class that have been erased by '%s' feature class.", eraseOutput, fc, overlapFC)
                        else:
                            arcpy.AddMessage("No overlapping regions to erase for " + fc)
                        logging.info("Processing for '%s' feature class complete\n", fc)

        else:
            arcpy.AddMessage("Workspace contains no overlapping features classes!")

        logging.info("parseNoOverlap.py script finished\n\n")

        return