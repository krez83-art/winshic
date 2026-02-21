"""
Claude Screenshot v4
- 핫키: Win+Shift+C (영역 선택 캡처)
- 핫키: Win+Shift+V (현재 활성 창 캡처)
- 트레이 더블클릭: 영역 캡처
- 트레이 우클릭 메뉴: 영역 캡처, 창 선택 캡처
- 여러 장 누적 후 한번에 붙여넣기 가능
- 멀티 모니터 지원
- 시스템 트레이 아이콘
"""

import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab, Image, ImageDraw
from pynput import keyboard
import pystray
import os
from datetime import datetime
import threading
import queue
import ctypes
import ctypes.wintypes

# ============ 설정 ============
SAVE_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Claude_Screenshot")
HOTKEY_REGION = '<cmd>+<shift>+c'  # Win+Shift+C (영역 선택)
HOTKEY_WINDOW = '<cmd>+<shift>+v'  # Win+Shift+V (활성 창)
# =============================

# 누적 경로 리스트
screenshot_paths = []
# 이벤트 큐
event_queue = queue.Queue()


def get_virtual_screen_info():
    """전체 가상 스크린 정보 (멀티 모니터 포함)"""
    user32 = ctypes.windll.user32
    # SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN = 가상 스크린 왼쪽 상단
    # SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 가상 스크린 크기
    x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return x, y, width, height


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]


def get_window_rect_by_hwnd(hwnd):
    """hwnd로 창 영역 가져오기"""
    dwmapi = ctypes.windll.dwmapi
    rect = RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    result = dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect), ctypes.sizeof(rect)
    )
    if result == 0:
        return (rect.left, rect.top, rect.right, rect.bottom)
    user32 = ctypes.windll.user32
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right, rect.bottom)
    return None


def get_foreground_window_rect():
    """현재 활성화된 창의 영역 가져오기"""
    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    return get_window_rect_by_hwnd(hwnd)


def get_window_at_point(x, y):
    """특정 좌표의 최상위 창 hwnd 반환"""
    user32 = ctypes.windll.user32
    point = ctypes.wintypes.POINT(x, y)
    hwnd = user32.WindowFromPoint(point)
    if not hwnd:
        return None
    # 최상위 부모 창으로 올라감
    root_hwnd = user32.GetAncestor(hwnd, 2)  # GA_ROOT
    return root_hwnd if root_hwnd else hwnd


def copy_to_clipboard(text):
    """클립보드에 텍스트 복사 (Windows clip 명령어)"""
    import subprocess
    process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
    process.communicate(text.encode('utf-16-le'))


def flash_effect(region):
    """캡처 영역에 부드러운 페이드아웃 효과"""
    x1, y1, x2, y2 = region
    width = x2 - x1
    height = y2 - y1

    flash = tk.Tk()
    flash.overrideredirect(True)
    flash.geometry(f"{width}x{height}+{x1}+{y1}")
    flash.attributes('-alpha', 0.3)
    flash.attributes('-topmost', True)
    flash.configure(bg='white')

    # 페이드아웃 애니메이션
    def fade_out(alpha):
        if alpha <= 0:
            flash.destroy()
            return
        flash.attributes('-alpha', alpha)
        flash.after(20, lambda: fade_out(alpha - 0.03))

    flash.after(50, lambda: fade_out(0.3))
    flash.mainloop()


def take_screenshot(region, show_flash=False):
    """스크린샷 찍고 저장, 경로 누적"""
    global screenshot_paths

    os.makedirs(SAVE_DIR, exist_ok=True)

    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    filename = f"ss_{timestamp}.png"
    filepath = os.path.join(SAVE_DIR, filename)

    # 캡처
    img = ImageGrab.grab(bbox=region, all_screens=True)
    img.save(filepath, "PNG")

    # 경로 누적
    screenshot_paths.append(filepath)

    # 클립보드에 누적된 모든 경로 복사
    clipboard_text = "\n".join([f"Screenshot:{p}" for p in screenshot_paths])
    copy_to_clipboard(clipboard_text)

    # 플래시 효과
    if show_flash:
        flash_effect(region)


