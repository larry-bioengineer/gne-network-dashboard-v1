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

    # read the data.xlsx file
    df = pd.read_excel('config_file/data.xlsx', sheet_name='Port assignment')

    return render_template('config_edit.html', df=df.to_dict(orient='records'))

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
