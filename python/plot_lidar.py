import os
import sys
import serial
import serial.tools.list_ports
import pygame
import time
import math
from collections import deque
from datetime import datetime

# ===== SETTINGS =====
def find_arduino_port():
    """AUTO-DETECT ARDUINO COM PORT"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description.upper() for keyword in 
               ['ARDUINO', 'CH340', 'CH341', 'FTDI', 'USB-SERIAL']):
            return port.device
    
    # TRY COMMON PORTS IF NO ARDUINO FOUND
    for port_name in ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8']:
        try:
            test_port = serial.Serial(port_name, 9600, timeout=1)
            test_port.close()
            return port_name
        except:
            continue
    return None

BAUD = 9600
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1177, 630
MIN_WIDTH, MIN_HEIGHT = 1177, 630
WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT

# DYNAMIC CENTER CALCULATION
def get_center():
    return WIDTH // 2 - 122, int(HEIGHT // 1.4) + PADDING_TOP

MAX_CM = 70
SCALE = 5                    
MAP_SMOOTH_N = 3             # REDUCED for more responsive mapping
BEAM_SMOOTH_N = 2            

# COLORS
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
LIGHT_GREEN = (100, 255, 100)
DARK_GREEN = (0, 180, 0)
RED = (255, 50, 50)
GRAY = (60, 60, 60)
LIGHT_GRAY = (120, 120, 120)
DARK_GRAY = (30, 30, 30)
BLUE = (100, 150, 255)
ORANGE = (255, 165, 0)
PURPLE = (200, 100, 255)
CYAN = (0, 255, 255)

PADDING_TOP = 30

# 3D RENDERING SETTINGS
VIEW_MODE_2D = 0
VIEW_MODE_3D = 1
view_mode = VIEW_MODE_2D

# 3D Camera settings
camera_angle_x = -30  # Tilt down to see the surface
camera_angle_y = 0    # Rotation around Y axis
camera_distance = 400 # Distance from center
camera_height = 200   # Height above the scan plane
auto_rotate = True    # Auto rotate in 3D mode

# ===== SERIAL =====
PORT = find_arduino_port()
if PORT is None:
    print("No Arduino found! Check connection and drivers.")
    input("Press Enter to exit...")
    exit()

print(f"Arduino found on {PORT}")
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

# ===== RESOURCE PATH HELPER =====
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ===== PYGAME SETUP WITH IMPROVED ICON HANDLING =====
pygame.init()

os.environ['SDL_VIDEO_WINDOW_POS'] = 'centered'

def find_icon_files():
    """FIND BOTH ICO AND PNG FILES WITH COMPREHENSIVE SEARCH"""
    icon_files = {'ico': None, 'png': None}
    
    search_paths = [
        os.getcwd(),  
        os.path.dirname(os.path.abspath(__file__)),  
        resource_path(""),  
        os.path.join(os.getcwd(), "assets"),  
        os.path.join(os.path.dirname(__file__), "assets"),  
    ]
    
    ico_names = ["objectscanner4.ico", "icon.ico", "app.ico"]
    png_names = ["objectscanner4.png", "icon.png", "app.png"]
    
    # SEARCH FOR ICO FILES
    for path in search_paths:
        if icon_files['ico']:
            break
        for filename in ico_names:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                icon_files['ico'] = full_path
                print(f"Found ICO file: {full_path}")
                break
    
    # SEARCH FOR PNG FILES
    for path in search_paths:
        if icon_files['png']:
            break
        for filename in png_names:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                icon_files['png'] = full_path
                print(f"Found PNG file: {full_path}")
                break
    
    return icon_files

def setup_window_icon(icon_files):
    """SETUP WINDOW TAB ICON (PREFERS ICO, FALLBACK TO PNG)"""
    try:
        if icon_files['ico']:
            try:
                icon_surface = pygame.image.load(icon_files['ico'])
                pygame.display.set_icon(icon_surface)
                print("[SUCCESS] Window icon set successfully (ICO)")
                return True
            except Exception as e:
                print(f"Failed to load ICO file: {e}")
        
        if icon_files['png']:
            try:
                icon_surface = pygame.image.load(icon_files['png'])
                pygame.display.set_icon(icon_surface)
                print("[SUCCESS] Window icon set successfully (PNG fallback)")
                return True
            except Exception as e:
                print(f"Failed to load PNG file: {e}")
        
        print("[ERROR] No suitable icon file found for window")
        return False
        
    except Exception as e:
        print(f"Window icon setup failed: {e}")
        return False

def setup_taskbar_icon(icon_files):
    """SETUP TASKBAR ICON (USES PNG FOR BETTER COMPATIBILITY)"""
    try:
        import ctypes
        from ctypes import wintypes
        
        app_id = 'surroundsense.radar.scanner.v1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
            print("[SUCCESS] App ID set for taskbar grouping")
        except Exception as e:
            print(f"Failed to set app ID: {e}")
        
        if not icon_files['png']:
            print("[ERROR] No PNG file available for taskbar icon")
            return False
        
        png_path = os.path.abspath(icon_files['png'])
        
        hwnd = pygame.display.get_wm_info()["window"]
        
        # WINDOWS API CONSTANTS
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        
        hicon_small = ctypes.windll.user32.LoadImageW(
            None, png_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
        )
        hicon_big = ctypes.windll.user32.LoadImageW(
            None, png_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE
        )
        
        success = False
        if hicon_small:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
            success = True
        
        if hicon_big:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
            success = True
        
        if success:
            print("[SUCCESS] Taskbar icon set successfully (PNG)")
            return True
        else:
            print("[ERROR] Failed to load PNG as taskbar icon")
            return False
            
    except ImportError:
        print("Not on Windows - taskbar icon setup skipped")
        return False
    except Exception as e:
        print(f"Taskbar icon setup failed: {e}")
        return False

def setup_all_icons():
    """SETUP BOTH WINDOW AND TASKBAR ICONS"""
    print("Setting up application icons...")
    
    icon_files = find_icon_files()
    
    if not icon_files['ico'] and not icon_files['png']:
        print("[WARNING] No icon files found!")
        print("   Expected files: objectscanner4.ico and/or objectscanner4.png")
        return False, False
    
    window_success = setup_window_icon(icon_files)
    
    return window_success, icon_files

window_icon_success, icon_files = setup_all_icons()

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("SurroundSense")

def setup_taskbar_post_display():
    """SETUP TASKBAR ICON AFTER DISPLAY IS CREATED"""
    if icon_files and icon_files['png']:
        taskbar_success = setup_taskbar_icon(icon_files)
        return taskbar_success
    return False

taskbar_success = setup_taskbar_post_display()

print(f"[{'OK' if window_icon_success else 'FAIL'}] Window icon: {'Success' if window_icon_success else 'Failed'}")
print(f"[{'OK' if taskbar_success else 'FAIL'}] Taskbar icon: {'Success' if taskbar_success else 'Failed/Skipped'}")

clock = pygame.time.Clock()
font_small = pygame.font.SysFont('Arial', 14)
font_medium = pygame.font.SysFont('Arial', 16, bold=True)
font_large = pygame.font.SysFont('Arial', 20, bold=True)

# WINDOW STATE
minimized = False
fullscreen = False
MINI_WIDTH, MINI_HEIGHT = 400, 300

# SCREENSHOT STATE
screenshot_message = ""
screenshot_timer = 0
taking_screenshot = False  # NEW FLAG TO TRACK SCREENSHOT PROCESS

# ===== STATE =====
map_yaw_hist = deque(maxlen=MAP_SMOOTH_N)
beam_yaw_hist = deque(maxlen=BEAM_SMOOTH_N)

sensor = {
    "distance_raw": 0.0,
    "yaw_raw": 90.0,
    "yaw_instant": 90.0,
    "direction": "Stationary",
    "object": "None",
    "gyro": "Still",
}

# IMPROVED DISTANCE HANDLING - USE RAW DISTANCES FOR ACCURACY
current_distance = 0.0  # CURRENT RAW DISTANCE FROM SENSOR
beam_distance = 0.0     # DISTANCE FOR BEAM DISPLAY
calibrated = False
yaw_offset = 0.0
scan_active = False  # SCANNING AND BEAM ONLY ACTIVE AFTER FIRST R PRESS
scan_points = {}  # angle -> {'coord': (x,y), 'has_object': bool, 'distance': float}

# ===== 3D MATH HELPERS =====
def rotate_point_3d(x, y, z, angle_x, angle_y, angle_z=0):
    """Rotate a 3D point around all three axes"""
    # Convert angles to radians
    ax, ay, az = math.radians(angle_x), math.radians(angle_y), math.radians(angle_z)
    
    # Rotation around X axis
    y1 = y * math.cos(ax) - z * math.sin(ax)
    z1 = y * math.sin(ax) + z * math.cos(ax)
    y, z = y1, z1
    
    # Rotation around Y axis
    x1 = x * math.cos(ay) + z * math.sin(ay)
    z1 = -x * math.sin(ay) + z * math.cos(ay)
    x, z = x1, z1
    
    # Rotation around Z axis
    x1 = x * math.cos(az) - y * math.sin(az)
    y1 = x * math.sin(az) + y * math.cos(az)
    x, y = x1, y1
    
    return x, y, z

def project_3d_to_2d(x, y, z, camera_distance=400):
    """Project 3D point to 2D screen coordinates with perspective"""
    if z + camera_distance <= 0:
        return None, None
    
    CENTER_X, CENTER_Y = get_center()
    
    # Perspective projection
    scale_factor = camera_distance / (z + camera_distance)
    screen_x = CENTER_X + x * scale_factor
    screen_y = CENTER_Y - y * scale_factor  # Negative because screen Y increases downward
    
    return int(screen_x), int(screen_y)

def generate_3d_surface_mesh():
    """Generate 3D mesh from scan points for extruded surface"""
    if not scan_points:
        return []
    
    vertices = []
    triangles = []
    
    # Create vertices for the scanned surface
    angles = sorted(scan_points.keys())
    extrusion_height = 50  # Height of extrusion in 3D space
    
    # Base vertices (on the scan plane)
    base_vertices = []
    top_vertices = []
    
    for angle in angles:
        data = scan_points[angle]
        if data['has_object']:
            # Convert polar to cartesian (relative to center)
            distance = data['distance'] * SCALE * 0.3  # Scale down for 3D
            angle_rad = math.radians(angle)
            
            x = distance * math.cos(angle_rad)
            z = distance * math.sin(angle_rad)  # Use Z as the depth axis
            
            # Base vertex (y = 0)
            base_vertices.append((x, 0, z))
            # Top vertex (y = extrusion_height)  
            top_vertices.append((x, extrusion_height, z))
    
    # Add center points
    center_base = (0, 0, 0)
    center_top = (0, extrusion_height, 0)
    
    vertices = [center_base, center_top] + base_vertices + top_vertices
    
    # Generate triangles for the surface
    if len(base_vertices) >= 2:
        for i in range(len(base_vertices)):
            next_i = (i + 1) % len(base_vertices)
            
            # Base triangle (center to edge)
            triangles.append((0, 2 + i, 2 + next_i))
            
            # Top triangle (center to edge)  
            triangles.append((1, 2 + len(base_vertices) + next_i, 2 + len(base_vertices) + i))
            
            # Side quad (split into two triangles)
            base_current = 2 + i
            base_next = 2 + next_i
            top_current = 2 + len(base_vertices) + i
            top_next = 2 + len(base_vertices) + next_i
            
            # First triangle of quad
            triangles.append((base_current, base_next, top_current))
            # Second triangle of quad
            triangles.append((base_next, top_next, top_current))
    
    return vertices, triangles

def draw_3d_wireframe(vertices, triangles):
    """Draw 3D wireframe mesh"""
    if not vertices or not triangles:
        return
    
    # Transform and project vertices
    projected_vertices = []
    
    for x, y, z in vertices:
        # Apply camera rotation and position
        rx, ry, rz = rotate_point_3d(x, y, z, camera_angle_x, camera_angle_y)
        
        # Project to 2D
        screen_x, screen_y = project_3d_to_2d(rx, ry, rz - camera_distance)
        
        if screen_x is not None and screen_y is not None:
            projected_vertices.append((screen_x, screen_y))
        else:
            projected_vertices.append(None)
    
    # Draw triangles as wireframe
    for triangle in triangles:
        points = []
        valid = True
        
        for vertex_idx in triangle:
            if vertex_idx < len(projected_vertices) and projected_vertices[vertex_idx] is not None:
                points.append(projected_vertices[vertex_idx])
            else:
                valid = False
                break
        
        if valid and len(points) == 3:
            # Draw triangle edges
            for i in range(3):
                start_point = points[i]
                end_point = points[(i + 1) % 3]
                
                # Check if points are within screen bounds
                if (0 <= start_point[0] < WIDTH and 0 <= start_point[1] < HEIGHT and
                    0 <= end_point[0] < WIDTH and 0 <= end_point[1] < HEIGHT):
                    pygame.draw.line(screen, LIGHT_GREEN, start_point, end_point, 2)

def draw_3d_filled_surface(vertices, triangles):
    """Draw 3D filled surface with depth sorting"""
    if not vertices or not triangles:
        return
    
    # Transform vertices and calculate depths
    transformed_triangles = []
    
    for triangle_idx, triangle in enumerate(triangles):
        triangle_vertices = []
        triangle_z_values = []
        
        for vertex_idx in triangle:
            if vertex_idx < len(vertices):
                x, y, z = vertices[vertex_idx]
                
                # Apply camera rotation
                rx, ry, rz = rotate_point_3d(x, y, z, camera_angle_x, camera_angle_y)
                
                # Project to 2D
                screen_x, screen_y = project_3d_to_2d(rx, ry, rz - camera_distance)
                
                if screen_x is not None and screen_y is not None:
                    triangle_vertices.append((screen_x, screen_y))
                    triangle_z_values.append(rz)
                else:
                    triangle_vertices = []
                    break
        
        if len(triangle_vertices) == 3:
            avg_z = sum(triangle_z_values) / 3
            transformed_triangles.append((avg_z, triangle_vertices))
    
    # Sort triangles by depth (back to front)
    transformed_triangles.sort(key=lambda x: x[0], reverse=True)
    
    # Draw triangles
    for avg_z, triangle_vertices in transformed_triangles:
        # Color based on depth and surface type
        depth_factor = max(0.3, min(1.0, (avg_z + 200) / 400))
        
        # Use green tones for the extruded surface
        color_intensity = int(150 * depth_factor)
        surface_color = (0, color_intensity, int(color_intensity * 0.7))
        
        # Check if all vertices are on screen
        if all(0 <= x < WIDTH and 0 <= y < HEIGHT for x, y in triangle_vertices):
            pygame.draw.polygon(screen, surface_color, triangle_vertices)
            # Draw outline
            pygame.draw.polygon(screen, LIGHT_GREEN, triangle_vertices, 1)

# ===== HELPERS =====
def clamp(v, lo, hi): return max(lo, min(hi, v))
def movavg(buf, val): buf.append(val); return sum(buf)/len(buf)
def wrap360(a):
    while a < 0: a += 360
    while a >= 360: a -= 360
    return a

def parse_line(line):
    out = {}
    for part in line.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
    return out

def get_beam_angle(yaw_raw):
    y = yaw_raw - yaw_offset if calibrated else yaw_raw
    y = wrap360(y)
    if 0.0 <= y <= 180.0:
        reversed_y = 180 - y
        return movavg(beam_yaw_hist, reversed_y)
    return None

def get_map_angle(yaw_raw):
    y = yaw_raw - yaw_offset if calibrated else yaw_raw
    y = wrap360(y)
    if 0.0 <= y <= 180.0:
        reversed_y = 180 - y
        return movavg(map_yaw_hist, reversed_y)
    return None

def polar_to_xy(angle_deg, dist_cm):
    CENTER_X, CENTER_Y = get_center()
    r = dist_cm * SCALE
    a = math.radians(angle_deg)
    x = CENTER_X + r * math.cos(a)
    y = CENTER_Y - r * math.sin(a)
    return (int(x), int(y))

def get_downloads_folder():
    """GET THE USER'S DOWNLOADS FOLDER PATH ACROSS DIFFERENT OS"""
    try:
        # WINDOWS
        if os.name == 'nt':
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                downloads_path = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                if os.path.exists(downloads_path):
                    return downloads_path
            
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            if os.path.exists(downloads_path):
                return downloads_path
        
        # MACOS AND LINUX
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_path):
            return downloads_path
            
        return os.getcwd()
        
    except Exception:
        return os.getcwd()

