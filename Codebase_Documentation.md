# NeuroDrive Project Codebase Documentation

This document provides a technical breakdown of the key Python files in the NeuroDrive workspace. These scripts form the "Edge AI" and "Mission Control" layers of the system.

## 1. `neuro_brain.py` (The Backend Logic)
**Role:** The core "Brain" of the autonomous safety system.
**Function:** Run this script to start the autonomous monitoring and self-healing engine without the graphical interface.

### Key Responsibilities:
*   **Neural Engine (Machine Learning)**:
    *   Uses `sklearn.ensemble.IsolationForest` to detect subtle statistical anomalies described as "Physics Paradoxes" (e.g., drift, noise).
    *   Includes a **Training Phase**: When started, it records ~10 seconds of "normal driving" data to calibrate the ML model.
*   **Symbolic Engine (Rule-Based)**:
    *   Implements hard-coded safety rules (e.g., `IF Speed < 1.0 AND Vibration > 0.02 THEN FAULT`).
    *   Acts as a deterministic safety net for obvious sensor failures.
*   **Loop Architecture**:
    *   Continuously polls UDP Port **5005** for telemetry.
    *   Evaluates data against both Neural and Symbolic logic.
    *   Triggers **Self-Healing** by sending commands to Unity via UDP Port **5006** if either engine detects a fault.

---

## 2. `dashboard.py` (The Mission Control UI)
**Role:** The frontend Human-Machine Interface (HMI).
**Function:** Run this with `streamlit run dashboard.py` to launch the web-based control panel.

### Key Responsibilities:
*   **Real-Time Visualization**:
    *   **Video Feed**: Receives and decodes TCP video frames on Port **5007**.
    *   **GPS Map**: Uses Plotly to draw the vehicle's path live on a 2D plane.
    *   **Telemetry Graphs**: Visualizes the correlation between Speed and Vibration to prove the "Physics Paradox" concept to human observers.
*   **Remote Control**:
    *   Captures `WASD` keyboard inputs and transmits them as steering/throttle commands to Unity.
*   **Threading**:
    *   Manages 3 separate background threads (Video, Telemetry, Controls) to keep the UI responsive while handling high-frequency network I/O.
*   **Hybrid Operation**: *Note: This file contains a simplified version of the logic found in `neuro_brain.py` so it can operate independently for demonstrations.*

---

## 3. `listener.py` (Diagnostic Tool)
**Role:** A lightweight debugging utility.
**Function:** Run this to verify network connectivity and inspect raw data packets.

### Key Responsibilities:
*   **Packet Inspection**:
    *   Listens on UDP Port **5005**.
    *   Decodes the JSON packets coming from the Unity simulation.
*   **Verification**:
    *   Prints a clean, formatted line for every packet received (Timestamp, Speed, Vibration, Status).
    *   Useful for checking if the Simulation is actually sending data before launching the complex logic scripts.

---

## 4. `rep.py` (Backup/Duplicate)
**Role:** Redundant file.
**Function:** This appears to be a copy or previous iteration of `dashboard.py`. It contains similar Streamlit initialization code and is likely a workspace artifact. It is recommended to use `dashboard.py` as the primary interface.
