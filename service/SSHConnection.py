import paramiko
import os
import sys
import socket
from dotenv import load_dotenv
import time
import pandas as pd
import re


def extract_ip_address(text):
    """
    Extract IP address from text using a robust detection method.
    Handles various formats like:
    - "BOA1FPOE2 10.12.0.5"
    - "Switch-01 192.168.1.100"
    - "10.12.0.5" (IP only)
    - "10.12.0.5:22" (IP with port)
    - Multiple IPs (returns first valid IPv4)
    
    Args:
        text: String that may contain an IP address
        
    Returns:
        str: The first valid IPv4 address found
        
    Raises:
        ValueError: If no valid IP address is found or text is empty
    """
    if not text or pd.isna(text):
        raise ValueError("Empty or None IP address value")
    
    # Convert to string if not already
    text = str(text).strip()
    
    # Regular expression for IPv4 addresses with improved pattern
    # This pattern handles IPs in various contexts and formats
    ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    
    # Find all IPv4 addresses in the text
    ip_matches = re.findall(ipv4_pattern, text)
    
    if not ip_matches:
        # Try a more flexible approach - look for IP patterns even without word boundaries
        flexible_pattern = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
        ip_matches = re.findall(flexible_pattern, text)
        
    if not ip_matches:
        raise ValueError(f"No valid IP address found in: {text}")
    
    # Use the first match found
    first_ip = ip_matches[0]
    
    # Additional validation - verify it's a properly formatted IP using socket
    try:
        socket.inet_aton(first_ip)
        return first_ip
    except socket.error:
        raise ValueError(f"Invalid IP address format: {first_ip}")


def connect_ssh(config, timeout=10):
    """
    Connect to SSH server and execute port reset commands
    """
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        
        # Automatically add the server's host key
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Connecting to {config['hostname']}:{config['port']} with {timeout}s timeout...")
        
        # Connect to the server with timeout
        ssh.connect(
            hostname=config['hostname'],
            port=config['port'],
            username=config['username'],
            password=config['password'],
            timeout=timeout
        )
        
        print("Connected successfully!")
        
        # List of commands to execute
        commands = [
            'configure',
            'edit interfaces ge-0/0/16 unit 0',
            'set description larry-test',
            'commit',
            'exit',
            'exit',
        ]
        
        print("\n--- Executing Port Reset Commands ---")
        
        # Create an interactive shell session
        shell = ssh.invoke_shell()
        time.sleep(2)  # Wait for shell to initialize
        
        # Execute commands in sequence
        for i, command in enumerate(commands, 1):
            print(f"\n[{i}/{len(commands)}] Executing: {command}")
            
            # Send command
            shell.send(command + '\n')
            time.sleep(2)  # Wait for command to complete
            
            # Read output
            if shell.recv_ready():
                output = shell.recv(4096).decode('utf-8')
                print(f"Output: {output}")
        
        # Close the shell
        shell.close()
        
        
        # Final status check
        print("\n--- Final Status Check ---")
        stdin, stdout, stderr = ssh.exec_command('show interfaces brief')
        output = stdout.read().decode('utf-8').strip()
        if output:
            print(output)
        
        # Close the connection
        ssh.close()
        print("\nConnection closed.")
        return True
        
    except paramiko.AuthenticationException:
        error_msg = "🔐 SSH Authentication failed. Please check your credentials in the .env file."
        print(error_msg)
        return False
    except paramiko.SSHException as e:
        error_msg = f"🔌 SSH Protocol error: {e}"
        print(error_msg)
        return False
    except socket.timeout:
        error_msg = f"⏱️  SSH CONNECTION TIMEOUT: Failed to connect to {config['hostname']}:{config['port']} within {timeout} seconds.\n" \
                   f"   This indicates a network connectivity issue. Please check:\n" \
                   f"   • Network connection to {config['hostname']}\n" \
                   f"   • Firewall settings blocking SSH (port {config['port']})\n" \
                   f"   • SSH service status on the target server\n" \
                   f"   • Consider increasing timeout if network is slow"
        print(error_msg)
        return False
    except ConnectionRefusedError:
        error_msg = f"🚫 SSH Connection refused: The server {config['hostname']}:{config['port']} is not accepting SSH connections.\n" \
                   f"   This indicates the SSH service is not running or not accessible. Please check:\n" \
                   f"   • SSH service is running on the target server\n" \
                   f"   • SSH is listening on port {config['port']}\n" \
                   f"   • Firewall is allowing SSH connections"
        print(error_msg)
        return False
    except socket.gaierror as e:
        error_msg = f"🌐 DNS/Hostname resolution failed: Cannot resolve {config['hostname']}.\n" \
                   f"   Please check:\n" \
                   f"   • Hostname/IP address is correct\n" \
                   f"   • DNS server configuration\n" \
                   f"   • Network connectivity"
        print(error_msg)
        return False
    except Exception as e:
        error_msg = f"❌ SSH Connection error: {e}"
        print(error_msg)
        return False

