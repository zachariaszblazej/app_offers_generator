"""
Navigation manager for handling frame switching
"""
from tkinter import *


class NavigationManager:
    """Manages navigation between different screens/frames"""
    
    def __init__(self, root_window):
        self.root = root_window
        self.current_frame = None
        self.frames = {}
        
    def add_frame(self, name, frame_class, *args, **kwargs):
        """Add a frame to the navigation manager"""
        frame = frame_class(self.root, self, *args, **kwargs)
        self.frames[name] = frame
        return frame
    
    def show_frame(self, frame_name, **kwargs):
        """Show the specified frame with optional parameters"""
        # Hide all frames first
        for name, frame in self.frames.items():
            frame.hide()
        
        # Show the requested frame
        if frame_name in self.frames:
            # Handle special cases with parameters
            if frame_name == 'offer_editor' and 'offer_path' in kwargs:
                # Initialize editor with offer path using frame's method
                self.frames[frame_name].offer_path = kwargs['offer_path']
                # Clear existing instance to force recreation
                self.frames[frame_name].offer_app_instance = None
                # Clear existing content
                if hasattr(self.frames[frame_name], 'content_container'):
                    for widget in self.frames[frame_name].content_container.winfo_children():
                        widget.destroy()
                # Initialize with new offer path
                self.frames[frame_name].initialize_offer_app(kwargs['offer_path'])
            elif frame_name == 'wz_editor' and 'wz_path' in kwargs:
                # Initialize WZ editor with WZ path using frame's method
                self.frames[frame_name].wz_path = kwargs['wz_path']
                # Clear existing instance to force recreation
                self.frames[frame_name].wz_app_instance = None
                # Clear existing content
                if hasattr(self.frames[frame_name], 'content_container'):
                    for widget in self.frames[frame_name].content_container.winfo_children():
                        widget.destroy()
                # Initialize with new WZ path
                self.frames[frame_name].initialize_wz_app(kwargs['wz_path'])
            elif frame_name == 'offer_generator' and 'template_context' in kwargs:
                # Create new generator instance with template context
                from src.core.offer_generator_app import OfferGeneratorApp
                # Clear existing content
                for widget in self.frames[frame_name].content_container.winfo_children():
                    widget.destroy()
                # Create new generator app with template context and source frame information
                source_frame = kwargs.get('source_frame', None)
                self.frames[frame_name].offer_app_instance = OfferGeneratorApp(
                    self.frames[frame_name], 
                    self, 
                    template_context=kwargs['template_context'],
                    source_frame=source_frame
                )
                # Update back button text
                if hasattr(self.frames[frame_name], 'update_back_button_text'):
                    self.frames[frame_name].update_back_button_text()
            elif frame_name == 'offer_generator':
                # Regular generator without template - ensure it's initialized
                if not hasattr(self.frames[frame_name], 'offer_app_instance') or not self.frames[frame_name].offer_app_instance:
                    self.frames[frame_name].initialize_offer_app()
            elif frame_name == 'offer_creation':
                # Always create fresh instance for offer creation to ensure clean state
                # Clear existing content first
                if hasattr(self.frames[frame_name], 'content_container'):
                    for widget in self.frames[frame_name].content_container.winfo_children():
                        widget.destroy()
                # Always create new instance with template_context=None
                self.frames[frame_name].initialize_offer_app()
            elif frame_name == 'wz_creation':
                # Always create fresh instance for WZ creation to ensure clean state
                # Clear existing content first
                if hasattr(self.frames[frame_name], 'content_container'):
                    for widget in self.frames[frame_name].content_container.winfo_children():
                        widget.destroy()
                # Always create new instance
                self.frames[frame_name].initialize_wz_app()
            elif frame_name == 'browse_wz':
                # Refresh WZ list when showing browse frame
                if hasattr(self.frames[frame_name], 'refresh_wz_list'):
                    self.frames[frame_name].refresh_wz_list()
            
            self.frames[frame_name].show()
            self.current_frame = frame_name
        else:
            print(f"Frame '{frame_name}' not found!")
    
    def show_main_generator(self):
        """Show main generator without template"""
        if 'offer_generator' in self.frames:
            # Clear existing content
            for widget in self.frames['offer_generator'].content_container.winfo_children():
                widget.destroy()
            # Create new generator app without template
            from src.core.offer_generator_app import OfferGeneratorApp
            OfferGeneratorApp(self.frames['offer_generator'], self)
            self.show_frame('offer_generator')
