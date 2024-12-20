import asyncio
import serial
import serial.tools.list_ports
import websockets
import json
import re

serial_connection = None
running = False  # Flag to control whether we are reading from the serial port
clients = set()  # Track connected clients
stop_event = asyncio.Event()  # Event to signal when to stop the server

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

async def handle_client(websocket):
    global serial_connection, running

    # Add the new client to the set
    clients.add(websocket)

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
                
            elif data.get('type') == 'page_closed':
                print("Page closed signal received. Handling cleanup.")
                # Remove the client and check if it's the last client
                clients.remove(websocket)
                if not clients:
                    # Signal the main function to stop the server
                    stop_event.set()
                    return
    
    except websockets.ConnectionClosed:
        print("Connection closed")
    finally:
        if websocket in clients:
            clients.remove(websocket)

async def main():
    global stop_event
    server = await websockets.serve(handle_client, "localhost", 8765)
    print("WebSocket server started on ws://localhost:8765")

    try:
        # Wait until the stop event is set
        await stop_event.wait()
    finally:
        print("Stopping server...")
        server.close()
        await server.wait_closed()
        
        # Ensure all remaining tasks are finished
        await asyncio.sleep(0)  # Yield control to process pending tasks
        if serial_connection:
            serial_connection.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server interrupted and shutting down.")
    finally:
        if serial_connection:
            serial_connection.close()
