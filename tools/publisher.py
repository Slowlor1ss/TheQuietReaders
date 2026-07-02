import customtkinter as ctk
from tkinter import filedialog, messagebox
from github import Github
from PIL import Image
import io
import os
import re
import sys
import shutil
import zipfile
import json
from datetime import datetime
import threading
import markdown 
from tkhtmlview import HTMLLabel

try:
    from bs4 import BeautifulSoup, Comment
except ImportError:
    BeautifulSoup = None

# CONFIG
GITHUB_REPO_NAME = "Slowlor1ss/TheQuietReaders"
# hehe not pushing this to my public github lol
GITHUB_TOKEN = "ghp_"
# Appearance
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def clean_filename(filename):
    # Remove the file extension
    name = os.path.splitext(filename)[0]
    
    # Handle CamelCase (DeepEnd -> Deep End)
    name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    
    # Replace spaces, underscores, and dots with hyphens
    name = re.sub(r'[\s_.]+', '-', name)
    
    # Remove weird chars
    name = re.sub(r'[^a-zA-Z0-9-]', '', name)
    
    # Convert to lowercase and strip ends
    return name.lower().strip('-')

class ConsoleRedirector:
    def __init__(self):
        self.buffer = []
        self.console_textbox = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, text):
        self.original_stdout.write(text) 
        self.buffer.append(text)
        
        # Update text in the console textbox if it exists
        if self.console_textbox and self.console_textbox.winfo_exists():
            self.console_textbox.configure(state="normal")
            self.console_textbox.insert("end", text)
            self.console_textbox.see("end") # Auto-scroll to bottom
            self.console_textbox.configure(state="disabled")

    def flush(self):
        self.original_stdout.flush()

# Resize function and changes to webp
def process_image_to_memory(input_path, height):
    if not os.path.exists(input_path):
        return None, None

    # Get the clean name using your function
    original_filename = os.path.basename(input_path)
    slug_name = clean_filename(original_filename)

    with Image.open(input_path) as img:
        # Convert to RGB (Standard for WebP)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        # Aspect Ratio Math
        aspect_ratio = img.width / img.height
        new_width = int(height * aspect_ratio)

        resized_img = img.resize((new_width, height), Image.Resampling.LANCZOS)

        # Save to Memory Buffer
        img_buffer = io.BytesIO()
        resized_img.save(img_buffer, format="WEBP", quality=85)
        img_buffer.seek(0) # Go to start of file

        # Construct the filename: slug-height.webp
        output_filename = f"{slug_name}-{height}.webp"
        
        return img_buffer, output_filename

# Resize function for Cover Images (Width Based - e.g., 1200px for Articles)
def process_image_to_width(input_path, target_width):
    if not os.path.exists(input_path):
        return None, None
        
    slug_name = clean_filename(os.path.basename(input_path))
    
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "P"): img = img.convert("RGBA")
        else: img = img.convert("RGB")
        
        # Calculate new height to keep aspect ratio perfect
        aspect = img.height / img.width
        new_height = int(target_width * aspect)
        
        resized_img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        
        img_buffer = io.BytesIO()
        resized_img.save(img_buffer, format="WEBP", quality=85)
        img_buffer.seek(0)
        
        return img_buffer, f"{slug_name}-{target_width}w.webp"

# Resize function for Inline Article Images
def process_inline_image(input_path, max_width=800):
    if not os.path.exists(input_path): return None
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "P"): img = img.convert("RGBA")
        else: img = img.convert("RGB")
        
        if img.width > max_width:
            aspect = img.height / img.width
            new_height = int(max_width * aspect)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=85)
        buf.seek(0)
        return buf

