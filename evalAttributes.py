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
executed after "parseNoOverlap.py" and is followed by "mergeAreas.py".

SUMMARY
Evaluates the overlapping polygons that contain two sets of attributes, in order
to select which single set of attributes to be applied to that overlapping region.
This is determined by a selection criteria comparing values of one set of attributes
to the other.

INPUT
- Total Overlap Feature Classes (automated input): Feature classes containing all
overlapping polygons with two sets of attributes.

- Attribute Evaluation Criteria (automated input, taken from user input for
'condition_darkTargets.py'): SQL expression which is used to determine
which set of attributes is selected and applied in those regions of overlapping
dark targets which contains two sets of attributes.

OUTPUT
- toMerge Feature Classes (automated output): Output feature classes resulting
from the Merge of the selection of polygons meeting the attribute evaluation
criteria for the first set of attributes and the selection of the second set of
attributes for the polygons that do not meet the attribute evaluation criteria.
This has the effect of merging the original polygon geometries with a single set
 of attributes for each polygon. These feature classes are used in the final
 merge conditioning step where each acquisition day is merged together as a single
 feature class."""

# Libraries
# =========
import arcpy
import os
import logging


class evalAttributes(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "evalAttributes"
        self.description = "Evaluates which set of attributes to preserve for \
        those regions of overlapping dark targets, determined by user criteria."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [None]*2

        params[0] = arcpy.Parameter(
            displayName="Overlap Dataset",
            name="overlapWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        params[1] = arcpy.Parameter(
            displayName="Overlapping Attribute Evaluation Criteria",
            name="attrSQL",
            datatype="GPSQLExpression",
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
        arcpy.AddMessage("\nEvaluating overlapping attributes...")
        logging.info("Starting evalAttributes.py script...\n")
        # Define variables from parameters
        overlapWorkspace = parameters[0].valueAsText
        where_clause = parameters[1].valueAsText

        # Determine list of total overlap feature classes to process
        arcpy.env.workspace = overlapWorkspace
        overlapList = arcpy.ListFeatureClasses("*_TotalOverlap")

        # Check for presence of total overlap feature classes
        if len(overlapList) > 0:
            arcpy.AddMessage("Workspace contains the following " + str(len(overlapList)) + " total overlap feature classes: " + str(overlapList))

            # Iterate through total overlap feature classes
            for fc in overlapList:
                arcpy.AddMessage("\nProcessing " + fc)
                logging.info("Processing '%s' feature class", fc)

                # Create feature layer to apply evaluation criteria selection
                arcpy.MakeFeatureLayer_management(fc, "fc_lyr")
                logging.info("Make Feature Layer: 'fc_lyr' layer created from '%s' feature class", fc)
                arcpy.AddMessage("Evaluating overlapping attributes...")

                # Apply selection for values on first set of attributes (left side columns) and copy results to an output feature class
                arcpy.SelectLayerByAttribute_management("fc_lyr", "NEW_SELECTION", where_clause)
                logging.info("Select Layer by Attribute: Features from 'fc_lyr' selected, meeting the following evaluation criteria: '%s'", where_clause)
                selectOutputString = fc + "_Select"
                selectOutput = os.path.join(overlapWorkspace, selectOutputString)
                arcpy.CopyFeatures_management("fc_lyr", selectOutput)
                logging.info("Copy Features: '%s' feature class created from 'fc_lyr' selection", selectOutput)

                # Apply inverted selection for values on second set of attributes (right side columns) and copy results to an output feature class
                arcpy.SelectLayerByAttribute_management("fc_lyr", "SWITCH_SELECTION")
                logging.info("Select Layer By Attribute: Selection switched on 'fc_lyr'")
                selectOutputString_1 = fc + "_Select_1"
                selectOutput_1 = os.path.join(overlapWorkspace, selectOutputString_1)
                arcpy.CopyFeatures_management("fc_lyr", selectOutput_1)
                logging.info("Copy Features: '%s' feature class created from switched 'fc_lyr' selection", selectOutput_1)

                # Delete and rename extra fields to prepare selection output feature classes for merge back to single set of attributes
                arcpy.AddMessage("Deleting extra attribute fields...")
                fieldList = arcpy.ListFields(selectOutput)
                for field in fieldList:
                    if field.name.endswith("_1"):
                        arcpy.DeleteField_management(selectOutput, field.name)
                fieldList_1 = arcpy.ListFields(selectOutput_1)
                noDeleteField = ["OBJECTID","Shape","targetID","Shape_Length","Shape_Area"]
                for field in fieldList_1:
                    if field.name.endswith("_1"):
                        arcpy.AlterField_management(selectOutput_1, field.name, field.name[:-2])
                    if field.name in noDeleteField:
                        continue
                    else:
                        arcpy.DeleteField_management(selectOutput_1, field.name)

                # Merge selection output feature classes into single feature class for subsequent merging with remainder of acquisition swathe
                arcpy.AddMessage("Merging results together into single toMerge feature class...")
                fcName = fc.strip("_TotalOverlap")
                mergeList = [selectOutput, selectOutput_1]
                mergeString = fcName + "_toMerge"
                mergeOutput = os.path.join(overlapWorkspace, mergeString)
                arcpy.Merge_management(mergeList, mergeOutput)
                logging.info("Merge: '%s' created from merging the following feature classes: '%s'", mergeOutput, str(mergeList))

                logging.info("Processing for '%s' feature class complete\n", fc)

        else:
            arcpy.AddMessage("No overlapping feature classes found in workspace. Evaluation of attributes not required!")

        logging.info("evalAttributes.py script finished\n\n")

        return