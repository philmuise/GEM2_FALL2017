#! /usr/bin/env python
# -*- coding: Latin-1 -*-

#==============================================================================#
# HISTORY                                                                      #
# -------                                                                      #
# Developed by D. Hennessy, January 2017.                                      #
#==============================================================================#

# Libraries
# =========
import arcpy

# Reload steps required to refresh memory if Catalog is open when changes are made
import condition_darkTargets                                    # get module reference for reload
reload(condition_darkTargets)                                   # reload step 1
from   condition_darkTargets import condition_darkTargets             # reload step 2

# import createGDBStruct                                    # get module reference for reload
# reload(createGDBStruct)                                   # reload step 1
# from   createGDBStruct import createGDBStruct             # reload step 2

# import loadDarkTargets                                    # get module reference for reload
# reload(loadDarkTargets)                                   # reload step 1
# from   loadDarkTargets import loadDarkTargets             # reload step 2

# import parseOverlap                                    # get module reference for reload
# reload(parseOverlap)                                   # reload step 1
# from   parseOverlap import parseOverlap             # reload step 2

# import parseNoOverlap                                    # get module reference for reload
# reload(parseNoOverlap)                                   # reload step 1
# from   parseNoOverlap import parseNoOverlap             # reload step 2

# import evalAttributes                              # get module reference for reload
# reload(evalAttributes)                             # reload step 1
# from evalAttributes import evalAttributes # reload step 2

# import mergeAreas                                    # get module reference for reload
# reload(mergeAreas)                                   # reload step 1
# from   mergeAreas import mergeAreas             # reload step 2

import updateMasterGDB                                    # get module reference for reload
reload(updateMasterGDB)                                   # reload step 1
from updateMasterGDB import updateMasterGDB             # reload step 2

import temporalPersisDay                                    # get module reference for reload
reload(temporalPersisDay)                                   # reload step 1
from   temporalPersisDay import temporalPersisDay             # reload step 2

import temporalPersisYear                                    # get module reference for reload
reload(temporalPersisYear)                                   # reload step 1
from   temporalPersisYear import temporalPersisYear             # reload step 2

import temporalVisuals                                    # get module reference for reload
reload(temporalVisuals)                                   # reload step 1
from   temporalVisuals import temporalVisuals             # reload step 2

import getChloro                                    # get module reference for reload
reload(getChloro)                                   # reload step 1
from   getChloro import getChloro             # reload step 2

import applyChloro                                    # get module reference for reload
reload(applyChloro)                                   # reload step 1
from   applyChloro import applyChloro             # reload step 2

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "GEM2 Oil Seep Detection and Analysis"
        self.alias = "oil_seep_analysis"

        # List of tool classes associated with this toolbox
        self.tools = [condition_darkTargets, getChloro, applyChloro, updateMasterGDB, temporalPersisDay, temporalPersisYear, temporalVisuals]

def main():
	print "In GEM2_Oil_Seep_Detection_Analysis.pyt main()..."

if __name__ == '__main__':
    main()