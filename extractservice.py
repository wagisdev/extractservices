#-------------------------------------------------------------------------------
# Name:     Portal Feature Copier
# Purpose:  This script extracts features and their attachments stored within
#           ArcGIS Online or Portal.  It then strips any downloaded relationship
#           drops the attached table and then projects the feature class into its
#           target projection.  Mail notifications for failures and completion are
#           included in the process.
#
# Author:   John Spence
#
# Created:  8/25/2020
# Modified:
# Modification Purpose:
#
#
#-------------------------------------------------------------------------------

# 888888888888888888888888888888888888888888888888888888888888888888888888888888
# ------------------------------- Configuration --------------------------------
# Pretty simple setup.  Just change your settings/configuration below.  Do not
# go below the "DO NOT UPDATE...." line.
#
# 888888888888888888888888888888888888888888888888888888888888888888888888888888

# Project Store Location
path_Proj = r'C:\ProjectPath\project.aprx'

# Data Store Location
path_DataProcessing = r'C:\ProjectPath\Pull-Processing.sde'
path_DataFinal = r'C:\ProjectPath\Pull-Final.sde'

# Target Projection
targetSRID = 6597

# Send confirmation of rebuild to
email_target = 'john@gis.dev'
email_customer = 'john@gis.dev'
email_subjectSchema = '' #Whatever you want the subject to be here.

# Configure the e-mail server and other info here.
mail_server = 'smtprelay.gis.dev'
mail_from = 'Message<noreply@gis.dev>'

# Portal Configs
portalURL = 'https://www.arcgis.com'
portalUser = '' #Your User Name
portalPW = '' #Your Password encoded Base64.  Remove decode if you are not practicing security by obscurity.

# ------------------------------------------------------------------------------
# DO NOT UPDATE BELOW THIS LINE OR RISK DOOM AND DISPAIR!  Have a nice day!
# ------------------------------------------------------------------------------

import arcpy, datetime, smtplib, string, os, base64

# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------


def main(portalURL,portalUser,portalPW):
#-------------------------------------------------------------------------------
# Name:        Function - main
# Purpose:  Starts the whole thing.
#-------------------------------------------------------------------------------

    connect(portalURL,portalUser,portalPW)
    findInfo()
    findProj()
    sendFinish()

    return

def connect(portalURL,portalUser,portalPW):
#-------------------------------------------------------------------------------
# Name:        Function - connect
# Purpose:  Logs into ArcGIS online for secured applications.
#-------------------------------------------------------------------------------

    try:
        portalPWd = base64.b64decode(portalPW)
        arcpy.SignInToPortal(portalURL, portalUser, portalPWd)
        print ('    Portal sign-on success...')
    except:
        print ('    WARNING - Unable to log on to Portal.  Please check your settings and try again.')

    return

def findInfo():
#-------------------------------------------------------------------------------
# Name:        Function - findInfo
# Purpose:  Looks up information about the databases and stores it for use.
#-------------------------------------------------------------------------------

    try:
        desc = arcpy.Describe(path_DataProcessing)
        dbNameTemp = desc.connectionProperties.database
        dbName.append(dbNameTemp)
        dbUserTemp = desc.connectionProperties.user
        dbUser.append(dbUserTemp)
    except:
        print ('FAILURE:  Unable to snag info from {}'.format(path_DataProcessing))
        mail_priority = '1'
        mail_subject = 'Portal Feature Copier Failure:  Find Info'
        mail_msg = ('A failure to find info has occured.  The error is as follows: \n\n' +
        'Error:  Unable to snag info from {}'.format(path_DataProcessing))

        sentMailNote(mail_priority, mail_subject, mail_msg)
        exit()

    try:
        desc = arcpy.Describe(path_DataFinal)
        dbNameTemp = desc.connectionProperties.database
        dbName.append(dbNameTemp)
        dbUserTemp = desc.connectionProperties.user
        dbUser.append(dbUserTemp)
    except:
        print ('FAILURE:  Unable to snag info from {}'.format(path_DataFinal))

        mail_priority = '1'
        mail_subject = 'Portal Feature Copier Failure:  Find Info'
        mail_msg = ('A failure to find info has occured.  The error is as follows: \n\n' +
        'Error:  Unable to snag info from {}'.format(path_DataFinal))

        sentMailNote(mail_priority, mail_subject, mail_msg)
        exit()

    print (dbName, dbUser)

    return