def save_screenshot():
    """SAVE CURRENT SCREEN AS PNG WITH TIMESTAMP TO DOWNLOADS FOLDER"""
    global screenshot_message, screenshot_timer, taking_screenshot
    
    try:
        # SET FLAG TO HIDE INSTRUCTION TEXT DURING SCREENSHOT
        taking_screenshot = True
        
        # REDRAW SCREEN WITHOUT INSTRUCTION TEXT
        screen.fill(BLACK)
        if not minimized:
            if scan_active:
                if view_mode == VIEW_MODE_2D:
                    draw_radar_display()
                    draw_scan_data()
                    if beam_angle is not None:
                        draw_beam(beam_angle, beam_distance)
                else:
                    draw_3d_view()
            else:
                draw_idle_screen()
        draw_ui()
        pygame.display.flip()
        
        # SMALL DELAY TO ENSURE CLEAN RENDER
        pygame.time.wait(50)
        
        downloads_dir = get_downloads_folder()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        view_suffix = "3D" if view_mode == VIEW_MODE_3D else "2D"
        filename = f"SurroundSense_Radar_{view_suffix}_{timestamp}.png"
        filepath = os.path.join(downloads_dir, filename)
        
        pygame.image.save(screen, filepath)
        
        # RESET FLAG
        taking_screenshot = False
        
        screenshot_message = f"SUCCESS|Saved to Downloads: {filename}"
        screenshot_timer = pygame.time.get_ticks() + 4000
        
        print(f"Screenshot saved: {filepath}")
        return True
        
    except Exception as e:
        taking_screenshot = False
        screenshot_message = f"ERROR|Save failed: {str(e)[:50]}..."
        screenshot_timer = pygame.time.get_ticks() + 4000
        print(f"Screenshot save failed: {e}")
        return False

