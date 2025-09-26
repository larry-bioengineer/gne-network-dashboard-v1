import paramiko
import os
import sys
import socket
from dotenv import load_dotenv
import time



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

def retrieve_ssh_info_from_config(ip):
    print(f"Retrieving port from config for {ip}")

    return {
        "hostname": "10.1.1.2",
        "port": 22,
        "target_port": 16
    }




