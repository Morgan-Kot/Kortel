import customtkinter as ctk
import os
import subprocess
import requests
import threading

# --- CONFIGURATION ---
GITHUB_USER = "Morgan-Kot"
GITHUB_REPO = "KotliteBrowser" 
EXCLUSION_KEYWORD = "WEFA5"  # Any release containing this will be ignored
# ---------------------

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class GitHubAppLauncher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Kotlite App Launcher")
        
        # Window Scaling (80% of screen size)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        ww, wh = int(sw * 0.8), int(sh * 0.8)
        self.geometry(f"{ww}x{wh}+{(sw-ww)//2}+{(sh-wh)//2}")

        # Path Setup (Stores downloaded executables in AppData)
        self.base_path = os.path.join(os.getenv('APPDATA'), "KotliteLauncher")
        self.apps_folder = os.path.join(self.base_path, "apps")
        os.makedirs(self.apps_folder, exist_ok=True)

        # In-memory storage for apps fetched from GitHub
        self.apps_data = []
        self.category_list = ["All Categories"]

        # Layout Configuration
        self.grid_rowconfigure(0, weight=0)  # Filter / Header frame
        self.grid_rowconfigure(1, weight=1)  # Content area frame
        self.grid_columnconfigure(0, weight=1)

        # Setup UI
        self.setup_filter_bar()
        self.setup_apps_panel()

        # Start loading data in background thread
        threading.Thread(target=self.fetch_github_releases, daemon=True).start()

    def setup_filter_bar(self):
        """Creates the header, search input, and category dropdown."""
        self.header_frame = ctk.CTkFrame(self, corner_radius=10)
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Top section: Title and Status Label
        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="Kotlite App Hub", 
            font=("Helvetica", 28, "bold")
        )
        self.title_label.pack(anchor="w", padx=20, pady=(15, 5))

        self.status_label = ctk.CTkLabel(
            self.header_frame, 
            text="Syncing with GitHub releases...", 
            text_color="gray",
            font=("Helvetica", 12)
        )
        self.status_label.pack(anchor="w", padx=20, pady=(0, 15))

        # Bottom section: Search bar & Category filter
        self.filter_controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.filter_controls_frame.pack(fill="x", padx=20, pady=(0, 15))
        self.filter_controls_frame.grid_columnconfigure(0, weight=3)
        self.filter_controls_frame.grid_columnconfigure(1, weight=1)

        # Search Bar
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_apps())
        self.search_entry = ctk.CTkEntry(
            self.filter_controls_frame, 
            placeholder_text="🔍 Search applications...", 
            textvariable=self.search_var,
            font=("Helvetica", 14),
            height=40
        )
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        # Category Filter Dropdown
        self.category_var = ctk.StringVar(value="All Categories")
        self.category_dropdown = ctk.CTkComboBox(
            self.filter_controls_frame,
            values=self.category_list,
            variable=self.category_var,
            command=lambda v: self.refresh_apps(),
            font=("Helvetica", 14),
            height=40,
            state="readonly"
        )
        self.category_dropdown.grid(row=0, column=1, sticky="ew")

    def setup_apps_panel(self):
        """Creates the scrollable section where all matching apps are drawn."""
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, 
            label_text="Available App Installations", 
            label_font=("Helvetica", 16, "bold"),
            corner_radius=10
        )
        self.scroll_frame.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="nsew")

    def fetch_github_releases(self):
        """Scans the GitHub repository releases and filters based on parameters."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases"
            response = requests.get(url)
            releases = response.json()

            if not isinstance(releases, list):
                self.after(0, lambda: self.status_label.configure(text="Error parsing GitHub response", text_color="red"))
                return

            self.apps_data = []
            categories = {"All Categories"}

            for release in releases:
                # 1. Identify Name, Tag, and Body
                name = release.get("name") or release.get("tag_name") or "Unknown App"
                version = release.get("tag_name", "v1.0")
                body = release.get("body", "") or ""

                # --- EXCLUSION CHECK ---
                # Skip release if exclusion keyword is found anywhere in the release
                if (EXCLUSION_KEYWORD in name) or (EXCLUSION_KEYWORD in version) or (EXCLUSION_KEYWORD in body):
                    continue

                # 2. Extract Category and Description from the body
                category = "General"
                description = ""

                for line in body.splitlines():
                    if line.lower().strip().startswith("category:"):
                        category = line.split(":", 1)[1].strip()
                    elif line.lower().strip().startswith("desc:") or line.lower().strip().startswith("description:"):
                        description = line.split(":", 1)[1].strip()

                # Fallback display text
                if not description:
                    for line in body.splitlines():
                        if line.strip() and not line.lower().strip().startswith("category:"):
                            description = line.strip()
                            break
                    if not description:
                        description = "A Kotlite release."

                # 3. Locate the first executable file in release assets
                download_url = None
                for asset in release.get("assets", []):
                    if asset["name"].endswith(".exe"):
                        download_url = asset["browser_download_url"]
                        break

                if download_url:
                    categories.add(category)
                    self.apps_data.append({
                        "name": name,
                        "version": version,
                        "category": category,
                        "desc": description,
                        "url": download_url,
                        "exe_filename": f"{name}_{version}.exe"
                    })

            # Update categories in UI dropdown
            self.category_list = sorted(list(categories))
            self.after(0, self.update_ui_after_fetch)

        except Exception:
            self.after(0, lambda: self.status_label.configure(text="Offline or GitHub connection failed.", text_color="red"))

    def update_ui_after_fetch(self):
        """Runs once GitHub finishes fetching to reset options and refresh layout."""
        self.category_dropdown.configure(values=self.category_list)
        self.status_label.configure(text=f"Synced successfully. Found {len(self.apps_data)} applications.", text_color="#11C659")
        self.refresh_apps()

    def refresh_apps(self):
        """Clears the scroll panel and builds filtered app cards."""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        search_query = self.search_var.get().lower().strip()
        selected_category = self.category_var.get()

        # Filtering logic
        filtered_apps = []
        for app in self.apps_data:
            matches_search = (search_query in app["name"].lower()) or (search_query in app["desc"].lower())
            matches_category = (selected_category == "All Categories") or (app["category"] == selected_category)

            if matches_search and matches_category:
                filtered_apps.append(app)

        if not filtered_apps:
            ctk.CTkLabel(
                self.scroll_frame, 
                text="No applications match your criteria.", 
                font=("Helvetica", 14, "italic"),
                text_color="gray"
            ).pack(pady=40)
            return

        for app in filtered_apps:
            self.create_app_card(app)

    def create_app_card(self, app):
        """Generates the card interface for an application."""
        card_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=10, fg_color="#2B2B2B")
        card_frame.pack(fill="x", pady=6, padx=5)

        card_frame.grid_columnconfigure(0, weight=1)
        card_frame.grid_columnconfigure(1, weight=0)

        # Left Column: Program info text
        info_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        title_label = ctk.CTkLabel(
            info_frame, 
            text=f"{app['name']} — {app['version']}", 
            font=("Helvetica", 18, "bold")
        )
        title_label.pack(anchor="w")

        desc_text = f"[{app['category']}] — {app['desc']}"
        desc_label = ctk.CTkLabel(
            info_frame, 
            text=desc_text, 
            font=("Helvetica", 12), 
            text_color="#A0A0A0"
        )
        desc_label.pack(anchor="w", pady=(3, 0))

        # Right Column: Action buttons
        btn_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=20, pady=12, sticky="e")

        exe_path = os.path.join(self.apps_folder, app["exe_filename"])
        is_installed = os.path.exists(exe_path)

        # Delete Button (shown only if already downloaded locally)
        if is_installed:
            del_btn = ctk.CTkButton(
                btn_frame, 
                text="🗑", 
                width=35, 
                height=40,
                font=("Helvetica", 14), 
                fg_color="#D32F2F", 
                hover_color="#B71C1C",
                command=lambda p=exe_path: self.delete_local_app(p)
            )
            del_btn.pack(side="left", padx=(0, 8))

        # Main Dynamic CTA Button (Launch or Install)
        action_text = "Launch" if is_installed else "Install"
        btn_color = "#11C659" if is_installed else "#3b8ed0"
        hover_color = "#0F9D47" if is_installed else "#296e9c"

        action_btn = ctk.CTkButton(
            btn_frame, 
            text=action_text, 
            font=("Helvetica", 14, "bold"),
            height=40, 
            width=110,
            fg_color=btn_color, 
            hover_color=hover_color,
            command=lambda a=app: self.handle_app_action(a)
        )
        action_btn.pack(side="right")

    def handle_app_action(self, app):
        """Decides whether to execute or trigger the download for the app."""
        exe_path = os.path.join(self.apps_folder, app["exe_filename"])

        if os.path.exists(exe_path):
            self.status_label.configure(text=f"Launching {app['name']}...", text_color="#11C659")
            subprocess.Popen(exe_path)
            self.after(2000, self.destroy)
        else:
            self.status_label.configure(text=f"Downloading {app['name']} from GitHub releases...", text_color="#3b8ed0")
            threading.Thread(target=self.download_app_file, args=(app,)).start()

    def download_app_file(self, app):
        """Handles the background downloading thread."""
        try:
            r = requests.get(app["url"], stream=True)
            path = os.path.join(self.apps_folder, app["exe_filename"])
            
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Reset UI and refresh app listings
            self.after(0, lambda: self.status_label.configure(text=f"Installed {app['name']} successfully!", text_color="#11C659"))
            self.after(0, self.refresh_apps)
        except Exception:
            self.after(0, lambda: self.status_label.configure(text="Download failed.", text_color="red"))

    def delete_local_app(self, file_path):
        """Removes the local exe cache file."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            self.status_label.configure(text="Local files successfully removed.", text_color="#11C659")
            self.refresh_apps()
        except Exception:
            self.status_label.configure(text="Error deleting file. Is it running?", text_color="red")

if __name__ == "__main__":
    app = GitHubAppLauncher()
    app.mainloop()
