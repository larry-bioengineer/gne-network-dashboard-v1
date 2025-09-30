#!/usr/bin/env python3
"""
ResetDownOnly.py - Script to ping ports and reset only those that are down

This script reads port details from data.xlsx file and performs ping checks for each port.
Only ports that fail the ping test will be reset via SSH. This is more efficient than
resetting all ports as it only targets problematic ones.

Usage:
    python ResetDownOnly.py
    
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
import subprocess

# Add the parent directory to sys.path to import service modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from service.SSHConnection import reset_port_poe, retrieve_ssh_info_from_config
from api.models import ResponseModel


def ping_host(ip_address, timeout=10, count=3):
    """
    Ping a host to check if it's reachable
    
    Args:
        ip_address (str): IP address to ping
        timeout (int): Timeout in seconds for each ping
        count (int): Number of ping packets to send
        
    Returns:
        bool: True if ping successful, False otherwise
    """
    try:
        print(f"Pinging {ip_address}...")
        ping_result = subprocess.run(
            ['ping', '-c', str(count), '-W', str(timeout), ip_address], 
            capture_output=True, 
            text=True,
            timeout=timeout + 5  # Add buffer to ping timeout
        )
        
        if ping_result.returncode == 0:
            print(f"✅ {ip_address} is reachable")
            return True
        else:
            print(f"❌ {ip_address} is unreachable")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏱️ Ping timeout for {ip_address}")
        return False
    except Exception as e:
        print(f"❌ Error pinging {ip_address}: {str(e)}")
        return False


def get_all_locations():
    """
    Read all locations from data.xlsx using the same logic as the API endpoints
    
    Returns:
        list: List of location names that can be checked
    """
    try:
        print("Reading configuration from data.xlsx...")
        # Get the project root directory (parent of routine directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        excel_path = os.path.join(project_root, 'config_file', 'data.xlsx')
        
        # Use same sheet as in routes.py - 'Hardware list'
        df = pd.read_excel(excel_path, sheet_name='Hardware list')

        # Return error if Location or IP is not found (same as API)
        if 'Location' not in df.columns or 'IP' not in df.columns:
            print("❌ Error: Location or IP column not found in data file")
            return []
        
        # Filter out NaN values to prevent issues (same pattern as API)
        df_clean = df.dropna(subset=['Location', 'IP'])
        locations = df_clean['Location'].unique().tolist()
        
        print(f"✅ Found {len(locations)} locations: {locations}")
        return locations, df_clean
        
    except FileNotFoundError:
        print("❌ Error: config_file/data.xlsx not found")
        return [], None
    except Exception as e:
        print(f"❌ Error reading data.xlsx: {str(e)}")
        return [], None


def analyze_ssh_error(ip, port, timeout):
    """
    Analyze potential SSH connection issues and provide diagnostic information
    Copied from routes.py for consistency with the API
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
    Reset a single location using the same logic as the API reset_port endpoint
    
    Args:
        location (str): The location name to reset
        timeout (int): Connection timeout in seconds
        
    Returns:
        bool: True if reset successful, False otherwise
    """
    try:
        print(f"\n🔧 Starting reset for location: {location}")
        
        # Use the same validation pattern as in API
        if not location:
            print("❌ Location name is required")
            return False

        # Same logic as API reset_port 
        config = retrieve_ssh_info_from_config(location)
        
        if not config:
            print("❌ SSH Configuration not found for location")
            return False

        # Load environment variables for SSH credentials (same as API)
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
        
        # Create SSH configuration (same as API)
        ssh_config = {
            'hostname': config['hostname'],
            'username': ssh_username,
            'password': ssh_password,
            'port': ssh_port
        }
        
        # Execute port reset with timeout (same as API)
        success = reset_port_poe(ssh_config, target_port, timeout)
        
        if success:
            print(f"✅ {location} - Port ge-0/0/{target_port} reset successfully")
            return True
        else:
            # Perform SSH connection diagnostics (same as API)
            diagnostics = analyze_ssh_error(ssh_config['hostname'], ssh_port, timeout)
            
            # Determine error type based on diagnostics (same error handling as API)
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
        # Handle unexpected errors (similar to API error handling)
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


def check_and_reset_down_ports(timeout=10):
    """
    Check all ports and reset only those that are down
    
    Args:
        timeout (int): Connection timeout in seconds for ping and SSH operations
        
    Returns:
        dict: Summary of operations with success/failure counts
    """
    print("=" * 60)
    print("🚀 SSHAutomation - Reset Down Ports Only")
    print("=" * 60)
    
    # Load environment variables first (same as API logic)
    load_dotenv()
    
    # Check if SSH credentials are available (same validation as API)
    ssh_username = os.getenv('SSH_USERNAME')
    ssh_password = os.getenv('SSH_PASSWORD')
    
    if not ssh_username or not ssh_password:
        print("❌ SSH credentials not configured!")
        print("Please set SSH_USERNAME and SSH_PASSWORD in .env file")
        return {'success': 0, 'failed': 0, 'error': 'SSH credentials not configured'}
    
    # Get all locations from configuration using same pattern as API
    locations, df_clean = get_all_locations()
    
    if not locations or df_clean is None:
        print("❌ No locations found to check")
        return {'success': 0, 'failed': 0, 'error': 'No locations found'}
    
    print(f"\n📋 Found {len(locations)} locations to check")
    print("=" * 60)
    
    # Track results
    total_checked = len(locations)
    reachable_locations = []
    unreachable_locations = []
    reset_attempted = []
    reset_successful = []
    reset_failed = []
    
    # Check each location
    for i, location in enumerate(locations, 1):
        print(f"\n[{i}/{len(locations)}] Processing: {location}")
        
        try:
            # Get the IP for this location
            location_data = df_clean[df_clean['Location'] == location]
            if location_data.empty:
                print(f"⚠️ No data found for location: {location}")
                continue
            
            ip_address = location_data['IP'].iloc[0]
            ip_address = str(ip_address).strip()
            
            # Ping the IP address
            is_reachable = ping_host(ip_address, timeout)
            
            if is_reachable:
                # IP is reachable - no action needed
                reachable_locations.append({
                    'location': location, 
                    'ip': ip_address,
                    'status': 'reachable'
                })
                print(f"✅ {location} is reachable - no reset needed")
            else:
                # IP is not reachable - attempt port reset
                unreachable_locations.append({
                    'location': location, 
                    'ip': ip_address,
                    'status': 'unreachable'
                })
                
                print(f"🔧 {location} is unreachable - attempting port reset...")
                
                # Attempt SSH reset
                reset_attempted.append({
                    'location': location,
                    'ip': ip_address
                })
                
                success = reset_single_location(location, timeout)
                
                if success:
                    reset_successful.append({
                        'location': location,
                        'ip': ip_address,
                        'status': 'reset_successful'
                    })
                else:
                    reset_failed.append({
                        'location': location,
                        'ip': ip_address,
                        'error': 'Port reset failed'
                    })
        
        except Exception as e:
            print(f"❌ Error processing {location}: {str(e)}")
            reset_failed.append({
                'location': location,
                'error': f'Error during processing: {str(e)}'
            })
        
        # Small delay between operations to prevent overwhelming switches
        if i < len(locations):
            print("⏳ Waiting 2 seconds before next check...")
            time.sleep(2)
    
    # Summary with consistent messaging
    print("\n" + "=" * 60)
    print("📊 CHECK AND RESET SUMMARY")
    print("=" * 60)
    print(f"📋 Total checked: {total_checked}")
    print(f"✅ Reachable (no action): {len(reachable_locations)}")
    print(f"❌ Unreachable: {len(unreachable_locations)}")
    print(f"🔧 Reset attempted: {len(reset_attempted)}")
    print(f"✅ Reset successful: {len(reset_successful)}")
    print(f"❌ Reset failed: {len(reset_failed)}")
    
    if reachable_locations:
        print(f"\n📍 Reachable locations: {', '.join([loc['location'] for loc in reachable_locations])}")
    
    if unreachable_locations:
        print(f"\n📍 Unreachable locations: {', '.join([loc['location'] for loc in unreachable_locations])}")
    
    if reset_successful:
        print(f"\n✅ Successfully reset: {', '.join([loc['location'] for loc in reset_successful])}")
    
    if reset_failed:
        print(f"\n❌ Failed to reset: {', '.join([loc['location'] for loc in reset_failed])}")
    
    print("=" * 60)
    print("🏁 Check and reset operation completed!")
    
    return {
        'total_checked': total_checked,
        'reachable': len(reachable_locations),
        'unreachable': len(unreachable_locations),
        'reset_attempted': len(reset_attempted),
        'reset_successful': len(reset_successful),
        'reset_failed': len(reset_failed),
        'reachable_locations': reachable_locations,
        'unreachable_locations': unreachable_locations,
        'reset_successful_locations': reset_successful,
        'reset_failed_locations': reset_failed
    }


def main():
    """
    Main function to execute check and reset operations
    """
    try:
        # Execute check and reset operation
        result = check_and_reset_down_ports()
        
        # Exit with appropriate code
        if result.get('error'):
            sys.exit(1)
        elif result['reset_failed'] > 0:
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
