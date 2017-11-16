#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Last modified: 31 March 2017 by D. Hennessy.                                 #
#==============================================================================#
"""USAGE
Module imported and used for the "4_Temporal Visualization" tool script in the
"GEM2_Oil_Seep_Detection_Analysis" Python Toolbox.

SUMMARY
Displays the results of the spatial-temporal analysis performed by either tool 3a
or 3b. The selected feature class is applied to a series of templates to produce
a map document used to visualize the persistence values and with the ability to
load corresponding radar imagery via hyperlink.

INPUT
- Persistent Targets Feature Class (user input): Feature class created as a result
of a spatial-temporal analysis by tool script 3a or 3b.

- Persistence Radius (meters) (user input): Checkbox selection indicating which
buffer distance,  for which persistence values has been previously calculated, is
to be included in the creation of the visual product. Any number of checkboxes can
be selected.

- 'templates' Folder (automated input): This folder, located in the "Results"
folder, contains the necessary templates to produce the visualization product.
This includes the following files:
    - heatmap.lyr: Layer file containing the symbology for the heat map layer
    - persis_weight.lyr: Layer file containing the symbology for the persistence
        and weight layers
    - radius.lyr: Layer file containing the symbology for the cluster layer
    - temporal_analysis.mxd: Map document which serves as a template for the
        analysis results output map document

OUTPUT
- Analysis Results .mxd File (automated output): Output map document in which the
various persistence values of the selected feature class are depicted with several
different layers.

- HeatMap layer (automated output): Output raster created by Kernel Density tool
and included in the analysis results map document.

- Supporting point and buffer feature classes (automated output): Point and buffer
feature classes used in the creation of the analysis result output map document.
"""

# Libraries
# =========
import arcpy
import os
import logging