def reset_port_poe(config, port_number, timeout=10):
    """
    Reset a specific port by disabling and enabling PoE
    """
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        
        # Automatically add the server's host key
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"Connecting to {config['hostname']}:{config['port']} with {timeout}s timeout...")
        
        # Connect to the server with timeout
        ssh.connect(
            hostname=config['hostname'],
            port=config['port'],
            username=config['username'],
            password=config['password'],
            timeout=timeout
        )
        
        print("Connected successfully!")
        
        # Commands to disable PoE port
        disable_commands = [
            'edit',
            f'set poe interface ge-0/0/{port_number} disable',
            'commit'
        ]
        
        # Commands to enable PoE port
        enable_commands = [
            'edit',
            f'delete poe interface ge-0/0/{port_number} disable',
            'commit'
        ]
        
        print(f"\n--- Resetting Port ge-0/0/{port_number} ---")
        
        # Create an interactive shell session
        shell = ssh.invoke_shell()
        time.sleep(2)  # Wait for shell to initialize
        
        # Execute disable commands
        print("\n--- Disabling PoE Port ---")
        for i, command in enumerate(disable_commands, 1):
            print(f"[{i}/{len(disable_commands)}] Executing: {command}")
            shell.send(command + '\n')
            time.sleep(2)  # Wait for command to complete
            
            # Read output
            if shell.recv_ready():
                output = shell.recv(4096).decode('utf-8')
                print(f"Output: {output}")
        
        # Wait a bit before enabling
        time.sleep(3)
        
        # Execute enable commands
        print("\n--- Enabling PoE Port ---")
        for i, command in enumerate(enable_commands, 1):
            print(f"[{i}/{len(enable_commands)}] Executing: {command}")
            shell.send(command + '\n')
            time.sleep(2)  # Wait for command to complete
            
            # Read output
            if shell.recv_ready():
                output = shell.recv(4096).decode('utf-8')
                print(f"Output: {output}")
        
        # Close the shell
        shell.close()
        
        # Final status check
        print("\n--- Final Status Check ---")
        stdin, stdout, stderr = ssh.exec_command('show poe interface ge-0/0/' + str(port_number))
        output = stdout.read().decode('utf-8').strip()
        if output:
            print(output)
        
        # Close the connection
        ssh.close()
        print(f"\nPort ge-0/0/{port_number} reset completed successfully!")
        return True
        
    except paramiko.AuthenticationException:
        error_msg = "🔐 SSH Authentication failed. Please check your credentials in the .env file."
        print(error_msg)
        return False
    except paramiko.SSHException as e:
        error_msg = f"🔌 SSH Protocol error: {e}"
        print(error_msg)
        return False
    except socket.timeout:
        error_msg = f"⏱️  SSH CONNECTION TIMEOUT: Failed to connect to {config['hostname']}:{config['port']} within {timeout} seconds.\n" \
                   f"   This indicates a network connectivity issue. Please check:\n" \
                   f"   • Network connection to {config['hostname']}\n" \
                   f"   • Firewall settings blocking SSH (port {config['port']})\n" \
                   f"   • SSH service status on the target server\n" \
                   f"   • Consider increasing timeout if network is slow"
        print(error_msg)
        return False
    except ConnectionRefusedError:
        error_msg = f"🚫 SSH Connection refused: The server {config['hostname']}:{config['port']} is not accepting SSH connections.\n" \
                   f"   This indicates the SSH service is not running or not accessible. Please check:\n" \
                   f"   • SSH service is running on the target server\n" \
                   f"   • SSH is listening on port {config['port']}\n" \
                   f"   • Firewall is allowing SSH connections"
        print(error_msg)
        return False
    except socket.gaierror as e:
        error_msg = f"🌐 DNS/Hostname resolution failed: Cannot resolve {config['hostname']}.\n" \
                   f"   Please check:\n" \
                   f"   • Hostname/IP address is correct\n" \
                   f"   • DNS server configuration\n" \
                   f"   • Network connectivity"
        print(error_msg)
        return False
    except Exception as e:
        error_msg = f"❌ SSH Connection error: {e}"
        print(error_msg)
        return False

def main(hostname, username, password, port):
    """
    Main function to load config and execute port reset
    """
    print("Automated SSH Port Reset Script")
    print("=" * 40)

    config = {
        'hostname': hostname,
        'username': username,
        'password': password,
        'port': port
    }
    
    print(f"Configuration loaded:")
    print(f"  Host: {config['hostname']}")
    print(f"  Username: {config['username']}")
    print(f"  Port: {config['port']}")
    print()
    
    # Confirm before proceeding
    # confirm = input("Proceed with port reset? (y/n): ").lower().strip()
    # if confirm != 'y':
    #     print("Operation cancelled.")
    #     return
    
    # Execute port reset
    connect_ssh(config)

def retrieve_ssh_info_from_config(locName):
    """
        Match against data.xlsx > Port assignment sheet to find the relevant SSH IP and Switch port

        Param:
            locName: The location name to match against

        Return:
            hostname: The IP address of the network switch
            port: The SSH port of the network switch
            target_port: The port to reset
    """
    print(f"Retrieving port from config for {locName}")
    df = pd.read_excel('config_file/data.xlsx', sheet_name='Port assignment')
    df_clean = df.dropna(subset=['Location', 'SSH IP', 'Switch port'])
    location_data = df_clean[df_clean['Location'] == locName]
    if location_data.empty:
        return None
    
    # process IP as it may have additional strings (e.g. BOA1FPOE2 10.12.0.5)
    try:
        ip_raw = location_data['SSH IP'].iloc[0]
        ip = extract_ip_address(ip_raw)
    except ValueError as e:
        print(f"Error extracting IP address: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during IP extraction: {e}")
        return None
    
    # process switch port as only need the port number instead of the full port name
    switch_port = location_data['Switch port'].iloc[0]
    switch_port = switch_port.split('/')[-1]

    print("SSH INFO:")
    print({
        "locName": locName,
        "hostname": ip,
        "port": 22,
        "target_port": switch_port
    })

    return {
        "hostname": ip,
        "port": 22,
        "target_port": switch_port
    }




