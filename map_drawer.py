import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, Scale
import json
import math
import logging
from datetime import datetime
import numpy as np
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('house_map_app.log')
    ]
)

class DrawingObject:
    """Base class for all drawing objects"""
    def __init__(self, canvas, x1, y1, x2=None, y2=None, **kwargs):
        self.canvas = canvas
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2
        self.id = None
        self.label_id = None
        self.handles = []
        self.properties = kwargs
        self.selected = False
        self.dragging_handle = None
        
    def draw(self):
        pass
    
    def contains_point(self, x: float, y: float, tolerance: Optional[float] = None) -> bool:
        return False
    
    def move(self, dx, dy):
        pass
    
    def draw_handles(self):
        """Draw selection handles"""
        if not self.selected:
            return
            
        # Remove existing handles
        for handle in self.handles:
            self.canvas.delete(handle)
        self.handles.clear()
        
        # Get handle positions
        handle_positions = self.get_handle_positions()
        
        for x, y in handle_positions:
            handle = self.canvas.create_oval(
                x-4, y-4, x+4, y+4,
                fill='red', outline='red',
                tags=('handle', 'object')
            )
            self.handles.append(handle)
    
    def get_handle_positions(self):
        """Return positions of adjustment handles"""
        return []
    
    def is_handle_hit(self, x, y):
        """Check if a handle was clicked"""
        if not self.selected:
            return None
            
        handle_positions = self.get_handle_positions()
        for i, (hx, hy) in enumerate(handle_positions):
            if abs(hx - x) <= 4 and abs(hy - y) <= 4:
                return i
        return None
    
    def update_from_handle(self, handle_index, x, y):
        """Update object based on handle drag"""
        pass
    
    def calculate_length(self):
        """Calculate length in real world units"""
        return 0
    
    def update_label(self):
        """Update dimension label"""
        if self.label_id:
            self.canvas.delete(self.label_id)
            self.label_id = None
    
    def to_dict(self):
        return {
            'type': self.__class__.__name__,
            'x1': self.x1,
            'y1': self.y1,
            'x2': self.x2,
            'y2': self.y2,
            'properties': self.properties
        }
    
    @classmethod
    def from_dict(cls, canvas, data):
        return cls(canvas, data['x1'], data['y1'], data['x2'], data['y2'], **data['properties'])

