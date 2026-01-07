# NeuroDrive: A Fail-Operational Digital Twin for Autonomous Vehicle Safety

## 1. Executive Summary
Modern Electric Vehicles (EVs) rely on over 100 sensors to operate. A single failure in a critical sensor (like a speed encoder) typically triggers a "Fail-Safe" mode, disabling advanced features or stopping the vehicle. NeuroDrive introduces a paradigm shift to a "Fail-Operational" architecture.

By creating a real-time Digital Twin, NeuroDrive utilizes **Neuro-Symbolic AI** to detect complex sensor anomalies (Signal Loss, Drift, Noise, Freeze) that traditional threshold-based systems miss. Upon detection, it instantly switches to a **Virtual Sensor Fusion** mode, allowing the vehicle to "heal" itself and continue operating safely without expensive hardware redundancy.

## 2. Problem Statement (The Why)
### The Trust Gap
Deep Learning models are "black boxes" and cannot be fully trusted for safety-critical decisions (ISO 26262 compliance issues).

### Hardware Reliance
Current industry standard for safety is adding redundant physical sensors, increasing weight and cost.

### Subtle Failures
Standard error checking catches dead sensors (0 values) but fails to detect "lying sensors" (drift, calibration loss, or frozen signals).

## 3. System Architecture (The How)
The system is built on a high-frequency Closed-Loop Architecture running at 60Hz.

### Physical/Simulation Layer (Unity Engine)
*   Acts as the "Real Vehicle."
*   Simulates rigorous physics: wheel friction, chassis vibration, engine RPM, and momentum.
*   Generates raw sensor telemetry (Speed, Vibration, GPS).
*   **Fault Injector**: Capable of injecting 4 distinct hardware failures in real-time.

### Transport Layer (UDP/TCP)
*   Low-latency telemetry stream (<10ms) over Localhost/Wi-Fi.
*   **UDP**: For high-speed physics data (Speed, Vib).
*   **TCP**: For live video feed transmission.

### Edge AI Layer (Python Backend)
*   **Logical Engine**: Checks for "Physics Paradoxes" (e.g., High Vibration + Zero Speed).
*   **ML Engine**: Uses an Isolation Forest model to detect statistical anomalies in noisy data.
*   **Virtual Sensor**: An estimator that calculates "True Speed" based on motor voltage and chassis vibration when the primary sensor fails.

### Mission Control Layer (Streamlit Dashboard)
*   A real-time "Glass Cockpit" for visualization.
*   Displays live video, GPS tracking, and the "Truth Graph" (Physics vs. Sensor data).
*   Allows manual remote control (WASD) and fault injection.

## 4. Detailed Implementation Strategy

### Module A: The Physics Twin (Unity & C#)
We developed a custom physics script (`NeuroDriveECU.cs`) attached to a 3D vehicle. It does not just play an animation; it calculates real forces.
*   **Vibration Synthesis**: We generate vibration data correlated to wheel speed. *fast speed = high frequency vibration*. This provides the "Ground Truth" for our AI.
*   **Fault Injection Logic**:
    *   **Signal Loss**: Forces output to 0.
    *   **Drift**: Adds a cumulative bias (`speed += 0.05 * time`).
    *   **Noise**: Adds random variance (`speed += random(-15, 15)`).
    *   **Freeze**: Locks the output variable to the last known value.

### Module B: The Neuro-Symbolic Brain (Python)
The core innovation is the hybrid detection logic:

**Symbolic Check (Rule-Based):**
*   **Rule**: `IF Speed == 0 AND Vibration > Threshold THEN Fault = True`
*   **Why**: A moving car physically must vibrate. If vibration exists but speed is zero, the sensor is lying.

**Neural Check (Model-Based):**
*   **Model**: Isolation Forest (Unsupervised Learning).
*   **Why**: Detects "Drift" and "Noise" by learning the normal correlation between Throttle, Vibration, and Speed. If the correlation breaks (divergence), it flags an anomaly.

### Module C: Self-Healing Mechanism
Upon detecting a fault, the system does not shut down. It triggers the Self-Healing Loop:
1.  **Isolate**: The faulty sensor data is discarded.
2.  **Estimate**: The Virtual Sensor activates, calculating:
    $$Speed_{virtual} = (Throttle \times MotorConstant) \times VibrationFactor$$
3.  **Inject**: This estimated value is fed back into the vehicle controller, allowing features like Cruise Control to remain active.

---

## 5. Technical Component Analysis: Mission Control (`dashboard.py`)

