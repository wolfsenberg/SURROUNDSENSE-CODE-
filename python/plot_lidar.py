import os
import sys
import serial
import serial.tools.list_ports
import pygame
import time
import math
from collections import deque
from datetime import datetime

def find_arduino_port():
    """AUTO-DETECT ARDUINO COM PORT"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(keyword in port.description.upper() for keyword in 
               ['ARDUINO', 'CH340', 'CH341', 'FTDI', 'USB-SERIAL']):
            return port.device
    
    for port_name in ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8']:
        try:
            test_port = serial.Serial(port_name, 9600, timeout=1)
            test_port.close()
            return port_name
        except:
            continue
    return None

def reset_to_idle():
    """RESET APP TO IDLE MODE AND CLEAR ALL CACHED DATA"""
    global scan_active, scan_paused, calibrated, yaw_offset, current_distance, beam_distance
    global camera_zoom, camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y
    global view_mode, screenshot_message, screenshot_timer, taking_screenshot
    
    # RESET SCANNING STATE
    scan_active = False
    scan_paused = False
    calibrated = False
    yaw_offset = 0.0
    current_distance = 0.0
    beam_distance = 0.0
    
    # CLEAR ALL CACHED DATA
    scan_points.clear()
    map_yaw_hist.clear()
    beam_yaw_hist.clear()
    
    # RESET SENSOR DATA
    sensor.update({
        "distance_raw": 0.0,
        "yaw_raw": 90.0,
        "yaw_instant": 90.0,
        "direction": "Stationary",
        "object": "None",
        "gyro": "Still",
    })
    
    # RESET 3D CAMERA TO DEFAULT
    camera_zoom = 1.0
    camera_rotation_x = -90
    camera_rotation_y = 0
    camera_pan_x = 0
    camera_pan_y = 0
    view_mode = VIEW_MODE_2D
    
    # CLEAR SCREENSHOT MESSAGES
    screenshot_message = ""
    screenshot_timer = 0
    taking_screenshot = False
    
    # SEND RESET COMMAND TO ARDUINO IF CONNECTED
    try:
        if ser and ser.is_open:
            ser.write(b"RESET\n")
            ser.flush()
    except Exception as e:
        print(f"Failed to send reset command: {e}")

# CORE SETTINGS
BAUD = 9600
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1200, 720
MIN_WIDTH, MIN_HEIGHT = 1200, 720

# GET DESKTOP RESOLUTION FOR FULLSCREEN DEFAULT
pygame.init()  # Initialize pygame early to get display info
display_info = pygame.display.Info()
FULLSCREEN_WIDTH = display_info.current_w
FULLSCREEN_HEIGHT = display_info.current_h

# SET INITIAL FULLSCREEN DIMENSIONS
WIDTH, HEIGHT = FULLSCREEN_WIDTH, FULLSCREEN_HEIGHT

def get_center():
    return WIDTH // 2 - 122, int(HEIGHT // 1.4) + PADDING_TOP

MAX_CM = 70
SCALE = 5
MAP_SMOOTH_N = 5  # Increased smoothing for better accuracy
BEAM_SMOOTH_N = 3  # Increased smoothing for stable beam

# DISTANCE FILTERING FOR ACCURACY
DISTANCE_FILTER_N = 3  # Filter for distance readings
distance_filter = deque(maxlen=DISTANCE_FILTER_N)

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

# VIEW MODES
VIEW_MODE_2D = 0
VIEW_MODE_3D = 1
view_mode = VIEW_MODE_2D

# 3D CAMERA SETTINGS
camera_zoom = 1.0
camera_rotation_x = -90
camera_rotation_y = 0
camera_pan_x = 0
camera_pan_y = 0

# MOUSE INTERACTION STATE
mouse_dragging = False
last_mouse_pos = (0, 0)
mouse_drag_mode = None

# SCANNING CONTROL
scan_paused = False

# ENHANCED DISPLAY STATE MANAGEMENT FOR FLICKER PREVENTION
display_state = {
    'surface_cache': None,
    'last_width': 0,
    'last_height': 0,
    'frame_buffer': None,
    'stable_buffer': None,
    'buffer_ready': False
}

# SERIAL CONNECTION SETUP
PORT = find_arduino_port()
if PORT is None:
    print("No Arduino found! Check connection and drivers.")
    input("Press Enter to exit...")
    exit()

print(f"Arduino found on {PORT}")
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# PYGAME SETUP
os.environ['SDL_VIDEO_WINDOW_POS'] = 'centered'

def find_icon_files():
    """FIND BOTH ICO AND PNG FILES"""
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
    
    for path in search_paths:
        if icon_files['ico']:
            break
        for filename in ico_names:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                icon_files['ico'] = full_path
                break
    
    for path in search_paths:
        if icon_files['png']:
            break
        for filename in png_names:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path):
                icon_files['png'] = full_path
                break
    
    return icon_files

def setup_window_icon(icon_files):
    """SETUP WINDOW TAB ICON"""
    try:
        if icon_files['ico']:
            try:
                icon_surface = pygame.image.load(icon_files['ico'])
                pygame.display.set_icon(icon_surface)
                return True
            except Exception:
                pass
        
        if icon_files['png']:
            try:
                icon_surface = pygame.image.load(icon_files['png'])
                pygame.display.set_icon(icon_surface)
                return True
            except Exception:
                pass
        
        return False
        
    except Exception:
        return False

def setup_taskbar_icon(icon_files):
    """SETUP TASKBAR ICON FOR WINDOWS"""
    try:
        import ctypes
        
        app_id = 'surroundsense.radar.scanner.v1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
        
        if not icon_files['png']:
            return False
        
        png_path = os.path.abspath(icon_files['png'])
        hwnd = pygame.display.get_wm_info()["window"]
        
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        
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
        
        return success
            
    except ImportError:
        return False
    except Exception:
        return False

def setup_all_icons():
    """SETUP BOTH WINDOW AND TASKBAR ICONS"""
    icon_files = find_icon_files()
    window_success = setup_window_icon(icon_files)
    return window_success, icon_files

window_icon_success, icon_files = setup_all_icons()

def setup_display_mode(width, height, fullscreen=False):
    """ENHANCED DISPLAY MODE SETUP WITH IMPROVED FULLSCREEN AND FLICKER PREVENTION"""
    global screen, WIDTH, HEIGHT, display_state
    
    # ENHANCED FLAGS FOR BETTER PERFORMANCE AND STABILITY
    base_flags = pygame.DOUBLEBUF | pygame.HWSURFACE
    
    if fullscreen:
        # GET CURRENT DESKTOP RESOLUTION FOR MAXIMUM COMPATIBILITY
        info = pygame.display.Info()
        desktop_width = info.current_w
        desktop_height = info.current_h
        
        # TRY FULLSCREEN WITH DESKTOP RESOLUTION
        flags = base_flags | pygame.FULLSCREEN
        try:
            screen = pygame.display.set_mode((desktop_width, desktop_height), flags)
            WIDTH, HEIGHT = desktop_width, desktop_height
            print(f"Fullscreen mode set: {WIDTH}x{HEIGHT}")
        except pygame.error as e:
            print(f"Fullscreen failed: {e}, falling back to windowed mode")
            try:
                screen = pygame.display.set_mode((width, height), base_flags | pygame.RESIZABLE)
                WIDTH, HEIGHT = width, height
            except pygame.error:
                screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), base_flags)
                WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
    else:
        flags = base_flags | pygame.RESIZABLE
        try:
            screen = pygame.display.set_mode((width, height), flags)
            WIDTH, HEIGHT = width, height
        except pygame.error:
            screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), base_flags)
            WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
    
    # ENHANCED DISPLAY STATE RESET WITH DOUBLE BUFFERING
    display_state.update({
        'surface_cache': None,
        'last_width': WIDTH,
        'last_height': HEIGHT,
        'frame_buffer': None,
        'stable_buffer': None,
        'buffer_ready': False
    })
    
    # IMMEDIATE BUFFER INITIALIZATION AND CLEARING
    try:
        display_state['frame_buffer'] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        display_state['stable_buffer'] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        display_state['buffer_ready'] = True
    except pygame.error:
        display_state['frame_buffer'] = pygame.Surface((WIDTH, HEIGHT))
        display_state['stable_buffer'] = pygame.Surface((WIDTH, HEIGHT))
        display_state['buffer_ready'] = True
    
    # CLEAR ALL BUFFERS TO PREVENT FLICKER
    screen.fill(BLACK)
    if display_state['frame_buffer']:
        display_state['frame_buffer'].fill(BLACK)
    if display_state['stable_buffer']:
        display_state['stable_buffer'].fill(BLACK)
    
    # FORCE IMMEDIATE DISPLAY UPDATE
    pygame.display.flip()
    pygame.time.wait(32)  # Increased wait for better stability
    
    return screen

# INITIALIZE DISPLAY WITH FULLSCREEN AS DEFAULT
fullscreen = True  # SET FULLSCREEN AS DEFAULT
screen = setup_display_mode(FULLSCREEN_WIDTH, FULLSCREEN_HEIGHT, fullscreen)

def setup_taskbar_post_display():
    """SETUP TASKBAR ICON AFTER DISPLAY IS CREATED"""
    if icon_files and icon_files['png']:
        taskbar_success = setup_taskbar_icon(icon_files)
        return taskbar_success
    return False

taskbar_success = setup_taskbar_post_display()

pygame.display.set_caption("SurroundSense")

clock = pygame.time.Clock()
font_small = pygame.font.SysFont('Arial', 14)
font_medium = pygame.font.SysFont('Arial', 16, bold=True)
font_large = pygame.font.SysFont('Arial', 20, bold=True)

# WINDOW STATE - START IN FULLSCREEN
minimized = False
MINI_WIDTH, MINI_HEIGHT = 400, 300

# SCREENSHOT STATE
screenshot_message = ""
screenshot_timer = 0
taking_screenshot = False

# STATE VARIABLES
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

# DISTANCE AND CALIBRATION
current_distance = 0.0
beam_distance = 0.0
calibrated = False
yaw_offset = 0.0
scan_active = False
scan_points = {}

# IMPROVED DISTANCE FILTERING FOR ACCURACY
def filter_distance(raw_distance):
    """FILTER DISTANCE READINGS FOR ACCURACY"""
    # CLAMP TO MAX RANGE FIRST
    clamped_distance = min(raw_distance, MAX_CM)
    
    # ADD TO FILTER BUFFER
    distance_filter.append(clamped_distance)
    
    # RETURN MEDIAN OF RECENT READINGS FOR STABILITY
    sorted_distances = sorted(distance_filter)
    median_idx = len(sorted_distances) // 2
    
    return sorted_distances[median_idx]

# 3D MATH HELPERS
def rotate_point_3d(x, y, z, angle_x, angle_y, angle_z=0):
    """ROTATE A 3D POINT AROUND ALL THREE AXES"""
    ax, ay, az = math.radians(angle_x), math.radians(angle_y), math.radians(angle_z)
    
    # X AXIS ROTATION
    y1 = y * math.cos(ax) - z * math.sin(ax)
    z1 = y * math.sin(ax) + z * math.cos(ax)
    y, z = y1, z1
    
    # Y AXIS ROTATION
    x1 = x * math.cos(ay) + z * math.sin(ay)
    z1 = -x * math.sin(ay) + z * math.cos(ay)
    x, z = x1, z1
    
    # Z AXIS ROTATION
    x1 = x * math.cos(az) - y * math.sin(az)
    y1 = x * math.sin(az) + y * math.cos(az)
    x, y = x1, y1
    
    return x, y, z

def project_3d_to_2d(x, y, z, zoom=1.0, pan_x=0, pan_y=0):
    """PROJECT 3D POINT TO 2D SCREEN COORDINATES"""
    CENTER_X, CENTER_Y = get_center()
    
    screen_x = CENTER_X + (x * zoom) + pan_x
    screen_y = CENTER_Y - (y * zoom) + pan_y
    
    return int(screen_x), int(screen_y)

def generate_extruded_mesh():
    """GENERATE 3D WIREFRAME MESH FROM SCAN POINTS"""
    if not scan_points:
        return [], []
    
    vertices = []
    lines = []
    
    extrusion_height = 60
    scale_factor = 2.0
    
    angles = sorted(scan_points.keys())
    
    if len(angles) < 2:
        return vertices, lines
    
    base_points = []
    top_points = []
    
    for angle in angles:
        data = scan_points[angle]
        if data['has_object']:
            distance = data['distance'] * scale_factor
            angle_rad = math.radians(angle)
            
            x = distance * math.cos(angle_rad)
            z = distance * math.sin(angle_rad)
            
            base_point = (x, 0, z)
            base_points.append(base_point)
            vertices.append(base_point)
            
            top_point = (x, extrusion_height, z)
            top_points.append(top_point)
            vertices.append(top_point)
    
    num_points = len(base_points)
    
    if num_points >= 2:
        # CONNECT BASE POINTS
        for i in range(num_points - 1):
            base_idx = i * 2
            next_base_idx = (i + 1) * 2
            lines.append((base_idx, next_base_idx))
        
        # CONNECT TOP POINTS
        for i in range(num_points - 1):
            top_idx = i * 2 + 1
            next_top_idx = (i + 1) * 2 + 1
            lines.append((top_idx, next_top_idx))
        
        # VERTICAL LINES
        for i in range(num_points):
            base_idx = i * 2
            top_idx = i * 2 + 1
            lines.append((base_idx, top_idx))
    
    return vertices, lines

def draw_3d_wireframe_view():
    """DRAW 3D WIREFRAME VIEW"""
    global camera_zoom, camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y
    
    vertices, lines = generate_extruded_mesh()
    
    if not vertices or not lines:
        CENTER_X, CENTER_Y = get_center()
        empty_text = font_large.render("3D VIEW - NO SCAN DATA", True, GRAY)
        text_rect = empty_text.get_rect(center=(CENTER_X, CENTER_Y))
        screen.blit(empty_text, text_rect)
        return
    
    projected_vertices = []
    
    for x, y, z in vertices:
        rx, ry, rz = rotate_point_3d(x, y, z, camera_rotation_x, camera_rotation_y)
        screen_x, screen_y = project_3d_to_2d(rx, ry, rz, camera_zoom, camera_pan_x, camera_pan_y)
        projected_vertices.append((screen_x, screen_y))
    
    # DRAW WIREFRAME LINES
    for line in lines:
        start_idx, end_idx = line
        
        if start_idx < len(projected_vertices) and end_idx < len(projected_vertices):
            start_pos = projected_vertices[start_idx]
            end_pos = projected_vertices[end_idx]
            
            if (-1000 <= start_pos[0] <= WIDTH + 1000 and -1000 <= start_pos[1] <= HEIGHT + 1000 and
                -1000 <= end_pos[0] <= WIDTH + 1000 and -1000 <= end_pos[1] <= HEIGHT + 1000):
                pygame.draw.line(screen, LIGHT_GREEN, start_pos, end_pos, 2)
    
    # DRAW ORIGIN
    origin_3d = rotate_point_3d(0, 0, 0, camera_rotation_x, camera_rotation_y)
    origin_2d = project_3d_to_2d(origin_3d[0], origin_3d[1], origin_3d[2], camera_zoom, camera_pan_x, camera_pan_y)
    
    if 0 <= origin_2d[0] < WIDTH and 0 <= origin_2d[1] < HEIGHT:
        pygame.draw.circle(screen, RED, origin_2d, 8)
        pygame.draw.circle(screen, WHITE, origin_2d, 6)
    
    # 3D NAVIGATION HELP
    if not taking_screenshot:
        help_text = [
            "3D NAVIGATION:",
            "Hold Left Click: Rotate View",
            "Hold Right Click: Pan view", 
            "Scroll Wheel: Zoom in/out"
        ]
        
        y_offset = HEIGHT - 120
        for i, text in enumerate(help_text):
            color = CYAN if i == 0 else WHITE
            help_surface = font_medium.render(text, True, color)
            screen.blit(help_surface, (20, y_offset + i * 18))

# MOUSE HANDLERS
def handle_mouse_wheel(event):
    """HANDLE ZOOM WITH MOUSE WHEEL"""
    global camera_zoom
    
    if view_mode == VIEW_MODE_3D:
        zoom_factor = 1.1 if event.y > 0 else 0.9
        camera_zoom = max(0.1, min(5.0, camera_zoom * zoom_factor))

def handle_mouse_button_down(event):
    """START MOUSE DRAG OPERATIONS"""
    global mouse_dragging, last_mouse_pos, mouse_drag_mode
    
    if view_mode == VIEW_MODE_3D:
        if event.button == 1:  # LEFT CLICK - ROTATE
            mouse_dragging = True
            mouse_drag_mode = 'rotate'
            last_mouse_pos = pygame.mouse.get_pos()
        elif event.button == 3:  # RIGHT CLICK - PAN
            mouse_dragging = True
            mouse_drag_mode = 'pan'
            last_mouse_pos = pygame.mouse.get_pos()

def handle_mouse_button_up(event):
    """END MOUSE DRAG OPERATIONS"""
    global mouse_dragging, mouse_drag_mode
    
    if event.button in [1, 3]:
        mouse_dragging = False
        mouse_drag_mode = None

def handle_mouse_motion(event):
    """HANDLE MOUSE DRAG FOR 3D NAVIGATION"""
    global camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y, last_mouse_pos
    
    if view_mode == VIEW_MODE_3D and mouse_dragging:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - last_mouse_pos[0]
        dy = mouse_y - last_mouse_pos[1]
        
        if mouse_drag_mode == 'rotate':
            camera_rotation_y += dx * 0.5
            camera_rotation_x += dy * 0.5
            camera_rotation_x = max(-90, min(90, camera_rotation_x))
            
        elif mouse_drag_mode == 'pan':
            camera_pan_x += dx * 2
            camera_pan_y += dy * 2
        
        last_mouse_pos = (mouse_x, mouse_y)

# UTILITY FUNCTIONS
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
    """CALCULATE BEAM ANGLE WITH PROPER CALIBRATION"""
    if not calibrated:
        return movavg(beam_yaw_hist, 90.0)
    else:
        y = yaw_raw - yaw_offset
    
    y = wrap360(y)
    
    if 0.0 <= y <= 180.0:
        reversed_y = 180 - y
        return movavg(beam_yaw_hist, reversed_y)
    
    return None

def get_map_angle(yaw_raw):
    """CALCULATE MAP ANGLE WITH PROPER CALIBRATION"""
    if not calibrated:
        return movavg(map_yaw_hist, 90.0)
    else:
        y = yaw_raw - yaw_offset
    
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
    """GET USER'S DOWNLOADS FOLDER PATH"""
    try:
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
        
        downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        if os.path.exists(downloads_path):
            return downloads_path
            
        return os.getcwd()
        
    except Exception:
        return os.getcwd()

