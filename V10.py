'''
Docstring for cycloidal_Gear_generator
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
fixed in 1.6:
- Added optional "Balance Disk": a second cycloid disk mounted 180 degrees out of phase
  (phi + pi) on the eccentric shaft, used in real cycloidal drives to cancel the rotating
  imbalance/vibration caused by a single eccentric lobe.
  * Toggle with "Show Balance Disk (180 deg offset)" checkbox
  * The balance disk's eccentric offset and lobe profile use (phi + pi) so it still meshes
    correctly with the SAME ring pins as disk 1.
  * Because that flips the disk's own rotation by half a lobe pitch (pi/num_lobes), the
    balance disk's OUTPUT HOLES are given an extra local phase offset of +pi/num_lobes so
    they land back on the SAME physical output pins as disk 1 (a single output pin set can
    pass through both disks).
  * SVG export draws it with dashed strokes so it's visually distinguishable from disk 1.
fixed in 1.7:
- DXF export of the balance disk now writes a SEPARATE file (e.g. "part_balance_disk.dxf")
  instead of overlapping layers in the same file, since two overlapping disk profiles are
  hard to select/cut individually in CAD software. export_to_dxf() now takes a
  disk_variant=("primary"|"balance") argument; the export button calls it twice
  automatically when the balance disk is enabled and reports both filenames.
fixed in V9:
- Updated default save filenames to "cycloidal_gearbox_externalPINAmount_ring radius.dxf/svg" format (e.g. "cycloidal_gearbox_12pins_40mm.dxf").
fixed in V10:
- Fixed eccentric shaft/camshaft geometry: the eccentric lobe (the ring inside the camshaft hole of the cycloid disk) is now the larger diameter, and the central input shaft is the smaller one.
- Slider now directly controls "Input Shaft Diameter" instead of the eccentric lobe outer diameter.
- The eccentric lobe diameter is automatically calculated as: Input Shaft Diameter + 2 * Eccentricity.
- Corrected tolerance clearance representation for the offset camshaft hole in the cycloid disk.
'''



import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl


# EXPORT FUNCTIONS 

