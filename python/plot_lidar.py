import os
import sys
import subprocess
import serial
import serial.tools.list_ports
import pygame
import time
import math
from collections import deque
from datetime import datetime

def find_arduino_port():
    """AUTO-DETECT ARDUINO COM PORT"""
    try:
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
    except Exception:
        pass
    return None

def reset_to_idle():
    """RESET APPLICATION TO IDLE STATE"""
    global scan_active, scan_paused, calibrated, scan_points, yaw_offset
    global camera_zoom, camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y
    global current_distance, beam_distance, beam_angle
    
    try:
        scan_active = False
        scan_paused = False
        calibrated = False
        scan_points.clear()
        yaw_offset = 0.0
        
        camera_zoom = 1.0
        camera_rotation_x = -90
        camera_rotation_y = 0
        camera_pan_x = 0
        camera_pan_y = 0
        
        current_distance = 0.0
        beam_distance = 0.0
        beam_angle = None
        
        map_yaw_hist.clear()
        beam_yaw_hist.clear()
        
        sensor.update({
            "distance_raw": 0.0,
            "yaw_raw": 90.0,
            "yaw_instant": 90.0,
            "direction": "Stationary",
            "object": "None",
            "gyro": "Still",
        })
        
    except Exception as e:
        print(f"RESET ERROR: {e}")

def safe_display_mode_change(new_size, flags=0):
    """SAFELY CHANGE DISPLAY MODE TO PREVENT FLICKERING"""
    global screen, WIDTH, HEIGHT, display_changing
    
    try:
        display_changing = True
        
        # STORE CURRENT FRAME
        current_surface = screen.copy()
        
        if flags == pygame.FULLSCREEN:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            WIDTH, HEIGHT = screen.get_size()
        else:
            screen = pygame.display.set_mode(new_size, flags)
            WIDTH, HEIGHT = new_size
        
        # IMMEDIATE CLEAR WITH BLACK
        screen.fill(BLACK)
        pygame.display.flip()
        
        display_changing = False
        return True
        
    except Exception as e:
        print(f"DISPLAY MODE CHANGE ERROR: {e}")
        display_changing = False
        return False

# CORE SETTINGS
BAUD = 9600
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1200, 720
MIN_WIDTH, MIN_HEIGHT = 1200, 720
WIDTH, HEIGHT = DEFAULT_WIDTH, DEFAULT_HEIGHT

def get_center():
    return WIDTH // 2 - 122, int(HEIGHT // 1.4) + PADDING_TOP

MAX_CM = 70
SCALE = 5
MAP_SMOOTH_N = 3
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

# DISPLAY STATE
display_changing = False

# SERIAL CONNECTION SETUP
PORT = None
ser = None

try:
    PORT = find_arduino_port()
    if PORT is None:
        print("NO ARDUINO DETECTED - CHECK CONNECTION AND DRIVERS")
        input("PRESS ENTER TO EXIT...")
        sys.exit(1)

    print(f"ARDUINO DETECTED ON {PORT}")
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    
except Exception as e:
    print(f"SERIAL CONNECTION ERROR: {e}")
    input("PRESS ENTER TO EXIT...")
    sys.exit(1)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# PYGAME SETUP
try:
    pygame.init()
    os.environ['SDL_VIDEO_WINDOW_POS'] = 'centered'
except Exception as e:
    print(f"PYGAME INITIALIZATION ERROR: {e}")
    sys.exit(1)

def find_icon_files():
    """FIND ICON FILES"""
    icon_files = {'ico': None, 'png': None}
    
    try:
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
            try:
                for filename in ico_names:
                    full_path = os.path.join(path, filename)
                    if os.path.exists(full_path):
                        icon_files['ico'] = full_path
                        break
            except Exception:
                continue
        
        for path in search_paths:
            if icon_files['png']:
                break
            try:
                for filename in png_names:
                    full_path = os.path.join(path, filename)
                    if os.path.exists(full_path):
                        icon_files['png'] = full_path
                        break
            except Exception:
                continue
                
    except Exception:
        pass
    
    return icon_files

