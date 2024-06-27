import psutil
import pandas as pd
import json
from datetime import datetime, timedelta
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import xlsxwriter

# Placeholder data (replace with actual data or functions)


license_cost_data_file = 'license_cost_data.json'

# Placeholder constants for power consumption and emissions factor
CPU_POWER_CONSUMPTION_W = 50  # Watts
MEMORY_POWER_CONSUMPTION_W_PER_GB = 5  # Watts per GB
EMISSIONS_FACTOR_KG_CO2_PER_KWH = 0.475  # Average emissions factor

# Initialize the SQLite database
conn = sqlite3.connect('process_monitor.db')
c = conn.cursor()

# Create tables
c.execute('''
    CREATE TABLE IF NOT EXISTS processes (
        id INTEGER PRIMARY KEY,
        pid INTEGER,
        name TEXT,
        memory_usage REAL,
        num_threads INTEGER,
        cpu_usage REAL,
        carbon_footprint REAL,
        license_cost REAL,
        sustainability_rating INTEGER,
        create_time TEXT,
        username TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS hourly_data (
        id INTEGER PRIMARY KEY,
        hour TEXT,
        avg_memory_usage REAL,
        avg_cpu_usage REAL,
        total_carbon_footprint REAL
    )
''')

conn.commit()

def load_license_cost_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def monitor_processes():
    current_time = datetime.now()
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'num_threads', 'cpu_percent', 'create_time', 'username']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            mem = proc.info['memory_info'].rss / (1024 ** 2)  # Memory in MB
            num_threads = proc.info['num_threads']
            cpu_percent = proc.info['cpu_percent'] / psutil.cpu_count()  # Average CPU usage across all cores
            create_time = datetime.fromtimestamp(proc.info['create_time'])
            username = proc.info.get('username', 'N/A')
            
            carbon_footprint = get_carbon_footprint(name,cpu_percent,mem)
            license_cost = get_license_cost(name)
            sustainability_rating = calculate_sustainability_rating(name, mem, num_threads)

            c.execute('''
                INSERT INTO processes (pid, name, memory_usage, num_threads, cpu_usage, carbon_footprint, license_cost, sustainability_rating, create_time, username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pid, name, mem, num_threads, cpu_percent, carbon_footprint, license_cost, sustainability_rating, create_time, username))
            conn.commit()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def get_carbon_footprint(process_name, avg_cpu_percent, avg_memory_usage_mb):
    # Estimate power consumption
    cpu_power_consumption = (avg_cpu_percent / 100) * CPU_POWER_CONSUMPTION_W
    memory_power_consumption = (avg_memory_usage_mb / 1024) * MEMORY_POWER_CONSUMPTION_W_PER_GB
    total_power_consumption_w = cpu_power_consumption + memory_power_consumption

    # Convert power consumption to energy consumption (kWh)
    # Assuming monitoring interval is 1 hour for simplicity
    energy_consumption_kwh = total_power_consumption_w / 1000

    # Convert energy consumption to carbon footprint
    carbon_footprint_kg = energy_consumption_kwh * EMISSIONS_FACTOR_KG_CO2_PER_KWH
    return carbon_footprint_kg

def get_license_cost(process_name):
    # Load license cost data from JSON file
    license_cost_data = load_license_cost_data(license_cost_data_file)
    return license_cost_data.get(process_name, 0.0)

def calculate_sustainability_rating(process_name, avg_memory_usage_mb, num_threads):
    # Example sustainability rating calculation based on memory usage and thread count
    sustainability_score = 0
    if avg_memory_usage_mb < 500:
        sustainability_score += 1
    if num_threads < 10:
        sustainability_score += 1
    
    return sustainability_score

def update_ui():
    monitor_processes()
    for row in tree.get_children():
        tree.delete(row)

    # Retrieve top 20 processes by average memory usage
    c.execute('''
        SELECT name, memory_usage, num_threads, cpu_usage, carbon_footprint, license_cost, sustainability_rating, create_time, username
        FROM processes
        GROUP BY name
        ORDER BY AVG(memory_usage) DESC
        LIMIT 20
    ''')
    top_processes = c.fetchall()
    
    for row in top_processes:
        tree.insert("", "end", values=row)

    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S')
    avg_memory_usage = sum(row[1] for row in top_processes) / len(top_processes)
    avg_cpu_usage = sum(row[3] for row in top_processes) / len(top_processes)  # Average CPU usage across all processes

    c.execute('''
        INSERT INTO hourly_data (hour, avg_memory_usage, avg_cpu_usage)
        VALUES (?, ?, ?)
    ''', (current_hour, avg_memory_usage, avg_cpu_usage))
    conn.commit()

    root.after(60000, update_ui)

def refresh_data():
    # Manually refresh data when the button is pressed
    update_ui()

def check_unused_license_cost():
    # Check for processes not run in the last 60 days and incurring license costs
    cutoff_date = datetime.now() - timedelta(days=60)
    c.execute('''
        SELECT name, license_cost
        FROM processes
        WHERE create_time <= ?
        AND license_cost > 0
    ''', (cutoff_date,))
    unused_license_cost_processes = c.fetchall()

    if unused_license_cost_processes:
        # Create a message with process names and license costs
        message = "Processes not run in the last 60 days and incurring license costs:\n\n"
        for process in unused_license_cost_processes:
            message += f"{process[0]} - License Cost: ${process[1]}\n"

        # Show popup message box with the results
        messagebox.showinfo("Unused License Cost Processes", message)
    else:
        messagebox.showinfo("Unused License Cost Processes", "No processes found not run in the last 60 days and incurring license costs.")


def show_hourly_analytics():
    # Retrieve hourly data
    c.execute('SELECT hour, avg_memory_usage, avg_cpu_usage FROM hourly_data ORDER BY hour')
    data = c.fetchall()

    hours = [row[0] for row in data]
    avg_memory_usage = [row[1] for row in data]
    avg_cpu_usage = [row[2] for row in data]

    # Plot the data
    plt.figure(figsize=(10, 6))
    plt.plot(hours, avg_memory_usage, marker='o', label='Average Memory Usage (MB)')
    plt.plot(hours, avg_cpu_usage, marker='o', label='Average CPU Usage (%)')
    plt.xlabel('Time')
    plt.ylabel('Usage')
    plt.title('Hourly Analytics - Memory and CPU Usage')
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def kill_process():
    # Get the selected process from the Treeview
    selected_item = tree.selection()
    if selected_item:
        item = tree.item(selected_item)
        pid = item['values'][-1]  # Assuming the last value is the PID in your Treeview setup

        try:
            process = psutil.Process(pid)
            process.terminate()  # Terminate the process
            messagebox.showinfo("Process Terminated", f"Process with PID {pid} has been terminated successfully.")
        except psutil.NoSuchProcess:
            messagebox.showerror("Error", f"Process with PID {pid} does not exist or has already been terminated.")
    else:
        messagebox.showwarning("No Process Selected", "Please select a process from the list.")

def export_to_excel():
    # Retrieve all process data
    c.execute('''
        SELECT name, memory_usage, num_threads, cpu_usage, carbon_footprint, license_cost, sustainability_rating, create_time, username
        FROM processes
        ORDER BY create_time DESC
    ''')
    data = c.fetchall()

    # Create a Pandas DataFrame from the retrieved data
    df = pd.DataFrame(data, columns=["Process Name", "Memory Usage (MB)", "Thread Count", "CPU Usage (%)", "Carbon Footprint (kg CO2)", "License Cost ($)", "Sustainability Rating", "Creation Time", "Username"])

    # Create a Pandas Excel writer using XlsxWriter as the engine
    excel_filename = 'process_data.xlsx'
    writer = pd.ExcelWriter(excel_filename, engine='xlsxwriter')

    # Convert the dataframe to an XlsxWriter Excel object
    df.to_excel(writer, sheet_name='Process Data', index=False)

    # Close the Pandas Excel writer and output the Excel file
    writer.save()

    messagebox.showinfo("Export to Excel", f"Process data exported successfully to {excel_filename}.")

# Create the main window
root = tk.Tk()
root.title("Process Monitor")

# Adjust font size to fit the screen
style = ttk.Style()
style.configure('Treeview', font=('Arial', 12))  # Adjust font and size as needed

# Create and pack the Treeview widget
columns = ("Process Name", "Memory Usage (MB)", "Thread Count", "CPU Usage (%)", "Carbon Footprint (kg CO2)", "License Cost ($)", "Sustainability Rating", "Creation Time", "Username")
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.pack(fill=tk.BOTH, expand=True)

for col in columns:
    tree.heading(col, text=col)

# Create and pack the Refresh button
refresh_button = tk.Button(root, text="Refresh", command=refresh_data)
refresh_button.pack(pady=10)

# Create and pack the Show Analytics button
analytics_button = tk.Button(root, text="Show Hourly Analytics", command=show_hourly_analytics)
analytics_button.pack(pady=10)

# Create and pack the Check Unused License Cost button
check_license_button = tk.Button(root, text="Check Unused License Cost", command=check_unused_license_cost)
check_license_button.pack(pady=10)

# Create and pack the Kill Process button
kill_process_button = tk.Button(root, text="Kill Process", command=kill_process)
kill_process_button.pack(pady=10)

# Create and pack the Export to Excel button
export_excel_button = tk.Button(root, text="Export to Excel", command=export_to_excel)
export_excel_button.pack(pady=10)

# Initial UI update
update_ui()

# Start the Tkinter main loop
root.mainloop()

# Close the database connection when the application closes
def on_closing():
    conn.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
