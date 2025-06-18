import asyncio
import customtkinter as ctk
from tkinter import messagebox
import threading
from bleak import BleakScanner, BleakClient
import logging
from PIL import Image, ImageTk
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernBLERelayController:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("BLE Relay Controller Pro")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Set window icon and styling
        self.root.iconbitmap(default="")  # You can add an .ico file here
        
        # BLE related variables
        self.client = None
        self.connected_device = None
        self.characteristic_uuid = "12345678-1234-1234-1234-123456789abc"  # Replace with your ESP32's characteristic UUID
        
        # UI variables
        self.relay_states = [False, False, False, False]
        self.relay_buttons = []
        self.scanning = False
        
        # Animation variables
        self.pulse_animation = {}
        
        # Create the UI
        self.create_modern_ui()
        
        # Start the async event loop in a separate thread
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.start_event_loop, daemon=True)
        self.thread.start()
        
    def start_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        
    def create_modern_ui(self):
        # Configure grid weights for the main window
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Header Frame
        self.create_header()
        
        # Main Content Frame
        self.create_main_content()
        
        # Footer Frame
        self.create_footer()
        
    def create_header(self):
        """Create modern header with title and connection status"""
        header_frame = ctk.CTkFrame(self.root, height=80, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(1, weight=1)
        
        # App Title
        title_label = ctk.CTkLabel(
            header_frame, 
            text="⚡ BLE Relay Controller Pro",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=("#1f6aa5", "#4a9eff")
        )
        title_label.grid(row=0, column=0, padx=30, pady=20, sticky="w")
        
        # Connection Status Indicator
        self.status_frame = ctk.CTkFrame(header_frame, width=200, height=50)
        self.status_frame.grid(row=0, column=1, padx=30, pady=15, sticky="e")
        
        self.status_indicator = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=ctk.CTkFont(size=20),
            text_color="#ff4757"  # Red for disconnected
        )
        self.status_indicator.grid(row=0, column=0, padx=(15, 5), pady=12, sticky="w")
        
        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Disconnected",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.status_text.grid(row=0, column=1, padx=(0, 15), pady=12, sticky="w")
        
    def create_main_content(self):
        """Create main content area with connection and relay controls"""
        main_frame = ctk.CTkFrame(self.root, corner_radius=15)
        main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Connection Section
        self.create_connection_section(main_frame)
        
        # Relay Control Section
        self.create_relay_section(main_frame)
        
    def create_connection_section(self, parent):
        """Create modern connection controls"""
        connection_frame = ctk.CTkFrame(parent, height=120)
        connection_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        connection_frame.grid_columnconfigure(1, weight=1)
        
        # Section Title
        conn_title = ctk.CTkLabel(
            connection_frame,
            text="🔗 Device Connection",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        conn_title.grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")
        
        # Device Selection
        device_label = ctk.CTkLabel(
            connection_frame,
            text="Select Device:",
            font=ctk.CTkFont(size=14)
        )
        device_label.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="w")
        
        self.device_combo = ctk.CTkComboBox(
            connection_frame,
            width=300,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            state="readonly"
        )
        self.device_combo.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        
        # Control Buttons Frame
        button_frame = ctk.CTkFrame(connection_frame, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="ew")
        
        self.scan_btn = ctk.CTkButton(
            button_frame,
            text="🔍 Scan Devices",
            command=self.scan_devices,
            width=140,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#2fa572", "#2fa572"),
            hover_color=("#1e7f4f", "#2b9348")
        )
        self.scan_btn.grid(row=0, column=0, padx=(0, 10), pady=5)
        
        self.connect_btn = ctk.CTkButton(
            button_frame,
            text="🔌 Connect",
            command=self.connect_device,
            width=140, 
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#1f6aa5", "#4a9eff"),
            hover_color=("#144870", "#2e7cd6")
        )
        self.connect_btn.grid(row=0, column=1, padx=10, pady=5)
        
        self.disconnect_btn = ctk.CTkButton(
            button_frame,
            text="❌ Disconnect",
            command=self.disconnect_device,
            width=140,
            height=35,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#d63031", "#ff4757"),
            hover_color=("#a4161a", "#e84545"),
            state="disabled"
        )
        self.disconnect_btn.grid(row=0, column=2, padx=(10, 0), pady=5)
        
    def create_relay_section(self, parent):
        """Create modern relay control section"""
        relay_main_frame = ctk.CTkFrame(parent)
        relay_main_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        relay_main_frame.grid_columnconfigure(0, weight=1)
        relay_main_frame.grid_rowconfigure(1, weight=1)
        
        # Section Title
        relay_title = ctk.CTkLabel(
            relay_main_frame,
            text="⚙️ Relay Controls",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        relay_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Relay Grid Container
        relay_container = ctk.CTkFrame(relay_main_frame, fg_color="transparent")
        relay_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(10, 20))
        
        # Configure grid for 2x2 layout
        for i in range(2):
            relay_container.grid_rowconfigure(i, weight=1)
            relay_container.grid_columnconfigure(i, weight=1)
        
        # Create relay buttons
        relay_colors = [
            ("#e74c3c", "#c0392b"),  # Red
            ("#3498db", "#2980b9"),  # Blue  
            ("#f39c12", "#e67e22"),  # Orange
            ("#2ecc71", "#27ae60")   # Green
        ]
        
        relay_icons = ["🔌", "💡", "🌡️", "🔋"]
        
        for i in range(4):
            row = i // 2
            col = i % 2
            
            # Create relay button with custom styling
            relay_frame = ctk.CTkFrame(relay_container, corner_radius=15)
            relay_frame.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            
            btn = ctk.CTkButton(
                relay_frame,
                text=f"{relay_icons[i]}\nRelay {i+1}\nOFF",
                font=ctk.CTkFont(size=16, weight="bold"),
                width=200,
                height=120,
                corner_radius=12,
                fg_color=("#565b5e", "#52595d"),
                hover_color=("#4a4f52", "#484e52"),
                text_color=("white", "white")
            )
            btn.pack(padx=15, pady=15, fill="both", expand=True)
            
            # Bind events for press and release
            btn.bind("<Button-1>", lambda e, idx=i: self.relay_press(idx))
            btn.bind("<ButtonRelease-1>", lambda e, idx=i: self.relay_release(idx))
            
            self.relay_buttons.append((btn, relay_colors[i], relay_icons[i]))
            
    def create_footer(self):
        """Create footer with info and credits"""
        footer_frame = ctk.CTkFrame(self.root, height=50, corner_radius=0)
        footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        
        info_label = ctk.CTkLabel(
            footer_frame,
            text="💡 Hold relay buttons to turn ON • Release to turn OFF • Powered by CustomTkinter",
            font=ctk.CTkFont(size=12),
            text_color=("#7f8c8d", "#95a5a6")
        )
        info_label.pack(pady=15)
        
    def scan_devices(self):
        """Scan for BLE devices with modern UI feedback"""
        if self.scanning:
            return
            
        self.scanning = True
        self.scan_btn.configure(text="🔄 Scanning...", state="disabled")
        self.device_combo.configure(values=[])
        
        # Start scanning animation
        self.start_scan_animation()
        
        def scan_task():
            asyncio.run_coroutine_threadsafe(self._scan_devices(), self.loop)
            
        threading.Thread(target=scan_task, daemon=True).start()
        
    def start_scan_animation(self):
        """Animate the scan button"""
        if not self.scanning:
            return
            
        current_text = self.scan_btn.cget("text")
        if "Scanning" in current_text:
            dots = current_text.count(".")
            if dots >= 3:
                new_text = "🔄 Scanning"
            else:
                new_text = current_text + "."
                
            self.scan_btn.configure(text=new_text)
            self.root.after(500, self.start_scan_animation)
        
    async def _scan_devices(self):
        """Async scan for BLE devices"""
        try:
            devices = await BleakScanner.discover(timeout=10.0)
            device_list = []
            
            for device in devices:
                name = device.name or "Unknown Device"
                device_list.append(f"{name} ({device.address})")
                
            # Update UI in main thread
            self.root.after(0, self._update_device_list, device_list)
            
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.root.after(0, self._scan_error, str(e))
            
    def _update_device_list(self, device_list):
        """Update device list in UI"""
        self.scanning = False
        self.device_combo.configure(values=device_list)
        self.scan_btn.configure(text="🔍 Scan Devices", state="normal")
        
        if device_list:
            # Show success with modern dialog
            self.show_custom_message("Scan Complete", f"Found {len(device_list)} devices", "success")
            if device_list:
                self.device_combo.set(device_list[0])  # Auto-select first device
        else:
            self.show_custom_message("Scan Complete", "No devices found", "warning")
            
    def _scan_error(self, error_msg):
        """Handle scan error"""
        self.scanning = False
        self.scan_btn.configure(text="🔍 Scan Devices", state="normal")
        self.show_custom_message("Scan Error", f"Failed to scan devices: {error_msg}", "error")
        
    def show_custom_message(self, title, message, msg_type="info"):
        """Show custom styled message"""
        if msg_type == "success":
            messagebox.showinfo(title, message)
        elif msg_type == "warning":
            messagebox.showwarning(title, message)
        elif msg_type == "error":
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)
        
    def connect_device(self):
        """Connect to selected device"""
        selected = self.device_combo.get()
        if not selected:
            self.show_custom_message("No Device", "Please select a device first", "warning")
            return
            
        # Extract MAC address from selection
        try:
            address = selected.split('(')[1].split(')')[0]
            self.connect_btn.configure(text="🔄 Connecting...", state="disabled")
            
            def connect_task():
                asyncio.run_coroutine_threadsafe(self._connect_device(address), self.loop)
                
            threading.Thread(target=connect_task, daemon=True).start()
            
        except Exception as e:
            self.show_custom_message("Connection Error", f"Invalid device selection: {e}", "error")
            
    async def _connect_device(self, address):
        """Async connect to device"""
        try:
            self.client = BleakClient(address)
            await self.client.connect()
            
            # Update UI in main thread
            self.root.after(0, self._connection_success)
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.root.after(0, self._connection_error, str(e))
            
    def _connection_success(self):
        """Handle successful connection with modern UI updates"""
        self.connected_device = self.device_combo.get()
        
        # Update status indicator
        self.status_indicator.configure(text_color="#2ecc71")  # Green
        self.status_text.configure(text="Connected")
        
        # Update buttons
        self.connect_btn.configure(text="🔌 Connect", state="disabled")
        self.disconnect_btn.configure(state="normal")
        
        self.show_custom_message("Connected", f"Successfully connected to {self.connected_device}", "success")
        
        # Start connection pulse animation
        self.start_status_pulse()
        
    def start_status_pulse(self):
        """Animate the connection status indicator"""
        if self.client and hasattr(self.client, 'is_connected') and self.client.is_connected:
            # Pulse between two green shades
            current_color = self.status_indicator.cget("text_color")
            if current_color == "#2ecc71":
                self.status_indicator.configure(text_color="#27ae60")
            else:
                self.status_indicator.configure(text_color="#2ecc71")
                
            self.root.after(1000, self.start_status_pulse)
        
    def _connection_error(self, error_msg):
        """Handle connection error"""
        self.connect_btn.configure(text="🔌 Connect", state="normal")
        self.show_custom_message("Connection Error", f"Failed to connect: {error_msg}", "error")
        
    def disconnect_device(self):
        """Disconnect from device"""
        self.disconnect_btn.configure(text="🔄 Disconnecting...", state="disabled")
        
        def disconnect_task():
            asyncio.run_coroutine_threadsafe(self._disconnect_device(), self.loop)
            
        threading.Thread(target=disconnect_task, daemon=True).start()
        
    async def _disconnect_device(self):
        """Async disconnect from device"""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
                
            self.root.after(0, self._disconnection_success)
            
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            self.root.after(0, self._disconnection_error, str(e))
            
    def _disconnection_success(self):
        """Handle successful disconnection"""
        self.client = None
        self.connected_device = None
        
        # Update status
        self.status_indicator.configure(text_color="#ff4757")  # Red
        self.status_text.configure(text="Disconnected")
        
        # Update buttons
        self.connect_btn.configure(state="normal")
        self.disconnect_btn.configure(text="❌ Disconnect", state="disabled")
        
        # Reset all relay states
        for i in range(4):
            self.relay_states[i] = False  
            btn, colors, icon = self.relay_buttons[i]
            btn.configure(
                text=f"{icon}\nRelay {i+1}\nOFF",
                fg_color=("#565b5e", "#52595d"),
                hover_color=("#4a4f52", "#484e52")
            )
            
    def _disconnection_error(self, error_msg):
        """Handle disconnection error"""
        self.disconnect_btn.configure(text="❌ Disconnect", state="normal")
        self.show_custom_message("Disconnection Error", f"Failed to disconnect: {error_msg}", "error")
        
    def relay_press(self, relay_index):
        """Handle relay button press with modern animations"""
        if not self.client or not self.client.is_connected:
            self.show_custom_message("Not Connected", "Please connect to a device first", "warning")
            return
            
        self.relay_states[relay_index] = True
        btn, colors, icon = self.relay_buttons[relay_index]
        
        # Update button appearance
        btn.configure(
            text=f"{icon}\nRelay {relay_index+1}\nON",
            fg_color=colors[0],
            hover_color=colors[1]
        )
        
        # Send command to ESP32
        self.send_relay_command(relay_index, 1)
        
        # Start pulse animation for active relay
        self.start_relay_pulse(relay_index)
        
    def start_relay_pulse(self, relay_index):
        """Animate active relay button"""
        if not self.relay_states[relay_index]:
            return
            
        btn, colors, icon = self.relay_buttons[relay_index]
        current_color = btn.cget("fg_color")
        
        if current_color == colors[0]:
            btn.configure(fg_color=colors[1])
        else:
            btn.configure(fg_color=colors[0])
            
        if self.relay_states[relay_index]:
            self.root.after(500, lambda: self.start_relay_pulse(relay_index))
        
    def relay_release(self, relay_index):
        """Handle relay button release"""
        if not self.client or not self.client.is_connected:
            return
            
        self.relay_states[relay_index] = False
        btn, colors, icon = self.relay_buttons[relay_index]
        
        # Reset button appearance
        btn.configure(
            text=f"{icon}\nRelay {relay_index+1}\nOFF",
            fg_color=("#565b5e", "#52595d"),
            hover_color=("#4a4f52", "#484e52")
        )
        
        # Send command to ESP32
        self.send_relay_command(relay_index, 0)
        
    def send_relay_command(self, relay_index, state):
        """Send relay command to ESP32"""
        def send_task():
            asyncio.run_coroutine_threadsafe(
                self._send_relay_command(relay_index, state), self.loop)
            
        threading.Thread(target=send_task, daemon=True).start()
        
    async def _send_relay_command(self, relay_index, state):
        """Async send relay command"""
        try:
            if self.client and self.client.is_connected:
                # Format: "R<relay_number><state>" (e.g., "R11" for relay 1 ON, "R10" for relay 1 OFF)
                command = f"R{relay_index + 1}{state}"
                await self.client.write_gatt_char(self.characteristic_uuid, command.encode())
                logger.info(f"Sent command: {command}")
                
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            self.root.after(0, lambda: self.show_custom_message("Command Error", 
                                                               f"Failed to send command: {e}", "error"))
            
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        finally:
            # Clean up
            if self.client:
                asyncio.run_coroutine_threadsafe(self._disconnect_device(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)

if __name__ == "__main__":
    app = ModernBLERelayController()
    app.run()