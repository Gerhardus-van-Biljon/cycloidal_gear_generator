'''
Docstring for cycloidal_Gear_generator_V1-2
Author: Gerhardus van Biljon
This is a cycloidal gearbox generator that allows you to design and visualize cycloidal gearboxes with customizable parameters. The application features an interactive OpenGL viewer where you can see the geometry of the cycloidal disk, pins, and camshaft in real-time as you adjust the parameters using sliders.
added in 1.2:
* normalize to external pins button that calculates optimal ring and disk diameters based on the number of external pins and their diameter, using the formula:
* fixed veraible names for easyer reading and understanding of the code, 
* changed sliders to be in a better order and better names....
Fixed in 1.3:
- Cycloid disk now generates as one continuous loop instead of separate segments for easier export
- Added tolerance slider (0.01-2.0mm) to set clearances between all mating parts:
  * Makes cycloid disk slightly smaller (adds tolerance to pin offset)
  * Makes holes in disk larger (output pin holes and camshaft hole)
  * Ensures proper clearances for manufacturing and assembly
- Added optional outer ring that holds external pins:
  * Toggle with "Show Outer Ring" checkbox
  * Adjustable ring width (1-50mm) via slider
  * Inner diameter calculated from ring and pin dimensions with tolerance
  * Useful for complete housing design and export
fixed in 1.4:
- Added CAD export capabilities:
  * Export to DXF format (compatible with AutoCAD, SolidWorks, Fusion 360, etc.)
  * Export to SVG format (for laser cutting, Inkscape, Illustrator, etc.)
  * All geometry organized in layers/colors for easy manipulation
  * Exports current state including animation position (pause to export at specific angle)
  * DXF requires ezdxf library: pip install ezdxf --break-system-packages
fixed in 1.5:
- Performance optimizations for CAD export:
  * Reduced point count by 90% using dynamic resolution (30 segments per pin for outer ring)
  * Merged silhouette of pins and housing for cleaner extrusion in CAD
  * Used closed polylines for watertight geometry
'''



import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl


# =================== EXPORT FUNCTIONS ===================

