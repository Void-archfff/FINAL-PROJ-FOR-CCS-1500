import tkinter as tk
from tkinter import font as tkfont
import random
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("DOWNLOAD PILLOW")

SHAPES = [
    {
        "id": "circle",
        "name": "Circle",
        "examples": ["Circle     Clock", "Coin", "Pizza", "Plate", "Button"],
        "ascii": "  OOO  \n O   O \n O   O \n  OOO  ",
        "sides": 1,
        "char": "O"
    },
    {
        "id": "square",
        "name": "Square",
        "examples": ["Window Pane", "Chessboard", "Box", "Tile", "Napkin"],
        "ascii": "#####\n#   #\n#   #\n#####",
        "sides": 4,
        "char": "#"
    },
    {
        "id": "triangle",
        "name": "Triangle",
        "examples": ["Yield Sign", "Slice of Pie", "Mountain", "Hanger", "Pizza Slice"],
        "ascii": "  ^  \n ^ ^ \n^   ^\n^^^^^",
        "sides": 3,
        "char": "^"
    },
    {
        "id": "star",
        "name": "Star",
        "examples": ["Starfish", "Sheriff Badge", "Magic Wand", "Christmas Star", "Sea Star"],
        "ascii": "  *  \n * * \n*   *\n * * ",
        "sides": 10,
        "char": "*"
    },
]

REQUIRED_POINTS = 30
TIME_LIMIT      = 10
TOTAL_LEVELS    = 5

COLORS = {
    "bg":      "#000000",
    "card":    "#111111",
    "accent":  "#ffffff",
    "text":    "#ffffff",
    "correct": "#22c55e",
    "wrong":   "#ef4444",
    "bonus":   "#facc15",
}


def resolve_image_path(shape_id, index):
    primary = os.path.join(SCRIPT_DIR, f"{shape_id}_{index}.png")
    if os.path.exists(primary):
        return primary
    if index == 1:
        fallback = os.path.join(SCRIPT_DIR, f"{shape_id}.png")
        if os.path.exists(fallback):
            return fallback
    return None


def load_image(path, size=(90, 90)):
    if not PIL_AVAILABLE or path is None:
        return None
    try:
        img = Image.open(path).resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception as e:
        print(f"Image load error ({path}): {e}")
        return None


