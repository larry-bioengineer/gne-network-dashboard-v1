"""
This module is used for logging the events of the API.

"""
import datetime
import os

# This method log incoming text to a log file. If the log file does not exist, it will be created. The log file will be created by day
def log_to_file(text, level='INFO'):
    """
        Log Format:
        [YYYY-MM-DD HH:MM:SS] [LEVEL] [MESSAGE]

        Args:
            text: The text to log
            level: The level of the log (INFO, WARNING, ERROR)

    """
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] [{level}] {text}"

    # Check if the log file for the day exists. If not, create it.
    log_file = f'Log/log_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt'
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write('')

    with open(log_file, 'a') as f:
        f.write(log_message + '\n')

    return "Success"