def run_region_selector():
    """영역 선택 창 실행 (멀티 모니터 지원)"""
    # 가상 스크린 정보 가져오기
    vx, vy, vw, vh = get_virtual_screen_info()

    root = tk.Tk()
    root.overrideredirect(True)  # 타이틀바 제거
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")  # 전체 가상 스크린 크기로 설정
    root.attributes('-alpha', 0.3)
    root.attributes('-topmost', True)
    root.configure(bg='gray')
    root.configure(cursor="cross")
    root.focus_force()

    canvas = tk.Canvas(root, bg='gray', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # 남은 횟수 표시 (실시간 업데이트용) - 화면 중앙에
    text_id = canvas.create_text(
        vw // 2, 50,
        text="",
        font=('맑은 고딕', 24, 'bold'),
        fill='white'
    )

    state = {'start_x': None, 'start_y': None, 'rect_id': None, 'cancelled': False}

    def update_count():
        if state['cancelled']:
            return
        remaining = event_queue.qsize() + 1
        canvas.itemconfig(text_id, text=f"남은횟수: {remaining}    (ESC: 취소)")
        root.after(100, update_count)

    update_count()

    def on_press(event):
        state['start_x'] = event.x
        state['start_y'] = event.y

    def on_drag(event):
        if state['rect_id']:
            canvas.delete(state['rect_id'])
        state['rect_id'] = canvas.create_rectangle(
            state['start_x'], state['start_y'], event.x, event.y,
            outline='red', width=2, fill='white', stipple='gray50'
        )

    def on_release(event):
        x1 = min(state['start_x'], event.x)
        y1 = min(state['start_y'], event.y)
        x2 = max(state['start_x'], event.x)
        y2 = max(state['start_y'], event.y)

        state['cancelled'] = True
        root.destroy()

        if x2 - x1 > 10 and y2 - y1 > 10:
            # 캔버스 좌표를 실제 스크린 좌표로 변환
            real_x1 = vx + x1
            real_y1 = vy + y1
            real_x2 = vx + x2
            real_y2 = vy + y2
            take_screenshot((real_x1, real_y1, real_x2, real_y2))

    def cancel(event=None):
        state['cancelled'] = True
        # ESC 누르면 큐 비우고 종료
        while not event_queue.empty():
            try:
                event_queue.get_nowait()
            except:
                pass
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Escape>", cancel)
    canvas.bind("<Escape>", cancel)

    root.mainloop()


def run_window_selector():
    """창 선택 캡처: 오버레이 표시 후 사용자가 클릭한 창을 캡처"""
    import time
    vx, vy, vw, vh = get_virtual_screen_info()

    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{vw}x{vh}+{vx}+{vy}")
    root.attributes('-alpha', 0.15)
    root.attributes('-topmost', True)
    root.configure(bg='gray')
    root.configure(cursor="hand2")
    root.focus_force()

    canvas = tk.Canvas(root, bg='gray', highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    canvas.create_text(
        vw // 2, vh // 2,
        text="캡처할 창을 클릭하세요\n(ESC: 취소)",
        font=('맑은 고딕', 36, 'bold'),
        fill='white'
    )

    def on_click(event):
        # 클릭 좌표 → 실제 스크린 좌표
        screen_x = vx + event.x
        screen_y = vy + event.y
        root.destroy()

        # 잠깐 대기 (오버레이 사라진 뒤 창 감지)
        time.sleep(0.15)

        hwnd = get_window_at_point(screen_x, screen_y)
        if hwnd:
            rect = get_window_rect_by_hwnd(hwnd)
            if rect:
                take_screenshot(rect, show_flash=True)

    def cancel(event=None):
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_click)
    root.bind("<Escape>", cancel)

    root.mainloop()


def cleanup_old_files():
    """오래된 파일 정리 (250개 초과시 전부 삭제)"""
    try:
        if not os.path.exists(SAVE_DIR):
            return

        files = [f for f in os.listdir(SAVE_DIR) if f.startswith('ss_') and f.endswith('.png')]

        if len(files) > 250:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)

            result = messagebox.askyesno(
                "Claude Screenshot",
                f"스크린샷 폴더에 파일이 {len(files)}개 있습니다.\n\n전부 삭제할까요?"
            )

            root.destroy()

            if result:
                deleted = 0
                for f in files:
                    try:
                        os.remove(os.path.join(SAVE_DIR, f))
                        deleted += 1
                    except:
                        pass

                root2 = tk.Tk()
                root2.withdraw()
                messagebox.showinfo("Claude Screenshot", f"{deleted}개 파일 삭제 완료")
                root2.destroy()
    except:
        pass


