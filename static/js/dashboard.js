// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadData();
});

async function loadData() {
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const table = document.getElementById('dataTable');
    const tableBody = document.getElementById('tableBody');
    
    // Show loading, hide error and table
    loading.style.display = 'block';
    error.style.display = 'none';
    table.style.display = 'none';
    
    try {
        const response = await fetch('/api/network/get_ip_and_location');
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch data');
        }
        
        // Clear existing table rows
        tableBody.innerHTML = '';
        
        // Create table rows
        const locations = data.Location || [];
        const ips = data.IP || [];
        
        if (locations.length === 0) {
            throw new Error('No data available');
        }
        
        for (let i = 0; i < locations.length; i++) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${locations[i] || 'N/A'}</td>
                <td>${ips[i] || 'N/A'}</td>
                <td>
                    <div class="action-container">
                        <div class="action-buttons">
                            <button class="action-btn sse-ping-btn" onclick="pingLocationSSE('${ips[i] || ''}', '${locations[i] || ''}', this)">
                                <span class="btn-icon">📺</span>
                                <span class="btn-text">Live Ping</span>
                            </button>
                            <button class="action-btn reset-port-btn" onclick="resetPort('${ips[i] || ''}', '${locations[i] || ''}', this)">
                                <span class="btn-icon">🔄</span>
                                <span class="btn-text">Reset Port</span>
                            </button>
                            <!-- Future buttons can be added here, for example:
                            <button class="action-btn ssh-btn" onclick="sshConnect('${ips[i] || ''}', '${locations[i] || ''}', this)">
                                <span class="btn-icon">🔐</span>
                                <span class="btn-text">SSH</span>
                            </button>
                            <button class="action-btn traceroute-btn" onclick="tracerouteLocation('${ips[i] || ''}', '${locations[i] || ''}', this)">
                                <span class="btn-icon">🛣️</span>
                                <span class="btn-text">Trace</span>
                            </button>
                            -->
                        </div>
                        <div class="result-container" id="result-container-${i}">
                            <div class="result-header" onclick="toggleResult('result-${i}')">
                                <span class="result-title">Ping Result</span>
                                <span class="toggle-icon" id="toggle-${i}">▼</span>
                            </div>
                            <div class="ping-result" id="result-${i}"></div>
                        </div>
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        }
        
        // Hide loading, show table
        loading.style.display = 'none';
        table.style.display = 'table';
        
    } catch (err) {
        console.error('Error loading data:', err);
        loading.style.display = 'none';
        error.style.display = 'block';
        error.textContent = 'Error loading data: ' + err.message;
    }
}


async function pingLocationSSE(ip, location, button) {
    if (!ip || ip === 'N/A') {
        alert('No valid IP address to ping');
        return;
    }
    
    const btnText = button.querySelector('.btn-text');
    const btnIcon = button.querySelector('.btn-icon');
    const originalText = btnText.textContent;
    const originalIcon = btnIcon.textContent;
    
    button.disabled = true;
    btnText.textContent = 'Live Pinging...';
    btnIcon.textContent = '⏳';
    button.classList.add('loading');
    
    // Find the result container and show it
    const resultContainer = button.closest('.action-container').querySelector('.result-container');
    const resultDiv = resultContainer.querySelector('.ping-result');
    const resultTitle = resultContainer.querySelector('.result-title');
    
    // Show result container with animation
    resultContainer.classList.add('active');
    resultTitle.textContent = 'Live Ping...';
    resultDiv.innerHTML = '<div class="sse-ping-container"><div class="sse-ping-output"></div></div>';
    resultDiv.className = 'ping-result sse-ping-result';
    
    // Immediately expand to maximum height for live ping
    resultDiv.style.maxHeight = '300px';
    resultDiv.style.padding = '15px';
    resultContainer.classList.add('expanded');
    
    // Update toggle icon to show expanded state
    const toggleIcon = resultContainer.querySelector('.toggle-icon');
    if (toggleIcon) {
        toggleIcon.textContent = '▲';
    }
    
    const outputDiv = resultDiv.querySelector('.sse-ping-output');
    
    try {
        // Use fetch with streaming response for SSE
        const response = await fetch('/api/network/ping_sse_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                location: location,
                count: 10  // More pings for live display
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Process the stream
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
                break;
            }
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const jsonData = line.substring(6); // Remove 'data: ' prefix
                        const data = JSON.parse(jsonData);
                        
                        switch(data.type) {
                            case 'start':
                                outputDiv.innerHTML = `<div class="sse-event start-event">${data.message}</div>`;
                                break;
                            case 'ping_line':
                                const pingLine = document.createElement('div');
                                pingLine.className = 'sse-event ping-line';
                                pingLine.textContent = data.data;
                                outputDiv.appendChild(pingLine);
                                // Auto-scroll to bottom
                                outputDiv.scrollTop = outputDiv.scrollHeight;
                                break;
                            case 'complete':
                                outputDiv.innerHTML += `<div class="sse-event complete-event">${data.message}</div>`;
                                resultTitle.textContent = 'Live Ping Result ✓';
                                break;
                            case 'error':
                                outputDiv.innerHTML += `<div class="sse-event error-event">${data.message}</div>`;
                                resultTitle.textContent = 'Live Ping Result ✗';
                                break;
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }
        
    } catch (err) {
        console.error('SSE ping error:', err);
        outputDiv.innerHTML = '<div class="sse-event error-event">Error: ' + err.message + '</div>';
        resultTitle.textContent = 'Live Ping Result ✗';
    } finally {
        // Reset button state
        button.disabled = false;
        btnText.textContent = originalText;
        btnIcon.textContent = originalIcon;
        button.classList.remove('loading');
    }
}

