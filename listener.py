import socket
import json

UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("🎧 NeuroDrive Listener Active... Waiting for Unity Car...")

while True:
    data, addr = sock.recvfrom(1024)
    packet = json.loads(data.decode())
    
    # Debug: Print all keys if a specific one is missing, or just print the whole packet to see structure
    # print(f"Received Packet Keys: {list(packet.keys())}") 
    
    # Safe access or just dumping the raw packet for inspection
    print(f"RAW PACKET: {packet}")
    
    # print(f"Time: {packet['timestamp']:.2f} | Speed: {packet['wheel_speed_fl']:.1f} km/h | Vib: {packet['vibration_level']:.3f} | Status: {packet['status']}")