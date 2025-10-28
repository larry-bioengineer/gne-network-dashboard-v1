// Tracking variables for auto-refresh
let isLoading = false;
let autoRefreshInterval = null;
let autoRefreshIntervalSeconds = 20; // Default to 20 seconds

// Load data when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadData();
    
    // Start auto-refresh interval
    startAutoRefresh();
});

function startAutoRefresh() {
    // Clear any existing interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Set interval to check and reload data
    autoRefreshInterval = setInterval(async function() {
        // If currently loading, skip this round
        if (isLoading) {
            console.log('Still loading, skipping this refresh cycle');
            return;
        }
        
        // Check if status checks are complete by looking for any "Checking..." status
        const allStatusComplete = checkAllStatusComplete();
        
        if (!allStatusComplete) {
            console.log('Status checks not complete, skipping this refresh cycle');
            return;
        }
        
        // All done, trigger reload
        console.log('Triggering auto-refresh...');
        loadData();
    }, autoRefreshIntervalSeconds * 1000);
}

function checkAllStatusComplete() {
    // Check all status elements to see if any are still "Checking..."
    const statusElements = document.querySelectorAll('.status-indicator');
    
    for (let statusElement of statusElements) {
        const statusText = statusElement.querySelector('.status-text');
        if (statusText && statusText.textContent === 'Checking...') {
            return false; // Still checking
        }
    }
    
    return true; // All complete
}

async function loadData() {
    if (isLoading) {
        console.log('Already loading, skipping duplicate request');
        return;
    }
    
    isLoading = true;
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
                <td class="checkbox-column">
                    <input type="checkbox" class="location-checkbox" data-location="${locations[i] || ''}" data-ip="${ips[i] || ''}" onchange="updateSelectionCount()">
                </td>
                <td>${locations[i] || 'N/A'}</td>
                <td>${ips[i] || 'N/A'}</td>
                <td class="status-column">
                    <span class="status-indicator" id="status-${i}">
                        <span class="status-text">Checking...</span>
                        <span class="status-icon">⏳</span>
                    </span>
                </td>
                <td>
                    <div class="action-container">
                        <div class="action-buttons">
                            <button class="action-btn sse-ping-btn" onclick="pingLocationSSE('${ips[i] || ''}', '${locations[i] || ''}', this)">
                                <span class="btn-text">Live Ping</span>
                            </button>
                            <button class="action-btn reset-port-btn" onclick="resetPort('${ips[i] || ''}', '${locations[i] || ''}', this)">
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
        
        // Show batch controls after data is loaded
        document.getElementById('batchControls').style.display = 'block';
        
        // Hide loading, show table
        loading.style.display = 'none';
        table.style.display = 'table';
        
        // Start pinging all IPs to check their status and wait for completion
        await pingAllStatuses();
        
    } catch (err) {
        console.error('Error loading data:', err);
        loading.style.display = 'none';
        error.style.display = 'block';
        error.textContent = 'Error loading data: ' + err.message;
    } finally {
        isLoading = false;
    }
}


async function pingLocationSSE(ip, location, button) {
    if (!ip || ip === 'N/A') {
        alert('No valid IP address to ping');
        return;
    }
    
    const btnText = button.querySelector('.btn-text');
    const originalText = btnText.textContent;
    
    button.disabled = true;
    btnText.textContent = 'Live Pinging...';
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
        const locationCell = row.cells[1]; // Location is now in the second column (after checkbox)
        const locationText = locationCell.textContent.toLowerCase();
        
        if (searchTerm === '' || locationText.includes(searchTerm)) {
            row.classList.remove('filtered');
            visibleCount++;
        } else {
            row.classList.add('filtered');
        }
    });
    
    // Update selection count after filtering
    updateSelectionCount();
    
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
    
    // Update selection count after clearing filter
    updateSelectionCount();
    
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
    const originalText = btnText.textContent;
    
    button.disabled = true;
    btnText.textContent = 'Resetting...';
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
        button.classList.remove('loading');
    }
}

