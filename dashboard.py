import streamlit as st
import socket
import json
import time
import threading
import plotly.graph_objects as go
from collections import deque
import numpy as np
from PIL import Image
import io
import struct
import keyboard 
import pandas as pd

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
LISTEN_PORT = 5005   # Telemetry
SEND_PORT = 5006     # Commands
VIDEO_PORT = 5007    # Video Stream

# --- SHARED STATE ---
class NeuroBrain:
    def __init__(self):
        self.latest_packet = {"speed": 0.0, "vibration": 0.0, "status": "OFFLINE"}
        self.latest_frame = None 
        
        # HISTORY BUFFERS
        self.path_x = deque(maxlen=50)
        self.path_z = deque(maxlen=50)
        self.data_log = deque(maxlen=100) 
        
        self.alert_status = "System Normal"
        self.healing_active = False
        self.current_throttle = 0.0
        self.current_steer = 0.0
        
        # FIX: Track if initialized to prevent (0,0) jump
        self.is_initialized = False

        # SOCKETS
        try:
            self.sock_listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock_listen.bind((UDP_IP, LISTEN_PORT))
            self.sock_listen.setblocking(False)
            
            self.sock_send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.sock_video = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock_video.bind((UDP_IP, VIDEO_PORT))
            self.sock_video.listen(1)
            self.conn_video = None
        except: pass

    def send_command(self, type, val1, val2=0.0):
        try:
            cmd = json.dumps({"type": type, "value1": val1, "value2": val2})
            self.sock_send.sendto(cmd.encode(), (UDP_IP, SEND_PORT))
        except: pass

    def process_telemetry(self):
        try:
            latest = None
            while True:
                try:
                    data, _ = self.sock_listen.recvfrom(1024)
                    latest = data
                except BlockingIOError: break
            
            if latest:
                packet = json.loads(latest.decode())
                self.latest_packet = packet
                
                px = packet.get('position_x', 0)
                pz = packet.get('position_z', 0)

                # --- FIX: SMART GPS INITIALIZATION ---
                # Only start tracking path if we have non-zero coordinates
                # or if we have already started tracking.
                if not self.is_initialized:
                    if abs(px) > 0.1 or abs(pz) > 0.1:
                        self.is_initialized = True
                        # Clear any dummy 0,0 points
                        self.path_x.clear()
                        self.path_z.clear()
                        self.path_x.append(px)
                        self.path_z.append(pz)
                else:
                    self.path_x.append(px)
                    self.path_z.append(pz)
                
                # Update Graph History
                self.data_log.append({
                    "time": time.time(),
                    "speed": packet['speed'],
                    "vib": packet['vibration'] * 1000 
                })
                
                status = packet.get('status', 'OK')
                if packet['speed'] < 1.0 and packet['vibration'] > 0.02 and status != "HEALED (VIRTUAL_SENSOR)":
                    self.alert_status = "CRITICAL: SIGNAL LOSS"
                    if not self.healing_active:
                        self.send_command("HEAL", 1.0)
                        self.healing_active = True
                elif status == "HEALED (VIRTUAL_SENSOR)":
                    self.alert_status = "RECOVERED (VIRTUAL)"
                    self.healing_active = True
                else:
                    self.alert_status = "System Normal"
        except: pass

    def process_video(self):
        try:
            if self.conn_video is None:
                self.sock_video.setblocking(False)
                try:
                    conn, addr = self.sock_video.accept()
                    self.conn_video = conn
                    self.conn_video.setblocking(True) 
                except BlockingIOError: return 

            if self.conn_video:
                size_data = self.conn_video.recv(4)
                if not size_data: self.conn_video = None; return
                size = struct.unpack('<L', size_data)[0] 
                data = b""
                while len(data) < size:
                    packet = self.conn_video.recv(size - len(data))
                    if not packet: return
                    data += packet
                image = Image.open(io.BytesIO(data))
                self.latest_frame = image
        except: self.conn_video = None

    def process_controls(self):
        target_t = 0.0
        target_s = 0.0
        if keyboard.is_pressed('w'): target_t = 1.0
        elif keyboard.is_pressed('s'): target_t = -1.0
        if keyboard.is_pressed('a'): target_s = -1.0
        elif keyboard.is_pressed('d'): target_s = 1.0
        self.current_throttle = target_t 
        self.current_steer = target_s
        self.send_command("DRIVE", self.current_throttle, self.current_steer)

