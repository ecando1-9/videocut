import os, sys, subprocess, math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

# ================= PATH SETUP =================
def resource_path(p):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.abspath(p)

FFMPEG = resource_path("ffmpeg.exe")
FFPROBE = resource_path("ffprobe.exe")

# ================= ROOT APP =================
app = tk.Tk()
app.title("VideoCut Studio - Pro Colors")
app.geometry("1300x900")

# --- ICON SETUP ---
icon_path = resource_path("videocut.ico")
if os.path.exists(icon_path):
    try: app.iconbitmap(icon_path)
    except: pass

# ================= VARIABLES =================
video_path = ""
video_dur = 0.0

# Clips
clip_len = tk.IntVar(value=59)
step_len = tk.IntVar(value=59)
start_time = tk.IntVar(value=0)
end_time = tk.IntVar(value=0)
max_clips_possible = tk.IntVar(value=0)
user_export_limit = tk.IntVar(value=0)

# Visuals
text_str = tk.StringVar(value="PART {n}")
font_size = tk.IntVar(value=30)
text_color = tk.StringVar(value="white")
text_opacity = tk.DoubleVar(value=1.0) # 0.1 to 1.0
outline_color = tk.StringVar(value="black")
outline_on = tk.BooleanVar(value=True)
show_ui_overlay = tk.BooleanVar(value=True)

# Colors List
COLOR_LIST = [
    "white", "black", "red", "green", "blue", "yellow", 
    "cyan", "magenta", "orange", "purple", "pink", 
    "gold", "teal", "lime", "navy", "gray", "brown"
]

# Zoom / Pan
zoom_var = tk.DoubleVar(value=1.0)
pan_x = 0; pan_y = 0
text_rel_x = 0.5; text_rel_y = 0.2
original_img = None; display_img = None
CV_W = 360; CV_H = 640

# ================= UI LAYOUT =================
main_pane = tk.PanedWindow(app, orient=tk.HORIZONTAL, sashwidth=5, bg="#ccc")
main_pane.pack(fill=tk.BOTH, expand=True)

left_scroll = tk.Canvas(main_pane, bg="#f0f0f0")
left_frame = tk.Frame(left_scroll, bg="#f0f0f0", padx=15, pady=15)
scrollbar = tk.Scrollbar(main_pane, orient="vertical", command=left_scroll.yview)
left_scroll.configure(yscrollcommand=scrollbar.set)
left_scroll.create_window((0, 0), window=left_frame, anchor="nw")
left_frame.bind("<Configure>", lambda e: left_scroll.configure(scrollregion=left_scroll.bbox("all")))
main_pane.add(left_scroll, minsize=380, width=400)

right_frame = tk.Frame(main_pane, bg="#222")
main_pane.add(right_frame, minsize=400)

