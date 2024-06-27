import winreg
import datetime

def get_last_used_date(software_name):
    try:
        # Open the registry key
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\RecentDocs"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        
        # Iterate through the subkeys
        for i in range(0, winreg.QueryInfoKey(key)[0]):
            subkey_name = winreg.EnumKey(key, i)
            subkey_path = f"{key_path}\\{subkey_name}"
            subkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey_path, 0, winreg.KEY_READ)
            
            for j in range(0, winreg.QueryInfoKey(subkey)[1]):
                value_name, value_data, value_type = winreg.EnumValue(subkey, j)
                if software_name.lower() in value_name.lower():
                    timestamp = int(value_data)
                    last_used_date = datetime.datetime.fromtimestamp(timestamp)
                    return last_used_date
                
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Error accessing the registry: {e}")
        return None

software_name = "notepad"  # Replace with the software name you're looking for
last_used_date = get_last_used_date(software_name)

if last_used_date:
    print(f"The last used date of {software_name} is: {last_used_date}")
else:
    print(f"Could not find the last used date for {software_name}.")
