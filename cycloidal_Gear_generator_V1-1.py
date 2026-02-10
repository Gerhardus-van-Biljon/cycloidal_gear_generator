import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl

# =================== MATH FUNCTIONS ===================

def pin_ring(N, D, d):
    t = np.linspace(0, 2*np.pi, 200)
    pins = []
    for i in range(N):
        x = d/2*np.sin(t) + D/2*np.cos(2*np.pi*i/N)
        y = d/2*np.cos(t) + D/2*np.sin(2*np.pi*i/N)
        pins.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return pins


def inner_pins(n, N, rd, Rd, phi):
    t = np.linspace(0, 2*np.pi, 200)
    num = N - 1  # Number of lobes = N-1
    pins = []
    for i in range(n):
        x = (rd*np.sin(t)+Rd*np.cos(2*np.pi*i/n))*np.cos(-phi/num) - (rd*np.cos(t)+Rd*np.sin(2*np.pi*i/n))*np.sin(-phi/num)
        y = (rd*np.sin(t)+Rd*np.cos(2*np.pi*i/n))*np.sin(-phi/num) + (rd*np.cos(t)+Rd*np.sin(2*np.pi*i/n))*np.cos(-phi/num)
        pins.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return pins


def inner_circles(e, n, N, rd, Rd, phi):
    t = np.linspace(0, 2*np.pi, 200)
    num = N - 1  # Number of lobes = N-1
    circles = []
    for i in range(n):
        # Circle radius needs to be larger than pin by eccentricity amount
        # so the pin can orbit inside the hole
        # hole_radius = rd (pin radius) + e (eccentricity clearance)
        hole_radius = rd + e
        x = (hole_radius*np.cos(t)+Rd*np.cos(2*np.pi*i/n))*np.cos(-phi/num) - (hole_radius*np.sin(t)+Rd*np.sin(2*np.pi*i/n))*np.sin(-phi/num) + e*np.cos(phi)
        y = (hole_radius*np.cos(t)+Rd*np.cos(2*np.pi*i/n))*np.sin(-phi/num) + (hole_radius*np.sin(t)+Rd*np.sin(2*np.pi*i/n))*np.cos(-phi/num) + e*np.sin(phi)
        circles.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return circles


def cycloid_disk(e, N, D, d, phi):
    RD = D/2
    rd = d/2
    num = N - 1  # Number of lobes = N-1
    t1 = np.linspace(-np.pi/num, np.pi/num, 1500)

    # Corrected pitch circle calculations for N-1 lobes
    # The cycloid disk should roll inside the ring
    rc = (num/(num+1)) * RD  # Rolling circle radius
    rm = RD / (num+1)         # Stationary circle radius (pin circle)

    curves = []
    for i in range(num):
        xa = (rc+rm)*np.cos(t1) - e*np.cos((rc+rm)/rm*t1)
        ya = (rc+rm)*np.sin(t1) - e*np.sin((rc+rm)/rm*t1)

        dxa = (rc+rm)*(-np.sin(t1) + (e/rm)*np.sin((rc+rm)/rm*t1))
        dya = (rc+rm)*( np.cos(t1) - (e/rm)*np.cos((rc+rm)/rm*t1))

        xd = xa + rd/np.sqrt(dxa**2 + dya**2)*(-dya)
        yd = ya + rd/np.sqrt(dxa**2 + dya**2)*( dxa)

        x = xd*np.cos(i*2*np.pi/num - phi/num) - yd*np.sin(i*2*np.pi/num - phi/num) + e*np.cos(phi)
        y = xd*np.sin(i*2*np.pi/num - phi/num) + yd*np.cos(i*2*np.pi/num - phi/num) + e*np.sin(phi)

        curves.append(np.vstack([x, y, np.zeros_like(x)]).T)
    return curves


def camshaft(camshaft_d, phi):
    """Generate camshaft hole in the cycloid disk - this is the fixed outer boundary"""
    t = np.linspace(0, 2*np.pi, 200)
    # This is the hole in the cycloid disk - uses full camshaft_d
    x = camshaft_d/2 * np.cos(t)
    y = camshaft_d/2 * np.sin(t)
    return np.vstack([x, y, np.zeros_like(x)]).T