def export_to_dxf(filename, params, phi=0, disk_variant="primary"):
    """
    Final Optimized DXF export:
    - FAST & LIGHT: Reduces point count by 90% using dynamic resolution (30 segments per pin).
    - MERGED SILHOUETTE: Clean merged profile of pins+housing for easy extrusion.
    - WATERTIGHT: Uses closed Polylines.

    disk_variant selects WHICH disk's cycloid profile / output holes / eccentric lobe are
    written to this file:
      - "primary": disk 1 (phi), the normal single-disk export.
      - "balance": the 180-degree phase-offset balance disk (phi + pi), with its output
        holes phase-corrected so they line up with the SAME output pins as disk 1.

    Each variant is a fully self-contained file (ring pins, output pins, camshaft hole,
    outer ring, and center axis are all included for reference/alignment) but only ONE
    disk's geometry is written per file. This is intentional: if both disks' profiles were
    stacked in a single file they overlap and are hard to select/cut in CAD. To export a
    balanced gearbox, call this twice with disk_variant="primary" and "balance" and two
    different filenames (the SliderPanel export button already does this for you).
    """
    try:
        import ezdxf
    except ImportError:
        raise ImportError("Install ezdxf: pip install ezdxf --break-system-packages")

    if disk_variant not in ("primary", "balance"):
        raise ValueError("disk_variant must be 'primary' or 'balance'")

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
    input_shaft_d = params["input_shaft_diameter"]
    tol = params["tolerance"]
    show_ring = params["show_outer_ring"]
    ring_w = params["outer_ring_width"]

    # Layers - same names in every file since each file only ever contains ONE disk's
    # geometry (no need for _2 suffixes when there's nothing to collide with).
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
    num_lobes = Ne - 1

    # This file's crank angle and hole phase, depending on which disk we're exporting.
    # See cycloid_disk()/inner_circles() docstrings for why "balance" uses phi+pi and
    # an extra pi/num_lobes hole phase so its holes still fit the shared output pins.
    if disk_variant == "balance":
        disk_phi = phi + np.pi
        toggle_phase_offset = np.pi / num_lobes
    else:
        disk_phi = phi
        toggle_phase_offset = 0.0

    # Disk Offset
    disk_center_x = e * np.cos(disk_phi)
    disk_center_y = e * np.sin(disk_phi)

    #   CENTER REFERENCE 
    msp.add_point((0, 0), dxfattribs={"layer": "CENTER_AXIS"})

    # EXTERNAL PIN CENTERS 
    for i in range(Ne):
        a = 2 * np.pi * i / Ne
        cx = R * np.cos(a)
        cy = R * np.sin(a)
        msp.add_point((cx, cy), dxfattribs={"layer": "PIN_CENTERS"})

    #  MERGED OUTER RING (OPTIMIZED) 
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

    #OUTPUT PINS 
    for i in range(No):
        a = 2 * np.pi * i / No - phi / num_lobes
        cx = Rd * np.cos(a)
        cy = Rd * np.sin(a)
        msp.add_circle((cx, cy), out_pin_d / 2, dxfattribs={"layer": "OUTPUT_PINS"})

    #  OUTPUT HOLES (In Disk) 
    # toggle_phase_offset is 0 for the primary disk, and pi/num_lobes for the balance disk
    # so its holes still register on the SAME physical output pins drawn above.
    hole_r = out_pin_d / 2 + e + tol
    for i in range(No):
        a = 2 * np.pi * i / No + toggle_phase_offset - disk_phi / num_lobes
        cx = Rd * np.cos(a) + disk_center_x
        cy = Rd * np.sin(a) + disk_center_y
        msp.add_circle((cx, cy), hole_r, dxfattribs={"layer": "OUTPUT_HOLES"})

    #  CAMSHAFT HOLE & CAM 
    # Hole in the housing centered at (0, 0) (Blue Ring: smaller than yellow ring by 2 * eccentricity)
    cam_hole_r = input_shaft_d / 2 - e
    msp.add_circle((0, 0), cam_hole_r, dxfattribs={"layer": "CAMSHAFT_HOLE"})

    # Hole in the cycloid disk centered at the disk offset (Yellow Ring: exactly input_shaft_diameter)
    cam_lobe_r = input_shaft_d / 2
    if cam_lobe_r > 0:
        msp.add_circle((disk_center_x, disk_center_y), cam_lobe_r, dxfattribs={"layer": "ECCENTRIC_CAM"})

    #  CYCLOID DISK 
    # Cycloid disk with optimized resolution
    points_per_lobe = 60 # Reduced from 80 (nogstteds smooth)
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

    # NOTE: xd, yd don't depend on phi at all - only the final rotate/translate below does.
    # That's why using disk_phi = phi + pi for the balance disk still meshes correctly:
    # it's just this same curve family evaluated at a shifted crank angle.
    x = xd*np.cos(-disk_phi/num_lobes) - yd*np.sin(-disk_phi/num_lobes) + disk_center_x
    y = xd*np.sin(-disk_phi/num_lobes) + yd*np.cos(-disk_phi/num_lobes) + disk_center_y

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
    input_shaft_diameter = params['input_shaft_diameter']
    tolerance = params['tolerance']
    show_outer_ring = params['show_outer_ring']
    outer_ring_width = params['outer_ring_width']
    show_balance_disk = params.get('show_balance_disk', False)
    
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
    
    # Camshaft hole / Input shaft hole at origin (blue)
    cam = camshaft(input_shaft_diameter, eccentricity, phi)
    path = points_to_path(cam)
    svg_lines.append(f'<path d="{path}" fill="none" stroke="#4444FF" stroke-width="0.6"/>')
    
    # Eccentric camshaft/lobe hole in disk (yellow/orange)
    ecc_cam = eccentric_camshaft(eccentricity, input_shaft_diameter, phi)
    path = points_to_path(ecc_cam)
    svg_lines.append(f'<path d="{path}" fill="none" stroke="#FFAA00" stroke-width="0.5"/>')
    
    # Outer ring (if enabled)
    if show_outer_ring:
        inner_profile, outer_profile = outer_ring(num_external_pins, ring_diameter, pin_diameter, outer_ring_width, tolerance)
        inner_path = points_to_path(inner_profile)
        outer_path = points_to_path(outer_profile)
        svg_lines.append(f'<path d="{inner_path}" fill="none" stroke="#888888" stroke-width="0.6"/>')
        svg_lines.append(f'<path d="{outer_path}" fill="none" stroke="#888888" stroke-width="0.6"/>')

    # Balance disk (180 deg phase-offset second disk), drawn dashed to distinguish it
    if show_balance_disk:
        num_lobes = num_external_pins - 1
        phi2 = phi + np.pi
        toggle_phase_offset = np.pi / num_lobes

        cd2 = cycloid_disk(eccentricity, num_external_pins, ring_diameter, pin_diameter, phi2, tolerance)
        if len(cd2) > 0:
            path = points_to_path(cd2[0])
            svg_lines.append(f'<path d="{path}" fill="none" stroke="#FF8800" stroke-width="0.8" stroke-dasharray="2,1.2"/>')

        ic2 = inner_circles(eccentricity, num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi2, tolerance, toggle_phase_offset)
        for circle in ic2:
            path = points_to_path(circle)
            svg_lines.append(f'<path d="{path}" fill="none" stroke="#AA44FF" stroke-width="0.5" stroke-dasharray="2,1.2"/>')

        ecc_cam2 = eccentric_camshaft(eccentricity, input_shaft_diameter, phi2)
        path = points_to_path(ecc_cam2)
        svg_lines.append(f'<path d="{path}" fill="none" stroke="#FF00AA" stroke-width="0.5" stroke-dasharray="2,1.2"/>')
    
    # Close SVG
    svg_lines.append('</g>')
    svg_lines.append('</svg>')
    
    # Write to file
    with open(filename, 'w') as f:
        f.write('\n'.join(svg_lines))
    
    return True

