const ws = new WebSocket('ws://localhost:8765');
const debugTerminal = document.getElementById('debugTerminal');
const espTerminal = document.getElementById('espTerminal');
const autoScrollCheckbox = document.getElementById('autoScrollCheckbox');
const ShowTimeStaCheckbox = document.getElementById('ShowTimeStaCheckbox');
const startStopButton = document.getElementById('startStopButton');
let isMonitoring = false;
var shTmeSta = true;

function getColorClass(ansiCode) {
    if (ansiCode.includes('[0;32mI')) return 'info';    // Info (Green)
    if (ansiCode.includes('[0;33mW')) return 'warning'; // Warning (Yellow)
    if (ansiCode.includes('[0;31mE')) return 'error';   // Error (Red)
    if (ansiCode.includes('[0;33mD')) return 'debug';   // Debug (Cyan)
    if (ansiCode.includes('[0;31mV')) return 'verbose';  // Verbose (Grey)
    return '';  // Default, no special class
}

// Open the WebSocket connection
ws.onopen = () => {
    console.log('Connected to the WebSocket server');

    // Send a request to get available ports
    const request = JSON.stringify({ command: 'getAvlPort' });
    ws.send(request);
};

ws.onmessage = function (event) {
    try {
        const message = JSON.parse(event.data);

        if (message.type === 'available_ports') {
            if (message.type === 'available_ports') {
                const ports = message.data;
                console.log('Available ports:', ports);
                updatePortOptions(ports); // Update the select element with available ports
            }
        } else if (message.data) {
            // Ensure the data is a string
            const line = typeof message.data === 'string' ? message.data : message.data.toString().trim();

            // Determine if the line is log data or debug data
            if (line.includes('[0;32mI') || line.includes('[0;33mW') || line.includes('[0;31mE') || line.includes('[0;33mD') || line.includes('[0;31mV')) {
                // This is log data
                const colorClass = getColorClass(line);
                var newline = ansiToAscii(line);

                if(ShowTimeStaCheckbox.checked){
                    newline = genTimeStamp() + " -> " + newline;
                }
                
                const styledLine = `<div class="${colorClass}">${newline}</div>`;
                espTerminal.innerHTML += styledLine;

                // Auto-scroll the log terminal if enabled
                if (autoScrollCheckbox.checked) {
                    espTerminal.scrollTop = espTerminal.scrollHeight;
                }
            } else {
                // This is debug data
                var newline = line;
               
                if(ShowTimeStaCheckbox.checked){
                    newline = genTimeStamp() + " -> " + newline;
                }

                const styledDebugLine = `<div class="debug-line">${newline}</div>`;
                debugTerminal.innerHTML += styledDebugLine;

                // Auto-scroll the debug terminal if enabled
                if (autoScrollCheckbox.checked) {
                    debugTerminal.scrollTop = debugTerminal.scrollHeight;
                }
            }
        }
    } catch (error) {
        console.error('Error parsing message:', error);
    }
};

ws.onclose = function () {
    console.log('WebSocket connection closed');
    if (isMonitoring) {
        startStopButton.textContent = 'Start';
        isMonitoring = false;
    }
};

ws.onerror = function (error) {
    console.error('WebSocket error:', error);
};

function toggleMonitoring() {
    if (isMonitoring) {
        ws.send(JSON.stringify({ command: 'stop' }));
        startStopButton.textContent = 'Start';
    } else {
        const port = document.getElementById('port').value;
        const baudRate = document.getElementById('baudRate').value;
        ws.send(JSON.stringify({ command: 'configure', port, baud_rate: baudRate }));
        ws.send(JSON.stringify({ command: 'start' }));
        startStopButton.textContent = 'Stop';
    }
    isMonitoring = !isMonitoring;
}

function ansiToAscii(str) {
    return str.replace(/\x1B\[[0-9;]*m/g, ''); // Removes ANSI escape sequences
}




const portSelect = document.getElementById('port');
// Function to update port options
function updatePortOptions(ports) {
    portSelect.innerHTML = ''; // Clear existing options
    ports.forEach(port => {
        const option = document.createElement('option');
        option.value = port;
        option.textContent = port;
        portSelect.appendChild(option);
    });
}

// Notify the server when the page is closed
window.addEventListener("beforeunload", function (event) {
    ws.send("page_closed");
});

function genTimeStamp() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-GB', { hour12: false }) + '.' + now.getMilliseconds().toString().padStart(3, '0');
    return timeString;
}
