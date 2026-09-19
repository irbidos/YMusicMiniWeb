"""YMusic Mini: official Yandex Music in WebView2 plus a floating mini remote."""

import ctypes
import ctypes.wintypes
import json
import os
import sys
import threading
import time
import webview
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume


APP_TITLE = "YMusic Mini"
MUSIC_TITLE = "Yandex Music"
MUSIC_URL = "https://music.yandex.ru/"
PROFILE_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "YMusicMini",
    "WebView2Profile",
)
WINDOW_WIDTH = 500
WINDOW_HEIGHT = 180

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_TOP = 0
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_SHOWWINDOW = 0x0040
SW_RESTORE = 9

WM_APPCOMMAND = 0x0319
APPCOMMAND_MEDIA_NEXTTRACK = 0x000B
APPCOMMAND_MEDIA_PREVIOUSTRACK = 0x000C
APPCOMMAND_MEDIA_PLAY_PAUSE = 0x000E

WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001

VK_SPACE = 0x20
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

CHROME_WIDGET_CLASS = "Chrome_WidgetWin"
CHROME_RENDER_WIDGET_CLASS = "Chrome_RenderWidgetHostHWND"

MONITOR_DEFAULTTONEAREST = 2
SNAP_PX = 16

_PLAY_PAUSE_BUTTON_LABELS = ["Воспроизведение", "Пауза"]
_PREVIOUS_BUTTON_LABELS = ["Предыдущая песня", "Предыдущая композиция"]
_NEXT_BUTTON_LABELS = ["Следующая песня", "Следующая композиция"]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("union", _INPUT_UNION)]


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", ctypes.wintypes.DWORD),
    ]


_EnumChildProc = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
)

_user32 = ctypes.WinDLL("user32", use_last_error=True) if sys.platform == "win32" else None
if _user32:
    _user32.SetWindowPos.argtypes = [
        ctypes.wintypes.HWND, ctypes.wintypes.HWND,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint,
    ]
    _user32.SetWindowPos.restype = ctypes.c_int
    _user32.EnumChildWindows.argtypes = [ctypes.wintypes.HWND, _EnumChildProc, ctypes.wintypes.LPARAM]
    _user32.EnumChildWindows.restype = ctypes.wintypes.BOOL
    _user32.GetClassNameW.argtypes = [ctypes.wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
    _user32.GetClassNameW.restype = ctypes.c_int
    _user32.SendMessageW.argtypes = [
        ctypes.wintypes.HWND, ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
    ]
    _user32.PostMessageW.argtypes = [
        ctypes.wintypes.HWND, ctypes.wintypes.UINT,
        ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
    ]
    _user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
    _user32.IsWindowVisible.restype = ctypes.wintypes.BOOL
    _user32.GetWindowRect.argtypes = [
        ctypes.wintypes.HWND, ctypes.POINTER(_RECT),
    ]
    _user32.GetWindowRect.restype = ctypes.wintypes.BOOL
    _user32.MonitorFromWindow.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.DWORD]
    _user32.MonitorFromWindow.restype = ctypes.c_void_p
    _user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(_MONITORINFO)]
    _user32.GetMonitorInfoW.restype = ctypes.wintypes.BOOL


