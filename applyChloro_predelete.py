#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Modified by Philippe Muise                                                   #
# Last modified: 15 Sept 2017 by Philippe Muise                                #
#==============================================================================#
"""USAGE
Module imported and used as the "1b_Apply Chlorophyll_a Values" script
tool in the "GEM2_Oil_Seep_Detection_Analysis" Python Toolbox.

SUMMARY
Applies chlorophyll_a values from the MODIS chlorophyll_a data, downloaded with
the "1a_Download Chlorophyll_a NetCDF Files" script tool, to the dark targets
feature classes in the Yearly Data geodatabases. The value is a measure of the
concentration of chlorophyll_a in mg/m-3. The analysis is performed over a range of
days input by user to assess chlorophyll_a over dark targets over a greater period of
time.

INPUT
- Folder Location of Dark Targets GDBs (user input): Folder containing the geodatabases
produced by "1_Condition Yearly Dark Targets Data". The script will iterate through
the geodatabases and apply the chlorophyll_a values for that acquisition day to
the dark targets.

- Neighbourhood Cell Size (default user input): Integer parameter indicating the
size of the neighbourhood window to be used in the focal statistics calculation
to determine the mean pixel value within the neighbourhood window.

- Chlorophyll Day Range Size From Date of Acquisition (user input): Integer parameter
indicating the range of days +/- from the date of acquistion of the dark features
feature class. Range of days must be equal or lesser than the range of days input in
the 1a_Download Chlorophyll_a NetCDF Files step.

OUTPUT
- "chlor_a" and "chlor_5x5" Attribute Fields (automated output): Attribute fields
that are joined to the acquisition day feature classes found within the various
dark targets yearly geodatabases. The "chlor_a" attribute field contains the
extracted raster value of the chlorophyll at the location of the dark target's
centroid. The "chlor_5x5_" attribute field contains the extracted raster value of
the mean of the pixel value within the specified neighbourhood window. ('5x5' in
this case)

ADDITIONAL FUNCTIONS (explained in script below)
- yearDay
- adapted from ESRI's Join_Field.py functions
    - joindataGen
    - percentile
    - join_field
- cleanWorkspace"""

# Libraries
# =========
import arcpy
import os
import sys
import datetime
import logging


