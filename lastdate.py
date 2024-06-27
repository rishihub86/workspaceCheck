import wmi
import datetime

def get_last_execution_time(process_name):
    try:
        # Connect to the WMI service
        c = wmi.WMI()

        # Query for processes matching the process name
        for process in c.Win32_Process(name=process_name):
            last_execution_time = process.CreationDate.split('.')[0]  # Remove microseconds
            last_execution_time = datetime.datetime.strptime(last_execution_time, "%Y%m%d%H%M%S")
            return last_execution_time
    except Exception as e:
        print(f"Error accessing WMI: {e}")
        return None

# Replace with the process name of the software you're interested in
process_name = "notepad.exe"

last_execution_time = get_last_execution_time(process_name)

if last_execution_time:
    print(f"The last execution time of {process_name} was: {last_execution_time}")
else:
    print(f"Could not find {process_name} running.")