# --- THREAD-SAFE INITIALIZATION ---
if 'brain' not in st.session_state:
    st.session_state['brain'] = NeuroBrain()
    
    def run_telemetry(brain_instance):
        while True: brain_instance.process_telemetry(); time.sleep(0.01)
        
    def run_video(brain_instance):
        while True: brain_instance.process_video(); time.sleep(0.01)
        
    def run_controls(brain_instance):
        while True: brain_instance.process_controls(); time.sleep(0.03)

    brain_ref = st.session_state['brain']
    threading.Thread(target=run_telemetry, args=(brain_ref,), daemon=True).start()
    threading.Thread(target=run_video, args=(brain_ref,), daemon=True).start()
    threading.Thread(target=run_controls, args=(brain_ref,), daemon=True).start()

brain = st.session_state['brain']
packet = brain.latest_packet

# --- DASHBOARD UI ---
st.set_page_config(page_title="NeuroDrive Commander", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem; padding-left: 2rem; padding-right: 2rem;}
    h3 {margin-top: 0; padding-top: 0;}
    div[data-testid="stVerticalBlock"] { gap: 0.5rem; }
</style>
""", unsafe_allow_html=True) 

st.title("🛡️ NeuroDrive: Mission Control")

col_video, col_data = st.columns([1.5, 2.5]) 

# --- LEFT: VIDEO ---
with col_video:
    st.markdown("##### 🎥 Live Feed")
    if brain.latest_frame:
        st.image(brain.latest_frame, width="stretch")
    else:
        st.info("Waiting for Video...")

# --- RIGHT: DATA CLUSTER ---
with col_data:
    c_map, c_stat = st.columns([1, 1])
    
    with c_map:
        st.markdown("##### 📍 GPS Tracking")
        fig_map = go.Figure()
        fig_map.add_trace(go.Scatter(x=list(brain.path_x), y=list(brain.path_z), mode='lines', line=dict(color='cyan', width=2)))
        fig_map.add_trace(go.Scatter(x=[packet.get('position_x', 0)], y=[packet.get('position_z', 0)], mode='markers', marker=dict(color='yellow', size=12)))
        
        # FIX: Better defaults for layout to reduce jitter
        fig_map.update_layout(height=180, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark", 
                              xaxis=dict(autorange=True, showgrid=False, visible=False), 
                              yaxis=dict(autorange=True, showgrid=False, visible=False, scaleanchor="x", scaleratio=1),
                              showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_map, width="stretch")

    with c_stat:
        st.markdown("##### 🚦 Status")
        status = brain.alert_status
        if "CRITICAL" in status: st.error(f"⚠️ {status}")
        elif "RECOVERED" in status: st.warning(f"🛡️ {status}")
        else: st.success(f"✅ {status}")
        
        m1, m2 = st.columns(2)
        m1.metric("Speed", f"{packet['speed']:.0f} km/h")
        m2.metric("Vib", f"{packet['vibration']:.3f} G")
        
        if st.button("🔥 INJECT SIGNAL LOSS", type="primary", use_container_width=True):
            brain.send_command("FAULT", 1.0); brain.healing_active = False
        if st.button("♻️ RESET SYSTEM", use_container_width=True):
            brain.send_command("FAULT", 0.0); brain.healing_active = False

    st.divider()

    st.markdown("##### 📉 Physics Verification (Real-Time)")
    df = pd.DataFrame(list(brain.data_log))
    if not df.empty:
        fig_graph = go.Figure()
        fig_graph.add_trace(go.Scatter(y=df['speed'], name='Sensor Speed', line=dict(color='cyan', width=2)))
        fig_graph.add_trace(go.Scatter(y=df['vib'], name='Physics Vib (x1000)', line=dict(color='orange', width=2), fill='tozeroy', fillcolor='rgba(255,165,0,0.1)'))
        fig_graph.update_layout(height=200, margin=dict(l=0,r=0,t=0,b=0), template="plotly_dark", 
                                xaxis=dict(showgrid=False, visible=False), 
                                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_graph, width="stretch")

time.sleep(0.1)
st.rerun()