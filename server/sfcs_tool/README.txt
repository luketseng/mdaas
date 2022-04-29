Usage:

python3 GetUPNInformation.py -s WQ3302900ZN1A -t TA -n CARTONREMARK -v NA

python3 GetUSNGenealogyBasic.py -s WQ3302900ZN1A -t TA


Example 1:

/opt/wiwynn/mdaas/server/sfcs_tool# python3.6 FetchMetholdList.py |grep -v Upload

SFCS IP [WMX]: 10.49.200.155:912
--------
AllocateAndroidKey
AllocateAwaitingUnitSnList
AllocateAwaitingUnitSnListForExtendCode_x002F_Zack
AllocateSonyKey
AllocateSonyKeys
AssignUserGroupCode
BarcodeValidationWithGivenCategory
BindingUSNRIPalletID
BreakUpUSNRIPalletByUSN
CheckAutoPickUpRoute
CheckEngravingBoradBarcLotNo
CheckErrorCode
CheckInByUser
CheckInOutIPCBurnInRoom
CheckOPID
CheckOutByUser
CheckRoute
CheckSFCDLSkill
CheckSampling
CheckTestFixture
Complete
CompleteWithDefectRemark
CompleteWithDefectRemark_x002F_Bios_x002F_Diag
CompleteWithDefectRemark_x002F_Json
CompleteWithErrorDescription
CompleteWithSingleTrnData
DeductCPN
DynamicDBFunction
Get2SLabelInfo
GetAISImageFileName
GetAISImageFileNameSplit
GetAndProcessKtlOutEvent
GetAutoStickLabelPN
GetAvailableGradeList
GetBomPnDescription
GetCIPlusKey
GetCfiData
GetCfiNewSiList
GetCfiSiInfo
GetCurrentDBSysdate
GetDcsChassisInfo
GetDefectUsnList
GetDynamicData
GetEDIDFilename
GetEarliestSIList
GetEllaRackLoction
GetEngravingInfo
GetHDCPFileName
GetHDCPKey
GetICPN
GetIDValueByMO
GetJDMD3FileJobInfo
GetKeyInfoFromView
GetLastFixtureId
GetLastGrade
GetLastTransactionData
GetLinkUSN
GetLocInfo
GetMFGTypeByStage
GetMO53PNItem
GetMOInfo
GetMOItem
GetMOItemByMo
GetMacSecurityKey
GetMessage
GetMoAndBoardInfo
GetMoGenealogy
GetMoInfoByMo
GetNextStage
GetPanelParameter
GetPanelParameterWithDataSearchType
GetPreparedMOList
GetRIRackPositionByUSN
GetSPCConfig
GetSWCPNForUPN
GetScrapQualify
GetSetCA210OffsetTable
GetSkuBomData
GetTEModelName
GetTVKey
GetTeNotReadyMoList
GetTestSuiteInfo
GetTestSuiteInfoWithDataSearchType
GetTransactionTime
GetTvDacDataList
GetUPNInformation
GetUSNByCSN
GetUSNByRIPalletID
GetUSNByRIRackPosition
GetUSNByUSNInfo
GetUSNGenealogyBasic
GetUSNInfo
GetUSNInfoByMAC
GetUSNInformation
GetUSNItem
GetUSNlistByRange
GetUUTData
GetUpnInfoFromView
GetUsnById
GetUsnDefect
GetUsnGenealogy
GetUsnID
GetUsnIdWithoutCombine
GetUsnInfoAtStage
GetUsnInformationList
GetUsnRepair
GetWebServiceConfig
GetWebServiceInfo
IACSReturnPrepareMaterialStatusToSFCS
IPCUSNPositionLinkage
InsertHoldByUSN
IsCPNComplete
LinkMultiBoardUSN
LinkUSNRIPalletID
LinkUsnWorkingPalletId
LinkWorkingPalletCSN
RaiseMTDLRequest
RecordESOPInfo
RecordLogMessage
RequestLabelPrint
RequstJDMD3FileJob
RosaHddMoLinkCRUD
RosaSwPoNackRuleCheck
SetMoOnLine
SetReflowStage
SwapPalletIDUSN
SwapUSN
SwapWorkingPallet
TransferIPCBurnInLocation
UnlinkWorkingPallet

Example 2:

/opt/wiwynn/mdaas/server/sfcs_tool# python3.6 GetUSNGenealogyBasic.py -s R436903030012012 -t ZZ
Method: GetUSNGenealogyBasic
[*] Query successes. return code: [200]
                Unit S/N:R436903030012012
               MO Number:000090002717
                Unit P/N:M1144369-001$GJ20
              Stage Tour:AI,AO,H1,IN,WT,PT,TN,TO,TP,QN,SU,WB,BI,BO,LK,CS,FN,IO,PO,IP,SN,DS
      Next Process Stage:QN
Previous Processed Stage:DS