def draw_card(surface, x, y, w, h, title, content, title_color=WHITE, bg_color=(25, 25, 25)):
    w = max(w, 200)
    h = max(h, 80)
    
    card_rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, bg_color, card_rect, border_radius=12)
    pygame.draw.rect(surface, (70, 70, 70), card_rect, 2, border_radius=12)
    
    title_surf = font_medium.render(title, True, title_color)
    surface.blit(title_surf, (x + 15, y + 12))
    
    content_y = y + 35
    line_height = 16 if h < 100 else 18
    
    for line in content:
        if content_y + line_height > y + h - 10:
            break
        text_surf = font_small.render(line, True, WHITE)
        surface.blit(text_surf, (x + 15, content_y))
        content_y += line_height

def draw_radar_display():
    CENTER_X, CENTER_Y = get_center()
    
    # ARC BACKGROUND
    pygame.draw.arc(
        screen,
        (15, 15, 15),
        pygame.Rect(
            CENTER_X - (MAX_CM * SCALE + 10),
            CENTER_Y - (MAX_CM * SCALE + 10),
            2 * (MAX_CM * SCALE + 10),
            2 * (MAX_CM * SCALE + 10)
        ),
        math.radians(0),
        math.radians(180),
        10
    )

    # OUTER ARC BORDER
    pygame.draw.arc(
        screen,
        GRAY,
        pygame.Rect(
            CENTER_X - MAX_CM * SCALE,
            CENTER_Y - MAX_CM * SCALE,
            2 * MAX_CM * SCALE,
            2 * MAX_CM * SCALE
        ),
        math.radians(0),
        math.radians(180),
        2
    )

    # RANGE RINGS
    for r in [10, 20, 30, 40, 50, 60]:
        pygame.draw.arc(
            screen,
            DARK_GRAY,
            pygame.Rect(CENTER_X - r * SCALE, CENTER_Y - r * SCALE, r * SCALE * 2, r * SCALE * 2),
            math.radians(0),
            math.radians(180),
            1
        )

    # ANGLE LINES
    for angle in range(0, 181, 30):
        end_pos = polar_to_xy(angle, MAX_CM)
        color = LIGHT_GRAY if angle == 90 else DARK_GRAY
        width = 2 if angle == 90 else 1
        pygame.draw.line(screen, color, (CENTER_X, CENTER_Y), end_pos, width)

    # RANGE LABELS
    for r in [10, 20, 30, 40, 50, 60, 70]:
        label_pos = polar_to_xy(90, r)
        label = font_small.render(f"{r}cm", True, LIGHT_GRAY)
        screen.blit(label, (label_pos[0] - 12, label_pos[1] - 8))

    # ANGLE LABELS
    for angle in [0, 30, 60, 90, 120, 150, 180]:
        label_pos = polar_to_xy(angle, MAX_CM + 15)
        label = font_small.render(f"{angle}°", True, LIGHT_GRAY)
        label_rect = label.get_rect(center=label_pos)
        screen.blit(label, label_rect)
        
    # SCANNING INSTRUCTION TEXT - HIDDEN DURING SCREENSHOT OR WHEN SCREENSHOT MESSAGE IS SHOWING
    if scan_active and not screenshot_message and not taking_screenshot:
        instruction_text = font_large.render("Rotate the sensor very slow", True, GRAY)
        text_rect = instruction_text.get_rect(center=(CENTER_X, CENTER_Y + 50))
        screen.blit(instruction_text, text_rect)

