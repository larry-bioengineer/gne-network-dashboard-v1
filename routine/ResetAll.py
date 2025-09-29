#!/usr/bin/env python3
"""
ResetAll.py - Script to reset all locations from data.xlsx file

This script reads all locations from the data.xlsx file and performs SSH reset operations
for each location. It uses the same logic and patterns as the Flask API endpoints for consistency.
Specifically, this script incorporates the logic from:
    - /network/get_ip_and_location (for obtaining locations)
    - /network/reset_port (for reset operations)

Usage:
    python ResetAll.py
    
Requirements:
    - config_file/data.xlsx must exist with 'Hardware list' sheet
    - SSH credentials configured in .env file
    - Internet connectivity to reach network switches
"""

import sys
import os
import pandas as pd
from dotenv import load_dotenv
import time
import socket

# Add the parent directory to sys.path to import service modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from service.SSHConnection import reset_port_poe, retrieve_ssh_info_from_config
from api.models import ResponseModel


def get_all_locations():
    """
    Read all locations from data.xlsx using the same logic as the get_ip_and_location() endpoint
    
    Returns:
        list: List of location names that can be reset
    """
    try:
        print("Reading configuration from data.xlsx...")
        # Use same sheet as in routes.py - 'Hardware list'
        df = pd.read_excel('config_file/data.xlsx', sheet_name='Hardware list')

        # Return error if Location or IP is not found (same as get_ip_and_location)
        if 'Location' not in df.columns or 'IP' not in df.columns:
            print("❌ Error: Location or IP column not found in data file")
            return []
        
        # Filter out NaN values to prevent issues (same pattern as routes)
        df_clean = df.dropna(subset=['Location', 'IP'])
        locations = df_clean['Location'].unique().tolist()
        
        print(f"✅ Found {len(locations)} locations: {locations}")
        return locations
        
    except FileNotFoundError:
        print("❌ Error: config_file/data.xlsx not found")
        return []
    except Exception as e:
        print(f"❌ Error reading data.xlsx: {str(e)}")
        return []


def analyze_ssh_error(ip, port, timeout):
    """
    Analyze potential SSH connection issues and provide diagnostic information
    Copied from routes.py for consistency with the endpoint
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


def reset_single_location(location, timeout=10):
    """
    Reset a single location using the same logic as network/reset_port endpoint
    
    Args:
        location (str): The location name to reset
        timeout (int): Connection timeout in seconds
        
    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        print(f"\n🔧 Starting reset for location: {location}")
        
        # Use the same validation pattern as in routes.py
        if not location:
            print("❌ Location name is required")
            return False

        # Same logic as routes/reset_port 
        config = retrieve_ssh_info_from_config(location)
        
        if not config:
            print("❌ SSH Configuration not found for location")
            return False

        # Load environment variables for SSH credentials (same as routes)
        load_dotenv()
        ssh_username = os.getenv('SSH_USERNAME')
        ssh_password = os.getenv('SSH_PASSWORD')
        
        if not ssh_username or not ssh_password:
            print("❌ SSH credentials not configured. Please set SSH_USERNAME and SSH_PASSWORD in .env file")
            return False

        ssh_port = config['port']
        
        try:
            ssh_port = int(ssh_port)
        except ValueError:
            print("❌ Invalid SSH_PORT in config file. Must be a valid integer")
            return False
        
        # Store the target_port before overwriting config
        target_port = config['target_port']
        
        # Create SSH configuration (same as routes)
        ssh_config = {
            'hostname': config['hostname'],
            'username': ssh_username,
            'password': ssh_password,
            'port': ssh_port
        }
        
        # Execute port reset with timeout (same as routes)
        success = reset_port_poe(ssh_config, target_port, timeout)
        
        if success:
            print(f"✅ {location} - Port ge-0/0/{target_port} reset successfully")
            return True
        else:
            # Perform SSH connection diagnostics (same as routes)
            diagnostics = analyze_ssh_error(ssh_config['hostname'], ssh_port, timeout)
            
            # Determine error type based on diagnostics (same error handling as routes)
            if diagnostics["hostname_resolution"] == "failed":
                print(f"❌ {location} - Cannot resolve hostname/IP: {ssh_config['hostname']}")
            elif diagnostics["ssh_port_open"] == "closed":
                print(f"❌ {location} - SSH port {ssh_port} is closed or filtered")
            elif diagnostics["connection_test"] == "success":
                print(f"❌ {location} - SSH authentication failed (connection established but auth failed)")
            else:
                print(f"❌ {location} - SSH connection timeout after {timeout} seconds")
            
            return False
            
    except Exception as e:
        # Handle unexpected errors (similar to routes error handling)
        diagnostics = None
        
        try:
            # Try to get diagnostics for better error reporting
            if 'ssh_config' in locals() and ssh_config:
                diagnostics = analyze_ssh_error(ssh_config['hostname'], ssh_config.get('port', 22), timeout)
            elif 'config' in locals() and config:
                diagnostics = analyze_ssh_error(config['hostname'], config.get('port', 22), timeout)
        except:
            pass  # Ignore diagnostics errors
        
        print(f"❌ {location} - Unexpected error during reset: {str(e)}")
        
        if diagnostics:
            print(f"🔍 Diagnostics: {diagnostics}")
        
        return False


