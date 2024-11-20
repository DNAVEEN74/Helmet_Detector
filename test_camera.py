import serial
import struct
import os

# BMP file header constants
FILE_HEADER_SIZE = 14
INFO_HEADER_SIZE = 40
PIXEL_ARRAY_OFFSET = FILE_HEADER_SIZE + INFO_HEADER_SIZE

def create_bmp_header(width, height):
    # BMP File Header
    file_size = PIXEL_ARRAY_OFFSET + (width * height * 3)
    file_header = struct.pack(
        '<2sIHHI',
        b'BM',        # Signature
        file_size,    # File size
        0,            # Reserved
        0,            # Reserved
        PIXEL_ARRAY_OFFSET  # Offset to pixel data
    )
    
    # BMP Info Header
    info_header = struct.pack(
        '<IIIHHIIIIII',
        INFO_HEADER_SIZE,  # Header size
        width,             # Image width
        height,            # Image height
        1,                 # Number of color planes
        24,                # Bits per pixel
        0,                 # Compression (0 = none)
        file_size - PIXEL_ARRAY_OFFSET,  # Image size
        2835,              # Horizontal resolution (72 DPI)
        2835,              # Vertical resolution (72 DPI)
        0,                 # Number of colors in palette
        0                  # Important colors
    )
    return file_header + info_header

def save_image_as_bmp(file_path, width, height, pixel_data):
    header = create_bmp_header(width, height)
    with open(file_path, 'wb') as bmp_file:
        bmp_file.write(header)
        # BMP pixel data is stored bottom-to-top
        for row in reversed(pixel_data):
            for color in row:
                bmp_file.write(color.to_bytes(3, 'little'))

def read_image_from_serial(port, width, height, marker):
    with serial.Serial(port, 1000000, timeout=5) as ser:
        print("Looking for image marker...")
        buffer = []
        while True:
            byte = ser.read(1)
            if not byte:
                raise RuntimeError("No data from serial port.")
            buffer.append(byte)
            if len(buffer) > len(marker):
                buffer.pop(0)
            if buffer == marker:
                print("Image marker found!")
                break
        
        print("Reading image data...")
        pixel_data = []
        for _ in range(height):
            row = []
            for _ in range(width):
                gray = ord(ser.read(1))
                row.append(gray | (gray << 8) | (gray << 16))  # Convert to RGB
            pixel_data.append(row)
        return pixel_data

if __name__ == "__main__":
    PORT = "COM2"
    WIDTH = 320
    HEIGHT = 240
    MARKER = [b'*', b'R', b'D', b'Y', b'*']
    OUTPUT_DIR = "./out"
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Track image counter
    image_counter = 1
    
    while True:
        try:
            img_data = read_image_from_serial(PORT, WIDTH, HEIGHT, MARKER)
            file_path = os.path.join(OUTPUT_DIR, f"{image_counter}.bmp")
            save_image_as_bmp(file_path, WIDTH, HEIGHT, img_data)
            print(f"Image {image_counter} saved as {file_path}")
            
            # Increment counter for next image
            image_counter += 1
            
        except Exception as e:
            print(f"Error: {e}")
            break