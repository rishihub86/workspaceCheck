import psutil
import pandas as pd
import json
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from collections import defaultdict

# Load datasets
with open('license_cost_data.json') as f:
    license_cost_data = json.load(f)

# Placeholder constants for power consumption and emissions factor
CPU_POWER_CONSUMPTION_W = 50  # Watts
MEMORY_POWER_CONSUMPTION_W_PER_GB = 5  # Watts per GB
EMISSIONS_FACTOR_KG_CO2_PER_KWH = 0.475  # Average emissions factor

# Initialize data structures
process_usage = {}
hourly_data = defaultdict(lambda: {'memory_usage': [], 'carbon_footprint': []})

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

            if name not in process_usage:
                process_usage[name] = {'pid': pid, 'last_used': current_time, 'mem_usage': [], 'cpu_usage': [], 'disk_read': [], 'disk_write': [], 'num_threads': [], 'create_time': create_time, 'username': username}
            process_usage[name]['last_used'] = current_time
            process_usage[name]['mem_usage'].append((current_time, mem))
            process_usage[name]['cpu_usage'].append((current_time, cpu_percent))
            process_usage[name]['disk_read'].append((current_time, disk_read))
            process_usage[name]['disk_write'].append((current_time, disk_write))
            process_usage[name]['num_threads'].append((current_time, num_threads))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def remove_unused_processes(threshold_days=30):
    current_time = datetime.now()
    unused_processes = []
    for name, info in process_usage.items():
        if current_time - info['last_used'] > timedelta(days=threshold_days):
            unused_processes.append(name)
    for name in unused_processes:
        del process_usage[name]

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
    return license_cost_data.get(process_name, 0.0)

def update_ui():
    monitor_processes()
    for row in tree.get_children():
        tree.delete(row)

    # Sort processes by average memory usage and select the top 20
    top_processes = sorted(process_usage.items(), key=lambda item: sum([mem for _, mem in item[1]['mem_usage']]) / len(item[1]['mem_usage']), reverse=True)[:20]
    
    for name, info in top_processes:
        avg_memory_usage = sum([mem for _, mem in info['mem_usage']]) / len(info['mem_usage'])
        avg_cpu_usage = sum([cpu for _, cpu in info['cpu_usage']]) / len(info['cpu_usage'])
        total_disk_read = sum([read for _, read in info['disk_read']])
        total_disk_write = sum([write for _, write in info['disk_write']])
        avg_threads = sum([threads for _, threads in info['num_threads']]) / len(info['num_threads'])
        carbon_footprint = get_carbon_footprint(name, avg_cpu_usage, avg_memory_usage)
        license_cost = get_license_cost(name)
        last_used = info['last_used'].strftime('%Y-%m-%d %H:%M:%S')
        
        tree.insert("", "end", values=(name, avg_memory_usage, avg_cpu_usage, total_disk_read, total_disk_write, avg_threads, carbon_footprint, license_cost, last_used, info['create_time'].strftime('%Y-%m-%d %H:%M:%S'), info['username']))
    
    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    hourly_data[current_hour]['memory_usage'].append(avg_memory_usage)
    hourly_data[current_hour]['carbon_footprint'].append(carbon_footprint)
    
    root.after(5, update_ui)

def refresh_data():
    # Manually refresh data when the button is pressed
    update_ui()

def show_hourly_analytics():
    # Calculate hourly averages
    hours = sorted(hourly_data.keys())
    avg_memory_usage = [sum(hourly_data[hour]['memory_usage']) / len(hourly_data[hour]['memory_usage']) for hour in hours]
    total_carbon_footprint = [sum(hourly_data[hour]['carbon_footprint']) for hour in hours]

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