### Overview
`dashboard.py` serves as the frontend control interface for the "NeuroDrive" system. It is a **Streamlit** application designed as a "Mission Control" specifically for monitoring and controlling a remote system (likely a vehicle or simulation). It features real-time telemetry, video streaming, and remote control capabilities.

### Technical Stack
*   **Framework**: `streamlit` (Web UI)
*   **Networking**: `socket` (UDP for telemetry/commands, TCP for video)
*   **Visualization**: `plotly.graph_objects` (Real-time charts/maps)
*   **Data Handling**: `pandas`, `json`, `collections.deque` (Rolling buffers)
*   **Image Processing**: `PIL.Image`, `io`, `struct`
*   **Input**: `keyboard` (Capture local keystrokes for remote control)
*   **Concurrency**: `threading` (Background data ingestion)

### Architecture & Components

#### The `NeuroBrain` Class (State Management)
The core logic engine is the `NeuroBrain` class, which is instantiated once and persisted in `st.session_state`.
*   **State Variables**: Stores the latest telemetry packet, video frame, and circular buffers (`deque`) for preserving history (GPS path, speed/vibration logs).
*   **Initialization Logic**: Contains specific logic (`is_initialized`) to prevent GPS mapping artifacts (jumping from 0,0) by waiting for valid coordinates before logging path data.

#### Networking (Comms Layer)
The system uses three distinct ports for communication:

| Port | Protocol | Direction | Purpose |
| :--- | :--- | :--- | :--- |
| **5005** | UDP | Inbound | Receives Telemetry JSON packets (Position, Speed, Vib) |
| **5006** | UDP | Outbound | Sends Commands (DRIVE, HEAL, FAULT) |
| **5007** | TCP | Inbound | Receives Video Stream frames |

#### Threading Model
To prevent UI freezing, the script launches **three daemon threads**:
1.  `run_telemetry`: Continuously polls UDP port 5005.
2.  `run_video`: Manages the TCP connection and decodes incoming image frames.
3.  `run_controls`: Polls keyboard state (WASD) and sends drive commands.

### User Interface (UI) Breakdown
The UI uses a "Wide" layout divided into two main columns:

#### Left Column (Video)
*   Displays the latest received video frame.
*   Shows a "Waiting for Video..." placeholder if the stream is offline.

#### Right Column (Data Cluster)
*   **GPS Tracking**: A Plotly Scatter Map showing the historical path (Cyan line) and current position (Yellow marker). Configured with a minimal "HUD" aesthetic (no grids/axes).
*   **Status Panel**:
    *   **Dynamic Badges**: Green (Normal), Red (Critical), Orange (Recovered/Virtual).
    *   **Metrics**: Large displays for Speed (km/h) and Vibration (G).
    *   **Manual Overrides**: Buttons to "INJECT SIGNAL LOSS" (Simulate failure) and "RESET SYSTEM".
*   **Physics Verification**:
    *   A bottom line chart correlating "Sensor Speed" vs "Physics Vibration" over time to visually verify data consistency.

---

## 6. Results & Validation (The Novelty)
We successfully demonstrated the "Physics Paradox" using the Mission Control Dashboard.

### Test Case 1: Signal Loss
*   **Action**: Injected fault at 50 km/h.
*   **Observation**: Sensor reading dropped to 0.
*   **Reaction**: Within 35ms, the system detected the vibration mismatch and restored the speed reading to 50 km/h (Virtual).
*   **Visual Proof**: The "V-Shape Dip" on the telemetry graph confirms the real-time detection and recovery.

### Test Case 2: Sensor Drift
*   **Action**: Induced a +0.5 km/h bias per frame.
*   **Observation**: Sensor reported 80 km/h while actual speed was 50 km/h.
*   **Reaction**: AI detected divergence from the Vibration profile and flagged "Calibration Failure," switching to the estimated value.

## 7. Technologies Used
*   **Simulation**: Unity 2022 LTS (C#)
*   **Backend**: Python 3.10, Socket Programming (UDP/TCP)
*   **Dashboard**: Streamlit, Plotly (Real-time graphing)
*   **Communication**: JSON over UDP
*   **Control**: keyboard library for global WASD input

## 8. Conclusion
NeuroDrive proves that **Software Redundancy can replace Hardware Redundancy**. By analyzing the physical correlation between different vehicle states (Speed vs. Vibration), we created a system that is not just "Smart" but "Resilient." This architecture paves the way for Level 5 Autonomous Vehicles that can suffer hardware failures without disengaging the driver.