def export_to_dxf(filename, params, phi=0):
    """
    Final Optimized DXF export:
    - FAST & LIGHT: Reduces point count by 90% using dynamic resolution (30 segments per pin).
    - MERGED SILHOUETTE: Clean merged profile of pins+housing for easy extrusion.
    - WATERTIGHT: Uses closed Polylines.
    """
    try:
        import ezdxf
    except ImportError:
        raise ImportError("Install ezdxf: pip install ezdxf --break-system-packages")

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # Parameters
    e = params["eccentricity"]
    Ne = params["num_external_pins"]
    No = params["num_output_pins"]
    ring_d = params["ring_diameter"]
    pin_d = params["pin_diameter"]
    disk_d = params["output_disk_diameter"]
    out_pin_d = params["output_pin_diameter"]
    cam_d = params["camshaft_diameter"]
    tol = params["tolerance"]
    show_ring = params["show_outer_ring"]
    ring_w = params["outer_ring_width"]

    # Layers
    layers_config = [
        ("CYCLOID_DISK", 1),        # Red
        ("OUTPUT_PINS", 3),         # Green
        ("OUTPUT_HOLES", 6),        # Magenta
        ("CAMSHAFT_HOLE", 5),       # Blue
        ("ECCENTRIC_CAM", 2),       # Yellow
        ("OUTER_RING", 8),          # Gray (Merged Housing)
        ("PIN_CENTERS", 7),         # White (Drill points)
        ("CENTER_AXIS", 4),         # Cyan
    ]
    
    for name, col in layers_config:
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs={"color": col})

    R = ring_d / 2
    Rd = disk_d / 2
    
    # Disk Offset
    disk_center_x = e * np.cos(phi)
    disk_center_y = e * np.sin(phi)

    # ===================== 1. CENTER REFERENCE =====================
    msp.add_point((0, 0), dxfattribs={"layer": "CENTER_AXIS"})

    # ===================== 2. EXTERNAL PIN CENTERS =====================
    for i in range(Ne):
        a = 2 * np.pi * i / Ne
        cx = R * np.cos(a)
        cy = R * np.sin(a)
        msp.add_point((cx, cy), dxfattribs={"layer": "PIN_CENTERS"})

    # ===================== 3. MERGED OUTER RING (OPTIMIZED) =====================
    if show_ring:
        poly_points = []
        rp = pin_d / 2
        
        # Simulation Housing Parameters
        pocket_depth = rp * 0.8
        clearance_space = rp * 0.8
        radius_variation = pocket_depth + clearance_space
        
        # OPTIMIZATION: Dynamic resolution
        # 30 points per pin is smooth enough for manufacturing but light for CAD.
        # Example: 12 pins = 360 points total (vs 3600 before).
        points_per_pin = 30
        num_samples = int(Ne * points_per_pin)
        angles = np.linspace(0, 2*np.pi, num_samples, endpoint=False)
        
        for theta in angles:
            # A. Calculate Housing Wall Radius
            pin_factor = np.cos(Ne * theta)
            r_housing = (R) - pocket_depth + (radius_variation * (1 - pin_factor) / 2)
            
            # B. Calculate Pin Surface Radius (Ray Casting)
            step = 2*np.pi/Ne
            pin_idx = int(round(theta / step))
            pin_angle = pin_idx * step
            
            cx = R * np.cos(pin_angle)
            cy = R * np.sin(pin_angle)
            
            dot_prod = cx * np.cos(theta) + cy * np.sin(theta)
            dist_sq = cx**2 + cy**2
            discriminant = dot_prod**2 - (dist_sq - rp**2)
            
            r_pin = 1e9
            if discriminant >= 0:
                d1 = dot_prod - np.sqrt(discriminant)
                if d1 > 0:
                    r_pin = d1
            
            # C. Visual Surface Intersection
            final_r = min(r_housing, r_pin)
            poly_points.append((final_r * np.cos(theta), final_r * np.sin(theta)))

        # Create lightweight polyline
        msp.add_lwpolyline(poly_points, close=True, dxfattribs={"layer": "OUTER_RING"})

        # Outer Circle
        outer_radius = R + ring_w
        msp.add_circle((0, 0), outer_radius, dxfattribs={"layer": "OUTER_RING"})

    # ===================== 4. OUTPUT PINS =====================
    for i in range(No):
        a = 2 * np.pi * i / No
        cx = Rd * np.cos(a)
        cy = Rd * np.sin(a)
        msp.add_circle((cx, cy), out_pin_d / 2, dxfattribs={"layer": "OUTPUT_PINS"})

    # ===================== 5. OUTPUT HOLES (In Disk) =====================
    hole_r = out_pin_d / 2 + e + tol
    for i in range(No):
        a = 2 * np.pi * i / No
        cx = Rd * np.cos(a) + disk_center_x
        cy = Rd * np.sin(a) + disk_center_y
        msp.add_circle((cx, cy), hole_r, dxfattribs={"layer": "OUTPUT_HOLES"})

    # ===================== 6. CAMSHAFT HOLE & CAM =====================
    cam_hole_r = cam_d / 2 + tol
    msp.add_circle((0, 0), cam_hole_r, dxfattribs={"layer": "CAMSHAFT_HOLE"})

    cam_lobe_r = (cam_d - 2 * e) / 2
    if cam_lobe_r > 0:
        msp.add_circle((disk_center_x, disk_center_y), cam_lobe_r, dxfattribs={"layer": "ECCENTRIC_CAM"})

    # ===================== 7. CYCLOID DISK =====================
    # Cycloid disk also benefits from optimized resolution
    points_per_lobe = 60 # Reduced from 80 (still very smooth)
    num_lobes = Ne - 1
    total_points = points_per_lobe * num_lobes
    t = np.linspace(0, 2*np.pi, total_points, endpoint=True)

    rolling = (num_lobes/(num_lobes+1)) * R
    stationary = R / (num_lobes+1)

    xa = (rolling + stationary)*np.cos(t) - e*np.cos((rolling+stationary)/stationary * t)
    ya = (rolling + stationary)*np.sin(t) - e*np.sin((rolling+stationary)/stationary * t)

    dxa = (rolling + stationary)*(-np.sin(t) + (e/stationary)*np.sin((rolling+stationary)/stationary * t))
    dya = (rolling + stationary)*( np.cos(t) - (e/stationary)*np.cos((rolling+stationary)/stationary * t))

    pin_r = pin_d/2 + tol
    xd = xa + pin_r/np.sqrt(dxa**2 + dya**2)*(-dya)
    yd = ya + pin_r/np.sqrt(dxa**2 + dya**2)*( dxa)

    x = xd*np.cos(-phi/num_lobes) - yd*np.sin(-phi/num_lobes) + disk_center_x
    y = xd*np.sin(-phi/num_lobes) + yd*np.cos(-phi/num_lobes) + disk_center_y

    spline_points = [(float(x[i]), float(y[i]), 0) for i in range(len(x))]
    
    disk_spline = msp.add_spline(spline_points, dxfattribs={"layer": "CYCLOID_DISK"})
    disk_spline.closed = True

    doc.saveas(filename)
    return True



