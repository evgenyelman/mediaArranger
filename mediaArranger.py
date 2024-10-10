import os
import shutil
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
from pymediainfo import MediaInfo
import csv

def sanitize_device_name(device_name):
    return ''.join(c for c in device_name if c.isalnum() or c in (' ', '_')).strip()

def get_image_metadata(file_path):
    try:
        image = Image.open(file_path)
        info = image._getexif()
        if info is not None:
            exif_data = {TAGS.get(tag): value for tag, value in info.items()}
            date_taken = exif_data.get('DateTimeOriginal', None)
            if date_taken:
                date_taken = date_taken.split()[0].replace(':', '-')  # Extract only the date part
            
            make = exif_data.get('Make', 'Unknown')
            model = exif_data.get('Model', 'Unknown')
            device = sanitize_device_name(f"{make} {model}".strip())
            return date_taken, device
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return None, None

def get_video_metadata_mediainfo(file_path):
    try:
        media_info = MediaInfo.parse(file_path)
        for track in media_info.tracks:
            if track.track_type == "General":
                date_taken = track.tagged_date or track.encoded_date or track.file_last_modification_date
                device = track.other_file_creation_date or "Unknown Device"
                
                if date_taken:
                    # Extract the date part only and clean it up
                    date_taken = date_taken.split('T')[0] if 'T' in date_taken else date_taken.split()[0]
                    date_taken = date_taken.replace(':', '-')  # Ensure no invalid characters
                    return date_taken, sanitize_device_name(device)
    except Exception as e:
        print(f"MediaInfo error for {file_path}: {e}")
    
    return None, None

def update_sort_history(history_file, device, latest_date):
    history = {}
    
    if os.path.exists(history_file):
        with open(history_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            history = {rows[0]: rows[1] for rows in reader}
    
    history[device] = latest_date
    
    with open(history_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for key, value in history.items():
            writer.writerow([key, value])

def get_latest_date_from_history(history_file, device):
    if os.path.exists(history_file):
        with open(history_file, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row[0] == device:
                    return row[1]
    return None

def should_copy_file(date_taken, latest_date):
    if latest_date:
        return datetime.strptime(date_taken, "%Y-%m-%d") > datetime.strptime(latest_date, "%Y-%m-%d")
    return True

def get_media_metadata(file_path):
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext in ['.jpg', '.jpeg', '.tiff', '.png', '.bmp']:
        return get_image_metadata(file_path)
    elif file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']:
        return get_video_metadata_mediainfo(file_path)
    else:
        print(f"File format not recognized: {file_path}")  # Log unrecognized file paths
        return None, None

# Define the source and target directories
source_dir = r"C:\Users\evgen\OneDrive\Pictures\testInput"
target_dir = r"C:\Users\evgen\OneDrive\Pictures\Sorted Import\test1"
history_file = os.path.join(target_dir, "sort_history.csv")

latest_dates = {}
total_files = 0
files_copied = 0

# Count the total number of files
for root, _, files in os.walk(source_dir):
    total_files += len(files)

print(f"Total files to process: {total_files}")

# Process each file
processed_files = 0
for root, _, files in os.walk(source_dir):
    for file in files:
        file_path = os.path.join(root, file)
        date_taken, device = get_media_metadata(file_path)
        
        if date_taken and device:
            latest_date = get_latest_date_from_history(history_file, device)
            if should_copy_file(date_taken, latest_date):
                media_type = "images" if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')) else "videos"
                
                # Ensure date_taken contains only the date part in YYYY-MM-DD format
                date_taken = date_taken.split()[0]  # Clean out any time information if present
                
                # Create folders based only on date in YYYY-MM-DD format
                date_folder = os.path.join(target_dir, date_taken)  # Only YYYY-MM-DD format for folder name
                media_folder = os.path.join(date_folder, media_type)

                # Ensure that the date folder exists
                os.makedirs(date_folder, exist_ok=True)  # Create date folder
                os.makedirs(media_folder, exist_ok=True)  # Create media folder inside the date folder
                
                shutil.copy2(file_path, media_folder)
                files_copied += 1
                
                if device not in latest_dates or datetime.strptime(date_taken, "%Y-%m-%d") > datetime.strptime(latest_dates[device], "%Y-%m-%d"):
                    latest_dates[device] = date_taken
        
        # Update progress
        processed_files += 1
        progress = (processed_files / total_files) * 100
        print(f"Progress: {processed_files}/{total_files} files processed ({progress:.2f}%)")

# Update the sort history
for device, latest_date in latest_dates.items():
    update_sort_history(history_file, device, latest_date)

files_remaining = total_files - files_copied

print(f"Media sorting complete!")
print(f"Total files: {total_files}")
print(f"Files copied: {files_copied}")
print(f"Files remaining: {files_remaining}")
