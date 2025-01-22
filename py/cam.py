import threading

import cv2
from inputs import get_gamepad


vid = cv2.VideoCapture(0)  # Change me!!! 


def print_joystick():
    while True:
        print("nya")
    # events = get_gamepad()
    # for event in events:
    #     print(event.ev_type, event.code, event.state)


def show_frame():
    while True:
        _, frame = vid.read() 
        cv2.imshow('frame', frame)

    # if cv2.waitKey(1) & 0xFF == ord('q'): 
    #     break

t1 = threading.Thread(target=print_joystick)
t2 = threading.Thread(target=show_frame)

t1.start()
t2.start()

t1.join()
t2.join()

vid.release() 
cv2.destroyAllWindows() 