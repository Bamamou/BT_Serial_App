#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <Arduino.h>

// BLE Configuration
#define SERVICE_UUID        "12345678-1234-1234-1234-123456789abc"
#define CHARACTERISTIC_UUID "12345678-1234-1234-1234-123456789abc"
#define DEVICE_NAME         "ESP32-Relay-Controller"

// GPIO Pin Configuration (you can modify these)
#define RELAY_1_PIN     23   // GPIO 2
#define RELAY_2_PIN     5   // GPIO 4
#define RELAY_3_PIN     4  // GPIO 16
#define RELAY_4_PIN     13  // GPIO 17
#define LED_PIN         15  // Status LED (GPIO 18)
// #define BUZZER_PIN      19  // Optional buzzer (GPIO 19)


// FreeRTOS Configuration
#define STACK_SIZE      4096
#define QUEUE_SIZE      10

// Structure for relay commands
typedef struct {
    uint8_t relay_number;
    uint8_t state;
} RelayCommand;

// Global variables
BLEServer* pServer = nullptr;
BLECharacteristic* pCharacteristic = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// FreeRTOS handles
QueueHandle_t relayQueue;
TaskHandle_t relayTaskHandle;
TaskHandle_t statusTaskHandle;
TaskHandle_t heartbeatTaskHandle;

// Relay pin array for easy access
const int relayPins[4] = {RELAY_1_PIN, RELAY_2_PIN, RELAY_3_PIN, RELAY_4_PIN};
bool relayStates[4] = {false, false, false, false};

// BLE Server Callbacks
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        Serial.println("✅ Device Connected");
        
        // Turn on status LED
        digitalWrite(LED_PIN, HIGH);
        
        // Optional: Short beep to indicate connection
        // tone(BUZZER_PIN, 1000, 100);
    };

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        Serial.println("❌ Device Disconnected");
        
        // Turn off status LED
        digitalWrite(LED_PIN, LOW);
        
        // Turn off all relays for safety
        for (int i = 0; i < 4; i++) {
            digitalWrite(relayPins[i], LOW);
            relayStates[i] = false;
        }
        
        // Optional: Double beep to indicate disconnection
        // tone(BUZZER_PIN, 500, 100);
        // delay(150);
        // tone(BUZZER_PIN, 500, 100);
    }
};

// BLE Characteristic Callbacks
class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string rxValue = pCharacteristic->getValue();

        if (rxValue.length() > 0) {
            Serial.print("📨 Received: ");
            for (int i = 0; i < rxValue.length(); i++) {
                Serial.print(rxValue[i]);
            }
            Serial.println();

            // Parse command (format: "R<relay_number><state>")
            if (rxValue.length() >= 3 && rxValue[0] == 'R') {
                RelayCommand cmd;
                cmd.relay_number = rxValue[1] - '0';  // Convert char to int
                cmd.state = rxValue[2] - '0';         // Convert char to int
                
                // Validate command
                if (cmd.relay_number >= 1 && cmd.relay_number <= 4 && 
                    (cmd.state == 0 || cmd.state == 1)) {
                    
                    // Send command to relay task
                    if (xQueueSend(relayQueue, &cmd, pdMS_TO_TICKS(100)) == pdTRUE) {
                        Serial.printf("✅ Command queued: Relay %d -> %s\n", 
                                    cmd.relay_number, cmd.state ? "ON" : "OFF");
                    } else {
                        Serial.println("❌ Failed to queue command");
                    }
                } else {
                    Serial.println("❌ Invalid command format");
                }
            }
        }
    }
};

