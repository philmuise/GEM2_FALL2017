#  Join Field
# -*- coding: utf-8 -*-
#
#  A faster Join Field tool
#
#  Esri, November 2015


import arcpy
import sys

inTable = arcpy.GetParameterAsText(0)
inJoinField = arcpy.GetParameterAsText(1)
joinTable = arcpy.GetParameterAsText(2)
outJoinField = arcpy.GetParameterAsText(3)
joinFields = arcpy.GetParameterAsText(4)

arcpy.AddMessage('\nJoining fields from {0} to {1} via the join {2}:{3}'.format(joinTable,inTable,inJoinField,outJoinField))

# Define generator for join data
def joindataGen(joinTable,fieldList,sortField):
    with arcpy.da.SearchCursor(joinTable,fieldList,sql_clause=['DISTINCT',
                                                               'ORDER BY '+sortField]) as cursor:
        for row in cursor:
            yield row

# Function for progress reporting
def percentile(n,pct):
    return int(float(n)*float(pct)/100.0)

# Add join fields
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
joinDataGen = joindataGen(joinTable,fieldList,outJoinField)
version = sys.version_info[0]
if version == 2:
    joinTuple = joinDataGen.next()
else:
    joinTuple = next(joinDataGen)
# 
fieldList = [inJoinField] + joinFields.split(';')
count = int(arcpy.GetCount_management(inTable).getOutput(0))
breaks = [percentile(count,b) for b in range(10,100,10)]
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

arcpy.SetParameter(5,inTable)
arcpy.AddMessage('\nDone.')


