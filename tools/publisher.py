import customtkinter as ctk
from tkinter import filedialog, messagebox
from github import Github
from PIL import Image
import io
import os
import re
from datetime import datetime
import threading
import markdown 
from tkhtmlview import HTMLLabel

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

# Resize function for Inline Article Images (Width Based - Max 800px)
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

# UI
class SimplePublisher(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Quiet Readers Publisher Tool")
        self.geometry("550x900")
        self.selected_image_path = None
        self.mode = "Book" # Default to Book mode
        self.inline_images = []

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

        # Description
        self.desc_label = ctk.CTkLabel(self.scroll, text="Short Description: (1-2 lines preferably)")
        self.desc_label.pack(anchor="w", pady=(0), padx=(5))
        self.entry_custom_desc = ctk.CTkTextbox(self.scroll, height=60)
        self.entry_custom_desc.pack(fill="x", pady=5, padx=5)

        # Body
        ctk.CTkLabel(self.scroll, text="Full Review (Markdown):").pack(anchor="w", pady=(0), padx=(5))
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

        # Article Tools Container
        self.article_tools_container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.btn_set_inline = ctk.CTkButton(self.article_tools_container, text="Set Inline Images", command=self.set_inline_images, fg_color="#d35400")
        self.btn_set_inline.pack(pady=5, padx=5)

        # Image Selector
        self.btn_image = ctk.CTkButton(self.scroll, text="Select Cover Image", command=self.select_image, fg_color="#8e44ad")
        self.btn_image.pack(pady=5, padx=5)

        # Preview button
        self.btn_preview = ctk.CTkButton(self.scroll, text="Preview Post", command=self.open_preview, fg_color="#555555", height=32)
        self.btn_preview.pack(pady=20, padx=5)

        # Cover image preview
        self.lbl_image = ctk.CTkLabel(self.scroll, text="No image selected", text_color="gray")
        self.lbl_image.pack(pady=5, padx=5)

        # Submit
        self.btn_submit = ctk.CTkButton(self, text="Publish Book Review", height=50, command=self.start_upload, fg_color="green")
        self.btn_submit.pack(fill="x", padx=20, pady=20)

    def format_affiliate_links(self, html_text):
        
        # Match Both (Amazon followed by Bookshop)
        p1 = r'(?is)(?:<p[^>]*>\s*)?<a[^>]*href="([^"]+)"[^>]*>[^<]*Amazon[^<]*</a>\s*(?:</p>\s*)?(?:<p[^>]*>\s*)?<a[^>]*href="([^"]+)"[^>]*>[^<]*Bookshop[^<]*</a>(?:\s*</p>)?'
        html_text = re.sub(p1, r'%%%AFFILIATE_BOTH_||\1||\2%%%', html_text)
        
        # Match Both (Bookshop followed by Amazon - just in case they are flipped)
        p2 = r'(?is)(?:<p[^>]*>\s*)?<a[^>]*href="([^"]+)"[^>]*>[^<]*Bookshop[^<]*</a>\s*(?:</p>\s*)?(?:<p[^>]*>\s*)?<a[^>]*href="([^"]+)"[^>]*>[^<]*Amazon[^<]*</a>(?:\s*</p>)?'
        html_text = re.sub(p2, r'%%%AFFILIATE_BOTH_||\2||\1%%%', html_text)
        
        # Match Amazon Only (that didn't get caught in the pairs above)
        p3 = r'(?is)(?:<p[^>]*>\s*)?<a[^>]*href="([^"]+)"[^>]*>[^<]*Amazon[^<]*</a>(?:\s*</p>)?'
        html_text = re.sub(p3, r'%%%AFFILIATE_AMZ_||\1%%%', html_text)
        
        # Match Bookshop Only (that didn't get caught in the pairs above)
        p4 = r'(?is)(?:<p[^>]*>\s*)?<a[^>]*href="([^"]+)"[^>]*>[^<]*Bookshop[^<]*</a>(?:\s*</p>)?'
        html_text = re.sub(p4, r'%%%AFFILIATE_BS_||\1%%%', html_text)

        # Expand the tokens into the final, clean HTML blocks
        def expand_tokens(m):
            data = m.group(1).split('||')
            action = data[0]
            
            if action == "AFFILIATE_BOTH_":
                amz, bs = data[1], data[2]
                return f'''
<div class="affiliate-section">
    <div class="affiliate-buttons-col">
        <a href="{amz}" target="_blank" rel="nofollow noopener" class="buy-btn">
            Amazon
        </a>
        <a href="{bs}" target="_blank" rel="nofollow noopener" class="buy-btn">
            Bookshop
        </a>
    </div>
    <div class="affiliate-message-col">
        <div class="bookshop-reason">
        <span class="reason-icon">🌱</span>
        <p>
            <strong>Support Local:</strong> We recommend <strong>Bookshop</strong> to help keep independent bookstores alive.
        </p>
        </div>
    </div>
</div>
'''
            elif action == "AFFILIATE_AMZ_":
                amz = data[1]
                return f'''
<div class="affiliate-section">
    <div class="affiliate-buttons-col">
        <a href="{amz}" target="_blank" rel="nofollow noopener" class="buy-btn">
            Amazon
        </a>
    </div>
</div>
'''
            elif action == "AFFILIATE_BS_":
                bs = data[1]
                return f'''
<div class="affiliate-section">
    <div class="affiliate-buttons-col">
        <a href="{bs}" target="_blank" rel="nofollow noopener" class="buy-btn">
            Bookshop
        </a>
    </div>
    <div class="affiliate-message-col">
        <div class="bookshop-reason">
        <span class="reason-icon">🌱</span>
        <p>
            <strong>Support Local:</strong> We recommend <strong>Bookshop</strong> to help keep independent bookstores alive.
        </p>
        </div>
    </div>
</div>
'''
            return m.group(0)

        return re.sub(r'%%%([^%]+)%%%', expand_tokens, html_text)

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
        
        if value == "Book":
            # Show Book inputs safely above Description
            self.genre_container.pack(before=self.desc_label, fill="x")
            self.book_container.pack(before=self.desc_label, fill="x") 
            self.rating_container.pack(before=self.desc_label, fill="x")
            self.featured_container.pack(before=self.desc_label, fill="x")
            self.btn_submit.configure(text="Publish Book Review")
        elif value == "Film":
            # Show Film inputs safely above Description
            self.genre_container.pack(before=self.desc_label, fill="x")
            self.film_container.pack(before=self.desc_label, fill="x") 
            self.rating_container.pack(before=self.desc_label, fill="x")
            self.featured_container.pack(before=self.desc_label, fill="x")
            self.btn_submit.configure(text="Publish Film Review")
        elif value == "Article":
            self.article_tools_container.pack(before=self.btn_image, fill="x")
            self.btn_submit.configure(text="Publish Article")

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

    def set_inline_images(self):
        body_text = self.entry_body.get("1.0", "end-1c")
        parts = re.split(r'<pre class="prettyprint">\s*</pre>', body_text)
        
        if len(parts) <= 1:
            messagebox.showinfo("No Images Needed", "Could not find any <pre class=\"prettyprint\"></pre> placeholders in your text.")
            return

        self.inline_images = []
        for i in range(len(parts) - 1):
            context = parts[i]
            
            headings = re.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', context)
            closest_title = headings[-1] if headings else f"Image {i+1}"
            closest_title = re.sub(r'<[^>]+>', '', closest_title).strip()
            
            messagebox.showinfo("Inline Image Needed", f"Please select the image to go under:\n\n\"{closest_title}\"")
            
            img_path = filedialog.askopenfilename(title=f"Image for: {closest_title}", filetypes=[("Images", "*.jpg *.png *.jpeg *.webp")])
            if not img_path:
                messagebox.showerror("Cancelled", "Image selection cancelled. Your progress was not saved.")
                self.inline_images = []
                self.btn_set_inline.configure(text="Set Inline Images")
                return
            
            dialog = ctk.CTkInputDialog(text=f"Enter a short filename for this image\n(e.g. serpent-and-dove-cover):", title="Image Name")
            img_slug = dialog.get_input()
            if not img_slug:
                img_slug = f"inline-img-{i+1}"
                
            self.inline_images.append((img_path, clean_filename(img_slug)))
            
        messagebox.showinfo("Success", f"Successfully linked {len(self.inline_images)} inline images!")
        self.btn_set_inline.configure(text=f"Inline Images Set ({len(self.inline_images)})")

    def open_preview(self):
        # Run Validation First
        data = self.validate_inputs()
        if not data:
            return # Stop here if validation failed

        # Create the Pop-up Window
        preview = ctk.CTkToplevel(self)
        preview.title(f"{self.mode} Review Preview")
        preview.geometry("700x800")
        preview.attributes("-topmost", True)

        # Gather Data (From the CLEANED validation result)
        title = data['title']
        author = data['author']
        rating = data.get('rating', "")
        genre = data.get('genre', "")
        
        body_text = data['body']

        if self.mode == "Article":
            body_text = self.format_affiliate_links(body_text)

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
        
        if genre:
            ctk.CTkLabel(header_frame, text=genre.upper(), font=("Arial", 12), text_color="#888").pack(anchor="w")
            
        ctk.CTkLabel(header_frame, text=f"by {author}", font=("Georgia", 16, "italic"), text_color="#444").pack(anchor="w")
        
        if self.mode != "Article":
            ctk.CTkLabel(header_frame, text=f"Rating: {rating} / 5", font=("Arial", 14), text_color="#f39c12").pack(anchor="w", pady=10)

        # Extra Details - Dynamic based on mode
        details = []
        if self.mode == "Book":
            if data['pages']: details.append(f"{data['pages']} Pages")
            if data['isbn']: details.append(f"ISBN: {data['isbn']}")
        elif self.mode == "Film":
            if data['director']: details.append(f"Dir: {data['director']}")
            if data['year']: details.append(f"Year: {data['year']}")
            if data['runtime']: details.append(f"{data['runtime']}")
        
        if details:
            ctk.CTkLabel(header_frame, text=" | ".join(details), font=("Arial", 12), text_color="black").pack(anchor="w")

        # Actors (Film only)
        if self.mode == "Film" and data['actors']:
             # Clean quotes for display
             clean_actors = data['actors'].replace('"', '')
             ctk.CTkLabel(header_frame, text=f"Cast: {clean_actors}", font=("Arial", 12), text_color="#555").pack(anchor="w")

        # Link Check (Book only)
        if self.mode == "Book":
            links = []
            if data['amazon']: links.append("Amazon")
            if data['bookshop']: links.append("BookShop")
            if links:
                ctk.CTkLabel(header_frame, text="Links: " + ", ".join(links), font=("Arial", 12), text_color="green").pack(anchor="w", pady=5)

        # Image Thumbnail
        if hasattr(self, 'my_preview_image') and self.my_preview_image:
            img_label = ctk.CTkLabel(header_frame, text="", image=self.my_preview_image)
            img_label.place(relx=1.0, rely=0.0, anchor="ne")

        # Divider
        ctk.CTkFrame(page_frame, height=1, fg_color="#eee").pack(fill="x", padx=40, pady=(0, 20))

        # Body section
        parts = re.split(r'<pre class="prettyprint">\s*</pre>', body_text)
        
        for i, part in enumerate(parts):
            if part.strip():
                part_html = markdown.markdown(part)
                html_label = HTMLLabel(
                    page_frame, 
                    html=f"<div>{part_html}</div>",
                    background="white",
                    width=1
                )
                html_label.pack(fill="both", expand=True, padx=40, pady=5)
                html_label.fit_height()

            if self.mode == "Article" and self.inline_images and i < len(self.inline_images):
                img_path, _ = self.inline_images[i]
                try:
                    pil_img = Image.open(img_path)
                    target_width = 450
                    aspect = pil_img.height / pil_img.width
                    target_height = int(target_width * aspect)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(target_width, target_height))
                    img_label = ctk.CTkLabel(page_frame, text="", image=ctk_img)
                    img_label.image = ctk_img
                    img_label.pack(pady=20)
                except Exception:
                    err_lbl = ctk.CTkLabel(page_frame, text=f"[ Image Failed to Load: {os.path.basename(img_path)} ]", text_color="red")
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
            body_text = self.entry_body.get("1.0", "end-1c")
            parts = re.split(r'<pre class="prettyprint">\s*</pre>', body_text)
            placeholders = len(parts) - 1
            
            if placeholders > 0 and len(self.inline_images) != placeholders:
                answer = messagebox.askyesno(
                    "Missing Images", 
                    f"Warning: You have {placeholders} image placeholders in your text, but you have only set {len(self.inline_images)} images.\n\nDo you still want to publish without them?"
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
            data = self.validate_inputs()
            if not data:
                self.reset_ui()
                return

            # Connect to GitHub
            g = Github(GITHUB_TOKEN)
            repo = g.get_repo(GITHUB_REPO_NAME)
            
            # Prepare Slugs
            # We use your clean_filename logic for the folder slug too
            title = data['title']
            if self.mode == "Article": slug_text = f"{title} Article"
            else: slug_text = f"{title} {self.mode} Review"
            post_slug = clean_filename(slug_text)
            
            # TODO: and TEST
            # I think Jekyll requires Year-Month-Day (%Y-%m-%d) for filenames, 
            # or the posts won't appear in the right order.
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

            # Determine Paths based on Mode
            # Books go to _posts/books/ and assets/images/books/
            # Films go to _posts/films/ and assets/images/films/
            if self.mode == "Book": subfolder = "books"
            elif self.mode == "Film": subfolder = "films"
            else: subfolder = "articles"

            # Process images
            buf_420, name_420 = process_image_to_memory(self.selected_image_path, 420)
            buf_280, name_280 = process_image_to_memory(self.selected_image_path, 280)
            
            # NEW: Generate a 1200px wide image exclusively for Articles
            if self.mode == "Article":
                buf_1200, name_1200 = process_image_to_width(self.selected_image_path, 1200)
                path_1200 = f"assets/images/{subfolder}/{name_1200}"
            
            original_ext = os.path.splitext(self.selected_image_path)[1].lower()
            name_original = f"{post_slug}{original_ext}"
            
            # Read the raw bytes of the original file
            with open(self.selected_image_path, "rb") as f:
                buf_original = f.read()

            # Define Paths (Updated to use subfolder variable)
            path_420 = f"assets/images/{subfolder}/{name_420}"
            path_280 = f"assets/images/{subfolder}/{name_280}"
            path_orig = f"assets/images/{subfolder}/originals/{name_original}"

            is_featured = self.check_featured.get() == 1
            featured_line = "true" if is_featured else "false"

            # Create Branch & Commit early
            sb = repo.get_branch("main")
            branch_name = f"post-{post_slug}-{datetime.now().strftime('%H%M%S')}"
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=sb.commit.sha)

            # --- ARTICLE HTML & IMAGE PROCESSING ---
            body_content = data['body']
            if self.mode == "Article":
                
                body_content = self.format_affiliate_links(body_content)

                if self.inline_images:
                    parts = re.split(r'<pre class="prettyprint">\s*</pre>', body_content)
                    final_body = ""
                    for i in range(len(self.inline_images)):
                        if i < len(parts) - 1:
                            img_path, img_slug = self.inline_images[i]
                            
                            # Max width dropped to 600 to keep it a reasonable reading size
                            buf_inline = process_inline_image(img_path, max_width=600)
                            inline_repo_path = f"assets/images/articles/inline/{img_slug}-{datetime.now().strftime('%H%M%S')}.webp"
                            self.safe_upload(repo, inline_repo_path, f"Inline Img: {img_slug}", buf_inline.getvalue(), branch_name)
                            
                            img_tag = f'\n<img src="/{inline_repo_path}" alt="{img_slug}" loading="lazy" style="max-width: 250px; width: 35vw; height: auto; border-radius: 8px; margin: 20px auto; display: block;">\n'
                            final_body += parts[i] + img_tag
                        
                    remaining = parts[len(self.inline_images):]
                    final_body += "<pre class='prettyprint'></pre>".join(remaining)
                    body_content = final_body

            # Create Markdown - Logic split for Book vs Film
            if self.mode == "Book":
                md_content = f"""---
layout: review
category: "Book"
title: "{data['title']}"
seo_title: "{data['title']} | Book Review"
date: {today}
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
date: {today}
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
date: {today}
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
            md_filename = f"_posts/{subfolder}/{datetime.now().strftime('%d-%m-%y')}-{post_slug}.md"

            # Upload Files
            if self.mode == "Article":
                self.safe_upload(repo, path_1200, f"Img 1200: {title}", buf_1200.getvalue(), branch_name)
            else:
                self.safe_upload(repo, path_420, f"Img 420: {title}", buf_420.getvalue(), branch_name)
                
            self.safe_upload(repo, path_280, f"Img 280: {title}", buf_280.getvalue(), branch_name)
            self.safe_upload(repo, path_orig, f"Img Original: {title}", buf_original, branch_name)
            self.safe_upload(repo, md_filename, f"Post: {title}", md_content, branch_name)

            # Pull Request
            pr = repo.create_pull(title=f"New Post: {title}", body="Auto-generated", head=branch_name, base="main")

            messagebox.showinfo("Success", f"Done! PR Created.\n#{pr.number}")
            self.reset_ui()

        except Exception as e:
            messagebox.showerror("Error", str(e))
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
                messagebox.showinfo("Notice", f"({path})\nFile already exists on repo! We will send a request to update it.\n Dont worry about it - just tell me this message showed up and send a screenshot")
                print(f"Updated: {path}")
            except Exception as e2:
                # If it still fails, it's a real error (like permission issues)
                print(f"Critical Error uploading {path}: {e2}")

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
             # Optional: Add strict requirement for pages if you want? 
             pass
        elif self.mode == "Film":
            if not director: missing_fields.append("Director")
            if not runtime: missing_fields.append("Run Time")
            if not year: missing_fields.append("Release Year")

        if missing_fields:
            # Join them with commas (e.g. "Book Title, Rating")
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

        # Image Size Validation (Keep your original logic)
        with Image.open(self.selected_image_path) as img:
            if img.height < 420:
                messagebox.showerror("Image Too Small", f"Image must be at least 420px tall.\nYours is {img.height}px.")
                return None
        
        # Genre processing (comma seperated and in quotations)
        formatted_genre = ""
        main_genre = "Book"
        if self.mode != "Article":
            if raw_genre:
                # Split by comma, remove spaces, add quotes
                g_list = [f'"{g.strip()}"' for g in raw_genre.split(',') if g.strip()]
                formatted_genre = ", ".join(g_list)
                main_genre = raw_genre.split(',')[0].strip()
            else:
                messagebox.showerror("No Genre supplied", f"{raw_genre} Need at least 1 genre")
                return None
        
        # SEO description
        # TODO: Maybe add some variation and pick randomly from multiple templates 
        if self.mode == "Article":
            seo_description = f"Read our latest feature on {title}. A deep dive and discussion."
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
            "customdesc": self.entry_custom_desc.get("1.0", "end-1c").strip(),
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

if __name__ == "__main__":
    app = SimplePublisher()
    app.mainloop()