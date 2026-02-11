# Cycloidal Gearbox Generator
this was made when i tried to make a cycloidal profile in onshape but did not get the right parameter easily, and also was hard to make adjustments so yeah here is this:

A parametric design tool for creating and visualizing cycloidal gearboxes with real-time 3D preview and CAD export capabilities.


![Version](https://img.shields.io/badge/version-1.5-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Overview

This application allows you to design custom cycloidal gearboxes through an intuitive interface with interactive parameter sliders and real-time 3D visualization. Export your designs directly to DXF or SVG formats for 3d printing or whatever

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

## the view

The application displays: still want to add option to change colors maybe
- **Gray**: External pins (fixed)
- **Red**: Cycloidal disk (primary moving component)
- **Green**: Output pins (rotate with reduced speed)
- **Magenta**: Output pin holes in the disk
- **Blue**: Camshaft hole (center mounting)
- **Yellow/Orange**: Eccentric camshaft (drives the disk)
- **Gray outline**: Optional outer ring housing

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
python cycloidal_Gear_generator_V1-2.py
```

## Usage Guide

### Basic Parameters

1. **Animation Speed**: Controls rotation speed of the animation (1-2000)
2. **Eccentricity**: Offset distance that creates the cycloidal motion (0.5-10mm)
3. **External Pins**: Number of fixed pins in the ring (3-100, must be even)
4. **External Pin Diameter**: Size of the fixed pins (2-25mm)
5. **Ring Diameter**: Overall diameter of the pin circle (20-250mm)

### Output Configuration

6. **Output Pins**: Number of pins that transfer motion (3-45)
7. **Output Pin Diameter**: Size of output pins (0.5-25mm)
8. **Output Disk Diameter**: Diameter of the output pin circle (1-150mm)
9. **Camshaft Diameter**: Central shaft diameter (1-50mm)

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

## Design Tips

### Choosing Reduction Ratio

The gear reduction ratio is calculated as:
```
Reduction Ratio = num_external_pins / (num_external_pins - 1)
```

Examples:
- 24 external pins = 24:1 reduction
- 36 external pins = 36:1 reduction
- 48 external pins = 48:1 reduction

### Optimal Parameter Relationships

1. **Pin Size vs Ring Diameter**: Pins should be 5-10% of ring diameter
2. **Eccentricity**: Typically 1-3mm for small gearboxes, 3-8mm for larger ones
3. **Output Disk**: Should be 60-70% of ring diameter
4. **Tolerance**: Start with 0.15-0.25mm for 3D printing, 0.05-0.15mm for CNC



## Technical Details

### Cycloid Mathematics

The cycloidal disk profile is generated using parametric equations:

```python
# Rolling circle radius
rolling_radius = (num_lobes / (num_lobes + 1)) × ring_radius

# Stationary circle radius
stationary_radius = ring_radius / (num_lobes + 1)

# Cycloid curve with pin offset
x = (R_r + R_s) × cos(t) - e × cos((R_r + R_s)/R_s × t) + offset
y = (R_r + R_s) × sin(t) - e × sin((R_r + R_s)/R_s × t) + offset
```

Where:
- `num_lobes = num_external_pins - 1`
- `e` = eccentricity
- `t` = parameter (0 to 2π)


## Version History

### Version 1.5 (Current)
- Performance optimizations for CAD export
- Merged silhouette of pins and housing
- Cleaner geometry for CAD extrusion

### Version 1.4
- Added DXF export support
- Added SVG export support
- Layer-organized geometry
- Animation position export

### Version 1.3
- Continuous cycloid disk loop
- Added tolerance slider
- Optional outer ring housing
- Adjustable ring width

### Version 1.2
- Normalize to external pins function
- Improved variable naming
- Better slider organization

### Version 1.1
- Initial release with 3D viewer
- Basic parameter controls

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
