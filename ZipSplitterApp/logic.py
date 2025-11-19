import os
import time
import zipfile
import fnmatch
from datetime import datetime

class FileCategories:
    CATEGORIES = {
        "Videos": {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'},
        "Images": {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic', '.raw', '.ico'},
        "Audio": {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'},
        "Documents": {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv', '.md'}
    }

    @staticmethod
    def get_extensions(category):
        return FileCategories.CATEGORIES.get(category, set())

class FileInfo:
    def __init__(self, path, rel_path, size, mtime):
        self.path = path
        self.rel_path = rel_path
        self.size = size
        self.mtime = mtime

    def __repr__(self):
        return f"<FileInfo {self.rel_path} ({self.size} bytes)>"

class FileScanner:
    def scan(self, folder_path, exclude_patterns=None):
        files = []
        if not os.path.exists(folder_path):
            return files
            
        exclude_patterns = exclude_patterns or []
        
        for root, _, filenames in os.walk(folder_path):
            for filename in filenames:
                if any(fnmatch.fnmatch(filename, pat) for pat in exclude_patterns):
                    continue
                
                full_path = os.path.join(root, filename)
                try:
                    stat = os.stat(full_path)
                    rel_path = os.path.relpath(full_path, folder_path)
                    files.append(FileInfo(full_path, rel_path, stat.st_size, stat.st_mtime))
                except OSError:
                    pass # Skip files we can't read
                    
        return files

class Batcher:
    @staticmethod
    def parse_size(size_str):
        """Parses strings like '100 MB', '2 GB', '1024' into bytes."""
        size_str = size_str.strip().upper()
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        
        # Check for suffixes
        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix) or size_str.endswith(suffix + "B"):
                # Remove suffix 'GB', 'G', 'MB', 'M', etc.
                num_part = size_str.rstrip('B').rstrip(suffix)
                try:
                    return int(float(num_part) * mult)
                except ValueError:
                    return None
        
        # Assume bytes if no suffix
        try:
            return int(float(size_str))
        except ValueError:
            return None

    @staticmethod
    def format_bytes(size):
        power = 2**10
        n = 0
        power_labels = {0 : '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.2f} {power_labels.get(n, '')}B"

    @staticmethod
    def create_batches(files, max_size_bytes, sort_by='path'):
        # Sort files first
        if sort_by == 'size':
            files.sort(key=lambda x: x.size, reverse=True)
        elif sort_by == 'date':
            files.sort(key=lambda x: x.mtime)
        elif sort_by == 'type':
            files.sort(key=lambda x: os.path.splitext(x.path)[1].lower())
        else: # path/name
            files.sort(key=lambda x: x.rel_path)
            
        batches = []
        current_batch = []
        current_batch_size = 0
        
        for file in files:
            # If a single file is larger than max_size, it must go in its own batch
            if file.size > max_size_bytes:
                # If we have a pending batch, save it
                if current_batch:
                    batches.append({'files': current_batch, 'size': current_batch_size})
                    current_batch = []
                    current_batch_size = 0
                
                # Add the large file as a single batch
                batches.append({'files': [file], 'size': file.size})
                continue

            if current_batch_size + file.size > max_size_bytes:
                # Close current batch
                batches.append({'files': current_batch, 'size': current_batch_size})
                current_batch = []
                current_batch_size = 0
            
            current_batch.append(file)
            current_batch_size += file.size
            
        # Append final batch
        if current_batch:
            batches.append({'files': current_batch, 'size': current_batch_size})
            
        return batches

class Zipper:
    def __init__(self, callback=None):
        self.callback = callback # func(progress_str, percent_float)
        self.stop_requested = False

    def stop(self):
        self.stop_requested = True

    def create_archives(self, batches, output_dir, prefix="archive"):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        total_files = sum(len(b['files']) for b in batches)
        processed_files = 0

        created_archives = []

        for i, batch in enumerate(batches):
            if self.stop_requested:
                break

            archive_name = f"{prefix}_{i+1}.zip"
            archive_path = os.path.join(output_dir, archive_name)
            
            try:
                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for file_info in batch['files']:
                        if self.stop_requested:
                            break
                        
                        # Add file to zip
                        zf.write(file_info.path, file_info.rel_path)
                        
                        processed_files += 1
                        if self.callback:
                            percent = (processed_files / total_files) * 100
                            self.callback(f"Zipping {file_info.rel_path} into {archive_name}...", percent)
                            
                created_archives.append(archive_path)
            except Exception as e:
                print(f"Error creating {archive_path}: {e}")
                # Optionally re-raise or handle
        
        return created_archives
