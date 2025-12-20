import subprocess
import os
import sys
import json
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ================= VERSION INFO =================
APP_VERSION = "1.0.0"

GITHUB_OWNER = "ecando1-9"
GITHUB_REPO = "videocut"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


# ================= RESOURCE PATH =================
def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)

FFMPEG = resource_path("ffmpeg.exe")
FFPROBE = resource_path("ffprobe.exe")

destination_folder = ""

# ================= UPDATE CHECK =================
def is_newer_version(latest, current):
    def parse(v):
        return [int(x) for x in v.split(".")]
    return parse(latest) > parse(current)

def check_for_updates():
    try:
        with urllib.request.urlopen(RELEASES_URL, timeout=5) as response:
            data = json.loads(response.read().decode())

        latest_version = data["tag_name"].lstrip("v")

        if is_newer_version(latest_version, APP_VERSION):
            if messagebox.askyesno(
                "Update Available",
                f"New version available!\n\n"
                f"Current: {APP_VERSION}\n"
                f"Latest: {latest_version}\n\n"
                "Download update now?"
            ):
                webbrowser.open(data["html_url"])
    except Exception:
        pass  # silent fail (offline safe)

# ================= DESTINATION =================
def choose_destination():
    global destination_folder
    folder = filedialog.askdirectory(title="Select Destination Folder")
    if folder:
        destination_folder = folder
        dest_label.config(text=f"Destination: {folder}", fg="green")

# ================= MAIN SPLIT LOGIC =================
def split_videos():
    if not destination_folder:
        messagebox.showerror("Destination Required", "Select destination folder first")
        return

    videos = filedialog.askopenfilenames(
        title="Select Video(s)",
        filetypes=[("Video Files", "*.mp4 *.mkv *.avi")]
    )

    if not videos:
        return

    try:
        clip_duration = int(duration_entry.get())
        step = int(step_entry.get())
        if clip_duration <= 0 or step <= 0 or step > clip_duration:
            raise ValueError
    except ValueError:
        messagebox.showerror(
            "Invalid Input",
            "Duration and start must be valid numbers\n(Start ≤ Duration)"
        )
        return

    progress["value"] = 0
    progress["maximum"] = len(videos)

    for index, video_path in enumerate(videos, start=1):
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        status_label.config(text=f"Processing {index}/{len(videos)} : {video_name}")
        app.update_idletasks()

        out_dir = os.path.join(destination_folder, f"{video_name}_cut")
        os.makedirs(out_dir, exist_ok=True)

        duration = float(subprocess.check_output([
            FFPROBE, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]).decode().strip())

        start = 0
        clip_no = 1

        while start < duration:
            out_file = os.path.join(out_dir, f"{video_name}_clip_{clip_no}.mp4")

            subprocess.run([
                FFMPEG, "-y",
                "-ss", str(start),
                "-i", video_path,
                "-t", str(clip_duration),
                "-c", "copy",
                out_file
            ])

            start += step
            clip_no += 1

        progress["value"] = index

    status_label.config(text="Completed ✅")
    messagebox.showinfo("Done", "All videos processed successfully!")

# ================= PRESETS =================
def preset_shorts():
    duration_entry.delete(0, tk.END)
    step_entry.delete(0, tk.END)
    duration_entry.insert(0, "59")
    step_entry.insert(0, "52")

def preset_reels():
    duration_entry.delete(0, tk.END)
    step_entry.delete(0, tk.END)
    duration_entry.insert(0, "60")
    step_entry.insert(0, "55")

def preset_no_overlap():
    duration_entry.delete(0, tk.END)
    step_entry.delete(0, tk.END)
    duration_entry.insert(0, "60")
    step_entry.insert(0, "60")

# ================= GUI =================
app = tk.Tk()
app.title("VideoCut – Advanced Video Splitter")
app.geometry("560x500")
app.resizable(False, False)

tk.Label(app, text="VideoCut", font=("Arial", 18, "bold")).pack(pady=5)

tk.Label(app, text=f"Version {APP_VERSION}", fg="gray").pack()

frame = tk.Frame(app)
frame.pack(pady=10)

tk.Label(frame, text="Clip Duration (sec):").grid(row=0, column=0, padx=10)
duration_entry = tk.Entry(frame, width=10)
duration_entry.insert(0, "59")
duration_entry.grid(row=0, column=1)

tk.Label(frame, text="Next Clip Start (sec):").grid(row=1, column=0, padx=10)
step_entry = tk.Entry(frame, width=10)
step_entry.insert(0, "52")
step_entry.grid(row=1, column=1)

preset_frame = tk.Frame(app)
preset_frame.pack(pady=5)

tk.Button(preset_frame, text="YouTube Shorts", command=preset_shorts).grid(row=0, column=0, padx=5)
tk.Button(preset_frame, text="Instagram Reels", command=preset_reels).grid(row=0, column=1, padx=5)
tk.Button(preset_frame, text="No Overlap", command=preset_no_overlap).grid(row=0, column=2, padx=5)

tk.Button(app, text="Choose Destination Folder", command=choose_destination).pack(pady=5)

dest_label = tk.Label(app, text="Destination: Not selected", fg="red", wraplength=520)
dest_label.pack()

tk.Button(
    app,
    text="Select Video(s) & Split",
    bg="#4CAF50",
    fg="white",
    font=("Arial", 12),
    padx=20,
    pady=10,
    command=split_videos
).pack(pady=15)

progress = ttk.Progressbar(app, length=450, mode="determinate")
progress.pack(pady=10)

status_label = tk.Label(app, text="Waiting...", fg="gray")
status_label.pack()

app.after(1500, check_for_updates)  # 🔔 update check on startup
app.mainloop()