def setup_window_icon(icon_files):
    """SETUP WINDOW ICON"""
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
        from ctypes import wintypes
        
        app_id = 'surroundsense.radar.scanner.v1'
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
        
        if not icon_files.get('png'):
            return False
        
        try:
            png_path = os.path.abspath(icon_files['png'])
            if not os.path.exists(png_path):
                return False
                
            hwnd = pygame.display.get_wm_info()["window"]
            
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x00000010
            
            try:
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
            except Exception:
                return False
                
        except Exception:
            return False
            
    except ImportError:
        return False
    except Exception:
        return False

def setup_all_icons():
    """SETUP WINDOW AND TASKBAR ICONS"""
    try:
        icon_files = find_icon_files()
        window_success = setup_window_icon(icon_files)
        return window_success, icon_files
    except Exception:
        return False, {'ico': None, 'png': None}

window_icon_success, icon_files = setup_all_icons()

try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("SurroundSense")
except Exception as e:
    print(f"DISPLAY SETUP ERROR: {e}")
    sys.exit(1)

def setup_taskbar_post_display():
    """SETUP TASKBAR ICON AFTER DISPLAY CREATION"""
    try:
        if icon_files and icon_files.get('png'):
            taskbar_success = setup_taskbar_icon(icon_files)
            return taskbar_success
    except Exception:
        pass
    return False

taskbar_success = setup_taskbar_post_display()

try:
    clock = pygame.time.Clock()
    font_small = pygame.font.SysFont('Arial', 14)
    font_medium = pygame.font.SysFont('Arial', 16, bold=True)
    font_large = pygame.font.SysFont('Arial', 20, bold=True)
except Exception as e:
    print(f"FONT SETUP ERROR: {e}")
    sys.exit(1)

# WINDOW STATE
minimized = False
fullscreen = False
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

def rotate_point_3d(x, y, z, angle_x, angle_y, angle_z=0):
    """ROTATE 3D POINT AROUND ALL AXES"""
    try:
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
    except Exception:
        return x, y, z

def project_3d_to_2d(x, y, z, zoom=1.0, pan_x=0, pan_y=0):
    """PROJECT 3D POINT TO 2D SCREEN COORDINATES"""
    try:
        CENTER_X, CENTER_Y = get_center()
        
        screen_x = CENTER_X + (x * zoom) + pan_x
        screen_y = CENTER_Y - (y * zoom) + pan_y
        
        return int(screen_x), int(screen_y)
    except Exception:
        return 0, 0

def generate_extruded_mesh():
    """GENERATE 3D WIREFRAME MESH FROM SCAN POINTS"""
    if not scan_points:
        return [], []
    
    try:
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
            try:
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
            except Exception:
                continue
        
        num_points = len(base_points)
        
        if num_points >= 2:
            # CONNECT BASE POINTS
            for i in range(num_points - 1):
                try:
                    base_idx = i * 2
                    next_base_idx = (i + 1) * 2
                    lines.append((base_idx, next_base_idx))
                except Exception:
                    continue
            
            # CONNECT TOP POINTS
            for i in range(num_points - 1):
                try:
                    top_idx = i * 2 + 1
                    next_top_idx = (i + 1) * 2 + 1
                    lines.append((top_idx, next_top_idx))
                except Exception:
                    continue
            
            # VERTICAL LINES
            for i in range(num_points):
                try:
                    base_idx = i * 2
                    top_idx = i * 2 + 1
                    lines.append((base_idx, top_idx))
                except Exception:
                    continue
        
        return vertices, lines
        
    except Exception:
        return [], []

