#-------------------------------------------------------------------------------
# Name:        joinAttrFromCSV.py
#
# Author:      David Hennessy, with code snippets from Esri's Join_Field.py (as
#              a replacement to the Join Field geoprocessing tool, which suffers
#              from exceedingly lengthy processing times.)
#
# Created:     07-03-2017
# Credit:      Esri's Join_Field.py from
#              http://www.arcgis.com/home/item.html?id=da1540fb59d84b7cb02627856f65a98d
#-------------------------------------------------------------------------------

"""This script joins newly calculated values from the dark target CSV to its
corresponding feature class in the GEM2_Temporal_Analysis GDB.

Requirements:
    - This script must be executed in the same folder where the CSV file and
    analysis GDB are both located. (Usually in the 'Results' folder)

    - The Join will utilize the 'OBJECTID' field to join the CSV file to the
    feature class. This is the only obligatory field that must be present in the
     CSV file, in addition to the other fields to add, in order for the join to
     complete successfully.

    - Three variables require user input and are available in the 'ASSIGN
    VARIABLE VALUE HERE' section below. These variables confirm the name of the
     input CSV file, the name of the feature class in the Analysis GDB, and the
     list of fields to add from the CSV to the feature class"""

# Import libraries
print "Importing python libraries (arcpy, os, sys)..."
import arcpy
import os
import sys

# ASSIGN VARIABLE VALUES HERE---------------------------------------------------
# Name of input csv file
inputCSV = "persistent_targets_2010to2012.csv"

# Name of feature class in Analysis GDB to which the values will be joined
inTable = "persistent_targets_2010to2012"

# List of fields from the input CSV that will be added to the feature class.
addFields = ["testpy"]

# If multiple fields to add are desired, the format to follow is:
##addFields = ["fld_1",
##              "fld_2",
##              "fld_3"]
# ------------------------------------------------------------------------------

# Define generator for join data (copied from Esri's Join_Field.py)-------------
def joindataGen(joinTable,fieldList,sortField):
    with arcpy.da.SearchCursor(joinTable,fieldList,sql_clause=['DISTINCT',
                                                               'ORDER BY '+sortField]) as cursor:
        for row in cursor:
            yield row
# ------------------------------------------------------------------------------

# Function for progress reporting (copied from Esri's Join_Field.py)------------
def percentile(n,pct):
    return int(float(n)*float(pct)/100.0)
# ------------------------------------------------------------------------------

def main():
    # Determine arcpy workspace
    analysisGDB = "GEM2_Temporal_Analysis.gdb"
    arcpy.env.workspace = analysisGDB

    # Assign variables for import of csv to gdb table
    csvPath = os.path.abspath(inputCSV)
    gdbPath = os.path.join(os.path.dirname(__file__), analysisGDB)
    joinTable = os.path.splitext(inputCSV)[0] + "_table"

    # Import csv table into gdb
    print "\nImporting CSV as table into Analysis GDB..."
    if arcpy.Exists(joinTable):
        arcpy.Delete_management(joinTable)
    arcpy.TableToTable_conversion(csvPath, gdbPath, joinTable)

    # Assign variables for join process
    joinField = "OBJECTID"
##    inTable = "persistent_targets"

    # Add join fields (adapted from Esri's Join_Field.py)-----------------------
    print '\nAdding join fields...'
    fList = [f for f in arcpy.ListFields(joinTable) if f.name in addFields]
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
    # --------------------------------------------------------------------------

    # Write values to join fields (adapted from Esri's Join_Field.py)-----------
    print '\nJoining data...'
    # Create generator for values
    fieldList = [joinField] + addFields
    joinDataGen = joindataGen(joinTable,fieldList,joinField)
    version = sys.version_info[0]
    if version == 2:
        joinTuple = joinDataGen.next()
    else:
        joinTuple = next(joinDataGen)
    #
    count = int(arcpy.GetCount_management(inTable).getOutput(0))
    breaks = [percentile(count,b) for b in range(10,100,10)]
    j = 0
    with arcpy.da.UpdateCursor(inTable,fieldList,sql_clause=(None,'ORDER BY '+joinField)) as cursor:
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
    # --------------------------------------------------------------------------

    # Delete gdb table (working file) from analysis GDB
    print "\nDeleting CSV table in Analysis GDB..."
    arcpy.Delete_management(joinTable)

if __name__ == '__main__':
    main()