def reset_all_locations():
    """
    Reset all locations from the data.xlsx file using consistent route patterns
    
    Returns:
        dict: Summary of reset operations with success/failure counts
    """
    print("=" * 60)
    print("🚀 SSHAutomation - Reset All Locations")
    print("=" * 60)
    
    # Load environment variables first (same as routes logic)
    load_dotenv()
    
    # Check if SSH credentials are available (same validation as routes)
    ssh_username = os.getenv('SSH_USERNAME')
    ssh_password = os.getenv('SSH_PASSWORD')
    
    if not ssh_username or not ssh_password:
        print("❌ SSH credentials not configured!")
        print("Please set SSH_USERNAME and SSH_PASSWORD in .env file")
        return {'success': 0, 'failed': 0, 'error': 'SSH credentials not configured'}
    
    # Get all locations from configuration using same pattern as get_ip_and_location
    locations = get_all_locations()
    
    if not locations:
        print("❌ No locations found to reset")
        return {'success': 0, 'failed': 0, 'error': 'No locations found'}
    
    print(f"\n📋 Found {len(locations)} locations to reset")
    print("=" * 60)
    
    # Track success and failure
    success_count = 0
    failed_count = 0
    failed_locations = []
    
    # Reset each location (using same logic as routes reset_port)
    for i, location in enumerate(locations, 1):
        print(f"\n[{i}/{len(locations)}] Processing: {location}")
        
        # Use default timeout from routes (10 seconds, same as routes endpoint)
        success = reset_single_location(location, timeout=10)
        
        if success:
            success_count += 1
        else:
            failed_count += 1
            failed_locations.append(location)
        
        # Small delay between operations to prevent overwhelming switches
        if i < len(locations):
            print("⏳ Waiting 5 seconds before next reset...")
            time.sleep(5)
    
    # Summary with consistent messaging
    print("\n" + "=" * 60)
    print("📊 RESET SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"📋 Total processed: {len(locations)}")
    
    if failed_locations:
        print(f"\n📍 Failed locations: {', '.join(failed_locations)}")
    
    print("=" * 60)
    print("🏁 Reset All operation completed!")
    
    return {
        'success': success_count,
        'failed': failed_count,
        'failed_locations': failed_locations,
        'total': len(locations)
    }


def main():
    """
    Main function to execute reset all operations
    """
    try:
        # Execute reset all operation
        result = reset_all_locations()
        
        # Exit with appropriate code
        if result.get('error'):
            sys.exit(1)
        elif result['failed'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
