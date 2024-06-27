import psutil
import pandas as pd
import json
from datetime import datetime, timedelta
import sqlite3
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt

# Load datasets
#carbon_footprint_data = pd.read_csv('carbon_footprint_data.csv')
with open('license_cost_data.json') as f:
    license_cost_data = json.load(f)

# Convert to dictionary for faster lookups
#carbon_footprint_dict = dict(zip(carbon_footprint_data['process_name'], carbon_footprint_data['carbon_footprint_per_mb']))

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
        cpu_percent REAL,
        memory_usage REAL,
        disk_read INTEGER,
        disk_write INTEGER,
        num_threads INTEGER,
        carbon_footprint REAL,
        license_cost REAL,
        last_used TEXT,
        create_time TEXT,
        username TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS hourly_data (
        id INTEGER PRIMARY KEY,
        hour TEXT,
        avg_memory_usage REAL,
        total_carbon_footprint REAL
    )
''')

conn.commit()

def monitor_processes():
    current_time = datetime.now()
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'io_counters', 'num_threads', 'create_time', 'username']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            cpu_percent = proc.info['cpu_percent']
            mem = proc.info['memory_info'].rss / (1024 ** 2)  # Memory in MB
            io_counters = proc.info.get('io_counters', None)
            disk_read = io_counters.read_bytes if io_counters else 0
            disk_write = io_counters.write_bytes if io_counters else 0
            num_threads = proc.info['num_threads']
            create_time = datetime.fromtimestamp(proc.info['create_time'])
            username = proc.info.get('username', 'N/A')
            last_used = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            carbon_footprint = get_carbon_footprint(name, cpu_percent, mem)
            license_cost = get_license_cost(name)

            c.execute('''
                INSERT INTO processes (pid, name, cpu_percent, memory_usage, disk_read, disk_write, num_threads, carbon_footprint, license_cost, last_used, create_time, username)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (pid, name, cpu_percent, mem, disk_read, disk_write, num_threads, carbon_footprint, license_cost, last_used, create_time, username))
            conn.commit()

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def get_carbon_footprint(process_name, avg_cpu_percent, avg_memory_usage_mb):
    # Estimate power consumption
    cpu_power_consumption = (avg_cpu_percent / 100) * CPU_POWER_CONSUMPTION_W
    memory_power_consumption = (avg_memory_usage_mb / 1024) * MEMORY_POWER_CONSUMPTION_W_PER_GB
    total_power_consumption_w = cpu_power_consumption + memory_power_consumption

    # Convert power consumption to energy consumption (kWh)
    energy_consumption_kwh = total_power_consumption_w / 1000

    # Convert energy consumption to carbon footprint
    carbon_footprint_kg = energy_consumption_kwh * EMISSIONS_FACTOR_KG_CO2_PER_KWH
    return carbon_footprint_kg

def get_license_cost(process_name):
    return license_cost_data.get(process_name, 0.0)

def update_ui():
    monitor_processes()
    for row in tree.get_children():
        tree.delete(row)

    # Retrieve top 20 processes by average memory usage
    c.execute('''
        SELECT name, AVG(memory_usage), AVG(cpu_percent), SUM(disk_read), SUM(disk_write), AVG(num_threads), AVG(carbon_footprint), license_cost, MAX(last_used), create_time, username
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
    total_carbon_footprint = sum(row[6] for row in top_processes)

    c.execute('''
        INSERT INTO hourly_data (hour, avg_memory_usage, total_carbon_footprint)
        VALUES (?, ?, ?)
    ''', (current_hour, avg_memory_usage, total_carbon_footprint))
    conn.commit()

    root.after(60, update_ui)

def refresh_data():
    # Manually refresh data when the button is pressed
    update_ui()

def show_hourly_analytics():
    # Retrieve hourly data
    c.execute('SELECT hour, avg_memory_usage, total_carbon_footprint FROM hourly_data ORDER BY hour')
    data = c.fetchall()

    hours = [row[0] for row in data]
    avg_memory_usage = [row[1] for row in data]
    total_carbon_footprint = [row[2] for row in data]

    # Plot the data
    fig, ax1 = plt.subplots()

    color = 'tab:blue'
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Average Memory Usage (MB)', color=color)
    ax1.plot(hours, avg_memory_usage, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Total Carbon Footprint (kg CO2)', color=color)
    ax2.plot(hours, total_carbon_footprint, color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()
    plt.show()

# Create the main window
root = tk.Tk()
root.title("Process Monitor")

# Create and pack the Treeview widget
columns = ("Process Name", "Memory Usage (MB)", "CPU Usage (%)", "Disk Read (Bytes)", "Disk Write (Bytes)", "Thread Count", "Carbon Footprint (kg CO2)", "License Cost ($)", "Last Used", "Creation Time", "Username")
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

# Initial UI update
update_ui()

# Start the Tkinter main loop
root.mainloop()

# Close the database connection when the application closes
def on_closing():
    conn.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
