from flask import Blueprint, jsonify, request, Response
from api.models import ResponseModel
import subprocess
import pandas as pd
import os
import time
import threading
import json
import socket
from dotenv import load_dotenv
from service.SSHConnection import reset_port_poe, retrieve_ssh_info_from_config

# Create a Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

def analyze_ssh_error(ip, port, timeout):
    """
    Analyze potential SSH connection issues and provide diagnostic information
    """
    diagnostics = {
        "connection_test": "pending",
        "ssh_port_open": "pending", 
        "hostname_resolution": "pending",
        "recommendations": []
    }
    
    try:
        # Test hostname resolution
        socket.gethostbyname(ip)
        diagnostics["hostname_resolution"] = "success"
    except socket.gaierror:
        diagnostics["hostname_resolution"] = "failed"
        diagnostics["recommendations"].append("Check if the IP address or hostname is correct")
    
    try:
        # Test if SSH port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            diagnostics["ssh_port_open"] = "open"
            diagnostics["connection_test"] = "success"
        else:
            diagnostics["ssh_port_open"] = "closed"
            diagnostics["connection_test"] = "failed"
            diagnostics["recommendations"].append(f"SSH port {port} appears to be closed or filtered")
    except Exception as e:
        diagnostics["connection_test"] = "error"
        diagnostics["recommendations"].append(f"Unable to test connection: {str(e)}")
    
    return diagnostics

# Admin endpoints
@api_bp.route('/admin/health', methods=['GET'])
def health_check():
    """Health check endpoint that returns success status"""
    response = ResponseModel(
        success=True,
        message="API is healthy and running",
        data={"status": "ok", "service": "SSH Automation Server"}
    )
    return jsonify(response.to_dict())

@api_bp.route('/admin/status', methods=['GET'])
def get_status():
    """Status endpoint that returns current system status"""
    response = ResponseModel(
        success=True,
        message="System status retrieved successfully",
        data={
            "system": "SSH Automation Server",
            "version": "1.0.0",
            "uptime": "running"
        }
    )
    return jsonify(response.to_dict())

# Network endpoints
@api_bp.route('/network/ping', methods=['POST'])
def ping():
    """
    Ping a given network interface

    Args:
        interface: The network interface to ping

    Returns:
        A JSON response with the ping result
    """
    data = request.json
    interface = data.get('interface')

    if not interface:
        return jsonify({'error': 'Interface is required'}), 400

    # ping the interface
    ping_result = subprocess.run(['ping', '-c', '4', interface], capture_output=True, text=True)
    
    return jsonify({'result': ping_result.stdout})

@api_bp.route('/network/get_ip_and_location', methods=['GET'])
def get_ip_and_location():
    """
    Get the IP and location from the data.xlsx file
    """
    try:
        df = pd.read_excel('config_file/data.xlsx', sheet_name='Hardware list')
        
        # Filter out NaN values to prevent JSON serialization errors
        df_clean = df.dropna(subset=['Location', 'IP'])
        
        return jsonify({'Location': df_clean['Location'].values.tolist(), 'IP': df_clean['IP'].values.tolist()})
    except Exception as e:
        return jsonify({'error': f'Failed to read data file: {str(e)}'}), 500

