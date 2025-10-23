from flask import Flask, redirect, render_template, jsonify
import os
import dotenv
from api.routes import api_bp
import pandas as pd
dotenv.load_dotenv()

app = Flask(__name__)

# Register the API blueprint
app.register_blueprint(api_bp)

@app.route('/')
def home():
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/automation')
def automation():
    return render_template('automation.html')

@app.route('/config_edit')
def config_edit():

    # read both sheets from the data.xlsx file
    hardware_df = pd.read_excel('config_file/data.xlsx', sheet_name='Hardware list')
    port_df = pd.read_excel('config_file/data.xlsx', sheet_name='Port assignment')
    
    # Filter out device name columns from port data
    device_name_columns = ['Unnamed: 0', 'Device Name', 'Device', 'Name', 'Hostname']
    columns_to_drop = [col for col in device_name_columns if col in port_df.columns]
    if columns_to_drop:
        port_df = port_df.drop(columns=columns_to_drop)

    return render_template('config_edit.html', 
                         hardware_data=hardware_df.to_dict(orient='records'),
                         port_data=port_df.to_dict(orient='records'))

if __name__ == '__main__':
    # check if config_file/data.xlsx exists
    if not os.path.exists('config_file/data.xlsx'):
        print('config_file/data.xlsx does not exist')
        exit()

    
    app.run(
        debug=True,
        port=int(os.getenv('SERVER_PORT', 5000)),
        threaded=True
        )