class temporalVisuals(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "4_Temporal Visualization"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        params0 = arcpy.Parameter(
            displayName="Input: Persistent Targets Feature Class",
            name="targetsFC",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input")

        params1 = arcpy.Parameter(
            displayName="Input: Persistence Radius (meters)",
            name="persisRadius",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
            multiValue=True)

        params1.filter.type = "ValueList"
        params1.filter.list = []

        params = [params0, params1]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
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
        if parameters[0].value:
            fcDesc = arcpy.Describe(parameters[0].valueAsText)
            fldList = arcpy.ListFields(parameters[0].valueAsText)
            distanceList = []
            for fld in fldList:
                if fcDesc.baseName.startswith("persistent_targets"):
                    if fld.name.startswith("Ypers"):
                        distString = fld.name[5:]
                        distanceList.append(distString)
                else:
                    if fld.name.startswith("pers"):
                        distString = fld.name[4:]
                        distanceList.append(distString)
            parameters[1].filter.list = distanceList
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define variables from parameters
        targetsFC = parameters[0].valueAsText
        targetDesc = arcpy.Describe(targetsFC)
        workspace = targetDesc.path
        arcpy.env.workspace = workspace
        bufferDists = parameters[1].valueAsText
        bufferDistanceList = bufferDists.split(";")
        mxdPath = os.path.join(os.path.dirname(workspace), "templates", "temporal_analysis.mxd")
        mxd = arcpy.mapping.MapDocument(mxdPath)

        # ========================================== #
        # Create and populate VISIBLE subtype Field  #
        # ========================================== #

        # Add VISIBLE field
        fieldName = "VISIBLE"
        arcpy.AddField_management(targetsFC,fieldName,'SHORT')

        # Set VISIBLE as subtype
        arcpy.SetSubtypeField_management(targetsFC, fieldName)

        # Save subtypes to a dictionary
        stypeDict = {"0": "Look-a-Like", "1": "Dark Feature"}

        # use a for loop to cycle through the dictionary
        for code in stypeDict:
            arcpy.AddSubtype_management(targetsFC, code, stypeDict[code])

        # Set default subtype to "Dark Feature"
        arcpy.SetDefaultSubtype_management(targetsFC, "1")
        
        # Set each feature to a VISIBLE value of 1. This will be used in the visualisation analysis process to hide look-a-likes
        with arcpy.da.UpdateCursor(targetsFC, fieldName) as cursor:
             for row in cursor:
                 row[0] = 1
                 cursor.updateRow(row)

        # add VISIBLE field to describe
        targetDesc = arcpy.Describe(targetsFC)

        arcpy.CheckOutExtension("Spatial")

        # Set log configuration
        logPath = os.path.join(os.path.dirname(workspace), "logs")
        if not os.path.exists(logPath):
            os.makedirs(logPath)
        logFile = os.path.join(logPath, "visuals.log")
        logging.basicConfig(filename=logFile, format='%(asctime)s -- %(message)s', datefmt='%d/%m/%Y %H:%M:%S', level=logging.INFO)
        logging.info("Starting temporalVisuals.py script...\n")
        logging.info("Check Out Extension: Spatial Analyst extension checked out\n")

        # Define variables according to nature of analysis to visualize (day-to-day within year or overall year-to-year)
        if targetDesc.name.startswith("RS2_"):
            yrPersisBool = False
        else:
            yrPersisBool = True
        if yrPersisBool:
            dataset = "pt_visual"
            pointFC = os.path.join(workspace, dataset, "pt_pointFC")
            bufferPath = os.path.join(workspace, dataset, "pt_")
            weight = "Ywght"
            persis = "Ypers"
            clusterID = "Yclst"
        else:
            dataset = targetDesc.name + "_visual"
            pointFC = os.path.join(workspace, dataset, targetDesc.name + "_pointFC")
            bufferPath = os.path.join(workspace, dataset, targetDesc.name + "_")
            weight = "wght"
            persis = "pers"
            clusterID = "clst"
        persisField = persis + bufferDistanceList[0]
        where_clause = '{} IS NOT NULL And VISIBLE = 1'.format(persisField)

        # ============================ #
        # Create visualization results #
        # ============================ #

        # Create feature dataset to hold visualization feature classes
        if not arcpy.Exists(dataset):
            arcpy.AddMessage("\nCreating visualization dataset...")
            sr = targetDesc.spatialReference
            arcpy.CreateFeatureDataset_management(workspace, dataset, sr)
            logging.info("Create Feature Dataset: '%s' feature dataset created in '%s' workspace to contain visualization products\n", dataset, workspace)

        # Create points feature class for buffer distance calculations
        if arcpy.Exists(pointFC):
            arcpy.Delete_management(pointFC)
            logging.info("Delete: '%s' feature class deleted to allow overwrite", pointFC)
        arcpy.AddMessage("\nCreating points feature class...")
        targetLyr = "filteredTargetLyr"
##        persisField = persis + bufferDistanceList[0]
##        where_clause = persisField + " IS NOT NULL"
        arcpy.MakeFeatureLayer_management(targetsFC, targetLyr, where_clause)
        logging.info("Make Feature Layer: '%s' layer created from '%s' feature class with selection of features where persistence fields at '%s' meters are not null", targetLyr, targetsFC, bufferDistanceList[0])
        arcpy.FeatureToPoint_management(targetLyr, pointFC, "CENTROID")
        logging.info("Feature to Point: '%s' points feature class created from centroid of features in '%s' layer\n", pointFC, targetLyr)

        # Create buffer feature class for each desired buffer distance
        arcpy.AddMessage("\nCreating buffer feature classes...")
        for radius in bufferDistanceList:
            logging.info("Processing buffer feature class at '%s' meters", radius)
            if radius != '0':
                persisField = persis + radius
                clusterField = clusterID + radius
                bufferOutput = bufferPath + radius + "_radius"
                if arcpy.Exists(bufferOutput):
                    arcpy.Delete_management(bufferOutput)
                    logging.info("Delete: '%s' feature class deleted to allow overwrite", bufferOutput)
                ptLyr = "pointsLyr" + radius
                arcpy.MakeFeatureLayer_management(pointFC, ptLyr)
                logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", ptLyr, pointFC)
                distance = radius + " Meters"
                arcpy.AddMessage("Buffering at " + radius + " meters...")
                arcpy.Buffer_analysis(ptLyr, bufferOutput, distance, "FULL", "ROUND", "LIST", clusterField, "GEODESIC")
                logging.info("Buffer: '%s' buffer feature class created from '%s' layer at a distance of '%s' meters", bufferOutput, ptLyr, distance)
            logging.info("Processing for buffer feature class at '%s' meters complete\n", radius)

        # Create background heat map (kernel density based on concentration of individual dark targets)
        arcpy.AddMessage("\nCreating heat map...")
        heatPtLyr = "heatPtLyr"
##        where_clause = persis + bufferDistanceList[0] + " IS NOT NULL"
        arcpy.MakeFeatureLayer_management(pointFC, heatPtLyr, where_clause)
        logging.info("Make Feature Layer: '%s' layer created from '%s' points feature class with selection of features where persistence fields at '%s' meters are not null", heatPtLyr, pointFC, bufferDistanceList[0])
        outKDens = arcpy.sa.KernelDensity(heatPtLyr, "NONE", "#", "#", "SQUARE_KILOMETERS", "#", "GEODESIC")
        logging.info("Kernel Density: '%s' kernel density raster created from '%s' layer", outKDens)
        heatMap = os.path.join(workspace, "HeatMap")
        outKDens.save(heatMap)
        logging.info("Save: '%s' kernel density raster saved as '%s'\n", outKDens, heatMap)

        # ======================================================= #
        # Update template map document with visualization results #
        # ======================================================= #

        arcpy.AddMessage("\nUpdating map document template with visualization results...")
        logging.info("Processing to update '%s' map document with visualization results", mxdPath)
        df = arcpy.mapping.ListDataFrames(mxd)[0]
        darkTargetsLyr = arcpy.mapping.ListLayers(mxd)[0]
        groupLyr = arcpy.mapping.ListLayers(mxd)[1]

        # Update data source of dark targets layer in map document
        arcpy.AddMessage("Replacing dark targets layer data source...")
##        arcpy.mapping.ListLayers(mxd)[0].replaceDataSource(targetDesc.path, "FILEGDB_WORKSPACE", targetDesc.name)
        darkTargetsLyr.replaceDataSource(targetDesc.path, "FILEGDB_WORKSPACE", targetDesc.name)
        logging.info("Replace Data Source (Mapping): Data source for '%s' layer set to '%s'", darkTargetsLyr, os.path.join(targetDesc.path, targetDesc.name))

        # Add layer of persistent dark targets (filtered) to map document
        arcpy.AddMessage("Adding filtered persistent dark targets layer...")
        filterLyr = "filteredTargets"
##        where_clause = persis + bufferDistanceList[0] + " IS NOT NULL"
##        arcpy.MakeFeatureLayer_management(targetsFC, filterLyr, where_clause)
        addLayer = arcpy.mapping.Layer(targetLyr)
        addLayer.name = "Filtered Targets (applied selection criteria)"
        logging.info("Layer (Mapping): '%s' layer object created from '%s' layer", addLayer.name, targetLyr)
        addLayer.visible = True
        arcpy.mapping.AddLayer(df, addLayer, "TOP")
        logging.info("Add Layer (Mapping): '%s' layer added to top of dataframe", addLayer.name)

        # Add heat map layer to map document
        arcpy.AddMessage("Adding heat map layer...")
        heatMapLyr = "heatMapLyr"
        arcpy.MakeRasterLayer_management(heatMap, heatMapLyr)
        logging.info("Make Raster Layer: '%s' layer created from '%s' raster", heatMapLyr, heatMap)
        addLayer = arcpy.mapping.Layer(heatMapLyr)
        addLayer.name = "Heat Map"
        logging.info("Layer (Mapping): '%s' layer object created from '%s' layer", addLayer.name, heatMapLyr)
        sourceLayerPath = os.path.join(os.path.dirname(workspace), "templates", "heatmap.lyr")
        sourceLayer = arcpy.mapping.Layer(sourceLayerPath)
        logging.info("Layer (Mapping): '%s' layer object created from '%s' layer", sourceLayer.name, sourceLayerPath)
        arcpy.mapping.UpdateLayer(df, addLayer, sourceLayer)
        logging.info("Update Layer (Mapping): '%s' layer updated with properties of '%s' layer", addLayer.name, sourceLayer.name)
        arcpy.mapping.AddLayer(df, addLayer, "BOTTOM")
        logging.info("Add Layer (Mapping): '%s' layer added to bottom of dataframe", addLayer.name)

        # Iterate through buffer distances to update map document with corresponding visualization results.
        for radius in bufferDistanceList:
            arcpy.AddMessage("Adding visualization layers for persistence at " + radius + " meters...")
            dist = int(radius)
            if dist < 1000:
                distKm = str(dist) + " m"
            else:
                distKm = str(dist/1000) + " km"
            persisField = persis + radius
            weightField = weight + radius
            clusterField = clusterID + radius

            # Add blank group layer (copy from template group layer)
            arcpy.mapping.AddLayer(df, groupLyr, "TOP")
            newGpLyr = arcpy.mapping.ListLayers(mxd)[0]
            newGpLyr.name = "Persistent Targets - " + distKm
            logging.info("Add Layer (Mapping): '%s' group layer added to top of dataframe", newGpLyr.name)

            # Add persistence count layer
            arcpy.AddMessage("Adding persistence count layer...")
            persisLyr = "persisLyr" + radius
##            where_clause = persisField + " IS NOT NULL"
            arcpy.MakeFeatureLayer_management(targetsFC, persisLyr, where_clause)
            addLayer = arcpy.mapping.Layer(persisLyr)
            addLayer.name = "Persistence by Time (Persistence Count)"
            logging.info("Layer (Mapping): '%s' layer object created from '%s' layer", addLayer.name, persisLyr)
            sourceLayerPath = os.path.join(os.path.dirname(workspace), "templates", "persis_weight.lyr")
            sourceLayer = arcpy.mapping.Layer(sourceLayerPath)
            logging.info("Layer (Mapping): '%s' layer object created from '%s' layer", sourceLayer.name, sourceLayerPath)
            arcpy.mapping.UpdateLayer(df, addLayer, sourceLayer)
            addLayer.symbology.valueField = persisField
            addLayer.symbology.addAllValues()
            logging.info("Update Layer (Mapping): '%s' layer updated with properties and persistence field values for symbology of '%s' layer", addLayer.name, sourceLayer.name)
            arcpy.mapping.AddLayerToGroup(df, newGpLyr, addLayer)
            logging.info("Add Layer to Group (Mapping): '%s' layer added to '%s' group layer", addLayer.name, newGpLyr.name)

            # Add weight value layer
            arcpy.AddMessage("Adding weight value layer...")
            addLayer.name = "Weight Value (Target Count within Radius)"
            logging.info("Persistence count layer object renamed to '%s'", addLayer.name)
            arcpy.mapping.UpdateLayer(df, addLayer, sourceLayer)
            addLayer.symbology.valueField = weightField
            addLayer.symbology.addAllValues()
            logging.info("Update Layer (Mapping): '%s' layer updated with properties and weight field values for symbology of '%s' layer", addLayer.name, sourceLayer.name)
            arcpy.mapping.AddLayerToGroup(df, newGpLyr, addLayer, "BOTTOM")
            logging.info("Add Layer to Group (Mapping): '%s' layer added to bottom of '%s' group layer", addLayer.name, newGpLyr.name)

            # Add cluster ID buffer layer
            arcpy.AddMessage("Adding cluster ID layer...")
            if radius != '0':
                radiusFC = bufferPath + radius + "_radius"
                radiusLyr = "radiusLyr" + radius
                arcpy.MakeFeatureLayer_management(radiusFC, radiusLyr)
                logging.info("Make Feature Layer: '%s' layer created from '%s' feature class", radiusLyr, radiusFC)
                addLayer = arcpy.mapping.Layer(radiusLyr)
            addLayer.name = "Clustered Targets (ID.monthsTimeSpan)"
            if radius != '0':
                logging.info("Layer (Mapping): '%s' layer object created from '%s' layer", addLayer.name, radiusLyr)
            else:
                logging.info("Layer (Mapping): Weight value layer object renamed to '%s'", addLayer.name)
            sourceLayerPath = os.path.join(os.path.dirname(workspace), "templates", "radius.lyr")
            sourceLayer = arcpy.mapping.Layer(sourceLayerPath)
            arcpy.mapping.UpdateLayer(df, addLayer, sourceLayer)
            if radius != '0':
                addLayer.transparency = 70
            addLayer.symbology.valueField = clusterField
            addLayer.symbology.addAllValues()
            addLayer.labelClasses[0].expression = """ "<FNT size = '16'>" + [""" + clusterField + """] + "</FNT>" """
            addLayer.labelClasses[0].SQLQuery = clusterField + " IS NOT NULL"
            addLayer.showLabels = True
            logging.info("Update Layer (Mapping): '%s' layer updated with properties and cluster ID field values for symbology of '%s' layer", addLayer.name, sourceLayer.name)
            arcpy.mapping.AddLayerToGroup(df, newGpLyr, addLayer, "BOTTOM")
            logging.info("Add Layer to Group (Mapping): '%s' layer added to bottom of '%s' group layer", addLayer.name, newGpLyr.name)

        arcpy.mapping.RemoveLayer(df, groupLyr)
        logging.info("Remove Layer (Mapping): '%s' template layer removed from map document", groupLyr.name)
        logging.info("Processing for update of '%s' map document with visualization results complete\n", mxdPath)
        arcpy.AddMessage("Saving analysis results map document from copy of template map document...")
        mxdCopy = os.path.join(os.path.dirname(workspace), "analysis_results.mxd")
        mxd.saveACopy(mxdCopy)
        logging.info("Save a Copy (mxd): '%s' saved from copy of '%s'", mxdCopy, mxdPath)
        del mxd

        arcpy.CheckInExtension("Spatial")
        logging.info("Check In Extension: Spatial Analyst extension checked back in")
        logging.info("temporalVisuals.py script finished\n\n")
        return