def draw_3d_wireframe_view():
    """DRAW 3D WIREFRAME VIEW"""
    global camera_zoom, camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y
    
    try:
        vertices, lines = generate_extruded_mesh()
        
        if not vertices or not lines:
            CENTER_X, CENTER_Y = get_center()
            empty_text = font_large.render("3D VIEW - NO SCAN DATA", True, GRAY)
            text_rect = empty_text.get_rect(center=(CENTER_X, CENTER_Y))
            screen.blit(empty_text, text_rect)
            return
        
        projected_vertices = []
        
        for x, y, z in vertices:
            try:
                rx, ry, rz = rotate_point_3d(x, y, z, camera_rotation_x, camera_rotation_y)
                screen_x, screen_y = project_3d_to_2d(rx, ry, rz, camera_zoom, camera_pan_x, camera_pan_y)
                projected_vertices.append((screen_x, screen_y))
            except Exception:
                projected_vertices.append((0, 0))
        
        # DRAW WIREFRAME LINES
        for line in lines:
            try:
                start_idx, end_idx = line
                
                if start_idx < len(projected_vertices) and end_idx < len(projected_vertices):
                    start_pos = projected_vertices[start_idx]
                    end_pos = projected_vertices[end_idx]
                    
                    if (-1000 <= start_pos[0] <= WIDTH + 1000 and -1000 <= start_pos[1] <= HEIGHT + 1000 and
                        -1000 <= end_pos[0] <= WIDTH + 1000 and -1000 <= end_pos[1] <= HEIGHT + 1000):
                        pygame.draw.line(screen, LIGHT_GREEN, start_pos, end_pos, 2)
            except Exception:
                continue
        
        # DRAW ORIGIN
        try:
            origin_3d = rotate_point_3d(0, 0, 0, camera_rotation_x, camera_rotation_y)
            origin_2d = project_3d_to_2d(origin_3d[0], origin_3d[1], origin_3d[2], camera_zoom, camera_pan_x, camera_pan_y)
            
            if 0 <= origin_2d[0] < WIDTH and 0 <= origin_2d[1] < HEIGHT:
                pygame.draw.circle(screen, RED, origin_2d, 8)
                pygame.draw.circle(screen, WHITE, origin_2d, 6)
        except Exception:
            pass
        
        # 3D NAVIGATION HELP
        if not taking_screenshot:
            try:
                help_text = [
                    "3D NAVIGATION:",
                    "Hold Left Click: Rotate View",
                    "Hold Right Click: Pan view", 
                    "Scroll Wheel: Zoom in/out"
                ]
                
                y_offset = HEIGHT - 120
                for i, text in enumerate(help_text):
                    color = CYAN if i == 0 else LIGHT_GRAY
                    help_surface = font_medium.render(text, True, color)
                    screen.blit(help_surface, (20, y_offset + i * 18))
            except Exception:
                pass
                
    except Exception:
        CENTER_X, CENTER_Y = get_center()
        error_text = font_large.render("3D VIEW ERROR", True, RED)
        text_rect = error_text.get_rect(center=(CENTER_X, CENTER_Y))
        screen.blit(error_text, text_rect)

def handle_mouse_wheel(event):
    """HANDLE ZOOM WITH MOUSE WHEEL"""
    global camera_zoom
    
    try:
        if view_mode == VIEW_MODE_3D:
            zoom_factor = 1.1 if event.y > 0 else 0.9
            camera_zoom = max(0.1, min(5.0, camera_zoom * zoom_factor))
    except Exception:
        pass

def handle_mouse_button_down(event):
    """START MOUSE DRAG OPERATIONS"""
    global mouse_dragging, last_mouse_pos, mouse_drag_mode
    
    try:
        if view_mode == VIEW_MODE_3D:
            if event.button == 1:
                mouse_dragging = True
                mouse_drag_mode = 'rotate'
                last_mouse_pos = pygame.mouse.get_pos()
            elif event.button == 3:
                mouse_dragging = True
                mouse_drag_mode = 'pan'
                last_mouse_pos = pygame.mouse.get_pos()
    except Exception:
        pass

def handle_mouse_button_up(event):
    """END MOUSE DRAG OPERATIONS"""
    global mouse_dragging, mouse_drag_mode
    
    try:
        if event.button in [1, 3]:
            mouse_dragging = False
            mouse_drag_mode = None
    except Exception:
        pass

