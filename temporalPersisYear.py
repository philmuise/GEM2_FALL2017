#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 31 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used as the "3b_Temporal Persistence Analysis (year to year)"
in the "GEM2_Oil_Seep_Detection_Analysis" Python Toolbox. Calls the
'temporalPersistence.py' script to perform the analysis.

SUMMARY
Performs a spatial-temporal analysis of the persistence of dark targets on an
overall year to year basis.

INPUT
- Location of GEM2 Temporal Analysis GDB (user input): GDB containing the output
feature classes created by "3a_Temporal Persistence Analysis (day to day)" tool.

- Consolidated Yearly Feature Classes (automated input): Feature classes created
 by "3a_Temporal Persistence Analysis (day to day)" tool.

- Attribute Selection Criteria (default user input): SQL expression which is used
 to filter the number of dark targets to be considered during the analysis.

- Attribute Rejection Criteria (default user input): SQL expression which is used
 for rejecting certain unwanted attribute values that may be selected with the
 selection criteria expression.

- Persistence Radius (meters) (user input): List of values which are used for the distances
with which the spatial portion of the analysis will be performed (in meters).
Any number of distance values may be entered.

- Dark Targets Shapefiles of Feature Classes from Other Sources (optional user input):
A shapefile or feature class of dark targets produced outside of this toolbox to
 be incorporated as additional data in a multi-year persistence analysis. The ID
  column for the other source must be identified, along with an attribute field
  which indicates the year of the dark target.

OUTPUT
- Consolidated feature class (automated output): Final output feature class which
consolidates all dark targets from every acquisition year together in a single
feature class, with their associated persistence values. Named 'persistent_targets'
and appended with year span of the dark targets used in the analysis
('persistent_targets_2010to2012)"""

# Libraries
# =========
import arcpy
import os
from datetime import datetime
import logging
import sys

# Reload steps required to refresh memory if Catalog is open when changes are made
import temporalPersistence                      # get module reference for reload
reload(temporalPersistence)                     # reload step 1
from temporalPersistence import temporalPersistence # reload step 2


class temporalPersisYear(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "3b_Temporal Persistence Analysis (year to year)"
        self.description = "Determines persistence between dark targets at set \
        distances and spanning different times (daily or yearly analysis)."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        params0 = arcpy.Parameter(
            displayName="Input: Analysis GDB",
            name="sourceGDB",
            datatype=["DEWorkspace"],
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
##        # Set log configuration
##        logPath = os.path.join(os.path.dirname(parameters[0].valueAsText), "logs")
##        if not os.path.exists(logPath):
##            os.makedirs(logPath)
##        logFile = os.path.join(logPath, "conditionData.log")
##        logging.basicConfig(filename=logFile, format='%(asctime)s -- %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)
##        logging.info("Starting condition_darkTargets.py script...\n")

        temporalPersis = temporalPersistence()
        temporalPersisParams = temporalPersis.getParameterInfo()

        temporalPersisParams[0] = parameters[0]

        temporalPersisParams[1] = parameters[1]

        temporalPersisParams[2] = parameters[2]

        temporalPersisParams[3] = parameters[3]

        temporalPersisParams[4] = parameters[4]

        temporalPersis.execute(temporalPersisParams, None)

        return