def draw_3d_view():
    """Draw the 3D extruded view of the scanned area"""
    global camera_angle_y
    
    # Auto-rotate camera in 3D mode
    if auto_rotate:
        camera_angle_y += 0.5  # Slow rotation
        if camera_angle_y >= 360:
            camera_angle_y = 0
    
    # Generate 3D mesh from scan data
    vertices, triangles = generate_3d_surface_mesh()
    
    if vertices and triangles:
        # Draw filled surface
        draw_3d_filled_surface(vertices, triangles)
        
        # Draw wireframe overlay for better definition
        draw_3d_wireframe(vertices, triangles)
    
    # Draw 3D mode indicator
    CENTER_X, CENTER_Y = get_center()
    mode_text = font_large.render("3D VIEW - EXTRUDED SCAN DATA", True, CYAN)
    text_rect = mode_text.get_rect(center=(CENTER_X, CENTER_Y + 100))
    screen.blit(mode_text, text_rect)
    
    # Draw rotation indicator if auto-rotating
    if auto_rotate and not taking_screenshot:
        rotate_text = font_medium.render("Auto-rotating... Press T to toggle", True, LIGHT_GRAY)
        rotate_rect = rotate_text.get_rect(center=(CENTER_X, CENTER_Y + 130))
        screen.blit(rotate_text, rotate_rect)

