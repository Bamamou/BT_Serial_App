import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import queue
import time
import serial
import serial.tools.list_ports
from datetime import datetime
import asyncio
import sys
from PIL import Image, ImageTk
import tkinter as tk

# Try to import bleak for modern Bluetooth support
try:
    import bleak
    from bleak import BleakScanner, BleakClient
    BLEAK_AVAILABLE = True
    print("Bleak successfully imported!")
except ImportError as e:
    BLEAK_AVAILABLE = False
    print(f"Bleak import failed: {e}")
except Exception as e:
    BLEAK_AVAILABLE = False
    print(f"Bleak import error: {e}")

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class ModernBluetoothApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluetooth Serial Data Receiver")
        self.root.geometry("1100x800")
        self.root.minsize(900, 600)
        
        # Connection variables
        self.connection = None
        self.connected = False
        self.receive_thread = None
        self.data_queue = queue.Queue()
        self.connection_type = "serial"
        self.data_count = 0
        
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create main layout
        self.create_sidebar()
        self.create_main_content()
        
        # Start GUI update loop
        self.update_gui()
        
        # Initial scan
        self.scan_devices()
        
    def create_sidebar(self):
        """Create the left sidebar with controls"""
        # Sidebar frame
        self.sidebar_frame = ctk.CTkFrame(self.root, width=350, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        # App title
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🔗 Bluetooth Monitor", 
                                      font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))
        
        # Connection type section
        self.conn_type_label = ctk.CTkLabel(self.sidebar_frame, text="Connection Type", 
                                           font=ctk.CTkFont(size=16, weight="bold"))
        self.conn_type_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.conn_type_var = ctk.StringVar(value="serial")
        
        self.serial_radio = ctk.CTkRadioButton(self.sidebar_frame, text="Serial/COM Port", 
                                              variable=self.conn_type_var, value="serial",
                                              command=self.on_connection_type_change)
        self.serial_radio.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        ble_text = f"Bluetooth LE (BLE)" + ("" if BLEAK_AVAILABLE else " (Unavailable)")
        self.ble_radio = ctk.CTkRadioButton(self.sidebar_frame, text=ble_text,
                                           variable=self.conn_type_var, value="ble",
                                           command=self.on_connection_type_change,
                                           state="normal" if BLEAK_AVAILABLE else "disabled")
        self.ble_radio.grid(row=3, column=0, padx=20, pady=5, sticky="w")
        
        # Device selection section
        self.device_label = ctk.CTkLabel(self.sidebar_frame, text="Device Selection", 
                                        font=ctk.CTkFont(size=16, weight="bold"))
        self.device_label.grid(row=5, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.device_combo = ctk.CTkComboBox(self.sidebar_frame, width=300, state="readonly")
        self.device_combo.grid(row=6, column=0, padx=20, pady=5)
        
        self.scan_btn = ctk.CTkButton(self.sidebar_frame, text="🔍 Scan Devices", 
                                     command=self.scan_devices, width=300)
        self.scan_btn.grid(row=7, column=0, padx=20, pady=10)
        
        # Serial settings frame (initially visible)
        self.serial_settings_frame = ctk.CTkFrame(self.sidebar_frame)
        self.serial_settings_frame.grid(row=8, column=0, padx=20, pady=10, sticky="ew")
        
        ctk.CTkLabel(self.serial_settings_frame, text="Serial Settings", 
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        ctk.CTkLabel(self.serial_settings_frame, text="Baud Rate:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.baud_combo = ctk.CTkComboBox(self.serial_settings_frame, 
                                         values=["9600", "19200", "38400", "57600", "115200"],
                                         width=100)
        self.baud_combo.set("9600")
        self.baud_combo.grid(row=1, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(self.serial_settings_frame, text="Data Bits:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.databits_combo = ctk.CTkComboBox(self.serial_settings_frame, values=["7", "8"], width=100)
        self.databits_combo.set("8")
        self.databits_combo.grid(row=2, column=1, padx=5, pady=2)
        
        # Connection section
        self.connection_label = ctk.CTkLabel(self.sidebar_frame, text="Connection", 
                                           font=ctk.CTkFont(size=16, weight="bold"))
        self.connection_label.grid(row=9, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.connect_btn = ctk.CTkButton(self.sidebar_frame, text="🔌 Connect", 
                                        command=self.toggle_connection, width=300, height=40,
                                        font=ctk.CTkFont(size=14, weight="bold"))
        self.connect_btn.grid(row=10, column=0, padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="🔴 Disconnected", 
                                        font=ctk.CTkFont(size=12))
        self.status_label.grid(row=11, column=0, padx=20, pady=5)
        
        # Statistics section
        self.stats_frame = ctk.CTkFrame(self.sidebar_frame)
        self.stats_frame.grid(row=12, column=0, padx=20, pady=20, sticky="ew")
        
        ctk.CTkLabel(self.stats_frame, text="Statistics", 
                    font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        self.data_count_label = ctk.CTkLabel(self.stats_frame, text="Messages: 0")
        self.data_count_label.grid(row=1, column=0, columnspan=2, pady=2)
        
        self.connection_time_label = ctk.CTkLabel(self.stats_frame, text="Connected: --:--:--")
        self.connection_time_label.grid(row=2, column=0, columnspan=2, pady=2)
        
    def create_main_content(self):
        """Create the main content area"""
        # Main content frame
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header frame
        self.header_frame = ctk.CTkFrame(self.main_frame, height=60)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        # Data display title
        self.data_title = ctk.CTkLabel(self.header_frame, text="📊 Data Monitor", 
                                      font=ctk.CTkFont(size=20, weight="bold"))
        self.data_title.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        # Header controls
        self.controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.controls_frame.grid(row=0, column=1, padx=20, pady=10, sticky="e")
        
        # Display format
        self.format_label = ctk.CTkLabel(self.controls_frame, text="Format:")
        self.format_label.grid(row=0, column=0, padx=(0, 5))
        
        self.display_format = ctk.StringVar(value="text")
        self.format_combo = ctk.CTkComboBox(self.controls_frame, values=["Text", "Hex"], 
                                           width=80, command=self.on_format_change)
        self.format_combo.set("Text")
        self.format_combo.grid(row=0, column=1, padx=5)
        
        # Auto-scroll switch
        self.auto_scroll_var = ctk.BooleanVar(value=True)
        self.auto_scroll_switch = ctk.CTkSwitch(self.controls_frame, text="Auto-scroll",
                                               variable=self.auto_scroll_var)
        self.auto_scroll_switch.grid(row=0, column=2, padx=10)
        
        # Data display area
        self.data_frame = ctk.CTkFrame(self.main_frame)
        self.data_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.data_frame.grid_columnconfigure(0, weight=1)
        self.data_frame.grid_rowconfigure(0, weight=1)
        
        # Text area with scrollbar
        self.data_textbox = ctk.CTkTextbox(self.data_frame, font=ctk.CTkFont(family="Consolas", size=12))
        self.data_textbox.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Bottom controls
        self.bottom_controls = ctk.CTkFrame(self.main_frame, height=50)
        self.bottom_controls.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.clear_btn = ctk.CTkButton(self.bottom_controls, text="🗑️ Clear", 
                                      command=self.clear_data, width=100)
        self.clear_btn.grid(row=0, column=0, padx=20, pady=10)
        
        self.save_btn = ctk.CTkButton(self.bottom_controls, text="💾 Save Data", 
                                     command=self.save_data, width=120)
        self.save_btn.grid(row=0, column=1, padx=10, pady=10)
        
        self.export_btn = ctk.CTkButton(self.bottom_controls, text="📤 Export CSV", 
                                       command=self.export_csv, width=120)
        self.export_btn.grid(row=0, column=2, padx=10, pady=10)
        
        # Theme switch
        self.theme_btn = ctk.CTkButton(self.bottom_controls, text="🌙 Dark Theme", 
                                      command=self.toggle_theme, width=120)
        self.theme_btn.grid(row=0, column=3, padx=10, pady=10)
        
    def on_connection_type_change(self):
        """Handle connection type change"""
        self.connection_type = self.conn_type_var.get()
        if self.connection_type == "serial":
            self.serial_settings_frame.grid()
        else:
            self.serial_settings_frame.grid_remove()
        self.scan_devices()
        
    def on_format_change(self, choice):
        """Handle display format change"""
        self.display_format.set(choice.lower())
        
    def scan_devices(self):
        """Scan for available devices based on connection type"""
        self.scan_btn.configure(state="disabled", text="🔍 Scanning...")
        self.device_combo.configure(values=[])
        
        if self.connection_type == "serial":
            self.scan_serial_ports()
        elif self.connection_type == "ble" and BLEAK_AVAILABLE:
            self.scan_ble_devices()
        else:
            self.scan_btn.configure(state="normal", text="🔍 Scan Devices")
            messagebox.showerror("Error", "BLE not available. Install bleak: pip install bleak")
            
    def scan_serial_ports(self):
        """Scan for available serial/COM ports"""
        def scan_worker():
            try:
                ports = serial.tools.list_ports.comports()
                port_list = []
                
                for port in ports:
                    description = port.description.lower()
                    if any(keyword in description for keyword in ['bluetooth', 'bt', 'serial']):
                        port_list.insert(0, f"{port.device} - {port.description}")
                    else:
                        port_list.append(f"{port.device} - {port.description}")
                
                self.root.after(0, self.update_device_list, port_list, "serial")
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Port scan failed: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.scan_btn.configure(state="normal", text="🔍 Scan Devices"))
                
        threading.Thread(target=scan_worker, daemon=True).start()
        
    def scan_ble_devices(self):
        """Scan for BLE devices"""
        def scan_worker():
            try:
                async def ble_scan():
                    devices = await BleakScanner.discover(timeout=10)
                    return [(device.address, device.name or "Unknown Device") for device in devices]
                
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                devices = loop.run_until_complete(ble_scan())
                loop.close()
                
                device_list = [f"{name} ({addr})" for addr, name in devices]
                self.root.after(0, self.update_device_list, device_list, "ble")
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"BLE scan failed: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.scan_btn.configure(state="normal", text="🔍 Scan Devices"))
                
        threading.Thread(target=scan_worker, daemon=True).start()
        
    def update_device_list(self, devices, scan_type):
        """Update the device combobox with found devices"""
        self.device_combo.configure(values=devices)
        if devices:
            self.device_combo.set(devices[0])
            self.show_notification(f"Found {len(devices)} {scan_type} devices", "success")
        else:
            self.show_notification(f"No {scan_type} devices found", "warning")
            
    def show_notification(self, message, type="info"):
        """Show a temporary notification"""
        # Create notification frame
        notification = ctk.CTkFrame(self.main_frame, fg_color=("gray70", "gray25"))
        notification.place(relx=0.5, rely=0.1, anchor="center")
        
        color = {"success": "green", "warning": "orange", "error": "red", "info": "blue"}[type]
        
        label = ctk.CTkLabel(notification, text=message, text_color=color,
                            font=ctk.CTkFont(size=12, weight="bold"))
        label.pack(padx=20, pady=10)
        
        # Auto-hide after 3 seconds
        self.root.after(3000, notification.destroy)
        
    def get_device_identifier(self):
        """Get device identifier from selected device string"""
        device_str = self.device_combo.get()
        if not device_str:
            return None
            
        if self.connection_type == "serial":
            return device_str.split(" - ")[0]
        else:
            start = device_str.rfind('(') + 1
            end = device_str.rfind(')')
            return device_str[start:end]
            
    def toggle_connection(self):
        """Connect or disconnect from selected device"""
        if not self.connected:
            self.connect_device()
        else:
            self.disconnect_device()
            
    def connect_device(self):
        """Connect to the selected device"""
        device_id = self.get_device_identifier()
        if not device_id:
            messagebox.showerror("Error", "Please select a device first")
            return
            
        self.connect_btn.configure(state="disabled", text="🔄 Connecting...")
        self.status_label.configure(text="🟡 Connecting...")
        
        if self.connection_type == "serial":
            self.connect_serial(device_id)
        elif self.connection_type == "ble":
            self.connect_ble(device_id)
            
    def connect_serial(self, port):
        """Connect to serial port"""
        def connect_worker():
            try:
                self.connection = serial.Serial(
                    port=port,
                    baudrate=int(self.baud_combo.get()),
                    bytesize=int(self.databits_combo.get()),
                    stopbits=1,
                    timeout=1
                )
                self.connection_start_time = datetime.now()
                self.root.after(0, self.on_connected)
                
            except Exception as e:
                self.root.after(0, lambda: self.on_connection_failed(str(e)))
                
        threading.Thread(target=connect_worker, daemon=True).start()
        
    def connect_ble(self, address):
        """Connect to BLE device"""
        def connect_worker():
            try:
                async def ble_connect():
                    self.connection = BleakClient(address)
                    await self.connection.connect()
                    return True
                
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                    
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(ble_connect())
                
                if success:
                    self.connection_start_time = datetime.now()
                    self.root.after(0, self.on_connected)
                else:
                    self.root.after(0, lambda: self.on_connection_failed("Connection failed"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.on_connection_failed(str(e)))
                
        threading.Thread(target=connect_worker, daemon=True).start()
        
    def on_connected(self):
        """Handle successful connection"""
        self.connected = True
        self.connect_btn.configure(state="normal", text="🔌 Disconnect", fg_color="red", hover_color="darkred")
        self.status_label.configure(text="🟢 Connected")
        self.show_notification("Successfully connected!", "success")
        self.start_receiving()
        
    def on_connection_failed(self, error_msg):
        """Handle connection failure"""
        self.connect_btn.configure(state="normal", text="🔌 Connect", fg_color=None, hover_color=None)
        self.status_label.configure(text="🔴 Connection Failed")
        self.show_notification(f"Connection failed: {error_msg}", "error")
        
    def start_receiving(self):
        """Start receiving data"""
        if self.connection_type == "serial":
            self.start_serial_receiving()
        elif self.connection_type == "ble":
            self.start_ble_receiving()
            
    def start_serial_receiving(self):
        """Start receiving data from serial port"""
        def receive_worker():
            try:
                while self.connected and self.connection and self.connection.is_open:
                    try:
                        if self.connection.in_waiting > 0:
                            data = self.connection.read(self.connection.in_waiting)
                            if data:
                                self.process_received_data(data)
                        else:
                            time.sleep(0.01)
                            
                    except serial.SerialException as e:
                        if self.connected:
                            self.root.after(0, lambda: self.show_notification(f"Serial error: {str(e)}", "error"))
                        break
                        
            except Exception as e:
                if self.connected:
                    self.root.after(0, lambda: self.show_notification(f"Receive error: {str(e)}", "error"))
                    
            self.root.after(0, self.disconnect_device)
            
        self.receive_thread = threading.Thread(target=receive_worker, daemon=True)
        self.receive_thread.start()
        
    def start_ble_receiving(self):
        """Start receiving data from BLE device"""
        self.show_notification("BLE data receiving requires device-specific implementation", "info")
        
    def process_received_data(self, data):
        """Process received data and add to queue"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        if self.display_format.get() == "hex":
            formatted_data = " ".join([f"{b:02X}" for b in data])
        else:
            formatted_data = data.decode('utf-8', errors='ignore').strip()
            
        self.data_queue.put(f"[{timestamp}] {formatted_data}")
        self.data_count += 1
        
    def disconnect_device(self):
        """Disconnect from device"""
        self.connected = False
        
        if self.connection:
            try:
                if self.connection_type == "serial":
                    self.connection.close()
                elif self.connection_type == "ble":
                    pass  # BLE disconnect would be async
            except:
                pass
            self.connection = None
            
        self.connect_btn.configure(text="🔌 Connect", fg_color=None, hover_color=None)
        self.status_label.configure(text="🔴 Disconnected")
        
    def update_gui(self):
        """Update GUI with received data and statistics"""
        # Update received data
        try:
            while True:
                data = self.data_queue.get_nowait()
                self.data_textbox.insert("end", data + "\n")
                
                if self.auto_scroll_var.get():
                    self.data_textbox.see("end")
                    
        except queue.Empty:
            pass
            
        # Update statistics
        self.data_count_label.configure(text=f"Messages: {self.data_count}")
        
        if self.connected and hasattr(self, 'connection_start_time'):
            elapsed = datetime.now() - self.connection_start_time
            hours, remainder = divmod(elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.connection_time_label.configure(text=f"Connected: {hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.connection_time_label.configure(text="Connected: --:--:--")
            
        self.root.after(100, self.update_gui)
        
    def clear_data(self):
        """Clear the data display"""
        self.data_textbox.delete("1.0", "end")
        self.data_count = 0
        
    def save_data(self):
        """Save received data to file"""
        data = self.data_textbox.get("1.0", "end")
        if not data.strip():
            self.show_notification("No data to save", "warning")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(data)
                self.show_notification(f"Data saved successfully!", "success")
            except Exception as e:
                self.show_notification(f"Failed to save file: {str(e)}", "error")
                
    def export_csv(self):
        """Export data to CSV format"""
        data = self.data_textbox.get("1.0", "end").strip()
        if not data:
            self.show_notification("No data to export", "warning")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Data"])
                    
                    for line in data.split('\n'):
                        if line.strip() and line.startswith('['):
                            # Extract timestamp and data
                            end_bracket = line.find(']')
                            if end_bracket != -1:
                                timestamp = line[1:end_bracket]
                                data_part = line[end_bracket+2:]
                                writer.writerow([timestamp, data_part])
                                
                self.show_notification("Data exported to CSV successfully!", "success")
            except Exception as e:
                self.show_notification(f"Failed to export CSV: {str(e)}", "error")
                
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="🌙 Dark Theme")
        else:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="☀️ Light Theme")
            
    def on_closing(self):
        """Handle application closing"""
        if self.connected:
            self.disconnect_device()
        self.root.destroy()

def main():
    # Check dependencies
    missing_deps = []
    
    try:
        import customtkinter
    except ImportError:
        missing_deps.append("customtkinter")
        
    try:
        import serial
    except ImportError:
        missing_deps.append("pyserial")
        
    try:
        from PIL import Image
    except ImportError:
        missing_deps.append("Pillow")
    
    if missing_deps:
        print("Missing dependencies:")
        for dep in missing_deps:
            print(f"  pip install {dep}")
        print("\nInstall all at once:")
        print(f"  pip install {' '.join(missing_deps)}")
        return
        
    root = ctk.CTk()
    app = ModernBluetoothApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()