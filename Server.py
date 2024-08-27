import asyncio
import serial
import serial.tools.list_ports
import websockets
import json
import re

serial_connection = None
running = False  # Flag to control whether we are reading from the serial port

async def read_serial(websocket):
    global serial_connection, running
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

async def handle_client(websocket, path):
    global serial_connection, running

    # Task to read serial data
    read_serial_task = None

    try:
        async for message in websocket:
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
                    # Start serial reading in a separate task
                    if read_serial_task is None or read_serial_task.done():
                        read_serial_task = asyncio.create_task(read_serial(websocket))
            
            elif command == 'stop':
                running = False
                if serial_connection:
                    serial_connection.close()
                if read_serial_task:
                    read_serial_task.cancel()
                    try:
                        await read_serial_task
                    except asyncio.CancelledError:
                        pass
            
            elif command == 'getAvlPort':
                ports = serial.tools.list_ports.comports()
                available_ports = [port.device for port in ports]
                await websocket.send(json.dumps({'type': 'available_ports', 'data': available_ports}))
    
    except websockets.ConnectionClosed:
        print("Connection closed")

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