class applyChloro(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1b_Apply Chlorophyll_a Values"
        self.description = "Creates and applies chlorophyll_a attribute value\
         to each dark targets feature class located in the yearly GDBs."
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
            displayName="Input: Neighbourhood Cell Size (pixels)",
            name="cell_size",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        params1.value = 5

        params2 = arcpy.Parameter(
            displayName="Input: Chlorophyll Day Range Size From Date of Acquisition",
            name="Day Range",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")

        params = [params0, params1, params2]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute. This script requires Spatial Analyst extension to function."""
        try:
            if arcpy.CheckExtension("Spatial") != "Available":
                raise Exception
        except Exception:
            return False

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
        logPath = os.path.join(parameters[0].valueAsText, "logs")
        if not os.path.exists(logPath):
            os.makedirs(logPath)
        logFile = os.path.join(logPath, "chloro.log")
        logging.basicConfig(filename=logFile, format='%(asctime)s -- %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)
        arcpy.AddMessage("\nApplying available chlorophyll_a values to dark targets...")
        logging.info("Starting applyChloro.py script...")

        arcpy.CheckOutExtension("Spatial")
        logging.info("Check Out Extension: Spatial Analyst extension checked out\n")

        # Define variables from parameters
        working_folder = parameters[0].valueAsText
        chloro_folder = os.path.join(os.path.dirname(working_folder), "Auxiliary", "Chlorophyll")
        if not os.path.exists(chloro_folder):
            os.makedirs(chloro_folder)
        cell_size = parameters[1].value

        focal_field = "chlor_a_" + str(cell_size) + "x" + str(cell_size)

        dayRange = parameters[2].value


        # Determine list of yearly GDBs in workspace
        arcpy.env.workspace = working_folder
        gdbList = arcpy.ListWorkspaces("*", "FileGDB")
        arcpy.AddMessage("Workspace contains the following " + str(len(gdbList)) + " GDBs: " + str(gdbList))

        # Iterate through yearly GDBs
        for gdb in gdbList:
            arcpy.AddMessage("\nProcessing " + str(gdb))
            logging.info("Processing '%s' geodatabase\n", gdb)
            gdbDesc = arcpy.Describe(gdb)
            gdbYear = gdbDesc.baseName

            # Determine list of .nc files in corresponding yearly chlorophyll folder
            chloro_year = os.path.join(chloro_folder, gdbYear)
            arcpy.env.workspace = chloro_year
            ncList = arcpy.ListFiles('*.nc')

            # Determine list of feature classes in current GDB
            arcpy.env.workspace = gdb
            fcList = arcpy.ListFeatureClasses()
            arcpy.AddMessage("\nGDB contains the following " + str(len(fcList)) + " feature classes: " + str(fcList))

            # Iterate through feature classes in GDB
            for fc in fcList:

                # Check if chlorophyll_a has already been added to current feature class
                arcpy.AddMessage("\nVerifying " + fc + "...")
                logging.info("Processing '%s' feature class", fc)
                fldList = arcpy.ListFields(fc)
                fldNames = []
                for fld in fldList:
                    fldNames.append(fld.name)

                # If no chlorophyll_a data already in feature class, proceed with applying values
                if not focal_field in fldNames:

                    dayCounter = 0

                    # Create points feature class from current feature class to extract chlorophyll raster values
                    arcpy.AddMessage("Creating points feature class...")
                    targetLyr = "targetLyr"
                    arcpy.MakeFeatureLayer_management(fc, targetLyr)
                    logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", targetLyr, fc)
                    pointFC = fc + "_point"
                    arcpy.FeatureToPoint_management(targetLyr, pointFC, "CENTROID")
                    logging.info("Feature To Point: '%s' points feature class created from centroid of features in '%s' layer", pointFC, targetLyr)

                    # Determine year and day of year to load appropriate .nc file as raster
                    yDay = self.yearDay(fc.split("_")[1], dayRange)


                    arcpy.AddMessage('{}'.format(yDay))
                    # Iterate through list of year's .nc files to find corresponding file to current feature class
                    for day in yDay:
                        chloro_file = "A" + day
                        arcpy.AddMessage('{}'.format(chloro_file))
                        for ncFile in ncList:
                            # Check for .nc file and feature class match
                               if ncFile.startswith(chloro_file):

                                    # Make NetCDF raster layer from .nc file
                                    arcpy.AddMessage("Preparing chlorophyll_a raster layer...")
                                    ncFilePath = os.path.join(chloro_year, ncFile)
                                    chlor_a = "chlor_a_{}"
                                    arcpy.MakeNetCDFRasterLayer_md(ncFilePath, 'chlor_a', "lon", "lat", chloro_file)
                                    logging.info("Make NetCDF Raster Layer: '%s' raster layer created from '%s'", chloro_file, ncFilePath)


                                    arcpy.AddMessage('{a},{b},{c},{d}'.format(-160.0, 40.0, -40.0, 89.989002))
                                                                        # Apply extent to raster layer (to limit processing to pertinent region)
                                    chloro_extent = arcpy.Extent(-160.0, 40.0, -40.0, 89.989002)
                                    chloro_rectExtract = arcpy.sa.ExtractByRectangle(chloro_file, chloro_extent, "INSIDE")
                                    logging.info("Extract By Rectangle: Extent (-160 (W), 40 (S), -40 (E), 89.989002 (N)) applied to '%s'", chloro_file)

                                    # Calculate focal statistics (mean value of focal window)
                                    arcpy.AddMessage("Calculating focal statistics...")
                                    neighborhood = arcpy.sa.NbrRectangle(cell_size, cell_size, "CELL")
                                    chloro_focal = arcpy.sa.FocalStatistics(chloro_rectExtract, neighborhood, "MEAN", "DATA")
                                    logging.info("Focal Statistics: '%s' raster created by calculating mean value of '%s'x'%s' neighbourhood calculated for cells from '%s'", chloro_focal, str(cell_size), str(cell_size), chloro_file)

                                    if not chlor_a in fldNames:
                                        # Extract point values from raster
                                        arcpy.AddMessage("Extracting raster chlorophyll_a values to points...")
                                        extractFC = fc + "_extract"
                                        arcpy.sa.ExtractValuesToPoints(pointFC, chloro_rectExtract, extractFC)
                                        arcpy.AlterField_management(extractFC, "RASTERVALU", chlor_a)
                                        logging.info("Extract Values to Points: '%s' feature class created with point values calculated from '%s' raster layer with '%s' feature class", extractFC, chloro_file, pointFC)

                                    # Extract focal values from raster
                                    arcpy.AddMessage("Extracting raster chlorophyll_a mean values to points...")
                                    finalExtractFC = fc + "_final_extract" + str(dayCounter)
                                    arcpy.sa.ExtractValuesToPoints(extractFC, chloro_focal, finalExtractFC)
                                    focal_field_Day = "chlor_a_" + str(cell_size) + "x" + str(cell_size) + '_' + str(day)
                                    arcpy.AlterField_management(finalExtractFC, "RASTERVALU", focal_field_Day)
                                    logging.info("Extract Values to Points: '%s' feature class created with point values calculated from '%s' raster layer with '%s' feature class", finalExtractFC, chloro_focal, extractFC)

                                    # Join point and focal values to feature class
                                    arcpy.AddMessage("Joining values to feature class...")
                                    self.join_field(fc, "OBJECTID", finalExtractFC, "ORIG_FID", "chlor_a_{};".format(day) + focal_field_Day)
                                    logging.info("Join Field: chlor_a and chlor_a focal values joined to '%s' feature class from '%s' table", fc, finalExtractFC)

                                    # add field with day difference in range
                                    arcpy.AddField_management(fc,"chloro_dayRange","DOUBLE")
                                    arcpy.AddField_management(fc,'chlor_a_{0}x{0}'.format(cell_size),"DOUBLE")
                                    arcpy.AddMessage('Added field')

                                    arcpy.AddMessage('{}'.format(dayCounter))

                                    with arcpy.da.UpdateCursor(fc, [focal_field_Day, 'chloro_dayRange','chlor_a_{0}x{0}'.format(cell_size)]) as cursor:
                                         for row in cursor:
                                             if row[0] != -9999 and row[1] == None:
                                                row[1] = self.dayDisplay(dayCounter)
                                                row[2] = row[0]
                                                cursor.updateRow(row)
                                    if dayCounter != 0:
                                        arcpy.DeleteField_management(fc,[chlor_a,focal_field_Day])
                                    dayCounter += 1
                                    break

                                    # Break iteration through .nc files once processing with corresponding .nc file and feature class is complete


                # If chlorophyll_a values found in feature class, no further processing required for current feature class
                else:
                    arcpy.AddMessage("Chlorophyll_a values already applied to feature class. Continuing...")
                    logging.info("Values already applied")


                logging.info("Processing for '%s' feature class complete\n", fc)

            # Delete extra feature classes used during geoprocessing
            self.cleanWorkspace(gdb)

        arcpy.CheckInExtension("Spatial")
        logging.info("Check In Extension: Spatial Analyst extension checked back in")
        logging.info("applyChloro.py script finished\n\n")

        return

    def yearDay(self, fc_dateString, fc_dateRange):
        """Calculate the day of the year for each RADARSAT-2 acquisition (to conform to MODIS naming convention) and for the days +/- date range desired

        Parameter:
            fc_dateString = Date string acquired from the feature class name in the input geodatabase,
            conforming to the following format: YYYYmmDD (e.g. 20100925 for 25 September 2010)

        Return:
            Returns sub-directory list of strings to be concatenated with ftp file directory in order to point to the required year and day of the year to access the desired MODIS imagery,
            conforming to the following format: YYYYDDD (e.g. 2010268 for 25 September 2010)
        Edits:
              Developed by D. Hennessey. Modified by Philippe Muise to return a list for the window of analysis.
        """
        year = fc_dateString[:4]
        month = fc_dateString[4:6].lstrip("0")
        day = fc_dateString[-2:].lstrip("0")
        fc_date = datetime.date(int(year), int(month), int(day))
        fc_dateList = [fc_date]
        for i in range(fc_dateRange):
            fc_dateList.append(fc_date - datetime.timedelta(days = i + 1))
            fc_dateList.append(fc_date + datetime.timedelta(days = i + 1))

        chloroDateList = []
        for chloroDate in fc_dateList:
            yDay = chloroDate.timetuple().tm_yday
            chloroDateList.append(str(chloroDate.year) + str(yDay).rjust(3,'0'))

        return chloroDateList

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

    def cleanWorkspace(self, workspace):
        """Clears geodatabase workspace of interim feature classes used during geoprocessing executed in this script.

        Parameter:
            workspace = Points to the workspace in which the deletion of feature classes will occur.

        Return:
            No return
        Edits:
              Modified by Philippe Muise"""
        arcpy.env.workspace = workspace
        arcpy.AddMessage("\nCleaning workspace...")
        pointList = arcpy.ListFeatureClasses("*_point")
        arcpy.AddMessage("Deleting point feature classes...")
        for fc in pointList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)
        extractList = arcpy.ListFeatureClasses("*_extract")
        arcpy.AddMessage("Deleting raster value extraction feature classes...")
        for fc in extractList:
            arcpy.Delete_management(fc)
            logging.info("Delete: '%s' feature class deleted", fc)

    def dayDisplay(self, number):
        """Determines the offset date used in chlorophyll analysis.
        Parameter:
             number = dayCounter value is input
        Return:
               Returns the offset value associated with the input value.
        Edits:
              Developed by Philippe Muise"""
        if (number % 2) == 0:
           return number/2
        else:
           return -(number+1)/2