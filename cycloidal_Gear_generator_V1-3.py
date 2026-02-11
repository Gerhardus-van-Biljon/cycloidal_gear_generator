'''
Docstring for cycloidal_Gear_generator_V1-2
Author: Gerhardus van Biljon
This is a cycloidal gearbox generator that allows you to design and visualize cycloidal gearboxes with customizable parameters. The application features an interactive OpenGL viewer where you can see the geometry of the cycloidal disk, pins, and camshaft in real-time as you adjust the parameters using sliders.
added in 1.2:
normalize to external pins button that calculates optimal ring and disk diameters based on the number of external pins and their diameter, using the formula:
fixed veraible names for easyer reading and understanding of the code, 
changed sliders to be in a better order and better names....
Fixed in 1.3:
- Cycloid disk now generates as one continuous loop instead of separate segments for easier export
- Added tolerance slider (0.01-2.0mm) to set clearances between all mating parts:
  * Makes cycloid disk slightly smaller (adds tolerance to pin offset)
  * Makes holes in disk larger (output pin holes and camshaft hole)
  * Ensures proper clearances 
'''



import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl

# =================== MATH FUNCTIONS ===================

def pin_ring(num_pins, ring_diameter, pin_diameter):
    t = np.linspace(0, 2*np.pi, 200)
    pins = []
    for i in range(num_pins):
        x = pin_diameter/2*np.sin(t) + ring_diameter/2*np.cos(2*np.pi*i/num_pins)
        y = pin_diameter/2*np.cos(t) + ring_diameter/2*np.sin(2*np.pi*i/num_pins)
        pins.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return pins


def inner_pins(num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi):
    """output_pin_diameter and output_disk_diameter are diameters, not radii"""
    t = np.linspace(0, 2*np.pi, 200)
    num_lobes = num_external_pins - 1  # Number of lobes = num_external_pins - 1
    pins = []
    output_pin_radius = output_pin_diameter / 2  # Convert to radius
    output_disk_radius = output_disk_diameter / 2  # Convert to radius
    
    for i in range(num_output_pins):
        x = (output_pin_radius*np.sin(t) + output_disk_radius*np.cos(2*np.pi*i/num_output_pins))*np.cos(-phi/num_lobes) - (output_pin_radius*np.cos(t) + output_disk_radius*np.sin(2*np.pi*i/num_output_pins))*np.sin(-phi/num_lobes)
        y = (output_pin_radius*np.sin(t) + output_disk_radius*np.cos(2*np.pi*i/num_output_pins))*np.sin(-phi/num_lobes) + (output_pin_radius*np.cos(t) + output_disk_radius*np.sin(2*np.pi*i/num_output_pins))*np.cos(-phi/num_lobes)
        pins.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return pins


def inner_circles(eccentricity, num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi, tolerance=0):
    """output_pin_diameter and output_disk_diameter are diameters, not radii"""
    t = np.linspace(0, 2*np.pi, 200)
    num_lobes = num_external_pins - 1  # Number of lobes = num_external_pins - 1
    circles = []
    output_pin_radius = output_pin_diameter / 2  # Convert to radius
    output_disk_radius = output_disk_diameter / 2  # Convert to radius
    
    for i in range(num_output_pins):
        # Circle radius needs to be larger than pin by eccentricity amount plus tolerance
        # hole_radius = output_pin_radius + eccentricity + tolerance (for clearance)
        hole_radius = output_pin_radius + eccentricity + tolerance
        x = (hole_radius*np.cos(t) + output_disk_radius*np.cos(2*np.pi*i/num_output_pins))*np.cos(-phi/num_lobes) - (hole_radius*np.sin(t) + output_disk_radius*np.sin(2*np.pi*i/num_output_pins))*np.sin(-phi/num_lobes) + eccentricity*np.cos(phi)
        y = (hole_radius*np.cos(t) + output_disk_radius*np.cos(2*np.pi*i/num_output_pins))*np.sin(-phi/num_lobes) + (hole_radius*np.sin(t) + output_disk_radius*np.sin(2*np.pi*i/num_output_pins))*np.cos(-phi/num_lobes) + eccentricity*np.sin(phi)
        circles.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return circles