def on_hotkey_region():
    """영역 선택 핫키 (Win+Shift+C)"""
    global screenshot_paths

    # 큐가 비었으면 새 세션 → 리스트 클리어
    if event_queue.empty():
        screenshot_paths = []

    event_queue.put('region')


def on_hotkey_window():
    """활성 창 캡처 핫키 (Win+Shift+V)"""
    global screenshot_paths

    # 큐가 비었으면 새 세션 → 리스트 클리어
    if event_queue.empty():
        screenshot_paths = []

    event_queue.put('window')


def start_listener():
    """키보드 리스너 시작 (GlobalHotKeys 사용)"""
    hotkeys = keyboard.GlobalHotKeys({
        HOTKEY_REGION: on_hotkey_region,
        HOTKEY_WINDOW: on_hotkey_window
    })
    hotkeys.start()
    return hotkeys


def create_tray_icon():
    """트레이 아이콘 이미지 생성 (📷 카메라 스타일)"""
    size = 64
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 보라색 둥근 배경
    draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill='#8B5CF6')

    # 카메라 본체 (흰색)
    draw.rounded_rectangle([12, 20, 52, 48], radius=6, fill='white')

    # 카메라 렌즈 (보라색 원)
    draw.ellipse([24, 26, 40, 42], fill='#8B5CF6')

    # 플래시 부분
    draw.rectangle([18, 14, 28, 20], fill='white')

    return img


def on_tray_exit(icon, item):
    """트레이 메뉴에서 종료"""
    icon.stop()
    os._exit(0)


def on_tray_open_folder(icon, item):
    """스크린샷 폴더 열기"""
    import subprocess
    if os.path.exists(SAVE_DIR):
        subprocess.Popen(['explorer', SAVE_DIR])


def on_tray_window_select():
    """트레이 메뉴에서 창 선택 캡처"""
    global screenshot_paths
    if event_queue.empty():
        screenshot_paths = []
    event_queue.put('window_select')


def on_tray_double_click(icon, item):
    """트레이 더블클릭 → 영역 캡처"""
    on_hotkey_region()


def setup_tray():
    """시스템 트레이 설정"""
    icon_image = create_tray_icon()

    menu = pystray.Menu(
        pystray.MenuItem("📷 영역 캡처 (Win+Shift+C)", lambda icon, item: on_hotkey_region(), default=True),
        pystray.MenuItem("🪟 창 선택 캡처", lambda icon, item: on_tray_window_select()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("📁 폴더 열기", on_tray_open_folder),
        pystray.MenuItem("❌ 종료", on_tray_exit)
    )

    icon = pystray.Icon(
        "Claude Screenshot",
        icon_image,
        "Claude Screenshot\nWin+Shift+C: 영역\nWin+Shift+V: 창",
        menu
    )

    return icon


def main():
    # 폴더 미리 생성
    os.makedirs(SAVE_DIR, exist_ok=True)

    # 오래된 파일 정리 체크
    cleanup_old_files()

    # 키보드 리스너 시작
    listener = start_listener()
    last_check = datetime.now()

    # 트레이 아이콘 시작 (별도 스레드)
    tray_icon = setup_tray()
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    # 메인 루프 - 이벤트 큐 체크 + 리스너 상태 체크
    while True:
        try:
            event = event_queue.get(timeout=0.5)
            if event == 'region':
                run_region_selector()
            elif event == 'window':
                # 활성 창 캡처 (핫키)
                rect = get_foreground_window_rect()
                if rect:
                    take_screenshot(rect, show_flash=True)
            elif event == 'window_select':
                # 창 선택 캡처 (트레이 메뉴)
                run_window_selector()
        except queue.Empty:
            pass

        # 30초마다 리스너 상태 체크 (절전모드 복귀 대응)
        now = datetime.now()
        if (now - last_check).seconds >= 30:
            last_check = now
            if not listener.is_alive():
                # 리스너 죽었으면 재시작
                listener = start_listener()


if __name__ == "__main__":
    main()