def findProj():
#-------------------------------------------------------------------------------
# Name:        Function - findProj
# Purpose:  Pulls up the ArcGIS Pro Project and begins the extraction process.
#-------------------------------------------------------------------------------

    aprx = arcpy.mp.ArcGISProject(path_Proj)
    for maps in aprx.listMaps():
        mapName = maps.name
        currentDT = datetime.datetime.now()
        print ('Publish Task Started:  {}'.format(str(currentDT)))
        print ('    Map name:  {}'.format(mapName))

        m_var = '{}'.format(mapName)
        m = aprx.listMaps(m_var)[0]
        for lyr in m.listLayers('*'):
            if lyr.isGroupLayer == False and lyr.isBasemapLayer == False:
                print ('        \nTarget ID\'d as:  {}'.format(lyr))
                extractService(lyr)


        currentDT = datetime.datetime.now()

    return

def findExists_SCRATCH(target):
#-------------------------------------------------------------------------------
# Name:        Function - findExists_Scratch
# Purpose:  Checks if the item that is going to be copied exists in the scratch
#           DB prior to copying in.
#-------------------------------------------------------------------------------

    arcpy.env.workspace = path_DataProcessing

    fcTarget = dbUser[0] + '.' + target

    if arcpy.Exists(fcTarget):
        print ('        Found {}'.format(fcTarget))
        targetDesc = path_DataProcessing + '\\' + fcTarget
        desc = arcpy.Describe(targetDesc)
        fcTarget_REL = desc.relationshipClassNames
        if fcTarget_REL:
            print ('        Relationship Detected.')
            print ('        ',fcTarget_REL)
            for RELItem in fcTarget_REL:
                RelDescription = arcpy.Describe(RELItem)
                print('%-25s %s' % ('       Backward Path Label:', RelDescription.backwardPathLabel))
                print('%-25s %s' % ('       Cardinality:', RelDescription.cardinality))
                print('%-25s %s' % ('       Class key:', RelDescription.classKey))
                print('%-25s %s' % ('       Destination Class Names:', RelDescription.destinationClassNames))
                print('%-25s %s' % ('       Forward Path Label:', RelDescription.forwardPathLabel))
                print('%-25s %s' % ('       Is Attributed:', RelDescription.isAttributed))
                print('%-25s %s' % ('       Is Composite:', RelDescription.isComposite))
                print('%-25s %s' % ('       Is Reflexive:', RelDescription.isReflexive))
                print('%-25s %s' % ('       Key Type:', RelDescription.keyType))
                print('%-25s %s' % ('       Notification Direction:', RelDescription.notification))
                print('%-25s %s' % ('       Origin Class Names:', RelDescription.originClassNames))

                for RELTable in RelDescription.destinationClassNames:
                    print ('\n')
                    print ('        Deleting: {}'.format(RELTable))
                    arcpy.Delete_management(RELTable)
                print ('        Deleting: {}'.format(RELItem))
                arcpy.Delete_management(RELItem)
            print ('        Deleting: {}'.format(fcTarget))
            arcpy.Delete_management(fcTarget)
        else:
            print ('        No Relationship Detected.')
            print ('\n')
            print ('        Deleting: {}'.format(fcTarget))
            arcpy.Delete_management(fcTarget)
    return

