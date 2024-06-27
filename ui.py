import tkinter as tk
from tkinter import ttk

import psutil
import time
import pandas as pd
from datetime import datetime, timedelta

# Initialize data structures
process_usage = {}

def monitor_processes():
    current_time = datetime.now()
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            pid = proc.info['pid']
            name = proc.info['name']
            mem = proc.info['memory_info'].rss / (1024 ** 2)  # Memory in MB

            if name not in process_usage:
                process_usage[name] = {'pid': pid, 'last_used': current_time, 'mem_usage': []}
            process_usage[name]['last_used'] = current_time
            process_usage[name]['mem_usage'].append((current_time, mem))
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


def update_ui():
    monitor_processes()
    for row in tree.get_children():
        tree.delete(row)
    
    for name, info in process_usage.items():
        mem_usage = sum([mem for _, mem in info['mem_usage']]) / len(info['mem_usage'])
        carbon_footprint = 100
        license_cost = 100
        last_used = info['last_used'].strftime('%Y-%m-%d %H:%M:%S')
        
        tree.insert("", "end", values=(name, mem_usage, carbon_footprint, license_cost, last_used))
    
    root.after(10, update_ui)

root = tk.Tk()
root.title("Process Monitor")

columns = ("Process Name", "Memory Usage (MB)", "Carbon Footprint (kg CO2)", "License Cost ($)", "Last Used")
tree = ttk.Treeview(root, columns=columns, show="headings")
tree.pack(fill=tk.BOTH, expand=True)

for col in columns:
    tree.heading(col, text=col)

update_ui()
root.mainloop()
