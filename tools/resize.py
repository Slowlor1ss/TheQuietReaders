import sys
import os
import re
from PIL import Image

def clean_filename(filename):
    """
    Converts 'Deep End Ali Hazelwood.png' or 'DeepEndAliHazelwood.png'
    into 'deep-end-ali-hazelwood'.
    """
    # Remove the file extension (.png, .jpg)
    name = os.path.splitext(filename)[0]
    
    # Handle CamelCase (e.g., DeepEnd -> Deep End)
    # Adds a space before any capital letter that follows a lowercase letter
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    
    # Replace spaces, underscores, and dots with hyphens
    name = re.sub(r'[\s_.]+', '-', name)
    
    # Remove any weird non-alphanumeric characters (keep hyphens)
    name = re.sub(r'[^a-zA-Z0-9-]', '', name)
    
    # Convert to lowercase and strip extra hyphens from ends
    return name.lower().strip('-')

def resize_and_convert(input_path):
    if not os.path.exists(input_path):
        print(f"Error: Could not find file '{input_path}'")
        return

    # Generate the clean slug automatically
    original_filename = os.path.basename(input_path)
    slug_name = clean_filename(original_filename)

    try:
        with Image.open(input_path) as img:
            # Convert to RGB (standard for WebP)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            target_heights = [420, 280]

            print(f"Processing: '{original_filename}' -> slug: '{slug_name}'")

            for height in target_heights:
                # Aspect Ratio Math
                aspect_ratio = img.width / img.height
                new_width = int(height * aspect_ratio)

                # Resize
                resized_img = img.resize((new_width, height), Image.Resampling.LANCZOS)

                # Save
                output_filename = f"{slug_name}-{height}.webp"
                resized_img.save(output_filename, "WEBP", quality=85)
                
                print(f"  Saved: {output_filename} ({new_width}x{height})")

    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python resize.py [IMAGE_FILE]")
        print("Example: python resize.py 'Deep End Ali Hazelwood.png'")
    else:
        # Loop through all files provided (allows dragging multiple files at once)
        for i in range(1, len(sys.argv)):
            resize_and_convert(sys.argv[i])