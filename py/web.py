import os
import struct
import array
import random
import asyncio
import threading

from fcntl import ioctl

from typing import AsyncGenerator
from contextlib import asynccontextmanager

import cv2
import uvicorn
import aiofiles
import aioserial

from ultralytics import YOLO
from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse

from crsf import channels_CRSF_to_packet


FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 1
COLOR = (255, 0, 0)
THICKNESS = 2

CHANNEL_MIN = 1
CHANNEL_CENTER = 992
CHANNEL_MAX = 1984

AXIS_MIN = -32768
AXIS_MAX = 32767



queue_screen = asyncio.Queue(1)
queue_uart = asyncio.Queue()
model = YOLO("yolo-Weights/yolov8n.pt")

class_names = [
    "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
    "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
    "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon",
    "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", 
    "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed",
    "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote",
    "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
    "hair drier", "toothbrush"
]

axis_names = {
    0x00 : "x",
    0x01 : "y",
    0x02 : "z",
    0x03 : "rx",
    0x04 : "ry",
    0x05 : "rz",
    0x06 : "throttle",
    0x07 : "rudder",
    0x08 : "wheel",
    0x09 : "gas",
    0x0a : "brake",
    0x10 : "hat0x",
    0x11 : "hat0y",
    0x12 : "hat1x",
    0x13 : "hat1y",
    0x14 : "hat2x",
    0x15 : "hat2y",
    0x16 : "hat3x",
    0x17 : "hat3y",
    0x18 : "pressure",
    0x19 : "distance",
    0x1a : "tilt_x",
    0x1b : "tilt_y",
    0x1c : "tool_width",
    0x20 : "volume",
    0x28 : "misc",
}


def map_range(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)
    

async def write_channels(ser: aioserial.AioSerial):
    # last_data = {"ch0": CHANNEL_CENTER, "ch1": CHANNEL_CENTER}
    # data = {"ch0": CHANNEL_CENTER, "ch1": CHANNEL_CENTER}
    ch0 = CHANNEL_CENTER
    ch1 = CHANNEL_CENTER
    while True:
        try:
            data = queue_uart.get_nowait()
            ch0 = data["ch0"]
            ch1 = data["ch1"]
        except asyncio.QueueEmpty:
            pass

        channels = [
            ch0, ch1, 992, 992, 992, 992, 992, 992, 
            992, 992, 992, 992, 992, 992, 992, 992
        ]

        await ser.write_async(channels_CRSF_to_packet(channels))


async def read_channels(ser: aioserial.AioSerial):
    while True:
        # data = await ser.read_async()
        print((await ser.read_async()), flush=True)
        await asyncio.sleep(0.05)


async def read_joystick():
    axis_states = {}
    axis_map = []

    async with aiofiles.open("/dev/input/js0", "rb") as jsdev:

        buf = array.array("B", [0] * 64)
        ioctl(jsdev, 0x80006a13 + (0x10000 * len(buf)), buf)
        # js_name = buf.tobytes().rstrip(b"\x00").decode("utf-8")

        # Get number of axes and buttons.
        buf = array.array("B", [0])
        ioctl(jsdev, 0x80016a11, buf) # JSIOCGAXES
        num_axes = buf[0]

        # Get the axis map.
        buf = array.array("B", [0] * 0x40)
        ioctl(jsdev, 0x80406a32, buf) # JSIOCGAXMAP

        for axis in buf[:num_axes]:
            axis_name = axis_names.get(axis, f"unknown(0x{axis:02x}")
            axis_map.append(axis_name)
            axis_states[axis_name] = 0.0

        ret = {"ch0": CHANNEL_CENTER, "ch1": CHANNEL_CENTER}
        while True:
            # print(ret) 
            evbuf = await jsdev.read(8)
            if evbuf:
                time, value, type, number = struct.unpack("IhBB", evbuf)

                if type & 0x02:
                    axis = axis_map[number]
                    if axis:
                        axis_states[axis] = value
                        
                        gas = map_range(
                            axis_states["gas"], 
                            AXIS_MIN, 
                            AXIS_MAX,
                            CHANNEL_CENTER,
                            CHANNEL_MAX
                        )
                        brake = map_range(
                            axis_states["brake"], 
                            AXIS_MIN, 
                            AXIS_MAX,
                            CHANNEL_CENTER + 1,
                            CHANNEL_MIN
                        )
                        steering = map_range(
                            axis_states["x"], 
                            AXIS_MIN, 
                            AXIS_MAX,
                            CHANNEL_MIN,
                            CHANNEL_MAX
                        )
                        gas_brake = brake if gas == CHANNEL_CENTER else gas
                        
                        ret = {
                            "ch0": gas_brake,
                            "ch1": steering,
                        }
                              
                try:
                    # print(ret)
                    # queue_screen.put_nowait(ret)
                    # print(queue_uart.qsize())
                    await queue_uart.put(ret)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    try:
        ser = aioserial.AioSerial(port="/dev/ttyUSB0", baudrate=115200)
        asyncio.gather(
            read_joystick(),
            # read_channels(ser),
            write_channels(ser)
        )

        yield
    except asyncio.exceptions.CancelledError as error:
        print(error.args)
    finally:
        camera.release()
        print("Camera resource released.")

