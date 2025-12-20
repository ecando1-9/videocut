import os, sys, subprocess, math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

PP_VERSION = "1.2.0"
GITHUB_OWNER = "ecando1-9"
GITHUB_REPO = "videocut"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# ================= PATH SETUP =================
def resource_path(p):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, p)
    return os.path.abspath(p)

# Ensure ffmpeg/ffprobe are available
FFMPEG = resource_path("ffmpeg.exe")
FFPROBE = resource_path("ffprobe.exe")
# FFMPEG = "ffmpeg"  # Uncomment if using system PATH

# ================= ROOT APP =================
app = tk.Tk()
app.title("VideoCut Studio - Resizable Edition")
app.geometry("1400x850")

# ================= VARIABLES =================
video_path = ""
video_dur = 0.0

# Clip / Cut Settings
clip_len = tk.IntVar(value=59)
step_len = tk.IntVar(value=59)
start_time = tk.IntVar(value=0)
end_time = tk.IntVar(value=0)

# Export Limits
max_clips_possible = tk.IntVar(value=0)
user_export_limit = tk.IntVar(value=0)

# Text / Visuals
text_str = tk.StringVar(value="PART {n}")
font_size = tk.IntVar(value=30)
text_color = tk.StringVar(value="white")
outline_color = tk.StringVar(value="black")
outline_on = tk.BooleanVar(value=True)
show_ui_overlay = tk.BooleanVar(value=True)

# Zoom / Pan
zoom_var = tk.DoubleVar(value=1.0)
pan_x = 0
pan_y = 0
text_rel_x = 0.5
text_rel_y = 0.2

# Image Cache
original_img = None
display_img = None
CV_W = 360
CV_H = 640

# ================= UI LAYOUT (PANED WINDOW) =================
# FIX: sashwidth must be lowercase
main_pane = tk.PanedWindow(app, orient=tk.HORIZONTAL, sashwidth=5, bg="#ccc")
main_pane.pack(fill=tk.BOTH, expand=True)

# LEFT PANEL (Controls)
left_scroll = tk.Canvas(main_pane, bg="#f0f0f0")
left_frame = tk.Frame(left_scroll, bg="#f0f0f0", padx=15, pady=15)

# Scrollbar for left panel if window is small
scrollbar = tk.Scrollbar(main_pane, orient="vertical", command=left_scroll.yview)
left_scroll.configure(yscrollcommand=scrollbar.set)
left_scroll.create_window((0, 0), window=left_frame, anchor="nw")

def _on_frame_configure(event):
    left_scroll.configure(scrollregion=left_scroll.bbox("all"))
left_frame.bind("<Configure>", _on_frame_configure)

# Add Left Panel to Pane
main_pane.add(left_scroll, minsize=350, width=400)

# RIGHT PANEL (Preview)
right_frame = tk.Frame(main_pane, bg="#222")
main_pane.add(right_frame, minsize=400)

