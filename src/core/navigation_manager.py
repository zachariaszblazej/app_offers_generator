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
        """Show a specific frame and hide others"""
        if self.current_frame:
            self.current_frame.pack_forget()
        
        if frame_name in self.frames:
            self.current_frame = self.frames[frame_name]
            self.current_frame.pack(fill=BOTH, expand=True)
            
            # Initialize offer app if this is the offer creation frame
            if frame_name == 'offer_creation' and hasattr(self.current_frame, 'initialize_offer_app'):
                self.current_frame.initialize_offer_app()
            
            # Initialize offer editor if this is the offer editor frame
            elif frame_name == 'offer_editor' and hasattr(self.current_frame, 'initialize_offer_app'):
                offer_path = kwargs.get('offer_path')
                self.current_frame.initialize_offer_app(offer_path)
        else:
            raise ValueError(f"Frame '{frame_name}' not found")