class ShapeTowerGame:
    def __init__(self, root):
        self.root = root
        self.root.title("TOWER NI JES")
        self.root.geometry("800x600")
        self.root.configure(bg=COLORS["bg"])

        self.title_font = tkfont.Font(family="Helvetica", size=24, weight="bold")

        self.points          = 0
        self.current_level   = 1
        self.time_left       = 0
        self.status          = "menu"

        self.target_shape        = None
        self.options             = []
        self.target_example_index = 0
        self.last_target_id      = None

        self.timer_running = False
        self.main_timer_id = None
        self.next_level_id = None

        self.image_cache = {}
        self.drag_data   = {"x": 0, "y": 0}

        self.score_label = None
        self.timer_label = None

        self.root.bind("<Configure>", self.on_window_resize)
        self.setup_ui()

    def on_window_resize(self, event):
        if event.widget == self.root and self.status == "playing":
            self.render_game()

    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_container.pack(fill="both", expand=True)
        self.show_menu()

    def clear_container(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

#MENU SECTIONS
    def show_menu(self):
        self.cancel_all_timers()
        self.clear_container()
        self.status = "menu"

        tk.Label(
            self.main_container, text="TOWER NI JES",
            font=self.title_font, bg=COLORS["bg"], fg=COLORS["text"]
        ).pack(pady=60)

        frame = tk.Frame(
            self.main_container, bg=COLORS["card"], padx=20, pady=10,
            highlightthickness=1, highlightbackground=COLORS["accent"]
        )
        frame.pack(pady=10, ipadx=50)

        tk.Label(frame, text="EASY", font=("Helvetica", 16, "bold"),
                 bg=COLORS["card"], fg=COLORS["text"]).pack()
        tk.Label(frame, text="Match Shapes", font=("Helvetica", 10),
                 bg=COLORS["card"], fg="#888888").pack()

        frame.bind("<Button-1>", lambda e: self.start_tower())
        for child in frame.winfo_children():
            child.bind("<Button-1>", lambda e: self.start_tower())

#GAME FUNCTIONS
    def start_tower(self):
        self.points        = 0
        self.current_level = 1
        self.last_target_id = None
        self.status        = "playing"
        self.generate_level()
        self.render_game()

    def generate_level(self):
        self.cancel_all_timers()

        valid_shapes = [s for s in SHAPES if s["id"] != self.last_target_id] or SHAPES
        self.target_shape        = random.choice(valid_shapes)
        self.target_example_index = random.randint(1, 5)
        self.last_target_id      = self.target_shape["id"]

        others = [s for s in SHAPES if s["id"] != self.target_shape["id"]]
        random.shuffle(others)
        self.options = [self.target_shape] + others[:2]
        random.shuffle(self.options)

        self.time_left     = TIME_LIMIT
        self.timer_running = True

    def get_cached_image(self, shape_id, index, size=(90, 90)):
        key = f"{shape_id}_{index}_{size[0]}x{size[1]}"
        if key not in self.image_cache:
            path = resolve_image_path(shape_id, index)
            self.image_cache[key] = load_image(path, size)
        return self.image_cache[key]

#RENDERING
    def render_game(self):
        self.clear_container()
        self.root.update_idletasks()

        canv_w = self.main_container.winfo_width()
        canv_h = self.main_container.winfo_height()
        if canv_w <= 1: canv_w = 800
        if canv_h <= 1: canv_h = 600
        scale_x = canv_w / 800
        scale_y = canv_h / 600
        scale   = min(scale_x, scale_y)

#Header
        header = tk.Frame(self.main_container, bg=COLORS["bg"], pady=int(10 * scale_y))
        header.pack(fill="x", padx=int(40 * scale_x))
        tk.Label(header, text="TOWER: EASY", font=("Helvetica", int(10 * scale), "bold"),
                 bg=COLORS["bg"], fg="#888888").pack(side="left")
        tk.Label(header, text=f"LEVEL {self.current_level}/{TOTAL_LEVELS}",
                 font=("Helvetica", int(10 * scale), "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(side="left", padx=int(20 * scale_x))
        self.score_label = tk.Label(header, text=f"SCORE: {self.points}",
                                    font=("Helvetica", int(10 * scale), "bold"),
                                    bg=COLORS["bg"], fg=COLORS["text"])
        self.score_label.pack(side="right")

        #Timer
        timer_frame = tk.Frame(self.main_container, bg=COLORS["bg"])
        timer_frame.pack(fill="x", padx=int(40 * scale_x))
        self.timer_label = tk.Label(timer_frame, text=f"{self.time_left:.1f}s",
                                    font=("Courier", int(14 * scale), "bold"),
                                    bg=COLORS["bg"], fg=COLORS["text"])
        self.timer_label.pack(side="right")

#Canvas
        self.canvas = tk.Canvas(self.main_container, bg=COLORS["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        target_w = 180 * scale_x
        target_h = 150 * scale_y
        start_x  = (canv_w - (3 * target_w + 2 * 40 * scale_x)) / 2
        spacing  = target_w + 40 * scale_x

        self.target_rects = []
        ascii_font = tkfont.Font(family="Courier", size=max(6, int(10 * scale)))

        for i, option in enumerate(self.options):
            x = start_x + i * spacing
            y = 50 * scale_y
            self.canvas.create_rectangle(
                x, y, x + target_w, y + target_h,
                outline="#333333", width=2, fill=COLORS["card"]
            )
            self.target_rects.append((x, y, x + target_w, y + target_h, option))
            self.canvas.create_text(
                x + target_w / 2, y + target_h / 2,
                text=option["ascii"], fill=COLORS["accent"],
                font=ascii_font, justify="center"
            )
            self.canvas.create_text(
                x + target_w / 2, y + target_h + 15 * scale_y,
                text=f"TARGET {i + 1}", fill="#666666",
                font=("Helvetica", int(8 * scale), "bold")
            )

#Draggable item
        drag_w, drag_h   = 100 * scale, 100 * scale
        self.drag_home_x = canv_w / 2
        self.drag_home_y = canv_h * 0.75

        self.drag_item_bg = self.canvas.create_rectangle(
            self.drag_home_x - drag_w / 2, self.drag_home_y - drag_h / 2,
            self.drag_home_x + drag_w / 2, self.drag_home_y + drag_h / 2,
            fill=COLORS["accent"], outline="#cccccc", width=2
        )

        example_text = self.target_shape["examples"][self.target_example_index - 1]
        drag_size    = (int(drag_w * 0.85), int(drag_h * 0.85))
        photo        = self.get_cached_image(self.target_shape["id"], self.target_example_index, size=drag_size)

        if photo:
            self.drag_item_content = self.canvas.create_image(
                self.drag_home_x, self.drag_home_y, image=photo
            )
        else:
            self.drag_item_content = self.canvas.create_text(
                self.drag_home_x, self.drag_home_y,
                text=example_text.upper(), fill="black",
                font=("Helvetica", int(11 * scale), "bold"),
                width=int(90 * scale), justify="center"
            )

        self.canvas.create_text(
            self.drag_home_x, self.drag_home_y + drag_h / 2 + 20 * scale_y,
            text="!!!MATCH THE OBJECT!!!", fill=COLORS["bonus"],
            font=("Helvetica", int(8 * scale), "bold")
        )

        for tag in (self.drag_item_bg, self.drag_item_content):
            self.canvas.tag_bind(tag, "<Button-1>",       self.on_drag_start)
            self.canvas.tag_bind(tag, "<B1-Motion>",      self.on_drag_motion)
            self.canvas.tag_bind(tag, "<ButtonRelease-1>", self.on_drag_release)

        if self.timer_running:
            if self.main_timer_id:
                self.root.after_cancel(self.main_timer_id)
            self.update_timer()

#Timer
    def update_timer(self):
        if not self.timer_running or self.status != "playing":
            self.main_timer_id = None
            return
        self.time_left -= 0.1
        if self.time_left <= 0:
            self.time_left     = 0
            self.timer_running = False
            self.main_timer_id = None
            self.handle_failure()
        else:
            try:
                color = COLORS["wrong"] if self.time_left < 2 else COLORS["text"]
                self.timer_label.config(text=f"{self.time_left:.1f}s", fg=color)
                self.main_timer_id = self.root.after(100, self.update_timer)
            except tk.TclError:
                self.main_timer_id = None

#Drag Function
    def on_drag_start(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag_motion(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        self.canvas.move(self.drag_item_bg,      dx, dy)
        self.canvas.move(self.drag_item_content, dx, dy)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag_release(self, event):
        dropped_on = None
        for rx1, ry1, rx2, ry2, shape in self.target_rects:
            if rx1 <= event.x <= rx2 and ry1 <= event.y <= ry2:
                dropped_on = shape
                break

        if dropped_on:
            if dropped_on["id"] == self.target_shape["id"]:
                self.handle_success()
            else:
                self.handle_failure()
        else:
            #back to home position
            bbox = self.canvas.bbox(self.drag_item_bg)
            if bbox:
                w = (bbox[2] - bbox[0]) / 2
                h = (bbox[3] - bbox[1]) / 2
                self.canvas.coords(self.drag_item_bg,
                                   self.drag_home_x - w, self.drag_home_y - h,
                                   self.drag_home_x + w, self.drag_home_y + h)
            self.canvas.coords(self.drag_item_content, self.drag_home_x, self.drag_home_y)

#Outcome 
    def handle_success(self):
        self.timer_running = False
        earned       = max(1, int(10 * (self.time_left / TIME_LIMIT)))
        self.points += earned
        self.canvas.itemconfig(self.drag_item_bg, fill=COLORS["correct"])
        if self.next_level_id:
            self.root.after_cancel(self.next_level_id)
        self.next_level_id = self.root.after(500, self.next_level)

    def handle_failure(self):
        self.timer_running = False
        self.canvas.itemconfig(self.drag_item_bg, fill=COLORS["wrong"])
        if self.next_level_id:
            self.root.after_cancel(self.next_level_id)
        self.next_level_id = self.root.after(500, self.next_level)

    def next_level(self):
        self.next_level_id = None
        if self.current_level >= TOTAL_LEVELS:
            self.finish_tower()
        else:
            self.current_level += 1
            self.generate_level()
            self.render_game()

    def finish_tower(self):
        self.cancel_all_timers()
        self.status = "result"
        self.clear_container()

        success = self.points >= REQUIRED_POINTS
        title   = "TOWER COMPLETED!" if success else "TOWER FAILED!"
        color   = COLORS["correct"] if success else COLORS["wrong"]

        tk.Label(self.main_container, text=title, font=self.title_font,
                 bg=COLORS["bg"], fg=color).pack(pady=40)
        tk.Label(self.main_container, text=f"Final Score: {self.points}",
                 font=("Helvetica", 18), bg=COLORS["bg"], fg=COLORS["text"]).pack()
        tk.Label(self.main_container, text=f"Required: {REQUIRED_POINTS}",
                 font=("Helvetica", 12), bg=COLORS["bg"], fg="#888888").pack(pady=10)

        msg = "VERY GOOD!" if success else "TRY AGAIN!"
        msg_color = COLORS["bonus"] if success else "#888888"
        tk.Label(self.main_container, text=msg, font=("Helvetica", 12, "bold"),
                 bg=COLORS["bg"], fg=msg_color).pack(pady=20)

        tk.Button(self.main_container, text="BACK TO MENU", command=self.show_menu,
                  bg=COLORS["accent"], fg="black", font=("Helvetica", 12, "bold"),
                  padx=20, pady=10, borderwidth=0).pack(pady=20)
        
#Helpers
    def cancel_all_timers(self):
        if self.main_timer_id:
            self.root.after_cancel(self.main_timer_id)
            self.main_timer_id = None
        if self.next_level_id:
            self.root.after_cancel(self.next_level_id)
            self.next_level_id = None


if __name__ == "__main__":
    root = tk.Tk()
    game = ShapeTowerGame(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()
