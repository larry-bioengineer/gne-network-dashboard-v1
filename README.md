# SSH Automation Server

A Flask-based web application for automated SSH management of network switches, enabling port resets, connectivity tests, and network diagnostics.

## System Requirements

- **Python 3.8 or higher**
- **Windows 10/11** (for batch file support)
- **Internet connection** (for dependency downloads)
- **Excel 2007+** (for data file support)

## Quick Start

### Option 1: Using the Automated Setup

1. Download Python [here](https://www.python.org/downloads/)
2. Download Git [here](https://git-scm.com/downloads)

2. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd SSH-Automation-Server
   ```

3. **Run the automated setup:**

   - **On Windows:** Double-click `START_ME.bat`
   - **On macOS/Linux:** Open a terminal and run:
     ```bash
     bash START_ME.sh
     ```
   - The script will automatically check dependencies and start the server


### Option 2: Manual Setup

#### 1. Create Virtual Environment

```bash
python -m venv venv
```

#### Windows:
```bash
venv\Scripts\activate
```

#### macOS/Linux:
```bash
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables

Create a `.env` file in the project root with your SSH credentials:

```env
SSH_USERNAME=your_ssh_username
SSH_PASSWORD=your_ssh_password
BATCH_VERIFICATION_DELAY_SECONDS=30
```

### Optional Environment Variables

- **`BATCH_VERIFICATION_DELAY_SECONDS`** (default: 30) - Delay in seconds after all port resets before batch verification
- **`SLEEP_DURATION_BEFORE_ENABLE_IN_SECOND`** (default: 2) - Delay between disabling and enabling PoE ports

#### 4. Prepare Configuration File

Ensure you have `config_file/data.xlsx` with the following structure:
- Sheet: `Hardware list`
- Required columns:
  - `Location` - descriptive name of the location
  - `IP` - IP address of the network switch

#### 5. Start the Server

```bash
python main.py
```

The server will be available at **http://127.0.0.1:5000**

## Required Files

The application requires these files to run:

### Essential Files

1. **`config_file/data.xlsx`** (MANDATORY)
   - Contains network location and IP mappings
   - Must have `Hardware list` sheet
   - Must include `Location` and `IP` columns

2. **`.env`** (Optional)
   - SSH credentials for switch authentication
   - Create for enhanced features

### Configuration Files

- **`.env`** - Environment variables
- **`config_file/data.xlsx`** - Network devices configuration

#### Network devices configuration
Inside the `config_file/` directory, there is an `example.xlsx` detailing the format for the xlsx file. You must follow the format to create a new file named `data.xlsx`. An error will return if such a file doesn't exist when you try running `START_ME`

## Installation Troubleshooting

### Common Issues

#### "config_file/data.xlsx does not exist"
- Create the file path `config_file/data.xlsx`
- Add your network device data with `Location` and `IP` columns

#### Virtual Environment Errors
```bash
# Windows
venv\Scripts\python -m pip install --upgrade pip
pip install -r requirements.txt
```

```bash
# macOS/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Port Already in Use
- Change the port in `main.py`:
  ```python
  app.run(debug=True, port=5001)  # Change to different port
  ```

#### SSH Connection Issues
- Verify credentials in `.env` file
- Check network connectivity to target devices
- Ensure SSH service is running on target switches

## Running the Application

### Development Mode
```bash
python main.py
```

### Production Deployment
1. Set `debug=False` in `main.py`
2. Configure production WSGI server (e.g., Gunicorn)
3. Set up reverse proxy if needed

## Features

- **Network Diagnostics**: Ping tests for network connectivity
- **Port Management**: Automated SSH port resets with verification
- **Batch Port Verification**: Automatic connectivity verification after all port resets are completed
- **Location-Based Operations**: Interface with network devices by location
- **Real-time Updates**: Live connectivity monitoring
- **Web Dashboard**: User-friendly interface for all operations

## File Structure

```
SSH Automation Server/
├── api/                    # API endpoints
│   ├── models.py          # Data models
│   └── routes.py          # HTTP routes
├── config_file/           # Configuration data
│   ├── data.xlsx          # Network hardware list
│   └── example.xlsx       # Configuration template
├── service/               # Core services
│   └── SSHConnection.py   # SSH automation logic
├── templates/             # Web templates
│   └── dashboard.html     # Main dashboard
├── static/                # Static assets
│   ├── js/               # JavaScript files
│   └── style/            # CSS files
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── START_ME.bat          # Quick start script
```

## Dashboard Access

Navigate to:
- **http://127.0.0.1:5000** - Main dashboard
- **http://127.0.0.1:5000/dashboard** - Direct dashboard access
- **http://127.0.0.1:5000/api/admin/health** - Health check API

## Stopping the Application

### Development (Local)
- Press `Ctrl+C` in the terminal running the server

### Windows Batch File
- Close the command window that opened automatically
- Or terminate `python.exe` processes in Task Manager

## Security Notes

- Change default SSH credentials immediately
- Store `.env` file securely and keep it private
- Use strong passwords for SSH authentication
- Consider using SSH keys instead of passwords for production

## Need Help?

Common solution paths:
1. Check that all required files exist
2. Verify virtual environment is activated
3. Ensure dependencies are installed (`pip install -r requirements.txt`)
4. Check `config_file/data.xlsx` format matches requirements
5. Verify `.env` file has correct SSH credentials