# UI
class SimplePublisher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Quiet Readers Publisher Tool")
        self.geometry("550x900")

        # Garbage Collection
        self.cleanup_temp_folders() # Clean up any messes from previous crashes on startup
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Catch the 'X' button to clean up before closing

        self.selected_image_path = None
        self.mode = "Book" # Default to Book mode
        self.gdocs_zip_data = None

        # Console window for debugging
        self.dev_console_window = None
        self.console_logger = ConsoleRedirector()
        sys.stdout = self.console_logger
        sys.stderr = self.console_logger # Catches errors too!
        
        self.menu_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.menu_bar.pack(fill="x", side="top")
        menu_style = {
            "fg_color": "transparent",
            "text_color": "#030303",
            "hover_color": "#CCCCCC",
            "height": 24,
            "width": 60,
            "font": ("Arial", 12),
            "corner_radius": 0
        }
        self.btn_console = ctk.CTkButton(self.menu_bar, text="Console", command=self.toggle_dev_console, **menu_style)
        self.btn_console.pack(side="left")
        self.btn_save = ctk.CTkButton(self.menu_bar, text="Save Draft", command=self.start_save, **menu_style)
        self.btn_save.pack(side="left")
        self.bind("<Control-Shift-D>", lambda event: self.toggle_dev_console())
        self.bind("<Control-Shift-d>", lambda event: self.toggle_dev_console())
        self.bind("<Control-S>", lambda event: self.start_save())
        self.bind("<Control-s>", lambda event: self.start_save())

        # Check for BeautifulSoup dependency
        if BeautifulSoup is None:
            messagebox.showerror("Dependency Missing", "To process Google Docs HTML, you must install beautifulsoup4.\n\nRun:\npip install beautifulsoup4")
            self.destroy()
            return

        # Scrollable container
        self.scroll = ctk.CTkScrollableFrame(
            self, 
            scrollbar_button_color="#CCCCCC",
            scrollbar_button_hover_color="#af7bc5",
            scrollbar_fg_color="transparent",
            border_width=0,
            corner_radius=0
        )
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        ctk.CTkLabel(self.scroll, text="New Review", font=("Arial", 20, "bold")).pack(pady=10)

        # --- MODE SWITCHER ---
        self.mode_selector = ctk.CTkSegmentedButton(
            self.scroll, 
            values=["Book", "Film", "Article"],
            command=self.switch_mode,
            selected_color="#8e44ad",
            selected_hover_color="#732d91"
        )
        self.mode_selector.set("Book")
        self.mode_selector.pack(pady=10)

        # --- SHARED FIELDS ---
        self.entry_title = self.create_input("Title")
        self.entry_author = self.create_input("Review Author Name")
        
        # Genre Container
        self.genre_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.genre_container.pack(fill="x")
        self.entry_genre = self.create_input("Genre (e.g. Romance, Comedy)", parent=self.genre_container)
        
        # --- BOOK SPECIFIC FIELDS CONTAINER ---
        self.book_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.book_container.pack(fill="x") # Shown by default
        
        self.entry_pages = self.create_input("Pages", parent=self.book_container)
        self.entry_isbn = self.create_input("ISBN", parent=self.book_container)
        self.entry_amznlink = self.create_input("Amazon Link", parent=self.book_container)
        self.entry_bookshplink = self.create_input("BookShop Link", parent=self.book_container)

        # --- FILM SPECIFIC FIELDS CONTAINER ---
        self.film_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        # Hidden by default (we don't pack it yet)

        self.entry_director = self.create_input("Director", parent=self.film_container)
        self.entry_actors = self.create_input("Leading Actors (comma separated)", parent=self.film_container)
        self.entry_runtime = self.create_input("Run Time (e.g. 106 minutes)", parent=self.film_container)
        self.entry_year = self.create_input("Release Year (e.g. 2023)", parent=self.film_container)

        # --- SHARED FIELDS (Bottom) ---
        self.rating_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.rating_container.pack(fill="x")
        self.entry_rating = self.create_input("Rating (0-5, e.g. 4.5)", parent=self.rating_container)

        self.featured_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.featured_container.pack(fill="x")
        self.check_featured = ctk.CTkCheckBox(self.featured_container, text="Feature this post on Homepage?", fg_color="#8e44ad")
        self.check_featured.pack(anchor="w", pady=(10, 5), padx=20)

        # Article Tools Container
        self.article_tools_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.btn_select_zip = ctk.CTkButton(self.article_tools_container, text="📦 Select GDocs ZIP", command=self.select_gdocs_zip, fg_color="#d35400", hover_color="#e67e22", height=35)
        self.btn_select_zip.pack(pady=10, padx=5)

        # Description
        self.desc_label = ctk.CTkLabel(self.scroll, text="Short Description: (1-2 lines preferably)")
        self.desc_label.pack(anchor="w", pady=(0), padx=(5))
        self.entry_custom_desc = ctk.CTkTextbox(self.scroll, height=60)
        self.entry_custom_desc.pack(fill="x", pady=5, padx=5)

        # Body
        self.body_label = ctk.CTkLabel(self.scroll, text="Full Review (Markdown):")
        self.body_label.pack(anchor="w", pady=(0), padx=(5))
        self.entry_body = ctk.CTkTextbox(self.scroll, height=100)
        self.entry_body.pack(fill="x", pady=5, padx=5)
        self.fix_scroll_propagation(self.entry_body)
        
        self.grip = ctk.CTkFrame(
                    self.scroll, 
                    height=5,
                    width=200,
                    fg_color="#999999",
                    corner_radius=8,
                    cursor="sb_v_double_arrow"
        )
        self.grip.pack(pady=(0, 10)) 
        
        self.grip.bind("<Button-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.perform_resize)

        # Preview button
        self.btn_preview = ctk.CTkButton(self.scroll, text="👁️ Preview Post", command=self.open_preview, fg_color="#555555", height=30)
        self.btn_preview.pack(pady=5, padx=5)

        # Image Selector
        self.btn_image = ctk.CTkButton(self.scroll, text="Select Cover Image", command=self.select_image, fg_color="#8e44ad")
        self.btn_image.pack(pady=20, padx=5)
        self.lbl_image = ctk.CTkLabel(self.scroll, text="No image selected", text_color="gray")
        self.lbl_image.pack()

        # Submit
        self.btn_submit = ctk.CTkButton(self, text="Publish Book Review", height=50, command=self.start_upload, fg_color="green")
        self.btn_submit.pack(fill="x", padx=20, pady=(10, 0))

        # Autosave Indicator (Hidden by default)
        self.lbl_autosave = ctk.CTkLabel(self, text="", text_color="green", font=("Arial", 11))
        self.lbl_autosave.pack(pady=(0, 0))

        # Autosave
        self.last_saved_data = None
        self.check_and_offer_autosave() # Ask to restore first
        self.start_autosave() # Then start the background timer

    def create_input(self, placeholder, parent=None):
        target = parent if parent else self.scroll
        entry = ctk.CTkEntry(target, placeholder_text=placeholder)
        entry.pack(fill="x", pady=5, padx=5)
        return entry

    def switch_mode(self, value):
        self.mode = value
        
        # Hide dynamic inputs cleanly
        self.genre_container.pack_forget()
        self.book_container.pack_forget()
        self.film_container.pack_forget()
        self.rating_container.pack_forget()
        self.featured_container.pack_forget()
        self.article_tools_container.pack_forget()
        
        # Shared text
        self.desc_label.pack_forget()
        self.entry_custom_desc.pack_forget()
        self.body_label.pack_forget()
        self.entry_body.pack_forget()
        self.grip.pack_forget()

        if value == "Book":
            # Show Book inputs safely above Description
            self.genre_container.pack(before=self.btn_preview, fill="x")
            self.book_container.pack(before=self.btn_preview, fill="x") 
            self.rating_container.pack(before=self.btn_preview, fill="x")
            self.featured_container.pack(before=self.btn_preview, fill="x")
            
            # Text
            self.desc_label.pack(before=self.btn_preview, anchor="w", pady=(0), padx=(5))
            self.entry_custom_desc.pack(before=self.btn_preview, fill="x", pady=5, padx=5)
            self.body_label.configure(text="Full Review (Markdown):")
            self.body_label.pack(before=self.btn_preview, anchor="w", pady=(0), padx=(5))
            self.entry_body.pack(before=self.btn_preview, fill="x", pady=5, padx=5)
            self.grip.pack(before=self.btn_preview, pady=(0, 10))

            self.btn_submit.configure(text="Publish Book Review")
        elif value == "Film":
            # Show Film inputs safely above Description
            self.genre_container.pack(before=self.btn_preview, fill="x")
            self.film_container.pack(before=self.btn_preview, fill="x") 
            self.rating_container.pack(before=self.btn_preview, fill="x")
            self.featured_container.pack(before=self.btn_preview, fill="x")
            
            # Text
            self.desc_label.pack(before=self.btn_preview, anchor="w", pady=(0), padx=(5))
            self.entry_custom_desc.pack(before=self.btn_preview, fill="x", pady=5, padx=5)
            self.body_label.configure(text="Full Review (Markdown):")
            self.body_label.pack(before=self.btn_preview, anchor="w", pady=(0), padx=(5))
            self.entry_body.pack(before=self.btn_preview, fill="x", pady=5, padx=5)
            self.grip.pack(before=self.btn_preview, pady=(0, 10))

            self.btn_submit.configure(text="Publish Film Review")
        elif value == "Article":
            self.article_tools_container.pack(before=self.btn_preview, fill="x")
            self.btn_submit.configure(text="Publish Article")
            
            # Description for Article!
            self.desc_label.pack(before=self.btn_preview, anchor="w", pady=(0), padx=(5))
            self.entry_custom_desc.pack(before=self.btn_preview, fill="x", pady=5, padx=5)

            # Hide the body textbox and grip (as the body comes from the ZIP)
            self.body_label.pack_forget()
            self.entry_body.pack_forget()
            self.grip.pack_forget()

    def toggle_dev_console(self, event=None):
        if self.dev_console_window is None or not self.dev_console_window.winfo_exists():
            # Make a window
            self.dev_console_window = ctk.CTkToplevel(self)
            self.dev_console_window.lift()
            self.dev_console_window.title("Dev Console")
            self.dev_console_window.geometry("600x400")
            
            # MAke read-only textbox
            txt_console = ctk.CTkTextbox(self.dev_console_window, font=("Consolas", 12), fg_color="#1e1e1e", text_color="#cccccc")
            txt_console.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Dump history buffer
            txt_console.insert("1.0", "".join(self.console_logger.buffer))
            txt_console.see("end")
            txt_console.configure(state="disabled")

            # I dont know why but the console window drops to the back 
            # I I think at some point I forced the main window to be on top of other windows we create, 
            # but for now this ill do
            # and no it doesnt work withouth the delay of 1ms
            self.dev_console_window.after(1, lambda: self.dev_console_window.lift())

            # Link to logger
            self.console_logger.console_textbox = txt_console
        else:
            # If its already open close it
            self.dev_console_window.destroy()

    def fix_scroll_propagation(self, widget):
        def _on_mousewheel(event):
            # Check if we are currently typing in the text box
            if self.focus_get() == widget._textbox:
                # Box Selected -> Scroll the Text Box (Standard speed)
                widget._textbox.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break" # Stop the parent page from scrolling
            else:
                # Box not Selected -> Scroll the Parent Page
                # We multiply by 10 as otherwise our scroll is super slow for some reason???
                self.scroll._parent_canvas.yview_scroll(int(-1*(event.delta/120)*10), "units")
                return "break" # Stop the parent page from scrolling

        # Bind for Windows (MouseWheel) and Linux (Button-4/5)
        widget._textbox.bind("<MouseWheel>", _on_mousewheel)

    # Resize Logic
    def start_resize(self, event):
        # Remember where we started dragging
        self._drag_start_y = event.y_root
        self._initial_height = self.entry_body.cget("height")

    def perform_resize(self, event):
        # Calculate how far we moved
        delta = event.y_root - self._drag_start_y
        new_height = self._initial_height + delta
        
        # Set limits so it doesn't vanish or get too huge
        if new_height < 100: new_height = 100
        if new_height > 800: new_height = 800
        
        # Apply new height
        self.entry_body.configure(height=new_height)

    def select_gdocs_zip(self):
        title = self.entry_title.get()
        if not title:
            messagebox.showerror("Missing Title", "Please enter the Article Title first so we can properly name the images in the ZIP.")
            return

        zip_path = filedialog.askopenfilename(filetypes=[("GDocs Webpage ZIP", "*.zip")])
        if not zip_path: return

        # Disable button while processing
        self.btn_select_zip.configure(state="disabled", text="Processing ZIP...")
        self.update() # Force UI refresh

        try:
            # Process the ZIP
            # BeautifulSoup for HTML cleaning and image restructuring
            processor = GDocsProcessor(zip_path, clean_filename(title))
            processor.extract_and_clean()
            self.gdocs_zip_data = processor.get_cleaned_data()
            
            num_images = len(self.gdocs_zip_data['inline_images'])
            messagebox.showinfo("Success", f"ZIP Processed!\n\nExtracted HTML and {num_images} optimized images.\nReady to publish.")
            self.btn_select_zip.configure(text=f"ZIP Processed ({num_images} Images)", fg_color="green")

        except Exception as e:
            self.gdocs_zip_data = None
            messagebox.showerror("ZIP Error", f"Failed to process ZIP:\n\n{str(e)}")
            self.btn_select_zip.configure(text="ZIP Error - Retry", fg_color="red")
        
        finally:
            self.btn_select_zip.configure(state="normal")

    def open_preview(self):
        # Create the Pop-up Window
        preview = ctk.CTkToplevel(self)
        preview.title(f"{self.mode} Review Preview")
        preview.geometry("700x800")
        # preview.attributes("-topmost", True) # Commented out as tkhtmlview popups can get stuck behind it

        # Gathering Data
        title = self.entry_title.get() or "[ Missing Title ]"
        author = self.entry_author.get() or "[ Missing Author ]"
        
        # Book fields
        amznlink = self.entry_amznlink.get()
        bookshoplink = self.entry_bookshplink.get()
        genre = self.entry_genre.get()
        rating = self.entry_rating.get()

        body_text = ""
        inline_image_paths = []

        if self.mode == "Article":
            if not self.gdocs_zip_data:
                messagebox.showerror("Missing ZIP", "Please select a processed Google Docs ZIP first to preview the article content.")
                preview.destroy()
                return
            
            # Use the cleaned HTML directly!
            body_html = self.gdocs_zip_data['cleaned_html']
            
            # Get local paths of processed images to show in native Tkinter UI
            inline_image_paths = [img['local_path'] for img in self.gdocs_zip_data['inline_images']]

        else:
            # For Book/Film reviews, it's markdown from textbox, formatted to HTML
            md_body = self.entry_body.get("1.0", "end-1c")
            body_html = markdown.markdown(md_body)

        # Create Scrollable Frame
        page_frame = ctk.CTkScrollableFrame(
            preview, 
            fg_color="white", # Paper color
            corner_radius=0
        )
        page_frame.pack(fill="both", expand=True)

        # Header section
        header_frame = ctk.CTkFrame(page_frame, fg_color="white")
        header_frame.pack(fill="x", padx=40, pady=30)

        # Title Info
        ctk.CTkLabel(header_frame, text=title, font=("Georgia", 32, "bold"), text_color="black", wraplength=400, justify="left").pack(anchor="w", pady=5)
        
        if self.mode != "Article" and genre:
            ctk.CTkLabel(header_frame, text=genre.upper(), font=("Arial", 12), text_color="#888").pack(anchor="w")
            
        ctk.CTkLabel(header_frame, text=f"by {author}", font=("Georgia", 16, "italic"), text_color="#444").pack(anchor="w")
        
        if self.mode != "Article" and rating:
            ctk.CTkLabel(header_frame, text=f"Rating: {rating} / 5", font=("Arial", 14), text_color="#f39c12").pack(anchor="w", pady=10)

        # Link Check (Book only)
        if self.mode == "Book":
            links = []
            if amznlink: links.append("Amazon")
            if bookshoplink: links.append("BookShop")
            if links:
                ctk.CTkLabel(header_frame, text="Links: " + ", ".join(links), font=("Arial", 12), text_color="green").pack(anchor="w", pady=5)

        # Image Thumbnail
        if hasattr(self, 'my_preview_image') and self.my_preview_image:
            img_label = ctk.CTkLabel(header_frame, text="", image=self.my_preview_image)
            img_label.place(relx=1.0, rely=0.0, anchor="ne")

        # Divider
        ctk.CTkFrame(page_frame, height=1, fg_color="#eee").pack(fill="x", padx=40, pady=(0, 20))

        # Body section
        # Instead of feeding raw absolute file paths (like file:///C:/Users/...) to tkhtmlview,
        # which can crash tkhtmlview entirely if PIL fails to read the path,
        # we split the body content by <img> tags and render images using rock-solid native CTkImages.

        # Split body content by image tags
        # Captures any <img> with a src attribute. Note: GDocs HTML cleaning is done in select_gdocs_zip
        parts = re.split(r'<img[^>]*src=[^>]*>', body_html)
        
        for i, part in enumerate(parts):
            # Render the Text Chunk using tkhtmlview Label
            if part.strip():
                # Wrap part in proper markdown format if required? 
                # (body_html is already converted to HTML from MD above for Book/Film reviews)
                
                html_label = HTMLLabel(
                    page_frame, 
                    html=f"<div style='font-family: Georgia, serif; font-size: 14pt; line-height: 1.6;'>{part}</div>",
                    background="white",
                    width=1
                )
                html_label.pack(fill="both", expand=True, padx=40, pady=5)
                html_label.fit_height()

            # Render the Native UI Image (If we have one for this slot)
            if self.mode == "Article" and i < len(inline_image_paths):
                img_path = inline_image_paths[i]
                try:
                    pil_img = Image.open(img_path)
                    
                    # Resizing for Tkinter preview
                    target_width = 300
                    aspect = pil_img.height / pil_img.width
                    target_height = int(target_width * aspect)
                    ctk_img = ctk.CTkImage(
                        light_image=pil_img, 
                        dark_image=pil_img, 
                        size=(target_width, target_height)
                    )
                    img_label = ctk.CTkLabel(page_frame, text="", image=ctk_img)
                    img_label.image = ctk_img # Keep it in memory
                    img_label.pack(pady=20)
                except Exception as e:
                    err_lbl = ctk.CTkLabel(page_frame, text=f"[ Native Image Preview Failed: {os.path.basename(img_path)} ]", text_color="red")
                    err_lbl.pack(pady=10)

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.png *.jpeg *.webp")])
        if path:
            self.selected_image_path = path
            
            try:
                # Open the image
                pil_image = Image.open(path)
                
                # Calculate aspect ratio for a nice thumbnail (max height 200px)
                # Ensures we don't distort the image preview
                aspect = pil_image.width / pil_image.height
                target_height = 200
                target_width = int(target_height * aspect)
                
                # Create a CTkImage (CustomTkinter wrapper)
                # Pass the same image for both light/dark mode
                self.my_preview_image = ctk.CTkImage(
                    light_image=pil_image,
                    dark_image=pil_image,
                    size=(target_width, target_height)
                )
                
                # Update the label to show the image
                # We remove the text ("No image selected") and set the image arg
                self.lbl_image.configure(image=self.my_preview_image, text="")
                
            except Exception as e:
                self.lbl_image.configure(text=f"Error loading preview: {e}", image=None)

    def start_upload(self):
        if self.mode == "Article":
            if not self.gdocs_zip_data:
                messagebox.showerror("Missing ZIP", "Please select and process a Google Docs ZIP first before publishing an Article.")
                return
        else:
            # Backup placeholders split check for Markdown textbox
            body_text = self.entry_body.get("1.0", "end-1c")
            parts = re.split(r'<pre class="prettyprint">\s*</pre>', body_text)
            placeholders = len(parts) - 1
            if placeholders > 0:
                 answer = messagebox.askyesno(
                    "Placeholders Found", 
                    f"Warning: You have {placeholders} image placeholders in your text. This only works for articles published via ZIP now.\n\nDo you still want to publish without processing them?"
                )
            if not answer:
                return

        answer = messagebox.askyesno(
            "Confirm Publish", 
            "Are you sure you want to publish this review?\n\nThis will send the files to GitHub immediately.\n\n\
Make sure you have done a preview first (use the preview button under review)"
        )
        
        if not answer:
            return

        # Disable button to prevent double clicks
        self.btn_submit.configure(state="disabled", text="Working...")
        threading.Thread(target=self.upload_logic, daemon=True).start()

    def upload_logic(self):
        try:
            # Input Validation
            data = self.validate_inputs()
            if not data:
                self.reset_ui()
                return

            # Connect to GitHub
            global GITHUB_TOKEN
            repo = None

            while repo is None:
                if GITHUB_TOKEN == "ghp_" or not GITHUB_TOKEN:
                    dialog = ctk.CTkInputDialog(text="Please enter your GitHub Personal Access Token (starts with ghp_):", title="GitHub Token Required")
                    input_token = dialog.get_input()
                    
                    if not input_token:
                        messagebox.showerror("Upload Cancelled", "A GitHub token is required to publish to the repository.")
                        self.reset_ui()
                        return
                    
                    # Save it temporarily
                    GITHUB_TOKEN = input_token.strip()

                try:
                    # Actually test if the token works
                    g = Github(GITHUB_TOKEN)
                    repo = g.get_repo(GITHUB_REPO_NAME)
                except Exception as e:
                    # If it fails, wipe the bad token
                    GITHUB_TOKEN = "" 
                    
                    # Retry
                    retry = messagebox.askretrycancel(
                        "Authentication Failed", 
                        f"Could not connect to GitHub. Please check your token and permissions.\n\nError details: {str(e)}"
                    )
                    if not retry:
                        self.reset_ui()
                        return

            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(GITHUB_REPO_NAME)
            
            # Prepare Slugs
            title = data['title']
            # Folders go by mode name (books, films, articles) for image paths
            if self.mode == "Book": subfolder = "books"
            elif self.mode == "Film": subfolder = "films"
            else: subfolder = "articles"

            post_slug = clean_filename(f"{title} {self.mode} Review")
            today = datetime.now().strftime("%d-%m-%Y")

            with Image.open(self.selected_image_path) as check_img:
                # We want at least 420px height for the big version
                if check_img.height < 420:
                    messagebox.showerror(
                        "Image Too Small :(", 
                        f"The image is too small!\n\nIt needs to be at least 420px tall.\nYour image is only {check_img.height}px tall. :)"
                    )
                    self.reset_ui()
                    return

            # Cover image
            buf_280, name_280 = process_image_to_memory(self.selected_image_path, 280)

            if self.mode == "Article":
                buf_1200, name_1200 = process_image_to_width(self.selected_image_path, 1200)
                path_1200 = f"assets/images/{subfolder}/{name_1200}"
            else:
                 # Standard size used for Book/Film cards
                 buf_420, name_420 = process_image_to_memory(self.selected_image_path, 420)
                 path_420 = f"assets/images/{subfolder}/{name_420}"

            original_ext = os.path.splitext(self.selected_image_path)[1].lower()
            name_original = f"{post_slug}{original_ext}"
            
            # Read the raw bytes of the original file
            with open(self.selected_image_path, "rb") as f:
                buf_original = f.read()

            # Define paths
            path_280 = f"assets/images/{subfolder}/{name_280}"
            path_orig = f"assets/images/{subfolder}/originals/{name_original}"

            is_featured = self.check_featured.get() == 1
            featured_line = "true" if is_featured else "false"

            # Create Branch
            sb = repo.get_branch("main")
            branch_name = f"post-{post_slug}-{datetime.now().strftime('%H%M%S')}"
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sb.commit.sha)

            # --- ARTICLE HTML & IMAGE PROCESSING ---
            if self.mode == "Article":
                # Cleaned HTML
                body_content = self.gdocs_zip_data['cleaned_html']
                
                # Process & upload inline images
                inline_images = self.gdocs_zip_data['inline_images']
                
                # Split body content by image tags to get placeholders
                # Regex <img> tags with a src attribute
                parts = re.split(r'<img[^>]*src=[^>]*>', body_content)
                final_body = ""
                
                # The processor cleaned the HTML to have placeholders in the correct order
                for i, part in enumerate(parts):
                    # Re-add text chunk
                    final_body += part
                    
                    # Process and upload image if available for this slot
                    if i < len(inline_images):
                        img_info = inline_images[i]
                        img_slug = img_info['slug']
                        
                        # Max width 600px
                        buf_inline = process_inline_image(img_info['local_path'], max_width=600)
                        
                        if buf_inline:
                            inline_repo_path = f"assets/images/articles/inline/{img_slug}-{datetime.now().strftime('%H%M%S')}.webp"

                            self.safe_upload(repo, inline_repo_path, f"Inline Img: {img_slug}", buf_inline.getvalue(), branch_name)
                            
                            # Responsive view width (35vw) with desktop max (350px), centered
                            img_tag = f'\n<img src="/{inline_repo_path}" alt="{img_slug}" loading="lazy" style="max-width: 350px; width: 35vw; height: auto; border-radius: 8px; margin: 20px auto; display: block;">\n'
                            final_body += img_tag
                
                # Clean up any leftover text chunks after images are exhausted
                # (This happens if GDocs HTML logic left text without a closing <img> placeholder)
                # re.split usually appends leftover text to the final chunk, but this handles edge cases
                if len(parts) > len(inline_images) + 1:
                     messagebox.showerror("HTML Error", "There was an issue parsing the GDocs HTML structure. There are more text chunks than placeholders.")
                     self.reset_ui()
                     return

                body_content = final_body
            else:
                # Normal Markdown body for Books/Films
                body_content = data['body']

            # Create Markdown - Logic split for Book vs Film
            # Update date format for compatibility with Jekyll date fields
            date_field = datetime.now().strftime("%d-%m-%Y")

            if self.mode == "Book":
                md_content = f"""---
layout: review
category: "Book"
title: "{data['title']}"
seo_title: "{data['title']} | Book Review"
date: {date_field}
author: "{data['author']}"
genre: [{data['genre']}]
pages: {data['pages']}
rating: {data['rating']}
image: "/{path_280}"
isbn: "{data['isbn']}"
amznlink: "{data['amazon']}"
bookshplink: "{data['bookshop']}"
featured: {featured_line}
description: "{data['seodesc']}"
customdesc: "{data['customdesc']}"
---

{body_content}
"""
            elif self.mode == "Film":
                md_content = f"""---
layout: review
title: "{data['title']}"
seo_title: "{data['title']} | Movie Review"
date: {date_field}
# FILM SPECIFIC FIELDS
leading_actors: [{data['actors']}]
director: "{data['director']}"
run_time: "{data['runtime']}"
release_year: "{data['year']}" 
# STANDARD FIELDS
image: "/{path_280}"
genre: [{data['genre']}]
category: "Film"
rating: {data['rating']}
featured: {featured_line}
description: "{data['seodesc']}"
customdesc: "{data['customdesc']}"
author: "{data['author']}"
---

{body_content}
"""
            else: # Article
                md_content = f"""---
layout: article
title: "{data['title']}"
seo_title: "{data['title']} | Article"
date: {date_field}
image: "/{path_1200}"
category: "Article"
description: "{data['seodesc']}"
customdesc: "{data['customdesc']}"
author: "{data['author']}"
---

{body_content}
"""

            # Not using the variable today as we want 26 rather then 2026
            # Updated to use subfolder variable
			# TODO: we need to look in to this again as now were using

            post_filename_date = datetime.now().strftime("%d-%m-%y")
            md_filename = f"_posts/{subfolder}/{post_filename_date}-{post_slug}.md"

			# Upload Files
            if self.mode == "Article":
                self.safe_upload(repo, path_1200, f"Img 1200w: {title}", buf_1200.getvalue(), branch_name)
            else:
                self.safe_upload(repo, path_420, f"Img 420px: {title}", buf_420.getvalue(), branch_name)
                
            self.safe_upload(repo, path_280, f"Img 280px: {title}", buf_280.getvalue(), branch_name)
            self.safe_upload(repo, path_orig, f"Img Original Archival: {title}", buf_original, branch_name)
            self.safe_upload(repo, md_filename, f"Post MD: {title}", md_content, branch_name)

            # Pull Request
            pr = repo.create_pull(title=f"New Post: {title} ({self.mode})", body="Auto-generated via Publisher Tool", head=branch_name, base="main")

            messagebox.showinfo("Success", f"Done! PR Created.\n#{pr.number}")
            
            # Wipe the temporary folders
            self.cleanup_temp_folders()
            self.gdocs_zip_data = None 
            
            # Wipe the autosave draft
            if os.path.exists("autosave_draft.json"):
                os.remove("autosave_draft.json")
                
            self.reset_ui()

        except Exception as e:
            messagebox.showerror("Upload Error", f"Failed to publish:\n\n{str(e)}")
            self.reset_ui()

    def safe_upload(self, repo, path, message, content, branch):
        """
        Tries to Create a file. If it exists, it Updates it instead.
        """
        try:
            # Try to Create
            repo.create_file(path, message, content, branch=branch)
            print(f"Created: {path}")
            
        except Exception as e:
            # Fallback to Update
            # If create failed, it likely exists. We need to find the 'sha' to overwrite it.
            print(f"File exists ({path}), switching to Update mode...")
            try:
                # Get the existing file info to find its 'sha'
                contents = repo.get_contents(path, ref=branch)
                
                # Update it
                repo.update_file(path, message, content, contents.sha, branch=branch)
                print(f"Updated: {path}")
            except Exception as e2:
                # If it still fails, it's a real error (like permission issues)
                print(f"Critical Error uploading {path}: {e2}")
                raise

    def validate_inputs(self):
        # Gather raw data (Shared fields)
        title = self.entry_title.get()
        author = self.entry_author.get()
        raw_rating = self.entry_rating.get()
        raw_genre = self.entry_genre.get()
        
        # Book fields
        raw_pages = self.entry_pages.get()
        raw_isbn = self.entry_isbn.get()
        link_amzn = self.entry_amznlink.get()
        link_book = self.entry_bookshplink.get()

        # Film fields
        director = self.entry_director.get()
        raw_actors = self.entry_actors.get()
        runtime = self.entry_runtime.get()
        year = self.entry_year.get()

        # Basic Requirements Shared
        missing_fields = []
        if not title: missing_fields.append("Title")
        if not author: missing_fields.append("Author Name")
        if not self.selected_image_path: missing_fields.append("Cover Image")

        # Specific Requirements
        if self.mode != "Article":
            if not raw_genre: missing_fields.append("Genre")
            if not raw_rating: missing_fields.append("Rating")

        if self.mode == "Book":
             # Optional fields for book (maybe later)
             pass
        elif self.mode == "Film":
            if not director: missing_fields.append("Director")
            if not runtime: missing_fields.append("Run Time")
            if not year: missing_fields.append("Release Year")

        if missing_fields:
            error_msg = "The following fields are required:\n\n• " + "\n• ".join(missing_fields)
            messagebox.showerror("Missing Information", error_msg)
            return None

        # Rating Validation
        rating = ""
        if self.mode != "Article":
            try:
                rating = float(raw_rating)
                if rating < 0 or rating > 5: raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Rating", "Rating must be a number between 0 and 5 (e.g. 3.5 or 4)")
                return None

        # --- BOOK SPECIFIC VALIDATIONS ---
        pages_int = ""
        if self.mode == "Book":
            # Pages Validation
            if raw_pages:
                try:
                    pages_int = int(raw_pages)
                except ValueError:
                    messagebox.showerror("Invalid Pages", "Pages must be a whole number.")
                    return None

            # ISBN Validation
            if raw_isbn:
                clean_isbn = raw_isbn.replace("-", "").replace(" ", "")
                if not clean_isbn.isdigit():
                    messagebox.showerror("Invalid ISBN", "ISBN must contain only numbers.")
                    return None
                if len(clean_isbn) not in [10, 13]:
                    messagebox.showerror("Invalid ISBN", f"ISBN must be 10 or 13 digits.\nYou entered {len(clean_isbn)}.")
                    return None

            # Link Validation
            for name, url in [("Amazon", link_amzn), ("BookShop", link_book)]:
                if url and not url.lower().startswith("http"):
                    messagebox.showerror("Invalid Link", f"{name} link must start with http:// or https://")
                    return None
        
        # --- FILM SPECIFIC PROCESSING ---
        formatted_actors = ""
        if self.mode == "Film":
            if raw_actors:
                # Split by comma, remove spaces, add quotes
                a_list = [f'"{a.strip()}"' for a in raw_actors.split(',') if a.strip()]
                formatted_actors = ", ".join(a_list)

        # Genre processing (comma seperated and in quotations)
        formatted_genre = ""
        main_genre = "Article"
        if self.mode != "Article":
            if raw_genre:
                g_list = [f'"{g.strip()}"' for g in raw_genre.split(',') if g.strip()]
                formatted_genre = ", ".join(g_list)
                # Main genre for SEO desc (e.g., Romance novel, Comedy movie)
                main_genre = raw_genre.split(',')[0].strip()
            else:
                messagebox.showerror("No Genre supplied", f"{raw_genre} Need at least 1 genre")
                return None
        
        custom_desc_text = self.entry_custom_desc.get("1.0", "end-1c").strip()

        # SEO description
		# TODO: Maybe add some variation and pick randomly from multiple templates 
        if self.mode == "Article":
            # seo_description = f"Read our latest feature on {title}. A deep dive and discussion."
            seo_description = custom_desc_text
        else:
            type_str = "novel" if self.mode == "Book" else "movie"
            seo_description = f"Read our honest review on {title} a {main_genre} {type_str}. We discuss the plot, characters, and if it's worth the hype."

        # Return a dictionary of clean data if all passed
        return {
            "title": title,
            "author": author,
            "rating": rating,
            "genre": formatted_genre,
            "seodesc": seo_description,
            "customdesc": custom_desc_text,
            "body": self.entry_body.get("1.0", "end-1c"),
            # Book placeholders
            "pages": pages_int,
            "isbn": raw_isbn,
            "amazon": link_amzn,
            "bookshop": link_book,
            # Film placeholders
            "director": director,
            "actors": formatted_actors,
            "runtime": runtime,
            "year": year
        }

    def reset_ui(self):
        self.btn_submit.configure(state="normal", text=f"Publish {self.mode} Review")

    def start_save(self):
        """Starts the background loop that saves data every 10 seconds."""
        self.autosave_loop(force_save_message=True)

    def start_autosave(self):
        """Starts the background loop that saves data every 10 seconds."""
        self.autosave_loop()

    def autosave_loop(self, force_save_message=False):
        """Silently saves all current text inputs to a local JSON file."""
        try:
            # We don't save image paths as they might move/delete between sessions
            data = {
                "mode": self.mode,
                "title": self.entry_title.get(),
                "author": self.entry_author.get(),
                "genre": self.entry_genre.get(),
                "pages": self.entry_pages.get(),
                "isbn": self.entry_isbn.get(),
                "amznlink": self.entry_amznlink.get(),
                "bookshplink": self.entry_bookshplink.get(),
                "director": self.entry_director.get(),
                "actors": self.entry_actors.get(),
                "runtime": self.entry_runtime.get(),
                "year": self.entry_year.get(),
                "rating": self.entry_rating.get(),
                "customdesc": self.entry_custom_desc.get("1.0", "end-1c"),
                "body": self.entry_body.get("1.0", "end-1c"),
                "featured": self.check_featured.get(),
                "image_path": self.selected_image_path if self.selected_image_path else ""
            }
            
            # Only save if there is actually some text typed in somewhere
            has_content = any(str(v).strip() for k, v in data.items() if k != "mode")

            if has_content and data != self.last_saved_data:
                with open("autosave_draft.json", "w", encoding="utf-8") as f:
                    json.dump(data, f)
                
                # Update saved data tracker so we can only save when something changes
                self.last_saved_data = data

                # Show a little notification
                self.lbl_autosave.configure(text="Saved Draft")
                
                # Automatically erase text after some time
                self.after(2000, lambda: self.lbl_autosave.configure(text=""))
            elif force_save_message:
                self.lbl_autosave.configure(text="Saved Draft")
                self.after(2000, lambda: self.lbl_autosave.configure(text=""))

            if has_content:
                with open("autosave_draft.json", "w", encoding="utf-8") as f:
                    json.dump(data, f)
        except Exception as e:
            print(f"Autosave silently failed: {e}")
            
        # Schedule this function to run again in 10,000 milliseconds (10 seconds)
        self.after(10000, self.autosave_loop)

    def check_and_offer_autosave(self):
        """Checks for an existing draft on startup and offers to restore it."""
        if not os.path.exists("autosave_draft.json"):
            return
            
        try:
            with open("autosave_draft.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Double check there is actual text to restore
            has_content = any(str(v).strip() for k, v in data.items() if k != "mode")
            if not has_content:
                return
                
            if messagebox.askyesno("Unsaved Draft Found", "The tool found an unsaved draft from your last session.\n\nWould you like to restore it?"):
                # Restore the correct tab mode
                saved_mode = data.get("mode", "Book")
                self.mode_selector.set(saved_mode)
                self.switch_mode(saved_mode)
                
                # Helper to safely clear and insert text into CTk boxes
                def safe_insert(widget, text):
                    if not text: return
                    # Determine if this is a multi-line Textbox or a single-line Entry
                    if isinstance(widget, ctk.CTkTextbox):
                        widget.delete("1.0", "end")
                        widget.insert("1.0", str(text))
                    else:
                        widget.delete(0, "end")
                        widget.insert(0, str(text))
                        
                # Populate fields
                safe_insert(self.entry_title, data.get("title", ""))
                safe_insert(self.entry_author, data.get("author", ""))
                safe_insert(self.entry_genre, data.get("genre", ""))
                safe_insert(self.entry_pages, data.get("pages", ""))
                safe_insert(self.entry_isbn, data.get("isbn", ""))
                safe_insert(self.entry_amznlink, data.get("amznlink", ""))
                safe_insert(self.entry_bookshplink, data.get("bookshplink", ""))
                safe_insert(self.entry_director, data.get("director", ""))
                safe_insert(self.entry_actors, data.get("actors", ""))
                safe_insert(self.entry_runtime, data.get("runtime", ""))
                safe_insert(self.entry_year, data.get("year", ""))
                safe_insert(self.entry_rating, data.get("rating", ""))
                safe_insert(self.entry_custom_desc, data.get("customdesc", ""))
                safe_insert(self.entry_body, data.get("body", ""))

                if data.get("featured", 0) == 1:
                    self.check_featured.select()
                else:
                    self.check_featured.deselect()
                    
                # Restore the Cover Image if the file wasn't deleted or moved
                saved_img = data.get("image_path", "")
                if saved_img and os.path.exists(saved_img):
                    self.selected_image_path = saved_img
                    try:
                        pil_image = Image.open(saved_img)
                        aspect = pil_image.width / pil_image.height
                        target_height = 200
                        target_width = int(target_height * aspect)
                        self.my_preview_image = ctk.CTkImage(
                            light_image=pil_image,
                            dark_image=pil_image,
                            size=(target_width, target_height)
                        )
                        self.lbl_image.configure(image=self.my_preview_image, text="")
                    except Exception as e:
                        print(f"Failed to load autosaved image: {e}")
                
        except Exception as e:
            print(f"Failed to restore autosave: {e}")

    def on_closing(self):
            """Runs when the user clicks the X to close the window."""
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self.cleanup_temp_folders()
            self.destroy()

    def cleanup_temp_folders(self):
        """Finds and deletes any leftover Google Docs temporary folders."""
        try:
            # Look at every file/folder in the current directory
            for item in os.listdir('.'):
                if os.path.isdir(item) and item.startswith("temp_gdocs_"):
                    # Delete the folder and everything inside it
                    shutil.rmtree(item, ignore_errors=True)
                    print(f"Garbage Collection: Deleted {item}")
        except Exception as e:
            print(f"Garbage collection error: {e}")

class GDocsProcessor:
    def __init__(self, zip_path, title_slug):
        self.zip_path = zip_path
        self.title_slug = title_slug
        
        self.temp_root = f"temp_gdocs_{datetime.now().strftime('%H%M%S')}"
        self.extract_path = os.path.join(self.temp_root, "raw_extract")
        self.processed_img_path = os.path.join(self.temp_root, "processed_images")
        
        self.cleaned_html = ""
        self.inline_images = []

        if BeautifulSoup is None:
            raise ImportError("Required library beautifulsoup4 not installed. Processing failed.")

    def extract_and_clean(self):
        import urllib.parse
        os.makedirs(self.extract_path, exist_ok=True)
        os.makedirs(self.processed_img_path, exist_ok=True)

        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.extract_path)

        html_files = [f for f in os.listdir(self.extract_path) if f.lower().endswith(".html")]
        if not html_files:
            raise Exception("ZIP is missing an HTML file.")
        
        main_html_file = os.path.join(self.extract_path, html_files[0])

        with open(main_html_file, 'r', encoding='utf-8') as f:
            raw_html = f.read()

        soup = BeautifulSoup(raw_html, 'html.parser')

        # Perserve bold and italics
        bold_classes = set()
        italic_classes = set()
        for style_tag in soup.find_all("style"):
            css_text = style_tag.get_text()
            bold_classes.update(re.findall(r'\.([a-zA-Z0-9_-]+)\{[^\}]*font-weight:\s*(?:700|bold)', css_text))
            italic_classes.update(re.findall(r'\.([a-zA-Z0-9_-]+)\{[^\}]*font-style:\s*italic', css_text))

        for tag in soup(["style", "head", "script", "meta", "title"]):
            tag.decompose()
        
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.decompose()

        for span in soup.find_all("span"):
            children = [c for c in span.contents if c.name or str(c).strip()]
            if len(children) == 1 and children[0].name == "a":
                a_tag = children[0]
                a_tag['class'] = a_tag.get('class', []) + span.get('class', [])
                a_tag['style'] = a_tag.get('style', '') + ';' + span.get('style', '')
                span.unwrap()

        # Clean google redirect links
        for a_tag in soup.find_all("a"):
            href = a_tag.get("href", "")
            if "google.com/url?q=" in href:
                try:
                    parsed = urllib.parse.urlparse(href)
                    qs = urllib.parse.parse_qs(parsed.query)
                    if 'q' in qs:
                        a_tag['href'] = qs['q'][0]
                except:
                    pass

        # Affilate link builder
        for a_tag in soup.find_all("a"):
            text = a_tag.get_text(strip=True).lower()
            container = a_tag.find_parent(["p", "ul", "div"])
            if "amazon" in text or "bookshop" in text:
                if not container or not container.parent: continue
                
                if container.find_parent(class_="affiliate-section"): continue
                    
                amz_url = a_tag['href'] if "amazon" in text else None
                bs_url = a_tag['href'] if "bookshop" in text else None
                
                nodes_to_remove = [container]
                
                prev_sib = container.find_previous_sibling()
                if prev_sib and "check it out here" in prev_sib.get_text(strip=True).lower():
                    nodes_to_remove.append(prev_sib)
                    
                next_sib = container.find_next_sibling()
                if next_sib and next_sib.name in ["p", "li", "div"]:
                    next_a = next_sib.find("a")
                    if next_a:
                        next_text = next_a.get_text(strip=True).lower()
                        if "bookshop" in next_text and not bs_url:
                            bs_url = next_a['href']
                            nodes_to_remove.append(next_sib)
                        elif "amazon" in next_text and not amz_url:
                            amz_url = next_a['href']
                            nodes_to_remove.append(next_sib)
                            
                new_div = soup.new_tag("div", **{'class': 'affiliate-section'})
                btn_col = soup.new_tag("div", **{'class': 'affiliate-buttons-col'})
                
                if amz_url:
                    amz_btn = soup.new_tag("a", href=amz_url, target="_blank", rel="nofollow noopener", **{'class': 'buy-btn'})
                    amz_btn.string = "Amazon"
                    btn_col.append(amz_btn)
                if bs_url:
                    bs_btn = soup.new_tag("a", href=bs_url, target="_blank", rel="nofollow noopener", **{'class': 'buy-btn'})
                    bs_btn.string = "Bookshop"
                    btn_col.append(bs_btn)
                    
                new_div.append(btn_col)
                
                if bs_url:
                    msg_col = BeautifulSoup('''
                    <div class="affiliate-message-col">
                        <div class="bookshop-reason">
                        <span class="reason-icon">🌱</span>
                        <p>
                            <strong>Support Local:</strong> We recommend <strong>Bookshop.org</strong> to help keep independent bookstores alive.
                        </p>
                        </div>
                    </div>
                    ''', 'html.parser')
                    new_div.append(msg_col)
                    
                container.insert_before(new_div)
                for n in nodes_to_remove: n.decompose()
            # TODO: i think theres still a bug in here its late and im lost
            else:
                if not container or not container.parent: continue
                if container.find_parent(class_="read-more-callout"): continue

                new_div = soup.new_tag("div", **{'class': 'read-more-callout'})
                
                icon_span = soup.new_tag("span", **{'class': 'read-more-icon'})
                icon_span.string = "📖"
                
                text_wrapper = soup.new_tag("div", **{'class': 'read-more-text'})
                text_wrapper.extend(container.contents)
                
                new_div.append(icon_span)
                new_div.append(text_wrapper)
                new_div.append(a_tag)
                
                container.insert_before(new_div)
                container.decompose()

        # Apply bold and italics
        def wrap_contents(tag, wrapper_name):
            wrapper = soup.new_tag(wrapper_name)
            wrapper.extend(tag.contents)
            tag.clear()
            tag.append(wrapper)

        for tag in soup.find_all(["span", "a", "p", "ul", "li", "h1", "h2", "h3", "h4", "h5", "h6"]):
            classes = tag.get("class", [])
            style = tag.get("style", "").replace(" ", "").lower()
            
            is_bold = any(c in bold_classes for c in classes) or "font-weight:700" in style or "font-weight:bold" in style
            is_italic = any(c in italic_classes for c in classes) or "font-style:italic" in style
            
            if is_bold: wrap_contents(tag, "strong")
            if is_italic: wrap_contents(tag, "em")

        # Global attribute scrubbing
        valid_attributes = ['href', 'src', 'alt', 'target', 'rel', 'class']
        for tag in soup.find_all(True):
            non_essential = [attr for attr in tag.attrs if attr not in valid_attributes]
            for attr in non_essential: del tag[attr]
            
            # Keep our new custom CSS classes safe from the scrubber!
            if 'class' in tag.attrs:
                allowed_classes = [
                    'affiliate-section', 'affiliate-buttons-col', 'buy-btn', 
                    'affiliate-message-col', 'bookshop-reason', 'reason-icon',
                    'read-more-callout', 'read-more-icon', 'read-more-text'
                ]
                tag['class'] = [c for c in tag['class'] if c in allowed_classes]
                if not tag['class']: del tag['class']

        for span in soup.find_all("span"):
            if not span.attrs: span.unwrap()

        for h1 in soup.find_all("h1"): h1.name = "h2"

        for tag in soup.find_all(True):
            if tag.string: tag.string = tag.string.replace(u'\xa0', u' ')

        # Process inline images & dynamic naming
        header_counts = {}
        for img_tag in soup.find_all("img"):
            gdocs_src = img_tag.get("src")
            if not gdocs_src: continue

            raw_img_path = os.path.join(self.extract_path, gdocs_src.replace("\\", "/"))
            if not os.path.exists(raw_img_path):
                 img_tag.decompose()
                 continue
            
            header = img_tag.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
            if header and header.get_text(strip=True):
                base_slug = clean_filename(header.get_text(strip=True))
            else:
                base_slug = self.title_slug
                
            if base_slug not in header_counts:
                header_counts[base_slug] = 0
            header_counts[base_slug] += 1
            
            if header_counts[base_slug] == 1: img_slug = base_slug
            else: img_slug = f"{base_slug}-{header_counts[base_slug]}"

            processed_filename = f"{img_slug}-processed.webp"
            processed_local_path = os.path.join(self.processed_img_path, processed_filename)

            try:
                with Image.open(raw_img_path) as img:
                    if img.mode in ("RGBA", "P"): img = img.convert("RGBA")
                    else: img = img.convert("RGB")
                    img.save(processed_local_path, format="WEBP", quality=85)
            except Exception as e:
                img_tag.decompose()
                continue

            self.inline_images.append({
                'gdocs_src': gdocs_src,
                'slug': img_slug,
                'local_path': processed_local_path
            })
            
            img_tag['src'] = f"PLATFORM_PREVIEW_TEMP_IMG_{img_slug}"
            img_tag['alt'] = img_slug

        # Get cleaned HTML
        body_content = ""
        if soup.body:
             content_list = []
             for child in soup.body.children:
                 content_list.append(str(child))
             body_content = "".join(content_list).strip()
        else:
             body_content = str(soup).strip()

        self.cleaned_html = body_content

    def get_cleaned_data(self):
        return {
            'cleaned_html': self.cleaned_html,
            'inline_images': self.inline_images
        }

if __name__ == "__main__":
    app = SimplePublisher()
    app.mainloop()