def draw_scan_data():
    if not scan_points:
        return
    
    # DRAW CONTINUOUS DOTTED LINE CONNECTING ALL SCAN POINTS
    all_angles = sorted(scan_points.keys())
    if len(all_angles) > 1:
        for i in range(len(all_angles) - 1):
            angle1 = all_angles[i]
            angle2 = all_angles[i + 1]
            
            data1 = scan_points[angle1]
            data2 = scan_points[angle2]
            
            coord1 = data1['coord'] if data1['has_object'] else polar_to_xy(angle1, MAX_CM)
            coord2 = data2['coord'] if data2['has_object'] else polar_to_xy(angle2, MAX_CM)
            
            draw_dotted_line(coord1, coord2, GREEN, dot_size=1, spacing=2)

def draw_dotted_line(start_pos, end_pos, color, dot_size=1, spacing=2):
    """DRAW A FINE DOTTED LINE WITH NO GAPS BETWEEN TWO POINTS"""
    start_x, start_y = start_pos
    end_x, end_y = end_pos
    
    dx = end_x - start_x
    dy = end_y - start_y
    distance = math.sqrt(dx*dx + dy*dy)
    
    if distance == 0:
        return
    
    num_dots = int(distance / spacing) + 1
    for i in range(num_dots + 1):
        progress = i / max(num_dots, 1) if num_dots > 0 else 0
        dot_x = start_x + progress * dx
        dot_y = start_y + progress * dy
        pygame.draw.circle(screen, color, (int(dot_x), int(dot_y)), dot_size)

def draw_beam(angle_deg, dist_cm):
    if angle_deg is None:
        return
    
    CENTER_X, CENTER_Y = get_center()
    end_point = polar_to_xy(angle_deg, dist_cm)
    
    # BEAM LINE WITH GRADIENT EFFECT
    pygame.draw.line(screen, LIGHT_GREEN, (CENTER_X, CENTER_Y), end_point, 4)
    pygame.draw.line(screen, GREEN, (CENTER_X, CENTER_Y), end_point, 2)
    
    # TARGET INDICATOR
    if sensor["object"].lower() != "none" and dist_cm < MAX_CM:
        pygame.draw.circle(screen, RED, end_point, 12)
        pygame.draw.circle(screen, WHITE, end_point, 12, 3)
        pygame.draw.circle(screen, RED, end_point, 6)
    
    # CENTER SENSOR
    pygame.draw.circle(screen, WHITE, (CENTER_X, CENTER_Y), 8)
    pygame.draw.circle(screen, BLUE, (CENTER_X, CENTER_Y), 6)