def eccentric_camshaft(e, camshaft_d, phi):
    """Generate eccentric shaft that orbits inside the camshaft hole"""
    t = np.linspace(0, 2*np.pi, 200)
    # The eccentric shaft diameter should be smaller than camshaft_d by 2*e
    # so it can orbit by distance e inside the hole
    shaft_radius = (camshaft_d - 2*e) / 2
    x = shaft_radius * np.cos(t) + e * np.cos(phi)
    y = shaft_radius * np.sin(t) + e * np.sin(phi)
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

    def rebuild_items(self, N, n):
        """Rebuild OpenGL items when N or n changes"""
        # Remove old items
        for item in self.outer_pin_items + self.inner_pin_items + self.inner_circle_items + self.cycloid_items:
            self.removeItem(item)

        # Create new items with lighter colors
        self.outer_pin_items = [gl.GLLinePlotItem(color=(0.4, 0.4, 0.4, 1), width=2) for _ in range(N)]
        self.inner_pin_items = [gl.GLLinePlotItem(color=(0.3, 0.9, 0.3, 1), width=2) for _ in range(n)]
        self.inner_circle_items = [gl.GLLinePlotItem(color=(0.9, 0.5, 0.9, 1), width=2) for _ in range(n)]
        self.cycloid_items = [gl.GLLinePlotItem(color=(1, 0.3, 0.3, 1), width=2.5) for _ in range(N)]

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

    def update_geometry(self, e, N, n, D, d, Rd, rd, camshaft_d, phi):
        """Update all geometry"""
        # Outer pins
        pins = pin_ring(N, D, d)
        for i, item in enumerate(self.outer_pin_items):
            if i < len(pins):
                item.setData(pos=pins[i])

        # Inner pins
        ip = inner_pins(n, N, rd, Rd, phi)
        for i, item in enumerate(self.inner_pin_items):
            if i < len(ip):
                item.setData(pos=ip[i])

        # Inner circles
        ic = inner_circles(e, n, N, rd, Rd, phi)
        for i, item in enumerate(self.inner_circle_items):
            if i < len(ic):
                item.setData(pos=ic[i])

        # Cycloid disk
        cd = cycloid_disk(e, N, D, d, phi)
        for i, item in enumerate(self.cycloid_items):
            if i < len(cd):
                item.setData(pos=cd[i])
        
        # Camshaft (stationary center)
        cam = camshaft(camshaft_d, phi)
        self.camshaft_item.setData(pos=cam)
        
        # Eccentric camshaft (rotating with cycloid disk)
        ecc_cam = eccentric_camshaft(e, camshaft_d, phi)
        self.eccentric_camshaft_item.setData(pos=ecc_cam)


# =================== SLIDER PANEL ===================

class SliderPanel(QtWidgets.QWidget):
    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer

        # Parameters
        self.params = {
            'e': 1.2,
            'N': 18,
            'n': 6,
            'D': 45.0,
            'd': 5.0,
            'Rd': 12.0,
            'rd': 1.5,
            'camshaft_d': 8.0,
            'speed': 60
        }
        self.phi = 0
        self.paused = False

        layout = QtWidgets.QVBoxLayout()

        # Title
        title = QtWidgets.QLabel("Cycloidal Gearbox Designer")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Add sliders
        self.add_slider(layout, "Eccentricity (e)", 'e', 0.5, 5.0, 0.1)
        self.add_slider(layout, "External Pins (N)", 'N', 6, 40, 1, is_int=True)
        self.add_slider(layout, "Output Pins (n)", 'n', 3, 15, 1, is_int=True)
        self.add_slider(layout, "Ring Diameter (D)", 'D', 20, 100, 1)
        self.add_slider(layout, "External Pin Dia (d)", 'd', 2, 15, 0.5)
        self.add_slider(layout, "Output Disk Dia (Rd)", 'Rd', 5, 30, 0.5)
        self.add_slider(layout, "Output Pin Dia (rd)", 'rd', 0.5, 5, 0.1)
        self.add_slider(layout, "Camshaft Dia", 'camshaft_d', 2, 20, 0.5)
        self.add_slider(layout, "Animation Speed", 'speed', 1, 200, 1, is_int=True)

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
        self.viewer.rebuild_items(self.params['N'], self.params['n'])
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
                # Round to nearest even number for N
                if key == 'N':
                    value = value if value % 2 == 0 else value + 1
            else:
                value = round(v / scale, 2)
            
            old_N = self.params.get('N')
            old_n = self.params.get('n')
            
            self.params[key] = value
            label.setText(f"{name}: {value}")
            
            # Rebuild items if N or n changed
            if key in ['N', 'n'] and (self.params['N'] != old_N or self.params['n'] != old_n):
                self.viewer.rebuild_items(self.params['N'], self.params['n'])
            
            self.update_viewer()

        slider.valueChanged.connect(update)

        layout.addWidget(label)
        layout.addWidget(slider)

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.setText("Resume Animation" if self.paused else "Pause Animation")

    def reset_params(self):
        defaults = {
            'e': 1.2, 'N': 18, 'n': 6, 'D': 45.0,
            'd': 5.0, 'Rd': 12.0, 'rd': 1.5, 'camshaft_d': 8.0, 'speed': 60
        }
        self.params.update(defaults)
        self.phi = 0
        
        # Update all slider displays
        for child in self.findChildren(QtWidgets.QLabel):
            for key, val in defaults.items():
                if key in child.text().lower():
                    child.setText(f"{child.text().split(':')[0]}: {val}")
        
        self.viewer.rebuild_items(self.params['N'], self.params['n'])
        self.update_viewer()

    def update_viewer(self):
        """Update the viewer with current parameters"""
        self.viewer.update_geometry(
            self.params['e'], self.params['N'], self.params['n'],
            self.params['D'], self.params['d'], self.params['Rd'],
            self.params['rd'], self.params['camshaft_d'], self.phi
        )

    def advance_animation(self):
        """Advance animation by one frame"""
        if not self.paused:
            self.phi += 0.01 * (self.params['speed'] / 60)
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