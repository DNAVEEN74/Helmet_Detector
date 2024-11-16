import cv2
import math
import cvzone
from ultralytics import YOLO
import serial
import serial.tools.list_ports
import time

def connect_to_arduino():
    ports = serial.tools.list_ports.comports()
    print("\nAvailable ports:")
    for port in ports:
        print(f"- {port.device}: {port.description}")
    
    arduino_ports = [
        p.device for p in ports
        if 'arduino' in p.description.lower() 
        or 'ch340' in p.description.lower()
        or 'usb' in p.description.lower()
    ]
    
    if arduino_ports:
        print(f"\nFound possible Arduino ports: {arduino_ports}")
    else:
        print("\nNo Arduino ports found automatically")
        port = input("Please enter Arduino port manually (e.g., COM3): ")
        arduino_ports = [port]
    
    for port in arduino_ports:
        try:
            arduino = serial.Serial(port=port, baudrate=9600, timeout=1)
            print(f"\nSuccessfully connected to Arduino on {port}")
            time.sleep(2)
            return arduino
        except serial.SerialException as e:
            print(f"\nFailed to connect to {port}: {str(e)}")
            print("Common issues:")
            print("1. Arduino IDE Serial Monitor is open")
            print("2. Wrong port name")
            print("3. Another program is using the port")
            print("4. Insufficient permissions")
    
    return None

cap = cv2.VideoCapture(0)
model = YOLO("weights/best.pt")
classNames = ['With Helmet', 'Without Helmet']

print("Attempting to connect to Arduino...")
arduino = connect_to_arduino()

if arduino is None:
    user_choice = input("\nCouldn't connect to Arduino. Run without Arduino? (y/n): ")
    if user_choice.lower() != 'y':
        print("Exiting program")
        exit()

last_sent_state = None
send_interval = 1.0
last_send_time = time.time()

def send_to_arduino(value):
    if arduino is not None:
        try:
            arduino.write(str(value).encode())
            arduino.flush()
            print(f"Sent {value} to Arduino")
            return True
        except serial.SerialException as e:
            print(f"Error sending to Arduino: {str(e)}")
            return False

try:
    while True:
        success, img = cap.read()
        if not success:
            print("Failed to grab frame")
            break
            
        results = model(img, stream=True)
        current_state = 0
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                w, h = x2 - x1, y2 - y1
                cvzone.cornerRect(img, (x1, y1, w, h))
                
                conf = math.ceil((box.conf[0]*100)) / 100
                cls = int(box.cls[0])
                
                if cls == 0 and conf > 0.5:
                    current_state = 1
                
                cvzone.putTextRect(img, f'{classNames[cls]} {conf}', 
                                 (max(0, x1), max(35, y1)), 
                                 scale=1, thickness=1)
        
        current_time = time.time()
        if (current_state != last_sent_state and 
            current_time - last_send_time >= send_interval):
            if send_to_arduino(current_state):
                last_sent_state = current_state
                last_send_time = current_time
        
        status = "Helmet Detected" if current_state == 1 else "No Helmet Detected"
        cv2.putText(img, f"Status: {status}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        connection_status = "Arduino Connected" if arduino else "Arduino Not Connected"
        cv2.putText(img, connection_status, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, 
                   (0, 255, 0) if arduino else (0, 0, 255), 2)
        
        cv2.imshow("Image", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    if arduino is not None:
        arduino.close()