#  MATH FUNCTIONS

def pin_ring(num_pins, ring_diameter, pin_diameter):
    t = np.linspace(0, 2*np.pi, 200)
    pins = []
    for i in range(num_pins):
        x = pin_diameter/2*np.sin(t) + ring_diameter/2*np.cos(2*np.pi*i/num_pins)
        y = pin_diameter/2*np.cos(t) + ring_diameter/2*np.sin(2*np.pi*i/num_pins)
        pins.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return pins


def inner_pins(num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi):
    """output_pin_diameter and output_disk_diameter are diameters, not radii.
    These are the physical output-shaft pins - a single shared set that both
    the primary disk and (if enabled) the balance disk orbit around."""
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


def inner_circles(eccentricity, num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi, tolerance=0, hole_phase_offset=0.0):
    """output_pin_diameter and output_disk_diameter are diameters, not radii.

    hole_phase_offset: extra local rotation (radians) applied to the hole pattern
    before the disk's own rotation is applied. Used by the balance disk (phi + pi)
    so its holes land back on the SAME physical output pins as the primary disk -
    without this, using phi+pi for the disk would shift the holes by half a lobe
    pitch relative to the pins. Leave at 0.0 for the primary disk.
    """
    t = np.linspace(0, 2*np.pi, 200)
    num_lobes = num_external_pins - 1  # Number of lobes = num_external_pins - 1
    circles = []
    output_pin_radius = output_pin_diameter / 2  # Convert to radius
    output_disk_radius = output_disk_diameter / 2  # Convert to radius
    
    for i in range(num_output_pins):
        # Circle radius needs to be larger than pin by eccentricity amount plus tolerance
        # hole_radius = output_pin_radius + eccentricity + tolerance (for clearance)
        hole_radius = output_pin_radius + eccentricity + tolerance
        base_angle = 2*np.pi*i/num_output_pins + hole_phase_offset
        x = (hole_radius*np.cos(t) + output_disk_radius*np.cos(base_angle))*np.cos(-phi/num_lobes) - (hole_radius*np.sin(t) + output_disk_radius*np.sin(base_angle))*np.sin(-phi/num_lobes) + eccentricity*np.cos(phi)
        y = (hole_radius*np.cos(t) + output_disk_radius*np.cos(base_angle))*np.sin(-phi/num_lobes) + (hole_radius*np.sin(t) + output_disk_radius*np.sin(base_angle))*np.cos(-phi/num_lobes) + eccentricity*np.sin(phi)
        circles.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return circles