def draw_idle_screen():
    """DRAW IDLE SCREEN WHEN SCAN IS NOT ACTIVE"""
    CENTER_X, CENTER_Y = get_center()
    
    # DRAW BASIC RADAR OUTLINE
    pygame.draw.arc(
        screen,
        (40, 40, 40),
        pygame.Rect(
            CENTER_X - MAX_CM * SCALE,
            CENTER_Y - MAX_CM * SCALE,
            2 * MAX_CM * SCALE,
            2 * MAX_CM * SCALE
        ),
        math.radians(0),
        math.radians(180),
        2
    )
    
    # CENTER DOT
    pygame.draw.circle(screen, GRAY, (CENTER_X, CENTER_Y), 4)
    
    # IDLE MESSAGE
    idle_text1 = font_large.render("WELCOME TO SURROUNDSENSE", True, GRAY)
    idle_text2 = font_medium.render("Press R and C to start scanning", True, LIGHT_GRAY)
    
    text1_rect = idle_text1.get_rect(center=(CENTER_X, CENTER_Y - 30))
    text2_rect = idle_text2.get_rect(center=(CENTER_X, CENTER_Y + 10))
    
    screen.blit(idle_text1, text1_rect)
    screen.blit(idle_text2, text2_rect)

def draw_screenshot_message():
    """DRAW SCREENSHOT SAVE STATUS MESSAGE"""
    global screenshot_message, screenshot_timer
    
    if screenshot_message and pygame.time.get_ticks() < screenshot_timer:
        msg_surface = font_medium.render(screenshot_message, True, BLACK)
        msg_rect = msg_surface.get_rect()
        
        card_width = max(300, msg_rect.width + 60)
        card_height = 80
        card_x = (WIDTH - card_width) // 2
        card_y = (HEIGHT - card_height) // 2
        
        if screenshot_message.startswith("SUCCESS|"):
            bg_color = (240, 255, 240)
            border_color = (100, 200, 100)
            title_color = (0, 120, 0)
        else:
            bg_color = (255, 240, 240)
            border_color = (200, 100, 100)
            title_color = (120, 0, 0)
        
        card_rect = pygame.Rect(card_x, card_y, card_width, card_height)
        pygame.draw.rect(screen, bg_color, card_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, card_rect, 3, border_radius=12)
        
        # SHADOW EFFECT
        shadow_rect = pygame.Rect(card_x + 3, card_y + 3, card_width, card_height)
        shadow_surface = pygame.Surface((card_width, card_height))
        shadow_surface.set_alpha(50)
        shadow_surface.fill((0, 0, 0))
        screen.blit(shadow_surface, shadow_rect.topleft)
        
        pygame.draw.rect(screen, bg_color, card_rect, border_radius=12)
        pygame.draw.rect(screen, border_color, card_rect, 3, border_radius=12)
        
        if screenshot_message.startswith("SUCCESS|"):
            title_text = "EXPORT SUCCESS"
        else:
            title_text = "EXPORT FAILED"
        
        title_surface = font_medium.render(title_text, True, title_color)
        title_x = card_x + 20
        title_y = card_y + 15
        screen.blit(title_surface, (title_x, title_y))
        
        display_message = screenshot_message.split("|", 1)[1] if "|" in screenshot_message else screenshot_message
        content_surface = font_small.render(display_message, True, BLACK)
        content_x = card_x + 20
        content_y = card_y + 45
        screen.blit(content_surface, (content_x, content_y))
        
    elif pygame.time.get_ticks() >= screenshot_timer:
        screenshot_message = ""

