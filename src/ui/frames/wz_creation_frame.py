"""
WZ creation frame for creating new WZ documents
"""
from tkinter import *
import tkinter.messagebox


class WzCreationFrame(Frame):
    """Frame for WZ creation"""
    
    def __init__(self, parent, nav_manager, wz_app_class):
        super().__init__(parent)
        self.nav_manager = nav_manager
        self.wz_app_class = wz_app_class
        self.wz_app_instance = None
        
        # Scroll conflict management
        self.is_over_product_table = False
        self.global_scroll_disabled = False
        self.mouse_check_job = None  # For periodic mouse position checking
        
        self.create_ui()
    
    def create_ui(self):
        """Create the WZ creation UI with scrollable content"""
        # Create a container for the WZ app
        self.wz_container = Frame(self, bg='white')
        self.wz_container.pack(fill=BOTH, expand=True)
        
        # Back button frame (top-left) - this stays fixed at top
        back_frame = Frame(self.wz_container, bg='white', height=40)
        back_frame.pack(fill=X, padx=10, pady=5)
        back_frame.pack_propagate(False)
        
        # Create back button
        self.back_btn = Button(back_frame, 
                              text="← Powrót do menu głównego",
                              font=("Arial", 12),
                              bg='#9E9E9E', fg='black',
                              padx=15, pady=5,
                              command=self.return_to_source,
                              cursor='hand2')
        self.back_btn.pack(side=LEFT)
        
        # Title indicating this is WZ creation mode
        title_label = Label(back_frame, 
                           text="TWORZENIE WZ",
                           font=("Arial", 16, "bold"),
                           bg='white', fg='#ff6600')
        title_label.pack(side=RIGHT, padx=20)
        
        # Create scrollable content area
        self.create_scrollable_content()
    
    def create_scrollable_content(self):
        """Create scrollable content area for the WZ application"""
        # Create frame for scrollable area
        scroll_frame = Frame(self.wz_container, bg='white')
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
        if (hasattr(self, 'wz_app_instance') and 
            self.wz_app_instance and 
            hasattr(self.wz_app_instance, 'product_table')):
            
            # Check if table has any items that might need scrolling
            try:
                item_count = len(self.wz_app_instance.product_table.tree.get_children())
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
            if (hasattr(self, 'wz_app_instance') and 
                self.wz_app_instance and 
                hasattr(self.wz_app_instance, 'product_table') and
                self.wz_app_instance.product_table.tree):
                
                # Get current mouse position relative to root window
                x = self.winfo_pointerx() - self.winfo_rootx()
                y = self.winfo_pointery() - self.winfo_rooty()
                
                # Check if cursor is over table area
                tree = self.wz_app_instance.product_table.tree
                scrollbar = self.wz_app_instance.product_table.scrollbar_y
                
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
    
    def initialize_wz_app(self):
        """Initialize the WZ application components"""
        try:
            # Always create a fresh WZ app instance
            # This ensures clean state when re-entering the frame
            from src.core.wz_generator_app import WzGeneratorApp
            self.wz_app_instance = WzGeneratorApp(self, self.nav_manager)
            
            # Force GUI update to ensure proper rendering
            self.update_idletasks()
            
            # Update scroll region after content is loaded
            self.after(100, self.update_scroll_region)
            
            # Start mouse position checking
            self.start_mouse_position_checking()
        except Exception as e:
            tkinter.messagebox.showerror("Błąd", f"Nie udało się załadować interfejsu tworzenia WZ: {e}")
            print(f"Detailed error: {e}")  # For debugging
    
    def update_scroll_region(self):
        """Force update of scroll region"""
        self.content_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def return_to_source(self):
        """Return to main menu"""
        # Clean up any resources if needed
        if self.wz_app_instance:
            try:
                # Try to clean up the WZ app instance properly
                if hasattr(self.wz_app_instance, 'cleanup'):
                    self.wz_app_instance.cleanup()
            except:
                pass  # Ignore cleanup errors
            self.wz_app_instance = None
        
        self.nav_manager.show_frame('main_menu')
    
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
        
        # Clean up WZ app instance to force recreation on next show
        if self.wz_app_instance:
            try:
                # Try to clean up the WZ app instance properly
                if hasattr(self.wz_app_instance, 'cleanup'):
                    self.wz_app_instance.cleanup()
            except:
                pass  # Ignore cleanup errors
            self.wz_app_instance = None
        
        # Clear content container to ensure fresh start
        if hasattr(self, 'content_container'):
            for widget in self.content_container.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass  # Ignore destruction errors
        
        self.pack_forget()
    
    def show(self):
        """Show this frame"""
        self.pack(fill=BOTH, expand=True)
        
        # Re-bind global mouse wheel events when showing
        self.bind_all("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Button-4>", self.on_mousewheel)
        self.bind_all("<Button-5>", self.on_mousewheel)
        self.bind_all("<Shift-MouseWheel>", self.on_mousewheel)
        
        # Initialize only if not already created (e.g. when coming with template_context)
        # NavigationManager may have already created wz_app_instance (with template). Don't overwrite it.
        if not self.wz_app_instance:
            self.initialize_wz_app()
        else:
            # Ensure scroll region reflects existing content
            self.after(100, self.update_scroll_region)