function toggleResult(resultId) {
    const resultDiv = document.getElementById(resultId);
    const toggleIcon = document.getElementById('toggle-' + resultId.split('-')[1]);
    const resultContainer = resultDiv.closest('.result-container');
    
    if (resultDiv.style.maxHeight && resultDiv.style.maxHeight !== '0px') {
        // Collapse
        resultDiv.style.maxHeight = '0px';
        resultDiv.style.padding = '0 15px';
        toggleIcon.textContent = '▼';
        resultContainer.classList.remove('expanded');
    } else {
        // Expand
        resultDiv.style.maxHeight = resultDiv.scrollHeight + 'px';
        resultDiv.style.padding = '15px';
        toggleIcon.textContent = '▲';
        resultContainer.classList.add('expanded');
    }
}

function filterTable() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearBtn');
    const table = document.getElementById('dataTable');
    const noResults = document.getElementById('noResults');
    const searchTerm = searchInput.value.toLowerCase().trim();
    
    // Enable/disable clear button based on search input
    clearBtn.disabled = searchTerm === '';
    
    // Get all table rows (excluding header)
    const rows = table.querySelectorAll('tbody tr');
    let visibleCount = 0;
    
    rows.forEach(row => {
        const locationCell = row.cells[0]; // Location is in the first column
        const locationText = locationCell.textContent.toLowerCase();
        
        if (searchTerm === '' || locationText.includes(searchTerm)) {
            row.classList.remove('filtered');
            visibleCount++;
        } else {
            row.classList.add('filtered');
        }
    });
    
    // Show/hide no results message
    if (visibleCount === 0 && searchTerm !== '') {
        noResults.style.display = 'block';
        table.style.display = 'none';
    } else {
        noResults.style.display = 'none';
        table.style.display = 'table';
    }
}

function clearFilter() {
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearBtn');
    const table = document.getElementById('dataTable');
    const noResults = document.getElementById('noResults');
    
    // Clear search input
    searchInput.value = '';
    
    // Disable clear button
    clearBtn.disabled = true;
    
    // Show all rows
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.classList.remove('filtered');
    });
    
    // Hide no results message and show table
    noResults.style.display = 'none';
    table.style.display = 'table';
}

async function resetPort(ip, location, button) {
    if (!ip || ip === 'N/A') {
        alert('No valid IP address to reset port');
        return;
    }
    
    const btnText = button.querySelector('.btn-text');
    const btnIcon = button.querySelector('.btn-icon');
    const originalText = btnText.textContent;
    const originalIcon = btnIcon.textContent;
    
    button.disabled = true;
    btnText.textContent = 'Resetting...';
    btnIcon.textContent = '⏳';
    button.classList.add('loading');
    
    // Find the result container and show it
    const resultContainer = button.closest('.action-container').querySelector('.result-container');
    const resultDiv = resultContainer.querySelector('.ping-result');
    const resultTitle = resultContainer.querySelector('.result-title');
    
    // Show result container with animation
    resultContainer.classList.add('active');
    resultTitle.textContent = 'Reset Port...';
    resultDiv.innerHTML = '<div class="reset-port-container"><div class="reset-port-output">Resetting port...</div></div>';
    resultDiv.className = 'ping-result reset-port-result';
    
    // Immediately expand to show result
    resultDiv.style.maxHeight = '200px';
    resultDiv.style.padding = '15px';
    resultContainer.classList.add('expanded');
    
    // Update toggle icon to show expanded state
    const toggleIcon = resultContainer.querySelector('.toggle-icon');
    if (toggleIcon) {
        toggleIcon.textContent = '▲';
    }
    
    const outputDiv = resultDiv.querySelector('.reset-port-output');
    
    try {
        const response = await fetch('/api/network/reset_port', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                locName: location
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            outputDiv.innerHTML = `
                <div class="reset-success">
                    <strong>✓ Port Reset Successful</strong><br>
                    <span class="reset-details">Location: ${data.data.locName}</span><br>
                    <span class="reset-details">Port: ge-0/0/${data.data.port}</span><br>
                    <span class="reset-details">Status: ${data.data.status}</span>
                </div>
            `;
            resultTitle.textContent = 'Reset Port Result ✓';
        } else {
            outputDiv.innerHTML = `
                <div class="reset-error">
                    <strong>✗ Port Reset Failed</strong><br>
                    <span class="reset-details">Error: ${data.message || 'Unknown error'}</span>
                </div>
            `;
            resultTitle.textContent = 'Reset Port Result ✗';
        }
        
    } catch (err) {
        console.error('Reset port error:', err);
        outputDiv.innerHTML = `
            <div class="reset-error">
                <strong>✗ Reset Port Error</strong><br>
                <span class="reset-details">Error: ${err.message}</span>
            </div>
        `;
        resultTitle.textContent = 'Reset Port Result ✗';
    } finally {
        // Reset button state
        button.disabled = false;
        btnText.textContent = originalText;
        btnIcon.textContent = originalIcon;
        button.classList.remove('loading');
    }
}