# ================= LOGIC =================
def load_video():
    global video_path, video_dur, original_img, pan_x, pan_y
    path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi")])
    if not path: return
    video_path = path

    try:
        if not os.path.exists(FFPROBE):
            messagebox.showerror("Error", "ffprobe.exe missing!")
            return
            
        out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path])
        video_dur = float(out)
        end_time.set(int(video_dur))
        
        subprocess.run([FFMPEG, "-y", "-ss", "2", "-i", path, "-vframes", "1", "-vf", "scale=1080:-1", "temp_preview.jpg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        original_img = Image.open("temp_preview.jpg")
        pan_x = 0; pan_y = 0; zoom_var.set(1.0)
        update_clips()
        render()
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load video.\n{e}")

def update_clips(*args):
    s = start_time.get(); e = end_time.get(); length = clip_len.get(); step = step_len.get()
    if e > s and step > 0:
        count = math.ceil((e - s - length) / step) + 1
        max_clips_possible.set(max(0, count))
        user_export_limit.set(max(0, count))
    else:
        max_clips_possible.set(0); user_export_limit.set(0)

# ================= RENDERER =================
canvas = tk.Canvas(right_frame, width=CV_W, height=CV_H, bg="black", highlightthickness=0)
canvas.pack(expand=True, pady=20)

def draw_stroked_text(cv, x, y, text, font, fill, outline, width=2):
    # Preview ignores Opacity (Tkinter limit), but Export uses it.
    if outline and outline != "none":
        for ox, oy in [(-width,-width), (-width,width), (width,-width), (width,width), (-width,0), (width,0), (0,-width), (0,width)]:
            cv.create_text(x+ox, y+oy, text=text, font=font, fill=outline, tags="text_bg")
    cv.create_text(x, y, text=text, font=font, fill=fill, tags="text_fg")

def render(*args):
    global display_img
    canvas.delete("all")
    if original_img:
        base_scale = CV_W / original_img.width
        final_scale = base_scale * zoom_var.get()
        new_w = int(original_img.width * final_scale) // 2 * 2
        new_h = int(original_img.height * final_scale) // 2 * 2
        resized = original_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        display_img = ImageTk.PhotoImage(resized)
        dx = ((CV_W - new_w) // 2) + pan_x
        dy = ((CV_H - new_h) // 2) + pan_y
        canvas.create_image(dx, dy, image=display_img, anchor="nw", tags="video")
        canvas.video_meta = {"scale": final_scale, "x": dx, "y": dy, "w": new_w, "h": new_h}

    tx, ty = CV_W * text_rel_x, CV_H * text_rel_y
    t_font = ("Arial", font_size.get(), "bold")
    t_out = outline_color.get() if outline_on.get() else None
    draw_stroked_text(canvas, tx, ty, text_str.get().replace("{n}", "1"), t_font, text_color.get(), t_out)
    
    bbox = canvas.bbox("text_fg")
    if bbox: canvas.create_rectangle(bbox, fill="", outline="", tags="text_hitbox")

    if show_ui_overlay.get():
        c = "#ddd"; rx = CV_W - 40; sy = 280
        for i in range(5): canvas.create_oval(rx-20, sy+(i*65)-20, rx+20, sy+(i*65)+20, outline=c, width=2)
        canvas.create_rectangle(10, CV_H-140, CV_W-70, CV_H-20, outline=c, width=2, dash=(4,4))
        canvas.create_text(20, CV_H-120, anchor="w", text="@Channel", fill=c, font=("Arial", 11, "bold"))

# ================= INTERACTION =================
drag_data = {"item": None, "x": 0, "y": 0}
def on_click(e):
    drag_data["x"], drag_data["y"] = e.x, e.y
    overlap = canvas.find_overlapping(e.x-5, e.y-5, e.x+5, e.y+5)
    tags = [t for i in overlap for t in canvas.gettags(i)]
    drag_data["item"] = "text" if "text_fg" in tags or "text_hitbox" in tags else "video"

def on_drag(e):
    global pan_x, pan_y, text_rel_x, text_rel_y
    dx, dy = e.x - drag_data["x"], e.y - drag_data["y"]
    if drag_data["item"] == "video": pan_x += dx; pan_y += dy; render()
    elif drag_data["item"] == "text":
        text_rel_x = ((CV_W * text_rel_x) + dx) / CV_W; text_rel_y = ((CV_H * text_rel_y) + dy) / CV_H
        render()
    drag_data["x"], drag_data["y"] = e.x, e.y
canvas.bind("<Button-1>", on_click); canvas.bind("<B1-Motion>", on_drag)

# ================= EXPORT LOGIC =================
def export():
    if not video_path: return
    
    if not os.path.exists(FFMPEG):
        messagebox.showerror("Error", f"ffmpeg.exe not found at:\n{FFMPEG}")
        return

    root_out_dir = filedialog.askdirectory(title="Select Output Location")
    if not root_out_dir: return

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    final_out_dir = os.path.join(root_out_dir, f"{video_name}_videocut")
    try: os.makedirs(final_out_dir, exist_ok=True)
    except OSError: messagebox.showerror("Error", "Could not create folder."); return

    limit = user_export_limit.get()
    progress["maximum"] = limit; progress["value"] = 0
    
    R = 3.0; meta = canvas.video_meta
    rw = int(meta["w"] * R) // 2 * 2
    rh = int(meta["h"] * R) // 2 * 2
    rx = int(meta["x"] * R); ry = int(meta["y"] * R)
    
    vf_geo = f"scale={rw}:{rh} [fg]; color=s=1080x1920:c=black [bg]; [bg][fg] overlay=x={rx}:y={ry}:shortest=1"
    
    # --- TEXT WITH OPACITY ---
    # format: fontcolor=white@0.5
    f_color = f"{text_color.get()}@{text_opacity.get()}"
    border = f":borderw=5:bordercolor={outline_color.get()}" if outline_on.get() else ""
    
    vf_txt = f",drawtext=text='PART {{n}}':x=(w*{text_rel_x})-(text_w/2):y=(h*{text_rel_y})-(text_h/2):fontsize={font_size.get()*3}:fontcolor={f_color}{border}"
    full_vf = vf_geo + vf_txt
    
    start = start_time.get(); part = 1; count = 0
    
    while start < end_time.get() and count < limit:
        out_f = os.path.join(final_out_dir, f"{video_name}_clip_{part}.mp4")
        
        cmd = [
            FFMPEG, "-y", "-ss", str(start), "-i", video_path, 
            "-t", str(clip_len.get()),
            "-filter_complex", full_vf.replace("{n}", str(part)),
            "-c:a", "aac", "-b:a", "128k",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
            out_f
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                messagebox.showerror("FFmpeg Error", f"Clip {part} failed:\n\n{result.stderr[-500:]}")
                return
        except Exception as e:
            messagebox.showerror("System Error", str(e)); return

        start += step_len.get(); part += 1; count += 1; progress["value"] += 1
        app.update_idletasks()
        
    messagebox.showinfo("Success", f"Exported {count} clips to:\n{final_out_dir}")

# ================= UI CONTROLS =================
tk.Label(left_frame, text="VideoCut Pro", font=("Segoe UI", 22, "bold"), bg="#f0f0f0").pack(anchor="w")
tk.Button(left_frame, text="📂 LOAD VIDEO", command=load_video, bg="#0078D7", fg="white", font=("Segoe UI", 10, "bold"), height=2).pack(fill="x", pady=10)

# 1. CLIPS
frame_time = tk.LabelFrame(left_frame, text="Clip Options", font=("Segoe UI", 11, "bold"), bg="#f0f0f0", padx=10, pady=10)
frame_time.pack(fill="x", pady=10)
tk.Label(frame_time, text="Start:", bg="#f0f0f0").grid(row=0, column=0); tk.Entry(frame_time, textvariable=start_time, width=6).grid(row=0, column=1, padx=5)
tk.Label(frame_time, text="End:", bg="#f0f0f0").grid(row=0, column=2); tk.Entry(frame_time, textvariable=end_time, width=6).grid(row=0, column=3, padx=5)
tk.Label(frame_time, text="Len:", bg="#f0f0f0").grid(row=1, column=0, pady=5); tk.Entry(frame_time, textvariable=clip_len, width=6).grid(row=1, column=1)
tk.Label(frame_time, text="Step:", bg="#f0f0f0").grid(row=1, column=2); tk.Entry(frame_time, textvariable=step_len, width=6).grid(row=1, column=3)
tk.Label(frame_time, text="Export Limit:", bg="#f0f0f0", fg="blue").grid(row=2, column=0, pady=5, columnspan=2); tk.Entry(frame_time, textvariable=user_export_limit, width=6).grid(row=2, column=2)

# 2. VISUALS
frame_vis = tk.LabelFrame(left_frame, text="Visual Editor", font=("Segoe UI", 11, "bold"), bg="#f0f0f0", padx=10, pady=10)
frame_vis.pack(fill="x", pady=10)

tk.Label(frame_vis, text="Video Zoom:", bg="#f0f0f0").pack(anchor="w")
tk.Scale(frame_vis, from_=1.0, to=3.0, resolution=0.1, orient="horizontal", variable=zoom_var, bg="#f0f0f0").pack(fill="x")

tk.Label(frame_vis, text="Text Content:", bg="#f0f0f0").pack(anchor="w", pady=(10,0))
tk.Entry(frame_vis, textvariable=text_str).pack(fill="x")

# Colors Row 1 (Text)
c_row1 = tk.Frame(frame_vis, bg="#f0f0f0"); c_row1.pack(fill="x", pady=5)
tk.Label(c_row1, text="Fill Color:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
ttk.Combobox(c_row1, textvariable=text_color, values=COLOR_LIST, width=12).pack(side="left")

# Colors Row 2 (Outline)
c_row2 = tk.Frame(frame_vis, bg="#f0f0f0"); c_row2.pack(fill="x", pady=5)
tk.Label(c_row2, text="Line Color:", bg="#f0f0f0", width=10, anchor="w").pack(side="left")
ttk.Combobox(c_row2, textvariable=outline_color, values=COLOR_LIST + ["none"], width=12).pack(side="left")

# Intensity Slider
tk.Label(frame_vis, text="Text Intensity (Opacity):", bg="#f0f0f0").pack(anchor="w", pady=(5,0))
tk.Scale(frame_vis, from_=0.1, to=1.0, resolution=0.1, orient="horizontal", variable=text_opacity, bg="#f0f0f0").pack(fill="x")

tk.Scale(frame_vis, from_=10, to=100, orient="horizontal", variable=font_size, label="Font Size", bg="#f0f0f0").pack(fill="x")
tk.Checkbutton(frame_vis, text="Enable Outline", variable=outline_on, bg="#f0f0f0").pack(anchor="w")
tk.Checkbutton(frame_vis, text="Show Safe Zone", variable=show_ui_overlay, bg="#f0f0f0").pack(anchor="w")

tk.Button(left_frame, text="START EXPORT", command=export, bg="#28a745", fg="white", font=("Segoe UI", 11, "bold"), height=2).pack(fill="x", pady=20)
progress = ttk.Progressbar(left_frame); progress.pack(fill="x")

for v in [zoom_var, text_str, font_size, text_color, text_opacity, outline_color, outline_on, show_ui_overlay]: v.trace_add("write", lambda *a: render())
for v in [clip_len, step_len, start_time, end_time]: v.trace_add("write", update_clips)

app.mainloop()