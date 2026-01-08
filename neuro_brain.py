import socket
import json
import numpy as np
import time
from sklearn.ensemble import IsolationForest

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
LISTEN_PORT = 5005   # From Unity
SEND_PORT = 5006     # To Unity (Command Channel)

# --- NEURAL LAYER ---
class NeuralEngine:
    def __init__(self):
        self.model = IsolationForest(contamination=0.01) # Very conservative
        self.is_trained = False
        self.scaler_max_speed = 1.0 
        self.scaler_max_vib = 1.0
        self.anomaly_counter = 0 # To filter out transient noise


    def train(self, data_points):
        print("🧠 Neural Layer: Processing calibration data...")
        X = np.array(data_points)
        max_s = np.max(X[:, 0]) if np.max(X[:, 0]) > 0 else 1.0
        max_v = np.max(X[:, 1]) if np.max(X[:, 1]) > 0 else 1.0
        self.scaler_max_speed = max_s
        self.scaler_max_vib = max_v
        
        X_normalized = np.column_stack((X[:, 0]/max_s, X[:, 1]/max_v))
        try:
            self.model.fit(X_normalized)
            self.is_trained = True
            print("✅ Neural Layer: Active.")
        except: pass

    def detect_anomaly(self, speed, vibration):
        if not self.is_trained: return False
        
        # LOGIC GATE: If we are just stopped or moving slowly, IT IS NOT AN ANOMALY.
        if speed < 5.0 and vibration < 0.1: # Increased vib tolerance for low speeds
            self.anomaly_counter = 0
            return False

        try:
            is_anomaly = self.model.predict([[speed/self.scaler_max_speed, vibration/self.scaler_max_vib]])[0] == -1
            if is_anomaly:
                self.anomaly_counter += 1
            else:
                self.anomaly_counter = max(0, self.anomaly_counter - 1)
            
            # TRIGGER ONLY IF SUSTAINED (e.g. 10 frames = ~0.2s)
            return self.anomaly_counter > 10
        except: return False 

# --- SYMBOLIC LAYER (SAFETY RULES) ---
class SymbolicEngine:
    def __init__(self):
        self.fault_counter = 0
        self.last_valid_speed = 0.0

    def check_safety_rules(self, speed, vibration):
        # RULE 1: Physics Paradox (Stopped but vibrating)
        # Reduced threshold slightly (0.05) to catch highway cruising failures
        paradox = (speed < 1.0 and vibration > 0.05)
        
        # RULE 2: Impossible Deceleration (Instant Stop)
        # If speed drops from >20km/h to 0 instantly, it's a sensor failure.
        impossible_stop = False
        if self.last_valid_speed > 20.0 and speed < 1.0:
            impossible_stop = True
            
        # Update/Reset State
        if speed > 1.0:
            self.last_valid_speed = speed
            self.fault_counter = 0
        elif paradox or impossible_stop:
            self.fault_counter += 1
        else:
             # Just a normal stop
            self.fault_counter = 0

        if self.fault_counter > 3: # Fast reaction (approx 0.05s)
            return "CRITICAL: Wheel Speed Sensor Failure (Signal Loss)"
        return None 

