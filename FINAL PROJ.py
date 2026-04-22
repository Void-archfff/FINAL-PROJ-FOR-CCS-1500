import tkinter as tk
import random  
import os
import math
import threading
try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Pillow is not installed yet")

SHAPES = [
    {
        "id": "circle",
        "name": "Circle",
        "Real_shapes": ["Wall Clock", "Coin", "Pizza", "Plate", "Button"],
        "sides": 1,
        "char": "O"
    },
    {
        "id": "square",
        "name": "Square",
        "Real_shapes": ["Window Pane", "Chessboard", "Box", "Tile", "Napkin"],
        "sides": 4,
        "char": "#"
    },
    {
        "id": "triangle",
        "name": "Triangle",
        "Real_shapes": ["Yield Sign", "Slice of Pie", "Mountain", "Hanger", "Pizza Slice"],
        "sides": 3,
        "char": "^"
    },
    {
        "id": "star",
        "name": "Star",
        "Real_shapes": ["Starfish", "Sheriff Badge", "Magic Wand", "Christmas Star", "Sea Star"],
        "sides": 10,
        "char": "*"
    },
    {
        "id": "hexagon",
        "name": "Hexagon",
        "Real_shapes": ["Honeycomb", "Hardware Nut", "Bolt Head", "Pencil End", "Floor Tile"],
        "sides": 6,
        "char": "H"
    },
    {
        "id": "heart",
        "name": "Heart",
        "Real_shapes": ["Love Cookie", "Leaf", "Chocolate Box", "Valentine", "Locket"],
        "sides": 2,
        "char": "V"
    },
    {
        "id": "diamond",
        "name": "Diamond",
        "Real_shapes": ["Playing Card", "Kite", "Road Sign", "Gemstone", "Baseball Diamond"],
        "sides": 4,
        "char": "<>"
    },
    {
        "id": "pentagon",
        "name": "Pentagon",
        "Real_shapes": ["The Pentagon", "Birdhouse", "School Zone Sign", "Okra Slice", "Soccer Ball Patch"],
        "sides": 5,
        "char": "P"
    },
    {
        "id": "octagon",
        "name": "Octagon",
        "Real_shapes": ["Stop Sign", "Umbrella", "Spider Web", "Wall Clock", "Medal"],
        "sides": 8,
        "char": "8"
    },
]

TOWER_CONFIG = {
    "Easy": {
        "requiredPoints": 30,
        "timeLimit": 10,
        "shapes": SHAPES[:4],
        "next": "Medium",
        "descriptions": "Shapes"
    },
    "Medium": {
        "requiredPoints": 30,
        "timeLimit": 10,
        "shapes": SHAPES[:7],
        "next": "Hard",
        "descriptions": "Shapes and Words"
    },
    "Hard": {
        "requiredPoints": 30,
        "timeLimit": 10,
        "shapes": SHAPES,
        "next": None,
        "descriptions": "Shapes and Sides"
    },
}

COLORS = {
    "bg":      "#0a0a0f",
    "card":    "#13131a",
    "accent":  "#6366f1",
    "text":    "#f1f5f9",
    "correct": "#10b981",
    "wrong":   "#f43f5e",
    "bon_ins": "#a5b4fc"
}