class Wall(DrawingObject):
    def __init__(self, canvas, x1, y1, x2, y2, **kwargs):
        super().__init__(canvas, x1, y1, x2, y2, **kwargs)
        self.properties.setdefault('width', 3)
        self.properties.setdefault('color', 'black')
        self.properties.setdefault('curvature', 0)  # 0 = straight, positive/negative = curve direction
        self.properties.setdefault('rotation', 0)  # Rotation angle in degrees
        self.draw()
        
    def draw(self):
        if self.id:
            self.canvas.delete(self.id)
        
        # Apply rotation if any
        x1, y1, x2, y2 = self.get_rotated_points()
        
        curvature = self.properties.get('curvature', 0)
        
        if curvature == 0:
            # Straight line
            self.id = self.canvas.create_line(
                x1, y1, x2, y2,
                width=self.properties['width'],
                fill=self.properties['color'],
                tags=('wall', 'object')
            )
        else:
            # Curved line using quadratic Bezier curve
            control_x = (x1 + x2) / 2
            control_y = (y1 + y2) / 2
            
            # Calculate perpendicular direction for curvature
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                perp_x, perp_y = -dy/length, dx/length
                curve_distance = curvature * length * 0.3  # Adjust curvature strength
                control_x += perp_x * curve_distance
                control_y += perp_y * curve_distance
            
            # Create curved line using multiple line segments
            points = []
            for t in np.linspace(0, 1, 20):
                x = (1-t)**2 * x1 + 2*(1-t)*t * control_x + t**2 * x2
                y = (1-t)**2 * y1 + 2*(1-t)*t * control_y + t**2 * y2
                points.extend([x, y])
            
            self.id = self.canvas.create_line(
                *points,
                width=self.properties['width'],
                fill=self.properties['color'],
                smooth=False,  # We're creating our own curve
                tags=('wall', 'object')
            )
        
        if self.selected:
            self.canvas.itemconfig(self.id, width=self.properties['width'] + 2, fill='red')
        
        # Don't draw length label (removed as requested)
        self.draw_handles()
    
    def get_rotated_points(self):
        """Calculate rotated endpoints based on rotation angle"""
        if self.properties.get('rotation', 0) == 0:
            return self.x1, self.y1, self.x2, self.y2
        
        # Calculate center point
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        
        # Calculate original vector from center
        vec1_x = self.x1 - center_x
        vec1_y = self.y1 - center_y
        vec2_x = self.x2 - center_x
        vec2_y = self.y2 - center_y
        
        # Apply rotation
        angle_rad = math.radians(self.properties['rotation'])
        cos_angle = math.cos(angle_rad)
        sin_angle = math.sin(angle_rad)
        
        # Rotate first point
        new_x1 = center_x + vec1_x * cos_angle - vec1_y * sin_angle
        new_y1 = center_y + vec1_x * sin_angle + vec1_y * cos_angle
        
        # Rotate second point
        new_x2 = center_x + vec2_x * cos_angle - vec2_y * sin_angle
        new_y2 = center_y + vec2_x * sin_angle + vec2_y * cos_angle
        
        return new_x1, new_y1, new_x2, new_y2
    
    def contains_point(self, x: float, y: float, tolerance: Optional[float] = None) -> bool:
        if tolerance is None:
            tolerance = 8
            
        # Use rotated points for hit testing
        x1, y1, x2, y2 = self.get_rotated_points()
        
        if self.properties.get('curvature', 0) == 0:
            # Straight line hit test
            line_vector = (x2 - x1, y2 - y1)
            point_vector = (x - x1, y - y1)
            
            line_length_squared = line_vector[0]**2 + line_vector[1]**2
            if line_length_squared == 0:
                return False
                
            t = max(0, min(1, (point_vector[0]*line_vector[0] + point_vector[1]*line_vector[1]) / line_length_squared))
            
            closest_point = (
                x1 + t * line_vector[0],
                y1 + t * line_vector[1]
            )
            
            distance = math.sqrt((x - closest_point[0])**2 + (y - closest_point[1])**2)
            return distance <= tolerance
        else:
            # Curved line hit test - approximate with multiple segments
            control_x = (x1 + x2) / 2
            control_y = (y1 + y2) / 2
            
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                perp_x, perp_y = -dy/length, dx/length
                curve_distance = self.properties['curvature'] * length * 0.3
                control_x += perp_x * curve_distance
                control_y += perp_y * curve_distance
            
            # Check distance to curve segments
            prev_x, prev_y = x1, y1
            for t in np.linspace(0, 1, 20):
                curve_x = (1-t)**2 * x1 + 2*(1-t)*t * control_x + t**2 * x2
                curve_y = (1-t)**2 * y1 + 2*(1-t)*t * control_y + t**2 * y2
                
                if t > 0:
                    # Check distance to segment
                    seg_vec = (curve_x - prev_x, curve_y - prev_y)
                    pt_vec = (x - prev_x, y - prev_y)
                    
                    seg_len_sq = seg_vec[0]**2 + seg_vec[1]**2
                    if seg_len_sq > 0:
                        t_seg = max(0, min(1, (pt_vec[0]*seg_vec[0] + pt_vec[1]*seg_vec[1]) / seg_len_sq))
                        closest_x = prev_x + t_seg * seg_vec[0]
                        closest_y = prev_y + t_seg * seg_vec[1]
                        
                        distance = math.sqrt((x - closest_x)**2 + (y - closest_y)**2)
                        if distance <= tolerance:
                            return True
                
                prev_x, prev_y = curve_x, curve_y
            
            return False
    
    def move(self, dx, dy):
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy
        self.draw()
    
    def get_handle_positions(self):
        handles = []
        
        # Use rotated points for handles
        x1, y1, x2, y2 = self.get_rotated_points()
        
        # Endpoint handles
        handles.append((x1, y1))
        handles.append((x2, y2))
        
        # Rotation handle (placed at a distance from the center)
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        if length > 0:
            # Place rotation handle perpendicular to the wall
            dx, dy = (x2 - x1)/length, (y2 - y1)/length
            perp_x, perp_y = -dy, dx
            rotation_handle_distance = 30
            rotation_x = center_x + perp_x * rotation_handle_distance
            rotation_y = center_y + perp_y * rotation_handle_distance
            handles.append((rotation_x, rotation_y))
        
        # Curvature adjustment handle (only for curved walls)
        if self.properties.get('curvature', 0) != 0:
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                perp_x, perp_y = -dy/length, dx/length
                curve_distance = self.properties['curvature'] * length * 0.3
                handle_x = mid_x + perp_x * (curve_distance + 20)  # Offset for better usability
                handle_y = mid_y + perp_y * (curve_distance + 20)
                handles.append((handle_x, handle_y))
        
        return handles
    
    def update_from_handle(self, handle_index, x, y):
        if handle_index == 0:  # Start point
            self.x1, self.y1 = x, y
        elif handle_index == 1:  # End point
            self.x2, self.y2 = x, y
        elif handle_index == 2:  # Rotation handle
            # Calculate rotation angle based on handle position
            center_x = (self.x1 + self.x2) / 2
            center_y = (self.y1 + self.y2) / 2
            
            # Vector from center to rotation handle
            handle_vec_x = x - center_x
            handle_vec_y = y - center_y
            
            # Vector from center to original perpendicular direction
            dx, dy = self.x2 - self.x1, self.y2 - self.y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                original_perp_x, original_perp_y = -dy/length, dx/length
                
                # Calculate angle between vectors
                dot_product = original_perp_x * handle_vec_x + original_perp_y * handle_vec_y
                cross_product = original_perp_x * handle_vec_y - original_perp_y * handle_vec_x
                angle_rad = math.atan2(cross_product, dot_product)
                
                # Convert to degrees and update rotation
                self.properties['rotation'] = math.degrees(angle_rad)
        
        elif handle_index == 3:  # Curvature handle (only for curved walls)
            # Use rotated points for curvature calculation
            x1, y1, x2, y2 = self.get_rotated_points()
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                perp_x, perp_y = -dy/length, dx/length
                
                # Calculate signed distance from line to handle
                handle_vec_x, handle_vec_y = x - mid_x, y - mid_y
                dot_product = handle_vec_x * perp_x + handle_vec_y * perp_y
                
                # Normalize curvature value
                self.properties['curvature'] = (dot_product - 20) / (length * 0.3)
        
        self.draw()
    
    def calculate_length(self):
        # Always calculate based on original points (before rotation)
        if self.properties.get('curvature', 0) == 0:
            # Straight line length
            dx, dy = self.x2 - self.x1, self.y2 - self.y1
            pixel_length = math.sqrt(dx*dx + dy*dy)
        else:
            # Approximate curved line length
            control_x = (self.x1 + self.x2) / 2
            control_y = (self.y1 + self.y2) / 2
            
            dx, dy = self.x2 - self.x1, self.y2 - self.y1
            length = math.sqrt(dx*dx + dy*dy)
            perp_x, perp_y = -dy/length, dx/length
            curve_distance = self.properties['curvature'] * length * 0.3
            control_x += perp_x * curve_distance
            control_y += perp_y * curve_distance
            
            # Approximate curve length using numerical integration
            total_length = 0
            prev_x, prev_y = self.x1, self.y1
            for t in np.linspace(0, 1, 50):
                curve_x = (1-t)**2 * self.x1 + 2*(1-t)*t * control_x + t**2 * self.x2
                curve_y = (1-t)**2 * self.y1 + 2*(1-t)*t * control_y + t**2 * self.y2
                
                if t > 0:
                    segment_length = math.sqrt((curve_x - prev_x)**2 + (curve_y - prev_y)**2)
                    total_length += segment_length
                
                prev_x, prev_y = curve_x, curve_y
            
            pixel_length = total_length
        
        # Convert to real world units - now 1 grid unit = 1 foot
        return pixel_length / self.canvas.app.grid_spacing