def findExists_PREP(target):
#-------------------------------------------------------------------------------
# Name:        Function - Prep
# Purpose:  Performs the same functions as scratch.  Checks if it exists and
#           deletes it prior to starting work.
#-------------------------------------------------------------------------------

    arcpy.env.workspace = path_DataProcessing

    fcTarget = dbUser[0] + '.' + target

    if arcpy.Exists(fcTarget):
        print ('        Found {}'.format(fcTarget))
        targetDesc = path_DataProcessing + '\\' + fcTarget
        desc = arcpy.Describe(targetDesc)
        fcTarget_REL = desc.relationshipClassNames
        if fcTarget_REL:
            print ('        Relationship Detected.')
            print ('        ',fcTarget_REL)
            for RELItem in fcTarget_REL:
                RelDescription = arcpy.Describe(RELItem)
                print('%-25s %s' % ('       Backward Path Label:', RelDescription.backwardPathLabel))
                print('%-25s %s' % ('       Cardinality:', RelDescription.cardinality))
                print('%-25s %s' % ('       Class key:', RelDescription.classKey))
                print('%-25s %s' % ('       Destination Class Names:', RelDescription.destinationClassNames))
                print('%-25s %s' % ('       Forward Path Label:', RelDescription.forwardPathLabel))
                print('%-25s %s' % ('       Is Attributed:', RelDescription.isAttributed))
                print('%-25s %s' % ('       Is Composite:', RelDescription.isComposite))
                print('%-25s %s' % ('       Is Reflexive:', RelDescription.isReflexive))
                print('%-25s %s' % ('       Key Type:', RelDescription.keyType))
                print('%-25s %s' % ('       Notification Direction:', RelDescription.notification))
                print('%-25s %s' % ('       Origin Class Names:', RelDescription.originClassNames))

                for RELTable in RelDescription.destinationClassNames:
                    print ('\n')
                    print ('        Deleting: {}'.format(RELTable))
                    arcpy.Delete_management(RELTable)
                print ('        Deleting: {}'.format(RELItem))
                arcpy.Delete_management(RELItem)
        else:
            print ('        No Relationship Detected.')

    return

def findExists_FINAL(target, path_Workspace):
#-------------------------------------------------------------------------------
# Name:        Function - findExists_Final
# Purpose:  Checks the final destination if an item exists.
#-------------------------------------------------------------------------------

    arcpy.env.workspace = path_Workspace

    fcTarget = dbUser[1] + '.' + target

    if arcpy.Exists(fcTarget):
        print ('        Found {}'.format(fcTarget))
        arcpy.Delete_management(fcTarget)
    else:
        print ('        {} not found at target'.format(fcTarget))

    return

