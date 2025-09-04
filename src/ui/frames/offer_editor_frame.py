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
        
        # Scroll conflict management
        self.is_over_product_table = False
        self.global_scroll_disabled = False
        self.mouse_check_job = None  # For periodic mouse position checking
        
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

        back_btn = Button(
            back_frame,
            text="← Powrót do przeglądania ofert",
            font=("Arial", 12),
            bg='#9E9E9E', fg='black',
            padx=15, pady=5,
            command=self.return_to_browse_offers,
            cursor='hand2'
        )
        back_btn.pack(side=LEFT)

        # Placeholder for header action (save)
        self.action_btn = Button(
            back_frame,
            text="Zapisz zmiany",
            font=("Arial", 12, "bold"),
            bg='#ffcc00', fg='black',
            padx=15, pady=5,
            cursor='hand2'
        )
        self.action_btn.pack(side=LEFT, padx=(10, 0))
        
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
        
        # Bind globally to the entire frame for universal scrolling
        self.bind_all("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Button-4>", self.on_mousewheel)
        self.bind_all("<Button-5>", self.on_mousewheel)
        self.bind_all("<Shift-MouseWheel>", self.on_mousewheel)
    
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
        """Handle mouse wheel scrolling with product table conflict detection"""
        try:
            # Only scroll if this frame is currently visible
            if not self.winfo_viewable():
                return
            
            # Check if we should disable global scrolling due to product table
            if self.global_scroll_disabled:
                return
                
            # Different handling for different platforms and event types
            if event.delta:
                # Windows and macOS
                delta = event.delta
                # Normalize delta for better scrolling experience
                if abs(delta) > 100:
                    delta = delta // abs(delta) * 120  # Normalize to standard wheel step
            elif event.num == 4:
                # Linux scroll up
                delta = 120
            elif event.num == 5:
                # Linux scroll down
                delta = -120
            else:
                delta = 0
            
            # Apply scrolling to canvas
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        except Exception as e:
            pass  # Silently ignore scrolling errors
    
    def on_product_table_enter(self):
        """Called when mouse enters product table area (event-based backup)"""
        # Always disable global scroll when over table if table has items
        if (hasattr(self, 'offer_app_instance') and 
            self.offer_app_instance and 
            hasattr(self.offer_app_instance, 'product_table')):
            
            # Check if table has any items that might need scrolling
            try:
                item_count = len(self.offer_app_instance.product_table.tree.get_children())
                if item_count >= 5:  # Conservative threshold - disable scroll for 5+ items
                    self.global_scroll_disabled = True
                    self.is_over_product_table = True
            except:
                # If we can't check items, assume scrollbar might be needed
                self.global_scroll_disabled = True
                self.is_over_product_table = True
    
    def on_product_table_leave(self):
        """Called when mouse leaves product table area (event-based backup)"""
        self.global_scroll_disabled = False
        self.is_over_product_table = False
    
    def start_mouse_position_checking(self):
        """Start periodic checking of mouse position relative to product table"""
        self.check_mouse_position()
    
    def check_mouse_position(self):
        """Check if mouse is over product table and adjust scroll behavior"""
        try:
            if (hasattr(self, 'offer_app_instance') and 
                self.offer_app_instance and 
                hasattr(self.offer_app_instance, 'product_table') and
                self.offer_app_instance.product_table.tree):
                
                # Get current mouse position relative to root window
                x = self.winfo_pointerx() - self.winfo_rootx()
                y = self.winfo_pointery() - self.winfo_rooty()
                
                # Check if cursor is over table area
                tree = self.offer_app_instance.product_table.tree
                scrollbar = self.offer_app_instance.product_table.scrollbar_y
                
                # Get table bounds
                try:
                    table_x = tree.winfo_x()
                    table_y = tree.winfo_y() 
                    table_width = tree.winfo_width()
                    table_height = tree.winfo_height()
                    
                    # Get scrollbar bounds
                    sb_x = scrollbar.winfo_x()
                    sb_y = scrollbar.winfo_y()
                    sb_width = scrollbar.winfo_width()
                    sb_height = scrollbar.winfo_height()
                    
                    # Check if mouse is over table or scrollbar
                    over_table = (table_x <= x <= table_x + table_width and 
                                 table_y <= y <= table_y + table_height)
                    over_scrollbar = (sb_x <= x <= sb_x + sb_width and 
                                     sb_y <= y <= sb_y + sb_height)
                    
                    is_over_table_area = over_table or over_scrollbar
                    
                    # Check if table has many items (likely needs scrolling)
                    item_count = len(tree.get_children())
                    
                    if is_over_table_area and item_count >= 5:
                        if not self.global_scroll_disabled:
                            self.global_scroll_disabled = True
                            self.is_over_product_table = True
                    else:
                        if self.global_scroll_disabled:
                            self.global_scroll_disabled = False
                            self.is_over_product_table = False
                            
                except Exception as e:
                    pass  # Ignore widget geometry errors
                    
        except Exception as e:
            pass  # Ignore any errors in mouse checking
        
        # Schedule next check
        if self.mouse_check_job:
            self.after_cancel(self.mouse_check_job)
        self.mouse_check_job = self.after(100, self.check_mouse_position)  # Check every 100ms
    
    def initialize_offer_app(self, offer_path=None):
        """Initialize the offer application components for editing"""
        try:
            if not self.offer_app_instance:
                # Create a modified offer app for editing
                from src.core.offer_editor_app import OfferEditorApp
                self.offer_app_instance = OfferEditorApp(self, self.nav_manager, offer_path or self.offer_path)
                # Update scroll region after content is loaded
                self.after(100, self.update_scroll_region)
                
                # Wire header action button to app's update_offer now that instance exists
                try:
                    if hasattr(self, 'action_btn') and self.action_btn.winfo_exists():
                        self.action_btn.config(command=self.offer_app_instance.update_offer)
                except Exception:
                    pass
                
                # Start mouse position checking
                self.start_mouse_position_checking()
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
        # Stop mouse position checking
        if self.mouse_check_job:
            self.after_cancel(self.mouse_check_job)
            self.mouse_check_job = None
            
        # Unbind global mouse wheel events to prevent conflicts
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")
        self.unbind_all("<Shift-MouseWheel>")
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
        
        # Re-bind global mouse wheel events when showing
        self.bind_all("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Button-4>", self.on_mousewheel)
        self.bind_all("<Button-5>", self.on_mousewheel)
        self.bind_all("<Shift-MouseWheel>", self.on_mousewheel)
        
        # Ensure offer app is initialized when frame is shown
        if not self.offer_app_instance and self.offer_path:
            self.initialize_offer_app(self.offer_path)