// FreeRTOS Task: Handle relay control
void relayControlTask(void *parameter) {
    RelayCommand cmd;
    
    while (true) {
        // Wait for relay commands from the queue
        if (xQueueReceive(relayQueue, &cmd, portMAX_DELAY) == pdTRUE) {
            int relayIndex = cmd.relay_number - 1;  // Convert to 0-based index
            
            // Update relay state
            relayStates[relayIndex] = cmd.state;
            digitalWrite(relayPins[relayIndex], cmd.state);
            
            Serial.printf("🔌 Relay %d: %s (GPIO %d)\n", 
                         cmd.relay_number, 
                         cmd.state ? "ON" : "OFF", 
                         relayPins[relayIndex]);
            
            // Optional: Feedback beep
            // if (cmd.state) {
            //     tone(BUZZER_PIN, 800, 50);  // High beep for ON
            // } else {
            //     tone(BUZZER_PIN, 400, 50);  // Low beep for OFF
            // }
            
            // Send confirmation back to app (optional)
            if (deviceConnected && pCharacteristic) {
                String response = "ACK_R" + String(cmd.relay_number) + String(cmd.state);
                pCharacteristic->setValue(response.c_str());
                pCharacteristic->notify();
            }
        }
    }
}

// FreeRTOS Task: Status LED management
void statusLedTask(void *parameter) {
    bool ledState = false;
    
    while (true) {
        if (deviceConnected) {
            // Solid ON when connected
            digitalWrite(LED_PIN, HIGH);
            vTaskDelay(pdMS_TO_TICKS(1000));
        } else {
            // Slow blink when disconnected
            ledState = !ledState;
            digitalWrite(LED_PIN, ledState);
            vTaskDelay(pdMS_TO_TICKS(500));
        }
    }
}

// FreeRTOS Task: Heartbeat and system monitoring
void heartbeatTask(void *parameter) {
    unsigned long lastHeartbeat = 0;
    int activeRelays = 0;
    
    while (true) {
        // Print system status every 10 seconds
        if (millis() - lastHeartbeat > 10000) {
            lastHeartbeat = millis();
            
            // Count active relays
            activeRelays = 0;
            for (int i = 0; i < 4; i++) {
                if (relayStates[i]) activeRelays++;
            }
            
            Serial.println("═══════════════════════════════════");
            Serial.printf("💓 System Status - Uptime: %.2f minutes\n", millis() / 60000.0);
            Serial.printf("🔗 BLE Status: %s\n", deviceConnected ? "Connected" : "Disconnected");
            Serial.printf("⚡ Active Relays: %d/4\n", activeRelays);
            Serial.printf("🧠 Free Heap: %d bytes\n", ESP.getFreeHeap());
            Serial.printf("📊 Stack High Water Mark: %d bytes\n", 
                         uxTaskGetStackHighWaterMark(NULL));
            
            // Print individual relay states
            for (int i = 0; i < 4; i++) {
                Serial.printf("   Relay %d (GPIO %d): %s\n", 
                             i + 1, relayPins[i], relayStates[i] ? "ON" : "OFF");
            }
            Serial.println("═══════════════════════════════════");
        }
        
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("🚀 ESP32 BLE Relay Controller Starting...");
    
    // Initialize GPIO pins
    Serial.println("📌 Initializing GPIO pins...");
    
    // Configure relay pins as outputs
    for (int i = 0; i < 4; i++) {
        pinMode(relayPins[i], OUTPUT);
        digitalWrite(relayPins[i], LOW);  // Start with all relays OFF
        Serial.printf("   Relay %d: GPIO %d\n", i + 1, relayPins[i]);
    }
    
    // Configure status LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    Serial.printf("   Status LED: GPIO %d\n", LED_PIN);
    
    // Configure buzzer (optional)
    // pinMode(BUZZER_PIN, OUTPUT);
    // Serial.printf("   Buzzer: GPIO %d\n", BUZZER_PIN);
    
    // Startup sequence with LED and buzzer
    Serial.println("🎵 Startup sequence...");
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_PIN, HIGH);
        // tone(BUZZER_PIN, 1000 + (i * 200), 100);
        delay(150);
        digitalWrite(LED_PIN, LOW);
        delay(100);
    }
    
    // Create FreeRTOS queue
    Serial.println("📦 Creating FreeRTOS queue...");
    relayQueue = xQueueCreate(QUEUE_SIZE, sizeof(RelayCommand));
    if (relayQueue == NULL) {
        Serial.println("❌ Failed to create relay queue!");
        return;
    }
    
    // Initialize BLE
    Serial.println("📡 Initializing BLE...");
    BLEDevice::init(DEVICE_NAME);
    
    // Create BLE Server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    
    // Create BLE Service
    BLEService *pService = pServer->createService(SERVICE_UUID);
    
    // Create BLE Characteristic
    pCharacteristic = pService->createCharacteristic(
                        CHARACTERISTIC_UUID,
                        BLECharacteristic::PROPERTY_READ |
                        BLECharacteristic::PROPERTY_WRITE |
                        BLECharacteristic::PROPERTY_NOTIFY
                      );
    
    pCharacteristic->setCallbacks(new MyCallbacks());
    pCharacteristic->addDescriptor(new BLE2902());
    
    // Start the service
    pService->start();
    
    // Start advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(false);
    pAdvertising->setMinPreferred(0x0);
    BLEDevice::startAdvertising();
    
    Serial.println("✅ BLE Service started!");
    Serial.printf("📱 Device Name: %s\n", DEVICE_NAME);
    Serial.printf("🆔 Service UUID: %s\n", SERVICE_UUID);
    Serial.println("🔍 Waiting for client connection...");
    
    // Create FreeRTOS tasks
    Serial.println("⚙️ Creating FreeRTOS tasks...");
    
    // Relay control task (highest priority)
    xTaskCreate(
        relayControlTask,
        "RelayControl",
        STACK_SIZE,
        NULL,
        3,  // High priority
        &relayTaskHandle
    );
    
    // Status LED task (medium priority)
    xTaskCreate(
        statusLedTask,
        "StatusLED",
        STACK_SIZE / 2,
        NULL,
        2,  // Medium priority
        &statusTaskHandle
    );
    
    // Heartbeat task (low priority)
    xTaskCreate(
        heartbeatTask,
        "Heartbeat",
        STACK_SIZE,
        NULL,
        1,  // Low priority
        &heartbeatTaskHandle
    );
    
    Serial.println("🎯 All tasks created successfully!");
    Serial.println("🔄 System ready - entering main loop...");
    
    // Success indication
    // tone(BUZZER_PIN, 1500, 200);
    // delay(250);
    // tone(BUZZER_PIN, 2000, 200);
}