def cycloid_disk(eccentricity, num_external_pins, ring_diameter, pin_diameter, phi, tolerance=0):
    ring_radius = ring_diameter/2  # Convert to radius
    pin_radius = pin_diameter/2  # Convert to radius
    num_lobes = num_external_pins - 1  # Number of lobes = num_external_pins - 1

    # Corrected pitch circle calculations for num_lobes lobes
    # The cycloid disk should roll inside the ring
    rolling_circle_radius = (num_lobes/(num_lobes+1)) * ring_radius  # Rolling circle radius
    stationary_circle_radius = ring_radius / (num_lobes+1)         # Stationary circle radius (pin circle)

    # Generate one continuous curve for the entire disk
    # Use enough points for smooth curve: ~1500 points per lobe
    points_per_lobe = 1500
    total_points = points_per_lobe * num_lobes
    t_full = np.linspace(0, 2*np.pi, total_points, endpoint=True)
    
    # Generate the cycloid curve
    xa = (rolling_circle_radius + stationary_circle_radius)*np.cos(t_full) - eccentricity*np.cos((rolling_circle_radius + stationary_circle_radius)/stationary_circle_radius*t_full)
    ya = (rolling_circle_radius + stationary_circle_radius)*np.sin(t_full) - eccentricity*np.sin((rolling_circle_radius + stationary_circle_radius)/stationary_circle_radius*t_full)

    dxa = (rolling_circle_radius + stationary_circle_radius)*(-np.sin(t_full) + (eccentricity/stationary_circle_radius)*np.sin((rolling_circle_radius + stationary_circle_radius)/stationary_circle_radius*t_full))
    dya = (rolling_circle_radius + stationary_circle_radius)*( np.cos(t_full) - (eccentricity/stationary_circle_radius)*np.cos((rolling_circle_radius + stationary_circle_radius)/stationary_circle_radius*t_full))

    # Offset by pin radius plus tolerance to create the outer profile
    # Add tolerance to make disk slightly smaller (clearance)
    effective_pin_radius = pin_radius + tolerance
    xd = xa + effective_pin_radius/np.sqrt(dxa**2 + dya**2)*(-dya)
    yd = ya + effective_pin_radius/np.sqrt(dxa**2 + dya**2)*( dxa)

    # Apply rotation and translation
    x = xd*np.cos(-phi/num_lobes) - yd*np.sin(-phi/num_lobes) + eccentricity*np.cos(phi)
    y = xd*np.sin(-phi/num_lobes) + yd*np.cos(-phi/num_lobes) + eccentricity*np.sin(phi)

    # Return as single continuous curve
    return [np.vstack([x, y, np.zeros_like(x)]).T]


def camshaft(camshaft_diameter, phi, tolerance=0):
    """Generate camshaft hole in the cycloid disk - this is the fixed outer boundary"""
    t = np.linspace(0, 2*np.pi, 200)
    # Add tolerance to make hole larger (clearance)
    hole_diameter = camshaft_diameter + 2 * tolerance
    x = hole_diameter/2 * np.cos(t)
    y = hole_diameter/2 * np.sin(t)
    return np.vstack([x, y, np.zeros_like(x)]).T


def eccentric_camshaft(eccentricity, camshaft_diameter, phi):
    """Generate eccentric shaft that orbits inside the camshaft hole"""
    t = np.linspace(0, 2*np.pi, 200)
    # The eccentric shaft diameter should be smaller than camshaft_diameter by 2*eccentricity
    # so it can orbit by distance eccentricity inside the hole
    shaft_radius = (camshaft_diameter - 2*eccentricity) / 2
    x = shaft_radius * np.cos(t) + eccentricity * np.cos(phi)
    y = shaft_radius * np.sin(t) + eccentricity * np.sin(phi)
    return np.vstack([x, y, np.zeros_like(x)]).T


# =================== OPENGL VIEWER ===================

