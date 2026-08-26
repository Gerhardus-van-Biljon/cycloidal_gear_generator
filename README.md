# Cycloidal Gearbox Generator
this was made when i tried to make a cycloidal profile in onshape but did not get the right parameter easily, and also was hard to make adjustments so yeah here is this:

A parametric design tool for creating and visualizing cycloidal gearboxes with real-time 3D preview and CAD export capabilities.


![Version](https://img.shields.io/badge/version-11.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Overview

<img width="1913" height="1027" alt="Screenshot 2026-08-25 123531" src="https://github.com/user-attachments/assets/01a04889-5096-4585-a76c-90ab1a3e3eee" />
<img width="1916" height="1026" alt="Screenshot 2026-08-25 123542" src="https://github.com/user-attachments/assets/25fdd452-6452-49a1-a8dd-80f593f2aa4b" />
<img width="1913" height="1025" alt="Screenshot 2026-08-25 123555" src="https://github.com/user-attachments/assets/c161e7c5-c313-495b-875e-9c604e412801" />

This application allows you to design custom cycloidal gearboxes through an intuitive interface with interactive parameter sliders and real-time 3D visualization. Export your designs directly to DXF or SVG formats for 3d printing or whatever

[example full design 20-1 ratio connected to a nema 17 stepper in onshape:](https://cad.onshape.com/documents/e6067050a8cc672fdf2bf5c1/w/24bbea19256e5ed42b9632d2/e/e50b16ec9ee2356670b31e9d)
### What is a Cycloidal Gearbox?

A cycloidal gearbox is a high-precision, high-torque gear reduction mechanism that uses a cycloidal disk rolling inside a ring of pins. These gearboxes offer:
- High gear reduction ratios in compact spaces
- Excellent torque transmission
- Minimal backlash
- Smooth operation
- Long service life

## Features

- **Real-time 3D Visualization**: Interactive OpenGL viewer showing all gearbox components
- **Parametric Design**: Adjust all dimensions with intuitive sliders
- **Manufacturing Tolerances**: Built-in tolerance settings for proper clearances
- **CAD Export**: Export to DXF and SVG formats for CNC machining or laser cutting i guess
- **Optimized Geometry**: Efficient point reduction for clean CAD imports
- **Complete Housing Design**: optional outer ring with pin pockets (can be improved)
- **Animation Control**: Pause/resume animation to examine specific positions

## The View

The application displays the following color-coded components:
- **Gray**: External pins (fixed)
- **Red**: Cycloidal disk (primary moving component)
- **Green**: Output pins (rotate with reduced speed)
- **Magenta**: Output pin holes in the disk
- **Blue**: Camshaft hole (center mounting)
- **Yellow/Orange**: Eccentric camshaft (drives the disk)
- **Gray outline**: Optional outer ring housing
- **Orange (Dotted)**: Balance disk (180° offset second disk, if enabled)
- **Purple (Dotted)**: Balance disk output holes (if enabled)
- **Pink (Dotted)**: Balance disk eccentric camshaft (if enabled)

## Installation

### Requirements

- Python 3.8 or higher
- PyQt6
- PyQtGraph
- NumPy
- OpenGL
- ezdxf (for DXF export)

### Install Dependencies

```bash
# Basic requirements
pip install PyQt6 pyqtgraph numpy PyOpenGL

# For DXF export capability
pip install ezdxf --break-system-packages
```

### Run the Application

```bash
python V11.py
```

## Usage Guide

### Basic Parameters

1. **Animation Speed**: Controls rotation speed of the animation (1-2000)
2. **Eccentricity**: Offset distance that creates the cycloidal motion (0.5-10mm)
3. **External Pins**: Number of fixed pins in the ring (3-100)
4. **External Pin Diameter**: Size of the fixed pins (2-25mm)
5. **Ring Diameter**: Overall diameter of the pin circle (20-250mm)

### Output Configuration

6. **Output Pins**: Number of pins that transfer motion (3-45)
7. **Output Pin Diameter**: Size of output pins (0.5-25mm)
8. **Output Disk Diameter**: Diameter of the output pin circle (1-150mm)
9. **Input Shaft Diameter**: Central input shaft diameter (1-50mm)

### Manufacturing Settings

10. **Tolerance**: Clearance between parts (0.01-2.0mm)
    - Increases hole sizes
    - Reduces disk size
    - Ensures parts don't bind

11. **Show Outer Ring**: Toggle housing ring display
12. **Outer Ring Width**: Thickness of housing wall (1-50mm)

### Design Tools

#### Normalize to External Pins
Automatically calculates a ring and disk diameters based on:
- Number of external pins
- Pin diameter
- makes the design process easyer if you want to change the gear ratios
Formula used:
```
Ring Diameter = ((pin_diameter × num_pins) + (1.25 × pin_diameter) × (num_pins - 1)) / π
Output Disk Diameter = (2/3) × Ring Diameter
```

#### Export Functions

**Export DXF** (for CAD software):
- Compatible with AutoCAD, SolidWorks, Fusion 360, FreeCAD
- Organized in named layers for easy manipulation
- Optimized geometry with reduced point count (can be improved)
- Merged housing profile for clean extrusion

**Export SVG** (for laser cutting):
- Vector format for Inkscape, Illustrator
- Color-coded components
- Scalable for any size manufacturing

**Layers in DXF Export**:
- `CYCLOID_DISK` (Red) - Main disk profile
- `OUTPUT_PINS` (Green) - Output pin positions
- `OUTPUT_HOLES` (Magenta) - Holes in the disk
- `CAMSHAFT_HOLE` (Blue) - Center mounting hole
- `ECCENTRIC_CAM` (Yellow) - Eccentric shaft profile
- `OUTER_RING` (Gray) - Housing with pin pockets
- `PIN_CENTERS` (White) - External pin drill points
- `CENTER_AXIS` (Cyan) - Center reference

## How it looks in CAD

<img width="1085" height="658" alt="Screenshot 2026-08-25 123711" src="https://github.com/user-attachments/assets/5dd1d3fe-ea06-4e57-893a-bf709217b3be" />
<img width="1042" height="671" alt="Screenshot 2026-08-25 123736" src="https://github.com/user-attachments/assets/b5d52f04-cfbe-44fe-9e10-e2f03c57d960" />
<img width="288" height="683" alt="Screenshot 2026-08-25 123903" src="https://github.com/user-attachments/assets/5fb63264-cfce-4db9-b7ee-a2f9bf7569fa" />

## Design Tips

### Choosing Reduction Ratio

The gear reduction ratio is determined by the number of external pins. Since the number of lobes on the cycloid disk is always `num_external_pins - 1`, the gearbox reduction ratio is:
```
Reduction Ratio = (num_external_pins - 1) : 1
```

Examples:
- 25 external pins (24 lobes) = 24:1 reduction
- 37 external pins (36 lobes) = 36:1 reduction
- 49 external pins (48 lobes) = 48:1 reduction

### Optimal Parameter Relationships

1. **Pin Size vs Ring Diameter**: Pins should be 5-10% of ring diameter
2. **Eccentricity**: Typically 1-3mm for small gearboxes, 3-8mm for larger ones
3. **Output Disk**: Should be 60-70% of ring diameter
4. **Tolerance**: Start with 0.15-0.25mm for 3D printing, 0.05-0.15mm for CNC



## Technical Details

### Cycloid Mathematics

The cycloidal disk profile is generated using the following parametric equations:

```python
# Rolling circle and stationary circle radii
rolling_circle_radius = (num_lobes / (num_lobes + 1)) * ring_radius
stationary_circle_radius = ring_radius / (num_lobes + 1)

# Base hypocycloid curve coordinates
xa = (rolling_circle_radius + stationary_circle_radius) * cos(t) - e * cos((rolling_circle_radius + stationary_circle_radius) / stationary_circle_radius * t)
ya = (rolling_circle_radius + stationary_circle_radius) * sin(t) - e * sin((rolling_circle_radius + stationary_circle_radius) / stationary_circle_radius * t)

# First derivatives for normal offset calculation
dxa = (rolling_circle_radius + stationary_circle_radius) * (-sin(t) + (e / stationary_circle_radius) * sin((rolling_circle_radius + stationary_circle_radius) / stationary_circle_radius * t))
dya = (rolling_circle_radius + stationary_circle_radius) * (cos(t) - (e / stationary_circle_radius) * cos((rolling_circle_radius + stationary_circle_radius) / stationary_circle_radius * t))

# Offset by the pin radius (plus tolerance clearance) to generate the outer disk surface
effective_pin_radius = pin_radius + tolerance
x_disk = xa + effective_pin_radius / sqrt(dxa**2 + dya**2) * (-dya)
y_disk = ya + effective_pin_radius / sqrt(dxa**2 + dya**2) * dxa
```

Where:
- `num_lobes = num_external_pins - 1`
- `e` = eccentricity
- `t` = parameter (0 to 2π)


## Version History

### Version 11.0 (Current)
- **Standardized CAD Export Orientation**: DXF and SVG exports now always use a fixed crank angle of -90 degrees (-pi/2) so the primary disk always points down (270 deg) and the balance disk points up (90 deg), ensuring consistent alignments regardless of animation state.

### Version 10.0
- **Restructured Camshaft/Eccentric Lobe Geometry**: The eccentric lobe (the ring inside the camshaft hole of the disk) is now modeled as the larger diameter and the central input shaft as the smaller one.
- **Improved UI Sliders**: The slider panel now directly controls the "Input Shaft Diameter" instead of the eccentric lobe outer diameter.
- **Accurate Tolerances**: Corrected tolerance clearance representation for the offset camshaft hole in the cycloid disk.

### Version 9.0
- **Standardized Output File Naming**: Updated default DXF/SVG filenames to `"cycloidal_gearbox_{pins}pins_{radius}mm"` (e.g., `cycloidal_gearbox_24pins_40mm.dxf`).

### Version 1.7
- **Separate DXF Exports**: The balance disk is now exported to a separate file (e.g. `*_balance_disk.dxf`) to prevent overlapping layers from colliding inside CAD software.

### Version 1.6
- **Optional Balance Disk**: Added a second cycloid disk mounted 180 degrees out of phase (`phi + pi`) on the eccentric shaft to cancel rotating vibrations.
- **Hole Phase Correction**: Introduced an extra local rotation phase of `pi / num_lobes` so the balance disk output holes align perfectly with the shared output pin set.

### Version 1.5
- Performance optimizations for CAD export.
- Merged silhouette of pins and housing.
- Cleaner geometry for CAD extrusion.

### Version 1.4
- Added DXF export support.
- Added SVG export support.
- Layer-organized geometry.
- Animation position export.

### Version 1.3
- Continuous cycloid disk loop.
- Added tolerance slider.
- Optional outer ring housing.
- Adjustable ring width.

### Version 1.2
- Normalize to external pins function.
- Improved variable naming.
- Better slider organization.

### Version 1.1
- Initial release with 3D viewer.
- Basic parameter controls.

## Troubleshooting

### Common Issues

**Application won't start**
```bash
# Check Python version
python --version  # Should be 3.8+

# Reinstall dependencies
pip install --upgrade PyQt6 pyqtgraph numpy PyOpenGL
```

**DXF export fails**
```bash
# Install ezdxf
pip install ezdxf --break-system-packages
```

**Geometry looks incorrect**
- Check that external pins is an even number
- Ensure eccentricity < pin diameter
- Verify tolerance isn't too large
- Try "Reset to Defaults" button

**Parts don't fit together**
- Increase tolerance (0.2-0.3mm for 3D printing)
- Check that holes are larger than pins
- Verify eccentricity matches design

## Contributing

Contributions are welcome! Areas for improvement:
- Additional export formats (STEP, IGES)
- Strength analysis tools
- Material selection guidance
- Assembly instructions generator
- Multi-stage gearbox design
- more customization for chosing colors
- better housing ring geometry calculations / variations

## Author

**Gerhardus van Biljon**

## License

This project is open source and available under the MIT License.

## Acknowledgments
- [@tamato_1107 on Youtube for the idea of modeling it in python](https://youtube.com/shorts/73DANPATrQU?si=pQQuMwgBrV7yK-sT)
- [Dajan form how to Mechatronics, for inspiration for size of my first CAD design](https://howtomechatronics.com/projects/cnc-machined-vs-3d-printed-cycloidal-drive-designing-testing/#cycloidal-drive-191-ratio-stl-files)
- [RoTechnic's video also inspiration and understanding of how to model](https://youtu.be/r2TWC7vTdvs?si=ZUQ2BDLxWgYFLBEo)
- Based on cycloidal gear theory and hypocycloid mathematics
- Uses PyQt6 for GUI framework
- OpenGL rendering via PyQtGraph
- DXF export using ezdxf library

## Support

For issues, questions, or suggestions:
1. Check the troubleshooting section
2. Review parameter relationships
3. Try the "Normalize to External Pins" feature
4. Export and inspect in CAD software

## Further Reading

- [Cycloidal Drive Wikipedia](https://en.wikipedia.org/wiki/Cycloidal_drive)
- [Hypocycloid Mathematics](https://mathworld.wolfram.com/Hypocycloid.html)


---

**Happy Designing! 🔧⚙️**
