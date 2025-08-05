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
                # Create new editor instance with offer path
                from src.core.offer_editor_app import OfferEditorApp
                # Clear existing content
                for widget in self.frames[frame_name].content_container.winfo_children():
                    widget.destroy()
                # Create new editor app
                OfferEditorApp(self.frames[frame_name], self, kwargs['offer_path'])
            elif frame_name == 'offer_generator' and 'template_context' in kwargs:
                # Create new generator instance with template context
                from src.core.offer_generator_app import OfferGeneratorApp
                # Clear existing content
                for widget in self.frames[frame_name].content_container.winfo_children():
                    widget.destroy()
                # Create new generator app with template context
                OfferGeneratorApp(self.frames[frame_name], self, template_context=kwargs['template_context'])
            
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