class GearboxViewer(gl.GLViewWidget):
    def __init__(self):
        super().__init__()
        self.setCameraPosition(distance=150)

        # Grid
        grid = gl.GLGridItem()
        grid.scale(10, 10, 1)
        self.addItem(grid)

        # Initialize items lists
        self.outer_pin_items = []
        self.inner_pin_items = []
        self.inner_circle_items = []
        self.cycloid_items = []
        self.camshaft_item = None
        self.eccentric_camshaft_item = None

    def rebuild_items(self, num_external_pins, num_output_pins):
        """Rebuild OpenGL items when num_external_pins or num_output_pins changes"""
        # Remove old items
        for item in self.outer_pin_items + self.inner_pin_items + self.inner_circle_items + self.cycloid_items:
            self.removeItem(item)

        # Create new items with lighter colors
        self.outer_pin_items = [gl.GLLinePlotItem(color=(0.4, 0.4, 0.4, 1), width=2) for _ in range(num_external_pins)]
        self.inner_pin_items = [gl.GLLinePlotItem(color=(0.3, 0.9, 0.3, 1), width=2) for _ in range(num_output_pins)]
        self.inner_circle_items = [gl.GLLinePlotItem(color=(0.9, 0.5, 0.9, 1), width=2) for _ in range(num_output_pins)]
        # Now only need 1 item for the continuous cycloid disk
        self.cycloid_items = [gl.GLLinePlotItem(color=(1, 0.3, 0.3, 1), width=2.5)]

        # Add new items
        for item in self.outer_pin_items + self.inner_pin_items + self.inner_circle_items + self.cycloid_items:
            self.addItem(item)
        
        # Add camshaft items if not already added
        if self.camshaft_item is None:
            self.camshaft_item = gl.GLLinePlotItem(color=(0.2, 0.5, 0.9, 1), width=3)
            self.addItem(self.camshaft_item)
        
        if self.eccentric_camshaft_item is None:
            self.eccentric_camshaft_item = gl.GLLinePlotItem(color=(0.9, 0.7, 0.2, 1), width=2)
            self.addItem(self.eccentric_camshaft_item)

    def update_geometry(self, eccentricity, num_external_pins, num_output_pins, ring_diameter, pin_diameter, output_disk_diameter, output_pin_diameter, camshaft_diameter, tolerance, phi):
        """Update all geometry"""
        # Outer pins
        pins = pin_ring(num_external_pins, ring_diameter, pin_diameter)
        for i, item in enumerate(self.outer_pin_items):
            if i < len(pins):
                item.setData(pos=pins[i])

        # Inner pins
        ip = inner_pins(num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi)
        for i, item in enumerate(self.inner_pin_items):
            if i < len(ip):
                item.setData(pos=ip[i])

        # Inner circles (holes in cycloid disk) - with tolerance
        ic = inner_circles(eccentricity, num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi, tolerance)
        for i, item in enumerate(self.inner_circle_items):
            if i < len(ic):
                item.setData(pos=ic[i])

        # Cycloid disk - with tolerance
        cd = cycloid_disk(eccentricity, num_external_pins, ring_diameter, pin_diameter, phi, tolerance)
        if len(cd) > 0 and len(self.cycloid_items) > 0:
            self.cycloid_items[0].setData(pos=cd[0])
        
        # Camshaft hole - with tolerance
        cam = camshaft(camshaft_diameter, phi, tolerance)
        self.camshaft_item.setData(pos=cam)
        
        # Eccentric camshaft (rotating with cycloid disk)
        ecc_cam = eccentric_camshaft(eccentricity, camshaft_diameter, phi)
        self.eccentric_camshaft_item.setData(pos=ecc_cam)


# =================== SLIDER PANEL ===================