def save_screenshot():
    """SAVE CURRENT SCREEN AS PNG TO DOWNLOADS FOLDER"""
    global screenshot_message, screenshot_timer, taking_screenshot
    
    try:
        taking_screenshot = True
        
        # RENDER TO FRAME BUFFER TO AVOID FLICKER
        frame_surface = pygame.Surface((WIDTH, HEIGHT))
        frame_surface.fill(BLACK)
        
        # RENDER CONTENT TO BUFFER
        temp_screen = screen
        screen = frame_surface
        
        if not minimized:
            if scan_active:
                if view_mode == VIEW_MODE_2D:
                    draw_radar_display()
                    draw_scan_data()
                    if beam_angle is not None and not scan_paused:
                        draw_beam(beam_angle, beam_distance)
                else:
                    draw_3d_wireframe_view()
            else:
                draw_idle_screen()
        draw_ui()
        
        # RESTORE SCREEN REFERENCE
        screen = temp_screen
        
        downloads_dir = get_downloads_folder()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        view_suffix = "3D" if view_mode == VIEW_MODE_3D else "2D"
        filename = f"SurroundSense_Radar_{view_suffix}_{timestamp}.png"
        filepath = os.path.join(downloads_dir, filename)
        
        pygame.image.save(frame_surface, filepath)
        
        taking_screenshot = False
        
        screenshot_message = f"SUCCESS|Saved to Downloads: {filename}"
        screenshot_timer = pygame.time.get_ticks() + 4000
        
        return True
        
    except Exception as e:
        taking_screenshot = False
        screenshot_message = f"ERROR|Save failed: {str(e)[:50]}..."
        screenshot_timer = pygame.time.get_ticks() + 4000
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
    for r in [10, 20, 30, 40, 50, 60, 70]:  # Include 70cm ring
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

    # RANGE LABELS - SHOW ALL INCLUDING 70
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
        
    # SCANNING INSTRUCTIONS
    if scan_active and not screenshot_message and not taking_screenshot and not scan_paused:
        instruction_text = font_medium.render("ROTATE THE SENSOR VERY SLOW", True, WHITE)
        text_rect = instruction_text.get_rect(center=(CENTER_X, CENTER_Y + 35))
        screen.blit(instruction_text, text_rect)
        instruction_text2 = font_medium.render("Ensure the area is well-lit and the sensor is calibrated (press C to calibrate)", True, WHITE)
        text_rect2 = instruction_text2.get_rect(center=(CENTER_X, CENTER_Y + 65))
        screen.blit(instruction_text2, text_rect2)
        instruction_text3 = font_medium.render("If the app freezes, press X to restart", True, WHITE)
        text_rect3 = instruction_text3.get_rect(center=(CENTER_X, CENTER_Y + 95))
        screen.blit(instruction_text3, text_rect3)
    elif scan_paused and not screenshot_message and not taking_screenshot:
        paused_text = font_large.render("SCAN PAUSED - Press P to resume", True, ORANGE)
        text_rect = paused_text.get_rect(center=(CENTER_X, CENTER_Y + 50))
        screen.blit(paused_text, text_rect)

