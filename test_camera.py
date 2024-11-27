import serial
import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
from PIL import Image, ImageTk
import threading
import time

class SerialImageReader:
    def __init__(self, master):
        self.master = master
        master.title("OV7670 Serial Image Reader")
        master.geometry("480x400")

        # Status Label
        self.status_label = tk.Label(master, text="-", anchor='w')
        self.status_label.pack(fill='x', padx=10, pady=5)

        # Image Display
        self.image_label = tk.Label(master)
        self.image_label.pack(padx=10, pady=10)

        # Serial Port Selection
        self.port_frame = tk.Frame(master)
        self.port_frame.pack(pady=10)

        tk.Label(self.port_frame, text="Serial Port:").pack(side='left')
        self.port_combobox = tk.StringVar(master)
        self.port_dropdown = tk.OptionMenu(self.port_frame, self.port_combobox, "")
        self.port_dropdown.pack(side='left', padx=10)

        # Buttons
        self.button_frame = tk.Frame(master)
        self.button_frame.pack(pady=10)

        self.check_ports_btn = tk.Button(self.button_frame, text="Check Ports", command=self.check_serial_ports)
        self.check_ports_btn.pack(side='left', padx=5)

        self.start_btn = tk.Button(self.button_frame, text="Start", command=self.start_reading)
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = tk.Button(self.button_frame, text="Stop", command=self.stop_reading, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        self.save_btn = tk.Button(self.button_frame, text="Save Picture", command=self.save_image)
        self.save_btn.pack(side='left', padx=5)

        # Image capture attributes
        self.WIDTH = 240
        self.HEIGHT = 320
        self.serial_port = None
        self.is_reading = False
        self.current_image = None

        # Initial port check
        self.check_serial_ports()

    def check_serial_ports(self):
        import serial.tools.list_ports
        ports = [port.device for port in serial.tools.list_ports.comports()]

        self.port_dropdown['menu'].delete(0, 'end')
        for port in ports:
            self.port_dropdown['menu'].add_command(label=port, command=tk._setit(self.port_combobox, port))

        if ports:
            self.port_combobox.set(ports[0])
            self.start_btn.config(state='normal')
            self.update_status(f"Found {len(ports)} ports")
        else:
            self.start_btn.config(state='disabled')
            self.update_status("No serial ports found")

    def update_status(self, message):
        self.status_label.config(text=message)

    def start_reading(self):
        try:
            port = self.port_combobox.get()
            self.serial_port = serial.Serial(
                port=port, 
                baudrate=1000000, 
                bytesize=8, 
                parity='N', 
                stopbits=1,
                timeout=3
            )

            self.update_status(f"Opening {port} port...")
            self.is_reading = True

            # Start reading in a separate thread
            threading.Thread(target=self.read_image_thread, daemon=True).start()

            self.start_btn.config(state='disabled')
            self.stop_btn.config(state='normal')
        except Exception as e:
            self.update_status(f"Error: {str(e)}")

    def read_image_thread(self):
        try:
            start_time = time.time()
            
            while self.is_reading:
                # Read header
                header = self.serial_port.read(5)
                
                # Check for *RDY* marker (ASCII values: 42, 82, 68, 89, 42)
                if (len(header) == 5 and 
                    header[0] == 42 and header[1] == 82 and 
                    header[2] == 68 and header[3] == 89 and 
                    header[4] == 42):
                    
                    self.update_status("Found *RDY*")
                    self.update_status(f"Reading image from serial port {self.port_combobox.get()}...")

                    # Create bitmap
                    self.current_image = Image.new('RGB', (self.WIDTH, self.HEIGHT))
                    pixels = self.current_image.load()

                    # Read pixel data
                    for x in range(self.WIDTH):
                        for y in range(self.HEIGHT - 1, -1, -1):
                            if not self.is_reading:
                                return
                            
                            # Read single byte for R, G, B (grayscale)
                            pixel_value = self.serial_port.read(1)[0]
                            
                            # Set R, G, B to the same value (grayscale)
                            pixels[x, y] = (pixel_value, pixel_value, pixel_value)

                    # Display image in Tkinter
                    tk_image = ImageTk.PhotoImage(self.current_image)
                    self.image_label.config(image=tk_image)
                    self.image_label.image = tk_image

                    # Calculate and display time taken
                    end_time = time.time()
                    time_taken = int((end_time - start_time) * 1000)
                    self.update_status(f"Image was read. Time taken: {time_taken} ms")

                    # Small delay to prevent overwhelming the port
                    time.sleep(0.5)

                    # If stop button was pressed during reading
                    if not self.is_reading:
                        self.stop_reading()
                        break
        except Exception as e:
            self.update_status(f"Reading error: {str(e)}")
        finally:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                self.is_reading = False

    def stop_reading(self):
        self.is_reading = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()

        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.update_status("Reading stopped")

    def save_image(self):
        if self.current_image:
            filename = filedialog.asksaveasfilename(
                defaultextension=".bmp", 
                filetypes=[("Bitmap files", "*.bmp")]
            )
            if filename:
                self.current_image.save(filename)
        else:
            messagebox.showinfo("Save Image", "No image to save")

def main():
    root = tk.Tk()
    app = SerialImageReader(root)
    root.mainloop()

if __name__ == "__main__":
    main()