// Batch operation functions
function updateSelectionCount() {
    const allCheckboxes = document.querySelectorAll('.location-checkbox');
    const checkboxes = Array.from(allCheckboxes).filter(checkbox => 
        !checkbox.closest('tr').classList.contains('filtered')
    );
    const selectedCheckboxes = checkboxes.filter(checkbox => checkbox.checked);
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const selectionCount = document.getElementById('selectionCount');
    const batchPingBtn = document.querySelector('.batch-ping-btn');
    const batchResetBtn = document.querySelector('.batch-reset-btn');
    
    const visibleCount = checkboxes.length;
    const selectedCount = selectedCheckboxes.length;
    
    // Update selection count display
    selectionCount.textContent = `${selectedCount} selected`;
    
    // Update select all checkbox state
    if (selectedCount === 0) {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = false;
    } else if (selectedCount === visibleCount) {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = true;
    } else {
        selectAllCheckbox.indeterminate = true;
    }
    
    // Enable/disable batch action buttons
    const hasSelection = selectedCount > 0;
    batchPingBtn.disabled = !hasSelection;
    batchResetBtn.disabled = !hasSelection;
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const allCheckboxes = document.querySelectorAll('.location-checkbox');
    const checkboxes = Array.from(allCheckboxes).filter(checkbox => 
        !checkbox.closest('tr').classList.contains('filtered')
    );
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
    
    updateSelectionCount();
}

function selectAllVisible() {
    const allCheckboxes = document.querySelectorAll('.location-checkbox');
    const checkboxes = Array.from(allCheckboxes).filter(checkbox => 
        !checkbox.closest('tr').classList.contains('filtered')
    );
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
    });
    updateSelectionCount();
}

function deselectAll() {
    const allCheckboxes = document.querySelectorAll('.location-checkbox');
    const checkboxes = Array.from(allCheckboxes).filter(checkbox => 
        !checkbox.closest('tr').classList.contains('filtered')
    );
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    updateSelectionCount();
}

function getSelectedLocations() {
    const selectedCheckboxes = document.querySelectorAll('.location-checkbox:checked');
    return Array.from(selectedCheckboxes).map(checkbox => ({
        location: checkbox.dataset.location,
        ip: checkbox.dataset.ip
    }));
}

async function batchPingSelected() {
    const selectedLocations = getSelectedLocations();
    
    if (selectedLocations.length === 0) {
        alert('No locations selected');
        return;
    }
    
    const batchPingBtn = document.querySelector('.batch-ping-btn');
    const btnText = batchPingBtn.querySelector('.btn-text');
    const originalText = btnText.textContent;
    
    // Update button state
    batchPingBtn.disabled = true;
    btnText.textContent = `Pinging ${selectedLocations.length} locations...`;
    batchPingBtn.classList.add('loading');
    
    try {
        // Create a batch results container
        const batchResultsContainer = createBatchResultsContainer('Batch Live Ping Results');
        
        // Create result divs for all locations first
        for (let i = 0; i < selectedLocations.length; i++) {
            const location = selectedLocations[i];
            const resultDiv = document.createElement('div');
            resultDiv.className = 'batch-result-item';
            resultDiv.innerHTML = `
                <div class="batch-result-header">
                    <strong>${location.location}</strong> (${location.ip})
                    <span class="batch-result-status" id="status-${i}">Pinging...</span>
                </div>
                <div class="batch-result-content" id="content-${i}"></div>
            `;
            batchResultsContainer.appendChild(resultDiv);
        }
        
        // Start all pings concurrently (in parallel)
        const pingPromises = selectedLocations.map((location, i) => 
            pingLocationForBatch(location.location, location.ip, i)
        );
        
        // Wait for all pings to complete
        await Promise.all(pingPromises);
        
    } catch (err) {
        console.error('Batch ping error:', err);
        alert('Error during batch ping: ' + err.message);
    } finally {
        // Reset button state
        batchPingBtn.disabled = false;
        btnText.textContent = originalText;
        batchPingBtn.classList.remove('loading');
    }
}

