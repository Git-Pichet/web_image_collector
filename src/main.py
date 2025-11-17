# -*- coding: utf-8 -*-
import os
import io
import json
from urllib.parse import urljoin, urlparse

import tkinter as tk
from tkinter import filedialog, messagebox

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageTk

CONFIG_FILE = "config.json"
CONFIG_KEY_SAVE_PATH = "default_save_path"


class ImageScraperApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Web Image Collector (Python)")
        self.geometry("1000x700")

        # data structure: list of dict {url, data, photo, selected_var, filename}
        self.images = []
        self.config_data = {}

        self._load_config()
        self._build_ui()

    # -----------------------------------
    # Config
    # -----------------------------------
    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.config_data = json.load(f)
            except Exception:
                self.config_data = {}
        else:
            self.config_data = {}

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    # -----------------------------------
    # UI
    # -----------------------------------
    def _build_ui(self):
        # -------- URL Input --------
        url_frame = tk.Frame(self)
        url_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(url_frame, text="Page URL (copy from Chrome):").pack(side="left")
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(url_frame, textvariable=self.url_var)
        url_entry.pack(side="left", fill="x", expand=True, padx=5)

        scan_btn = tk.Button(url_frame, text="Scan Images", command=self.scan_images)
        scan_btn.pack(side="left", padx=5)

        # -------- Save Path Setting --------
        save_frame = tk.Frame(self)
        save_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(save_frame, text="Default Save Path:").pack(side="left")

        default_path = self.config_data.get(CONFIG_KEY_SAVE_PATH, os.getcwd())
        self.save_path_var = tk.StringVar(value=default_path)

        self.save_path_entry = tk.Entry(save_frame, textvariable=self.save_path_var)
        self.save_path_entry.pack(side="left", fill="x", expand=True, padx=5)

        save_browse_btn = tk.Button(save_frame, text="Browse...", command=self.browse_save_path)
        save_browse_btn.pack(side="left", padx=5)

        # -------- Action Buttons --------
        action_frame = tk.Frame(self)
        action_frame.pack(fill="x", padx=10, pady=5)

        select_all_btn = tk.Button(action_frame, text="Select All", command=self.select_all)
        select_all_btn.pack(side="left", padx=5)

        unselect_all_btn = tk.Button(action_frame, text="Unselect All", command=self.unselect_all)
        unselect_all_btn.pack(side="left", padx=5)

        save_selected_btn = tk.Button(action_frame, text="Save Selected", command=self.save_selected)
        save_selected_btn.pack(side="left", padx=5)

        clear_btn = tk.Button(action_frame, text="Clear List", command=self.clear_images)
        clear_btn.pack(side="left", padx=5)

        # -------- Scrollable Image List --------
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.images_frame = tk.Frame(self.canvas)

        self.images_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.images_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # mouse wheel scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        # Windows scroll direction
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # -----------------------------------
    # Browse Save Path
    # -----------------------------------
    def browse_save_path(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path_var.set(path)
            self.config_data[CONFIG_KEY_SAVE_PATH] = path
            self._save_config()

    # -----------------------------------
    # Core logic
    # -----------------------------------
    def scan_images(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Warning", "Please input URL (copy from Chrome address bar).")
            return

        # Basic normalize
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "http://" + url
            self.url_var.set(url)

        # Clear old images (cache in RAM) + UI
        self.clear_images(silent=True)

        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load page:\n{e}")
            return

        soup = BeautifulSoup(resp.text, "html.parser")
        img_tags = soup.find_all("img")

        if not img_tags:
            messagebox.showinfo("Info", "No <img> tags found on this page.")
            return

        found_count = 0
        for img in img_tags:
            src = img.get("src")
            if not src:
                continue
            img_url = urljoin(url, src)
            # Download image into RAM + create thumbnail
            if self._download_and_add_image(img_url):
                found_count += 1

        if found_count == 0:
            messagebox.showinfo("Info", "No images could be downloaded.")
        else:
            messagebox.showinfo("Info", f"Found and loaded {found_count} images into RAM (cache).")

    def _download_and_add_image(self, image_url: str) -> bool:
        try:
            resp = requests.get(image_url, timeout=15)
            resp.raise_for_status()
            data = resp.content
        except Exception as e:
            print(f"Failed to download image {image_url}: {e}")
            return False

        # Create thumbnail from RAM (no save to disk yet)
        try:
            img = Image.open(io.BytesIO(data))
            img.thumbnail((200, 200))  # Thumbnail size
            photo = ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Failed to create thumbnail for {image_url}: {e}")
            return False

        selected_var = tk.BooleanVar(value=True)

        # UI item
        item_frame = tk.Frame(self.images_frame, bd=1, relief="solid", padx=5, pady=5)
        item_frame.pack(side="top", fill="x", padx=5, pady=5)

        cb = tk.Checkbutton(item_frame, variable=selected_var)
        cb.pack(side="left")

        image_label = tk.Label(item_frame, image=photo)
        image_label.image = photo  # keep reference
        image_label.pack(side="left")

        text_label = tk.Label(item_frame, text=image_url, wraplength=600, justify="left")
        text_label.pack(side="left", padx=10)

        # Filename suggestion
        parsed = urlparse(image_url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = "image"
        if "." not in filename:
            filename = filename + ".jpg"

        # keep in RAM
        self.images.append({
            "url": image_url,
            "data": data,
            "photo": photo,
            "selected_var": selected_var,
            "filename": filename,
        })

        return True

    # -----------------------------------
    # Selection helpers
    # -----------------------------------
    def select_all(self):
        for item in self.images:
            item["selected_var"].set(True)

    def unselect_all(self):
        for item in self.images:
            item["selected_var"].set(False)

    # -----------------------------------
    # Save to disk
    # -----------------------------------
    def save_selected(self):
        if not self.images:
            messagebox.showwarning("Warning", "No images loaded.")
            return

        target_dir = self.save_path_var.get().strip()
        if not target_dir or not os.path.isdir(target_dir):
            messagebox.showwarning("Warning", "Invalid save path. Please set a valid folder.")
            return

        selected_items = [img for img in self.images if img["selected_var"].get()]
        if not selected_items:
            messagebox.showwarning("Warning", "No images selected.")
            return

        existing_files = set(os.listdir(target_dir))
        saved_count = 0

        for item in selected_items:
            filename = self._unique_filename(target_dir, item["filename"], existing_files)
            full_path = os.path.join(target_dir, filename)
            try:
                with open(full_path, "wb") as f:
                    f.write(item["data"])
                saved_count += 1
            except Exception as e:
                print(f"Failed to save {full_path}: {e}")

        messagebox.showinfo("Info", f"Saved {saved_count} image(s) to:\n{target_dir}")

    def _unique_filename(self, directory: str, filename: str, existing_files: set) -> str:
        base, ext = os.path.splitext(filename)
        candidate = filename
        i = 1
        while candidate in existing_files:
            candidate = f"{base}_{i}{ext}"
            i += 1
        existing_files.add(candidate)
        return candidate

    # -----------------------------------
    # Clear cache / UI
    # -----------------------------------
    def clear_images(self, silent: bool = False):
        # clear UI
        for widget in self.images_frame.winfo_children():
            widget.destroy()
        # clear RAM cache
        self.images.clear()
        if not silent:
            messagebox.showinfo("Info", "Cleared all loaded images from program (RAM).")


def main():
    app = ImageScraperApp()
    app.mainloop()


if __name__ == "__main__":
    main()