class SliderPanel(QtWidgets.QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        # Parameters - using descriptive names
        self.params = {
            'eccentricity': 1.2,
            'num_external_pins': 12,
            'num_output_pins': 5,
            'ring_diameter': 41.0,
            'pin_diameter': 5.0,
            'output_disk_diameter': 21.0,
            'output_pin_diameter': 1.5,
            'camshaft_diameter': 8.0,
            'animation_speed': 200,
            'tolerance': 0.1
        }
        self.phi = 0
        self.paused = False

        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("Cycloidal Gearbox Designer")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Add sliders with descriptive parameter names
        self.add_slider(layout, "Animation Speed", 'animation_speed', 1, 2000, 1, is_int=True)
        self.add_slider(layout, "Eccentricity (mm)", 'eccentricity', 0.5, 10.0, 0.1)
        self.add_slider(layout, "External Pins", 'num_external_pins', 3, 100, 1, is_int=True)
        self.add_slider(layout, "External Pin Diameter (mm)", 'pin_diameter', 2, 25, 0.5)
        self.add_slider(layout, "Ring Diameter (mm)", 'ring_diameter', 20, 250, 1)
        self.add_slider(layout, "Output Pins", 'num_output_pins', 3, 45, 1, is_int=True)
        self.add_slider(layout, "Output Pin Diameter (mm)", 'output_pin_diameter', 0.5, 25, 0.1)
        self.add_slider(layout, "Output Disk Diameter (mm)", 'output_disk_diameter', 1, 150, 0.5)
        self.add_slider(layout, "Camshaft Diameter (mm)", 'camshaft_diameter', 1, 50, 0.5)
        self.add_slider(layout, "Tolerance (mm)", 'tolerance', 0.01, 2.0, 0.01)

        # Normalize button
        normalize_btn = QtWidgets.QPushButton("Normalize to External Pins")
        normalize_btn.clicked.connect(self.normalize_to_pins)
        layout.addWidget(normalize_btn)

        # Pause/Resume button
        self.pause_btn = QtWidgets.QPushButton("Pause Animation")
        self.pause_btn.clicked.connect(self.toggle_pause)
        layout.addWidget(self.pause_btn)

        # Reset button
        reset_btn = QtWidgets.QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_params)
        layout.addWidget(reset_btn)

        layout.addStretch()
        self.setLayout(layout)

        # Initialize viewer
        self.viewer.rebuild_items(self.params['num_external_pins'], self.params['num_output_pins'])
        self.update_viewer()

    def add_slider(self, layout, name, key, min_val, max_val, step, is_int=False):
        label = QtWidgets.QLabel(f"{name}: {self.params[key]}")
        
        slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        
        if is_int:
            # For integer sliders, use the actual values directly
            slider.setMinimum(int(min_val))
            slider.setMaximum(int(max_val))
            slider.setValue(int(self.params[key]))
            slider.setSingleStep(int(step))
            scale = 1
        else:
            # For float sliders, scale by 1/step to get fine control
            scale = int(1 / step)
            slider.setMinimum(int(min_val * scale))
            slider.setMaximum(int(max_val * scale))
            slider.setValue(int(self.params[key] * scale))

        def update(v):
            if is_int:
                value = v
                # Round to nearest even number for num_external_pins
                if key == 'num_external_pins':
                    value = value if value % 2 == 0 else value + 1
            else:
                value = round(v / scale, 2)
            
            old_num_external_pins = self.params.get('num_external_pins')
            old_num_output_pins = self.params.get('num_output_pins')
            
            self.params[key] = value
            label.setText(f"{name}: {value}")
            
            # Rebuild items if num_external_pins or num_output_pins changed
            if key in ['num_external_pins', 'num_output_pins'] and (self.params['num_external_pins'] != old_num_external_pins or self.params['num_output_pins'] != old_num_output_pins):
                self.viewer.rebuild_items(self.params['num_external_pins'], self.params['num_output_pins'])
            
            self.update_viewer()

        slider.valueChanged.connect(update)

        layout.addWidget(label)
        layout.addWidget(slider)

    def normalize_to_pins(self):
        """Calculate optimal ring and disk diameters based on external pin count"""
        import math
        
        num_external_pins = self.params['num_external_pins']
        pin_diameter = self.params['pin_diameter']
        
        # Calculate gear ring diameter
        # Formula: ((pin_diameter*num_external_pins) + (1.25*pin_diameter)*(num_external_pins-1)) / pi
        ring_diameter = ((pin_diameter * num_external_pins) + (1.25 * pin_diameter) * (num_external_pins - 1)) / math.pi
        
        # Calculate output disk diameter (2/3 of ring diameter)
        output_disk_diameter = (2/3) * ring_diameter
        
        # Update parameters
        self.params['ring_diameter'] = round(ring_diameter, 1)
        self.params['output_disk_diameter'] = round(output_disk_diameter, 1)
        
        # Update all slider labels
        for child in self.findChildren(QtWidgets.QLabel):
            if "Ring Diameter" in child.text():
                child.setText(f"Ring Diameter (mm): {self.params['ring_diameter']}")
            elif "Output Disk Diameter" in child.text():
                child.setText(f"Output Disk Diameter (mm): {self.params['output_disk_diameter']}")
        
        self.update_viewer()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.setText("Resume Animation" if self.paused else "Pause Animation")

    def reset_params(self):
        defaults = {
            'eccentricity': 1.2,
            'num_external_pins': 12,
            'num_output_pins': 5,
            'ring_diameter': 41.0,
            'pin_diameter': 5.0,
            'output_disk_diameter': 21.0,
            'output_pin_diameter': 1.5,
            'camshaft_diameter': 8.0,
            'animation_speed': 200,
            'tolerance': 0.1
        }
        self.params.update(defaults)
        self.phi = 0
        
        # Update all slider displays
        for child in self.findChildren(QtWidgets.QLabel):
            text = child.text()
            for key, val in defaults.items():
                if key == 'eccentricity' and 'Eccentricity' in text:
                    child.setText(f"Eccentricity (mm): {val}")
                elif key == 'num_external_pins' and 'External Pins' in text:
                    child.setText(f"External Pins: {val}")
                elif key == 'num_output_pins' and 'Output Pins' in text:
                    child.setText(f"Output Pins: {val}")
                elif key == 'ring_diameter' and 'Ring Diameter' in text:
                    child.setText(f"Ring Diameter (mm): {val}")
                elif key == 'pin_diameter' and 'External Pin Diameter' in text:
                    child.setText(f"External Pin Diameter (mm): {val}")
                elif key == 'output_disk_diameter' and 'Output Disk Diameter' in text:
                    child.setText(f"Output Disk Diameter (mm): {val}")
                elif key == 'output_pin_diameter' and 'Output Pin Diameter' in text:
                    child.setText(f"Output Pin Diameter (mm): {val}")
                elif key == 'camshaft_diameter' and 'Camshaft Diameter' in text:
                    child.setText(f"Camshaft Diameter (mm): {val}")
                elif key == 'animation_speed' and 'Animation Speed' in text:
                    child.setText(f"Animation Speed: {val}")
                elif key == 'tolerance' and 'Tolerance' in text:
                    child.setText(f"Tolerance (mm): {val}")
        
        self.viewer.rebuild_items(self.params['num_external_pins'], self.params['num_output_pins'])
        self.update_viewer()

    def update_viewer(self):
        """Update the viewer with current parameters"""
        self.viewer.update_geometry(
            self.params['eccentricity'],
            self.params['num_external_pins'],
            self.params['num_output_pins'],
            self.params['ring_diameter'],
            self.params['pin_diameter'],
            self.params['output_disk_diameter'],
            self.params['output_pin_diameter'],
            self.params['camshaft_diameter'],
            self.params['tolerance'],
            self.phi
        )

    def advance_animation(self):
        """Advance animation by one frame"""
        if not self.paused:
            self.phi += 0.01 * (self.params['animation_speed'] / 60)
            self.update_viewer()


# =================== MAIN WINDOW ===================

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cycloidal Gearbox Parametric Designer")
        self.resize(1400, 900)

        # Create viewer and sliders
        self.viewer = GearboxViewer()
        self.sliders = SliderPanel(self.viewer)

        # Layout
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.sliders, 1)
        layout.addWidget(self.viewer, 3)
        container.setLayout(layout)

        self.setCentralWidget(container)

        # Animation timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.sliders.advance_animation)
        self.timer.start(16)  # ~60 FPS


# =================== RUN ===================

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())