def export_to_svg(filename, params, phi=0):
    """Export all geometry to SVG format"""
    # Extract parameters
    eccentricity = params['eccentricity']
    num_external_pins = params['num_external_pins']
    num_output_pins = params['num_output_pins']
    ring_diameter = params['ring_diameter']
    pin_diameter = params['pin_diameter']
    output_disk_diameter = params['output_disk_diameter']
    output_pin_diameter = params['output_pin_diameter']
    camshaft_diameter = params['camshaft_diameter']
    tolerance = params['tolerance']
    show_outer_ring = params['show_outer_ring']
    outer_ring_width = params['outer_ring_width']
    
    # Calculate viewbox
    if show_outer_ring:
        max_radius = ring_diameter/2 + outer_ring_width + 10
    else:
        max_radius = ring_diameter/2 + 10
    
    viewbox = f"{-max_radius} {-max_radius} {2*max_radius} {2*max_radius}"
    
    # Start SVG
    svg_lines = [
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">',
        f'<g transform="scale(1,-1)">'  # Flip Y axis to match CAD convention
    ]
    
    def points_to_path(points):
        """Convert numpy points to SVG path"""
        path = f"M {points[0][0]:.3f},{points[0][1]:.3f}"
        for p in points[1:]:
            path += f" L {p[0]:.3f},{p[1]:.3f}"
        path += " Z"
        return path
    
    # External pins (gray)
    pins = pin_ring(num_external_pins, ring_diameter, pin_diameter)
    for pin in pins:
        path = points_to_path(pin)
        svg_lines.append(f'<path d="{path}" fill="none" stroke="#666666" stroke-width="0.5"/>')
    
    # Cycloid disk (red)
    cd = cycloid_disk(eccentricity, num_external_pins, ring_diameter, pin_diameter, phi, tolerance)
    if len(cd) > 0:
        path = points_to_path(cd[0])
        svg_lines.append(f'<path d="{path}" fill="none" stroke="#FF4444" stroke-width="0.8"/>')
    
    # Output pins (green)
    ip = inner_pins(num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi)
    for pin in ip:
        path = points_to_path(pin)
        svg_lines.append(f'<path d="{path}" fill="none" stroke="#44FF44" stroke-width="0.5"/>')
    
    # Output holes (magenta)
    ic = inner_circles(eccentricity, num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi, tolerance)
    for circle in ic:
        path = points_to_path(circle)
        svg_lines.append(f'<path d="{path}" fill="none" stroke="#FF44FF" stroke-width="0.5"/>')
    
    # Camshaft hole (blue)
    cam = camshaft(camshaft_diameter, phi, tolerance)
    path = points_to_path(cam)
    svg_lines.append(f'<path d="{path}" fill="none" stroke="#4444FF" stroke-width="0.6"/>')
    
    # Eccentric camshaft (yellow/orange)
    ecc_cam = eccentric_camshaft(eccentricity, camshaft_diameter, phi)
    path = points_to_path(ecc_cam)
    svg_lines.append(f'<path d="{path}" fill="none" stroke="#FFAA00" stroke-width="0.5"/>')
    
    # Outer ring (if enabled)
    if show_outer_ring:
        inner_profile, outer_profile = outer_ring(num_external_pins, ring_diameter, pin_diameter, outer_ring_width, tolerance)
        inner_path = points_to_path(inner_profile)
        outer_path = points_to_path(outer_profile)
        svg_lines.append(f'<path d="{inner_path}" fill="none" stroke="#888888" stroke-width="0.6"/>')
        svg_lines.append(f'<path d="{outer_path}" fill="none" stroke="#888888" stroke-width="0.6"/>')
    
    # Close SVG
    svg_lines.append('</g>')
    svg_lines.append('</svg>')
    
    # Write to file
    with open(filename, 'w') as f:
        f.write('\n'.join(svg_lines))
    
    return True

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