@api_bp.route('/network/ping_specific_location', methods=['POST'])
def ping_specific_location():
    """
    Ping a given network interface to a specific location

    Args:
        interface: The network interface to ping
        location: The location to ping

    Returns:
        A JSON response with the ping result
    """
    data = request.json
    
    try:
        # open the data.xlsx file
        df = pd.read_excel('config_file/data.xlsx', sheet_name='Hardware List')
        
        # Filter out NaN values to prevent issues
        df_clean = df.dropna(subset=['Location', 'IP'])

        # get the interface and location
        interface = data.get('interface')
        location = data.get('location')

        if not interface or not location:
            return jsonify({'error': 'Both interface and location are required'}), 400

        # Find the IP for the specific location
        location_data = df_clean[df_clean['Location'] == location]
        if location_data.empty:
            return jsonify({'error': f'Location "{location}" not found'}), 404

        target_ip = location_data['IP'].iloc[0]
        
        # Ping the specific IP
        ping_result = subprocess.run(['ping', '-c', '4', target_ip], capture_output=True, text=True)
        
        return jsonify({
            'result': ping_result.stdout,
            'location': location,
            'target_ip': target_ip
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to ping location: {str(e)}'}), 500

@api_bp.route('/network/ping_sse', methods=['POST'])
def ping_sse():
    """
    Ping a given network interface using Server-Sent Events (SSE)
    
    Args:
        interface: The network interface to ping
        count: Number of ping packets to send (optional, defaults to 4)
        
    Returns:
        A Server-Sent Events stream with ping results
    """
    data = request.json
    interface = data.get('interface')
    count = data.get('count', 4)
    
    if not interface:
        return jsonify({'error': 'Interface is required'}), 400
    
    def generate_ping_events():
        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': f'Starting ping to {interface}', 'timestamp': time.time()})}\n\n"
            
            # Start ping process
            ping_process = subprocess.Popen(
                ['ping', '-c', str(count), interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read ping output line by line
            for line in iter(ping_process.stdout.readline, ''):
                if line:
                    # Send each ping line as an event
                    yield f"data: {json.dumps({'type': 'ping_line', 'data': line.strip(), 'timestamp': time.time()})}\n\n"
                    time.sleep(0.1)  # Small delay to prevent overwhelming the client
            
            # Wait for process to complete
            ping_process.wait()
            
            # Send completion event
            if ping_process.returncode == 0:
                yield f"data: {json.dumps({'type': 'complete', 'message': 'Ping completed successfully', 'timestamp': time.time()})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Ping failed', 'timestamp': time.time()})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error during ping: {str(e)}', 'timestamp': time.time()})}\n\n"
    
    return Response(
        generate_ping_events(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

@api_bp.route('/network/ping_sse_location', methods=['POST'])
def ping_sse_location():
    """
    Ping a specific location using Server-Sent Events (SSE)
    
    Args:
        location: The location to ping
        count: Number of ping packets to send (optional, defaults to 4)
        
    Returns:
        A Server-Sent Events stream with ping results
    """
    data = request.json
    location = data.get('location')
    count = data.get('count', 4)
    
    if not location:
        return jsonify({'error': 'Location is required'}), 400
    
    def generate_ping_events():
        try:
            # Load location data
            df = pd.read_excel('config_file/data.xlsx', sheet_name='Hardware list')
            df_clean = df.dropna(subset=['Location', 'IP'])
            
            # Find the IP for the specific location
            location_data = df_clean[df_clean['Location'] == location]
            if location_data.empty:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Location "{location}" not found', 'timestamp': time.time()})}\n\n"
                return
            
            target_ip = location_data['IP'].iloc[0]
            
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'message': f'Starting ping to {location} ({target_ip})', 'location': location, 'target_ip': target_ip, 'timestamp': time.time()})}\n\n"
            
            # Start ping process
            ping_process = subprocess.Popen(
                ['ping', '-c', str(count), target_ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read ping output line by line
            for line in iter(ping_process.stdout.readline, ''):
                if line:
                    # Send each ping line as an event
                    yield f"data: {json.dumps({'type': 'ping_line', 'data': line.strip(), 'location': location, 'target_ip': target_ip, 'timestamp': time.time()})}\n\n"
                    time.sleep(0.1)  # Small delay to prevent overwhelming the client
            
            # Wait for process to complete
            ping_process.wait()
            
            # Send completion event
            if ping_process.returncode == 0:
                yield f"data: {json.dumps({'type': 'complete', 'message': f'Ping to {location} completed successfully', 'location': location, 'target_ip': target_ip, 'timestamp': time.time()})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Ping to {location} failed', 'location': location, 'target_ip': target_ip, 'timestamp': time.time()})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Error during ping: {str(e)}', 'timestamp': time.time()})}\n\n"
    
    return Response(
        generate_ping_events(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control'
        }
    )

@api_bp.route('/network/reset_port', methods=['POST'])
def reset_port():
    """
    Reset the port of a given IP by disabling and enabling PoE
    
    Args:
        request.json (dict): JSON payload containing:
            - ip (str, required): The IP address of the network switch
            - port (int, optional): The port number to reset (e.g., 16 for ge-0/0/16). 
                                   Defaults to 22 if not provided.
            - timeout (int, optional): Connection timeout in seconds. Defaults to 10.
    
    Returns:
        ResponseModel: JSON response containing:
            - success (bool): Whether the operation was successful
            - message (str): Human-readable message describing the result
            - data (dict, optional): Additional data including:
                - ip (str): The target IP address
                - port (int): The port number that was reset
                - status (str): Status of the reset operation
    
    Raises:
        400: If IP address is missing from request
        500: If SSH credentials are not configured or invalid
        500: If port reset operation fails
        500: If any other error occurs during execution
    
    Environment Variables Required:
        - SSH_USERNAME: SSH username for switch authentication
        - SSH_PASSWORD: SSH password for switch authentication
        - SSH_PORT: SSH port number (optional, defaults to 22)
    
    Example:
        Request:
        {
            "ip": "192.168.1.1",
            "port": 16
        }
        
        Response (Success):
        {
            "success": true,
            "message": "Port ge-0/0/16 reset successfully",
            "data": {
                "ip": "192.168.1.1",
                "port": 16,
                "status": "reset_completed"
            }
        }
    """
    try:
        # Load environment variables
        load_dotenv()
        
        data = request.json
        locName = data.get('locName')
        timeout = data.get('timeout', 10)  # Default timeout of 10 seconds

        if not locName:
            response = ResponseModel(
                success=False,
                message="Location name is required",
                data=None
            )
            return jsonify(response.to_dict()), 400

        # INSERT PORT NUMBER LOOKUP CODE HERE
        config = retrieve_ssh_info_from_config(locName)
        
        # Validate timeout parameter
        try:
            timeout = int(timeout)
            if timeout <= 0 or timeout > 300:  # Allow 1-300 seconds
                raise ValueError("Timeout must be between 1 and 300 seconds")
        except (ValueError, TypeError):
            response = ResponseModel(
                success=False,
                message="Invalid timeout value. Must be an integer between 1 and 300 seconds",
                data=None
            )
            return jsonify(response.to_dict()), 400
        
        if not config:
            response = ResponseModel(
                success=False,
                message="SSH Configuration not found",
                data=None
            )
            return jsonify(response.to_dict()), 400
        
        # Get SSH credentials from environment variables
        ssh_username = os.getenv('SSH_USERNAME')
        ssh_password = os.getenv('SSH_PASSWORD')
        ssh_port = config['port']
        
        # Validate that all required credentials are provided
        if not ssh_username or not ssh_password:
            response = ResponseModel(
                success=False,
                message="SSH credentials not configured. Please set SSH_USERNAME and SSH_PASSWORD in .env file",
                data=None
            )
            return jsonify(response.to_dict()), 500
        
        
        try:
            ssh_port = int(ssh_port)
        except ValueError:
            response = ResponseModel(
                success=False,
                message="Invalid SSH_PORT in config file. Must be a valid integer",
                data=None
            )
            return jsonify(response.to_dict()), 500
        
        # Create SSH configuration
        config = {
            'hostname': config['hostname'],
            'username': ssh_username,
            'password': ssh_password,
            'port': ssh_port
        }
        
        # Execute port reset with timeout
        success = reset_port_poe(config, config['target_port'], timeout)
        
        if success:
            response = ResponseModel(   
                success=True,
                message=f"Port ge-0/0/{config['target_port']} reset successfully for {locName}",
                data={
                    "locName": locName,
                    "port": config['target_port'],
                    "status": f"reset_completed for {locName}"
                }
            )
            return jsonify(response.to_dict())
        else:
            # Perform SSH connection diagnostics
            diagnostics = analyze_ssh_error(config['hostname'], ssh_port, timeout)
            
            # Determine error type based on diagnostics
            if diagnostics["hostname_resolution"] == "failed":
                error_type = "DNS_RESOLUTION_FAILED"
                error_message = f"🔍 Cannot resolve hostname/IP: {config['hostname']}. Please verify the IP address is correct."
            elif diagnostics["ssh_port_open"] == "closed":
                error_type = "SSH_PORT_CLOSED"
                error_message = f"🚫 SSH connection failed: Port {ssh_port} is closed or filtered. SSH service may not be running."
            elif diagnostics["connection_test"] == "success":
                error_type = "SSH_AUTHENTICATION_FAILED"
                error_message = f"🔐 SSH connection established but authentication failed. Please check credentials."
            else:
                error_type = "SSH_CONNECTION_TIMEOUT"
                error_message = f"⏱️ SSH connection timeout after {timeout} seconds. Check network connectivity and firewall settings."
            
            response = ResponseModel(
                success=False,
                message=error_message,
                data={
                    "locName": locName,
                    "port": config['target_port'],
                    "ssh_port": ssh_port,
                    "timeout": timeout,
                    "status": "reset_failed",
                    "error_type": error_type,
                    "diagnostics": diagnostics
                }
            )
            return jsonify(response.to_dict()), 500
            
    except Exception as e:
        # Perform basic diagnostics even for unexpected errors
        diagnostics = analyze_ssh_error(config['hostname'], int(ssh_port) if ssh_port else 22, timeout)
        
        response = ResponseModel(
            success=False,
            message=f"❌ Unexpected error during port reset: {str(e)}",
            data={
                "locName": locName,
                "port": config['target_port'],
                "status": "error",
                "error_type": "UNEXPECTED_ERROR",
                "diagnostics": diagnostics
            }
        )
        return jsonify(response.to_dict()), 500
