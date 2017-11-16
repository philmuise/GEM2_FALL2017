#-------------------------------------------------------------------------------
# Name:        calcWghtAttr.py
# Purpose:     Used to add and calculate a weighted value field
#
# Author:      David Hennessy
#
# Created:     06-03-2017
#-------------------------------------------------------------------------------

# Import libraries
import arcpy
import os

# ASSIGN VARIABLE VALUES HERE---------------------------------------------------
# List of attributes to consider for the weighted value, format is ("Attribute Field", c1 value, c2 value, a value, b value)
atrFields = [["Lcard", .5, 1, 10, 15],
             ["PwindMin", .5, 1, 10, 15]]

# Name of weighted attribute field
addField = "WghtLH"

# Name of dark targets feature class from which to add and calculate a weighted value field
# =======================================================================================================  #
# Change in_table variable to point to RS2_* in order to add weighted value field to those feature classes #
# This is required to have the weighted field available for SQL filtering for the Temporal Analysis tool   #
# ======================================================================================================== #
in_table = "persistent_targets"
# in_table = "RS2_2010"
# in_table = "RS2_2011"
# in_table = "RS2_2012"
# ------------------------------------------------------------------------------

# Function used to calculate F value for every attribute
def calcFValue(atr, c1, c2, a, b):
    if atr <= a:
        f1 = c1
    if atr > b:
        f1 = c2
    else:
        f1 = c1 + (atr - a)/(b - a)
    return f1

# Function used to calculate the weighted value field
def calcWghtValue(wghtList):
    i = len(wghtList)
    WghtLH = sum(wghtList)/i
    return WghtLH

def main():
    # Determine path to dark targets feature class (based on relative position of script)
    tablePath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GEM2_Temporal_Analysis.gdb", in_table)

    # Add weighted value field, if necessary
    arcpy.AddField_management(tablePath, addField, "DOUBLE")

    # Determine fields to include for cursor iteration (fields used for attribute calculation)
    cursorFields = []
    for item in atrFields:
        cursorFields.append(item[0])
    cursorFields.append(addField)

    # Iterate through dark targets polygons using update cursor
    with arcpy.da.UpdateCursor(tablePath, cursorFields) as cursor:
        for row in cursor:
            wghtList = []
            for atrItem in atrFields:
                for cursorItem in cursorFields[:-1]:
                    if atrItem[0] == cursorItem:
                        valueIndex = cursorFields.index(cursorItem)
                        f1 = calcFValue(row[valueIndex], atrItem[1], atrItem[2], atrItem[3], atrItem[4])
                        wghtList.append(f1)
            row[len(row)-1] = calcWghtValue(wghtList)
            cursor.updateRow(row)

if __name__ == '__main__':
    main()