async function batchResetSelected() {
    const selectedLocations = getSelectedLocations();
    
    if (selectedLocations.length === 0) {
        alert('No locations selected');
        return;
    }
    
    if (!confirm(`Are you sure you want to reset ports for ${selectedLocations.length} selected locations?`)) {
        return;
    }
    
    const batchResetBtn = document.querySelector('.batch-reset-btn');
    const btnText = batchResetBtn.querySelector('.btn-text');
    const originalText = btnText.textContent;
    
    // Update button state
    batchResetBtn.disabled = true;
    btnText.textContent = `Resetting ${selectedLocations.length} locations...`;
    batchResetBtn.classList.add('loading');
    
    try {
        // Create a batch results container
        const batchResultsContainer = createBatchResultsContainer('Batch Reset Port Results');
        
        // Create result divs for all locations first
        for (let i = 0; i < selectedLocations.length; i++) {
            const location = selectedLocations[i];
            const resultDiv = document.createElement('div');
            resultDiv.className = 'batch-result-item';
            resultDiv.innerHTML = `
                <div class="batch-result-header">
                    <strong>${location.location}</strong> (${location.ip})
                    <span class="batch-result-status" id="status-${i}">Resetting...</span>
                </div>
                <div class="batch-result-content" id="content-${i}"></div>
            `;
            batchResultsContainer.appendChild(resultDiv);
        }
        
        // Start all resets concurrently (in parallel)
        const resetPromises = selectedLocations.map((location, i) => 
            resetPortForBatch(location.location, location.ip, i)
        );
        
        // Wait for all resets to complete
        await Promise.all(resetPromises);
        
    } catch (err) {
        console.error('Batch reset error:', err);
        alert('Error during batch reset: ' + err.message);
    } finally {
        // Reset button state
        batchResetBtn.disabled = false;
        btnText.textContent = originalText;
        batchResetBtn.classList.remove('loading');
    }
}

function createBatchResultsContainer(title) {
    // Remove existing batch results if any
    const existingContainer = document.getElementById('batchResultsContainer');
    if (existingContainer) {
        existingContainer.remove();
    }
    
    // Create new batch results container
    const container = document.createElement('div');
    container.id = 'batchResultsContainer';
    container.className = 'batch-results-container';
    container.innerHTML = `
        <div class="batch-results-header">
            <h3>${title}</h3>
            <button class="close-batch-results" onclick="closeBatchResults()">×</button>
        </div>
        <div class="batch-results-content"></div>
    `;
    
    // Insert after the table
    const table = document.getElementById('dataTable');
    table.parentNode.insertBefore(container, table.nextSibling);
    
    return container.querySelector('.batch-results-content');
}

function closeBatchResults() {
    const container = document.getElementById('batchResultsContainer');
    if (container) {
        container.remove();
    }
}