void loop() {
    // Handle BLE connection state changes
    if (!deviceConnected && oldDeviceConnected) {
        delay(500); // Give the bluetooth stack time to get ready
        pServer->startAdvertising(); // Restart advertising
        Serial.println("🔍 Restarting BLE advertising...");
        oldDeviceConnected = deviceConnected;
    }
    
    // Connecting
    if (deviceConnected && !oldDeviceConnected) {
        oldDeviceConnected = deviceConnected;
    }
    
    // Small delay to prevent watchdog reset
    delay(100);
}

// Utility function to handle system reset (optional)
void systemReset() {
    Serial.println("🔄 System Reset Requested...");
    
    // Turn off all relays
    for (int i = 0; i < 4; i++) {
        digitalWrite(relayPins[i], LOW);
    }
    
    // Clean shutdown tone
    // tone(BUZZER_PIN, 500, 500);
    // delay(1000);
    
    ESP.restart();
}

// Emergency stop function (can be called from serial or button)
void emergencyStop() {
    Serial.println("🚨 EMERGENCY STOP ACTIVATED!");
    
    // Turn off all relays immediately
    for (int i = 0; i < 4; i++) {
        digitalWrite(relayPins[i], LOW);
        relayStates[i] = false;
    }
    
    // Emergency tone sequence
    // for (int i = 0; i < 5; i++) {
    //     tone(BUZZER_PIN, 1000, 100);
    //     delay(150);
    // }
    
    Serial.println("🔒 All relays disabled for safety");
}