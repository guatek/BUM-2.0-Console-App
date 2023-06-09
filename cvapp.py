import KYFGLib
import cv2
import os
import numpy as np
import time
from KYFGLib import *
import queue
import signal
from loguru import logger
from datetime import datetime

from probe_control import ProbeController
from video_recorder import VideoRecorder

WINDOW_NAME = 'BUM2.0'
FPS_SMOOTHING = 0.9
WINDOW_NAME = 'BUM2.0'
cv2.namedWindow(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)


new_frame = False
frame_data = np.zeros((4600,5312),dtype=np.uint8)
full_frame_data = np.zeros((4600,5312,3),dtype=np.uint8)
tmp_img = None

# Global video and photo counter
video_counter = 0
photo_counter = 0

stop_app = False
def handler_stop_signals(signum, frame):
    global stop_app
    stop_app = True

signal.signal(signal.SIGINT, handler_stop_signals)
signal.signal(signal.SIGTERM, handler_stop_signals)



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
    #print("Buffer Info: Base " + str(pInfoBase) + ", Size " + str(pInfoSize) + ", Timestamp "+ str(pInfoTimestamp) + ", FPS " + str(pInfoFPS)
    #      + ", ID " + str(pInfoID), end='\r')

    #(KYFG_BufferGetInfo_status, frameIndex) = KYFG_StreamGetFrameIndex(buffHandle)
    #frameData = KYFG_StreamGetPtr(buffHandle, frameIndex)

    # convert to numpy array
    try:
        global frame_data, new_frame
        frame_data = make_nd_array(cast(pInfoBase,c_void_p), (4600, 5312), dtype=np.uint8)
        new_frame = True
    except Exception as e:
        logger.warning('Frame Handler Exception: ' + str(e))
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
    logger.remove()
    logger.add(sys.stderr, level='INFO')
    now = datetime.utcnow() # current date and time
    timestring = now.strftime("%Y%m%dT%H%M%S%f")
    logger.add(os.path.join('logs', timestring + '.log'), rotation="1 MB", retention="24 days")

    initParams = KYFGLib_InitParameters()
    KYFGLib_Initialize(initParams)

    (KY_GetSoftwareVersion_status, soft_ver) = KY_GetSoftwareVersion()
    logger.info("KYFGLib version: " + str(soft_ver.Major) + "." + str(soft_ver.Minor) + "." + str(soft_ver.SubMinor))
    if (soft_ver.Beta > 0):
        logger.info("(Beta " + str(soft_ver.Beta) + ")")
    if (soft_ver.RC > 0):
        logger.info("(RC " + str(soft_ver.RC) + ")")

    # Scan devices
    (status, fgAmount) = KYFGLib.KY_DeviceScan()
    if (status != FGSTATUS_OK):
        logger.info("KY_DeviceScan() status: " + str(format(status, '02x')))

    # Print available devices params
    for x in range(fgAmount):
        (status, dev_info) = KYFGLib.KY_DeviceInfo(x)
        if (status != FGSTATUS_OK):
            logger.info("Cant retrieve device #" + str(x) + " info")
            continue
        logger.info("Device " + str(x) + ": " + dev_info.szDeviceDisplayName)
    
    grabber_index = 0
    camera_index = 0

    # Get Grabber info
    grabberIndex = int(grabber_index)
    logger.info("Selected grabber: " + str(grabber_index))
    logger.info("\nGetting info about the grabber: ")
    (status, dev_info) = KY_DeviceInfo(grabberIndex)
    logger.info("DeviceDisplayName: " + dev_info.szDeviceDisplayName)
    logger.info("Bus: " + str(dev_info.nBus))
    logger.info("Slot: " + str(dev_info.nSlot))
    logger.info("Function: " + str(dev_info.nFunction))
    logger.info("DevicePID: " + str(dev_info.DevicePID))
    logger.info("isVirtual: " + str(dev_info.isVirtual))

    # connect to grabber
    connection = connectToGrabber(grabberIndex)

    # scan for connected cameras
    (CameraScan_status, camHandleArray[grabberIndex]) = KYFG_UpdateCameraList(handle[grabberIndex])
    logger.info("Found " + str(len(camHandleArray[grabberIndex])) + " cameras")
    if(len(camHandleArray[grabberIndex]) == 0):
        logger.info("Could not connect to a camera")

    # open a connection to chosen camera
    (KYFG_CameraOpen2_status,) = KYFG_CameraOpen2(camHandleArray[grabberIndex][0], None)
    # logger.info("KYFG_CameraOpen2_status: " + str(format(KYFG_CameraOpen2_status, '02x')))
    if (KYFG_CameraOpen2_status == FGSTATUS_OK):
        logger.info("Camera 0 was connected successfully")
    else:
        logger.info("Something went wrong while opening camera")

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
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    pc = ProbeController(port='/dev/ttyUSB0')

    fps = 0.0
    prev = time.time()
    min_time_between_events = 0.65 # Set to be just slightly longer the comms to the controller
    c = 'x'
    mode = 0
    white_flash_dur = 5
    uv_flash_dur = 500
    trigger_width = 4*uv_flash_dur
    recording = False
    threaded_rec = None
    pc.send_command_and_confirm("cameraon")
    pc.send_command("cfg,whiteflash," + str(white_flash_dur))
    pc.send_command("cfg,uvflash," + str(uv_flash_dur))
    pc.send_command("cfg,trigwidth," + str(trigger_width))
    pc.send_command("movelens,0.0")
    focus_pos = 0.0

    # filter events to eliminate false button presses
    button_event_filter = []

    last_command_time = time.time()

    while (not stop_app):

        now = time.time()
        fps = (fps*FPS_SMOOTHING + (1/(now - prev))*(1.0 - FPS_SMOOTHING))
        prev = now

        try:
            if new_frame:
                frame_data = cv2.cvtColor(frame_data,cv2.COLOR_BAYER_RG2RGB)
                full_frame_data = frame_data
                frame_data = frame_data[1220:(1220+2160),732:(732+3840),:]
                output_text = "Status: "
                if recording:
                    output_text = output_text + "REC"
                output_text = output_text + ", " + "Mode = "
                if mode == 0:
                    output_text = output_text + 'WHITE FLASH'
                else:
                    output_text = output_text + 'UV FLASH'
                output_text = output_text + ", " + "Focus = " + '{:.3f}'.format(focus_pos) + ", Flash Duration = "
                if mode == 0:
                    output_text = output_text + '{:.3f}'.format(white_flash_dur)
                else:
                    output_text = output_text + '{:.3f}'.format(uv_flash_dur)
                output_text = output_text + ", VID " + str(video_counter) + ", IMG " + str(photo_counter)
                cv2.putText(
                    img = frame_data,
                    text = output_text,
                    org = (50, 2130),
                    fontFace = cv2.FONT_HERSHEY_DUPLEX,
                    fontScale = 2,
                    color = (200, 246, 200),
                    thickness = 2
                )
                cv2.imshow(WINDOW_NAME, frame_data)
                new_frame = False
                if recording and threaded_rec is not None:
                    threaded_rec.add_frame(frame_data.copy())
            
            ui_event = cv2.waitKey(16)

            # Check for event and minimum event time
            if ui_event > 0:
                button_event_filter.append(ui_event)
                continue

                """
                # If this is the first event in a batch, wait for possiblee other events
                if len(button_event_filter) == 1:
                    last_command_time = time.time()
                    continue

                elapsed_time = time.time() - last_command_time
                # Don't process any commands if the time between them is too short
                if elapsed_time < min_time_between_events:
                    continue
                else:
                    last_command_time = time.time()
                """
            # Filter out multi button events. The assumption here is that any set of events is
            # a button read error and only events with a single 
            if time.time() - last_command_time >= 0.65:
                # Only pass events if there was one during the last time period
                last_command_time = time.time()
                if len(button_event_filter) == 1:
                    ui_event = button_event_filter[0]
                    button_event_filter = []
                else:
                    button_event_filter = []
                    continue
                


            # TAKE PHOTO
            if ui_event == 101:
                print("PHOTO")
                timestr = time.strftime("%Y%m%d-%H%M%S")
                cv2.imwrite(os.path.join('/NVMEDATA', timestr + '.tif'), full_frame_data)
                photo_counter += 1

            # MOVE LENS BACKWARD
            if ui_event == 119:
                print('RIGHT')
                if focus_pos + 0.04 < 3.0:
                    pc.send_command('steplens,0.04')
                    focus_pos += 0.04
            
            # MOVE LENS FORWARD
            if ui_event == 115:
                print('LEFT')
                if focus_pos - 0.04 > -2.0:
                    pc.send_command('steplens,-0.04')
                    focus_pos -= 0.04

            # TOGGLE FLASH MODE
            if ui_event == 105:
                print('MODE')
                if mode == 0:
                    pc.send_command('cfg,imagingmode,1')
                    mode = 1
                elif mode == 1:
                    pc.send_command('cfg,imagingmode,0')
                    mode = 0
            
            # INCREASE FLASH DURATION
            if ui_event == 100:
                if mode == 0:
                    white_flash_dur = white_flash_dur * 2
                    # Max white flash duration in us
                    if white_flash_dur > 1000:
                        white_flash_dur = 1000
                    pc.send_command("cfg,whiteflash," + str(white_flash_dur))
                elif mode == 1:
                    uv_flash_dur = uv_flash_dur * 2
                    # Max UV flash duration in us
                    if uv_flash_dur > 5000:
                        uv_flash_dur = 5000
                    pc.send_command("cfg,uvflash," + str(uv_flash_dur))
            
            # DECREASE FLASH DURATION
            if ui_event == 97:
                if mode == 0:
                    white_flash_dur = white_flash_dur / 2
                    pc.send_command("cfg,whiteflash," + str(white_flash_dur))
                elif mode == 1:
                    uv_flash_dur = uv_flash_dur / 2
                    pc.send_command("cfg,uvflash," + str(uv_flash_dur))

            # RECORD
            if ui_event == 114:
                if not recording:
                    print('RECORD')
                    threaded_rec = VideoRecorder()
                    threaded_rec.add_frame(frame_data.copy())
                    recording = True
                else:
                    print('STOP')
                    threaded_rec.end_recording()
                    threaded_rec = None
                    recording = False
                    video_counter += 1

            if ui_event == 27:
                break

        except Exception as e:
            print(e)
            break


    # Cleanup
    pc.send_command_and_confirm("cameraon")

    (CameraStop_status,) = KYFG_CameraStop(camHandleArray[grabberIndex][0])

    if (len(camHandleArray[grabberIndex]) > 0):
        (KYFG_CameraClose_status,) = KYFG_CameraClose(camHandleArray[grabberIndex][0])
        (CallbackRegister_status,) = KYFG_StreamBufferCallbackUnregister(cameraStreamHandle, Stream_callback_func)
    if (handle[grabberIndex] != 0):
        (KYFG_Close_status,) = KYFG_Close(handle[grabberIndex])




except KYException as KYe:
    logger.warning("KYException occurred: " + str(KYe))
    raise