def handle_mouse_motion(event):
    """HANDLE MOUSE DRAG FOR 3D NAVIGATION"""
    global camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y, last_mouse_pos
    
    try:
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
    except Exception:
        pass

def clamp(v, lo, hi): 
    try:
        return max(lo, min(hi, v))
    except:
        return v

def movavg(buf, val): 
    try:
        buf.append(val)
        return sum(buf)/len(buf)
    except:
        return val

def wrap360(a):
    try:
        while a < 0: a += 360
        while a >= 360: a -= 360
        return a
    except:
        return 0

def parse_line(line):
    try:
        out = {}
        for part in line.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip().lower()] = v.strip()
        return out
    except:
        return {}

def get_beam_angle(yaw_raw):
    """CALCULATE BEAM ANGLE WITH CALIBRATION"""
    try:
        if not calibrated:
            return movavg(beam_yaw_hist, 90.0)
        else:
            y = yaw_raw - yaw_offset
        
        y = wrap360(y)
        
        if 0.0 <= y <= 180.0:
            reversed_y = 180 - y
            smoothed_angle = movavg(beam_yaw_hist, reversed_y)
            # CLAMP ANGLE TO VALID RANGE
            return max(0.0, min(180.0, smoothed_angle))
        
        return None
    except:
        return None

def get_map_angle(yaw_raw):
    """CALCULATE MAP ANGLE WITH CALIBRATION"""
    try:
        if not calibrated:
            return movavg(map_yaw_hist, 90.0)
        else:
            y = yaw_raw - yaw_offset
        
        y = wrap360(y)
        
        if 0.0 <= y <= 180.0:
            reversed_y = 180 - y
            smoothed_angle = movavg(map_yaw_hist, reversed_y)
            # CLAMP ANGLE TO VALID RANGE
            return max(0.0, min(180.0, smoothed_angle))
        
        return None
    except:
        return None

def polar_to_xy(angle_deg, dist_cm):
    try:
        CENTER_X, CENTER_Y = get_center()
        r = dist_cm * SCALE
        a = math.radians(angle_deg)
        x = CENTER_X + r * math.cos(a)
        y = CENTER_Y - r * math.sin(a)
        return (int(x), int(y))
    except:
        return (0, 0)

def get_downloads_folder():
    """GET USER'S DOWNLOADS FOLDER PATH"""
    try:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                downloads_path = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
                if os.path.exists(downloads_path):
                    return downloads_path
        except:
            pass
        
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
        
        # REDRAW WITHOUT INSTRUCTION TEXT
        screen.fill(BLACK)
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
        pygame.display.flip()
        
        pygame.time.wait(50)
        
        downloads_dir = get_downloads_folder()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        view_suffix = "3D" if view_mode == VIEW_MODE_3D else "2D"
        filename = f"SurroundSense_Radar_{view_suffix}_{timestamp}.png"
        filepath = os.path.join(downloads_dir, filename)
        
        pygame.image.save(screen, filepath)
        
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
    try:
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
    except Exception:
        pass

def draw_radar_display():
    try:
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
            
        # SCANNING INSTRUCTIONS
        if scan_active and not screenshot_message and not taking_screenshot and not scan_paused:
            instruction_text = font_medium.render("ROTATE THE SENSOR VERY SLOW", True, WHITE)
            text_rect = instruction_text.get_rect(center=(CENTER_X, CENTER_Y + 35))
            screen.blit(instruction_text, text_rect)
            instruction_text2 = font_medium.render("Ensure the area is well-lit and the sensor is calibrated (press C to calibrate)", True, WHITE)
            text_rect2 = instruction_text2.get_rect(center=(CENTER_X, CENTER_Y + 65))
            screen.blit(instruction_text2, text_rect2)
            instruction_text3 = font_medium.render("If the app freezes, press X to restart", True, WHITE)
            text_rect3 = instruction_text3.get_rect(center=(CENTER_X, CENTER_Y + 90))
            screen.blit(instruction_text3, text_rect3)
        elif scan_paused and not screenshot_message and not taking_screenshot:
            paused_text = font_large.render("SCAN PAUSED - Press P to resume", True, ORANGE)
            text_rect = paused_text.get_rect(center=(CENTER_X, CENTER_Y + 50))
            screen.blit(paused_text, text_rect)
    except Exception:
        pass