def cycloid_disk(eccentricity, num_external_pins, ring_diameter, pin_diameter, phi, tolerance=0):
    """Generates the cycloid disk profile at crank angle phi.

    Note: to generate a second, 180-degree-balanced disk, simply call this again
    with (phi + np.pi) - the shape math (xa, ya, dxa, dya, xd, yd) doesn't depend
    on phi at all, only the final rotation/translation does, so f(phi + pi) is a
    valid point along the SAME continuous rolling path and meshes correctly with
    the same ring pins, just with the eccentric mass on the opposite side."""
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


def camshaft(input_shaft_diameter, eccentricity, phi):
    """Generate central input shaft hole at (0,0) (Blue Ring)
    Blue Ring Diameter = Yellow Ring Diameter - (2 * Eccentricity)
    Radius = input_shaft_diameter / 2 - eccentricity"""
    t = np.linspace(0, 2*np.pi, 200)
    hole_radius = input_shaft_diameter / 2 - eccentricity
    x = hole_radius * np.cos(t)
    y = hole_radius * np.sin(t)
    return np.vstack([x, y, np.zeros_like(x)]).T


def eccentric_camshaft(eccentricity, input_shaft_diameter, phi):
    """Generate eccentric shaft lobe (Yellow Ring).
    Radius is exactly input_shaft_diameter / 2 (no tolerance or offsets)."""
    t = np.linspace(0, 2*np.pi, 200)
    cam_radius = input_shaft_diameter / 2
    x = cam_radius * np.cos(t) + eccentricity * np.cos(phi)
    y = cam_radius * np.sin(t) + eccentricity * np.sin(phi)
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


