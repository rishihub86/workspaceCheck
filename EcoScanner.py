import asyncio
import aiofiles
import psutil
import pandas as pd
import json
from datetime import datetime, timedelta
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

# In-memory data storage
process_data = {}
hourly_data = {}
sustainability_hourly_data = {}

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

            # Calculate carbon footprint and license cost
            carbon_footprint = get_carbon_footprint(name,cpu_percent, mem)
            license_cost = get_license_cost(name)
            sustainability_rating = calculate_sustainability_rating(name, mem, num_threads)

            process_data[pid] = {
                'name': name,
                'memory_usage': mem,
                'num_threads': num_threads,
                'cpu_usage': cpu_percent,
                'carbon_footprint': carbon_footprint,
                'license_cost': license_cost,
                'sustainability_rating': sustainability_rating,
                'last_execution_time': current_time,
                'create_time': create_time,
                'username': username
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def load_license_cost_data(filename):
    with open(filename, 'r') as f:
        return json.load(f)

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
    sustainability_score = 0
    if avg_memory_usage_mb < 500:
        sustainability_score += 1
    if num_threads < 10:
        sustainability_score += 1
    return sustainability_score

def update_ui():
    monitor_processes()
    tree.delete(*tree.get_children())

    # Retrieve top 20 processes by average memory usage
    top_processes = sorted(process_data.values(), key=lambda x: x['memory_usage'], reverse=True)[:20]
    
    for proc in top_processes:
        tree.insert("", "end", values=(proc['name'], proc['memory_usage'], proc['num_threads'], proc['cpu_usage'], proc['carbon_footprint'], proc['license_cost'], proc['sustainability_rating'], proc['last_execution_time'], proc['username']))

    current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    avg_memory_usage = sum(proc['memory_usage'] for proc in top_processes) / len(top_processes)
    avg_cpu_usage = sum(proc['cpu_usage'] for proc in top_processes) / len(top_processes)
    total_carbon_footprint = sum(proc['carbon_footprint'] for proc in top_processes)

    hourly_data[current_hour.hour] = {
        'time' : datetime.now().replace(minute=0, second=0, microsecond=0),
        'avg_memory_usage': avg_memory_usage,
        'avg_cpu_usage': avg_cpu_usage,
        'total_carbon_footprint': total_carbon_footprint
    }

    sustainability_hourly_data[current_hour] = {
        'avg_memory_usage': avg_memory_usage,
        'avg_cpu_usage': avg_cpu_usage,
    }

    # Schedule asynchronous save to file
    asyncio.run(process_save_to_file())
    asyncio.run(hourdata_save_to_file())

    root.after(5000, update_ui)  # Schedule update_ui() to run every 60 seconds

def refresh_data():
    update_ui()

def show_hourly_analytics():
    hours = sorted(hourly_data.keys())
    avg_memory_usage = [hourly_data[hour]['avg_memory_usage'] for hour in hours]
    avg_cpu_usage = [hourly_data[hour]['avg_cpu_usage'] for hour in hours]
    total_carbon_footprint = [hourly_data[hour]['total_carbon_footprint'] for hour in hours]

    plt.figure(figsize=(10, 6))
    plt.plot(hours, total_carbon_footprint, marker='o', color='tab:green', label='Total Carbon Footprint (kg CO2)')
    plt.xlabel('Time')
    plt.ylabel('Total Carbon Footprint (kg CO2)')
    plt.title('Hourly Carbon Footprint Analytics')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

async def process_save_to_file():
    async with aiofiles.open('process_data.json', 'w') as f:
        await f.write(json.dumps(process_data, default=str, indent=4))

async def hourdata_save_to_file():
    async with aiofiles.open('hour_data_data.json', 'w') as f:
        await f.write(json.dumps(hourly_data, default=str, indent=4))

def show_sustainability_boxplot():
    hours = sorted(sustainability_hourly_data.keys())
    ratings = {hour: [] for hour in hours}

    for proc in process_data.values():
        for hour in ratings:
            if proc['last_execution_time'] >= hour and proc['last_execution_time'] < hour + timedelta(hours=1):
                ratings[hour].append(proc['sustainability_rating'])

    boxplot_data = [ratings[hour] for hour in hours]

    plt.figure(figsize=(10, 6))
    plt.boxplot(boxplot_data, labels=hours, vert=True, patch_artist=True)
    plt.xlabel('Time')
    plt.ylabel('Sustainability Ratings')
    plt.title('Sustainability Ratings of Processes per Hour')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def check_unused_license_cost():
    cutoff_date = datetime.now() - timedelta(days=60)
    unused_license_cost_processes = [proc for proc in process_data.values() if proc['last_execution_time'] <= cutoff_date and proc['license_cost'] > 0]

    if unused_license_cost_processes:
        message = "Processes not run in the last 60 days and incurring license costs:\n\n"
        for proc in unused_license_cost_processes:
            message += f"{proc['name']} - License Cost: ${proc['license_cost']}\n"
        messagebox.showinfo("Unused License Cost Processes", message)
    else:
        messagebox.showinfo("Unused License Cost Processes", "No processes found not run in the last 60 days and incurring license costs.")

def kill_process():
    selected_item = tree.selection()
    if selected_item:
        item = tree.item(selected_item)
        pid = item['values'][-1]  # Assuming the last value is the PID in your Treeview setup

        try:
            process = psutil.Process(int(pid))
            process.terminate()
            messagebox.showinfo("Process Terminated", f"Process with PID {pid} has been terminated successfully.")
        except psutil.NoSuchProcess:
            messagebox.showerror("Error", f"Process with PID {pid} does not exist or has already been terminated.")
    else:
        messagebox.showwarning("No Process Selected", "Please select a process from the list.")

def export_to_excel():
    df = pd.DataFrame.from_dict(process_data, orient='index')
    df = df.reset_index().drop(columns=['index'])
    excel_filename = 'process_data.xlsx'
    writer = pd.ExcelWriter(excel_filename, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Process Data', index=False)
    writer.save()
    messagebox.showinfo("Export to Excel", f"Process data exported successfully to {excel_filename}.")

# Create the main window
root = tk.Tk()
root.title("Process Monitor")

# Create and pack the Treeview widget
columns = ("Process Name", "Memory Usage (MB)", "Thread Count", "CPU Usage (%)", "Carbon Footprint (kg CO2)", "License Cost ($)", "Sustainability Rating", "Last Execution Time", "Username")
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

# Create and pack the Show Sustainability button
sustainability_button = tk.Button(root, text="Show Sustainability Ratings", command=show_sustainability_boxplot)
sustainability_button.pack(pady=10)

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
