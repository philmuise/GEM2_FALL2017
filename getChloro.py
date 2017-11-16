#! /usr/bin/env python
# -*- coding: utf-8 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
# Modified by Philippe Muise, September 2017                                   #
# Last modified: 15 Sept 2017 by Philippe Muise.                               #
#==============================================================================#
"""USAGE
Module imported and used as the "1a_Download Chlorophyll_a NetCDF Files" script
tool in the "GEM2_Oil_Seep_Detection_Analysis" Python Toolbox.

SUMMARY
Downloads MODIS chlorophyll_a data for those acquisition days where a corresponding
acquisition day for a dark targets feature class exists. If specified, chlorophyll_a data
is acquired for a range of days around each dark targets feature class.

INPUT
- Folder Location of Dark Targets GDBs (user input): Folder containing the geodatabases
produced by "1_Condition Yearly Dark Targets Data". The script will iterate through
the geodatabases in order to determine the dates required to download the appropriate
chlorophyll_a raster data.

- Chlorophyll_a Data FTP Directory (default user input): String parameter containing
the FTP directory where the chlorophyll_a MODIS data is available for download.

OUTPUT
- Chlorophyll_a NetCDF Files (automated output): Chlorophyll_a raster data in
NetCDF format. Each raster file consists of the global acquisition data for the
specified day. Downloaded files are placed in the "Auxiliary" folder (created if
necessary), inside which a "Chlorophyll" folder organizes the downloads by year
("2010", "2011", etc). The "Auxiliary" folder is created in the same directory as
the selected Folder Location of Dark Targets GDBs (usually the "Products" folder).

ADDITIONAL FUNCTIONS (explained in script below)
- yearDay
- getChloroFile"""

# Libraries
# =========
import arcpy
import os
import datetime
import ftplib
from ftplib import FTP
import logging
import time


