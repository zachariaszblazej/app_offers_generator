"""
Offer creation frame for creating new offers
"""
from tkinter import *
import tkinter.messagebox


class OfferCreationFrame(Frame):
    """Frame for offer creation (current functionality)"""
    
    def __init__(self, parent, nav_manager, offer_app_class):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.offer_app_class = offer_app_class
        self.offer_app_instance = None
        self.create_ui()
    
    def create_ui(self):
        """Create the offer creation UI with scrollable content"""
        # Create a container for the offer app
        self.offer_container = Frame(self, bg='white')
        self.offer_container.pack(fill=BOTH, expand=True)
        
        # Back button frame (top-left) - this stays fixed at top
        back_frame = Frame(self.offer_container, bg='white', height=40)
        back_frame.pack(fill=X, padx=10, pady=5)
        back_frame.pack_propagate(False)
        
        back_btn = Button(back_frame, 
                         text="← Powrót do menu głównego",
                         font=("Arial", 12),
                         bg='#9E9E9E', fg='black',
                         padx=15, pady=5,
                         command=self.return_to_main_menu,
                         cursor='hand2')
        back_btn.pack(side=LEFT)
        
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
        
        # Bind mouse wheel events to canvas
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        
        # Make sure the canvas can receive focus for mouse wheel events
        self.canvas.focus_set()
        
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
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        else:
            # For Linux
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(1, "units")
    
    def initialize_offer_app(self):
        """Initialize the offer application components"""
        try:
            if not self.offer_app_instance:
                self.offer_app_instance = self.offer_app_class(self, self.nav_manager)
                # Update scroll region after content is loaded
                self.after(100, self.update_scroll_region)
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować interfejsu tworzenia oferty: {e}")
            print(f"Detailed error: {e}")  # For debugging
    
    def update_scroll_region(self):
        """Force update of scroll region"""
        self.content_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def return_to_main_menu(self):
        """Return to main menu"""
        # Clean up any resources if needed
        if self.offer_app_instance:
            # Perform any necessary cleanup
            pass
        self.nav_manager.show_frame('main_menu')
    
    def hide(self):
        """Hide this frame"""
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
        # Initialize offer app when shown (only if not already initialized)
        if not self.offer_app_instance:
            self.initialize_offer_app()
