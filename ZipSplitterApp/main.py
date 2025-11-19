import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from logic import FileScanner, Batcher, Zipper, FileCategories

class ZipSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zip Splitter")
        self.root.geometry("850x650")
        
        self.scanner = FileScanner()
        self.zipper = None
        self.all_files = [] # Raw scan result
        self.filtered_files = [] # After type filtering
        self.batches = []
        
        self.setup_ui()
        
    def setup_ui(self):
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=2)
        
        # Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Section 1: Configuration ---
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # --- Section 3: Actions (Packed Bottom) ---
        action_frame = ttk.Frame(main_frame, padding="10")
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)

        # --- Section 2: Preview (Packed Center) ---
        preview_frame = ttk.LabelFrame(main_frame, text="Preview", padding="10")
        preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Source
        ttk.Label(config_frame, text="Source Folder:").grid(row=0, column=0, sticky="w")
        self.source_path_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.source_path_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(config_frame, text="Browse", command=self.browse_source).grid(row=0, column=2)
        
        # Destination
        ttk.Label(config_frame, text="Output Folder:").grid(row=1, column=0, sticky="w")
        self.dest_path_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.dest_path_var, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(config_frame, text="Browse", command=self.browse_dest).grid(row=1, column=2)
        
        # Size Limit
        ttk.Label(config_frame, text="Target Zip Size:").grid(row=2, column=0, sticky="w")
        self.size_var = tk.StringVar(value="2 GB")
        size_options = ["100 MB", "500 MB", "700 MB", "1 GB", "2 GB", "4 GB"]
        # state='normal' allows typing custom sizes
        self.size_combo = ttk.Combobox(config_frame, textvariable=self.size_var, values=size_options, width=10)
        self.size_combo.grid(row=2, column=1, sticky="w", padx=5)
        self.size_combo.bind("<<ComboboxSelected>>", self.on_settings_change)
        self.size_combo.bind("<Return>", self.on_settings_change)
        ttk.Label(config_frame, text="(Select or type, e.g. '3.5 GB')").grid(row=2, column=2, sticky="w")
        
        # Sort By
        ttk.Label(config_frame, text="Sort Files By:").grid(row=3, column=0, sticky="w")
        self.sort_var = tk.StringVar(value="Path")
        sort_options = ["Path", "Size", "Date", "Type"]
        self.sort_combo = ttk.Combobox(config_frame, textvariable=self.sort_var, values=sort_options, width=10)
        self.sort_combo.grid(row=3, column=1, sticky="w", padx=5)
        self.sort_combo.bind("<<ComboboxSelected>>", self.on_settings_change)
        
        # Exclude
        ttk.Label(config_frame, text="Exclude (names/exts):").grid(row=4, column=0, sticky="w")
        self.exclude_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.exclude_var, width=50).grid(row=4, column=1, padx=5)

        # Filter By Type
        ttk.Label(config_frame, text="Filter Type:").grid(row=5, column=0, sticky="w")
        self.filter_var = tk.StringVar(value="All Files")
        filter_options = ["All Files", "Videos", "Images", "Audio", "Documents"]
        self.filter_combo = ttk.Combobox(config_frame, textvariable=self.filter_var, values=filter_options, width=15, state="readonly")
        self.filter_combo.grid(row=5, column=1, sticky="w", padx=5)
        self.filter_combo.bind("<<ComboboxSelected>>", self.on_settings_change)

        ttk.Button(config_frame, text="Scan & Preview", command=self.scan_and_preview).grid(row=5, column=2)

        # Summary Label
        self.summary_label = ttk.Label(preview_frame, text="Ready to scan.")
        self.summary_label.pack(fill=tk.X)
        
        # Tabs
        self.tabs = ttk.Notebook(preview_frame)
        self.tabs.pack(fill=tk.BOTH, expand=True)
        
        # Batch Preview Tab
        self.batch_tree = ttk.Treeview(self.tabs, columns=("size", "count"), show="tree headings")
        self.batch_tree.heading("#0", text="Archive Name")
        self.batch_tree.heading("size", text="Est. Size")
        self.batch_tree.heading("count", text="File Count")
        self.tabs.add(self.batch_tree, text="Batches")
        
        # All Files Tab
        self.files_tree = ttk.Treeview(self.tabs, columns=("size", "relpath"), show="headings")
        self.files_tree.heading("size", text="Size")
        self.files_tree.heading("relpath", text="Path")
        self.tabs.add(self.files_tree, text="All Files")

        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(action_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))
        
        # Status
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(action_frame, textvariable=self.status_var, font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))
        
        # Buttons Container
        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        # Cancel Button
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_processing, state="disabled")
        self.cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Start Button (Bigger)
        self.start_btn = ttk.Button(btn_frame, text="Start Processing", command=self.start_processing, state="disabled")
        self.start_btn.pack(side=tk.RIGHT, padx=5, ipadx=10, ipady=5)

    def browse_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_path_var.set(path)
            # Default dest to parent of source or desktop
            if not self.dest_path_var.get():
                self.dest_path_var.set(os.path.dirname(path))
            self.scan_and_preview()

    def browse_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_path_var.set(path)

    def on_settings_change(self, event=None):
        # If we already have files, re-batch them
        if self.all_files:
            self.update_batches()

    def scan_and_preview(self):
        source = self.source_path_var.get()
        if not source:
            return
            
        self.status_var.set("Scanning...")
        self.root.update_idletasks()
        
        exclude_str = self.exclude_var.get()
        exclude_list = [x.strip() for x in exclude_str.split(",")] if exclude_str else []
        
        # Run scan
        self.all_files = self.scanner.scan(source, exclude_list)
        
        self.update_batches()
        self.status_var.set(f"Found {len(self.all_files)} files (Total). Filtered: {len(self.filtered_files)}")
        self.start_btn.config(state="normal" if self.filtered_files else "disabled")

    def update_batches(self):
        if not self.all_files:
            self.filtered_files = []
            self.batches = []
            self.files_tree.delete(*self.files_tree.get_children())
            self.batch_tree.delete(*self.batch_tree.get_children())
            return
            
        # Apply Filter
        filter_type = self.filter_var.get()
        if filter_type == "All Files":
            self.filtered_files = self.all_files
        else:
            extensions = FileCategories.get_extensions(filter_type)
            self.filtered_files = [f for f in self.all_files if os.path.splitext(f.path)[1].lower() in extensions]

        # Update Files Tree
        self.files_tree.delete(*self.files_tree.get_children())
        for f in self.filtered_files:
            self.files_tree.insert("", "end", values=(Batcher.format_bytes(f.size), f.rel_path))

        size_str = self.size_var.get()
        max_size = Batcher.parse_size(size_str)
        if not max_size:
            # Don't show error immediately on typing, maybe show in status?
            # For now, if invalid, assume 2GB or just return
            return 
            
        sort_map = {"Path": "path", "Size": "size", "Date": "date", "Type": "type"}
        sort_mode = sort_map.get(self.sort_var.get(), "path")
        
        self.batches = Batcher.create_batches(self.filtered_files, max_size, sort_mode)
        
        # Update Batch Tree
        self.batch_tree.delete(*self.batch_tree.get_children())
        prefix = filter_type if filter_type != "All Files" else "archive"
        
        for i, batch in enumerate(self.batches):
            name = f"{prefix}_{i+1}.zip"
            size_fmt = Batcher.format_bytes(batch['size'])
            count = len(batch['files'])
            item_id = self.batch_tree.insert("", "end", text=name, values=(size_fmt, count))
            
            # Optional: Add children to see files in batch
            for f in batch['files']:
                self.batch_tree.insert(item_id, "end", text=f.rel_path, values=(Batcher.format_bytes(f.size), ""))

        total_size = sum(f.size for f in self.filtered_files)
        self.summary_label.config(
            text=f"Filtered Size: {Batcher.format_bytes(total_size)} | Files: {len(self.filtered_files)} | Predicted Archives: {len(self.batches)}"
        )

    def start_processing(self):
        dest = self.dest_path_var.get()
        if not dest:
            messagebox.showerror("Error", "Please select an output folder.")
            return
            
        if not self.batches:
            return
            
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.zipper = Zipper(callback=self.update_progress)
        
        # Determine prefix
        filter_type = self.filter_var.get()
        prefix = filter_type if filter_type != "All Files" else "archive"
        
        # Run in thread
        t = threading.Thread(target=self.run_zip_thread, args=(dest, prefix))
        t.start()

    def cancel_processing(self):
        if self.zipper:
            self.zipper.stop()
            self.status_var.set("Stopping...")
            self.cancel_btn.config(state="disabled")

    def update_progress(self, msg, percent):
        # Thread safe update
        self.root.after(0, lambda: self._update_progress_ui(msg, percent))
        
    def _update_progress_ui(self, msg, percent):
        self.status_var.set(msg)
        self.progress_var.set(percent)

    def run_zip_thread(self, dest, prefix):
        try:
            self.zipper.create_archives(self.batches, dest, prefix)
            self.root.after(0, self.on_zip_complete)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.reset_ui_state)

    def on_zip_complete(self):
        if self.zipper and self.zipper.stop_requested:
            self.status_var.set("Cancelled.")
            messagebox.showinfo("Cancelled", "Processing was cancelled.")
        else:
            self.status_var.set("Completed!")
            self.progress_var.set(100)
            messagebox.showinfo("Success", f"Created zip archives in {self.dest_path_var.get()}")
        
        self.reset_ui_state()
        
    def reset_ui_state(self):
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = ZipSplitterApp(root)
    root.mainloop()
