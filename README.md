# 2D House Map Drawer

A lightweight, intuitive 2D map drawing application built with Python and Tkinter. This tool is designed to simplify the complex process of drawing house structures and floor plans by providing a user-friendly grid-based canvas.

## Features

* **Interactive Drawing Tools:**
  * **Walls:** Draw straight or seamlessly curved walls. Rotate them or specify exact lengths in feet.
  * **Rooms:** Drag and drop rectangular rooms. Designate specific rooms as the main "House Structure" for visual layering.
  * **Text Labels:** Annotate your floor plans easily.
* **Precision Controls:** * 1 grid unit = 1 foot scaling system.
  * Toggleable grid visibility and grid-snapping for exact placements.
  * Dynamic adjustment handles for resizing, rotating, and curving objects after placement.
* **Context Menus:** Right-click on any object to access specific properties (e.g., change room colors, set exact side lengths, adjust wall curvature, or edit text).
* **State Management:** Full Undo (`Ctrl+Z`) and Redo (`Ctrl+Y`) stack.
* **File Operations:** Save and load your projects as JSON files, or export your final map as a PostScript (`.ps`) file for printing.
* **Logging:** Automatically logs application events and errors to `house_map_app.log`.

---

## Requirements

This application requires Python 3.x and the following libraries:

* `tkinter` (Usually comes pre-installed with standard Python distributions)
* `numpy`

You can install the required external dependencies via pip:
```bash
pip install numpy

```

---

## Installation & Usage

1. Clone the repository or download the source code.
2. Navigate to the directory containing the file.
3. Run the application using Python:

```bash
python map_drawer.py

```

---

## Controls & Shortcuts

### **Mouse Controls**

* **Left Click:** Select objects or drag adjustment handles.
* **Left Click + Drag:** Draw walls/rooms, or move selected objects.
* **Right Click:** Open the context menu for the selected object (edit properties, change sizes, delete, etc.).

### **Keyboard Shortcuts**

* **`Ctrl + Z`**: Undo the last action
* **`Ctrl + Y`**: Redo the last undone action
* **`Ctrl + S`**: Save the current map
* **`Ctrl + O`**: Load an existing map
* **`Ctrl + N`**: Create a new map (clears canvas)
* **`Delete`**: Delete the currently selected object
* **`Ctrl + +`**: Zoom in (increases grid spacing)
* **`Ctrl + -`**: Zoom out (decreases grid spacing)

---

## How to Use

1. **Drawing a Wall:** Select the "Wall" tool from the top toolbar. Click and drag on the canvas. To curve a wall, switch to the "Select" tool, right-click the wall, and choose "Adjust Curvature," or drag its midpoint handle.
2. **Drawing a Room:** Select the "Room" tool. Click and drag to define the rectangular space. Right-click the room to change its dimensions, alter its color, or designate it as the base House Structure.
3. **Exact Measurements:** If you need a wall of a specific length, type the length (in feet) into the "Wall Length" box in the toolbar and click "Create Wall". Click anywhere on the canvas to place the starting point, then drag to define its direction.
