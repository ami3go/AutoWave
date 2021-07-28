/****************************************************************************
 *                       AutoWave                           
 *                                                                          
 * Title:    AutoWave.h                                        
 * Purpose:  AutoWave Driver                                       
 *           instrument driver declarations.                                
 *                                                                          
 ****************************************************************************/

#ifndef __AUTOWAVE_HEADER
#define __AUTOWAVE_HEADER

#include <cvidef.h>
#include <ivi.h>

#if defined(__cplusplus) || defined(__cplusplus__)
extern "C" {
#endif

/****************************************************************************
 *----------------- Instrument Driver Revision Information -----------------*
 ****************************************************************************/
#define AUTOWAVE_MAJOR_VERSION                1     /* Instrument driver major version   */
#define AUTOWAVE_MINOR_VERSION                0     /* Instrument driver minor version   */
                                                                
#define AUTOWAVE_CLASS_SPEC_MAJOR_VERSION     2     /* Class specification major version */
#define AUTOWAVE_CLASS_SPEC_MINOR_VERSION     0     /* Class specification minor version */


        /*=CHANGE:===============================================================
           Add supported instrument models.
           Add your company name.                                                 
           Add useful instrument driver description.                                                 
         *============================================================END=CHANGE=*/
#define AUTOWAVE_SUPPORTED_INSTRUMENT_MODELS  "AutoWave"
#define AUTOWAVE_DRIVER_VENDOR                "EM Test"
#define AUTOWAVE_DRIVER_DESCRIPTION           "Description"
                    

/**************************************************************************** 
 *---------------------------- Attribute Defines ---------------------------* 
 ****************************************************************************/

    /*- IVI Inherent Instrument Attributes ---------------------------------*/    

        /* User Options */
//#define AUTOWAVE_ATTR_RANGE_CHECK                   IVI_ATTR_RANGE_CHECK                    /* ViBoolean */
//#define AUTOWAVE_ATTR_QUERY_INSTRUMENT_STATUS       IVI_ATTR_QUERY_INSTRUMENT_STATUS        /* ViBoolean */
//#define AUTOWAVE_ATTR_CACHE                         IVI_ATTR_CACHE                          /* ViBoolean */
//#define AUTOWAVE_ATTR_SIMULATE                      IVI_ATTR_SIMULATE                       /* ViBoolean */
//#define AUTOWAVE_ATTR_RECORD_COERCIONS              IVI_ATTR_RECORD_COERCIONS               /* ViBoolean */
//#define AUTOWAVE_ATTR_INTERCHANGE_CHECK             IVI_ATTR_INTERCHANGE_CHECK              /* ViBoolean */
        
        /* Driver Information  */
#define AUTOWAVE_ATTR_SPECIFIC_DRIVER_PREFIX        IVI_ATTR_SPECIFIC_DRIVER_PREFIX         /* ViString, read-only  */
#define AUTOWAVE_ATTR_SUPPORTED_INSTRUMENT_MODELS   IVI_ATTR_SUPPORTED_INSTRUMENT_MODELS    /* ViString, read-only  */
#define AUTOWAVE_ATTR_GROUP_CAPABILITIES            IVI_ATTR_GROUP_CAPABILITIES             /* ViString, read-only  */
#define AUTOWAVE_ATTR_INSTRUMENT_MANUFACTURER       IVI_ATTR_INSTRUMENT_MANUFACTURER        /* ViString, read-only  */
#define AUTOWAVE_ATTR_INSTRUMENT_MODEL              IVI_ATTR_INSTRUMENT_MODEL               /* ViString, read-only  */
#define AUTOWAVE_ATTR_INSTRUMENT_FIRMWARE_REVISION  IVI_ATTR_INSTRUMENT_FIRMWARE_REVISION	/* ViString, read-only  */
#define AUTOWAVE_ATTR_SPECIFIC_DRIVER_REVISION      IVI_ATTR_SPECIFIC_DRIVER_REVISION       /* ViString, read-only  */
#define AUTOWAVE_ATTR_SPECIFIC_DRIVER_VENDOR        IVI_ATTR_SPECIFIC_DRIVER_VENDOR         /* ViString, read-only  */
#define AUTOWAVE_ATTR_SPECIFIC_DRIVER_DESCRIPTION   IVI_ATTR_SPECIFIC_DRIVER_DESCRIPTION    /* ViString, read-only  */
#define AUTOWAVE_ATTR_SPECIFIC_DRIVER_CLASS_SPEC_MAJOR_VERSION IVI_ATTR_SPECIFIC_DRIVER_CLASS_SPEC_MAJOR_VERSION /* ViInt32, read-only */
#define AUTOWAVE_ATTR_SPECIFIC_DRIVER_CLASS_SPEC_MINOR_VERSION IVI_ATTR_SPECIFIC_DRIVER_CLASS_SPEC_MINOR_VERSION /* ViInt32, read-only */

        /* Advanced Session Information */
//#define AUTOWAVE_ATTR_LOGICAL_NAME                  IVI_ATTR_LOGICAL_NAME                   /* ViString, read-only  */
//#define AUTOWAVE_ATTR_IO_RESOURCE_DESCRIPTOR        IVI_ATTR_IO_RESOURCE_DESCRIPTOR         /* ViString, read-only  */
//#define AUTOWAVE_ATTR_DRIVER_SETUP                  IVI_ATTR_DRIVER_SETUP                   /* ViString, read-only  */        
    
	/*- Instrument-Specific Attributes -------------------------------------*/
#define AUTOWAVE_ATTR_ID_QUERY_RESPONSE      (IVI_SPECIFIC_PUBLIC_ATTR_BASE + 1L)     /* ViString (Read Only) */

/**************************************************************************** 
 *---------------- Instrument Driver Function Declarations -----------------* 
 ****************************************************************************/

    /*- Init and Close Functions -------------------------------------------*/
ViStatus _VI_FUNC AutoWave_init (ViRsrc resourceName, ViBoolean IDQuery, ViBoolean resetDevice, ViSession *vi);
ViStatus _VI_FUNC AutoWave_InitWithOptions (ViRsrc resourceName, ViBoolean IDQuery, ViBoolean resetDevice, ViConstString optionString, ViSession *newVi);
ViStatus _VI_FUNC AutoWave_close (ViSession vi);   

    /*- Coercion Info Functions --------------------------------------------*/
ViStatus _VI_FUNC AutoWave_GetNextCoercionRecord (ViSession vi, ViInt32 bufferSize, ViChar record[]);
    
    /*- Locking Functions --------------------------------------------------*/
ViStatus _VI_FUNC AutoWave_LockSession (ViSession vi, ViBoolean *callerHasLock);   
ViStatus _VI_FUNC AutoWave_UnlockSession (ViSession vi, ViBoolean *callerHasLock);

    /*- Error Functions ----------------------------------------------------*/
ViStatus _VI_FUNC AutoWave_error_query (ViSession vi, ViInt32 *errorCode, ViChar errorMessage[]);
ViStatus _VI_FUNC AutoWave_GetError (ViSession vi, ViStatus *code, ViInt32 bufferSize, ViChar description[]);
ViStatus _VI_FUNC AutoWave_ClearError (ViSession vi);
ViStatus _VI_FUNC AutoWave_error_message (ViSession vi, ViStatus errorCode, ViChar errorMessage[256]);
    
    /*- Interchangeability Checking Functions ------------------------------*/
ViStatus _VI_FUNC AutoWave_GetNextInterchangeWarning (ViSession vi, ViInt32 bufferSize, ViChar warnString[]);
ViStatus _VI_FUNC AutoWave_ResetInterchangeCheck (ViSession vi);
ViStatus _VI_FUNC AutoWave_ClearInterchangeWarnings (ViSession vi);

    /*- Utility Functions --------------------------------------------------*/
ViStatus _VI_FUNC AutoWave_InvalidateAllAttributes (ViSession vi);

ViStatus _VI_FUNC AutoWave_GoToLocal (ViSession vi);
ViStatus _VI_FUNC AutoWave_Reboot (ViSession  vi);

ViStatus _VI_FUNC AutoWave_SetRangeOutput (ViSession vi, ViInt16 channel, ViBoolean polarity, ViInt16 inputDC, ViInt16 outputDC);
ViStatus _VI_FUNC AutoWave_SetRangeInput (ViSession vi, ViInt16 channel, ViInt16 voltage);

ViStatus _VI_FUNC AutoWave_SetMode (ViSession vi, ViChar mode[]);
ViStatus _VI_FUNC AutoWave_SetSource (ViSession vi, ViChar type[], ViChar file[]);
ViStatus _VI_FUNC AutoWave_SetEvents (ViSession vi, ViInt32 events);

ViStatus _VI_FUNC AutoWave_GetChannelMode (ViSession vi, ViInt16 channel, ViBoolean *outputState);
ViStatus _VI_FUNC AutoWave_SetChannelMode (ViSession vi, ViInt16 channel, ViBoolean outputState);

ViStatus _VI_FUNC AutoWave_SetVoltage (ViSession vi, ViInt16 channel, ViReal64 voltage);

ViStatus _VI_FUNC AutoWave_Start (ViSession vi);
ViStatus _VI_FUNC AutoWave_Stop (ViSession vi);
ViStatus _VI_FUNC AutoWave_Break (ViSession vi);

ViStatus _VI_FUNC AutoWave_GetDUTMonitor (ViSession vi, ViInt16 channel, ViChar action[]);
ViStatus _VI_FUNC AutoWave_SetDUTMonitor (ViSession vi, ViInt16 channel, ViInt16 action);

ViStatus _VI_FUNC AutoWave_GetPath (ViSession vi, ViChar directory[], ViChar path[]);
ViStatus _VI_FUNC AutoWave_GetPathContent (ViSession vi, ViChar directory[], ViChar content[]);
ViStatus _VI_FUNC AutoWave_GetFileHeader (ViSession vi, ViChar directory[], ViChar file[], ViChar header[]);
ViStatus _VI_FUNC AutoWave_GetFileSize (ViSession vi, ViChar directory[], ViChar file[], ViInt32 *size);
ViStatus _VI_FUNC AutoWave_TransmitFile (ViSession vi, ViChar sourcePath[], ViChar destinationDirectory[], ViChar destinationFile[]);
ViStatus _VI_FUNC AutoWave_RetrieveFile (ViSession vi, ViChar sourceDirectory[], ViChar sourceFile[], ViChar destinationPath[]);
ViStatus _VI_FUNC AutoWave_CheckFile (ViSession vi,  ViChar directory[], ViChar file[], ViBoolean *result);
ViStatus _VI_FUNC AutoWave_DeleteFile (ViSession vi, ViChar directory[], ViChar file[]);
ViStatus _VI_FUNC AutoWave_GetDUTFile (ViSession vi, ViChar destination[]);
ViStatus _VI_FUNC AutoWave_GetErrorFile (ViSession vi, ViChar destination[]);

ViStatus _VI_FUNC AutoWave_SetDisplay (ViSession vi, ViChar toDisplay[]);
ViStatus _VI_FUNC AutoWave_GetDate (ViSession vi, ViChar timestamp[]);
ViStatus _VI_FUNC AutoWave_SetDate (ViSession vi, ViChar timestamp[]);

ViStatus _VI_FUNC AutoWave_GetStateTest (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetStateInput (ViSession vi, ViInt16 channel, ViInt16 *status, ViInt16 *DUTStatus, ViReal64 *remainTime);
ViStatus _VI_FUNC AutoWave_GetStateOutput (ViSession vi, ViInt16 channel, ViInt16 *status, ViInt16 *DUTStatus, ViInt16 *iterationTotal, ViInt16 *iterationCurrent, ViInt16 *event, ViInt16 *segment, ViReal64 *remainTime, ViReal64 *testTime);
ViStatus _VI_FUNC AutoWave_GetStateSystem (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetStateBattery (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetStateSynthetiser (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetMacAddress (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetStateDUTmonitor (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetStateError (ViSession vi, ViChar state[]);
ViStatus _VI_FUNC AutoWave_GetStateDelay (ViSession vi, ViChar state[]);

ViStatus _VI_FUNC AutoWave_Query (ViSession vi, ViChar command[], ViChar receive[]);
ViStatus _VI_FUNC AutoWave_GetMonitorData (ViSession vi, ViChar monitorData[]);
ViStatus _VI_FUNC AutoWave_GetChannelCount (ViSession vi, ViChar channelType[],  ViInt16 *count);
ViStatus _VI_FUNC AutoWave_CheckChannel (ViSession vi, ViChar channelType[], ViInt16 channel);

    /*- Calibration Functions ----------------------------------------------*/
ViStatus _VI_FUNC AutoWave_CalStart (ViSession vi);
ViStatus _VI_FUNC AutoWave_CalEnd (ViSession vi);
ViStatus _VI_FUNC AutoWave_CalStop (ViSession vi);
ViStatus _VI_FUNC AutoWave_CalGetValue (ViSession vi, ViChar type[], ViInt16 channel, ViInt16 range, ViReal64 *mean, ViReal64 *min, ViReal64 *max, ViReal64 *stdDev, ViReal64 *samples);
ViStatus _VI_FUNC AutoWave_CalSetValue (ViSession vi, ViChar type[], ViInt16 channel, ViReal64 value);
ViStatus _VI_FUNC AutoWave_CalGetOutCorrect (ViSession vi, ViInt16 channel, ViReal64 *gain, ViReal64 *offset);
ViStatus _VI_FUNC AutoWave_CalSetOutCorrect (ViSession vi, ViInt16 channel, ViReal64 gain, ViReal64 offset);
ViStatus _VI_FUNC AutoWave_CalGetInCorrect (ViSession vi, ViInt16 channel, ViInt16 range, ViReal64 *gain, ViReal64 *offset);
ViStatus _VI_FUNC AutoWave_CalSetInCorrect (ViSession vi, ViInt16 channel, ViInt16 range, ViReal64 gain, ViReal64 offset);
ViStatus _VI_FUNC AutoWave_CalGetParameter (ViSession vi, ViChar type[], ViChar value[]);

    /*- Private Functions --------------------------------------------------*/
int AutoWave_FileSize (ViChar name[]);
void AutoWave_FileCopy (ViChar source[], ViChar destination[]);

ViStatus _VI_FUNC AutoWave_reset (ViSession vi);
ViStatus _VI_FUNC AutoWave_ResetWithDefaults (ViSession vi);
ViStatus _VI_FUNC AutoWave_self_test (ViSession vi, ViInt16 *selfTestResult, ViChar selfTestMessage[]);
ViStatus _VI_FUNC AutoWave_revision_query (ViSession vi, ViChar instrumentDriverRevision[], ViChar firmwareRevision[]);
ViStatus _VI_FUNC AutoWave_Disable (ViSession vi);

    /*- Set, Get, and Check Attribute Functions ----------------------------*/
ViStatus _VI_FUNC  AutoWave_GetAttributeViInt32 (ViSession vi, ViConstString channelName, ViAttr attribute, ViInt32 *value);
ViStatus _VI_FUNC  AutoWave_GetAttributeViReal64 (ViSession vi, ViConstString channelName, ViAttr attribute, ViReal64 *value);
ViStatus _VI_FUNC  AutoWave_GetAttributeViString (ViSession vi, ViConstString channelName, ViAttr attribute, ViInt32 bufSize, ViChar value[]); 
ViStatus _VI_FUNC  AutoWave_GetAttributeViSession (ViSession vi, ViConstString channelName, ViAttr attribute, ViSession *value);
ViStatus _VI_FUNC  AutoWave_GetAttributeViBoolean (ViSession vi, ViConstString channelName, ViAttr attribute, ViBoolean *value);

ViStatus _VI_FUNC  AutoWave_SetAttributeViInt32 (ViSession vi, ViConstString channelName, ViAttr attribute, ViInt32 value);
ViStatus _VI_FUNC  AutoWave_SetAttributeViReal64 (ViSession vi, ViConstString channelName, ViAttr attribute, ViReal64 value);
ViStatus _VI_FUNC  AutoWave_SetAttributeViString (ViSession vi, ViConstString channelName, ViAttr attribute, ViConstString value); 
ViStatus _VI_FUNC  AutoWave_SetAttributeViSession (ViSession vi, ViConstString channelName, ViAttr attribute, ViSession value);
ViStatus _VI_FUNC  AutoWave_SetAttributeViBoolean (ViSession vi, ViConstString channelName, ViAttr attribute, ViBoolean value);

ViStatus _VI_FUNC  AutoWave_CheckAttributeViInt32 (ViSession vi, ViConstString channelName, ViAttr attribute, ViInt32 value);
ViStatus _VI_FUNC  AutoWave_CheckAttributeViReal64 (ViSession vi, ViConstString channelName, ViAttr attribute, ViReal64 value);
ViStatus _VI_FUNC  AutoWave_CheckAttributeViString (ViSession vi, ViConstString channelName, ViAttr attribute, ViConstString value); 
ViStatus _VI_FUNC  AutoWave_CheckAttributeViSession (ViSession vi, ViConstString channelName, ViAttr attribute, ViSession value);
ViStatus _VI_FUNC  AutoWave_CheckAttributeViBoolean (ViSession vi, ViConstString channelName, ViAttr attribute, ViBoolean value);

/**************************************************************************** 
 *---------------------------- End Include File ----------------------------* 
 ****************************************************************************/

#define AUTOWAVE_VAL_GEN                                            1
#define AUTOWAVE_VAL_REC                                            2

#define AUTOWAVE_VAL_ON                                             1
#define AUTOWAVE_VAL_OFF                                            2
#define AUTOWAVE_VAL_ASK                                            3

#if defined(__cplusplus) || defined(__cplusplus__)
}
#endif
#endif /* __AUTOWAVE_HEADER */