def draw_scan_data():
    if not scan_points:
        return
    
    # DRAW CONTINUOUS DOTTED LINE CONNECTING SCAN POINTS
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
    """DRAW DOTTED LINE BETWEEN TWO POINTS"""
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
    
    # BEAM LINE
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
    
    pygame.draw.circle(screen, GRAY, (CENTER_X, CENTER_Y), 4)
    
    idle_text1 = font_large.render("WELCOME TO SURROUNDSENSE", True, WHITE)
    idle_text2 = font_small.render("BY GEINEL NIÑO DUNGAO", True, LIGHT_GRAY)
    idle_text3 = font_medium.render("PRESS R AND C TO START SCANNING", True, WHITE)
    
    text1_rect = idle_text1.get_rect(center=(CENTER_X, CENTER_Y - 50))
    text2_rect = idle_text2.get_rect(center=(CENTER_X, CENTER_Y - 20))
    text3_rect = idle_text3.get_rect(center=(CENTER_X, CENTER_Y + 30))

    screen.blit(idle_text1, text1_rect)
    screen.blit(idle_text2, text2_rect)
    screen.blit(idle_text3, text3_rect)

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
    global camera_zoom, camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y
    
    if minimized:
        pygame.draw.rect(screen, (40, 40, 40), (0, 0, MINI_WIDTH, 30), border_radius=8)
        title = font_medium.render("Radar (Minimized)", True, WHITE)
        screen.blit(title, (10, 6))
        
        restore_btn = pygame.Rect(MINI_WIDTH - 35, 5, 25, 20)
        pygame.draw.rect(screen, (80, 80, 80), restore_btn, border_radius=4)
        pygame.draw.rect(screen, WHITE, (restore_btn.x + 8, restore_btn.y + 8, 9, 4))
        
        y_pos = 45
        scan_status = "PAUSED" if scan_paused else ("SCANNING" if scan_active else "IDLE")
        scan_color = ORANGE if scan_paused else (GREEN if scan_active else GRAY)
        
        compact_data = [
            f"Status: {scan_status}",
            f"Distance: {current_distance:.1f}cm" if scan_active else "Distance: —",
            f"Angle: {get_beam_angle(sensor['yaw_instant']):.1f}°" if scan_active and get_beam_angle(sensor['yaw_instant']) else "Angle: —",
            f"Object: {sensor['object']}" if scan_active else "Object: —",
            f"Calibrated: {'YES' if calibrated else 'NO'}",
            f"View: {'3D' if view_mode == VIEW_MODE_3D else '2D'}",
            "",
            "R - Reset | C - Calibrate | V - Toggle View | P - Pause/Resume | S - Save PNG | X - Reset to Idle"
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
        # FULL UI WITH RESPONSIVE PANELS
        min_panel_width = 240
        max_panel_width = 320
        panel_width = max(min_panel_width, min(max_panel_width, WIDTH // 4))
        
        margin = 15
        panel_x = WIDTH - panel_width - margin
        panel_y = margin + PADDING_TOP
        
        available_height = HEIGHT - 2 * margin - 80
        card_height = max(80, min(120, available_height // 6 - 8))
        spacing = max(6, min(12, available_height // 35))
        
        if panel_x < WIDTH // 2 + 100:
            panel_width = max(200, WIDTH - (WIDTH // 2 + 100) - margin)
            panel_x = WIDTH - panel_width - margin
        
        # STATUS PANEL
        scan_status = "PAUSED" if scan_paused else ("SCANNING" if scan_active else "IDLE")
        scan_color = ORANGE if scan_paused else (GREEN if scan_active else GRAY)
        
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
        if view_mode == VIEW_MODE_3D:
            view_content = [
                f"Mode: 3D Wireframe Style",
                f"Zoom: {camera_zoom:.2f}x",
                f"Rotation: {camera_rotation_x:.0f}°, {camera_rotation_y:.0f}°",
                f"Pan: {camera_pan_x:.0f}, {camera_pan_y:.0f}"
            ]
        else:
            view_content = [
                f"Mode: 2D Radar Style",
                "Perspective: Top-down",
                " ",
                "Switch to 3D for navigation"
            ]
        view_color = CYAN if scan_active else GRAY
        draw_card(screen, panel_x, panel_y + 2*(card_height + spacing), panel_width, card_height,
                  "VIEW MODE", view_content, view_color)
        
        # SCAN CONTROL PANEL
        control_content = [
            f"Scanning: {'PAUSED' if scan_paused else 'ACTIVE'}" if scan_active else "Scanning: INACTIVE",
            " ",
            "P: Pause/Resume scanning",
            "Pause to freeze view while navigating"
        ]
        control_color = ORANGE if scan_paused else (GREEN if scan_active else GRAY)
        draw_card(screen, panel_x, panel_y + 3*(card_height + spacing), panel_width, card_height,
                  "SCAN PAUSE/RESUME CONTROL", control_content, control_color)
        
        # CONTROLS
        controls_content = [
            "R: Reset scan",
            "C: Calibrate sensor to 90°",
            "V: Switch between 2D/3D view"
        ]
        draw_card(screen, panel_x, panel_y + 4*(card_height + spacing), panel_width, card_height,
                  "SENSOR & VIEW CONTROLS", controls_content, BLUE)
        
        # EXPORT/SAVE PANEL
        export_content = [
            "Press S to save screenshot",
            " ",
            "S: Saves current view to your Downloads file"
        ]
        draw_card(screen, panel_x, panel_y + 5*(card_height + spacing), panel_width, card_height,
                  "EXPORT/SAVE", export_content, PURPLE)
        
        # TITLE AND INFO
        title = font_large.render("SurroundSense", True, WHITE)
        screen.blit(title, (20, 15 + PADDING_TOP))
        
        range_text = font_medium.render(f"MAX RANGE: {MAX_CM}cm", True, WHITE)
        screen.blit(range_text, (20, 45 + PADDING_TOP))
        
        view_mode_text = f"VIEW MODE: {'3D WIREFRAME STYLE' if view_mode == VIEW_MODE_3D else '2D RADAR STYLE'}"
        view_text = font_medium.render(view_mode_text, True, CYAN)
        screen.blit(view_text, (20, 70 + PADDING_TOP))
        
        return None, None, None

# ENHANCED RENDERING FUNCTION WITH IMPROVED FLICKER PREVENTION
def render_frame():
    """ENHANCED FRAME RENDERING WITH SUPERIOR FLICKER PREVENTION FOR FULLSCREEN"""
    global display_state
    
    # ENHANCED BUFFER MANAGEMENT WITH SIZE CHANGE DETECTION
    if (display_state['last_width'] != WIDTH or 
        display_state['last_height'] != HEIGHT or 
        not display_state['buffer_ready']):
        
        # RECREATE BUFFERS WITH ENHANCED ERROR HANDLING
        try:
            display_state['frame_buffer'] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA | pygame.HWSURFACE)
            display_state['stable_buffer'] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA | pygame.HWSURFACE)
            display_state['buffer_ready'] = True
        except pygame.error:
            # FALLBACK FOR PROBLEMATIC HARDWARE
            try:
                display_state['frame_buffer'] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                display_state['stable_buffer'] = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                display_state['buffer_ready'] = True
            except pygame.error:
                # FINAL FALLBACK
                display_state['frame_buffer'] = pygame.Surface((WIDTH, HEIGHT))
                display_state['stable_buffer'] = pygame.Surface((WIDTH, HEIGHT))
                display_state['buffer_ready'] = True
        
        display_state['last_width'] = WIDTH
        display_state['last_height'] = HEIGHT
    
    # ENSURE BUFFERS EXIST
    if not display_state.get('frame_buffer') or not display_state.get('stable_buffer'):
        display_state['frame_buffer'] = pygame.Surface((WIDTH, HEIGHT))
        display_state['stable_buffer'] = pygame.Surface((WIDTH, HEIGHT))
        display_state['buffer_ready'] = True
    
    # RENDER TO FRAME BUFFER FOR FLICKER-FREE DISPLAY
    frame_buffer = display_state['frame_buffer']
    frame_buffer.fill(BLACK)
    
    # REDIRECT RENDERING TO BUFFER
    global screen
    original_screen = screen
    screen = frame_buffer
    
    try:
        # RENDER ALL CONTENT TO BUFFER
        if not minimized:
            if scan_active:
                if view_mode == VIEW_MODE_2D:
                    draw_radar_display()
                    draw_scan_data()
                    if beam_angle is not None and not scan_paused:
                        beam_display_distance = clamp(beam_distance, 0.0, MAX_CM) if sensor["object"].lower() != "none" and beam_distance < MAX_CM else MAX_CM
                        draw_beam(beam_angle, beam_display_distance)
                else:
                    draw_3d_wireframe_view()
            else:
                draw_idle_screen()
        
        draw_ui()
        draw_screenshot_message()
        
    finally:
        # RESTORE ORIGINAL SCREEN
        screen = original_screen
    
    # SINGLE ATOMIC BLIT OPERATION WITH ENHANCED ERROR HANDLING
    try:
        # USE STABLE BUFFER FOR SMOOTHER TRANSITIONS
        display_state['stable_buffer'].blit(frame_buffer, (0, 0))
        screen.blit(display_state['stable_buffer'], (0, 0))
    except pygame.error:
        # DIRECT FALLBACK FOR PROBLEMATIC SYSTEMS
        try:
            screen.blit(frame_buffer, (0, 0))
        except pygame.error:
            # EMERGENCY FALLBACK - RENDER DIRECTLY
            pass

# MAIN LOOP
running = True
while running:
    # EVENT HANDLING
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.VIDEORESIZE:
            if not fullscreen and not minimized:
                WIDTH = max(MIN_WIDTH, e.w)
                HEIGHT = max(MIN_HEIGHT, e.h)
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.HWSURFACE | pygame.RESIZABLE)
        elif e.type == pygame.MOUSEWHEEL:
            handle_mouse_wheel(e)
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if not minimized:
                handle_mouse_button_down(e)
                # HANDLE MINIMIZE BUTTON CLICK
                restore_btn, _, _ = draw_ui()
                if restore_btn and restore_btn.collidepoint(e.pos):
                    minimized = False
                    WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT
                    screen = setup_display_mode(WIDTH, HEIGHT, False)
        elif e.type == pygame.MOUSEBUTTONUP:
            if not minimized:
                handle_mouse_button_up(e)
        elif e.type == pygame.MOUSEMOTION:
            if not minimized:
                handle_mouse_motion(e)
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r:
                # RESET SCAN - CLEAR ALL DATA AND START FRESH
                scan_points.clear()
                scan_active = True
                scan_paused = False
                map_yaw_hist.clear()
                beam_yaw_hist.clear()
                distance_filter.clear()  # Clear distance filter
                # RESET 3D CAMERA TO TOP VIEW
                camera_zoom = 1.0
                camera_rotation_x = -90
                camera_rotation_y = 0
                camera_pan_x = 0
                camera_pan_y = 0
            elif e.key == pygame.K_c:
                # CALIBRATE SENSOR TO 90 DEGREES - RESET BEAM POSITION ONLY
                yaw_offset = sensor["yaw_instant"] - 90.0
                calibrated = True
                # CLEAR BUFFERS AND INITIALIZE BEAM TO 90 DEGREES
                map_yaw_hist.clear()
                beam_yaw_hist.clear()
                distance_filter.clear()  # Clear distance filter on calibration
                for _ in range(BEAM_SMOOTH_N):
                    beam_yaw_hist.append(90.0)
                for _ in range(MAP_SMOOTH_N):
                    map_yaw_hist.append(90.0)
                try:
                    ser.write(b"CALIB\n")
                    ser.flush()
                except Exception as e:
                    print(f"Failed to send calibration command: {e}")
            elif e.key == pygame.K_p:
                if scan_active:
                    scan_paused = not scan_paused
            elif e.key == pygame.K_v:
                if scan_active:
                    view_mode = VIEW_MODE_3D if view_mode == VIEW_MODE_2D else VIEW_MODE_2D
                    if view_mode == VIEW_MODE_3D:
                        camera_zoom = 1.0
                        camera_rotation_x = -90
                        camera_rotation_y = 0
                        camera_pan_x = 0
                        camera_pan_y = 0
            elif e.key == pygame.K_s:
                save_screenshot()
            elif e.key == pygame.K_x:
                # RESET TO IDLE MODE INSTEAD OF RESTARTING APPLICATION
                reset_to_idle()
            elif e.key == pygame.K_F11:
                fullscreen = not fullscreen
                screen = setup_display_mode(DEFAULT_WIDTH, DEFAULT_HEIGHT, fullscreen)
            elif e.key == pygame.K_ESCAPE:
                if fullscreen:
                    fullscreen = False
                    screen = setup_display_mode(DEFAULT_WIDTH, DEFAULT_HEIGHT, False)

    # SERIAL COMMUNICATION - ONLY WHEN SCANNING ACTIVE AND NOT PAUSED
    if ser.in_waiting and scan_active and not scan_paused:
        try:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                parsed = parse_line(line)
                
                if "distance" in parsed:
                    raw_dist = float(parsed["distance"])
                    # APPLY DISTANCE FILTERING FOR ACCURACY
                    filtered_dist = filter_distance(raw_dist)
                    sensor["distance_raw"] = raw_dist
                    current_distance = filtered_dist
                    beam_distance = filtered_dist
                
                if "yaw" in parsed:
                    raw_yaw = wrap360(float(parsed["yaw"]))
                    sensor["yaw_instant"] = raw_yaw
                    sensor["yaw_raw"] = raw_yaw
                
                if "direction" in parsed: sensor["direction"] = parsed["direction"]
                if "object" in parsed: sensor["object"] = parsed["object"]
                if "gyro" in parsed: sensor["gyro"] = parsed["gyro"]
        except Exception as e:
            print(f"Serial read error: {e}")

    # ANGLE CALCULATIONS - ONLY WHEN SCANNING ACTIVE AND NOT PAUSED
    if scan_active and not scan_paused:
        beam_angle = get_beam_angle(sensor["yaw_instant"])
        map_angle = get_map_angle(sensor["yaw_raw"])

        # UPDATE SCAN POINTS WITH IMPROVED ACCURACY
        if map_angle is not None and 0 <= map_angle <= 180:
            angle_key = int(round(map_angle))
            has_object = sensor["object"].lower() != "none" and current_distance <= MAX_CM
            
            # USE EXACT DISTANCE FOR OBJECTS WITHIN RANGE
            display_distance = current_distance if has_object else MAX_CM
            
            scan_points[angle_key] = {
                'coord': polar_to_xy(angle_key, min(display_distance, MAX_CM)),
                'has_object': has_object,
                'distance': current_distance
            }
    else:
        beam_angle = get_beam_angle(sensor["yaw_instant"]) if scan_active else None

    # ENHANCED STABLE RENDERING WITH SUPERIOR FLICKER PREVENTION
    render_frame()
    
    # SINGLE DISPLAY FLIP WITH COMPREHENSIVE ERROR HANDLING
    try:
        pygame.display.flip()
    except pygame.error:
        # RECOVERY FOR DISPLAY ISSUES
        try:
            pygame.display.update()
        except pygame.error:
            # EMERGENCY FALLBACK
            pygame.time.wait(16)

    clock.tick(60)

ser.close()
pygame.quit()