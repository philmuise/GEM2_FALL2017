#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 28 March 2017 by D. Hennessy.                                 #
#==============================================================================#

# Libraries
# =========
import arcpy
import os
from datetime import datetime
import logging
import sys


class temporalPersistence(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3_Temporal Persistence Analysis"
        self.description = "Determines persistence between dark targets at set \
        distances and spanning different times (daily or yearly analysis)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        params0 = arcpy.Parameter(
            displayName="Input: Analysis GDB or Year Dataset",
            name="sourceGDB",
            datatype=["DEWorkspace","DEFeatureDataset"],
            parameterType="Required",
            direction="Input")

        params1 = arcpy.Parameter(
            displayName="Input: Attribute Selection Criteria",
            name="keepSQL",
            datatype="GPSQLExpression",
            parameterType="Optional",
            direction="Input")

        params1.value = "PcontrDb < -2.5 AND PwindMin < 4 AND SwindMean > 2 AND SwindMean < 10 AND Lcard < 10 AND Ldens < 0.0000075 AND SstdDb_Th < Th_SstdDb"

        params2 = arcpy.Parameter(
            displayName="Input: Attribute Rejection Criteria",
            name="rejectSQL",
            datatype="GPSQLExpression",
            parameterType="Optional",
            direction="Input")

        params2.value = "Pice = 1 OR PnearLand = 1 OR PeulerN < -50"

        params3 = arcpy.Parameter(
            displayName="Input: Persistence Radius (meters)",
            name="persisRadius",
            datatype="GPValueTable",
            parameterType="Required",
            direction="Input")

        params3.columns = [["GPLong", "Distances at which persistence will be calculated:"]]

        params4 = arcpy.Parameter(
            displayName="Optional Input: Dark targets shapefiles or feature classes from other sources",
            name="otherSourceFolder",
            datatype="GPValueTable",
            parameterType="Optional",
            direction="Input")

        params4.columns = [["DEShapefile", "Dark Targets Shapefile or Feature Class"], ["GPString", "ID Field"], ["GPString", "Year Field"]]
        params4.filters[1].type = "ValueList"
        params4.filters[1].list = [" "]
        params4.filters[2].type = "ValueList"
        params4.filters[2].list = [" "]

        params = [params0, params1, params2, params3, params4]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        if parameters[4].altered:
            paraValues = parameters[4].values

            numrows = len(paraValues)
            i = 0

            for line in paraValues:
                i += 1
                if i == numrows:
                    targetFC = line[0]
                    fld = line[1]
                    desc = arcpy.Describe(targetFC)
                    flds = desc.fields
                    fldList = []
                    for fld in flds:
                        fldList.append(fld.name)

            parameters[4].filters[1].list = fldList
            parameters[4].filters[2].list = fldList

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define variables from parameters
        source = parameters[0].valueAsText
        keepExpression = parameters[1].valueAsText
        rejectExpression = parameters[2].valueAsText
        bufferDists = parameters[3].valueAsText
        otherSources = parameters[4].valueAsText
        if otherSources is not None:
            otherSourceList = parameters[4].valueAsText.split(';')

        # Determine analysis GDB
        sourceDesc = arcpy.Describe(source)
        gdbName = "GEM2_Temporal_Analysis.gdb"
        if sourceDesc.dataType == 'Workspace':
            analysisGDB = source
        if sourceDesc.dataType == 'FeatureDataset':
            analysisGDB = os.path.join(os.path.dirname(sourceDesc.path), gdbName)

        # Set log configuration
        logPath = os.path.join(os.path.dirname(analysisGDB), "logs")
        if not os.path.exists(logPath):
            os.makedirs(logPath)
        logFile = os.path.join(logPath, "analysis.log")
        logging.basicConfig(filename=logFile, format='%(asctime)s -- %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)

        arcpy.AddMessage("\nAnalyzing temporal persistence of dark targets...")
        logging.info("Starting temporalPersistence.py script...\n")

        # Create analysis GDB if necessary
        if not arcpy.Exists(analysisGDB):
            outPath = os.path.dirname(analysisGDB)
            arcpy.AddMessage("Creating analysis GDB...")
            arcpy.CreateFileGDB_management(outPath, gdbName)
            logging.info("Create File GDB: '%s' created in '%s'\n", gdbName, outPath)

        # Determine contents of source workspace
        arcpy.env.workspace = source
        fcList = arcpy.ListFeatureClasses("RS2_*")
        sourceList = []
        for fc in fcList:
            fcPath = os.path.join(source, fc)
            sourceList.append(fcPath)
        arcpy.AddMessage("Workspace contains " + str(len(sourceList)) + " layers to analyze.")

        # Determine if there are other input sources to consider for analysis and associate ID and Year fields with each additional source
        if otherSources is not None:
            sourceFiles = {}
            for line in otherSourceList:
                item = line.split()
                sourceFiles[item[0]] = [item[1], item[2]]
            arcpy.AddMessage(str(len(sourceFiles)) + " addtional feature classes or shapefiles to analyze.")

        # Set boolean identifier, based on name of source workspace, for type of analysis to execute (day-to-day persistence within year, or year-to-year persistence for overall analysis)
        fcName = sourceList[0].split('\\')[len(sourceList[0].split('\\'))-1]
        if len(fcName) > 8:
            yrPersisBool = False
            arcpy.AddMessage("Analysis for day-to-day persistence within year detected")
        else:
            yrPersisBool = True
            sourceList.sort()
            minYr = fcName[4:]
            maxYr = sourceList[len(sourceList) - 1].split('\\')[len(sourceList[0].split('\\'))-1][4:]
            span = minYr + "to" + maxYr
            arcpy.AddMessage("Analysis for year-to-year overall persistence detected")

        # Check if source workspace contains only a single feature class, no temporal analysis required
        if len(sourceList) == 1:
            arcpy.AddMessage("Only one layer available, temporal analysis not required.")
            fcName = sourceList[0].split('\\')[len(sourceList[0].split('\\'))-1]
            if yrPersisBool is False:
                arcpy.AddMessage("Exporting year feature class to analysis GDB...")
                outFC = "RS2_" + fcName.split('_')[1][:4]
                arcpy.FeatureClassToFeatureClass_conversion(sourceList[0], analysisGDB, outFC)
                logging.info("Feature Class to Feature Class: '%s' feature class converted to '%s' in '%s' geodatabase\n", sourceList[0], outFC, analysisGDB)

        # More than one feature class in source workspace, execute temporal analysis
        else:
            # ======================================================= #
            # Apply filter criteria and dissolve polygons by targetID #
            # ======================================================= #

            # Iterate through source feature classes to apply filter criteria and dissolve dark target polygons by targetID
            for fc in sourceList:
                arcpy.AddMessage("\nProcessing " + fc + "...")
                logging.info("Processing '%s' feature class for filter criteria and targetID dissolve", fc)
                fcName = fc.split('\\')[len(fc.split('\\'))-1]

                # Add total layer count field and value
                arcpy.AddMessage("Adding total layer count field and values...")
                if yrPersisBool:
                    arcpy.AddField_management(fc, "totalYrLyr", "SHORT")
                    logging.info("Add Field: '%s' field added", 'totalYrLyr')
                    with arcpy.da.UpdateCursor(fc, "totalYrLyr") as cursor:
                        for row in cursor:
                            row[0] = len(sourceList)
                            if otherSources is not None:
                                row[0] = row[0] + len(otherSourceList)
                            cursor.updateRow(row)
                    logging.info("Update Cursor: '%s' values updated", 'totalYrLyr')
                else:
                    arcpy.AddField_management(fc, "totalLyr", "SHORT")
                    logging.info("Add Field: '%s' field added", 'totalLyr')
                    with arcpy.da.UpdateCursor(fc, "totalLyr") as cursor:
                        for row in cursor:
                            row[0] = len(sourceList)
                            cursor.updateRow(row)
                    logging.info("Update Cursor: '%s' values updated", 'totalLyr')

                # Apply attribute criteria filters to reduce number of polygons to analyze
                tempLayer = "dtLyr"
                arcpy.MakeFeatureLayer_management(fc, tempLayer)
                logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", tempLayer, fc)

                # Apply selection criteria for attributes to KEEP
                if keepExpression is not None:
                    arcpy.AddMessage("Selecting attributes to keep...")
                    arcpy.SelectLayerByAttribute_management(tempLayer, "NEW_SELECTION", keepExpression)
                    logging.info("Select Layer by Attribute: Features from '%s' selected, meeting the following selection criteria: '%s'", tempLayer, keepExpression)

                # Apply selection criteria for attributes to REJECT
                if rejectExpression is not None:
                    arcpy.AddMessage("Removing attributes to reject...")
                    if keepExpression is None:
                        arcpy.SelectLayerByAttribute_management(tempLayer, "NEW_SELECTION", rejectExpression)
                        arcpy.SelectLayerByAttribute_management(tempLayer, "SWITCH_SELECTION")
                    else:
                        arcpy.SelectLayerByAttribute_management(tempLayer, "REMOVE_FROM_SELECTION", rejectExpression)
                    logging.info("Select Layer by Attribute: Features from '%s' removed from selection, meeting the following rejection criteria: '%s'", tempLayer, rejectExpression)

                # Copy filtered dark targets to new feature class for subsequent dissolve
                if keepExpression is not None or rejectExpression is not None:
                    filterFC = os.path.join(analysisGDB, fcName + "_filter")
                    arcpy.CopyFeatures_management(tempLayer,filterFC)
                    logging.info("Copy Features: '%s' feature class copied from selected features in '%s' layer", filterFC, tempLayer)
                else:
                    filterFC = tempLayer

                # Dissolve filtered dark targets by targetID
                arcpy.AddMessage("Dissolving by targetID...")
                outFeatureClass = os.path.join(analysisGDB, fcName + '_byTargetID')
                arcpy.Dissolve_management(filterFC, outFeatureClass, "targetID")
                logging.info("Dissolve: '%s' feature class created from '%s' feature class dissolve", outFeatureClass, filterFC)

                # Rename targetID field to corresponding year or day feature class (for pairing with corresponding statistics table in subsequent analysis step)
                arcpy.AddMessage("Renaming targetID field with year or day of feature class")
                new_name = "targetID_" + fcName.split('_')[1]
                arcpy.AlterField_management(outFeatureClass, "targetID", new_name)
                logging.info("Alter Field: '%s' field renamed to '%s'", 'targetID', new_name)
                logging.info("Processing for '%s' feature class filter criteria and targetID dissolve complete\n", fc)

            # ========================================= #
            # Split and add other input sources by year #
            # ========================================= #

            arcpy.env.workspace = analysisGDB
            if otherSources is not None:
                # Check if year-to-year overall analysis, other input sources possible in this case
                if yrPersisBool:
                    arcpy.AddMessage("\nAdditional input shapefiles or feature classes detected for multi-year analysis. Appending data to appropriate years...")

                    # Copy original source list to preserve integrity of original feature classes
                    arcpy.AddMessage("Copying original input feature classes...")
                    newSourceList = []
                    fcTidList = arcpy.ListFeatureClasses("*_byTargetID")
                    for fc in sourceList:
                        fcCopy = os.path.join(analysisGDB, fc + "Copy")
                        arcpy.CopyFeatures_management(fc, fcCopy)
                        logging.info("Copy Features: '%s' feature class copied from '%s'", fcCopy, fc)
                        newSourceList.append(fcCopy)
                    sourceList = newSourceList
                    logging.info("Feature class copies complete\n")

                    # Iterate through other input sources to split and append dark targets by year
                    for fc in sourceFiles:
                        arcpy.AddMessage("Processing " + fc + "from other input files...")
                        logging.info("Processing '%s' feature class from other input sources", fc)

                        # Determine distinct year values in other source
                        yrField = sourceFiles[fc][1]
                        cursorField = [yrField]
                        yrValues = []
                        with arcpy.da.SearchCursor(fc, cursorField) as cursor:
                            for row in cursor:
                                yrValue = row[0]
                                if not yrValue in yrValues:
                                    yrValues.append(yrValue)
                        logging.info("Search Cursor: Year values present in other source: '%s'\n", str(yrValues))
                        arcpy.AddMessage("Following year values determined: " + str(yrValues))

                        # Iterate through distinct years to split other source by year and append to corresponding original feature classes, or create new year feature class
                        yrSpan = []
                        for yr in yrValues:

                            # Define appropriate file path and name variables
                            arcpy.AddMessage("Processing year: " + str(yr))
                            logging.info("Processing '%s' from distinct year values", str(yr))
                            yrOutput = str(yr).split('.')[0]
                            yrSpan.append(yrOutput)
                            equivSourceName = "RS2_" + yrOutput + "_byTargetID"
                            equivSourceCopyName = "RS2_" + yrOutput + "Copy"
                            otherSourceName = "dt_" + yrOutput + "_byTargetID"
                            otherSourceCopyName = "dt_" + yrOutput + "Copy"
                            where_clause = yrField + " = " + str(yr)
                            equivSourceYr = os.path.join(analysisGDB,equivSourceName)
                            equivSourceCopy = os.path.join(analysisGDB,equivSourceCopyName)
                            otherSourceYr = os.path.join(analysisGDB,otherSourceName)
                            otherSourceCopy = os.path.join(analysisGDB,otherSourceCopyName)
                            otherSourceID = sourceFiles[fc][0]

                            # Append current year's dark targets to already existing feature class for that year
                            if equivSourceName in fcTidList or otherSourceName in fcTidList:
                                arcpy.AddMessage("Feature class for current year detected...")
                                yrLyr = "yrLyr" + yrOutput
                                arcpy.MakeFeatureLayer_management(fc, yrLyr, where_clause)
                                logging.info("Make Feature Layer: '%s' layer created from current year selection of '%s' feature class", yrLyr, fc)

                                # Create field maps to link ID field from other source to targetID field in '*_byTargetID' and '*Copy' feature classes
                                fm_targetIDcopy = arcpy.FieldMap()
                                fldMpCopy = arcpy.FieldMappings()
                                fm_targetIDcopy.addInputField(yrLyr, otherSourceID)
                                idCopy_name = fm_targetIDcopy.outputField
                                idCopy_name.name = "targetID"
                                fm_targetIDcopy.outputField = idCopy_name
                                fldMpCopy.addFieldMap(fm_targetIDcopy)

                                fm_targetIDyr = arcpy.FieldMap()
                                fldMpYr = arcpy.FieldMappings()
                                fm_targetIDyr.addInputField(yrLyr, otherSourceID)
                                idYr_name = fm_targetIDyr.outputField
                                idYr_name.name = "targetID_" + yrOutput
                                fm_targetIDyr.outputField = idYr_name
                                fldMpYr.addFieldMap(fm_targetIDyr)

                                # Append dark targets from current year to already existing original feature class or to already existing feature class created from a previous other input source
                                arcpy.AddMessage("Appending dark targets...")
                                if equivSourceName in fcTidList:
                                    arcpy.Append_management(yrLyr, equivSourceYr, "NO_TEST", fldMpYr)
                                    logging.info("Append: Features from '%s' appended to '%s' feature class", yrLyr, equivSourceYr)
                                    arcpy.Append_management(yrLyr, equivSourceCopy, "NO_TEST", fldMpCopy)
                                    logging.info("Append: Features from '%s' appended to '%s' feature class", yrLyr, equivSourceCopy)
                                else:
                                    arcpy.Append_management(yrLyr, otherSourceYr, "NO_TEST", fldMpYr)
                                    logging.info("Append: Features from '%s' appended to '%s' feature class", yrLyr, otherSourceYr)
                                    arcpy.Append_management(yrLyr, otherSourceCopy, "NO_TEST", fldMpCopy)
                                    logging.info("Append: Features from '%s' appended to '%s' feature class", yrLyr, otherSourceCopy)

                            # If feature class for current year does not already exist, create new feature class from current year's dark targets
                            else:
                                arcpy.AddMessage("No feature class for current detected. Creating feature class...")
                                arcpy.Select_analysis(fc, otherSourceYr, where_clause)
                                logging.info("Select: '%s' feature class created from selection of current year's features from '%s'", otherSourceYr, fc)
                                arcpy.Select_analysis(fc, otherSourceCopy, where_clause)
                                logging.info("Select: '%s' feature class created from selection of current year's features from '%s'", otherSourceCopy, fc)

                                # Rename ID field to appropriate targetID fields
                                yrTargetIDField = "targetID_" + yrOutput
                                arcpy.AlterField_management(otherSourceYr, otherSourceID, yrTargetIDField)
                                fldList = arcpy.ListFields(otherSourceCopy)
                                for fld in fldList:
                                    if fld.name == otherSourceID:
                                        arcpy.AlterField_management(otherSourceCopy, otherSourceID, "targetID")
                                    elif fld.name == "OBJECTID" or "Shape" in fld.name:
                                        continue
                                    else:
                                        arcpy.DeleteField_management(otherSourceCopy, fld.name)

                                # Append new feature class to list of feature classes for analysis
                                sourceList.append(otherSourceCopy)

                            logging.info("Processing for '%s' from distinct year values complete\n")

                        # Update year span value if required
                        yrSpan.sort()
                        if yrSpan[0] < minYr:
                            minYr = yrSpan[0]
                        if yrSpan[len(yrSpan) - 1] > maxYr:
                            maxYr = yrSpan[len(yrSpan) - 1]
                        newSpan = minYr + "to" + maxYr
                        if newSpan != span:
                            span = newSpan

                        logging.info("Processing for '%s' feature class from other input sources complete\n", fc)

                # Not year-to-year overall analysis, cannot incorporate other input feature classes.
                else:
                    arcpy.AddMessage("\nCurrent temporal analysis is not multi-year. Other input shapefiles or feature classes will be ignored...")

            # ===================================== #
            # Calculate persistence of dark targets #
            # ===================================== #

            # Determine and iterate through list of feature classes with dark targets organized by '*_byTargetID' to create point feature classes
            fcTidList = arcpy.ListFeatureClasses("*_byTargetID")
            arcpy.AddMessage("\nCreating point feature classes from targetID feature classes...")
            logging.info("Processing 'byTargetID' feature classes for creation of point feature classes")
            for fc in fcTidList:
                pointName = fc + "_points"
                outFeatures = os.path.join(analysisGDB, pointName)
                arcpy.FeatureToPoint_management(fc, outFeatures, "CENTROID")
                logging.info("Feature To Point: '%s' points feature class created from centroid of features in '%s' feature class", outFeatures, fc)
            logging.info("Processing for creation of points feature classes complete\n")

            # Calculate persistence of dark targets via points feature classes and buffer distances
            pointFeatList = arcpy.ListFeatureClasses("*_points")
            bufferDistanceList = bufferDists.split(";")
            for dist in bufferDistanceList:
                arcpy.AddMessage("\nVerifying persistence of dark targets at " + str(dist) + " meters...")
                logging.info("Processing persistence analysis at distance of '%s' metres\n", str(dist))
                self.calcPersis(analysisGDB, yrPersisBool, fcTidList, pointFeatList, int(dist))
                logging.info("Processing for persistence analysis at distance of '%s' metres complete\n", str(dist))

            # =================================================== #
            # Join persistence values with source feature classes #
            # =================================================== #

            arcpy.AddMessage("\nJoining persistence stats with feature classes...")
            statsList = arcpy.ListTables()

            # Iterate through source feature classes to join persistence values
            for fc in sourceList:
                logging.info("Processing '%s' feature class to join persistence results", fc)
                persisLayer = "persisLyr"
                arcpy.MakeFeatureLayer_management(fc, persisLayer)
                logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", persisLayer, fc)
                statsTable = "targetID_" + fc.split('\\')[len(fc.split('\\'))-1].split('_')[1]
                if statsTable.endswith("Copy"):
                    statsTable = statsTable[:-4]

                # Iterate through stats tables to match with corresponding feature class (to join persistence values)
                for table in statsList:
                    if table.startswith(statsTable):
                        arcpy.AddMessage("Joining " + fc + " with " + table + "...")
                        outTable = os.path.join(analysisGDB, table)
                        joinField = statsTable
                        arcpy.AddJoin_management(persisLayer, "targetID", outTable, joinField)
                        logging.info("Add Join: '%s' table joined to joined to '%s' layer", outTable, persisLayer)
                outFC = fc.split('\\')[len(fc.split('\\'))-1] + "_persis"
                arcpy.FeatureClassToFeatureClass_conversion(persisLayer, analysisGDB, outFC)
                logging.info("Feature Class to Feature Class: '%s' layer converted to '%s' feature class", persisLayer, outFC)

                # Rename attribute fields to standardize for subsequent merge
                arcpy.AddMessage("Preparing " + fc + " for merge (renaming attribute fields)...")
                persisFC = os.path.join(analysisGDB, outFC)
                fieldList = arcpy.ListFields(persisFC)
                for field in fieldList:
                    if field.name.startswith("RS2_") or field.name.startswith("dt_"):
                        if field.name.endswith("Shape_Length") or field.name.endswith("Shape_Area"):
                            arcpy.DeleteField_management(persisFC, field.name)
                        else:
                            newNameSplit = field.name.split("_")
                            newName = "_".join(newNameSplit[2:])
                            arcpy.AlterField_management(persisFC, field.name, newName)
                    if field.name.startswith("targetID_"):
                        if "pers" in field.name or "wght" in field.name:
                            arcpy.AlterField_management(persisFC, field.name, field.name.split("_")[len(field.name.split("_"))-1])
                        else:
                            arcpy.DeleteField_management(persisFC, field.name)

                logging.info("Processing for '%s' feature class to join persistence results complete\n", fc)

            # ======================================================= #
            # Merge persistent dark targets into single feature class #
            # ======================================================= #

            arcpy.AddMessage("\nMerging persistent targets into single feature class...")
            persisList = arcpy.ListFeatureClasses("*_persis")
            if yrPersisBool:
                finalResultName = "persistent_targets_" + span
                mergeName = finalResultName + "_merge"
            else:
                finalResultName = "RS2_" + persisList[0].split('_')[1][:4]
                mergeName = finalResultName + "_merge"
            finalOutput = os.path.join(analysisGDB, finalResultName)
            outputMerge = os.path.join(analysisGDB, mergeName)
            arcpy.Merge_management(persisList, outputMerge)
            logging.info("Merge: '%s' created from merging the following feature classes: '%s'", outputMerge, str(persisList))

            # Check if output feature class already exists and join new persistence values
            if arcpy.Exists(finalOutput):
                arcpy.AddMessage("Final merge feature class already exists, incorporating in merge process...")
                logging.info("Exists: '%s' feature class already exists, joining new persistence values", finalOutput)
                addFields = []
                for dist in bufferDistanceList:
                    if yrPersisBool:
                        persisFieldName = "Ypers" + dist
                        wghtFieldName = "Ywght" + dist
                    else:
                        persisFieldName = "pers" + dist
                        wghtFieldName = "wght" + dist
                    fldList = arcpy.ListFields(finalOutput)
                    fldNames = []
                    for fld in fldList:
                        fldNames.append(fld.name)
                    if persisFieldName in fldNames:
                        arcpy.DeleteField_management(finalOutput, persisFieldName)
                        arcpy.DeleteField_management(finalOutput, wghtFieldName)
                    addFields.append(persisFieldName)
                    addFields.append(wghtFieldName)
                self.join_field(finalOutput, "targetID", outputMerge, "targetID", ";".join(addFields))
                logging.info("Joined new values to '%s' feature class for the following fields: '%s'\n", finalOutput, str(addFields))

            # If no previous output feature class, rename merge output to final day or year analysis output
            else:
                arcpy.Rename_management(outputMerge, finalOutput)
                logging.info("Rename: '%s' feature class renamed to '%s'\n", outputMerge, finalOutput)

            # ============================================ #
            # Assign cluster IDs to clustered dark targets #
            # ============================================ #

            arcpy.AddMessage("\nAssigning cluster IDs to clustered targets...")
            logging.info("Processing cluster IDs\n")

            # Determine dissolve feature classes (which contains data on intersecting dark targets) and organize by buffer distance
            dissolveList = arcpy.ListFeatureClasses("*_dissolve")
            dissolveListDict = {}
            for fc in dissolveList:
                bufferDist = fc.split("_")[len(fc.split("_"))-3]
                if bufferDist in dissolveListDict:
                    dissolveListDict[bufferDist].append(fc)
                else:
                    dissolveListDict[bufferDist] = [fc]

            # Iterate through buffer distances to determine clusters per distance
            for bufferDist in dissolveListDict:
                arcpy.AddMessage("\nProcessing clustering at " + bufferDist + " meters...")
                logging.info("Processing dark target clusters at '%s' meters\n", bufferDist)
                clusterList = []

                # Iterate through feature classes within buffer distance to determine clustered targets
                for fc in dissolveListDict[bufferDist]:
                    arcpy.AddMessage("Detecting clusters in " + fc + "...")
                    logging.info("Processing '%s' feature class for initial clustering of targetIDs", fc)

                    # Determine targetID fields from differing days or years (targetID_2010, targetID_2011, etc) to include in cursor iteration
                    fldList = arcpy.ListFields(fc)
                    cursorFields = []
                    for fld in fldList:
                        if fld.name.startswith("targetID"):
                            cursorFields.append(fld.name)

                    # Select rows for cursor iteration that contain a targetID (not empty) for current feature class and initialize clustered targets list
                    expression = cursorFields[0] + " <> ''"
                    targetList = []

                    # Cursor iteration through table rows of current feature class to detect clustered targets
                    with arcpy.da.SearchCursor(fc, cursorFields, expression) as cursor:
                        for row in cursor:
                            rowFields = []

                            # Iterate through fields within the row to detect presence of targetIDs from differing times and append to rowFields list to determine clustering
                            for item in row:
                                if item != "":
                                    rowFields.append(item)

                            # If more than one targetID detected in same row, row of targetIDs is appended as an initial cluster to the targetList
                            if len(rowFields) > 1:
                                targetList.append(rowFields)
                    logging.info("Search Cursor: Detected clustered targets in '%s' feature class", fc)

                    # Iterate through target list to group repeating targets into clusters
                    for item in targetList:
                        itemPresent = False

                        # Iterate through each targetID in the target list and check cluster list if already recorded
                        for target in item:
                            for cluster in clusterList:
                                if target in cluster:

                                    # If targetID found in cluster list, append all targetIDs in target list item to corresponding cluster in cluster list (targetID will be duplicated within cluster)
                                    itemPresent = True
                                    for target in item:
                                        cluster.append(target)

                        # If target is not previously recorded in a cluster, append target list item as a new cluster to cluster list
                        if not itemPresent:
                            clusterList.append(item)

                    logging.info("Processing for '%s' feature class for initial clustering of targetIDs complete\n", fc)

                # Iterate through cluster list to group clusters spanning differing times (days or years) that were missed in initialize iteration of feature classes
                arcpy.AddMessage("Detecting overall grouping of clusters...")
                groupClusterList = []
                for cluster in clusterList:
                    clusterPresent = False

                    # Iterate through each targetID in the cluster and check grouped cluster list if already recorded
                    for target in cluster:
                        for groupCluster in groupClusterList:
                            if target in groupCluster:

                                # If targetID found in grouped cluster list, append all targetID in cluster to corresponding grouped cluster in grouped cluster list (targetID will be duplicated within grouped cluster)
                                clusterPresent = True
                                for target in cluster:
                                    groupCluster.append(target)

                    # If target is not previously recorded in a grouped cluster, append cluster as a new grouped cluster to grouped cluster list
                    if not clusterPresent:
                        groupClusterList.append(cluster)

                logging.info("Determined overall grouping of targetID clusters")

                # Deduplication of targetIDs in each cluster
                arcpy.AddMessage("Removing targetID duplicates in clusters...")
                finalClusterList = []
                for cluster in groupClusterList:
                    dedupeCluster = set(cluster)
                    finalCluster = list(dedupeCluster)
                    finalClusterList.append(finalCluster)
                logging.info("Removed duplicate targetIDs in each cluster")

                # Assign cluster ID to each cluster (arbitrary number assignment before decimal, maximum month difference after decimal)
                arcpy.AddMessage("Assigning cluster ID and calculating time span (in months) for each cluster...")
                clusterDict = {}
                clusterid = 1
                for cluster in finalClusterList:
                    clusterDict[clusterid] = cluster
                    clusterid += 1

                # Detect and calculate maximum difference of months between dark targets for cluster ID
                monthDiffDict = {}
                for key, value in clusterDict.iteritems():
                    targetDates = []
                    for target in value:
                        if len(target.split("_")) == 5:
                            dateString = target.split("_")[2]
                        elif len(target.split("_")) == 3:
                            dateString = target.split("_")[1]
                        else:
                            dateString = None
                        if dateString is not None:
                            date = datetime.strptime(dateString, "%Y%m%d")
                            targetDates.append(date)
                    targetDates.sort()
                    if targetDates == []:
                        monthDiff = 0
                    else:
                        monthDiff = (targetDates[len(targetDates)-1].year - targetDates[0].year) * 12 + (targetDates[len(targetDates)-1].month - targetDates[0].month)
                    monthDiffDict[key] = monthDiff
                logging.info("Assigned cluster ID and calculated time span for each cluster")

                # Create clusterID field and update relevant dark targets with clusterID value
                arcpy.AddMessage("Creating clusterID field and updating clusterID values...")
                if yrPersisBool:
                    clusterFieldName = "Yclst" + bufferDist
                else:
                    clusterFieldName = "clst" + bufferDist
                arcpy.AddField_management(finalOutput, clusterFieldName, "TEXT")
                cursorFields = ["targetID", clusterFieldName]
                with arcpy.da.UpdateCursor(finalOutput, cursorFields) as cursor:
                    for row in cursor:
                        for key, value in clusterDict.iteritems():
                            if row[0] in value:
                                clusterIDString = str(key) + "." + str(monthDiffDict[key])
                                row[1] = clusterIDString
                        cursor.updateRow(row)
                logging.info("Update Cursor: Cluster ID values updated for '%s' feature class\n", finalOutput)
                logging.info("Processing for dark targets at '%s' meters complete\n", bufferDist)

            logging.info("Processing for cluster IDs complete\n")

            # ================================== #
            # Export attribute table as csv file #
            # ================================== #

            arcpy.AddMessage("Exporting attribute table for " + finalResultName + " as csv file...")
            fldValueList = []
            fldList = arcpy.ListFields(finalOutput)
            for fld in fldList:
                if fld.name != "Shape":
                    fldValueList.append(fld.name)
            output_csv = os.path.join(os.path.dirname(analysisGDB), finalResultName + ".csv")
            arcpy.ExportXYv_stats(finalOutput, fldValueList, "COMMA", output_csv, "ADD_FIELD_NAMES")
            logging.info("Export XY Values: Exported all attribute values for '%s' feature class as '%s' csv file\n", finalOutput, output_csv)

            # =============================== #
            # Clean up analysis GDB workspace #
            # =============================== #

            self.cleanWorkspace(analysisGDB, fcTidList, pointFeatList, statsList, outputMerge)

        logging.info("temporalPersistence.py script finished\n\n")
        return

    def calcPersis(self, workspace, yrPersisBool, targetIDfeatList, pointList, bufferDist):
        """Calculates persistence values of each dark target at the specified buffer distance.

        Parameters:
            workspace = Points to the workspace in which the geoprocessing occurs and to which interim feature classes and tables will be saved
            yrPersisBool = Boolean value indicating whether type of analysis is day-to-day within the year or overall year-to-year
            targetIDfeatList = List of feature classes in which dark targets are dissolved by targetID
            pointList = List of point feature classes created from the centroid of each dark target (by targetID)
            bufferDist = Buffer distance at which to carry out the persistence analysis

        Return:
            No return, however creates attribute table output with the persistence and weight values for each dark target.

            Persistence field is created as 'pers*' for a day-to-day analysis within the year and 'Ypers*' for a year-to-year overall analysis.
            (e.g. pers8000 for a day-to-day persistence value with a buffer of 8,000 metres, or Ypers10000 for a year-to-year persistence value
            with a buffer of 10,000 metres)

            Weight field is created as 'wght*' for a day-to-day analysis within the year and 'Ywght*' for a year-to-year overall analysis.
            (e.g. pers8000 for a day-to-day persistence value with a buffer of 8,000 metres, or Ypers10000 for a year-to-year persistence value
            with a buffer of 10,000 metres)

            Persistence = Number of links from one dark target to another from a
            different time frame (For example, a dark target from 2011 which has
            a dark target from 2012 within its buffer distance will have a
            persistence value of 1. If a dark target from 2010 was also within
            its buffer distance, the dark target from 2011 would have a persistence
            value of 2)

            Weight = Number of individual dark targets found within the buffer
            distance of the dark target. (For example, a dark target from 2011 which
            has two dark targets from 2010 within its buffer distance is considered
            persistent (at a value of 1), and has a weight value of 3 (1 for itself,
            and 1 for each dark target within its buffer distance)"""
        analysisGDB = workspace

        # Create distance buffer for each points feature class for persistence analysis
        if bufferDist > 0:
            arcpy.AddMessage("Creating buffers for point feature classes...")
            logging.info("Processing point feature classes for creation of buffer feature classes")
            for fc in pointList:
                bufferFC = fc + "_" + str(bufferDist) + "_buffer"
                outBuffer = os.path.join(analysisGDB, bufferFC)
                distance = str(bufferDist) + " Meters"
                arcpy.Buffer_analysis(fc, outBuffer, distance, "FULL", "ROUND", "NONE", "", "GEODESIC")
                logging.info("Buffer: '%s' buffer created from '%s' feature class", outBuffer, fc)
            logging.info("Processing for creation of buffers feature classes complete\n")
            wild_card = "*_" + str(bufferDist) + "_buffer"
            bufferList = arcpy.ListFeatureClasses(wild_card)

        # Check for persistence analysis by direct intersection of dark targets, if buffer distance set at 0
        if bufferDist > 0:
            fcList = bufferList
        else:
            fcList = targetIDfeatList

        # Iterate through buffer (or targetID, in case of analysis by direct intersection) feature classes to compile feature classes for union analysis
        for fc in fcList:
            arcpy.AddMessage("\nPerforming union for persistence analysis on dark targets in " + fc.split("_")[1] + "...")
            logging.info("Processing '%s' feature class for union analysis", fc)

            # Determine time (day or year) of current buffer feature class and use current buffer feature class to start list of feature classes to union
            fcTime = fc.split("_")[1]
            unionList = [fc]

            # Determine field and feature class names for union depending of type of analysis (day-to-day or year-to-year)
            if yrPersisBool:
                union = "persistent_targets_" + fcTime + "_"+ str(bufferDist) + "_Union"
                persisFieldName = "Ypers" + str(bufferDist)
                weightFieldName = "Ywght" + str(bufferDist)
            else:
                union = "RS2_" + fcTime + "_" + str(bufferDist) + "_Union"
                persisFieldName = "pers" + str(bufferDist)
                weightFieldName = "wght" + str(bufferDist)

            # Append targetID feature classes from times other than current buffer feature class to list of feature classes to union
            for targetFc in targetIDfeatList:
                if fcTime != targetFc.split("_")[1]:
                    unionList.append(targetFc)

            # Perform union of feature classes to determine dark target persistence between layers
            arcpy.Union_analysis(unionList, union)
            logging.info("Union: Created '%s' feature class from union of following feature classes: '%s'", union, str(unionList))

            # Dissolve union features by targetID to remove possible duplicate features
            arcpy.AddMessage("Dissolving...")
            dissolveName = union + "_dissolve"
            dissolve = os.path.join(analysisGDB, dissolveName)
            dissolveFields = []
            fldList = arcpy.ListFields(union)
            for fld in fldList:
                if fld.name.startswith("targetID"):
                    dissolveFields.append(fld.name)
            arcpy.Dissolve_management(union, dissolve, dissolveFields)
            logging.info("Dissolve: '%s' feature class created from '%s' feature class dissolve", dissolve, union)

            # Add and calculate persistence values
            arcpy.AddMessage("Calculating persistence value...")
            arcpy.AddField_management(dissolve, persisFieldName, "SHORT")
            logging.info("Add Field: '%s' field added to '%s' feature class", persisFieldName, dissolve)
            cursorFields = dissolveFields
            cursorFields.append(persisFieldName)
            with arcpy.da.UpdateCursor(dissolve, cursorFields) as cursor:

                # Calculate persistence of targets by checking for polygons with multiple targetIDs (indicating an overlap occurring after the Union of feature classes)
                for row in cursor:
                    persis_count = -1
                    for item in row[:-1]:
                        if item != "":
                            persis_count += 1
                    row[len(row)-1] = persis_count
                    cursor.updateRow(row)
            logging.info("Update Cursor: Persistence values calculated for '%s' feature class", dissolve)

            # Summarize persistence statistics (count maximum persistence value and determine weight value for each dark target)
            arcpy.AddMessage("Summarizing persistence statistics and determining weight value...")
            statsTable = "targetID_" + fcTime + "_" + str(bufferDist) + "_stats"
            outTable = os.path.join(analysisGDB, statsTable)
            if yrPersisBool:
                stats = "Ypers" + str(bufferDist) + " MAX"
            else:
                stats = "pers" + str(bufferDist) + " MAX"
            casefield = "targetID_" + fcTime
            arcpy.Statistics_analysis(dissolve, outTable, stats, casefield)
            logging.info("Statistics: '%s' table created with maximum persistence value and weight value (frequency) calculations from '%s' feature class", outTable, dissolve)
            arcpy.AlterField_management(outTable, "FREQUENCY", weightFieldName)

            logging.info("Processing for '%s' feature class for union analysis complete\n", fc)

    def cleanWorkspace(self,workspace,fcTidList,pointFeatList,statsTableList,mergeFC):
        """Clears geodatabase workspace of interim feature classes used during geoprocessing executed in this script.

        Parameter:
            workspace = Points to the workspace in which the deletion of feature classes will occur.
            fcTidList = List of "byTargetID" feature classes
            pointFeatList = List of points feature classes
            statsTableList = List of statistics tables
            mergeFC = Output merge feature class

        Return:
            No return"""
        arcpy.env.workspace = workspace
        arcpy.AddMessage("\nCleaning workspace...")
        copyList = arcpy.ListFeatureClasses("*Copy")
        if copyList != []:
            arcpy.AddMessage("Deleting copy feature classes...")
            for fc in copyList:
                arcpy.Delete_management(fc)
                logging.info("Delete: '%s' feature class deleted", fc)
        filterList = arcpy.ListFeatureClasses("*_filter")
        arcpy.AddMessage("Deleting filtered attribute feature classes...")
        for fc in filterList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        bufferList = arcpy.ListFeatureClasses("*_buffer")
        arcpy.AddMessage("Deleting buffer feature classes...")
        for fc in bufferList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        unionList = arcpy.ListFeatureClasses("*_Union")
        arcpy.AddMessage("Deleting union feature classes...")
        for fc in unionList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        dissolveList = arcpy.ListFeatureClasses("*_dissolve")
        arcpy.AddMessage("Deleting dissolved union feature classes...")
        for fc in dissolveList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        arcpy.AddMessage("Deleting targetID feature classes...")
        for fc in fcTidList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        arcpy.AddMessage("Deleting point feature classes")
        for fc in pointFeatList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        arcpy.AddMessage("Deleting summary stats tables...")
        for table in statsTableList:
            arcpy.Delete_management(table)
            logging.info("Delete: '%s' table deleted", table)
        arcpy.AddMessage("Deleting persistence calculation feature classes...")
        persisList = arcpy.ListFeatureClasses("*_persis")
        for fc in persisList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        arcpy.AddMessage("Deleting pre-dissolved merge feature class...")
        arcpy.Delete_management(mergeFC)
        logging.info("Delete: '%s' feature class deleted", mergeFC)

    def joindataGen(self,joinTable,fieldList,sortField):
        """Code snippet from Esri's Join_Field.py (as a replacement to the Join Field geoprocessing tool, which suffers from exceedingly lengthy processing times.)

        Define generator for join data"""
        with arcpy.da.SearchCursor(joinTable,fieldList,sql_clause=['DISTINCT',
                                                                   'ORDER BY '+sortField]) as cursor:
            for row in cursor:
                yield row

    def percentile(self,n,pct):
        """Code snippet from Esri's Join_Field.py (as a replacement to the Join Field geoprocessing tool, which suffers from exceedingly lengthy processing times.)

        Function for progress reporting"""
        return int(float(n)*float(pct)/100.0)

    def join_field(self, inTable, inJoinField, joinTable, outJoinField, joinFields):
        """Code snippet from Esri's Join_Field.py (as a replacement to the Join Field geoprocessing tool, which suffers from exceedingly lengthy processing times.)

        Add join fields"""
        arcpy.AddMessage('\nAdding join fields...')
        fList = [f for f in arcpy.ListFields(joinTable) if f.name in joinFields.split(';')]
        for i in range(len(fList)):
            name = fList[i].name
            type = fList[i].type
            if type in ['Integer','OID']:
                arcpy.AddField_management(inTable,name,field_type='LONG')
            elif type == 'String':
                arcpy.AddField_management(inTable,name,field_type='TEXT',field_length=fList[i].length)
            elif type == 'Double':
                arcpy.AddField_management(inTable,name,field_type='DOUBLE')
            elif type == 'Date':
                arcpy.AddField_management(inTable,name,field_type='DATE')
            else:
                arcpy.AddError('\nUnknown field type: {0} for field: {1}'.format(type,name))

        # Write values to join fields
        arcpy.AddMessage('\nJoining data...')
        # Create generator for values
        fieldList = [outJoinField] + joinFields.split(';')
        joinDataGen = self.joindataGen(joinTable,fieldList,outJoinField)
        version = sys.version_info[0]
        if version == 2:
            joinTuple = joinDataGen.next()
        else:
            joinTuple = next(joinDataGen)
        #
        fieldList = [inJoinField] + joinFields.split(';')
        count = int(arcpy.GetCount_management(inTable).getOutput(0))
        breaks = [self.percentile(count,b) for b in range(10,100,10)]
        j = 0
        with arcpy.da.UpdateCursor(inTable,fieldList,sql_clause=(None,'ORDER BY '+inJoinField)) as cursor:
            for row in cursor:
                j+=1
                if j in breaks:
                    arcpy.AddMessage(str(int(round(j*100.0/count))) + ' percent complete...')
                row = list(row)
                key = row[0]
                try:
                    while joinTuple[0] < key:
                        if version == 2:
                            joinTuple = joinDataGen.next()
                        else:
                            joinTuple = next(joinDataGen)
                    if key == joinTuple[0]:
                        for i in range(len(joinTuple))[1:]:
                            row[i] = joinTuple[i]
                        row = tuple(row)
                        cursor.updateRow(row)
                except StopIteration:
                    arcpy.AddWarning('\nEnd of join table.')
                    break