from flask import Flask, redirect, render_template
import os
import dotenv
from api.routes import api_bp

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

if __name__ == '__main__':
    # check if config_file/data.xlsx exists
    if not os.path.exists('config_file/data.xlsx'):
        print('config_file/data.xlsx does not exist')
        exit()

    
    app.run(
        debug=True,
        port=os.getenv('SERVER_PORT')
        )