app = FastAPI(lifespan=lifespan)


class Camera:
    """
    A class to handle video capture from a camera.
    """

    def __init__(self, url: str | int = 0) -> None:
        """
        Initialize the camera.

        :param camera_index: Index of the camera to use.
        """
        self.cap = cv2.VideoCapture(url)
        self.lock = threading.Lock()
        self.channels = {"ch0": CHANNEL_CENTER, "ch1": CHANNEL_CENTER}

    async def get_frame(self) -> bytes:
        """
        Capture a frame from the camera.

        :return: JPEG encoded image bytes.
        """
        with self.lock:

            ret, frame = self.cap.read()
            if not ret:
                return b""
            
            #  Detection and output.
            results = model(frame, stream=True, verbose=False)

            #  Coordinates.
            for r in results:
                boxes = r.boxes

                for box in boxes:
                    #  Bounding box.
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2) 

                    # put box in cam
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 3)

                    # class name
                    cls = int(box.cls[0])

                    # object details
                    cv2.putText(
                        frame, 
                        class_names[cls], 
                        [x1, y1], 
                        FONT, 
                        FONT_SCALE, 
                        COLOR, 
                        THICKNESS
                    )
            
            #  Show channals status.
            try:
                self.channels = queue_screen.get_nowait()
            except asyncio.QueueEmpty:
                    pass
            
            # cv2.putText(
            #     frame, 
            #     f"gas/brake: {self.channels["ch0"]}; steering: {self.channels["ch1"]}",
            #     [10, 40], 
            #     FONT, 
            #     FONT_SCALE, 
            #     COLOR, 
            #     THICKNESS
            # )

            ret, jpeg = cv2.imencode(".jpg", frame)
            if not ret:
                return b""

            return jpeg.tobytes()

    def release(self) -> None:
        """
        Release the camera resource.
        """
        with self.lock:
            if self.cap.isOpened():
                self.cap.release()


async def gen_frames() -> AsyncGenerator[bytes, None]:
    """
    An asynchronous generator function that yields camera frames.

    :yield: JPEG encoded image bytes.
    """
    try:
        while True:
            frame = await camera.get_frame()
            if frame:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )
            else:
                break
            await asyncio.sleep(0.01)
    except (asyncio.CancelledError, GeneratorExit):
        print("Frame generation cancelled.")
    finally:
        print("Frame generator exited.")


@app.get("/video")
async def video_feed() -> StreamingResponse:
    """
    Video streaming route.

    :return: StreamingResponse with multipart JPEG frames.
    """
    return StreamingResponse(
        gen_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/snapshot")
async def snapshot() -> Response:
    """
    Snapshot route to get a single frame.

    :return: Response with JPEG image.
    """
    frame = camera.get_frame()
    if frame:
        return Response(content=frame, media_type="image/jpeg")
    else:
        return Response(status_code=404, content="Camera frame not available.")


async def main():
    """
    Main entry point to run the Uvicorn server.
    """
    config = uvicorn.Config(app, host="0.0.0.0", port=8888)
    server = uvicorn.Server(config)

    # Run the server
    await server.serve()

if __name__ == "__main__":
    # Usage example: Streaming default camera for local webcam:
    camera = Camera(0)

    # Usage example: Streaming the camera for a specific camera index:
    # camera = Camera(0)

    # Usage example 3: Streaming an IP camera:
    # camera = Camera("rtsp://user:password@ip_address:port/")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user.")