class Room(DrawingObject):
    def __init__(self, canvas, x1, y1, x2, y2, **kwargs):
        super().__init__(canvas, x1, y1, x2, y2, **kwargs)
        self.properties.setdefault('fill', 'lightblue')
        self.properties.setdefault('outline', 'black')
        self.properties.setdefault('is_house', False)  # New property to mark as house structure
        self.draw()
        
    def draw(self):
        if self.id:
            self.canvas.delete(self.id)
            
        # Use different appearance for house structure
        if self.properties.get('is_house', False):
            fill_color = 'lightgray'
            outline_color = 'darkgray'
            outline_width = 3
        else:
            fill_color = self.properties['fill']
            outline_color = self.properties['outline']
            outline_width = 2
            
        # Draw rectangle
        self.id = self.canvas.create_rectangle(
            self.x1, self.y1, self.x2, self.y2,
            fill=fill_color,
            outline=outline_color,
            width=outline_width,
            tags=('room', 'object')
        )
        
        # Ensure house structure is at the bottom layer
        if self.properties.get('is_house', False):
            self.canvas.tag_lower(self.id)
        
        if self.selected:
            self.canvas.itemconfig(self.id, outline='red', width=3)
            self.draw_handles()
    
    def contains_point(self, x, y, tolerance=None):
        # For rooms, we want to check if the point is inside the rectangle
        # Use tolerance for better selection, especially for thin rooms
        if tolerance is None:
            tolerance = 5
            
        return (self.x1 - tolerance <= x <= self.x2 + tolerance and 
                self.y1 - tolerance <= y <= self.y2 + tolerance)
    
    def move(self, dx, dy):
        self.x1 += dx
        self.y1 += dy
        self.x2 += dx
        self.y2 += dy
        self.draw()
    
    def get_handle_positions(self):
        return [
            (self.x1, self.y1),  # Top-left
            (self.x2, self.y1),  # Top-right
            (self.x1, self.y2),  # Bottom-left
            (self.x2, self.y2),  # Bottom-right
            ((self.x1 + self.x2) / 2, self.y1),  # Top
            ((self.x1 + self.x2) / 2, self.y2),  # Bottom
            (self.x1, (self.y1 + self.y2) / 2),  # Left
            (self.x2, (self.y1 + self.y2) / 2),  # Right
        ]
    
    def update_from_handle(self, handle_index, x, y):
        if handle_index == 0:  # Top-left
            self.x1, self.y1 = x, y
        elif handle_index == 1:  # Top-right
            self.x2, self.y1 = x, y
        elif handle_index == 2:  # Bottom-left
            self.x1, self.y2 = x, y
        elif handle_index == 3:  # Bottom-right
            self.x2, self.y2 = x, y
        elif handle_index == 4:  # Top
            self.y1 = y
        elif handle_index == 5:  # Bottom
            self.y2 = y
        elif handle_index == 6:  # Left
            self.x1 = x
        elif handle_index == 7:  # Right
            self.x2 = x
        
        self.draw()
    
    def calculate_length(self):
        # Return perimeter in feet (1 grid unit = 1 foot)
        width = abs(self.x2 - self.x1) / self.canvas.app.grid_spacing
        height = abs(self.y2 - self.y1) / self.canvas.app.grid_spacing
        return 2 * (width + height)
    
    def get_side_lengths(self):
        """Return the lengths of all four sides in feet"""
        width = abs(self.x2 - self.x1) / self.canvas.app.grid_spacing
        height = abs(self.y2 - self.y1) / self.canvas.app.grid_spacing
        return {
            'top': width,
            'bottom': width,
            'left': height,
            'right': height
        }
    
    def set_as_house(self):
        """Set this room as the house structure"""
        # First, unset any existing house
        for obj in self.canvas.objects:
            if isinstance(obj, Room) and obj.properties.get('is_house', False):
                obj.properties['is_house'] = False
                obj.draw()  # Redraw to update appearance
        
        # Set this room as house
        self.properties['is_house'] = True
        self.draw()
        
        # Move to bottom layer
        self.canvas.tag_lower(self.id)

class TextLabel(DrawingObject):
    def __init__(self, canvas, x, y, **kwargs):
        super().__init__(canvas, x, y, **kwargs)
        self.properties.setdefault('text', 'Label')
        self.properties.setdefault('color', 'black')
        self.properties.setdefault('font_size', 12)
        self.draw()
        
    def draw(self):
        if self.id:
            self.canvas.delete(self.id)
            
        self.id = self.canvas.create_text(
            self.x1, self.y1,
            text=self.properties['text'],
            fill=self.properties['color'],
            font=('Arial', self.properties['font_size']),
            tags=('text', 'object')
        )
        
        if self.selected:
            self.canvas.itemconfig(self.id, fill='red')
            self.draw_handles()
    
    def contains_point(self, x, y, tolerance=None):
        if tolerance is None:
            tolerance = 10
        bbox = self.canvas.bbox(self.id)
        if bbox:
            return (bbox[0] - tolerance <= x <= bbox[2] + tolerance and 
                    bbox[1] - tolerance <= y <= bbox[3] + tolerance)
        return False
    
    def move(self, dx, dy):
        self.x1 += dx
        self.y1 += dy
        self.draw()
    
    def get_handle_positions(self):
        return [(self.x1, self.y1)]
    
    def update_from_handle(self, handle_index, x, y):
        self.x1, self.y1 = x, y
        self.draw()