def draw_scan_data():
    try:
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
    except Exception:
        pass

def draw_dotted_line(start_pos, end_pos, color, dot_size=1, spacing=2):
    """DRAW DOTTED LINE BETWEEN TWO POINTS"""
    try:
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
    except Exception:
        pass

def draw_beam(angle_deg, dist_cm):
    try:
        if angle_deg is None:
            return
        
        CENTER_X, CENTER_Y = get_center()
        # ENSURE VALID ANGLE AND DISTANCE
        angle_deg = max(0.0, min(180.0, angle_deg))
        dist_cm = max(0.0, min(MAX_CM, dist_cm))
        
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
    except Exception:
        pass

def draw_idle_screen():
    """DRAW IDLE SCREEN WHEN SCAN IS NOT ACTIVE"""
    try:
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
    except Exception:
        pass

def draw_screenshot_message():
    """DRAW SCREENSHOT SAVE STATUS MESSAGE"""
    global screenshot_message, screenshot_timer
    
    try:
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
    except Exception:
        pass

def draw_ui():
    global camera_zoom, camera_rotation_x, camera_rotation_y, camera_pan_x, camera_pan_y
    
    try:
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
                f"Angle: {beam_angle:.1f}°" if scan_active and beam_angle is not None else "Angle: —",
                f"Object: {sensor['object']}" if scan_active else "Object: —",
                f"Calibrated: {'YES' if calibrated else 'NO'}",
                f"View: {'3D' if view_mode == VIEW_MODE_3D else '2D'}",
                "",
                "R - Reset | C - Calibrate | V - Toggle View | P - Pause/Resume | S - Save PNG | X - Back to Idle"
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
                f"Angle: {beam_angle:.1f}°" if scan_active and beam_angle is not None else "Angle: —",
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
                "V: Switch between 2D/3D view",
                "X: Back to idle mode"
            ]
            draw_card(screen, panel_x, panel_y + 4*(card_height + spacing), panel_width, card_height,
                      "SENSOR & VIEW CONTROLS", controls_content, BLUE)
            
            # EXPORT/SAVE PANEL
            export_content = [
                "Press S to save screenshot",
                " ",
                "S: Saves current view to Downloads"
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
    except Exception:
        return None, None, None

# MAIN LOOP
running = True
beam_angle = None

try:
    while running:
        try:
            # EVENT HANDLING
            for e in pygame.event.get():
                try:
                    if e.type == pygame.QUIT:
                        running = False
                    elif e.type == pygame.VIDEORESIZE:
                        if not fullscreen and not minimized and not display_changing:
                            WIDTH = max(MIN_WIDTH, e.w)
                            HEIGHT = max(MIN_HEIGHT, e.h)
                            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    elif e.type == pygame.MOUSEWHEEL:
                        handle_mouse_wheel(e)
                    elif e.type == pygame.MOUSEBUTTONDOWN:
                        if minimized:
                            restore_btn, _, _ = draw_ui()
                            if restore_btn and restore_btn.collidepoint(e.pos):
                                minimized = False
                                safe_display_mode_change((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
                        else:
                            handle_mouse_button_down(e)
                    elif e.type == pygame.MOUSEBUTTONUP:
                        if not minimized:
                            handle_mouse_button_up(e)
                    elif e.type == pygame.MOUSEMOTION:
                        if not minimized:
                            handle_mouse_motion(e)
                    elif e.type == pygame.KEYDOWN:
                        if e.key == pygame.K_r:
                            scan_points.clear()
                            scan_active = True
                            scan_paused = False
                            map_yaw_hist.clear()
                            beam_yaw_hist.clear()
                            camera_zoom = 1.0
                            camera_rotation_x = -90
                            camera_rotation_y = 0
                            camera_pan_x = 0
                            camera_pan_y = 0
                        elif e.key == pygame.K_c:
                            yaw_offset = sensor["yaw_instant"] - 90.0
                            calibrated = True
                            map_yaw_hist.clear()
                            beam_yaw_hist.clear()
                            # INITIALIZE HISTORY BUFFERS WITH VALID VALUES
                            for _ in range(BEAM_SMOOTH_N):
                                beam_yaw_hist.append(90.0)
                            for _ in range(MAP_SMOOTH_N):
                                map_yaw_hist.append(90.0)
                            try:
                                ser.write(b"CALIB\n")
                                ser.flush()
                            except Exception:
                                pass
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
                            reset_to_idle()
                        elif e.key == pygame.K_F11:
                            fullscreen = not fullscreen
                            if fullscreen:
                                safe_display_mode_change((0, 0), pygame.FULLSCREEN)
                            else:
                                safe_display_mode_change((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
                        elif e.key == pygame.K_ESCAPE:
                            if fullscreen:
                                fullscreen = False
                                safe_display_mode_change((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
                except Exception:
                    continue

            # SKIP PROCESSING DURING DISPLAY CHANGES
            if display_changing:
                clock.tick(30)
                continue

            # SERIAL COMMUNICATION
            if ser and ser.in_waiting and scan_active and not scan_paused:
                try:
                    line = ser.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        parsed = parse_line(line)
                        
                        if "distance" in parsed:
                            try:
                                raw_dist = float(parsed["distance"])
                                sensor["distance_raw"] = raw_dist
                                current_distance = raw_dist
                                beam_distance = raw_dist
                            except:
                                pass
                        
                        if "yaw" in parsed:
                            try:
                                raw_yaw = wrap360(float(parsed["yaw"]))
                                sensor["yaw_instant"] = raw_yaw
                                sensor["yaw_raw"] = raw_yaw
                            except:
                                pass
                        
                        if "direction" in parsed: sensor["direction"] = parsed["direction"]
                        if "object" in parsed: sensor["object"] = parsed["object"]
                        if "gyro" in parsed: sensor["gyro"] = parsed["gyro"]
                except Exception:
                    pass

            # ANGLE CALCULATIONS AND BEAM UPDATE
            if scan_active and not scan_paused:
                try:
                    # CALCULATE BEAM ANGLE WITH CONTINUOUS UPDATE
                    new_beam_angle = get_beam_angle(sensor["yaw_instant"])
                    if new_beam_angle is not None:
                        beam_angle = new_beam_angle
                    
                    map_angle = get_map_angle(sensor["yaw_raw"])

                    # UPDATE SCAN POINTS
                    if map_angle is not None and 0 <= map_angle <= 180:
                        angle_key = int(round(map_angle))
                        has_object = sensor["object"].lower() != "none" and current_distance < MAX_CM
                        
                        display_distance = clamp(current_distance, 0.0, MAX_CM) if has_object else MAX_CM
                        
                        scan_points[angle_key] = {
                            'coord': polar_to_xy(angle_key, display_distance),
                            'has_object': has_object,
                            'distance': current_distance
                        }
                except Exception:
                    pass

            # RENDERING
            try:
                screen.fill(BLACK)
                
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

                pygame.display.flip()
                clock.tick(60)
            except Exception:
                screen.fill(BLACK)
                error_text = font_large.render("RENDERING ERROR - PRESS X TO GO BACK TO IDLE", True, RED)
                screen.blit(error_text, (50, HEIGHT // 2))
                pygame.display.flip()
                clock.tick(60)
                
        except Exception:
            try:
                screen.fill(BLACK)
                critical_text = font_large.render("CRITICAL ERROR - PRESS X TO GO BACK TO IDLE", True, RED)
                screen.blit(critical_text, (50, HEIGHT // 2))
                pygame.display.flip()
                clock.tick(10)
            except:
                pass

except Exception:
    print("FATAL ERROR OCCURRED")

finally:
    try:
        if ser and ser.is_open:
            ser.close()
    except:
        pass
    
    try:
        pygame.quit()
    except:
        pass