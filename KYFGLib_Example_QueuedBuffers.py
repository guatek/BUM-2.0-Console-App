import KYFGLib
import cv2
import numpy as np
from KYFGLib import *
import queue

WINDOW_NAME = 'BUM2.0'
FPS_SMOOTHING = 0.9
WINDOW_NAME = 'BUM2.0'
cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


new_frame = False
frame_data = np.zeros((4600,5312),dtype=np.uint8)
tmp_img = None


############################# Callback Function ##################################

# Example of user class containing stream information
class StreamInfoStruct:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.callbackCount = 0
        return
    
def make_nd_array(c_pointer, shape, dtype=np.float64, order='C', own_data=True):
    arr_size = np.prod(shape[:]) * np.dtype(dtype).itemsize 
    buf_from_mem = pythonapi.PyMemoryView_FromMemory
    buf_from_mem.restype = py_object
    buf_from_mem.argtypes = (c_void_p, c_int, c_int)
    buffer = buf_from_mem(c_pointer, arr_size, 0x100)
    arr = np.ndarray(tuple(shape[:]), dtype, buffer, order=order)
    if own_data and not arr.flags.owndata:
        return arr.copy()
    else:
        return arr

# Example of user Stream_callback_func function implementation
# Parameters brief:
#       buffHandle - API handle to received data. Type: STREAM_HANDLE
#       userContext - Retrieved when the callback is issued. Helps to determine the origin of stream in host application.
def Stream_callback_func(buffHandle, userContext): 

    if (buffHandle == 0 ):
        Stream_callback_func.copyingDataFlag = 0
        return


    if (userContext != 0):
        streamInfo = cast(userContext, py_object).value
        #print('buffer ' + str(format(buffHandle, '02x')) + ': height=' + str(streamInfo.height) + ', width=' + str(
        #    streamInfo.width) + ', callback count=' + str(streamInfo.callbackCount))
        streamInfo.callbackCount = streamInfo.callbackCount + 1


    # Example of retrieving buffer information
    (KYFG_BufferGetInfo_status, pInfoBase, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_BASE) # PTR
    (KYFG_BufferGetInfo_status, pInfoSize, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_SIZE) # SIZET
    (KYFG_BufferGetInfo_status, pInfoPTR, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_USER_PTR) # PTR
    (KYFG_BufferGetInfo_status, pInfoTimestamp, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_TIMESTAMP) # UINT64
    (KYFG_BufferGetInfo_status, pInfoFPS, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_INSTANTFPS) # FLOAT64
    (KYFG_BufferGetInfo_status, pInfoID, pInfoSize, pInfoType) = KYFG_BufferGetInfo(
        buffHandle, KY_STREAM_BUFFER_INFO_CMD.KY_STREAM_BUFFER_INFO_ID) # UINT32
    print("Buffer Info: Base " + str(pInfoBase) + ", Size " + str(pInfoSize) + ", Timestamp "+ str(pInfoTimestamp) + ", FPS " + str(pInfoFPS)
          + ", ID " + str(pInfoID), end='\r')

    #(KYFG_BufferGetInfo_status, frameIndex) = KYFG_StreamGetFrameIndex(buffHandle)
    #frameData = KYFG_StreamGetPtr(buffHandle, frameIndex)

    # convert to numpy array
    try:
        global frame_data, new_frame
        frame_data = make_nd_array(cast(pInfoBase,c_void_p), (4600, 5312), dtype=np.uint8)
        new_frame = True
    except Exception as e:
        print('In Frame Handler: ' + str(e))
        pass
    #frame_data = frame_data.astype(np.uint8)

    sys.stdout.flush()
    (KYFG_BufferToQueue_status,) = KYFG_BufferToQueue(buffHandle ,KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    #print("KYFG_BufferToQueue_status: " + str(format(KYFG_BufferToQueue_status, '02x'))) 
    Stream_callback_func.copyingDataFlag = 0



    return

Stream_callback_func.data = 0
Stream_callback_func.copyingDataFlag = 0

################################ Defines ###################################################

MAX_BOARDS = 4

handle = [0 for i in range(MAX_BOARDS)]

detectedCameras = []

grabberIndex = 1

camHandleArray = [[0 for x in range(0)] for y in range(MAX_BOARDS)]

buffHandle = STREAM_HANDLE()

cameraStreamHandle = 0

frameDataSize = 0
frameDataAligment = 0

streamBufferHandle = [0 for i in range(16)]
streamAllignedBuffer = [0 for i in range(16)]

streamInfoStruct = StreamInfoStruct()

DEVICE_QUEUED_BUFFERS_SUPPORTED = "FW_Dma_Capable_QueuedBuffers_Imp"
################################## Control Functions ####################################
def printErr(err, msg = ""):
    print(msg)
    print("Error description: {0}".format(err))


def connectToGrabber(grabberIndex):
    global handle
    (connected_fghandle,) = KYFG_Open(grabberIndex)
    connected = connected_fghandle.get()
    handle[grabberIndex] = connected

    (status, tested_dev_info) = KYFGLib.KY_DeviceInfo(grabberIndex)
    print ("Good connection to grabber " + str(grabberIndex) + ": " + tested_dev_info.szDeviceDisplayName + ", handle= " + str(format(connected, '02x')))
    
    (KYFG_GetGrabberValueInt_status, dmadQueuedBufferCapable) = KYFG_GetGrabberValueInt(handle[grabberIndex],DEVICE_QUEUED_BUFFERS_SUPPORTED)
    
    #print("StreamCreateAndAlloc_status: " + str(format(KYFG_GetGrabberValueInt_status, '02x')))
    #print("dmadQueuedBufferCapable: " + str(format(dmadQueuedBufferCapable, '02x')))
    
    if ( dmadQueuedBufferCapable != 1 ):
        print("grabber #" + str(grabberIndex) + " is not queued buffers capable\n")
    
    return 0


def startCamera (grabberIndex, cameraIndex):
    # put all buffers to input queue
    (KYFG_BufferQueueAll_status,) = KYFG_BufferQueueAll(cameraStreamHandle, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_UNQUEUED, KY_ACQ_QUEUE_TYPE.KY_ACQ_QUEUE_INPUT)
    print("KYFG_BufferQueueAll_status: " + str(format(KYFG_BufferQueueAll_status, '02x')))
    (KYFG_CameraStart_status,) = KYFG_CameraStart(camHandleArray[grabberIndex][cameraIndex], cameraStreamHandle, 0)
    print("KYFG_CameraStart_status: " + str(format(KYFG_CameraStart_status, '02x')))
    return 0

########################### Script ################################################


try:
    print("Welcome To KYFGLib Queued Buffers API Python Sample Script\n")

    initParams = KYFGLib_InitParameters()
    KYFGLib_Initialize(initParams)

    (KY_GetSoftwareVersion_status, soft_ver) = KY_GetSoftwareVersion()
    print("KYFGLib version: " + str(soft_ver.Major) + "." + str(soft_ver.Minor) + "." + str(soft_ver.SubMinor))
    if (soft_ver.Beta > 0):
        print("(Beta " + str(soft_ver.Beta) + ")")
    if (soft_ver.RC > 0):
        print("(RC " + str(soft_ver.RC) + ")")

    # Scan devices
    (status, fgAmount) = KYFGLib.KY_DeviceScan()
    if (status != FGSTATUS_OK):
        print("KY_DeviceScan() status: " + str(format(status, '02x')))

    # Print available devices params
    for x in range(fgAmount):
        (status, dev_info) = KYFGLib.KY_DeviceInfo(x)
        if (status != FGSTATUS_OK):
            print("Cant retrieve device #" + str(x) + " info")
            continue
        print("Device " + str(x) + ": " + dev_info.szDeviceDisplayName)
    
    grabber_index = 0
    camera_index = 0

    # Get Grabber info
    grabberIndex = int(grabber_index)
    print("Selected grabber: " + str(grabber_index))
    print("\nGetting info about the grabber: ")
    (status, dev_info) = KY_DeviceInfo(grabberIndex)
    print("DeviceDisplayName: " + dev_info.szDeviceDisplayName)
    print("Bus: " + str(dev_info.nBus))
    print("Slot: " + str(dev_info.nSlot))
    print("Function: " + str(dev_info.nFunction))
    print("DevicePID: " + str(dev_info.DevicePID))
    print("isVirtual: " + str(dev_info.isVirtual))

    # connect to grabber
    connection = connectToGrabber(grabberIndex)

    # scan for connected cameras
    (CameraScan_status, camHandleArray[grabberIndex]) = KYFG_UpdateCameraList(handle[grabberIndex])
    print("Found " + str(len(camHandleArray[grabberIndex])) + " cameras")
    if(len(camHandleArray[grabberIndex]) == 0):
        print("Could not connect to a camera")

    # open a connection to chosen camera
    (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camHandleArray[grabberIndex][0], None)
    # print("KYFG_CameraOpen2_status: " + str(format(KYFG_CameraOpen2_status, '02x')))
    if (KYFG_CameraOpen2_status == FGSTATUS_OK):
        print("Camera 0 was connected successfully")
    else:
        print("Something went wrong while opening camera")

    (SetCameraValueFloat_status_height,) = KYFG_SetCameraValueFloat(camHandleArray[grabberIndex][0], "AcquisitionFrameRate", 30.0)

    # Example of setting camera values
    (SetCameraValueInt_status_width,) = KYFG_SetCameraValueInt(camHandleArray[grabberIndex][0], "Width", 5312)
    # print("SetCameraValueInt_status_width: " + str(format(SetCameraValueInt_status_width, '02x')))
    (SetCameraValueInt_status_height,) = KYFG_SetCameraValueInt(camHandleArray[grabberIndex][0], "Height", 4600)
    # print("SetCameraValueInt_status_height: " + str(format(SetCameraValueInt_status_height, '02x')))
    #(SetCameraValueEnum_ByValueName_status,) = KYFG_SetCameraValueEnum_ByValueName(camHandleArray[grabberIndex][0], "PixelFormat", "Mono8")
    # print("SetCameraValueEnum_ByValueName_status: " + str(format(SetCameraValueEnum_ByValueName_status, '02x')))

    # Example of getting camera values
    (KYFG_GetValue_status, width) = KYFG_GetCameraValueInt(camHandleArray[grabberIndex][0], "Width")
    (KYFG_GetValue_status, height) = KYFG_GetCameraValueInt(camHandleArray[grabberIndex][0], "Height")

    streamInfoStruct.width = width
    streamInfoStruct.height = height

    # create stream and assign appropriate runtime acquisition callback function
    (KYFG_StreamCreate_status, cameraStreamHandle) = KYFG_StreamCreate(camHandleArray[grabberIndex][0], 0)
    # print("KYFG_StreamCreate_status: " + str(format(KYFG_StreamCreate_status, '02x')))

    # Register user 'Stream_callback_func' function and 'streamInfoStruct' as 'userContext'
    # 'streamInfoStruct' will be retrieved when the callback is issued
    (KYFG_StreamBufferCallbackRegister_status,) = KYFG_StreamBufferCallbackRegister(cameraStreamHandle,
        Stream_callback_func, py_object(streamInfoStruct))
    # print("KYFG_StreamBufferCallbackRegister_status: " + str(format(KYFG_StreamBufferCallbackRegister_status, '02x')))

    # Retrieve information about required frame buffer size and alignment
    (KYFG_StreamGetInfo_status, payload_size, frameDataSize, pInfoType) = \
        KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_PAYLOAD_SIZE)

    (KYFG_StreamGetInfo_status, buf_allignment, frameDataAligment, pInfoType) = \
        KYFG_StreamGetInfo(cameraStreamHandle, KY_STREAM_INFO_CMD.KY_STREAM_INFO_BUF_ALIGNMENT)

    # allocate memory for desired number of frame buffers
    for iFrame in range(len(streamBufferHandle)):
        streamAllignedBuffer[iFrame] = aligned_array(buf_allignment, c_ubyte, payload_size)
        # print("Address of alligned array: " + hex(addressof(streamAllignedBuffer[iFrame])))
        (status, streamBufferHandle[iFrame]) = KYFG_BufferAnnounce(cameraStreamHandle,
                                                                    streamAllignedBuffer[iFrame], None)

    # start camera
    startCamera(grabberIndex, 0)

    cv2.imshow(WINDOW_NAME, frame_data)

    fps = 0.0
    prev = time.time()
    c = 'x'
    while (c != 'e'):

        #c = input("")

        now = time.time()
        fps = (fps*FPS_SMOOTHING + (1/(now - prev))*(1.0 - FPS_SMOOTHING))
        prev = now

        #print("fps: {:.1f}".format(fps))

        try:
            if new_frame:
                frame_data = cv2.cvtColor(frame_data,cv2.COLOR_BAYER_RG2RGB)
                frame_data = frame_data[1220:(1220+2160),732:(732+3840)]
                cv2.imshow(WINDOW_NAME, frame_data)
                cv2.waitKey(2)
                new_frame = False
            if (cv2.waitKey(2) == 27):
                break

        except Exception as e:
            print(e)
            break


    (CameraStop_status,) = KYFG_CameraStop(camHandleArray[grabberIndex][0])

    if (len(camHandleArray[grabberIndex]) > 0):
        (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandleArray[grabberIndex][0])
        (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle, Stream_callback_func)
    if (handle[grabberIndex] != 0):
        (KYFG_Close_status,) = KYFG_Close(handle[grabberIndex])




except KYException as KYe:
    print("KYException occurred: ")
    raise