class DrawingCanvas(tk.Canvas):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.objects = []
        self.selected_object = None
        self.current_tool = 'wall'
        self.drag_start = None
        self.temp_object = None
        self.dragging_handle = None
        self.curving_wall = False
        self.curving_object = None
        
        # Bind events
        self.bind('<Button-1>', self.on_click)
        self.bind('<B1-Motion>', self.on_drag)
        self.bind('<ButtonRelease-1>', self.on_release)
        self.bind('<Motion>', self.on_motion)
        self.bind('<Button-3>', self.on_right_click)
        self.bind('<Configure>', self.on_resize)
        
        self.draw_grid()
        
    def draw_grid(self):
        if not self.app.show_grid:
            return
            
        self.delete('grid')
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width > 1 and height > 1:
            for x in range(0, width, self.app.grid_spacing):
                self.create_line(x, 0, x, height, fill='lightgray', tags='grid')
            for y in range(0, height, self.app.grid_spacing):
                self.create_line(0, y, width, y, fill='lightgray', tags='grid')
    
    def on_resize(self, event):
        self.draw_grid()
    
    def snap_point(self, x, y):
        if self.app.snap_to_grid:
            x = round(x / self.app.grid_spacing) * self.app.grid_spacing
            y = round(y / self.app.grid_spacing) * self.app.grid_spacing
        return x, y
    
    def on_click(self, event):
        x, y = self.snap_point(event.x, event.y)
        self.drag_start = (x, y)
        
        # Check if clicking on a handle first
        if self.selected_object:
            handle_index = self.selected_object.is_handle_hit(x, y)
            if handle_index is not None:
                self.dragging_handle = handle_index
                return
        
        if self.current_tool == 'select':
            # Check if clicking on existing object - use find_closest_with_zorder for proper selection
            clicked_obj = self.find_closest_with_zorder(x, y)
            
            if clicked_obj:
                if self.selected_object:
                    self.selected_object.selected = False
                    self.selected_object.draw()
                self.selected_object = clicked_obj
                self.selected_object.selected = True
                self.selected_object.draw()
                
                # Check if we're starting to curve a wall
                if isinstance(clicked_obj, Wall) and clicked_obj.properties.get('curvature', 0) == 0:
                    # Check if click is near the midpoint for curving
                    x1, y1, x2, y2 = clicked_obj.get_rotated_points()
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    if abs(mid_x - x) <= 8 and abs(mid_y - y) <= 8:
                        self.curving_wall = True
                        self.curving_object = clicked_obj
            else:
                if self.selected_object:
                    self.selected_object.selected = False
                    self.selected_object.draw()
                    self.selected_object = None
        elif self.current_tool == 'erase':
            # Delete clicked object - use find_closest_with_zorder for proper selection
            clicked_obj = self.find_closest_with_zorder(x, y)
            if clicked_obj:
                self.app.add_to_undo_stack('delete', clicked_obj)
                self.objects.remove(clicked_obj)
                if clicked_obj == self.selected_object:
                    self.selected_object = None
                if clicked_obj.id:
                    self.delete(clicked_obj.id)
        elif self.current_tool == 'wall':
            # Start drawing a wall
            if self.temp_object and self.temp_object.id:
                self.delete(self.temp_object.id)
            
            # Check if we have a specific length to create
            if hasattr(self.app, 'pending_wall_length') and self.app.pending_wall_length:
                # Create wall with specific length
                self.create_wall_with_length(x, y)
            else:
                # Normal wall creation
                self.temp_object = Wall(self, x, y, x, y)
    
    def find_closest_with_zorder(self, x, y):
        """Find the topmost object at the given coordinates, considering visual stacking order"""
        # Get all objects at this position
        objects_at_point = []
        for obj in self.objects:
            if obj.contains_point(x, y):
                objects_at_point.append(obj)
        
        if not objects_at_point:
            return None
            
        # If there's only one object, return it
        if len(objects_at_point) == 1:
            return objects_at_point[0]
            
        # For multiple objects, we need to determine the visual stacking order
        # Get the actual canvas stacking order using find_overlapping
        items_at_point = self.find_overlapping(x-1, y-1, x+1, y+1)
        
        # Filter only object items (not handles or grid)
        object_items = []
        for item in items_at_point:
            tags = self.gettags(item)
            if 'object' in tags and 'handle' not in tags:
                object_items.append(item)
        
        # Find the topmost object in our objects list that matches the topmost canvas item
        if object_items:
            # The last item in find_overlapping is the topmost visually
            topmost_item = object_items[-1]
            
            # Find which object corresponds to this canvas item
            for obj in objects_at_point:
                if obj.id == topmost_item:
                    return obj
        
        # Fallback: return the first object in our list if we couldn't determine stacking
        return objects_at_point[0]
    
    def create_wall_with_length(self, start_x, start_y):
        """Create a wall with specific length from the given start point"""
        length_pixels = self.app.pending_wall_length * self.app.grid_spacing
        
        # Create a temporary wall that can be rotated
        self.temp_object = Wall(self, start_x, start_y, start_x + length_pixels, start_y)
        self.app.pending_wall_length = None  # Reset after use
        self.app.update_status("Drag to set wall direction")
    
    def on_drag(self, event):
        if not self.drag_start:
            return
            
        x, y = self.snap_point(event.x, event.y)
        
        if self.curving_wall and self.curving_object:
            # Curving a wall by dragging its midpoint
            x1, y1, x2, y2 = self.curving_object.get_rotated_points()
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            
            dx, dy = x2 - x1, y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            if length > 0:
                perp_x, perp_y = -dy/length, dx/length
                
                # Calculate signed distance from line to mouse
                mouse_vec_x, mouse_vec_y = x - mid_x, y - mid_y
                dot_product = mouse_vec_x * perp_x + mouse_vec_y * perp_y
                
                # Set curvature based on distance
                self.curving_object.properties['curvature'] = dot_product / (length * 0.3)
                self.curving_object.draw()
                
        elif self.dragging_handle is not None and self.selected_object:
            # Dragging a handle
            self.selected_object.update_from_handle(self.dragging_handle, x, y)
            
        elif self.current_tool in ['wall', 'room']:
            if self.temp_object and self.temp_object.id:
                self.delete(self.temp_object.id)
            
            if self.current_tool == 'wall':
                # If we have a specific length, only rotate the wall
                if hasattr(self.app, 'pending_wall_length') and self.app.pending_wall_length:
                    # Calculate angle and set end point
                    dx = x - self.drag_start[0]
                    dy = y - self.drag_start[1]
                    length_pixels = self.app.pending_wall_length * self.app.grid_spacing
                    
                    if dx == 0 and dy == 0:
                        angle = 0
                    else:
                        angle = math.atan2(dy, dx)
                    
                    end_x = self.drag_start[0] + math.cos(angle) * length_pixels
                    end_y = self.drag_start[1] + math.sin(angle) * length_pixels
                    
                    self.temp_object = Wall(self, self.drag_start[0], self.drag_start[1], end_x, end_y)
                else:
                    # Normal wall dragging
                    self.temp_object = Wall(self, self.drag_start[0], self.drag_start[1], x, y)
            elif self.current_tool == 'room':
                self.temp_object = Room(self, self.drag_start[0], self.drag_start[1], x, y)
                
        elif self.current_tool == 'select' and self.selected_object and not self.dragging_handle:
            # Moving entire object
            dx = x - self.drag_start[0]
            dy = y - self.drag_start[1]
            self.selected_object.move(dx, dy)
            self.drag_start = (x, y)
    
    def on_release(self, event):
        if not self.drag_start:
            return
            
        x, y = self.snap_point(event.x, event.y)
        
        if self.curving_wall:
            self.curving_wall = False
            self.curving_object = None
            
        if self.dragging_handle is not None:
            self.dragging_handle = None
            
        elif self.current_tool == 'wall' and self.temp_object:
            # Only add if line has significant length
            if abs(x - self.drag_start[0]) > 5 or abs(y - self.drag_start[1]) > 5:
                wall = Wall(self, self.drag_start[0], self.drag_start[1], 
                           self.temp_object.x2, self.temp_object.y2)
                self.objects.append(wall)
                self.app.add_to_undo_stack('add', wall)
                length = wall.calculate_length()
                logging.info(f"Wall created: {length:.2f} ft")
                
        elif self.current_tool == 'room' and self.temp_object:
            # Only add if room has significant size
            if abs(x - self.drag_start[0]) > 10 and abs(y - self.drag_start[1]) > 10:
                room = Room(self, self.drag_start[0], self.drag_start[1], x, y)
                self.objects.append(room)
                self.app.add_to_undo_stack('add', room)
                width = abs(x - self.drag_start[0]) / self.app.grid_spacing
                height = abs(y - self.drag_start[1]) / self.app.grid_spacing
                logging.info(f"Room created: {width:.2f}×{height:.2f} ft")
                
        elif self.current_tool == 'text':
            text = simpledialog.askstring("Text Label", "Enter text:")
            if text:
                text_obj = TextLabel(self, x, y, text=text)
                self.objects.append(text_obj)
                self.app.add_to_undo_stack('add', text_obj)
                logging.info(f"Text label added: '{text}' at ({x}, {y})")
        
        if self.temp_object and self.temp_object.id:
            self.delete(self.temp_object.id)
            self.temp_object = None
            
        self.drag_start = None
    
    def on_motion(self, event):
        x, y = self.snap_point(event.x, event.y)
        
        # Convert to feet (1 grid unit = 1 foot)
        real_x = x / self.app.grid_spacing
        real_y = y / self.app.grid_spacing
        
        # Only show coordinates, no length
        self.app.update_status(f"Coordinates: ({real_x:.2f}, {real_y:.2f}) ft")
    
    def on_right_click(self, event):
        x, y = event.x, event.y
        
        # Find object under cursor - use find_closest_with_zorder for proper selection
        # Find object under cursor - use find_closest_with_zorder for proper selection
        clicked_obj = self.find_closest_with_zorder(x, y)
        
        context_menu = tk.Menu(self, tearoff=0)
        
        if clicked_obj:
            if not clicked_obj.selected:
                if self.selected_object:
                    self.selected_object.selected = False
                    self.selected_object.draw()
                self.selected_object = clicked_obj
                self.selected_object.selected = True
                self.selected_object.draw()
            
            if isinstance(clicked_obj, Wall):
                context_menu.add_command(label="Make Straight", 
                                       command=lambda: self.make_wall_straight(clicked_obj))
                context_menu.add_command(label="Adjust Curvature...", 
                                       command=lambda: self.adjust_curvature(clicked_obj))
                context_menu.add_command(label="Rotate Wall...", 
                                       command=lambda: self.rotate_wall(clicked_obj))
                context_menu.add_command(label="Set Length...", 
                                       command=lambda: self.set_wall_length(clicked_obj))
                context_menu.add_separator()
            elif isinstance(clicked_obj, Room):
                context_menu.add_command(label="Set as House Structure", 
                                       command=lambda: self.set_room_as_house(clicked_obj))
                context_menu.add_command(label="Change Color", 
                                       command=lambda: self.change_room_color(clicked_obj))
                context_menu.add_command(label="Set Width...", 
                                       command=lambda: self.set_room_width(clicked_obj))
                context_menu.add_command(label="Set Height...", 
                                       command=lambda: self.set_room_height(clicked_obj))
                context_menu.add_command(label="Set Side Length...", 
                                       command=lambda: self.set_room_side_length(clicked_obj))
                context_menu.add_separator()
            elif isinstance(clicked_obj, TextLabel):
                context_menu.add_command(label="Edit Text", 
                                       command=lambda: self.edit_text(clicked_obj))
                context_menu.add_command(label="Change Font Size", 
                                       command=lambda: self.change_font_size(clicked_obj))
            
            context_menu.add_command(label="Delete", 
                                   command=lambda: self.delete_object(clicked_obj))
            context_menu.add_separator()
        
        context_menu.add_command(label="Create Wall with Specific Length", 
                               command=self.create_wall_with_length_dialog)
        context_menu.add_command(label="Properties", 
                               command=self.show_properties)
        
        context_menu.post(event.x_root, event.y_root)
    
    def set_room_as_house(self, room):
        """Set the selected room as the house structure"""
        room.set_as_house()
        self.app.update_status("Room set as house structure")
        logging.info("Room set as house structure")
    
    def create_wall_with_length_dialog(self):
        length = simpledialog.askfloat("Wall Length", "Enter wall length in feet:")
        if length is not None and length > 0:
            self.app.pending_wall_length = length
            self.app.set_tool('wall')
            self.app.update_status(f"Click to place starting point for {length:.2f} ft wall")
    
    def make_wall_straight(self, wall):
        self.app.add_to_undo_stack('modify', wall, {'curvature': wall.properties.get('curvature', 0)})
        wall.properties['curvature'] = 0
        wall.draw()
    
    def adjust_curvature(self, wall):
        def update_curvature(val):
            wall.properties['curvature'] = float(val)
            wall.draw()
        
        curvature_window = tk.Toplevel(self)
        curvature_window.title("Adjust Wall Curvature")
        curvature_window.geometry("300x100")
        
        curvature = wall.properties.get('curvature', 0)
        scale = Scale(curvature_window, from_=-2, to=2, resolution=0.1, 
                     orient=tk.HORIZONTAL, label="Curvature",
                     command=update_curvature)
        scale.set(curvature)
        scale.pack(fill=tk.X, padx=20, pady=20)
    
    def rotate_wall(self, wall):
        angle = simpledialog.askfloat("Rotate Wall", "Enter rotation angle (degrees):",
                                    initialvalue=wall.properties.get('rotation', 0))
        if angle is not None:
            self.app.add_to_undo_stack('modify', wall, {'rotation': wall.properties.get('rotation', 0)})
            wall.properties['rotation'] = angle
            wall.draw()
    
    def set_wall_length(self, wall):
        current_length = wall.calculate_length()
        new_length = simpledialog.askfloat("Set Wall Length", 
                                         f"Current length: {current_length:.2f} ft\nEnter new length:",
                                         initialvalue=current_length)
        if new_length is not None and new_length > 0:
            self.app.add_to_undo_stack('modify', wall, {'x2': wall.x2, 'y2': wall.y2})
            
            # Calculate direction vector
            dx = wall.x2 - wall.x1
            dy = wall.y2 - wall.y1
            current_pixel_length = math.sqrt(dx*dx + dy*dy)
            
            if current_pixel_length > 0:
                # Calculate scale factor
                scale = (new_length * self.app.grid_spacing) / current_pixel_length
                
                # Update end point
                wall.x2 = wall.x1 + dx * scale
                wall.y2 = wall.y1 + dy * scale
                wall.draw()
    
    def set_room_width(self, room):
        current_width = abs(room.x2 - room.x1) / self.app.grid_spacing
        new_width = simpledialog.askfloat("Set Room Width", 
                                        f"Current width: {current_width:.2f} ft\nEnter new width:",
                                        initialvalue=current_width)
        if new_width is not None and new_width > 0:
            self.app.add_to_undo_stack('modify', room, {'x2': room.x2})
            
            # Calculate center to maintain position
            center_x = (room.x1 + room.x2) / 2
            new_pixel_width = new_width * self.app.grid_spacing
            
            # Update x coordinates while maintaining center
            room.x1 = center_x - new_pixel_width / 2
            room.x2 = center_x + new_pixel_width / 2
            room.draw()
    
    def set_room_height(self, room):
        current_height = abs(room.y2 - room.y1) / self.app.grid_spacing
        new_height = simpledialog.askfloat("Set Room Height", 
                                         f"Current height: {current_height:.2f} ft\nEnter new height:",
                                         initialvalue=current_height)
        if new_height is not None and new_height > 0:
            self.app.add_to_undo_stack('modify', room, {'y2': room.y2})
            
            # Calculate center to maintain position
            center_y = (room.y1 + room.y2) / 2
            new_pixel_height = new_height * self.app.grid_spacing
            
            # Update y coordinates while maintaining center
            room.y1 = center_y - new_pixel_height / 2
            room.y2 = center_y + new_pixel_height / 2
            room.draw()
    
    def set_room_side_length(self, room):
        # Get current side lengths
        side_lengths = room.get_side_lengths()
        
        # Create a dialog to select which side to change
        side_window = tk.Toplevel(self)
        side_window.title("Set Room Side Length")
        side_window.geometry("300x200")
        
        ttk.Label(side_window, text="Select side to modify:").pack(pady=10)
        
        side_var = tk.StringVar(value="top")
        
        sides_frame = ttk.Frame(side_window)
        sides_frame.pack(pady=10)
        
        ttk.Radiobutton(side_window, text=f"Top ({side_lengths['top']:.2f} ft)", 
                       variable=side_var, value="top").grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(side_window, text=f"Bottom ({side_lengths['bottom']:.2f} ft)", 
                       variable=side_var, value="bottom").grid(row=1, column=0, sticky='w')
        ttk.Radiobutton(side_window, text=f"Left ({side_lengths['left']:.2f} ft)", 
                       variable=side_var, value="left").grid(row=2, column=0, sticky='w')
        ttk.Radiobutton(side_window, text=f"Right ({side_lengths['right']:.2f} ft)", 
                       variable=side_var, value="right").grid(row=3, column=0, sticky='w')
        
        ttk.Label(side_window, text="New length (ft):").pack(pady=5)
        length_var = tk.StringVar()
        length_entry = ttk.Entry(side_window, textvariable=length_var)
        length_entry.pack(pady=5)
        
        def apply_side_length():
            try:
                new_length = float(length_var.get())
                if new_length <= 0:
                    messagebox.showerror("Error", "Length must be positive")
                    return
                
                side = side_var.get()
                self.app.add_to_undo_stack('modify', room, {'x1': room.x1, 'x2': room.x2, 'y1': room.y1, 'y2': room.y2})
                
                if side == "top" or side == "bottom":
                    # For top/bottom, adjust width
                    center_x = (room.x1 + room.x2) / 2
                    new_pixel_width = new_length * self.app.grid_spacing
                    room.x1 = center_x - new_pixel_width / 2
                    room.x2 = center_x + new_pixel_width / 2
                else:  # left or right
                    # For left/right, adjust height
                    center_y = (room.y1 + room.y2) / 2
                    new_pixel_height = new_length * self.app.grid_spacing
                    room.y1 = center_y - new_pixel_height / 2
                    room.y2 = center_y + new_pixel_height / 2
                
                room.draw()
                side_window.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")
        
        ttk.Button(side_window, text="Apply", command=apply_side_length).pack(pady=10)
    
    def change_room_color(self, room):
        color = simpledialog.askstring("Room Color", "Enter color name or hex code:",
                                     initialvalue=room.properties['fill'])
        if color:
            self.app.add_to_undo_stack('modify', room, {'fill': room.properties['fill']})
            room.properties['fill'] = color
            room.draw()
    
    def edit_text(self, text_obj):
        new_text = simpledialog.askstring("Edit Text", "Enter new text:",
                                        initialvalue=text_obj.properties['text'])
        if new_text:
            self.app.add_to_undo_stack('modify', text_obj, {'text': text_obj.properties['text']})
            text_obj.properties['text'] = new_text
            text_obj.draw()
    
    def change_font_size(self, text_obj):
        new_size = simpledialog.askinteger("Font Size", "Enter font size:",
                                         initialvalue=text_obj.properties.get('font_size', 12))
        if new_size and new_size > 0:
            self.app.add_to_undo_stack('modify', text_obj, {'font_size': text_obj.properties.get('font_size', 12)})
            text_obj.properties['font_size'] = new_size
            text_obj.draw()
    
    def delete_object(self, obj):
        self.app.add_to_undo_stack('delete', obj)
        if obj.id:
            self.delete(obj.id)
        if obj in self.objects:
            self.objects.remove(obj)
        if obj == self.selected_object:
            self.selected_object = None
    
    def show_properties(self):
        if self.selected_object:
            props = self.selected_object.to_dict()
            length = self.selected_object.calculate_length()
            messagebox.showinfo("Object Properties", 
                              f"Type: {props['type']}\n"
                              f"Position: ({props['x1']}, {props['y1']})\n"
                              f"Length: {length:.2f} ft\n"
                              f"Properties: {props['properties']}")
    
    def clear_canvas(self):
        self.delete('all')
        self.objects.clear()
        self.selected_object = None
        self.draw_grid()

class HouseMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("2D House Map Drawing Application")
        self.root.geometry("1400x900")
        
        # Initialize variables - 1 grid unit = 1 foot
        self.grid_spacing = 20  # pixels per grid unit (1 foot)
        self.unit_system = "feet"
        self.show_grid = True
        self.snap_to_grid = True
        self.undo_stack = []
        self.redo_stack = []
        self.pending_wall_length = None
        
        self.setup_ui()
        self.setup_bindings()
        
        logging.info("House Map Application started")
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Toolbar
        self.setup_toolbar(main_frame)
        
        # Canvas frame
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create canvas with scrollbars
        self.setup_canvas_with_scrollbars(canvas_frame)
        
        # Status bar
        self.setup_statusbar(main_frame)
    
    def setup_canvas_with_scrollbars(self, parent):
        # Create frame for canvas and scrollbars
        canvas_container = ttk.Frame(parent)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas
        self.canvas = DrawingCanvas(canvas_container, self, bg='white', relief=tk.SUNKEN, borderwidth=2,
                                   xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set,
                                   scrollregion=(0, 0, 2000, 2000))  # Large scrollable area
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbars
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)
    
    def setup_toolbar(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=2)
        
        # Tools
        ttk.Button(toolbar, text="Wall", command=lambda: self.set_tool('wall')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Room", command=lambda: self.set_tool('room')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Text", command=lambda: self.set_tool('text')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Select", command=lambda: self.set_tool('select')).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Erase", command=lambda: self.set_tool('erase')).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # File operations
        ttk.Button(toolbar, text="New", command=self.new_map).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Save", command=self.save_map).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Load", command=self.load_map).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Export PS", command=self.export_ps).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # Wall length input
        ttk.Label(toolbar, text="Wall Length (ft):").pack(side=tk.LEFT, padx=2)
        self.wall_length_var = tk.StringVar()
        wall_length_entry = ttk.Entry(toolbar, textvariable=self.wall_length_var, width=8)
        wall_length_entry.pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Create Wall", command=self.create_wall_with_length).pack(side=tk.LEFT, padx=2)
        
        # Grid controls
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(toolbar, text="Toggle Grid", command=self.toggle_grid).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Snap Toggle", command=self.toggle_snap).pack(side=tk.LEFT, padx=2)
        
        # Undo/Redo
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        ttk.Button(toolbar, text="Undo", command=self.undo).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Redo", command=self.redo).pack(side=tk.LEFT, padx=2)
    
    def setup_statusbar(self, parent):
        statusbar = ttk.Frame(parent)
        statusbar.pack(fill=tk.X, pady=2)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(statusbar, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X, padx=2, pady=2)
    
    def setup_bindings(self):
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-y>', lambda e: self.redo())
        self.root.bind('<Control-s>', lambda e: self.save_map())
        self.root.bind('<Control-o>', lambda e: self.load_map())
        self.root.bind('<Control-n>', lambda e: self.new_map())
        self.root.bind('<Delete>', lambda e: self.delete_selected())
        self.root.bind('<Control-plus>', lambda e: self.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.zoom_out())
    
    def set_tool(self, tool):
        self.canvas.current_tool = tool
        self.update_status(f"Tool: {tool.replace('_', ' ').title()}")
        logging.info(f"Tool changed to: {tool}")
    
    def update_status(self, message):
        self.status_var.set(message)
    
    def create_wall_with_length(self):
        try:
            length = float(self.wall_length_var.get())
            if length > 0:
                self.pending_wall_length = length
                self.set_tool('wall')
                self.update_status(f"Click to place starting point for {length:.2f} ft wall")
                logging.info(f"Wall length set to: {length} ft")
            else:
                messagebox.showerror("Error", "Wall length must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for wall length")
    
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        if self.show_grid:
            self.canvas.draw_grid()
            logging.info("Grid shown")
        else:
            self.canvas.delete('grid')
            logging.info("Grid hidden")
    
    def toggle_snap(self):
        self.snap_to_grid = not self.snap_to_grid
        status = "enabled" if self.snap_to_grid else "disabled"
        self.update_status(f"Snap to grid {status}")
        logging.info(f"Snap to grid {status}")
    
    def zoom_in(self):
        # Zoom in by increasing grid spacing
        if self.grid_spacing < 50:
            self.grid_spacing += 5
            self.canvas.draw_grid()
            logging.info(f"Zoom in - Grid size: {self.grid_spacing}")
    
    def zoom_out(self):
        # Zoom out by decreasing grid spacing
        if self.grid_spacing > 10:
            self.grid_spacing -= 5
            self.canvas.draw_grid()
            logging.info(f"Zoom out - Grid size: {self.grid_spacing}")
    
    def new_map(self):
        if self.canvas.objects and not messagebox.askyesno("New Map", "Are you sure you want to create a new map? Unsaved changes will be lost."):
            return
        self.canvas.clear_canvas()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.update_status("New map created")
        logging.info("New map created")
    
    def save_map(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                data = {
                    'grid_spacing': self.grid_spacing,
                    'unit_system': self.unit_system,
                    'objects': [obj.to_dict() for obj in self.canvas.objects],
                    'metadata': {
                        'created': datetime.now().isoformat(),
                        'version': '2.0'
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                self.update_status(f"Map saved: {filename}")
                logging.info(f"Map saved to: {filename}")
                
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save map: {str(e)}")
                logging.error(f"Save error: {str(e)}")
    
    def load_map(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                self.save_state()  # Save current state for undo
                self.canvas.clear_canvas()
                self.grid_spacing = data.get('grid_spacing', 20)
                self.unit_system = data.get('unit_system', 'feet')
                
                # Recreate objects
                object_map = {
                    'Wall': Wall,
                    'Room': Room,
                    'TextLabel': TextLabel
                }
                
                for obj_data in data.get('objects', []):
                    obj_type = obj_data['type']
                    if obj_type in object_map:
                        obj = object_map[obj_type].from_dict(self.canvas, obj_data)
                        self.canvas.objects.append(obj)
                
                self.canvas.draw_grid()
                self.update_status(f"Map loaded: {filename}")
                logging.info(f"Map loaded from: {filename}")
                
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load map: {str(e)}")
                logging.error(f"Load error: {str(e)}")
    
    def export_ps(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".ps",
            filetypes=[("PostScript", "*.ps"), ("All files", "*.*")]
        )
        if filename:
            try:
                self.canvas.postscript(file=filename, colormode='color')
                self.update_status(f"Exported to: {filename}")
                logging.info(f"Map exported to: {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
                logging.error(f"Export error: {str(e)}")
    
    def save_state(self):
        """Save current state to undo stack"""
        state = {
            'objects': [obj.to_dict() for obj in self.canvas.objects],
            'grid_spacing': self.grid_spacing,
            'unit_system': self.unit_system
        }
        self.undo_stack.append(state)
        # Clear redo stack when new action is performed
        self.redo_stack.clear()
    
    def add_to_undo_stack(self, action_type, obj, old_properties=None):
        """Add an action to the undo stack"""
        action = {
            'type': action_type,
            'object': obj.to_dict() if obj else None,
            'old_properties': old_properties
        }
        self.undo_stack.append(action)
        self.redo_stack.clear()
    
    def undo(self):
        if not self.undo_stack:
            return
            
        action = self.undo_stack.pop()
        
        if 'objects' in action:  # Full state save
            # Save current state to redo stack
            current_state = {
                'objects': [obj.to_dict() for obj in self.canvas.objects],
                'grid_spacing': self.grid_spacing,
                'unit_system': self.unit_system
            }
            self.redo_stack.append(current_state)
            
            # Restore previous state
            self.canvas.clear_canvas()
            self.grid_spacing = action.get('grid_spacing', self.grid_spacing)
            self.unit_system = action.get('unit_system', self.unit_system)
            
            # Recreate objects
            object_map = {
                'Wall': Wall,
                'Room': Room,
                'TextLabel': TextLabel
            }
            
            for obj_data in action.get('objects', []):
                obj_type = obj_data['type']
                if obj_type in object_map:
                    obj = object_map[obj_type].from_dict(self.canvas, obj_data)
                    self.canvas.objects.append(obj)
            
            self.canvas.draw_grid()
        else:  # Single action
            # Save current state to redo stack
            if self.canvas.selected_object:
                current_state = {
                    'type': 'modify',
                    'object': self.canvas.selected_object.to_dict(),
                    'old_properties': self.canvas.selected_object.properties.copy()
                }
            else:
                current_state = action.copy()
            self.redo_stack.append(current_state)
            
            # Perform undo based on action type
            if action['type'] == 'add':
                # Remove the object that was added
                obj_to_remove = None
                for obj in self.canvas.objects:
                    if (obj.x1 == action['object']['x1'] and 
                        obj.y1 == action['object']['y1'] and
                        obj.x2 == action['object']['x2'] and
                        obj.y2 == action['object']['y2']):
                        obj_to_remove = obj
                        break
                
                if obj_to_remove:
                    self.canvas.objects.remove(obj_to_remove)
                    if obj_to_remove.id:
                        self.canvas.delete(obj_to_remove.id)
                    if obj_to_remove == self.canvas.selected_object:
                        self.canvas.selected_object = None
            
            elif action['type'] == 'delete':
                # Restore the deleted object
                obj_data = action['object']
                object_map = {
                    'Wall': Wall,
                    'Room': Room,
                    'TextLabel': TextLabel
                }
                obj_type = obj_data['type']
                if obj_type in object_map:
                    obj = object_map[obj_type].from_dict(self.canvas, obj_data)
                    self.canvas.objects.append(obj)
            
            elif action['type'] == 'modify':
                # Restore old properties
                if self.canvas.selected_object and action['old_properties']:
                    for key, value in action['old_properties'].items():
                        self.canvas.selected_object.properties[key] = value
                    self.canvas.selected_object.draw()
        
        self.update_status("Undo performed")
        logging.info("Undo action")
    
    def redo(self):
        if not self.redo_stack:
            return
            
        action = self.redo_stack.pop()
        
        if 'objects' in action:  # Full state restore
            # Save current state to undo stack
            current_state = {
                'objects': [obj.to_dict() for obj in self.canvas.objects],
                'grid_spacing': self.grid_spacing,
                'unit_system': self.unit_system
            }
            self.undo_stack.append(current_state)
            
            # Restore state from redo stack
            self.canvas.clear_canvas()
            self.grid_spacing = action.get('grid_spacing', self.grid_spacing)
            self.unit_system = action.get('unit_system', self.unit_system)
            
            # Recreate objects
            object_map = {
                'Wall': Wall,
                'Room': Room,
                'TextLabel': TextLabel
            }
            
            for obj_data in action.get('objects', []):
                obj_type = obj_data['type']
                if obj_type in object_map:
                    obj = object_map[obj_type].from_dict(self.canvas, obj_data)
                    self.canvas.objects.append(obj)
            
            self.canvas.draw_grid()
        else:  # Single action redo
            # For now, just push back to undo stack
            self.undo_stack.append(action)
        
        self.update_status("Redo performed")
        logging.info("Redo action")
    
    def delete_selected(self):
        if self.canvas.selected_object:
            self.canvas.delete_object(self.canvas.selected_object)
            self.update_status("Selected object deleted")
            logging.info("Object deleted")

def main():
    try:
        root = tk.Tk()
        app = HouseMapApp(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Application crashed: {str(e)}")
        raise

if __name__ == "__main__":
    main()