# ================= LOGIC =================
def load_video():
    global video_path, video_dur, original_img, pan_x, pan_y
    path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv *.avi")])
    if not path: return
    video_path = path

    try:
        out = subprocess.check_output([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path])
        video_dur = float(out)
        end_time.set(int(video_dur))
        
        # Snapshot
        subprocess.run([FFMPEG, "-y", "-ss", "2", "-i", path, "-vframes", "1", "-vf", "scale=1080:-1", "temp_preview.jpg"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        original_img = Image.open("temp_preview.jpg")
        
        # Reset View
        pan_x = 0; pan_y = 0; zoom_var.set(1.0)
        update_clips()
        render()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def update_clips(*args):
    s = start_time.get()
    e = end_time.get()
    length = clip_len.get()
    step = step_len.get()
    if e > s and step > 0:
        count = math.ceil((e - s - length) / step) + 1
        count = max(0, count)
        max_clips_possible.set(count)
        # Update user limit only if it matches old max or is 0
        user_export_limit.set(count)
    else:
        max_clips_possible.set(0)
        user_export_limit.set(0)

# ================= CANVAS RENDERER =================
canvas = tk.Canvas(right_frame, width=CV_W, height=CV_H, bg="black", highlightthickness=0)
canvas.pack(expand=True, pady=20)

def draw_stroked_text(cv, x, y, text, font, fill, outline, width=2):
    """
    Tkinter canvas doesn't support 'outline' for text natively.
    We simulate it by drawing the text multiple times in the background.
    """
    # Draw outline (offsets)
    if outline and outline != "none":
        offsets = [( -width, -width), ( -width, width), ( width, -width), ( width, width), 
                   ( -width, 0), ( width, 0), ( 0, -width), ( 0, width)]
        for ox, oy in offsets:
            cv.create_text(x + ox, y + oy, text=text, font=font, fill=outline, tags="text_bg")
    
    # Draw main text
    cv.create_text(x, y, text=text, font=font, fill=fill, tags="text_fg")

def render(*args):
    global display_img
    canvas.delete("all")

    # 1. Video Layer
    if original_img:
        base_scale = CV_W / original_img.width
        final_scale = base_scale * zoom_var.get()
        new_w = int(original_img.width * final_scale)
        new_h = int(original_img.height * final_scale)
        
        resized = original_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        display_img = ImageTk.PhotoImage(resized)
        
        dx = ((CV_W - new_w) // 2) + pan_x
        dy = ((CV_H - new_h) // 2) + pan_y
        
        canvas.create_image(dx, dy, image=display_img, anchor="nw", tags="video")
        canvas.video_meta = {"scale": final_scale, "x": dx, "y": dy, "w": new_w, "h": new_h}

    # 2. Text Layer (With Outline Fix)
    tx = CV_W * text_rel_x
    ty = CV_H * text_rel_y
    
    t_font = ("Arial", font_size.get(), "bold")
    t_val = text_str.get().replace("{n}", "1")
    t_fill = text_color.get()
    
    # Decide outline
    t_out = outline_color.get() if outline_on.get() else None
    
    draw_stroked_text(canvas, tx, ty, t_val, t_font, t_fill, t_out, width=2)
    
    # Invisible Hitbox for Dragging (on top of text)
    bbox = canvas.bbox("text_fg")
    if bbox:
        canvas.create_rectangle(bbox, fill="", outline="", tags="text_hitbox")

    # 3. Safe Zone Overlay
    if show_ui_overlay.get():
        c = "#ddd"
        rx = CV_W - 40; sy = 280
        for i in range(5): canvas.create_oval(rx-20, sy+(i*65)-20, rx+20, sy+(i*65)+20, outline=c, width=2)
        canvas.create_rectangle(10, CV_H-140, CV_W-70, CV_H-20, outline=c, width=2, dash=(4,4))
        canvas.create_text(20, CV_H-120, anchor="w", text="@Channel", fill=c, font=("Arial", 11, "bold"))

# ================= INTERACTION =================
drag_data = {"item": None, "x": 0, "y": 0}

def on_click(e):
    drag_data["x"], drag_data["y"] = e.x, e.y
    # Check overlapping with text hitbox or text layers
    overlap = canvas.find_overlapping(e.x-5, e.y-5, e.x+5, e.y+5)
    tags = [canvas.gettags(i) for i in overlap]
    
    # Flatten tags list
    all_tags = [t for sub in tags for t in sub]
    
    if "text_fg" in all_tags or "text_hitbox" in all_tags:
        drag_data["item"] = "text"
    else:
        drag_data["item"] = "video"

def on_drag(e):
    global pan_x, pan_y, text_rel_x, text_rel_y
    dx, dy = e.x - drag_data["x"], e.y - drag_data["y"]
    
    if drag_data["item"] == "video":
        pan_x += dx; pan_y += dy
        render()
    elif drag_data["item"] == "text":
        # Calculate new relative position directly
        # We need current pixel pos + delta
        cur_px = (CV_W * text_rel_x) + dx
        cur_py = (CV_H * text_rel_y) + dy
        text_rel_x = cur_px / CV_W
        text_rel_y = cur_py / CV_H
        render()

    drag_data["x"], drag_data["y"] = e.x, e.y

canvas.bind("<Button-1>", on_click)
canvas.bind("<B1-Motion>", on_drag)

# ================= EXPORT =================
def export():
    if not video_path: return
    out_dir = filedialog.askdirectory()
    if not out_dir: return

    limit = user_export_limit.get()
    progress["maximum"] = limit; progress["value"] = 0
    
    # Preview(360w) -> Output(1080w) :: Ratio = 3.0
    R = 3.0
    meta = canvas.video_meta
    
    # Geometry
    rw, rh = int(meta["w"] * R), int(meta["h"] * R)
    rx, ry = int(meta["x"] * R), int(meta["y"] * R)
    vf_geo = f"scale={rw}:{rh},pad=1080:1920:{rx}:{ry}:black"
    
    # Text
    border = f":borderw=5:bordercolor={outline_color.get()}" if outline_on.get() else ""
    vf_txt = (f",drawtext=text='PART {{n}}':x=(w*{text_rel_x})-(text_w/2):y=(h*{text_rel_y})-(text_h/2):"
              f"fontsize={font_size.get()*3}:fontcolor={text_color.get()}{border}")
    
    full_vf = vf_geo + vf_txt
    
    start = start_time.get()
    part = 1
    count = 0
    
    while start < end_time.get() and count < limit:
        out_f = os.path.join(out_dir, f"clip_{part}.mp4")
        cmd = [FFMPEG, "-y", "-ss", str(start), "-i", video_path, "-t", str(clip_len.get()),
               "-vf", full_vf.replace("{n}", str(part)), "-c:a", "copy", "-c:v", "libx264", "-pix_fmt", "yuv420p", out_f]
        
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start += step_len.get(); part += 1; count += 1; progress["value"] += 1
        app.update_idletasks()
        
    messagebox.showinfo("Done", f"Exported {count} clips.")

# ================= CONTROLS (LEFT FRAME) =================
h1 = ("Segoe UI", 16, "bold")
h2 = ("Segoe UI", 11, "bold")

tk.Label(left_frame, text="VideoCut Pro", font=("Segoe UI", 22, "bold"), bg="#f0f0f0").pack(anchor="w")
tk.Button(left_frame, text="📂 LOAD VIDEO", command=load_video, bg="#0078D7", fg="white", font=("Segoe UI", 10, "bold"), height=2).pack(fill="x", pady=10)

# --- CLIPS & TIMELINE ---
frame_time = tk.LabelFrame(left_frame, text="Clip & Cut Options", font=h2, bg="#f0f0f0", padx=10, pady=10)
frame_time.pack(fill="x", pady=10)

# Grid for inputs
tk.Label(frame_time, text="Start (sec):", bg="#f0f0f0").grid(row=0, column=0, sticky="w")
tk.Entry(frame_time, textvariable=start_time, width=8).grid(row=0, column=1, padx=5, pady=2)

tk.Label(frame_time, text="End (sec):", bg="#f0f0f0").grid(row=0, column=2, sticky="w")
tk.Entry(frame_time, textvariable=end_time, width=8).grid(row=0, column=3, padx=5, pady=2)

tk.Label(frame_time, text="Clip Len (s):", bg="#f0f0f0").grid(row=1, column=0, sticky="w")
tk.Entry(frame_time, textvariable=clip_len, width=8).grid(row=1, column=1, padx=5, pady=2)

tk.Label(frame_time, text="Step/Loop:", bg="#f0f0f0").grid(row=1, column=2, sticky="w")
tk.Entry(frame_time, textvariable=step_len, width=8).grid(row=1, column=3, padx=5, pady=2)

ttk.Separator(frame_time, orient="horizontal").grid(row=2, column=0, columnspan=4, sticky="ew", pady=10)

tk.Label(frame_time, text="Max Possible:", bg="#f0f0f0", fg="gray").grid(row=3, column=0, columnspan=2, sticky="w")
tk.Label(frame_time, textvariable=max_clips_possible, bg="#f0f0f0", fg="gray", font=("Arial", 9, "bold")).grid(row=3, column=2, sticky="w")

tk.Label(frame_time, text="Export Count:", bg="#f0f0f0", font=("Segoe UI", 9, "bold")).grid(row=4, column=0, columnspan=2, sticky="w")
tk.Entry(frame_time, textvariable=user_export_limit, width=8, fg="blue").grid(row=4, column=2, sticky="w")

# --- VISUALS ---
frame_vis = tk.LabelFrame(left_frame, text="Visual Editor", font=h2, bg="#f0f0f0", padx=10, pady=10)
frame_vis.pack(fill="x", pady=10)

tk.Label(frame_vis, text="Video Zoom:", bg="#f0f0f0").pack(anchor="w")
tk.Scale(frame_vis, from_=1.0, to=3.0, resolution=0.1, orient="horizontal", variable=zoom_var, bg="#f0f0f0").pack(fill="x")

tk.Label(frame_vis, text="Text Overlay:", bg="#f0f0f0").pack(anchor="w", pady=(10,0))
tk.Entry(frame_vis, textvariable=text_str).pack(fill="x")

# Colors
c_row = tk.Frame(frame_vis, bg="#f0f0f0")
c_row.pack(fill="x", pady=5)
tk.Label(c_row, text="Fill:", bg="#f0f0f0").pack(side="left")
ttk.Combobox(c_row, textvariable=text_color, values=["white","yellow","red","cyan","lime","black"], width=7).pack(side="left", padx=5)
tk.Label(c_row, text="Line:", bg="#f0f0f0").pack(side="left")
ttk.Combobox(c_row, textvariable=outline_color, values=["black","white","red","blue"], width=7).pack(side="left", padx=5)

tk.Scale(frame_vis, from_=10, to=100, orient="horizontal", variable=font_size, label="Font Size", bg="#f0f0f0").pack(fill="x")

tk.Checkbutton(frame_vis, text="Enable Outline", variable=outline_on, bg="#f0f0f0").pack(anchor="w")
tk.Checkbutton(frame_vis, text="Show Safe Zone", variable=show_ui_overlay, bg="#f0f0f0").pack(anchor="w")

# --- EXPORT ---
tk.Button(left_frame, text="START EXPORT", command=export, bg="#28a745", fg="white", font=h1, height=2).pack(fill="x", pady=20)
progress = ttk.Progressbar(left_frame)
progress.pack(fill="x")

# Triggers
for v in [zoom_var, text_str, font_size, text_color, outline_color, outline_on, show_ui_overlay]:
    v.trace_add("write", lambda *a: render())
for v in [clip_len, step_len, start_time, end_time]:
    v.trace_add("write", update_clips)

app.mainloop()