# OPENGL VIEWER 

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

        # Balance disk items (180 deg phase-offset second disk)
        self.cycloid_items2 = []
        self.inner_circle_items2 = []
        self.eccentric_camshaft_item2 = None

    def rebuild_items(self, num_external_pins, num_output_pins):
        """Rebuild OpenGL items when num_external_pins or num_output_pins changes"""
        # Remove old items
        for item in (self.outer_pin_items + self.inner_pin_items + self.inner_circle_items
                     + self.cycloid_items + self.inner_circle_items2 + self.cycloid_items2):
            self.removeItem(item)

        # Create new items with lighter colors
        self.outer_pin_items = [gl.GLLinePlotItem(color=(0.4, 0.4, 0.4, 1), width=2) for _ in range(num_external_pins)]
        self.inner_pin_items = [gl.GLLinePlotItem(color=(0.3, 0.9, 0.3, 1), width=2) for _ in range(num_output_pins)]
        self.inner_circle_items = [gl.GLLinePlotItem(color=(0.9, 0.5, 0.9, 1), width=2) for _ in range(num_output_pins)]
        # Now only need 1 item for the continuous cycloid disk
        self.cycloid_items = [gl.GLLinePlotItem(color=(1, 0.3, 0.3, 1), width=2.5)]

        # Balance disk (180 deg offset): its own cycloid profile + its own output holes
        self.cycloid_items2 = [gl.GLLinePlotItem(color=(1, 0.6, 0.1, 1), width=2.5)]
        self.inner_circle_items2 = [gl.GLLinePlotItem(color=(0.7, 0.4, 0.95, 1), width=2) for _ in range(num_output_pins)]

        # Add new items
        for item in (self.outer_pin_items + self.inner_pin_items + self.inner_circle_items
                     + self.cycloid_items + self.inner_circle_items2 + self.cycloid_items2):
            self.addItem(item)
        
        # Add camshaft items if not already added
        if self.camshaft_item is None:
            self.camshaft_item = gl.GLLinePlotItem(color=(0.2, 0.5, 0.9, 1), width=3)
            self.addItem(self.camshaft_item)
        
        if self.eccentric_camshaft_item is None:
            self.eccentric_camshaft_item = gl.GLLinePlotItem(color=(0.9, 0.7, 0.2, 1), width=2)
            self.addItem(self.eccentric_camshaft_item)

        if self.eccentric_camshaft_item2 is None:
            self.eccentric_camshaft_item2 = gl.GLLinePlotItem(color=(0.95, 0.3, 0.8, 1), width=2)
            self.addItem(self.eccentric_camshaft_item2)
        
        # Add outer ring items if not already added
        if self.outer_ring_inner_item is None:
            self.outer_ring_inner_item = gl.GLLinePlotItem(color=(0.5, 0.5, 0.5, 1), width=2.5)
            self.addItem(self.outer_ring_inner_item)
        
        if self.outer_ring_outer_item is None:
            self.outer_ring_outer_item = gl.GLLinePlotItem(color=(0.5, 0.5, 0.5, 1), width=2.5)
            self.addItem(self.outer_ring_outer_item)

    def update_geometry(self, eccentricity, num_external_pins, num_output_pins, ring_diameter, pin_diameter, output_disk_diameter, output_pin_diameter, input_shaft_diameter, tolerance, show_outer_ring, outer_ring_width, phi, show_balance_disk=False):
        """Update all geometry"""
        # Outer pins
        pins = pin_ring(num_external_pins, ring_diameter, pin_diameter)
        for i, item in enumerate(self.outer_pin_items):
            if i < len(pins):
                item.setData(pos=pins[i])

        # Inner pins (shared physical output pins - same for both disks)
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
        
        # Central camshaft/input shaft hole (Blue Ring)
        cam = camshaft(input_shaft_diameter, eccentricity, phi)
        self.camshaft_item.setData(pos=cam)
        
        # Eccentric camshaft/lobe (Yellow Ring)
        ecc_cam = eccentric_camshaft(eccentricity, input_shaft_diameter, phi)
        self.eccentric_camshaft_item.setData(pos=ecc_cam)

        # Balance disk (180 deg phase-offset second disk) - show/hide based on checkbox
        if show_balance_disk:
            num_lobes = num_external_pins - 1
            phi2 = phi + np.pi
            # Extra local phase so the holes realign with the SAME output pins as disk 1
            toggle_phase_offset = np.pi / num_lobes

            cd2 = cycloid_disk(eccentricity, num_external_pins, ring_diameter, pin_diameter, phi2, tolerance)
            if len(cd2) > 0 and len(self.cycloid_items2) > 0:
                self.cycloid_items2[0].setData(pos=cd2[0])
                self.cycloid_items2[0].setVisible(True)

            ic2 = inner_circles(eccentricity, num_output_pins, num_external_pins, output_pin_diameter, output_disk_diameter, phi2, tolerance, toggle_phase_offset)
            for i, item in enumerate(self.inner_circle_items2):
                if i < len(ic2):
                    item.setData(pos=ic2[i])
                    item.setVisible(True)

            ecc_cam2 = eccentric_camshaft(eccentricity, input_shaft_diameter, phi2)
            self.eccentric_camshaft_item2.setData(pos=ecc_cam2)
            self.eccentric_camshaft_item2.setVisible(True)
        else:
            if len(self.cycloid_items2) > 0:
                self.cycloid_items2[0].setVisible(False)
            for item in self.inner_circle_items2:
                item.setVisible(False)
            if self.eccentric_camshaft_item2 is not None:
                self.eccentric_camshaft_item2.setVisible(False)
        
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
            'input_shaft_diameter': 20.0,
            'animation_speed': 200,
            'tolerance': 0.2,
            'show_outer_ring': False,
            'outer_ring_width': 15.0,
            'show_balance_disk': False
        }
        
        # Load configuration from file if it exists, otherwise use defaults
        self.load_config()
        
        self.phi = 0
        self.paused = False
        
        self.labels = {}
        self.sliders = {}

        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("Cycloidal Gearbox Designer")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Add sliders with descriptive parameter names
        self.add_slider(layout, "Animation Speed", 'animation_speed', 1, 2000, 1, is_int=True)
        self.add_slider(layout, "Eccentricity (mm)", 'eccentricity', 0.5, 10.0, 0.01)
        self.add_slider(layout, "External Pins", 'num_external_pins', 3, 100, 1, is_int=True)
        self.add_slider(layout, "External Pin Diameter (mm)", 'pin_diameter', 2, 25, 0.5)
        self.add_slider(layout, "Ring Diameter (mm)", 'ring_diameter', 20, 250, 1)
        self.add_slider(layout, "Output Pins", 'num_output_pins', 3, 45, 1, is_int=True)
        self.add_slider(layout, "Output Pin Diameter (mm)", 'output_pin_diameter', 0.5, 25, 0.1)
        self.add_slider(layout, "Output Disk Diameter (mm)", 'output_disk_diameter', 1, 150, 0.5)
        self.add_slider(layout, "Input Shaft Diameter (mm)", 'input_shaft_diameter', 1, 50, 0.5)
        self.add_slider(layout, "Tolerance (mm)", 'tolerance', 0.01, 2.0, 0.01)

        # Outer ring checkbox and slider
        self.outer_ring_checkbox = QtWidgets.QCheckBox("Show Outer Ring")
        self.outer_ring_checkbox.setChecked(self.params['show_outer_ring'])
        self.outer_ring_checkbox.stateChanged.connect(self.toggle_outer_ring)
        layout.addWidget(self.outer_ring_checkbox)
        
        self.add_slider(layout, "Outer Ring Width (mm)", 'outer_ring_width', 1, 50, 0.5)

        # Balance disk checkbox (180 deg phase-offset second disk for vibration cancellation)
        self.balance_disk_checkbox = QtWidgets.QCheckBox("Show Balance Disk (180° offset)")
        self.balance_disk_checkbox.setChecked(self.params['show_balance_disk'])
        self.balance_disk_checkbox.stateChanged.connect(self.toggle_balance_disk)
        layout.addWidget(self.balance_disk_checkbox)

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

    def load_config(self):
        import os
        import json
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_gearbox.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded = json.load(f)
                    # Backward compatibility for old configs
                    if "camshaft_diameter" in loaded and "input_shaft_diameter" not in loaded:
                        loaded["input_shaft_diameter"] = loaded["camshaft_diameter"]
                    for k, v in loaded.items():
                        if k in self.params:
                            # Safely cast loaded parameter to default type
                            if isinstance(self.params[k], bool):
                                self.params[k] = bool(v)
                            elif isinstance(self.params[k], int):
                                self.params[k] = int(v)
                            elif isinstance(self.params[k], float):
                                self.params[k] = float(v)
                            else:
                                self.params[k] = v
            except Exception as e:
                print(f"Error loading configuration: {e}")

    def save_config(self):
        import os
        import json
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config_gearbox.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(self.params, f, indent=4)
        except Exception as e:
            print(f"Error saving configuration: {e}")

    def update_gui_from_params(self):
        """Update slider and checkbox states in the GUI to match self.params."""
        for key, (slider, scale, is_int) in self.sliders.items():
            slider.blockSignals(True)
            if is_int:
                slider.setValue(int(self.params[key]))
            else:
                slider.setValue(int(self.params[key] * scale))
            slider.blockSignals(False)
            
            if key in self.labels:
                label, name = self.labels[key]
                label.setText(f"{name}: {self.params[key]}")
        
        self.outer_ring_checkbox.blockSignals(True)
        self.outer_ring_checkbox.setChecked(self.params['show_outer_ring'])
        self.outer_ring_checkbox.blockSignals(False)
        
        self.balance_disk_checkbox.blockSignals(True)
        self.balance_disk_checkbox.setChecked(self.params['show_balance_disk'])
        self.balance_disk_checkbox.blockSignals(False)

    def add_slider(self, layout, name, key, min_val, max_val, step, is_int=False):
        label = QtWidgets.QLabel(f"{name}: {self.params[key]}")
        self.labels[key] = (label, name)
        
        slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        
        if is_int:
            slider.setMinimum(int(min_val))
            slider.setMaximum(int(max_val))
            slider.setValue(int(self.params[key]))
            slider.setSingleStep(int(step))
            scale = 1
        else:
            scale = int(1 / step)
            slider.setMinimum(int(min_val * scale))
            slider.setMaximum(int(max_val * scale))
            slider.setValue(int(self.params[key] * scale))

        self.sliders[key] = (slider, scale, is_int)

        def update(v):
            if is_int:
                value = v
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
            self.save_config()

        slider.valueChanged.connect(update)

        layout.addWidget(label)
        layout.addWidget(slider)

    def toggle_outer_ring(self, state):
        """Toggle outer ring visibility"""
        self.params['show_outer_ring'] = bool(state)
        self.update_viewer()
        self.save_config()

    def toggle_balance_disk(self, state):
        """Toggle balance disk (180 deg phase-offset second disk) visibility"""
        self.params['show_balance_disk'] = bool(state)
        self.update_viewer()
        self.save_config()

    def export_dxf(self):
        """Export current geometry to DXF file"""
        pins_num = self.params['num_external_pins']
        ring_radius = self.params['ring_diameter'] / 2
        radius_str = f"{int(ring_radius)}" if ring_radius.is_integer() else f"{ring_radius:.2f}".rstrip('0').rstrip('.')
        default_filename = f"cycloidal_gearbox_{pins_num}pins_{radius_str}mm.dxf"
        
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export to DXF",
            default_filename,
            "DXF Files (*.dxf)"
        )
        
        if filename:
            try:
                export_to_dxf(filename, self.params, self.phi, disk_variant="primary")
                exported_files = [filename]

                if self.params.get('show_balance_disk'):
                    balance_filename = self._make_balance_filename(filename)
                    export_to_dxf(balance_filename, self.params, self.phi, disk_variant="balance")
                    exported_files.append(balance_filename)

                layer_note = (
                    "- EXTERNAL_PINS\n"
                    "- CYCLOID_DISK\n"
                    "- OUTPUT_PINS\n"
                    "- OUTPUT_HOLES\n"
                    "- CAMSHAFT_HOLE\n"
                    "- ECCENTRIC_SHAFT\n"
                    "- OUTER_RING (if enabled)\n"
                )

                if len(exported_files) == 1:
                    msg = f"Geometry exported to:\n{exported_files[0]}\n\nLayers:\n{layer_note}"
                else:
                    msg = (
                        f"Two separate files were exported so the disks don't overlap in CAD:\n\n"
                        f"Disk 1:\n{exported_files[0]}\n\n"
                        f"Balance disk (180° offset):\n{exported_files[1]}\n\n"
                        f"Each file contains the ring pins, output pins, camshaft hole, and outer "
                        f"ring for reference, plus that file's own CYCLOID_DISK / OUTPUT_HOLES / "
                        f"ECCENTRIC_CAM layers:\n{layer_note}"
                    )

                QtWidgets.QMessageBox.information(
                    self,
                    "Export Successful",
                    msg
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

    @staticmethod
    def _make_balance_filename(filename):
        """Given 'foo.dxf', returns 'foo_balance_disk.dxf' (or 'foo_balance_disk' if no
        extension was present)."""
        if '.' in filename.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]:
            base, _, ext = filename.rpartition('.')
            return f"{base}_balance_disk.{ext}"
        return f"{filename}_balance_disk"
    
    def export_svg(self):
        """Export current geometry to SVG file"""
        pins_num = self.params['num_external_pins']
        ring_radius = self.params['ring_diameter'] / 2
        radius_str = f"{int(ring_radius)}" if ring_radius.is_integer() else f"{ring_radius:.2f}".rstrip('0').rstrip('.')
        default_filename = f"cycloidal_gearbox_{pins_num}pins_{radius_str}mm.svg"
        
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export to SVG",
            default_filename,
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
        
        self.update_gui_from_params()
        self.update_viewer()
        self.save_config()

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
            'input_shaft_diameter': 20.0,
            'animation_speed': 200,
            'tolerance': 0.2,
            'show_outer_ring': False,
            'outer_ring_width': 15.0,
            'show_balance_disk': False
        }
        self.params.update(defaults)
        self.phi = 0
        
        self.update_gui_from_params()
        self.viewer.rebuild_items(self.params['num_external_pins'], self.params['num_output_pins'])
        self.update_viewer()
        self.save_config()

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
            self.params['input_shaft_diameter'],
            self.params['tolerance'],
            self.params['show_outer_ring'],
            self.params['outer_ring_width'],
            self.phi,
            self.params['show_balance_disk']
        )

    def advance_animation(self):
        """Advance animation by one frame"""
        if not self.paused:
            self.phi += 0.01 * (self.params['animation_speed'] / 60)
            self.update_viewer()


# MAIN WINDOW 

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


# RUN 

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
