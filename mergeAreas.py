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
executed after "evalAttributes.py" and is the final script executed as part of the
condition_darkTargets.py script.

SUMMARY
Merges the polygons

INPUT
- Total Overlap Feature Classes (automated input): Feature classes containing all
overlapping polygons with two sets of attributes. Provided as input in order to
access the combined targetID and assign it to the corresponding polygons in the
final output feature class.

- noOverlap Feature Classes (automated output): Feature classes containing all
regions from overlapping polygons that already had a single set of attributes.

- toMerge Feature Classes (automated output): Feature classes containing all
overlapping regions that have been evaluated with a single set of attributes.

OUTPUT
- Acquisition day Feature Classes (automated output): Output feature classes
resulting from the Merge of the toMerge and noOverlap feature classes for each
acquisition day. The Total Overlap feature class is used to pull the combined
targetID value and apply it to this feature class. These feature classes are
placed in the Yearly Dark Targets geodatabase for the specified year."""

# Libraries
# =========
import arcpy
import os
import logging


class mergeAreas(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "mergeAreas"
        self.description = "Merges dark targets feature classes into single \
        acquisition swathes by day."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        params = [None]*3

        params[0] = arcpy.Parameter(
            displayName="Overlap Dataset",
            name="overlapWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        params[1] = arcpy.Parameter(
            displayName="GDB Workspace",
            name="gdbWorkspace",
            datatype=["DEWorkspace", "DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        params[2] = arcpy.Parameter(
            displayName="Dark Features Dataset",
            name="dark_featWorkspace",
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
        arcpy.AddMessage("\nPerforming overall merge...")
        logging.info("Starting mergeAreas.py script...\n")
        # Define variables from parameters
        overlapWorkspace = parameters[0].valueAsText
        gdbWorkspace = parameters[1].valueAsText
        featWorkspace = parameters[2].valueAsText

        # Determine list of total overlap, no overlap and to merge feature classes in overlap feature dataset workspace to process.
        arcpy.env.workspace = overlapWorkspace
        mergeList = arcpy.ListFeatureClasses("*_toMerge")
        totalOverlapList = arcpy.ListFeatureClasses("*_TotalOverlap")
        noOverlapList = arcpy.ListFeatureClasses("*_noOverlap")
        if len(mergeList) > 0:
            arcpy.AddMessage("Workspace contains the following " + str(len(mergeList)) + " feature classes to merge: " + str(mergeList))

        # Organize toMerge feature classes by date
        mergeDictbyDate = {}
        for fc in mergeList:
            fcPath = os.path.join(overlapWorkspace, fc)
            fcDate = fc.split("_")[1]
            mergeDictbyDate[fcDate] = [fcPath]

        # Append no overlap feature classes toMerge feature classes by date
        for noOverlapFc in noOverlapList:
            noOverlapPath = os.path.join(overlapWorkspace, noOverlapFc)
            noOverlapDate = noOverlapFc.split("_")[1]
            mergeDictbyDate[noOverlapDate].append(noOverlapPath)

        # Organize dark targets feature classes by date
        arcpy.env.workspace = featWorkspace
        fcList = arcpy.ListFeatureClasses()
        fcDictByDate = {}
        for fc in fcList:
            fcPath = os.path.join(featWorkspace, fc)
            fcSplit = fc.split("_")
            if fcSplit[1] in fcDictByDate:
                fcDictByDate[fcSplit[1]].append(fcPath)
            else:
                fcDictByDate[fcSplit[1]] = [fcPath]

        # Iterate through dark targets acquisition dates and check for acquisition dates with more than a single feature class (for merging)
        for key in fcDictByDate:
            if len(fcDictByDate[key]) > 1:

                # Iterate through feature classes within acquisition date
                for fc in fcDictByDate[key]:
                    fcSplit = fc.split("_")

                    # Check for and add acquisition date toMerge feature classes if not already present
                    if fcSplit[len(fcSplit)-2] not in mergeDictbyDate:
                        mergeDictbyDate[fcSplit[len(fcSplit)-2]] = [fc]

                    # Check for and add feature class toMerge feature classes if not already present within acquisition date
                    else:
                        fcValue = fc.split("\\")[len(fc.split("\\"))-1] + "_noOverlap"
                        fcValuePath = os.path.join(overlapWorkspace,  fcValue)
                        if fcValuePath not in mergeDictbyDate[key]:
                            mergeDictbyDate[key].append(fc)

        # Iterate through dark targets acquisition dates to compile lists of feature classes to merge
        for key in mergeDictbyDate:
            arcpy.AddMessage("\nMerging feature classes in " + key + "...")
            logging.info("Processing merges for acquisition date '%s'", key)
            mergeList = []

            # Iterate through feature classes within acquisition date and append them to merge list
            for item in mergeDictbyDate[key]:
                mergeList.append(item)

            # Merge feature classes in merge list into single feature class for the acquisition date
            outputDissolveString = "RS2_" + key + "_toDissolve"
            outputDissolve = os.path.join(overlapWorkspace, outputDissolveString)
            arcpy.Merge_management(mergeList, outputDissolve)
            logging.info("Merge: '%s' created from merging the following feature classes: '%s'", outputDissolve, str(mergeList))

            # Dissolve attribute duplicates and rename fields
            arcpy.AddMessage("Dissolving...")
            dissolveLyr = "dissolveLyr"
            outputMergeString = "RS2_" + key + "_merged"
            outputMerge = os.path.join(gdbWorkspace, outputMergeString)
            dissolveFields = ["Pid", "RsatID"]
            fieldList = arcpy.ListFields(outputDissolve)
            statsFields = []
            for field in fieldList:
                if "OBJECTID" in field.name or "FID" in field.name or "Shape" in field.name or field.name in dissolveFields or field.name == "ID":
                    continue
                statsField = [field.name,"FIRST"]
                statsFields.append(statsField)
            arcpy.MakeFeatureLayer_management(outputDissolve, dissolveLyr)
            logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", dissolveLyr, outputDissolve)
            arcpy.Dissolve_management(dissolveLyr, outputMerge, dissolveFields, statsFields)
            logging.info("Dissolve: '%s' feature class created from '%s' layer dissolve", outputMerge, dissolveLyr)
            fieldList = arcpy.ListFields(outputMerge)
            for field in fieldList:
                if field.name.startswith("FIRST_"):
                    newName = field.name[6:]
                    arcpy.AlterField_management(outputMerge, field.name, newName)

            # Update targetID with combined target ID for overlapping features
            arcpy.AddMessage("Updating targetID...")
            finalOutputString = "RS2_" + key
            overlapBool = False

            # Iterate through total overlap feature classes
            for fc in totalOverlapList:

                # Check for merged acquisition date feature class containing overlapping features (by finding equivalent total overlap feature class)
                if finalOutputString == fc.strip("_TotalOverlap"):
                    overlapBool = True

                    # Perform spatial join to access targetID field from total overlap feature class
                    totalOverlapFc = os.path.join(overlapWorkspace, fc)
                    finalOutput = os.path.join(gdbWorkspace, finalOutputString)
                    fieldmappings = arcpy.FieldMappings()
                    fieldmappings.addTable(outputMerge)
                    fldmap_TARGETID = arcpy.FieldMap()
                    fldmap_TARGETID.addInputField(totalOverlapFc, "targetID")
                    fld_TARGETID = fldmap_TARGETID.outputField
                    fld_TARGETID.name = "targetID_1"
                    fldmap_TARGETID.outputField = fld_TARGETID
                    fieldmappings.addFieldMap(fldmap_TARGETID)
                    arcpy.SpatialJoin_analysis(outputMerge, totalOverlapFc, finalOutput, "#", "#", fieldmappings)
                    logging.info("Spatial Join: '%s' feature class created by joining '%s' with '%s'", finalOutput, outputMerge, totalOverlapFc)

                    # Update targetID with combined targetID determined from total overlap feature class
                    expression = "copyTargetID(!targetID!, !targetID_1!)"
                    codeblock = """def copyTargetID(targetID, comb_targetID):
                        if comb_targetID is None:
                            return targetID
                        else:
                            return comb_targetID"""
                    arcpy.CalculateField_management(finalOutput, "targetID", expression, "PYTHON_9.3", codeblock)
                    logging.info("Calculate Field: 'targetID' field value calculated for '%s' feature class", finalOutput)

                    # Delete extraneous fields
                    arcpy.DeleteField_management(finalOutput, "targetID_1")
                    arcpy.DeleteField_management(finalOutput, "Join_Count")
                    arcpy.DeleteField_management(finalOutput, "TARGET_FID")

            # Rename merged acquisition date feature class to appropriate name if it does not contain overlapping targets
            if overlapBool is False:
                arcpy.Rename_management(outputMerge, finalOutputString)
                logging.info("Rename: '%s' feature class renamed to '%s'", outputMerge, finalOutputString)

            # Delete unneeded process outputs (dissolve and merge outputs)
            arcpy.Delete_management(outputDissolve)
            logging.info("Delete: '%s' feature class deleted", outputDissolve)
            if arcpy.Exists(outputMerge):
                arcpy.Delete_management(outputMerge)
                logging.info("Delete: '%s' feature class deleted", outputMerge)

            logging.info("Processing for merges for acquisition date '%s' complete\n", key)

        # Iterate through dark targets acquisition dates to export single feature classes
        arcpy.AddMessage("\nExporting single feature classes...")
        logging.info("Processing single feature classes to export")
        for key in fcDictByDate:
            if len(fcDictByDate[key]) == 1:
                for fc in fcList:
                    fcSplit = fc.split("_")
                    if fcSplit[1] in mergeDictbyDate:
                        continue
                    else:
                        outputFeatureName = "RS2_" + fcSplit[1]
                        arcpy.FeatureClassToFeatureClass_conversion(fc, gdbWorkspace, outputFeatureName, "#", "#", )
                        logging.info("Feature Class to Feature Class: '%s' feature class converted to '%s'", fc, outputFeatureName)
                        outputFeatPath = os.path.join(gdbWorkspace, outputFeatureName)
                        arcpy.DeleteField_management(outputFeatPath, "FID")
        logging.info("Processing of single feature classes to export complete")

        logging.info("mergeAreas.py script finished\n\n")

        return