def draw_ui():
    if minimized:
        # MINIMIZED UI - COMPACT DISPLAY
        pygame.draw.rect(screen, (40, 40, 40), (0, 0, MINI_WIDTH, 30), border_radius=8)
        title = font_medium.render("Radar (Minimized)", True, WHITE)
        screen.blit(title, (10, 6))
        
        restore_btn = pygame.Rect(MINI_WIDTH - 35, 5, 25, 20)
        pygame.draw.rect(screen, (80, 80, 80), restore_btn, border_radius=4)
        pygame.draw.rect(screen, WHITE, (restore_btn.x + 8, restore_btn.y + 8, 9, 4))
        
        y_pos = 45
        scan_status = "SCANNING" if scan_active else "IDLE"
        scan_color = GREEN if scan_active else GRAY
        
        compact_data = [
            f"Status: {scan_status}",
            f"Distance: {current_distance:.1f}cm" if scan_active else "Distance: —",
            f"Angle: {get_beam_angle(sensor['yaw_instant']):.1f}°" if scan_active and get_beam_angle(sensor['yaw_instant']) else "Angle: —",
            f"Object: {sensor['object']}" if scan_active else "Object: —",
            f"Calibrated: {'YES' if calibrated else 'NO'}",
            f"View: {'3D' if view_mode == VIEW_MODE_3D else '2D'}",
            "",
            "R - Reset | C - Calibrate | V - Toggle View | S - Save PNG"
        ]
        
        for i, line in enumerate(compact_data):
            if i == 0:
                color = scan_color
            elif "object" in line.lower() and sensor["object"].lower() != "none":
                color = RED
            elif "Calibrated: YES" in line:
                color = GREEN
            elif "Calibrated: NO" in line:
                color = RED
            elif "View:" in line:
                color = CYAN
            else:
                color = WHITE
            
            text = font_small.render(line, True, color)
            screen.blit(text, (15, y_pos))
            y_pos += 18
            
        return restore_btn, None, None
    else:
        # FULL UI WITH RESPONSIVE PANEL POSITIONING
        min_panel_width = 240
        max_panel_width = 320
        panel_width = max(min_panel_width, min(max_panel_width, WIDTH // 4))
        
        margin = 15
        panel_x = WIDTH - panel_width - margin
        panel_y = margin + PADDING_TOP
        
        available_height = HEIGHT - 2 * margin - 80
        card_height = max(90, min(140, available_height // 5 - 10))
        spacing = max(8, min(15, available_height // 30))
        
        if panel_x < WIDTH // 2 + 100:
            panel_width = max(200, WIDTH - (WIDTH // 2 + 100) - margin)
            panel_x = WIDTH - panel_width - margin
        
        # STATUS PANEL
        scan_status = "SCANNING" if scan_active else "IDLE"
        scan_color = GREEN if scan_active else GRAY
        
        status_content = [
            f"Status: {scan_status}",
            f"Distance: {current_distance:.1f} cm" if scan_active else "Distance: —",
            f"Angle: {get_beam_angle(sensor['yaw_instant']):.1f}°" if scan_active and get_beam_angle(sensor['yaw_instant']) else "Angle: —",
            f"Object: {sensor['object']}" if scan_active else "Object: —"
        ]
        object_color = RED if scan_active and sensor["object"].lower() != "none" else scan_color
        draw_card(screen, panel_x, panel_y, panel_width, card_height, 
                  "SENSOR STATUS", status_content, object_color)
        
        # SYSTEM INFO
        system_content = [
            f"Calibrated: {'YES' if calibrated else 'NO'}",
            f"Direction: {sensor['direction']}" if scan_active else "Direction: —",
            f"Gyro: {sensor['gyro']}" if scan_active else "Gyro: —",
            f"Points: {len(scan_points)}" if scan_active else "Points: 0"
        ]
        calib_color = GREEN if calibrated else RED
        draw_card(screen, panel_x, panel_y + card_height + spacing, panel_width, card_height,
                  "SYSTEM", system_content, calib_color)
        
        # VIEW MODE PANEL
        view_content = [
            f"Mode: {'3D' if view_mode == VIEW_MODE_3D else '2D'}",
            f"Auto-rotate: {'ON' if auto_rotate else 'OFF'}" if view_mode == VIEW_MODE_3D else "Perspective: Top-down",
            " ",
            "V: Toggle 2D/3D view" if scan_active else "Start scanning to access 3D"
        ]
        view_color = CYAN if scan_active else GRAY
        draw_card(screen, panel_x, panel_y + 2*(card_height + spacing), panel_width, card_height,
                  "VIEW MODE", view_content, view_color)
        
        # CONTROLS
        controls_content = [
            "R: Reset scan & center position",
            "C: Calibrate sensor to 90°",
            "V: Toggle 2D/3D view",
            "T: Toggle auto-rotation (3D only)"
        ]
        draw_card(screen, panel_x, panel_y + 3*(card_height + spacing), panel_width, card_height,
                  "CONTROLS", controls_content, BLUE)
        
        # EXPORT/SAVE PANEL
        export_content = [
            "Press S to save screenshot",
            " ",
            "S: Saves current view to Downloads",
            "folder with timestamp"
        ]
        draw_card(screen, panel_x, panel_y + 4*(card_height + spacing), panel_width, card_height,
                  "EXPORT/SAVE", export_content, PURPLE)
        
        # TITLE AND INFO
        title = font_large.render("SurroundSense", True, WHITE)
        screen.blit(title, (20, 15 + PADDING_TOP))
        
        range_text = font_medium.render(f"MAX RANGE: {MAX_CM}cm", True, LIGHT_GRAY)
        screen.blit(range_text, (20, 45 + PADDING_TOP))
        
        # VIEW MODE INDICATOR UNDER MAX RANGE
        view_mode_text = f"VIEW MODE: {'3D EXTRUDED' if view_mode == VIEW_MODE_3D else '2D RADAR'}"
        view_text = font_medium.render(view_mode_text, True, CYAN)
        screen.blit(view_text, (20, 70 + PADDING_TOP))
        
        return None, None, None

# ===== MAIN LOOP =====
running = True
while running:
    # EVENTS
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.VIDEORESIZE:
            if not fullscreen and not minimized:
                WIDTH = max(MIN_WIDTH, e.w)
                HEIGHT = max(MIN_HEIGHT, e.h)
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                screen.fill(BLACK)
                pygame.display.flip()
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r:
                scan_points.clear()
                scan_active = True  # ENABLE SCANNING AND BEAM AFTER R PRESS
            elif e.key == pygame.K_c:
                yaw_offset = sensor["yaw_instant"] - 90.0
                calibrated = True
                # SEND CALIBRATION COMMAND TO ARDUINO
                try:
                    ser.write(b"CALIB\n")
                    ser.flush()  # ENSURE COMMAND IS SENT IMMEDIATELY
                except Exception as e:
                    print(f"Failed to send calibration command: {e}")
            elif e.key == pygame.K_v:
                # TOGGLE VIEW MODE (ONLY WHEN SCANNING IS ACTIVE)
                if scan_active:
                    view_mode = VIEW_MODE_3D if view_mode == VIEW_MODE_2D else VIEW_MODE_2D
                    print(f"Switched to {'3D' if view_mode == VIEW_MODE_3D else '2D'} view mode")
            elif e.key == pygame.K_t:
                # TOGGLE AUTO-ROTATION IN 3D MODE
                if view_mode == VIEW_MODE_3D:
                    auto_rotate = not auto_rotate
                    print(f"Auto-rotation {'enabled' if auto_rotate else 'disabled'}")
            elif e.key == pygame.K_s:
                save_screenshot()
            elif e.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    screen.fill(BLACK)
                    pygame.display.flip()
                    pygame.time.wait(10)
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    WIDTH, HEIGHT = screen.get_size()
                    screen.fill(BLACK)
                    pygame.display.flip()
                else:
                    screen.fill(BLACK)
                    pygame.display.flip()
                    pygame.time.wait(10)
                    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
                    WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
                    screen.fill(BLACK)
                    pygame.display.flip()
            elif e.key == pygame.K_ESCAPE:
                if fullscreen:
                    fullscreen = False
                    screen.fill(BLACK)
                    pygame.display.flip()
                    pygame.time.wait(10)
                    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
                    WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
                    screen.fill(BLACK)
                    pygame.display.flip()
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if minimized:
                restore_btn, _, _ = draw_ui()
                if restore_btn and restore_btn.collidepoint(e.pos):
                    minimized = False
                    screen.fill(BLACK)
                    pygame.display.flip()
                    pygame.time.wait(10)
                    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
                    WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
                    screen.fill(BLACK)
                    pygame.display.flip()

    # SERIAL READ - ONLY PROCESS DATA IF SCANNING IS ACTIVE
    if ser.in_waiting and scan_active:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                parsed = parse_line(line)
                
                # USE RAW DISTANCE DIRECTLY FOR ACCURACY
                if "distance" in parsed:
                    raw_dist = float(parsed["distance"])
                    sensor["distance_raw"] = raw_dist
                    current_distance = raw_dist  # STORE EXACT SENSOR READING
                    beam_distance = raw_dist     # USE SAME RAW VALUE FOR BEAM
                
                if "yaw" in parsed:
                    raw_yaw = wrap360(float(parsed["yaw"]))
                    sensor["yaw_instant"] = raw_yaw
                    sensor["yaw_raw"] = raw_yaw
                
                if "direction" in parsed: sensor["direction"] = parsed["direction"]
                if "object" in parsed: sensor["object"] = parsed["object"]
                if "gyro" in parsed: sensor["gyro"] = parsed["gyro"]
        except Exception as e:
            print(f"Serial read error: {e}")

    # CALCULATE ANGLES - ONLY WHEN SCANNING IS ACTIVE
    if scan_active:
        beam_angle = get_beam_angle(sensor["yaw_instant"])
        map_angle = get_map_angle(sensor["yaw_raw"])

        # UPDATE MAP WITH ACCURATE DISTANCE VALUES
        if map_angle is not None and 0 <= map_angle <= 180:
            angle_key = int(round(map_angle))
            has_object = sensor["object"].lower() != "none" and current_distance < MAX_CM
            
            # USE CLAMPED DISTANCE FOR DISPLAY BUT STORE RAW DISTANCE
            display_distance = clamp(current_distance, 0.0, MAX_CM) if has_object else MAX_CM
            
            scan_points[angle_key] = {
                'coord': polar_to_xy(angle_key, display_distance),
                'has_object': has_object,
                'distance': current_distance  # STORE RAW DISTANCE FOR ACCURACY
            }
    else:
        beam_angle = None

    # DRAW EVERYTHING
    screen.fill(BLACK)
    
    if not minimized:
        if scan_active:
            # DRAW ACTIVE SCANNING INTERFACE
            if view_mode == VIEW_MODE_2D:
                draw_radar_display()
                draw_scan_data()
                if beam_angle is not None:
                    # USE CLAMPED DISTANCE FOR BEAM DISPLAY
                    beam_display_distance = clamp(beam_distance, 0.0, MAX_CM) if sensor["object"].lower() != "none" and beam_distance < MAX_CM else MAX_CM
                    draw_beam(beam_angle, beam_display_distance)
            else:  # 3D MODE
                draw_3d_view()
        else:
            # DRAW IDLE SCREEN
            draw_idle_screen()
    
    draw_ui()
    draw_screenshot_message()

    pygame.display.flip()
    clock.tick(60)

ser.close()
pygame.quit()

#CALIB COMMAND NOW PROPERLY SENT TO ARDUINO WITH ERROR HANDLING
#ADDED 2D/3D VIEW MODE TOGGLE WITH 'V' KEY
#3D MODE EXTRUDES THE SCANNED GREEN AREA AND RENDERS IT AS A 3D SURFACE
#AUTO-ROTATION IN 3D MODE CAN BE TOGGLED WITH 'T' KEY
#VIEW MODE INDICATOR ADDED UNDER MAX RANGE DISPLAY