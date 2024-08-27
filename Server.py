import asyncio
import serial
import websockets
import json
import re

serial_connection = None
running = False  # Flag to control whether we are reading from the serial port

async def handle_client(websocket, path):
    global serial_connection, running
    while True:
        message = await websocket.recv()
        data = json.loads(message)
        command = data.get('command')
        
        if command == 'configure':
            port = data.get('port')
            baud_rate = data.get('baud_rate')
            if serial_connection:
                serial_connection.close()
            serial_connection = serial.Serial(port, baud_rate, timeout=1)
        
        elif command == 'start':
            if not running:
                running = True
                try:
                    while running:
                        if serial_connection:
                            line = serial_connection.readline().decode('utf-8').strip()
                            if line:
                                # Check for ANSI color codes
                                if re.match(r'\x1b\[\d+m', line):
                                    log_type = 'esp'
                                    line = line.encode('ascii', errors='replace').decode('ascii')
                                else:
                                    log_type = 'debug'

                                await websocket.send(json.dumps({'type': log_type, 'data': line}))
                        await asyncio.sleep(0.1)  # Adjust the delay as needed
                except asyncio.CancelledError:
                    # Handle the cancellation of the task
                    pass
        
        elif command == 'stop':
            running = False
            if serial_connection:
                serial_connection.close()

async def main():
    server = await websockets.serve(handle_client, "localhost", 8765)
    try:
        await asyncio.Future()  # Run forever
    finally:
        server.close()
        await server.wait_closed()

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped")
finally:
    if serial_connection:
        serial_connection.close()