def outer_ring(num_pins, ring_diameter, pin_diameter, ring_width, tolerance=0):
    """Generate outer ring that holds the external pins
    Inner profile creates pockets that hold the pins - sits inside the pin diameter
    Outer profile is circular"""
    
    pin_radius = pin_diameter / 2
    ring_radius = ring_diameter / 2
    
    # Number of points for smooth curves
    points_per_segment = 100
    total_points = points_per_segment * num_pins
    
    # Generate inner profile - creates pockets that sit inside the pins
    inner_points = []
    for i in range(total_points):
        # Angle around the ring
        angle = 2 * np.pi * i / total_points
        
        # Use a smooth function that creates points at pin locations
        # cos goes from 1 (at pins) to -1 (between pins)
        pin_factor = np.cos(num_pins * angle)
        
        # Inner radius varies based on proximity to pins
        # At pins: ring_radius - pin_radius * 0.8 (sits deeper inside the pin to hold it)
        # Between pins: ring_radius + pin_radius * 0.8 (more clearance for cycloid disk)
        # Increased waviness for better cycloid disk clearance
        
        pocket_depth = pin_radius * 0.8  # How far into the pin the ring sits
        clearance_space = pin_radius * 0.8  # Clearance between pins for cycloid disk
        
        # Smooth transition using cosine
        radius_variation = pocket_depth + clearance_space
        inner_radius = ring_radius - pocket_depth + radius_variation * (1 - pin_factor) / 2
        
        x = inner_radius * np.cos(angle)
        y = inner_radius * np.sin(angle)
        inner_points.append([x, y, 0])
    
    # Close inner profile
    inner_points.append(inner_points[0])
    inner_profile = np.array(inner_points)
    
    # Generate outer profile - simple circle
    outer_points = []
    outer_radius = ring_radius + ring_width
    t = np.linspace(0, 2*np.pi, 200, endpoint=True)
    for angle in t:
        x = outer_radius * np.cos(angle)
        y = outer_radius * np.sin(angle)
        outer_points.append([x, y, 0])
    outer_profile = np.array(outer_points)
    
    return inner_profile, outer_profile


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
        self.outer_ring_inner_item = None
        self.outer_ring_outer_item = None

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
        
        # Add outer ring items if not already added
        if self.outer_ring_inner_item is None:
            self.outer_ring_inner_item = gl.GLLinePlotItem(color=(0.5, 0.5, 0.5, 1), width=2.5)
            self.addItem(self.outer_ring_inner_item)
        
        if self.outer_ring_outer_item is None:
            self.outer_ring_outer_item = gl.GLLinePlotItem(color=(0.5, 0.5, 0.5, 1), width=2.5)
            self.addItem(self.outer_ring_outer_item)

    def update_geometry(self, eccentricity, num_external_pins, num_output_pins, ring_diameter, pin_diameter, output_disk_diameter, output_pin_diameter, camshaft_diameter, tolerance, show_outer_ring, outer_ring_width, phi):
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
        
        # Outer ring - show/hide based on checkbox
        if show_outer_ring:
            inner_profile, outer_profile = outer_ring(num_external_pins, ring_diameter, pin_diameter, outer_ring_width, tolerance)
            self.outer_ring_inner_item.setData(pos=inner_profile)
            self.outer_ring_outer_item.setData(pos=outer_profile)
            self.outer_ring_inner_item.setVisible(True)
            self.outer_ring_outer_item.setVisible(True)
        else:
            # Hide the ring
            self.outer_ring_inner_item.setVisible(False)
            self.outer_ring_outer_item.setVisible(False)