# --- MAIN LOOP ---
def start_neurodrive():
    # Setup Listening Socket (Data IN)
    sock_listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_listen.bind((UDP_IP, LISTEN_PORT))
    sock_listen.setblocking(False) 

    # Setup Sending Socket (Commands OUT)
    sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    brain = NeuralEngine()
    logic = SymbolicEngine()
    
    healing_triggered = False # Prevent spamming the command
    
    print(f"--- NEURODRIVE V2.0 (Self-Healing) INITIALIZED ---")
    
    # Phase 1: Calibration
    training_data = []
    print("🚗 ACTION REQUIRED: Drive normally for 10 seconds.")
    start_time = time.time()
    
    while time.time() - start_time < 10:
        try:
            latest_data = None
            while True:
                try:
                    data, _ = sock_listen.recvfrom(1024)
                    latest_data = data
                except BlockingIOError: break
            
            if latest_data:
                packet = json.loads(latest_data.decode())
                # Use keys consistent with dashboard.py
                current_speed = packet.get('speed', packet.get('wheel_speed_fl', 0))
                current_vib = packet.get('vibration', packet.get('vibration_level', 0))
                
                if current_speed > 1.0:
                    training_data.append([current_speed, current_vib])
                print(f"Calibrating... {int(10 - (time.time() - start_time))}s", end='\r')
        except Exception as e:
            # print(f"Error in calibration: {e}") 
            pass
        time.sleep(0.01) 

    # Phase 2: Knowledge Injection (Teach it that "Stopping" is also normal)
    # Inject synthetic "safe" data points for low speed/low vibration
    training_data.extend([[0.0, 0.001], [1.0, 0.002], [5.0, 0.005], [0.0, 0.0]]) 

    if len(training_data) < 5: training_data.extend([[10, 0.02], [50, 0.05]])
    brain.train(training_data)

    print("\n--- 🛡️ REAL-TIME MONITORING & HEALING ACTIVE ---")
    
    while True:
        try:
            # Low Latency Read
            latest_packet = None
            while True:
                try:
                    data, _ = sock_listen.recvfrom(1024)
                    latest_packet = data
                except BlockingIOError: break
            
            if latest_packet is None:
                time.sleep(0.001)
                continue

            packet = json.loads(latest_packet.decode())
            speed = packet.get('speed', packet.get('wheel_speed_fl', 0))
            vib = packet.get('vibration', packet.get('vibration_level', 0))
            status = packet.get('status', 'UNKNOWN')
            
            # 1. Check for Rules
            rule_fault = logic.check_safety_rules(speed, vib)
            
            # 2. Check for Neural Anomalies (Drift/Noise)
            neural_fault = brain.detect_anomaly(speed, vib)
            
            # 3. DECISION & SELF-HEALING LOGIC (Neuro-Symbolic)
            if (rule_fault or neural_fault) and not healing_triggered:
                reason = rule_fault if rule_fault else "CRITICAL: Neural Anomaly Detected (Drift/Noise)"
                print(f"⚠️  SAFETY ALERT! [{reason}]" + " "*10)
                print(f"    Telemetry: Speed={speed:.1f} | Vib={vib:.3f}")
                print(f"    ⚡ ACTION: Initiating Virtual Sensor Fusion...")
                
                # SEND COMMAND TO UNITY
                try:
                    cmd = json.dumps({"type": "HEAL", "value1": 1.0, "value2": 0.0})
                    sock_send.sendto(cmd.encode(), (UDP_IP, SEND_PORT))
                except:
                    # Fallback for older systems
                    sock_send.sendto(b"ACTIVATE_HEALING", (UDP_IP, SEND_PORT))
                
                healing_triggered = True # Mark as handled
                
            elif status == "HEALED (VIRTUAL_SENSOR)":
                # System detected the fix was successful
                print(f"✅ SYSTEM RECOVERED | Virtual Speed: {speed:.1f} km/h (Sensor Bypassed)   ", end='\r')
                
            elif not rule_fault and not neural_fault:
                print(f"✅ System Normal | Speed: {speed:.1f} | Vib: {vib:.3f}   ", end='\r')
                
                # RECOVERY LOGIC: If we were healing, but now data is robustly healthy again
                if healing_triggered and speed > 5.0:
                     print(f"\n✨ FAULT CLEARED: Sensor Signal Restored.")
                     print(f"    ⚡ ACTION: Deactivating Virtual Sensor...")
                     
                     # SEND RESET COMMAND TO UNITY
                     try:
                        # Use FAULT type with 0.0 to clear all faults (Signal Loss + Virtual Sensor)
                        cmd = json.dumps({"type": "FAULT", "value1": 0.0, "value2": 0.0})
                        sock_send.sendto(cmd.encode(), (UDP_IP, SEND_PORT))
                     except: pass
                     
                     healing_triggered = False # Reset flag
                
        except KeyboardInterrupt: break
        except Exception: pass

if __name__ == "__main__":
    start_neurodrive()