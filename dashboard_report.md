# Detailed Report: dashboard.py

## 1. Overview
`dashboard.py` serves as the frontend control interface for the "NeuroDrive" system. It is a **Streamlit** application designed as a "Mission Control" specifically for monitoring and controlling a remote system (likely a vehicle or simulation). It features real-time telemetry, video streaming, and remote control capabilities.

## 2. Technical Stack
*   **Framework**: `streamlit` (Web UI)
*   **Networking**: `socket` (UDP for telemetry/commands, TCP for video)
*   **Visualization**: `plotly.graph_objects` (Real-time charts/maps)
*   **Data Handling**: `pandas`, `json`, `collections.deque` (Rolling buffers)
*   **Image Processing**: `PIL.Image`, `io`, `struct`
*   **Input**: `keyboard` (Capture local keystrokes for remote control)
*   **Concurrency**: `threading` (Background data ingestion)

## 3. Architecture & Components

### A. The `NeuroBrain` Class (State Management)
The core logic engine is the `NeuroBrain` class, which is instantiated once and persisted in `st.session_state`.
*   **State Variables**: Stores the latest telemetry packet, video frame, and circular buffers (`deque`) for preserving history (GPS path, speed/vibration logs).
*   **Initialization Logic**: Contains specific logic (`is_initialized`) to prevent GPS mapping artifacts (jumping from 0,0) by waiting for valid coordinates before logging path data.

### B. Networking (Comms Layer)
The system uses three distinct ports for communication:

| Port | Protocol | Direction | Purpose |
| :--- | :--- | :--- | :--- |
| **5005** | UDP | Inbound | Receives Telemetry JSON packets (Position, Speed, Vib) |
| **5006** | UDP | Outbound | Sends Commands (DRIVE, HEAL, FAULT) |
| **5007** | TCP | Inbound | Receives Video Stream frames |

### C. Threading Model
To prevent UI freezing, the script launches **three daemon threads**:
1.  `run_telemetry`: Continuously polls UDP port 5005.
2.  `run_video`: Manages the TCP connection and decodes incoming image frames.
3.  `run_controls`: Polls keyboard state (WASD) and sends drive commands.

## 4. Key Logic & Features

### Self-Healing Mechanism
*   The `process_telemetry` function monitors `speed` and `vibration`.
*   **Trigger**: If speed drops below 1.0 AND vibration > 0.02, it flags "CRITICAL: SIGNAL LOSS".
*   **Action**: Automatically sends a `HEAL` command via UDP port 5006 to recover the remote system.

### Remote Control
*   Uses the `keyboard` library to detect W/A/S/D keys globally.
*   Converts key presses into throttle (1.0/-1.0) and steering (-1.0/1.0) values sent via UDP.

### Video Processing
*   Implements a custom frame protocol: 
    1.  Reads 4 bytes (Size header).
    2.  Reads N payload bytes based on header.
    3.  Decodes via `PIL.Image`.

## 5. User Interface (UI) Breakdown

The UI uses a "Wide" layout divided into two main columns:

### Left Column (Video)
*   Displays the latest received video frame.
*   Shows a "Waiting for Video..." placeholder if the stream is offline.

### Right Column (Data Cluster)
*   **GPS Tracking**: A Plotly Scatter Map showing the historical path (Cyan line) and current position (Yellow marker). Configured with a minimal "HUD" aesthetic (no grids/axes).
*   **Status Panel**:
    *   **Dynamic Badges**: Green (Normal), Red (Critical), Orange (Recovered/Virtual).
    *   **Metrics**: Large displays for Speed (km/h) and Vibration (G).
    *   **Manual Overrides**: Buttons to "INJECT SIGNAL LOSS" (Simulate failure) and "RESET SYSTEM".
*   **Physics Verification**:
    *   A bottom line chart correlating "Sensor Speed" vs "Physics Vibration" over time to visually verify data consistency.

## 6. Data Flow Summary
1.  **Input**: Network Data (JSON Telemetry, JPEG Images), User Keyboard (WASD), UI Buttons.
2.  **Processing**: Background threads update the `NeuroBrain` class attributes.
3.  **Output**: `st.rerun()` is called every **0.1 seconds** to refresh the UI with new state data.