async function pingLocationForBatch(location, ip, index) {
    const statusElement = document.getElementById(`status-${index}`);
    const contentElement = document.getElementById(`content-${index}`);
    
    try {
        const response = await fetch('/api/network/ping_sse_location', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                location: location,
                count: 4
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let output = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const jsonData = line.substring(6);
                        const data = JSON.parse(jsonData);
                        
                        if (data.type === 'ping_line') {
                            output += data.data + '\n';
                            contentElement.innerHTML = `<pre>${output}</pre>`;
                        } else if (data.type === 'complete') {
                            statusElement.textContent = '✓ Completed';
                            statusElement.className = 'batch-result-status success';
                        } else if (data.type === 'error') {
                            statusElement.textContent = '✗ Failed';
                            statusElement.className = 'batch-result-status error';
                            contentElement.innerHTML = `<div class="error">${data.message}</div>`;
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }
        
    } catch (err) {
        statusElement.textContent = '✗ Error';
        statusElement.className = 'batch-result-status error';
        contentElement.innerHTML = `<div class="error">Error: ${err.message}</div>`;
    }
}

async function resetPortForBatch(location, ip, index) {
    const statusElement = document.getElementById(`status-${index}`);
    const contentElement = document.getElementById(`content-${index}`);
    
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
            statusElement.textContent = '✓ Success';
            statusElement.className = 'batch-result-status success';
            contentElement.innerHTML = `
                <div class="success">
                    <strong>Port Reset Successful</strong><br>
                    Location: ${data.data.locName}<br>
                    Port: ge-0/0/${data.data.port}
                </div>
            `;
        } else {
            statusElement.textContent = '✗ Failed';
            statusElement.className = 'batch-result-status error';
            contentElement.innerHTML = `
                <div class="error">
                    <strong>Port Reset Failed</strong><br>
                    Error: ${data.message || 'Unknown error'}
                </div>
            `;
        }
        
    } catch (err) {
        statusElement.textContent = '✗ Error';
        statusElement.className = 'batch-result-status error';
        contentElement.innerHTML = `<div class="error">Error: ${err.message}</div>`;
    }
}

// Function to ping all IPs and update their status indicators using concurrent requests
async function pingAllStatuses() {
    try {
        // Get all IP addresses and locations from the table
        const tableRows = document.querySelectorAll('#tableBody tr');
        const pingPromises = [];
        const rowData = [];
        
        // Prepare data for each row
        for (let i = 0; i < tableRows.length; i++) {
            const row = tableRows[i];
            const ipCell = row.cells[2]; // IP is in the third column
            const locationCell = row.cells[1]; // Location is in the second column
            
            if (ipCell && locationCell) {
                const ip = ipCell.textContent.trim();
                const location = locationCell.textContent.trim();
                
                if (ip && ip !== 'N/A') {
                    rowData.push({ index: i, ip, location });
                    
                    // Create a promise for each ping request
                    const pingPromise = fetch('/api/network/ping_single_status', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            ip: ip,
                            location: location
                        })
                    }).then(response => response.json())
                      .then(data => ({ index: i, data, success: true }))
                      .catch(error => ({ index: i, error, success: false }));
                    
                    pingPromises.push(pingPromise);
                }
            }
        }
        
        console.log(`Starting concurrent ping for ${pingPromises.length} locations...`);
        
        // Execute all ping requests concurrently using Promise.all()
        const results = await Promise.all(pingPromises);
        
        let successfulPings = 0;
        let totalPings = results.length;
        
        // Process results and update status indicators
        results.forEach(result => {
            const statusElement = document.getElementById(`status-${result.index}`);
            if (statusElement) {
                const statusText = statusElement.querySelector('.status-text');
                const statusIcon = statusElement.querySelector('.status-icon');
                
                if (result.success && result.data.success) {
                    const pingData = result.data.data;
                    if (pingData.status) {
                        // IP is reachable
                        statusText.textContent = 'Online';
                        statusIcon.textContent = '🟢';
                        statusElement.className = 'status-indicator online';
                        successfulPings++;
                    } else {
                        // IP is not reachable
                        statusText.textContent = 'Offline';
                        statusIcon.textContent = '🔴';
                        statusElement.className = 'status-indicator offline';
                    }
                } else {
                    // Error occurred
                    statusText.textContent = 'Error';
                    statusIcon.textContent = '❌';
                    statusElement.className = 'status-indicator error';
                }
            }
        });
        
        console.log(`Concurrent status check completed: ${successfulPings}/${totalPings} locations online`);
        
    } catch (err) {
        console.error('Error checking ping statuses:', err);
        
        // Update all status indicators to show error
        const statusElements = document.querySelectorAll('.status-indicator');
        statusElements.forEach(element => {
            const statusText = element.querySelector('.status-text');
            const statusIcon = element.querySelector('.status-icon');
            statusText.textContent = 'Error';
            statusIcon.textContent = '❌';
            element.className = 'status-indicator error';
        });
    }
}