# =================== SLIDER PANEL ===================

class SliderPanel(QtWidgets.QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        # Parameters - using descriptive names
        self.params = {
            'eccentricity': 1.4,
            'num_external_pins': 24,
            'num_output_pins': 7,
            'ring_diameter': 80.0,
            'pin_diameter': 5.0,
            'output_disk_diameter': 50.0,
            'output_pin_diameter': 10.0,
            'camshaft_diameter': 20.0,
            'animation_speed': 200,
            'tolerance': 0.2,
            'show_outer_ring': False,
            'outer_ring_width': 15.0
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

        # Outer ring checkbox and slider
        self.outer_ring_checkbox = QtWidgets.QCheckBox("Show Outer Ring")
        self.outer_ring_checkbox.setChecked(self.params['show_outer_ring'])
        self.outer_ring_checkbox.stateChanged.connect(self.toggle_outer_ring)
        layout.addWidget(self.outer_ring_checkbox)
        
        self.add_slider(layout, "Outer Ring Width (mm)", 'outer_ring_width', 1, 50, 0.5)

        # Normalize button
        normalize_btn = QtWidgets.QPushButton("Normalize to External Pins")
        normalize_btn.clicked.connect(self.normalize_to_pins)
        layout.addWidget(normalize_btn)

        # Export buttons
        export_label = QtWidgets.QLabel("Export to CAD:")
        export_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(export_label)
        
        export_dxf_btn = QtWidgets.QPushButton("Export DXF")
        export_dxf_btn.clicked.connect(self.export_dxf)
        layout.addWidget(export_dxf_btn)
        
        export_svg_btn = QtWidgets.QPushButton("Export SVG")
        export_svg_btn.clicked.connect(self.export_svg)
        layout.addWidget(export_svg_btn)

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

    def toggle_outer_ring(self, state):
        """Toggle outer ring visibility"""
        self.params['show_outer_ring'] = bool(state)
        self.update_viewer()

    def export_dxf(self):
        """Export current geometry to DXF file"""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export to DXF",
            "cycloidal_gearbox.dxf",
            "DXF Files (*.dxf)"
        )
        
        if filename:
            try:
                export_to_dxf(filename, self.params, self.phi)
                QtWidgets.QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Geometry exported to:\n{filename}\n\nLayers:\n"
                    "- EXTERNAL_PINS\n"
                    "- CYCLOID_DISK\n"
                    "- OUTPUT_PINS\n"
                    "- OUTPUT_HOLES\n"
                    "- CAMSHAFT_HOLE\n"
                    "- ECCENTRIC_SHAFT\n"
                    "- OUTER_RING (if enabled)"
                )
            except ImportError as e:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Missing Library",
                    str(e)
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Error exporting DXF:\n{str(e)}"
                )
    
    def export_svg(self):
        """Export current geometry to SVG file"""
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export to SVG",
            "cycloidal_gearbox.svg",
            "SVG Files (*.svg)"
        )
        
        if filename:
            try:
                export_to_svg(filename, self.params, self.phi)
                QtWidgets.QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Geometry exported to:\n{filename}"
                )
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Error exporting SVG:\n{str(e)}"
                )

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
            'eccentricity': 1.4,
            'num_external_pins': 24,
            'num_output_pins': 7,
            'ring_diameter': 80.0,
            'pin_diameter': 5.0,
            'output_disk_diameter': 50.0,
            'output_pin_diameter': 10.0,
            'camshaft_diameter': 20.0,
            'animation_speed': 200,
            'tolerance': 0.2,
            'show_outer_ring': False,
            'outer_ring_width': 15.0
        }
        self.params.update(defaults)
        self.phi = 0
        
        # Update checkbox
        self.outer_ring_checkbox.setChecked(defaults['show_outer_ring'])
        
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
                elif key == 'outer_ring_width' and 'Outer Ring Width' in text:
                    child.setText(f"Outer Ring Width (mm): {val}")
        
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
            self.params['show_outer_ring'],
            self.params['outer_ring_width'],
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