REMOTE_HTML = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><style>
*{box-sizing:border-box}html,body{height:100%;margin:0;background:#181818;color:#fff;font:13px Segoe UI,Arial;overflow:hidden}
body{display:grid;grid-template-rows:40px 1fr 36px;border:1px solid #444;border-radius:10px}
header{display:flex;align-items:center;gap:7px;padding:0 9px;background:#202020;user-select:none}
.title{flex:1;font-weight:600;font-size:15px}button{border:0;border-radius:16px;background:#383838;color:#fff;cursor:pointer;height:30px;min-width:32px;font:inherit}button:hover{background:#555}
.pin{padding:0 10px;font-size:11px}.pin.active{background:#ffd21f;color:#222}.close:hover{background:#b83232}
main{display:flex;align-items:center;gap:9px;padding:8px 10px}.cover{width:50px;height:50px;border-radius:8px;background:#333;display:grid;place-items:center;color:#ffd21f;font-size:22px}
 .meta{min-width:0;flex:1}.track,.artist{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.track{font-weight:600}.artist{margin-top:4px;color:#aaa;font-size:12px}.controls{display:flex;gap:6px}.play{background:#ffd21f;color:#222}.empty{color:#999;font-size:11px}.cover img{width:100%;height:100%;object-fit:cover;border-radius:8px;display:none}
.vol{display:flex;align-items:center;gap:6px;padding:0 10px;border-top:1px solid #333;background:#1a1a1a}
.vol input[type=range]{flex:1;height:4px;-webkit-appearance:none;appearance:none;background:#555;border-radius:2px;outline:none;cursor:pointer}
.vol input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:#ffd21f;cursor:pointer}
.vol-lbl{font-size:11px;color:#aaa;min-width:28px;text-align:center}
</style></head><body><header id="drag"><div class="title">YMusic Mini</div><button class="pin" id="pin">Закрепить</button><button id="min">−</button><button class="close" id="close">×</button></header>
 <main><div class="cover"><span id="coverMark">♪</span><img id="coverImage" alt=""></div><div class="meta"><div class="track" id="track">Откройте «Мою волну»</div><div class="artist" id="artist">Пульт Яндекс.Музыки</div></div><div class="controls"><button id="show">Открыть</button><button id="prev">◀</button><button class="play" id="toggle">▶</button><button id="next">▶|</button></div></main>
<div class="vol"><span class="vol-lbl" id="volIcon">🔊</span><input type="range" id="volSlider" min="0" max="100" value="100"><span class="vol-lbl" id="volValue">100</span></div>
<script>
const api=()=>window.pywebview&&window.pywebview.api;
function updateTrack(s){document.getElementById('track').textContent=s.title||'Откройте «Мою волну»';document.getElementById('artist').textContent=s.artist||'Пульт Яндекс.Музыки';document.getElementById('toggle').textContent=s.playing?'Ⅱ':'▶';var image=document.getElementById('coverImage');image.style.display=s.cover?'block':'none';document.getElementById('coverMark').style.display=s.cover?'none':'block';if(s.cover)image.src=s.cover;}
function updateVolume(v){document.getElementById('volSlider').value=v;document.getElementById('volValue').textContent=v;document.getElementById('volIcon').textContent=v==0?'🔇':v<33?'🔈':v<66?'🔉':'🔊';}
document.getElementById('pin').onclick=()=>{const b=document.getElementById('pin'),on=!b.classList.contains('active');if(api())api().set_always_on_top(on).then(ok=>{b.classList.toggle('active',!!ok);b.textContent=ok?'Закреплено':'Закрепить'})};
document.getElementById('min').onclick=()=>api()&&api().minimize();document.getElementById('close').onclick=()=>api()&&api().close();
document.getElementById('show').onclick=()=>api()&&api().show_music();
document.getElementById('prev').onclick=()=>api()&&api().previous();document.getElementById('next').onclick=()=>api()&&api().next();document.getElementById('toggle').onclick=()=>api()&&api().toggle();
document.getElementById('volSlider').oninput=function(){var v=this.value;document.getElementById('volValue').textContent=v;document.getElementById('volIcon').textContent=v==0?'🔇':v<33?'🔈':v<66?'🔉':'🔊';if(api())api().set_volume(v/100);};
if(api())api().get_volume().then(function(r){if(r&&r.volume!=null)updateVolume(r.volume);});
document.getElementById('drag').addEventListener('mousedown',e=>{if(e.target.closest('button, input')||!api())return;const x=e.screenX,y=e.screenY;api().begin_drag();const move=m=>api().move_window(m.screenX-x,m.screenY-y);const up=()=>{removeEventListener('mousemove',move);removeEventListener('mouseup',up)};addEventListener('mousemove',move);addEventListener('mouseup',up)});
</script></body></html>"""

MUSIC_STATE_SCRIPT = """(function(){
  var m=navigator.mediaSession&&navigator.mediaSession.metadata;
  return JSON.stringify({
    title:m&&m.title||document.title||'',
    artist:m&&m.artist||'',
    cover:m&&m.artwork&&m.artwork.length?m.artwork[m.artwork.length-1].src:'',
    playing:navigator.mediaSession&&navigator.mediaSession.playbackState==='playing'
  });
})()"""

PLAYBACK_STATE_SCRIPT = """(function(){
  var session=navigator.mediaSession;
  var playing=null;
  if(session) playing=session.playbackState==='playing';
  return JSON.stringify({playing:playing,mediaSessionState:session?session.playbackState:null});
})()"""

BUTTON_CENTER_SCRIPT = """(function(){
  var labels=%s;
  var bar=document.querySelector('section[class*="PlayerBar_root"]')||document;
  var btns=bar.querySelectorAll('button');
  for(var i=0;i<btns.length;i++){
    var label=btns[i].getAttribute('aria-label')||'';
    if(labels.indexOf(label)>=0){
      var r=btns[i].getBoundingClientRect();
      return JSON.stringify({
        x:Math.round(r.x+r.width/2),
        y:Math.round(r.y+r.height/2),
        label:label
      });
    }
  }
  return 'null';
})()"""


def _handle(window):
    if sys.platform != "win32":
        return None
    try:
        return window.native.Handle.ToInt64()
    except Exception:
        return _user32.FindWindowW(None, APP_TITLE)


def _decode_js_json(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _get_class_name(hwnd):
    try:
        buff = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, buff, 256)
        return buff.value
    except Exception:
        return ""


def _enum_children(parent):
    found = []

    def callback(hwnd, lparam):
        found.append(hwnd)
        return True

    _user32.EnumChildWindows(parent, _EnumChildProc(callback), 0)
    return found


def _collect_webview_hwnds(top):
    targets = []

    def walk(parent, depth=0):
        for child in _enum_children(parent):
            if _get_class_name(child).startswith(CHROME_WIDGET_CLASS):
                targets.append((depth, child))
            walk(child, depth + 1)

    walk(top)
    targets.sort(key=lambda item: -item[0])
    return targets


def _render_widget_hwnd(chrome_hwnd):
    for child in _enum_children(chrome_hwnd):
        if _get_class_name(child).startswith(CHROME_RENDER_WIDGET_CLASS):
            return child
    return None


def _find_chrome_window(window):
    """Find the WebView2 Chrome_WidgetWin window inside the music window."""
    top = _handle(window)
    if not top:
        return None
    targets = _collect_webview_hwnds(top)
    if not targets:
        return None
    for depth, hwnd in targets:
        if _render_widget_hwnd(hwnd):
            return hwnd
    return targets[0][1]


def _find_render_hwnd(window):
    chrome = _find_chrome_window(window)
    if not chrome:
        return None
    return _render_widget_hwnd(chrome) or chrome


def _is_visible(window):
    try:
        hwnd = _handle(window)
        if not hwnd:
            return True
        return bool(_user32.IsWindowVisible(hwnd))
    except Exception:
        return True


def _window_rect(hwnd):
    rect = _RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return rect


def _work_area(hwnd):
    monitor = _user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
    if not monitor:
        return None
    info = _MONITORINFO()
    info.cbSize = ctypes.sizeof(_MONITORINFO)
    if not _user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
        return None
    return info.rcWork


def _lparam(x, y):
    return (int(y) << 16) | (int(x) & 0xFFFF)


def _real_click(window, labels):
    """Send a real Win32 mouse click to the page at the button center."""
    raw = window.evaluate_js(BUTTON_CENTER_SCRIPT % repr(labels))
    parsed = _decode_js_json(raw)
    x, y = parsed.get("x"), parsed.get("y")
    if x is None or y is None:
        return False
    render = _find_render_hwnd(window)
    if not render:
        return False
    xy = _lparam(x, y)
    _user32.PostMessageW(render, WM_MOUSEMOVE, 0, xy)
    _user32.PostMessageW(render, WM_LBUTTONDOWN, MK_LBUTTON, xy)
    time.sleep(0.03)
    _user32.PostMessageW(render, WM_LBUTTONUP, 0, xy)
    return True


def _send_appcommand(window, command):
    hwnd = _find_chrome_window(window)
    if not hwnd:
        return False
    _user32.SendMessageW(hwnd, WM_APPCOMMAND, command << 16, 0)
    return True


def _send_key(vk):
    extra = ctypes.c_ulong(0)
    down = _INPUT(INPUT_KEYBOARD, _KEYBDINPUT(vk, 0, 0, 0, ctypes.pointer(extra)))
    up = _INPUT(INPUT_KEYBOARD, _KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, ctypes.pointer(extra)))
    _user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(down))
    time.sleep(0.03)
    _user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(up))


def _focus_and_key(window, vk):
    """Last-resort: focus the music window and press a real key, then hide back."""
    try:
        hwnd = _handle(window)
        if not hwnd:
            return False
        _user32.ShowWindow(hwnd, SW_RESTORE)
        _user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        _user32.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        _send_key(vk)
        return True
    except Exception:
        return False


def _playback_verdict(window):
    try:
        return _decode_js_json(window.evaluate_js(PLAYBACK_STATE_SCRIPT))
    except Exception:
        return {}


def _state_changed(before, after):
    return before.get("playing") is not None and before.get("playing") != after.get("playing")


def _music_track(window):
    try:
        state = _decode_js_json(window.evaluate_js(MUSIC_STATE_SCRIPT))
        return (state.get("title") or "", state.get("artist") or "", state.get("cover") or "")
    except Exception:
        return None


def _update_remote(remote, music):
    try:
        state = _decode_js_json(music.evaluate_js(MUSIC_STATE_SCRIPT))
        remote.evaluate_js("updateTrack(%s);" % json.dumps(state, ensure_ascii=False))
    except Exception:
        pass


def _poll_music_state(remote, music, stop_event):
    while not stop_event.is_set():
        _update_remote(remote, music)
        stop_event.wait(0.7)


class RemoteApi:
    def __init__(self, remote=None, music=None):
        self._remote = remote
        self._music = music
        self._drag_origin = None
        self.pinned = False
        self._allow_music_close = False
        self._stop_event = threading.Event()

    def set_always_on_top(self, enabled):
        self.pinned = bool(enabled)
        hwnd = _handle(self._remote)
        if not hwnd:
            return False
        z = HWND_TOPMOST if self.pinned else HWND_NOTOPMOST
        return bool(_user32.SetWindowPos(hwnd, z, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW))

    def begin_drag(self):
        try:
            self._drag_origin = (self._remote.x, self._remote.y)
            return True
        except Exception:
            return False

    def move_window(self, dx, dy):
        if not self._drag_origin:
            return False
        self._remote.move(self._drag_origin[0] + int(dx), self._drag_origin[1] + int(dy))
        self._snap_to_edges()
        return True

    def _snap_to_edges(self):
        if sys.platform != "win32":
            return
        hwnd = _handle(self._remote)
        if not hwnd:
            return
        rect = _window_rect(hwnd)
        work = _work_area(hwnd)
        if not rect or not work:
            return
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        x, y, snapped = rect.left, rect.top, False

        if abs(rect.left - work.left) <= SNAP_PX:
            x, snapped = work.left, True
        elif abs(rect.right - work.right) <= SNAP_PX:
            x, snapped = work.right - width, True

        if abs(rect.top - work.top) <= SNAP_PX:
            y, snapped = work.top, True
        elif abs(rect.bottom - work.bottom) <= SNAP_PX:
            y, snapped = work.bottom - height, True

        if snapped and (x, y) != (rect.left, rect.top):
            _user32.SetWindowPos(
                hwnd, 0, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER
            )

    def minimize(self):
        self._remote.minimize()

    def close(self):
        self._allow_music_close = True
        self._stop_event.set()
        self._music.destroy()
        self._remote.destroy()

    def show_music(self):
        self._music.show()
        self._music.restore()
        return True

    def get_volume(self):
        try:
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = s.Process
                if proc and "msedgewebview2" in proc.name().lower():
                    vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                    return {"volume": int(vol.GetMasterVolume() * 100), "muted": bool(vol.GetMute()), "found": True}
        except Exception:
            pass
        return {"volume": 100, "muted": False, "found": False}

    def set_volume(self, level):
        level = max(0.0, min(1.0, float(level)))
        try:
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                proc = s.Process
                if proc and "msedgewebview2" in proc.name().lower():
                    vol = s._ctl.QueryInterface(ISimpleAudioVolume)
                    vol.SetMasterVolume(level, None)
                    vol.SetMute(False, None)
                    return True
        except Exception:
            pass
        return False

    def toggle(self):
        before = _playback_verdict(self._music)
        was_visible = _is_visible(self._music)

        _real_click(self._music, _PLAY_PAUSE_BUTTON_LABELS)
        time.sleep(0.6)
        final = _playback_verdict(self._music)
        changed = _state_changed(before, final)

        if not changed:
            for _ in range(3):
                _send_appcommand(self._music, APPCOMMAND_MEDIA_PLAY_PAUSE)
                time.sleep(0.5)
                final = _playback_verdict(self._music)
                if _state_changed(before, final):
                    changed = True
                    break

        if not changed:
            _focus_and_key(self._music, VK_SPACE)
            time.sleep(0.5)
            final = _playback_verdict(self._music)
            changed = _state_changed(before, final)
            if not was_visible:
                try:
                    self._music.hide()
                except Exception:
                    pass

        return bool(changed)

    def previous(self):
        before = _music_track(self._music)
        _real_click(self._music, _PREVIOUS_BUTTON_LABELS)
        time.sleep(0.8)
        after = _music_track(self._music)
        if before is not None and after is not None and after != before:
            return True
        _send_appcommand(self._music, APPCOMMAND_MEDIA_PREVIOUSTRACK)
        time.sleep(0.8)
        after = _music_track(self._music)
        return bool(before is not None and after is not None and after != before)

    def next(self):
        before = _music_track(self._music)
        _real_click(self._music, _NEXT_BUTTON_LABELS)
        time.sleep(0.8)
        after = _music_track(self._music)
        if before is not None and after is not None and after != before:
            return True
        _send_appcommand(self._music, APPCOMMAND_MEDIA_NEXTTRACK)
        time.sleep(0.8)
        after = _music_track(self._music)
        return bool(before is not None and after is not None and after != before)


def main():
    music = webview.create_window(MUSIC_TITLE, MUSIC_URL, width=900, height=650, resizable=True)
    api = RemoteApi(music=music)
    remote = webview.create_window(
        APP_TITLE,
        html=REMOTE_HTML,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        resizable=False,
        frameless=True,
        easy_drag=False,
        js_api=api,
    )
    api._remote = remote

    def hide_music():
        if api._allow_music_close:
            return True
        music.hide()
        return False

    music.events.closing += hide_music
    threading.Thread(
        target=_poll_music_state,
        args=(remote, music, api._stop_event),
        daemon=True,
    ).start()
    webview.start(debug=False, private_mode=False, storage_path=PROFILE_DIR)


if __name__ == "__main__":
    main()