class getChloro(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1a_Download Chlorophyll_a NetCDF Files"
        self.description = "Downloads MODIS chlorophyll_a data for each\
         RADARSAT-2 acquisition found in the dark targets yearly GDBs."
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
            displayName="Chlorophyll_a Data FTP Directory",
            name="ftp_dir",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        params1.value = 'podaac-ftp.jpl.nasa.gov/allData/modis/L3/aqua/chlA/v2014.0/4km/daily/'

        params2 = arcpy.Parameter(
            displayName="Chlorophyll Day Range",
            name="Day Range",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")



        params = [params0, params1, params2]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        # Spatial Analyst tool licence info??
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
        logging.info("Starting getChloro.py script...\n")

        # Define variables from parameters
        working_folder = parameters[0].valueAsText
        local_chloroFolder = os.path.join(os.path.dirname(working_folder), "Auxiliary", "Chlorophyll")
        if not os.path.exists(local_chloroFolder):
            os.makedirs(local_chloroFolder)
        ftpDir = parameters[1].valueAsText
        dayRange = parameters[2].value

        # Set value for FTP address of host site for MODIS data
        fileHostPath = ftpDir.split('/')[0]

        # Set value for FTP file directory pointing to daily chlorophyll_a data
        fileDir = '/' + '/'.join(ftpDir.split('/')[1:])

        # Determine list of yearly GDBs in workspace
        arcpy.env.workspace = working_folder
        gdbList = arcpy.ListWorkspaces("*", "FileGDB")
        arcpy.AddMessage("Workspace contains the following " + str(len(gdbList)) + " GDBs: " + str(gdbList))

        # Connect to ftp host
        arcpy.AddMessage("\nConnecting to host ftp site2: " + fileHostPath)
        ftp = FTP(fileHostPath)
        ftp.login()
        logging.info("Login established to FTP host '%s'\n", fileHostPath)

        # Iterate through yearly GDBs in order to determine required chlorophyll_a files for download
        arcpy.AddMessage("\nConnected. Verifying files to download...")
        for gdb in gdbList:

            # Determine list of feature classes requiring files in current GDB
            arcpy.env.workspace = gdb
            logging.info("Processing '%s' geodatabase", gdb)
            fcList = arcpy.ListFeatureClasses()

            arcpy.AddMessage("\nGDB contains the following " + str(len(fcList)) + " feature classes: " + str(fcList))
            logging.info("List of acquisition days requiring file downloads: '%s'\n", str(fcList))

            # Iterate through feature classes in GDB
            for fc in fcList:
                arcpy.AddMessage("Started to go through days")
                # Determine corresponding year and date path for location on ftp server
                dateFolder = self.yearDay(fc.split('_')[1], dayRange)
                arcpy.AddMessage("{}".format(dateFolder))

                for day in dateFolder:
                    chloroFilePath = fileDir + day
                    arcpy.AddMessage("{}".format(chloroFilePath))
                    # Initiate download of files for current feature class
                    logging.info("Attempting file downloads for '%s' feature class\n", fc)
                    for tries in range(5):
                      try:
                             self.getChloroFile(ftp, chloroFilePath, local_chloroFolder)
                             break
                      except ftplib.all_errors as e:
                             x = 20
                             arcpy.AddMessage('\n --------------------ERROR: FAILED ATTEMPT #{a} of 5. WILL ATTEMPT TO DOWNLOAD FILE AGAIN IN {x} SECONDS-----------------\n'.format(a = tries,x = x))
                             time.sleep(x)



            logging.info("Processing for '%s' geodatabase complete\n", gdb)

        # Disconnect from ftp host
        ftp.quit()
        arcpy.AddMessage("\nChlorophyll file downloads complete.")
        logging.info("getChloro.py script finished\n\n")

        return

    def yearDay(self, fc_dateString, dayRange):
        """Calculate the day of the year for each RADARSAT-2 acquisition (to conform to MODIS naming convention) and the day of year within the range desired

        Parameter:
            fc_dateString = Date string acquired from the feature class name in the input geodatabase,
            conforming to the following format: YYYYmmDD (e.g. 20100925 for 25 September 2010)
            dayRange = Integer input by user that sets the range +/- of days around fc_dateString for download of chlorophyll data.

        Return:
            Returns list of sub-directory strings to be concatenated with ftp file directory in order to point to the required year and day of the year to access the desired MODIS imagery,
            conforming to the following format: YYYY/DDD (e.g. 2010/268 for 25 September 2010)
        Edits:
              Originally developed by David H. Altered by Philippe Muise
        """
        year = fc_dateString[:4]
        month = fc_dateString[4:6].lstrip("0")
        day = fc_dateString[-2:].lstrip("0")
        fc_date = datetime.date(int(year), int(month), int(day))
        fc_dateList = [fc_date]
        for i in range(dayRange):
            fc_dateList.insert(0,fc_date - datetime.timedelta(days = i + 1))
            fc_dateList.append(fc_date + datetime.timedelta(days = i + 1))

        chloroDateList = []
        for chloroDate in fc_dateList:
            yDay = chloroDate.timetuple().tm_yday
            chloroDateList.append(str(chloroDate.year) + '/' + str(yDay).rjust(3,'0'))

        return chloroDateList

    def getChloroFile(self, ftp, chloroFilePath, localChloro):
        """Download chlorophyll_a data corresponding to the identified RADARSAT-2 acquisition day.

        Parameters:
            ftp = The ftp connection object, activated via connection to the ftp upon execution of this script.
            chloroFilePath = The folder directory on the ftp server specific to the required year and day of MODIS acquisition
            localChloro = The local folder directory, normally named "Chlorophyll", in which the chlorophyll_a data is downloaded

        Return:
            No return"""
        # Change working directory on ftp server to required year and day of the chlorophyll_a data.
        logging.info("Accessing '%s' on ftp server", chloroFilePath)
        ftp.cwd(chloroFilePath)
        arcpy.AddMessage("{}".format(chloroFilePath))


        # List all files in current ftp server folder (should be 1x .nc file and 1x .md5 file)
        files = ftp.nlst()
        logging.info("Directory contains following files to download: '%s'", str(files))

        # Identify year of data in order to point to appropriate local folder for download
        year = chloroFilePath.split('/')[len(chloroFilePath.split('/'))-2]

        # Iterate through files in current ftp server folder
        for item in files:

            # Determine local paths for file downloads (within appropriate year folder)
            local_folderPath = os.path.join(localChloro, year)
            local_filePath = os.path.join(local_folderPath, item)

            # Check if file has already been downloaded
            if os.path.exists(local_filePath):
                arcpy.AddMessage(item + " already downloaded.")
                logging.info("'%s' already downloaded in '%s'", item, local_folderPath)

            # Initiate file download
            else:

                # Check if year folder already exists or needs to be created on local directory
                if not os.path.exists(local_folderPath):
                    os.makedirs(local_folderPath)
                    logging.info("'%s' created for file download", local_folderPath)

                # Download file
                arcpy.AddMessage("Downloading " + item + "... (" + str(ftp.size(item)/1000000) + " MB)")
                logging.info("Starting download of '%s'", item)
                local_file = open(local_filePath, 'wb')
                ftp.retrbinary('RETR ' + item, open(local_filePath, 'wb').write)
                local_file.close()
                logging.info("Download of '%s' complete", item)

        logging.info("Downloads from '%s' complete\n", chloroFilePath)