def projectInto_FINAL(target):
#-------------------------------------------------------------------------------
# Name:        Function - projectInto_Final
# Purpose:  Projects the source in Scratch to the Final Destination
#-------------------------------------------------------------------------------

    fcSource = dbName[0] + '.' + dbUser[0] + '.' + target
    inFC = os.path.join(path_DataProcessing, fcSource)
    fcTarget = dbName[1] + '.' + dbUser[1] + '.' + target
    outFC = os.path.join(path_DataFinal, fcTarget)

    out_coordinate_system = arcpy.SpatialReference(targetSRID)

    try:
        # Add editor tracking fields
        arcpy.AddField_management(in_table=inFC, field_name="SysCreateDate", field_type="DATE", field_precision="", field_scale="", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
        arcpy.AddField_management(in_table=inFC, field_name="SysCreateUser", field_type="TEXT", field_precision="", field_scale="", field_length="80", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
        arcpy.AddField_management(in_table=inFC, field_name="SysChangeDate", field_type="DATE", field_precision="", field_scale="", field_length="", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")
        arcpy.AddField_management(in_table=inFC, field_name="SysChangeUser", field_type="TEXT", field_precision="", field_scale="", field_length="80", field_alias="", field_is_nullable="NULLABLE", field_is_required="NON_REQUIRED", field_domain="")

        # Enable editor tracking
        arcpy.EnableEditorTracking_management(inFC, "SysCreateUser", "SysCreateDate", "SysChangeUser", "SysChangeDate", "NO_ADD_FIELDS","UTC")
    except Exception as error_editorTracking:
        print ('Status:  Failure!')
        print(error_editorTracking.args[0])

        mail_priority = '1'
        mail_subject = 'Portal Feature Copier Failure:  Add editor tracking fields failed'
        mail_msg = ('A failure to project into final has occured.  The error is as follows: \n\n' +
        'Error:  {}'.format(error_editorTracking.args[0]))

        sentMailNote(mail_priority, mail_subject, mail_msg)
        exit()

    try:
        arcpy.Project_management(inFC, outFC, out_coordinate_system)

    except Exception as error_project_layer:
        print ('Status:  Failure!')
        print(error_project_layer.args[0])

        mail_priority = '1'
        mail_subject = 'Portal Feature Copier Failure:  Projection Into Final'
        mail_msg = ('A failure to project into final has occured.  The error is as follows: \n\n' +
        'Error:  {}'.format(error_project_layer.args[0]))

        sentMailNote(mail_priority, mail_subject, mail_msg)
        exit()

    return

def extractService(lyr):
#-------------------------------------------------------------------------------
# Name:        Function - extractService
# Purpose:  Runs through various layers in the project and extracts them into
#           a single schema for use.
#-------------------------------------------------------------------------------

    if '\\' in str(lyr):
        target_split = str(lyr).split('\\', 1)
        target = target_split[1]
    else:
        target = str(lyr)

    target = target.replace(' ', '')

    findExists_SCRATCH(target)

    try:
        arcpy.management.CopyFeatures(lyr, r'{}\{}'.format(path_DataProcessing, target), '', None, None, None)
        print ('            Status:  Successful Copy Complete')
        print ('            Scrubbing data')
        findExists_PREP(target)
        print ('            Status:  Successful Data Scrub')
        print ('            Preparing final destination')
        path_Workspace = path_DataFinal
        findExists_FINAL(target, path_Workspace)
        print ('            Status:  Final destination prepared')
        print ('            Preparing for projection to final destination')
        projectInto_FINAL(target)
        print ('                Publishing complete for {}'.format(target))

    except Exception as error_copy:
        print ('            Status:  Failure!')
        print (error_copy)

        mail_priority = '1'
        mail_subject = 'Portal Feature Copier Failure:  Service Extraction'
        mail_msg = ('A failure to extract a service from Portal has occured.  The error is as follows: \n\n' +
        'Error:  {}'.format(error_copy))

        sentMailNote(mail_priority, mail_subject, mail_msg)
        exit()


    return

def sentMailNote(mail_priority, mail_subject, mail_msg):
#-------------------------------------------------------------------------------
# Name:        Function - sentMailNote
# Purpose:  Universal use for both good and bad messages.
#-------------------------------------------------------------------------------

    mail_msg = mail_msg + ('\n\n[SYSTEM AUTO GENERATED MESSAGE]')
    mail_subject = email_subjectSchema + ' ' + mail_subject

    # Set SMTP Server and configuration of message.
    server = smtplib.SMTP(mail_server)
    send_mail = 'To: {0}\nFrom: {1}\nX-Priority: {2}\nSubject: {3}\n\n{4}'.format(email_target, mail_from, mail_priority, mail_subject, mail_msg)
    server.sendmail(mail_from, email_target, send_mail)
    server.quit()

    return

def sendFinish():
#-------------------------------------------------------------------------------
# Name:        Function - sendFinish
# Purpose:  Pops the I'm complete message via the sentMailNote function.
#-------------------------------------------------------------------------------

    mail_priority = '5'
    mail_subject = 'Portal Feature Staging Complete'
    mail_msg = 'Feature extraction from Portal has completed.'

    sentMailNote(mail_priority, mail_subject, mail_msg)

    return

#-------------------------------------------------------------------------------
#
#
#                                 MAIN SCRIPT
#
#
#-------------------------------------------------------------------------------

# Turn off history
arcpy.SetLogHistory(False)

# Set Overwrite Rules
arcpy.env.overwriteOutput = True

print ('***** Starting.....')

global worklist, dbName, dbUser, error_MSG
worklist = []
dbName = []
dbUser = []

if __name__ == '__main__':
    main(portalURL,portalUser,portalPW)