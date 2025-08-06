"""
Offer editor frame for editing existing offers
"""
from tkinter import *
import tkinter.messagebox
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class OfferEditorFrame(Frame):
    """Frame for editing existing offers"""
    
    def __init__(self, parent, nav_manager, offer_app_class, offer_path=None):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offer_app_class = offer_app_class
        self.offer_app_instance = None
        self.offer_path = offer_path
        self.create_ui()
    
    def create_ui(self):
        """Create the offer editor UI with scrollable content"""
        # Create a container for the offer app
        self.offer_container = Frame(self, bg='white')
        self.offer_container.pack(fill=BOTH, expand=True)
        
        # Back button frame (top-left) - this stays fixed at top
        back_frame = Frame(self.offer_container, bg='white', height=40)
        back_frame.pack(fill=X, padx=10, pady=5)
        back_frame.pack_propagate(False)
        
        back_btn = Button(back_frame, 
                         text="← Powrót do przeglądania ofert",
                         font=("Arial", 12),
                         bg='#9E9E9E', fg='black',
                         padx=15, pady=5,
                         command=self.return_to_browse_offers,
                         cursor='hand2')
        back_btn.pack(side=LEFT)
        
        # Title indicating this is edit mode
        title_label = Label(back_frame, 
                           text="EDYCJA OFERTY",
                           font=("Arial", 16, "bold"),
                           bg='white', fg='#ff6600')
        title_label.pack(side=RIGHT, padx=20)
        
        # Create scrollable content area
        self.create_scrollable_content()
    
    def create_scrollable_content(self):
        """Create scrollable content area for the offer application"""
        # Create frame for scrollable area
        scroll_frame = Frame(self.offer_container, bg='white')
        scroll_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Create canvas and scrollbar
        self.canvas = Canvas(scroll_frame, bg='white', highlightthickness=0)
        self.scrollbar = Scrollbar(scroll_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack scrollbar and canvas
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create content container inside canvas
        self.content_container = Frame(self.canvas, bg='white')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_container, anchor="nw")
        
        # Bind events for proper scrolling
        self.content_container.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Bind mouse wheel events to canvas and its parent
        self.bind_mousewheel(self.canvas)
        self.bind_mousewheel(self.canvas.master)
        self.bind_mousewheel(self)
        
        # Make sure the canvas can receive focus for mouse wheel events
        self.canvas.focus_set()
        
        # Add enter/leave events to handle focus
        self.canvas.bind("<Enter>", self.on_canvas_enter)
        self.canvas.bind("<Leave>", self.on_canvas_leave)
    
    def on_canvas_enter(self, event):
        """When mouse enters canvas, bind mousewheel events globally"""
        self.canvas.focus_set()
        
    def on_canvas_leave(self, event):
        """When mouse leaves canvas, we can keep the bindings active"""
        pass
    
    def bind_mousewheel(self, widget):
        """Bind mouse wheel events for scrolling - enhanced for better compatibility"""
        # Standard mouse wheel events
        widget.bind("<MouseWheel>", self.on_mousewheel)  # Windows
        widget.bind("<Button-4>", self.on_mousewheel)    # Linux scroll up
        widget.bind("<Button-5>", self.on_mousewheel)    # Linux scroll down
        
        # macOS specific events
        widget.bind("<Shift-MouseWheel>", self.on_mousewheel)  # macOS touchpad
        
        # Try to bind to all child widgets as well for better coverage
        for child in widget.winfo_children():
            try:
                self.bind_mousewheel(child)
            except:
                pass
        
    def unbind_mousewheel(self, widget):
        """Unbind mouse wheel events from a widget"""
        widget.unbind("<MouseWheel>")
        widget.unbind("<Button-4>")
        widget.unbind("<Button-5>")
        widget.unbind("<Shift-MouseWheel>")
        
    def on_frame_configure(self, event):
        """Update scroll region when content changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # Force an update to ensure proper sizing
        self.canvas.update_idletasks()
        
    def on_canvas_configure(self, event):
        """Update canvas window width when canvas size changes"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
    def on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        # Check if we're on macOS or Windows/Linux
        if event.delta:
            # Windows and macOS
            delta = event.delta
            # Normalize delta for different platforms
            if abs(delta) >= 120:
                scroll_amount = int(-1 * (delta / 120))
            else:
                scroll_amount = -1 if delta > 0 else 1
            self.canvas.yview_scroll(scroll_amount, "units")
        else:
            # Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
    
    def initialize_offer_app(self, offer_path=None):
        """Initialize the offer application components for editing"""
        try:
            if not self.offer_app_instance:
                # Create a modified offer app for editing
                from src.core.offer_editor_app import OfferEditorApp
                self.offer_app_instance = OfferEditorApp(self, self.nav_manager, offer_path or self.offer_path)
                # Update scroll region after content is loaded
                self.after(100, self.update_scroll_region)
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować interfejsu edycji oferty: {e}")
            print(f"Detailed error: {e}")  # For debugging
    
    def update_scroll_region(self):
        """Force update of scroll region"""
        self.content_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def return_to_browse_offers(self):
        """Return to browse offers"""
        # Clean up any resources if needed
        if self.offer_app_instance:
            # Perform any necessary cleanup
            pass
        self.nav_manager.show_frame('browse_offers')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
        # Ensure offer app is initialized when frame is shown
        if not self.offer_app_instance and self.offer_path:
            self.initialize_offer_app(self.offer_path)