# Distinct fill colors per shape for instant recognition
SHAPE_COLORS = {
    "circle":   "#e040fb",   # magenta
    "square":   "#00bcd4",   # cyan
    "triangle": "#ffb300",   # amber
    "star":     "#f43f5e",   # red-pink
    "hexagon":  "#10b981",   # emerald
    "heart":    "#ff6b6b",   # coral red
    "diamond":  "#818cf8",   # periwinkle
    "pentagon": "#fb923c",   # orange
    "octagon":  "#34d399",   # mint
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
        print(f"Image loading error ({path}): {e}")
        return None


class ShapeTowerGame:

    def __init__(self, root):
        self.root = root
        self.root.title("TOWER NI JES")
        self.root.geometry("800x600")
        self.root.configure(bg=COLORS["bg"])


        self.difficulty      = "Easy"
        self.points          = 0
        self.current_level   = 1
        self.time_left       = 0
        self.status          = "splash"
        self.unlocked_towers = ["Easy"]

        self.target_shape   = None
        self.options        = []
        self.option_types   = []

        self.timer_running  = False
        self.main_timer_id  = None
        self.next_level_id  = None

        self.last_target_id       = None
        self.target_display_type  = "char"
        self.target_example_index = 0

        self.image_cache = {}
        self.drag_data   = {"x": 0, "y": 0, "item": None}

        self.drag_anim_id    = None
        self.drag_anim_tick  = 0
        self.drag_is_grabbed = False

        self._resize_after_id = None

        # Bonus round state
        self.bonus_after_levels  = random.randint(2, 3)   # trigger after this many levels
        self.levels_since_bonus  = 0
        self.bonus_active        = False
        self.bonus_time_left     = 10
        self.bonus_word          = ""
        self.bonus_entry_var     = None
        self.bonus_countdown_id  = None

        self.root.bind("<Configure>", self.on_window_resize)
        self.setup_ui()

    def on_window_resize(self, event):
        if event.widget == self.root:
            # Debounce resize events to avoid excessive redraws
            if self._resize_after_id:
                self.root.after_cancel(self._resize_after_id)
            if self.status == "playing":
                self._resize_after_id = self.root.after(50, self.render_game)
            elif self.status == "menu":
                self._resize_after_id = self.root.after(50, self._redraw_menu_from_resize)
            elif self.status == "splash":
                self._resize_after_id = self.root.after(50, self.show_splash)
            elif self.status == "credits":
                self._resize_after_id = self.root.after(50, self.show_credits)

    def _redraw_menu_from_resize(self):
        self._resize_after_id = None
        self.root.update_idletasks()
        W = self.root.winfo_width()
        H = self.root.winfo_height()
        if W > 1 and H > 1:
            self._draw_menu(W, H)

    def setup_ui(self):
        self.main_container = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_container.pack(fill="both", expand=True)
        self.show_splash()

    def clear_container(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    # =========================================================================
    # SPLASH SCREEN
    # =========================================================================
    def show_splash(self):
        self.cancel_all_timers()
        self.clear_container()
        self.status = "splash"

        self.root.update_idletasks()
        W = self.root.winfo_width()  or 800
        H = self.root.winfo_height() or 600

        splash_canvas = tk.Canvas(
            self.main_container,
            highlightthickness=0, bd=0
        )
        splash_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.root.update_idletasks()
        cw = self.main_container.winfo_width()
        ch = self.main_container.winfo_height()
        if cw > 1: W = cw
        if ch > 1: H = ch

        self._splash_bg_photo = None
        bg_path = os.path.join(SCRIPT_DIR, "bg.jpg")
        if PIL_AVAILABLE and os.path.exists(bg_path):
            try:
                img = Image.open(bg_path)
                if img.height > img.width:
                    img = img.rotate(-90, expand=True)
                img = img.resize((W, H), Image.LANCZOS)
                self._splash_bg_photo = ImageTk.PhotoImage(img)
                splash_canvas.create_image(0, 0, anchor="nw", image=self._splash_bg_photo)
            except Exception as e:
                print(f"Splash bg error: {e}")
                splash_canvas.configure(bg=COLORS["bg"])
        else:
            splash_canvas.configure(bg=COLORS["bg"])

        splash_canvas.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")

        panel_bg = "#0d0d18"
        wrapper = tk.Frame(
            self.main_container,
            bg=panel_bg,
            padx=30, pady=20,
            highlightthickness=1,
            highlightbackground="#00bcd4"
        )
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        deco_top = tk.Frame(wrapper, bg=panel_bg)
        deco_top.pack(pady=(0, 8))
        deco_colors_top  = ["#6366f1", "#10b981", "#a5b4fc", "#f43f5e", "#818cf8"]
        deco_shapes_top  = ["●",        "▲",       "■",       "⬟",       "★"]
        for col, shape in zip(deco_colors_top, deco_shapes_top):
            tk.Label(deco_top, text=shape, font=("Helvetica", 14),
                     bg=panel_bg, fg=col).pack(side="left", padx=3)

        tk.Label(
            wrapper,
            text="TOWER NI JES",
            font=("Helvetica", 48, "bold"),
            bg=panel_bg, fg="#e040fb"
        ).pack()

        deco_bot = tk.Frame(wrapper, bg=panel_bg)
        deco_bot.pack(pady=(8, 20))
        deco_colors_bot = ["#818cf8", "#f43f5e", "#a5b4fc", "#10b981", "#6366f1"]
        deco_shapes_bot = ["⬡",        "◯",       "▼",       "✦",       "▣"]
        for col, shape in zip(deco_colors_bot, deco_shapes_bot):
            tk.Label(deco_bot, text=shape, font=("Helvetica", 14),
                     bg=panel_bg, fg=col).pack(side="left", padx=3)

        play_btn = tk.Button(
            wrapper,
            text="  PLAY  ",
            command=self.show_menu,
            font=("Helvetica", 18, "bold"),
            bg="#00bcd4", fg="#ffffff",
            activebackground="#4dd0e1", activeforeground="#ffffff",
            padx=30, pady=12,
            borderwidth=0, cursor="hand2",
            relief="flat"
        )
        play_btn.pack(pady=(0, 12), fill="x")
        play_btn.bind("<Enter>", lambda e: play_btn.config(bg="#4dd0e1"))
        play_btn.bind("<Leave>", lambda e: play_btn.config(bg="#00bcd4"))

        credits_btn = tk.Button(
            wrapper,
            text="  CREDITS  ",
            command=self.show_credits,
            font=("Helvetica", 18, "bold"),
            bg="#7c3aed", fg="#ffffff",
            activebackground="#9d5cf6", activeforeground="#ffffff",
            padx=30, pady=12,
            borderwidth=0, cursor="hand2",
            relief="flat"
        )
        credits_btn.pack(fill="x", pady=(0, 12))
        credits_btn.bind("<Enter>", lambda e: credits_btn.config(bg="#9d5cf6"))
        credits_btn.bind("<Leave>", lambda e: credits_btn.config(bg="#7c3aed"))

        exit_btn = tk.Button(
            wrapper,
            text="  EXIT  ",
            command=self.root.destroy,
            font=("Helvetica", 18, "bold"),
            bg="#e91e8c", fg="#ffffff",
            activebackground="#f06ab0", activeforeground="#ffffff",
            padx=30, pady=12,
            borderwidth=0, cursor="hand2",
            relief="flat"
        )
        exit_btn.pack(fill="x")
        exit_btn.bind("<Enter>", lambda e: exit_btn.config(bg="#f06ab0"))
        exit_btn.bind("<Leave>", lambda e: exit_btn.config(bg="#e91e8c"))

    # =========================================================================
    # CREDITS SCREEN
    # =========================================================================
    def show_credits(self):
        self.cancel_all_timers()
        self.clear_container()
        self.status = "credits"

        # Full-window dark background so no grey shows through
        bg_fill = tk.Frame(self.main_container, bg=COLORS["bg"])
        bg_fill.place(x=0, y=0, relwidth=1, relheight=1)

        wrapper = tk.Frame(self.main_container, bg=COLORS["bg"])
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            wrapper,
            text="CREDITS",
            font=("Helvetica", 30, "bold"),
            bg=COLORS["bg"], fg=COLORS["accent"]
        ).pack(pady=(0, 30))

        card = tk.Frame(wrapper, bg=COLORS["card"], padx=40, pady=30,
                        highlightthickness=1, highlightbackground="#0d1b2a")
        card.pack()

        credits_entries = [
            ("GAME DESIGN",   "CABAÑAL, DELATINA, NIEVES, JABAT"),
            ("PROGRAMMING",   "CABAÑAL, JABAT"),
            ("IMAGES",  "CABAÑAL, DELATINA, NIEVES, JABAT"),
            ("IMAGES SOURCES","PINTEREST, W0CKENFUSS, FACEBOOK, SHUTTERSHOCK"),
        ]

        for role, name in credits_entries:
            row = tk.Frame(card, bg=COLORS["card"])
            row.pack(fill="x", pady=6)

            tk.Label(
                row, text=role,
                font=("Helvetica", 9, "bold"),
                bg=COLORS["card"], fg="#64748b",
                width=16, anchor="e"
            ).pack(side="left", padx=(0, 12))

            tk.Label(
                row, text=name,
                font=("Helvetica", 13, "bold"),
                bg=COLORS["card"], fg=COLORS["bon_ins"],
                anchor="w"
            ).pack(side="left")

        tk.Frame(wrapper, bg="#1e1e2e", height=1, width=300).pack(pady=24)

        back_btn = tk.Button(
            wrapper,
            text="BACK",
            command=self.show_splash,
            font=("Helvetica", 12, "bold"),
            bg=COLORS["card"], fg=COLORS["text"],
            activebackground="#1e1e2e", activeforeground=COLORS["text"],
            padx=24, pady=8,
            borderwidth=0, cursor="hand2",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2d2d3f"
        )
        back_btn.pack()
        back_btn.bind("<Enter>", lambda e: back_btn.config(bg="#1e1e2e"))
        back_btn.bind("<Leave>", lambda e: back_btn.config(bg=COLORS["card"]))

    # =========================================================================
    # MAIN MENU
    # =========================================================================
    def show_menu(self):
        self.cancel_all_timers()
        self.clear_container()
        self.status = "menu"
        self.root.update_idletasks()
        W = self.root.winfo_width()  or 800
        H = self.root.winfo_height() or 600
        self._draw_menu(W, H)

    def _draw_menu(self, W, H):
        # Clear and redraw everything on one canvas
        for w in self.main_container.winfo_children():
            w.destroy()

        menu_canvas = tk.Canvas(
            self.main_container,
            highlightthickness=0, bd=0,
            bg="#000000"
        )
        menu_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._menu_canvas = menu_canvas

        # Background image - use actual window size
        self._menu_bg_photo = None
        bg_path = os.path.join(SCRIPT_DIR, "bg.jpg")
        if PIL_AVAILABLE and os.path.exists(bg_path):
            try:
                img = Image.open(bg_path)
                if img.height > img.width:
                    img = img.rotate(-90, expand=True)
                img = img.resize((W, H), Image.LANCZOS)
                self._menu_bg_photo = ImageTk.PhotoImage(img)
                menu_canvas.create_image(0, 0, anchor="nw", image=self._menu_bg_photo)
            except Exception as e:
                print(f"Menu bg error: {e}")

        # Dark overlay
        menu_canvas.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")

        # Title - scaled to window height
        title_fs = max(14, int(H * 0.055))
        menu_canvas.create_text(
            W / 2, int(H * 0.07),
            text="SELECT TOWER",
            font=("Helvetica", title_fs, "bold"),
            fill="#e040fb"
        )

        diff_styles = {
            "Easy":   {"fill": "#e91e8c", "hover": "#f06ab0", "locked": "#1a0a14"},
            "Medium": {"fill": "#00bcd4", "hover": "#4dd0e1", "locked": "#001a1f"},
            "Hard":   {"fill": "#7c3aed", "hover": "#9d5cf6", "locked": "#120a1f"},
        }

        # Pyramid: use more of the window space, scale properly
        pyramid_w = int(W * 0.72)
        pyramid_h = int(H * 0.70)
        off_x = (W - pyramid_w) / 2
        off_y = int(H * 0.12)

        cx     = pyramid_w // 2
        apex_y = int(pyramid_h * 0.03)
        base_y = pyramid_h - int(pyramid_h * 0.03)
        total_h = base_y - apex_y
        half_b  = int(pyramid_w * 0.48)

        def x_at(t):
            return cx - t * half_b, cx + t * half_b

        # Equal-height thirds
        t1 = 1/3;  y1 = apex_y + total_h * t1
        t2 = 2/3;  y2 = apex_y + total_h * t2
        y0 = apex_y
        y3 = base_y

        l1, r1 = x_at(t1)
        l2, r2 = x_at(t2)
        l3, r3 = x_at(1.0)

        sections = [
            ("Hard",   [cx, y0, l1, y1, r1, y1]),
            ("Medium", [l1, y1, l2, y2, r2, y2, r1, y1]),
            ("Easy",   [l2, y2, l3, y3, r3, y3, r2, y2]),
        ]
        text_ys = {
            "Hard":   (y0 + y1) / 2,
            "Medium": (y1 + y2) / 2,
            "Easy":   (y2 + y3) / 2,
        }

        # Compute actual pixel widths at the vertical midpoint of each band
        def band_pixel_width(diff):
            if diff == "Hard":
                mid_t = (0 + t1) / 2
            elif diff == "Medium":
                mid_t = (t1 + t2) / 2
            else:
                mid_t = (t2 + 1.0) / 2
            lx, rx = x_at(mid_t)
            return int((rx - lx) * 0.78)

        # Font sizes: scale by both window size and available band width
        def calc_font_sizes(diff):
            bw = band_pixel_width(diff)
            base_title = max(7, int(min(pyramid_h * 0.052, bw * 0.13)))
            base_desc  = max(5, int(min(pyramid_h * 0.030, bw * 0.075)))
            base_lock  = max(5, int(min(pyramid_h * 0.026, bw * 0.065)))
            return base_title, base_desc, base_lock

        def shift(pts):
            return [pts[i] + off_x if i % 2 == 0 else pts[i] + off_y
                    for i in range(len(pts))]

        for diff, pts in sections:
            config    = TOWER_CONFIG[diff]
            is_locked = diff not in self.unlocked_towers
            style     = diff_styles[diff]
            fill      = style["locked"] if is_locked else style["fill"]
            ty        = text_ys[diff] + off_y
            tcx       = cx + off_x
            bw        = band_pixel_width(diff)
            tfs, dfs, lfs = calc_font_sizes(diff)

            poly = menu_canvas.create_polygon(
                shift(pts), fill=fill, outline="#000000", width=2
            )

            # Title label
            menu_canvas.create_text(
                tcx, ty - int(pyramid_h * 0.045),
                text=diff.upper(),
                font=("Helvetica", tfs, "bold"),
                fill="#ffffff" if not is_locked else "#333355"
            )

            # Description — use wraplength based on available band width
            menu_canvas.create_text(
                tcx, ty + int(pyramid_h * 0.008),
                text=config["descriptions"],
                font=("Helvetica", dfs),
                fill="#dddddd" if not is_locked else "#333355",
                width=max(bw, 30), justify="center"
            )

            if is_locked:
                menu_canvas.create_text(
                    tcx, ty + int(pyramid_h * 0.065),
                    text="LOCKED",
                    font=("Helvetica", lfs, "bold"),
                    fill="#ff4081"
                )
            else:
                def _bind(poly_id, f, h, d):
                    menu_canvas.tag_bind(poly_id, "<Enter>",
                        lambda e, p=poly_id, hc=h: menu_canvas.itemconfig(p, fill=hc))
                    menu_canvas.tag_bind(poly_id, "<Leave>",
                        lambda e, p=poly_id, fc=f: menu_canvas.itemconfig(p, fill=fc))
                    menu_canvas.tag_bind(poly_id, "<Button-1>",
                        lambda e, diff=d: self.start_tower(diff))
                _bind(poly, fill, style["hover"], diff)

        # Back button at bottom, scaled
        btn_y = int(H * 0.93)
        btn_w = int(W * 0.16)
        back_box = menu_canvas.create_rectangle(
            W/2 - btn_w, btn_y - int(H*0.032),
            W/2 + btn_w, btn_y + int(H*0.032),
            fill="#1a0a2e", outline="#7c3aed", width=1
        )
        back_txt = menu_canvas.create_text(
            W/2, btn_y,
            text="◀  BACK TO TITLE",
            font=("Helvetica", max(9, int(H * 0.022)), "bold"),
            fill="#ce93d8"
        )
        for item in (back_box, back_txt):
            menu_canvas.tag_bind(item, "<Enter>",
                lambda e: [menu_canvas.itemconfig(back_box, fill="#7c3aed"),
                           menu_canvas.itemconfig(back_txt, fill="#ffffff")])
            menu_canvas.tag_bind(item, "<Leave>",
                lambda e: [menu_canvas.itemconfig(back_box, fill="#1a0a2e"),
                           menu_canvas.itemconfig(back_txt, fill="#ce93d8")])
            menu_canvas.tag_bind(item, "<Button-1>", lambda e: self.show_splash())

    # =========================================================================
    # GAME LOGIC
    # =========================================================================
    def start_tower(self, diff):
        self.difficulty         = diff
        self.points             = 0
        self.current_level      = 1
        self.last_target_id     = None
        self.levels_since_bonus = 0
        self.bonus_after_levels = random.randint(2, 3)
        self.status             = "playing"
        self.generate_level()
        self.render_game()

    def generate_level(self):
        self.cancel_all_timers()

        config    = TOWER_CONFIG[self.difficulty]
        available = config["shapes"]

        valid_shapes = [s for s in available if s["id"] != self.last_target_id]
        if not valid_shapes:
            valid_shapes = available

        self.target_example_index = random.randint(1, 5)
        self.target_display_type  = "image"

        if self.difficulty == "Hard":
            self.target_shape = random.choice(valid_shapes)
            target_sides      = self.target_shape["sides"]

            others_pool = [s for s in available if s["sides"] != target_sides]

            sides_map = {}
            for s in others_pool:
                if s["sides"] not in sides_map:
                    sides_map[s["sides"]] = s

            unique_side_shapes = list(sides_map.values())
            random.shuffle(unique_side_shapes)
            selected_others = unique_side_shapes[:2]

            self.options = [self.target_shape] + selected_others

            if random.random() > 0.5:
                self.option_types = ["sides", "sides", "sides"]
            else:
                self.option_types = ["ascii", "ascii", "ascii"]

        else:
            self.target_shape   = random.choice(valid_shapes)
            others              = [s for s in available if s["id"] != self.target_shape["id"]]
            random.shuffle(others)
            selected_others     = others[:2]
            self.options        = [self.target_shape] + selected_others

            if self.difficulty == "Medium":
                mode = "2s1w" if random.random() > 0.5 else "2w1s"
                if mode == "2s1w":
                    self.option_types = ["ascii", "ascii", "word"]
                else:
                    self.option_types = ["word", "word", "ascii"]
                random.shuffle(self.option_types)
            else:
                self.option_types = ["ascii", "ascii", "ascii"]

        self.last_target_id = self.target_shape["id"]
        random.shuffle(self.options)

        self.time_left     = config["timeLimit"]
        self.timer_running = True

    def get_cached_image(self, shape_id, index, size=(90, 90)):
        cache_key = f"{shape_id}_{index}_{size[0]}x{size[1]}"
        if cache_key not in self.image_cache:
            path = resolve_image_path(shape_id, index)
            self.image_cache[cache_key] = load_image(path, size)
        return self.image_cache[cache_key]

    # =========================================================================
    # SHAPE DRAWING (replaces ASCII art)
    # =========================================================================
    def draw_shape_on_canvas(self, canvas, shape_id, cx, cy, size, color, bg_color):
        """Draw a clean vector shape centered at (cx,cy) fitting within `size` pixels.
        If color is None, uses the per-shape color from SHAPE_COLORS."""
        if color is None:
            color = SHAPE_COLORS.get(shape_id, "#e040fb")
        import math
        r = size * 0.44  # radius / half-size with small margin

        def ngon(n, rot=0):
            pts = []
            for i in range(n):
                angle = math.pi * 2 * i / n + rot
                pts += [cx + r * math.cos(angle), cy + r * math.sin(angle)]
            return pts

        if shape_id == "circle":
            canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                               fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "square":
            canvas.create_rectangle(cx-r, cy-r, cx+r, cy+r,
                                    fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "triangle":
            pts = ngon(3, rot=-math.pi/2)
            canvas.create_polygon(pts, fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "star":
            pts = []
            for i in range(10):
                angle = math.pi * 2 * i / 10 - math.pi / 2
                rad   = r if i % 2 == 0 else r * 0.42
                pts  += [cx + rad * math.cos(angle), cy + rad * math.sin(angle)]
            canvas.create_polygon(pts, fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "hexagon":
            pts = ngon(6, rot=0)
            canvas.create_polygon(pts, fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "heart":
            # Heart drawn with two arcs + polygon approximation
            pts = []
            steps = 40
            for i in range(steps + 1):
                t = math.pi * 2 * i / steps
                hx = r * 0.9 * (16 * math.sin(t)**3) / 16
                hy = -r * 0.9 * (13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t)) / 13
                pts += [cx + hx, cy + hy * 0.88 + r * 0.08]
            canvas.create_polygon(pts, fill=color, outline=bg_color,
                                  smooth=True, width=max(2, int(size*0.03)))

        elif shape_id == "diamond":
            pts = [cx, cy-r,  cx+r*0.65, cy,  cx, cy+r,  cx-r*0.65, cy]
            canvas.create_polygon(pts, fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "pentagon":
            pts = ngon(5, rot=-math.pi/2)
            canvas.create_polygon(pts, fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        elif shape_id == "octagon":
            pts = ngon(8, rot=math.pi/8)
            canvas.create_polygon(pts, fill=color, outline=bg_color, width=max(2, int(size*0.03)))

        else:
            # Fallback: circle
            canvas.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color, outline=bg_color)

    def play_sound(self, kind):
        """Play a non-blocking beep. kind = 'correct', 'wrong', or 'bonus'."""
        if not WINSOUND_AVAILABLE:
            return
        if kind == "correct":
            # RPG correct — soft harp-like item pickup
            def _play():
                winsound.Beep(659,  60)  # E5
                winsound.Beep(784,  60)  # G5
                winsound.Beep(988,  60)  # B5
                winsound.Beep(1319, 150) # E6
            threading.Thread(target=_play, daemon=True).start()
        elif kind == "wrong":
            # RPG wrong — deep dungeon thud / error toll
            def _play():
                winsound.Beep(196, 150)  # G3
                winsound.Beep(147, 250)  # D3
            threading.Thread(target=_play, daemon=True).start()
        elif kind == "bonus":
            # RPG bonus — triumphant chest-open fanfare
            def _play():
                winsound.Beep(523,  80)  # C5
                winsound.Beep(659,  80)  # E5
                winsound.Beep(784,  80)  # G5
                winsound.Beep(659,  60)  # E5
                winsound.Beep(784,  60)  # G5
                winsound.Beep(1047, 80)  # C6
                winsound.Beep(1319, 300) # E6
            threading.Thread(target=_play, daemon=True).start()

    def render_game(self):
        self.clear_container()
        self.root.update_idletasks()

        canv_w = self.root.winfo_width()
        canv_h = self.root.winfo_height()
        if canv_w <= 1: canv_w = 800
        if canv_h <= 1: canv_h = 600

        scale_x = canv_w / 800
        scale_y = canv_h / 600
        scale   = min(scale_x, scale_y)

        G_BG         = "#0a0010"
        G_CARD       = "#150020"
        G_BORDER     = "#7c3aed"
        G_TEXT       = "#f0e6ff"
        G_MUTED      = "#ce93d8"
        G_ACCENT     = "#e040fb"
        G_ACCENT2    = "#00bcd4"
        G_DRAG_FILL  = "#1a0030"
        G_DRAG_OUT   = "#e91e8c"
        G_HINT       = "#ce93d8"
        G_TARGET_LBL = "#7c3aed"

        self.root.configure(bg=G_BG)
        self.main_container.configure(bg=G_BG)

        header = tk.Frame(self.main_container, bg=G_BG, pady=int(10 * scale_y))
        header.pack(fill="x", padx=int(40 * scale_x))

        tk.Label(
            header, text=f"{self.difficulty.upper()}  ·  LEVEL {self.current_level} / 5",
            font=("Helvetica", int(10 * scale), "bold"),
            bg=G_BG, fg=G_MUTED
        ).pack(side="left")

        self.score_label = tk.Label(
            header, text=f"SCORE  {self.points}",
            font=("Helvetica", int(10 * scale), "bold"),
            bg=G_BG, fg=G_TEXT
        )
        self.score_label.pack(side="right")

        timer_frame = tk.Frame(self.main_container, bg=G_BG)
        timer_frame.pack(fill="x", padx=int(40 * scale_x))

        self.timer_label = tk.Label(
            timer_frame, text=f"{self.time_left:.1f}s",
            font=("Helvetica", int(13 * scale), "bold"),
            bg=G_BG, fg=G_MUTED
        )
        self.timer_label.pack(side="right")

        self.canvas = tk.Canvas(self.main_container, bg=G_BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Compute card layout from actual window size
        card_area_w = canv_w - int(80 * scale_x)
        card_area_h = canv_h * 0.38
        padding     = int(20 * scale_x)
        target_width  = (card_area_w - padding * 2) / 3
        target_height = card_area_h
        start_x = (canv_w - (3 * target_width + 2 * padding)) / 2

        self.target_rects = []

        for i, option in enumerate(self.options):
            x = start_x + i * (target_width + padding)
            y = int(30 * scale_y)

            self.canvas.create_rectangle(
                x - 1, y - 1, x + target_width + 1, y + target_height + 1,
                outline=G_BORDER, width=1, fill=""
            )
            self.canvas.create_rectangle(
                x, y, x + target_width, y + target_height,
                outline=G_BORDER, width=2, fill=G_CARD
            )

            self.target_rects.append((x, y, x + target_width, y + target_height, option))

            display_type = self.option_types[i]
            font_size    = int(16 * scale)

            if display_type == "word":
                self.canvas.create_text(
                    x + target_width / 2, y + target_height / 2,
                    text=option["name"].upper(), fill=G_TEXT,
                    font=("Helvetica", font_size, "bold")
                )
            elif display_type == "sides":
                # Scale the number font to fit the card width
                num_font_size = max(12, int(min(target_width * 0.38, target_height * 0.38)))
                sub_font_size = max(7,  int(min(target_width * 0.11, target_height * 0.11)))
                self.canvas.create_text(
                    x + target_width / 2, y + target_height / 2 - sub_font_size * 1.8,
                    text=str(option["sides"]), fill=G_ACCENT2,
                    font=("Helvetica", num_font_size, "bold")
                )
                self.canvas.create_text(
                    x + target_width / 2, y + target_height / 2 + num_font_size * 0.7,
                    text="sides", fill=G_MUTED,
                    font=("Helvetica", sub_font_size)
                )
            elif display_type == "image":
                slot_size = (int(target_width * 0.82), int(target_height * 0.82))
                photo     = self.get_cached_image(option["id"], 1, size=slot_size)
                if photo:
                    self.canvas.create_image(
                        x + target_width / 2, y + target_height / 2, image=photo
                    )
                else:
                    txt_font_size = max(8, int(min(target_width * 0.11, 14 * scale)))
                    self.canvas.create_text(
                        x + target_width / 2, y + target_height / 2,
                        text=option["Real_shapes"][0].upper(),
                        fill=G_ACCENT2,
                        font=("Helvetica", txt_font_size, "bold"),
                        width=int(target_width * 0.85)
                    )
            else:
                # Draw clean vector shape instead of ASCII art
                shape_size = int(min(target_width, target_height) * 0.78)
                self.draw_shape_on_canvas(
                    self.canvas, option["id"],
                    x + target_width / 2, y + target_height / 2,
                    shape_size, None, G_CARD
                )

            self.canvas.create_text(
                x + target_width / 2, y + target_height + int(14 * scale_y),
                text=f"drop here", fill=G_TARGET_LBL,
                font=("Helvetica", max(6, int(7 * scale)))
            )

        drag_w = int(min(canv_w * 0.14, 110 * scale))
        drag_h = drag_w
        self.drag_home_x = canv_w / 2
        self.drag_home_y = canv_h * 0.76

        self.drag_item_bg = self.canvas.create_rectangle(
            self.drag_home_x - drag_w / 2, self.drag_home_y - drag_h / 2,
            self.drag_home_x + drag_w / 2, self.drag_home_y + drag_h / 2,
            fill=G_DRAG_FILL, outline=G_DRAG_OUT, width=2
        )

        if self.target_display_type == "image":
            example_text = self.target_shape["Real_shapes"][self.target_example_index - 1]
            drag_size = (int(drag_w * 0.85), int(drag_h * 0.85))
            photo     = self.get_cached_image(
                self.target_shape["id"], self.target_example_index, size=drag_size
            )

            if photo:
                self.drag_item_content = self.canvas.create_image(
                    self.drag_home_x, self.drag_home_y, image=photo
                )
            else:
                hint_fs = max(8, int(min(drag_w * 0.11, 11 * scale)))
                self.drag_item_content = self.canvas.create_text(
                    self.drag_home_x, self.drag_home_y,
                    text=example_text.upper(), fill=G_TEXT,
                    font=("Helvetica", hint_fs, "bold"),
                    width=int(drag_w * 0.85), justify="center"
                )

            self.canvas.create_text(
                self.drag_home_x, self.drag_home_y + drag_h / 2 + int(18 * scale_y),
                text="match the object", fill=G_HINT,
                font=("Helvetica", max(6, int(8 * scale)))
            )
        else:
            char_fs = max(12, int(40 * scale))
            self.drag_item_content = self.canvas.create_text(
                self.drag_home_x, self.drag_home_y,
                text=self.target_shape["char"], fill=G_TEXT,
                font=("Helvetica", char_fs)
            )

        self.canvas.tag_bind(self.drag_item_bg, "<Button-1>",        self.on_drag_start)
        self.canvas.tag_bind(self.drag_item_bg, "<B1-Motion>",       self.on_drag_motion)
        self.canvas.tag_bind(self.drag_item_bg, "<ButtonRelease-1>", self.on_drag_release)

        self.canvas.tag_bind(self.drag_item_content, "<Button-1>",        self.on_drag_start)
        self.canvas.tag_bind(self.drag_item_content, "<B1-Motion>",       self.on_drag_motion)
        self.canvas.tag_bind(self.drag_item_content, "<ButtonRelease-1>", self.on_drag_release)

        if self.timer_running:
            if self.main_timer_id:
                self.root.after_cancel(self.main_timer_id)
            self.update_timer()

        self.drag_is_grabbed = False
        self.drag_anim_tick  = 0
        if self.drag_anim_id:
            self.root.after_cancel(self.drag_anim_id)
        self.drag_anim_id = self.root.after(30, self.animate_drag_item)

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
                self.timer_label.config(
                    text=f"{self.time_left:.1f}s",
                    fg=COLORS["wrong"] if self.time_left < 2 else "#475569"
                )
                self.main_timer_id = self.root.after(100, self.update_timer)
            except:
                self.main_timer_id = None

    def animate_drag_item(self):
        if self.status != "playing" or self.drag_is_grabbed:
            self.drag_anim_id = None
            return

        try:
            self.drag_anim_tick += 1
            t = self.drag_anim_tick

            bob_speed  = 0.07
            bob_amp    = 6
            prev_y = bob_amp * math.sin(bob_speed * (t - 1))
            curr_y = bob_amp * math.sin(bob_speed * t)
            dy     = curr_y - prev_y

            self.canvas.move(self.drag_item_bg,      0, dy)
            self.canvas.move(self.drag_item_content, 0, dy)

            glow_t     = (math.sin(bob_speed * 1.5 * t) + 1) / 2
            out_w      = int(2 + glow_t * 3)
            r = int(0x1a + glow_t * (0xe9 - 0x1a))
            g = int(0x00 + glow_t * (0x1e - 0x00))
            b = int(0x30 + glow_t * (0x8c - 0x30))
            glow_color = f"#{r:02x}{g:02x}{b:02x}"

            self.canvas.itemconfig(self.drag_item_bg,
                                   outline=glow_color, width=out_w)

            self.drag_anim_id = self.root.after(30, self.animate_drag_item)

        except Exception:
            self.drag_anim_id = None

    def on_drag_start(self, event):
        self.drag_is_grabbed = True
        if self.drag_anim_id:
            self.root.after_cancel(self.drag_anim_id)
            self.drag_anim_id = None
        try:
            self.canvas.itemconfig(self.drag_item_bg, outline="#6366f1", width=2)
        except Exception:
            pass
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
        x, y       = event.x, event.y
        dropped_on = None
        drop_rect  = None

        for rx1, ry1, rx2, ry2, shape in self.target_rects:
            if rx1 <= x <= rx2 and ry1 <= y <= ry2:
                dropped_on = shape
                drop_rect  = (rx1, ry1, rx2, ry2)
                break

        if dropped_on:
            if dropped_on["id"] == self.target_shape["id"]:
                self.handle_success(drop_rect)
            else:
                self.handle_failure(drop_rect)
        else:
            self.drag_is_grabbed = False
            bbox = self.canvas.bbox(self.drag_item_bg)
            if bbox:
                w = (bbox[2] - bbox[0]) / 2
                h = (bbox[3] - bbox[1]) / 2
                self.canvas.coords(
                    self.drag_item_bg,
                    self.drag_home_x - w, self.drag_home_y - h,
                    self.drag_home_x + w, self.drag_home_y + h
                )
            self.canvas.coords(self.drag_item_content, self.drag_home_x, self.drag_home_y)
            if not self.drag_anim_id:
                self.drag_anim_id = self.root.after(30, self.animate_drag_item)

    def handle_success(self, drop_rect=None):
        self.timer_running = False
        config  = TOWER_CONFIG[self.difficulty]
        earned  = max(1, int(10 * (self.time_left / config["timeLimit"])))
        self.points += earned

        self.play_sound("correct")
        self.canvas.itemconfig(self.drag_item_bg,
                               fill=COLORS["correct"], outline=COLORS["correct"])

        if drop_rect:
            self.animate_match(drop_rect)
        else:
            if self.next_level_id:
                self.root.after_cancel(self.next_level_id)
            self.next_level_id = self.root.after(600, self.next_level)

    def animate_match(self, drop_rect):
        rx1, ry1, rx2, ry2 = drop_rect
        cx = (rx1 + rx2) / 2
        cy = (ry1 + ry2) / 2

        FRAMES  = 20
        SPARKS  = 10
        COLORS_FW = ["#10b981", "#6366f1", "#a5b4fc", "#34d399",
                     "#818cf8", "#f1f5f9", "#10b981", "#6366f1",
                     "#34d399", "#a5b4fc"]

        sparks = []
        for i in range(SPARKS):
            angle = (2 * math.pi / SPARKS) * i
            speed = random.uniform(5.0, 9.0)
            sparks.append({
                "x":  cx, "y": cy,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "dot": self.canvas.create_oval(
                    cx - 4, cy - 4, cx + 4, cy + 4,
                    fill=COLORS_FW[i], outline=""
                )
            })

        border = self.canvas.create_rectangle(
            rx1, ry1, rx2, ry2,
            outline="#10b981", width=3, fill=""
        )

        frame_ref = [0]

        def _step():
            f = frame_ref[0]
            frame_ref[0] += 1

            if f >= FRAMES:
                for s in sparks:
                    try: self.canvas.delete(s["dot"])
                    except: pass
                try: self.canvas.delete(border)
                except: pass
                if self.next_level_id:
                    self.root.after_cancel(self.next_level_id)
                self.next_level_id = self.root.after(60, self.next_level)
                return

            t = f / FRAMES

            for s in sparks:
                s["x"] += s["vx"]
                s["y"] += s["vy"]
                s["vx"] *= 0.85
                s["vy"] *= 0.85
                size = max(1, int(4 * (1 - t)))
                try:
                    self.canvas.coords(s["dot"],
                        s["x"] - size, s["y"] - size,
                        s["x"] + size, s["y"] + size)
                except: pass

            src = (0x10, 0xb9, 0x81)
            bg  = (0x16, 0x16, 0x2a)
            r = int(src[0] + (bg[0] - src[0]) * t)
            g = int(src[1] + (bg[1] - src[1]) * t)
            b = int(src[2] + (bg[2] - src[2]) * t)
            try:
                self.canvas.itemconfig(border, outline=f"#{r:02x}{g:02x}{b:02x}")
            except: pass

            self.root.after(30, _step)

        _step()

    def handle_failure(self, drop_rect=None):
        self.timer_running = False
        self.play_sound("wrong")
        self.canvas.itemconfig(self.drag_item_bg, fill=COLORS["wrong"],
                               outline=COLORS["wrong"])
        self.animate_wrong(drop_rect)

    def animate_wrong(self, drop_rect=None):
        FRAMES     = 16
        shake_seq  = [8, -8, 6, -6, 4, -4, 2, -2, 1, -1, 0, 0, 0, 0, 0, 0]

        border = None
        if drop_rect:
            rx1, ry1, rx2, ry2 = drop_rect
            border = self.canvas.create_rectangle(
                rx1, ry1, rx2, ry2,
                outline=COLORS["wrong"], width=3, fill=""
            )

        frame_ref  = [0]
        home_x     = self.drag_home_x

        def _step():
            f = frame_ref[0]
            frame_ref[0] += 1

            if f >= FRAMES:
                try:
                    bbox = self.canvas.bbox(self.drag_item_bg)
                    if bbox:
                        w  = (bbox[2] - bbox[0]) / 2
                        h  = (bbox[3] - bbox[1]) / 2
                        cy = (bbox[1] + bbox[3]) / 2
                        self.canvas.coords(self.drag_item_bg,
                                           home_x - w, cy - h,
                                           home_x + w, cy + h)
                        self.canvas.coords(self.drag_item_content, home_x, cy)
                except: pass
                if border:
                    try: self.canvas.delete(border)
                    except: pass
                if self.next_level_id:
                    self.root.after_cancel(self.next_level_id)
                self.next_level_id = self.root.after(60, self.next_level)
                return

            t = f / FRAMES

            offset = shake_seq[f] if f < len(shake_seq) else 0
            try:
                bbox = self.canvas.bbox(self.drag_item_bg)
                if bbox:
                    w  = (bbox[2] - bbox[0]) / 2
                    h  = (bbox[3] - bbox[1]) / 2
                    cy = (bbox[1] + bbox[3]) / 2
                    nx = home_x + offset
                    self.canvas.coords(self.drag_item_bg,
                                       nx - w, cy - h, nx + w, cy + h)
                    self.canvas.coords(self.drag_item_content, nx, cy)
            except: pass

            if border:
                src = (0xf4, 0x3f, 0x5e)
                bg  = (0x16, 0x16, 0x2a)
                r = int(src[0] + (bg[0] - src[0]) * t)
                g = int(src[1] + (bg[1] - src[1]) * t)
                b = int(src[2] + (bg[2] - src[2]) * t)
                try:
                    self.canvas.itemconfig(border, outline=f"#{r:02x}{g:02x}{b:02x}")
                except: pass

            self.root.after(30, _step)

        _step()

    def next_level(self):
        self.next_level_id = None
        self.levels_since_bonus += 1

        if self.current_level >= 5:
            self.finish_tower()
        else:
            self.current_level += 1
            # Check if bonus round should fire before the next level
            if self.levels_since_bonus >= self.bonus_after_levels:
                self.levels_since_bonus = 0
                self.bonus_after_levels = random.randint(2, 3)
                self.generate_level()          # prepare next level silently
                self.render_game()             # render the game screen first
                self.root.after(120, self.show_bonus_popup)  # then show popup over it
            else:
                self.generate_level()
                self.render_game()


    BONUS_WORDS = [
        # Shape / geometry words
        'TRIANGLE', 'HEXAGON', 'OCTAGON', 'CIRCLE', 'DIAMOND',
        'POLYGON', 'VERTEX', 'SHAPE', 'SQUARE', 'PENTAGON',
        'PRISM', 'SPHERE', 'RHOMBUS', 'GEOMETRY', 'TRAPEZOID',
        'CYLINDER', 'ELLIPSE', 'PARALLEL', 'TANGENT', 'RADIUS',
        # Random alphanumeric gibberish codes
        '3DAFY3', 'X7KQ2', 'B4NZ9W', 'R2T8M', 'W9XJ4K',
        'Q5VL7', 'Z3PH8N', 'K6YT2X', 'M4WR9', 'J8FN3C',
        'T2KX7B', 'P9ZQ4', 'H3MV6W', 'N7BF2K', 'C5XR8',
        'G4JT9M', 'V6NZ3', 'F8KW2P', 'L3QH7X', 'D9YM4B',
        'A7XK3Z', 'S2WP8N', 'E5TQ6', 'U4BF9J', 'Y3MV7C',
    ]

    def show_bonus_popup(self):
        """Draw bonus popup directly onto self.canvas so game stays visible behind it."""
        if self.status != "playing":
            return

        # Pause main timer
        self.timer_running = False
        if self.main_timer_id:
            self.root.after_cancel(self.main_timer_id)
            self.main_timer_id = None

        self.bonus_active    = True
        self.bonus_time_left = 10
        self._bonus_canvas_items = []   # track all canvas items to delete on close

        # Generate word / code
        if random.random() < 0.40:
            chars  = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            length = random.randint(4, 7)
            code   = (random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
                      + random.choice("23456789")
                      + ''.join(random.choices(chars, k=length - 2)))
            self.bonus_word = ''.join(random.sample(code, len(code)))
        else:
            self.bonus_word = random.choice(self.BONUS_WORDS)

        self.root.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10: cw = 600
        if ch < 10: ch = 400
        cx, cy = cw / 2, ch / 2

        # Card dimensions
        card_w, card_h = min(420, cw - 40), min(290, ch - 40)
        x0 = cx - card_w / 2
        y0 = cy - card_h / 2
        x1 = cx + card_w / 2
        y1 = cy + card_h / 2

        def _add(item):
            self._bonus_canvas_items.append(item)
            return item

        # Dim background — two stacked semi-dark rectangles to simulate transparency
        _add(self.canvas.create_rectangle(0, 0, cw, ch,
             fill="#000010", stipple="gray50", outline=""))
        _add(self.canvas.create_rectangle(0, 0, cw, ch,
             fill="#000010", stipple="gray75", outline=""))

        # Card shadow
        _add(self.canvas.create_rectangle(x0+6, y0+6, x1+6, y1+6,
             fill="#000000", outline="", width=0))
        # Card body
        _add(self.canvas.create_rectangle(x0, y0, x1, y1,
             fill="#0d0018", outline="#ffb300", width=2))

        # Amber glow border (inner)
        _add(self.canvas.create_rectangle(x0+3, y0+3, x1-3, y1-3,
             fill="", outline="#7c3aed", width=1))

        row1_y = y0 + card_h * 0.15
        row2_y = y0 + card_h * 0.30
        row3_y = y0 + card_h * 0.48
        row4_y = y0 + card_h * 0.68
        row5_y = y0 + card_h * 0.82

        fs_title  = max(12, int(card_h * 0.09))
        fs_sub    = max(8,  int(card_h * 0.055))
        fs_word   = max(16, int(card_h * 0.16))
        fs_timer  = max(8,  int(card_h * 0.058))

        _add(self.canvas.create_text(cx, row1_y,
             text="!!!BONUS QUESTION!!!",
             font=("Helvetica", fs_title, "bold"),
             fill="#ffb300"))
        _add(self.canvas.create_text(cx, row2_y,
             text="Type it correctly to earn +6.7 more seconds",
             font=("Helvetica", fs_sub),
             fill="#ce93d8"))
        _add(self.canvas.create_text(cx, row3_y,
             text=self.bonus_word,
             font=("Helvetica", fs_word, "bold"),
             fill="#e040fb"))

        # Entry widget embedded in canvas via create_window
        self.bonus_entry_var = tk.StringVar()
        entry_w = int(card_w * 0.72)
        entry = tk.Entry(self.canvas,
                         textvariable=self.bonus_entry_var,
                         font=("Helvetica", max(12, int(card_h * 0.09)), "bold"),
                         bg="#1a0030", fg="#f0e6ff",
                         insertbackground="#e040fb",
                         relief="flat", bd=0,
                         highlightthickness=2,
                         highlightbackground="#7c3aed",
                         highlightcolor="#e040fb",
                         justify="center", width=14)
        self._bonus_entry_widget = entry
        win = self.canvas.create_window(cx, row4_y, window=entry,
                                        width=entry_w, height=int(card_h * 0.13))
        _add(win)
        entry.focus_set()
        entry.bind("<Return>", lambda e: self._check_bonus_answer())

        # Countdown text item — we'll update tag "bonus_timer" each tick
        self.bonus_timer_item = _add(self.canvas.create_text(
             cx, row5_y,
             text=f"⏱ {self.bonus_time_left}s remaining",
             font=("Helvetica", fs_timer, "bold"),
             fill="#ffb300", tags="bonus_timer"))

        # Feedback text item
        self.bonus_feedback_item = _add(self.canvas.create_text(
             cx, y1 - card_h * 0.06,
             text="",
             font=("Helvetica", max(8, int(card_h * 0.06)), "bold"),
             fill="#10b981", tags="bonus_feedback"))

        # Start countdown
        self._bonus_tick()

    def _bonus_tick(self):
        if not self.bonus_active:
            return
        if self.bonus_time_left <= 0:
            self._close_bonus(success=False)
            return
        try:
            color = "#f43f5e" if self.bonus_time_left <= 3 else "#ffb300"
            self.canvas.itemconfig(self.bonus_timer_item,
                text=f"⏱ {self.bonus_time_left}s remaining", fill=color)
        except Exception:
            pass
        self.bonus_time_left -= 1
        self.bonus_countdown_id = self.root.after(1000, self._bonus_tick)

    def _check_bonus_answer(self):
        if not self.bonus_active:
            return
        typed = self.bonus_entry_var.get().strip().upper()
        if typed == self.bonus_word:
            if self.bonus_countdown_id:
                self.root.after_cancel(self.bonus_countdown_id)
                self.bonus_countdown_id = None
            self.play_sound("bonus")
            try:
                self.canvas.itemconfig(self.bonus_feedback_item,
                    text="Nice blud here +6.7 seconds!", fill="#10b981")
            except Exception:
                pass
            self.root.after(700, lambda: self._close_bonus(success=True))
        else:
            try:
                self.canvas.itemconfig(self.bonus_feedback_item,
                    text="Wrong blud Try again!", fill="#f43f5e")
                self.bonus_entry_var.set("")
            except Exception:
                pass

    def _close_bonus(self, success):
        if not self.bonus_active:
            return
        self.bonus_active = False

        if self.bonus_countdown_id:
            self.root.after_cancel(self.bonus_countdown_id)
            self.bonus_countdown_id = None

        # Destroy the embedded Entry widget first
        if hasattr(self, "_bonus_entry_widget") and self._bonus_entry_widget:
            try:
                self._bonus_entry_widget.destroy()
            except Exception:
                pass
            self._bonus_entry_widget = None

        # Delete all canvas items drawn for the bonus popup
        if hasattr(self, "_bonus_canvas_items"):
            for item in self._bonus_canvas_items:
                try:
                    self.canvas.delete(item)
                except Exception:
                    pass
            self._bonus_canvas_items = []

        # Apply reward
        if success:
            self.time_left = min(self.time_left + 6.7,
                                 TOWER_CONFIG[self.difficulty]["timeLimit"] + 6.7)

        # Resume main game timer
        self.timer_running = True
        self.update_timer()

    def finish_tower(self):
        self.cancel_all_timers()
        self.status = "result"
        self.clear_container()

        W = self.root.winfo_width()  or 800
        H = self.root.winfo_height() or 600
        config  = TOWER_CONFIG[self.difficulty]
        success = self.points >= config["requiredPoints"]

        res_canvas = tk.Canvas(
            self.main_container, width=W, height=H,
            highlightthickness=0, bd=0
        )
        res_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self._result_bg_photo = None
        bg_path = os.path.join(SCRIPT_DIR, "bg.jpg")
        if PIL_AVAILABLE and os.path.exists(bg_path):
            try:
                img = Image.open(bg_path)
                if img.height > img.width:
                    img = img.rotate(-90, expand=True)
                img = img.resize((W, H), Image.LANCZOS)
                self._result_bg_photo = ImageTk.PhotoImage(img)
                res_canvas.create_image(0, 0, anchor="nw", image=self._result_bg_photo)
            except Exception as e:
                print(f"Result bg error: {e}")
                res_canvas.configure(bg="#0a0010")
        else:
            res_canvas.configure(bg="#0a0010")

        res_canvas.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")

        panel_bg = "#0d0018"
        border_col = "#00bcd4" if success else "#e91e8c"
        wrapper = tk.Frame(
            self.main_container,
            bg=panel_bg, padx=40, pady=30,
            highlightthickness=2,
            highlightbackground=border_col
        )
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        is_hard_win = success and self.difficulty == "Hard"

        if is_hard_win:
            title     = "!!YOUUU CONQUEREDD THE TOWER BLUDD!!"
            title_col = "#ffb300"
        elif success:
            title     = "!!TOWER COMPLETE!!"
            title_col = "#00bcd4"
        else:
            title     = "!!TOWER FAILED!!"
            title_col = "#e91e8c"

        tk.Label(wrapper, text=title,
                 font=("Helvetica", 22, "bold"),
                 bg=panel_bg, fg=title_col).pack(pady=(0, 10))

        if is_hard_win:
            tk.Label(wrapper,
                     text="!!DAMN ALL THREE TOWERS!!",
                     font=("Helvetica", 11, "bold"),
                     bg=panel_bg, fg="#e040fb").pack(pady=(0, 4))
            tk.Label(wrapper,
                     text="CHILL OUT",
                     font=("Helvetica", 10),
                     bg=panel_bg, fg="#ce93d8").pack(pady=(0, 14))

        tk.Label(wrapper, text=f"Final Score: {self.points}",
                 font=("Helvetica", 18, "bold"),
                 bg=panel_bg, fg="#f0e6ff").pack()

        tk.Label(wrapper, text=f"Required: {config['requiredPoints']}",
                 font=("Helvetica", 12),
                 bg=panel_bg, fg="#ce93d8").pack(pady=(4, 16))

        if success:
            next_tower = config["next"]
            if next_tower and next_tower not in self.unlocked_towers:
                self.unlocked_towers.append(next_tower)
            if is_hard_win:
                msg     = "YOU A GENIUS BLUD"
                msg_col = "#ffb300"
            else:
                msg     = "NEW TOWER UNLOCKED!" if next_tower else "VERYY GOODD BLUD!!"
                msg_col = "#e040fb"
        else:
            msg     = "TRY AGAIN BLUD!!"
            msg_col = "#ce93d8"

        tk.Label(wrapper, text=msg,
                 font=("Helvetica", 12, "bold"),
                 bg=panel_bg, fg=msg_col).pack(pady=(0, 20))

        btn_col   = "#00bcd4" if success else "#e91e8c"
        btn_hover = "#4dd0e1" if success else "#f06ab0"
        back_btn = tk.Button(
            wrapper, text="BACK TO MENU", command=self.show_menu,
            bg=btn_col, fg="#ffffff",
            font=("Helvetica", 12, "bold"),
            padx=24, pady=10, borderwidth=0, cursor="hand2", relief="flat"
        )
        back_btn.pack(fill="x")
        back_btn.bind("<Enter>", lambda e: back_btn.config(bg=btn_hover))
        back_btn.bind("<Leave>", lambda e: back_btn.config(bg=btn_col))

    def cancel_all_timers(self):
        if self.main_timer_id:
            self.root.after_cancel(self.main_timer_id)
            self.main_timer_id = None
        if self.next_level_id:
            self.root.after_cancel(self.next_level_id)
            self.next_level_id = None
        if self.drag_anim_id:
            self.root.after_cancel(self.drag_anim_id)
            self.drag_anim_id = None
        if self.bonus_countdown_id:
            self.root.after_cancel(self.bonus_countdown_id)
            self.bonus_countdown_id = None


if __name__ == "__main__":
    root = tk.Tk()
    game = ShapeTowerGame(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        root.destroy()
