# Blender RPC ver 1.0.0, made with love by Aesu <3

bl_info = {
    "name": "Blender RPC",
    "author": "Aesu",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "Edit > Preferences > Add-ons",
    "description": "Cute Discord Rich Presence for Blender",
    "category": "System",
}

import bpy
import json
import os
import struct
import sys
import time
import uuid

CLIENT_ID = "1571612367567982724"

# settings & lists --- self-explanatory

ICONS = [
    ("og", "Original Icon", "Original Blender icon, orange/blue/white"),
    ("black", "Black", "Simple black logo. Nice."),
    ("pink2", "Fuchsia", "Soft fuchsia."),
    ("pink1", "Pink", "Medium baby pink."),
    ("peach", "Peach", "Warm pastel peach"),
    ("lemon", "Lemon", "Juicy pastel lemon! (Might be underripened...)"),
    ("lime", "Lime", "Sour lime! Yuck!"),
    ("teal", "Teal", "I love teal. Okay who gaf."),
    ("blue", "Icy Blue", "Fresh and cool pastel blue."),
    ("discord", "Blurple", "Matches Discord's logo color!"),
    ("purple", "Purple", "Purpurl."),
    ("san-black", "Chocolate Cat", "Cute black kitty."),
    ("san-red", "HKitty", "Cute kitty that says hello."),
    ("san-pink", "Melody", "Pink bunny!"),
    ("san-yellow", "PomPom", "Yellow doggo!"),
    ("san-blue", "Cinna", "Cinnamon roll in pastel blue!"),
    ("san-lilac", "Kuro", "Purple imp."),
]

PHRASES = [
    ("working", "Working on {project}", "Classic and clean"),
    ("cute", "Making {project} cute ♡", "Cute mode"),
    ("batty", "Haunting {project} 🦇", "Goth mode"),
    ("sleepy", "Sleepy-blending {project} ᶻᶻ", "4 am energy"),
    ("custom", "Custom text", "Write your own"),
]

VERBS = [
    ("0", "Playing", ""),
    ("3", "Watching", ""),
    ("2", "Listening to", ""),
    ("5", "Competing in", "Blender esports 💀"),
]

MODES = {
    "OBJECT": "Object Mode",
    "EDIT_MESH": "Modeling",
    "SCULPT": "Sculpting",
    "PAINT_WEIGHT": "Weight Painting",
    "PAINT_TEXTURE": "Texture Painting",
    "PAINT_VERTEX": "Vertex Painting",
    "POSE": "Posing",
    "EDIT_ARMATURE": "Rigging",
}


# discord connection

class DiscordIPC:
    def __init__(self, client_id):
        self.client_id = client_id
        self.pipe = None

    def connect(self):
        for i in range(10):
            try:
                if sys.platform == "win32":
                    self.pipe = open(rf"\\?\pipe\discord-ipc-{i}", "r+b", buffering=0)
                else:
                    import socket
                    folder = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("TMPDIR") or "/tmp"
                    sock = socket.socket(socket.AF_UNIX)
                    sock.connect(os.path.join(folder, f"discord-ipc-{i}"))
                    self.pipe = sock
                self.send(0, {"v": 1, "client_id": self.client_id})
                return True
            except OSError:
                self.pipe = None
        return False

    def write(self, data):
        if sys.platform == "win32":
            self.pipe.write(data)
        else:
            self.pipe.sendall(data)

    def read(self, size):
        if sys.platform == "win32":
            return self.pipe.read(size)
        return self.pipe.recv(size)

    def send(self, op, payload):  # sending stuff
        body = json.dumps(payload).encode("utf-8")
        self.write(struct.pack("<II", op, len(body)) + body)
        op_back, length = struct.unpack("<II", self.read(8))
        return json.loads(self.read(length).decode("utf-8"))

    def set_activity(self, activity):
        self.send(1, {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": activity},
            "nonce": str(uuid.uuid4()),
        })

    def close(self):
        try:
            self.pipe.close()
        except Exception:
            pass
        self.pipe = None


discord = DiscordIPC(CLIENT_ID)
start_time = int(time.time())


# heartbeat --- NOTE: updates every 15 seconds!

def update_presence():
    prefs = bpy.context.preferences.addons[__package__].preferences
    try:
        if discord.pipe is None:
            if not discord.connect():
                return 15.0
        if not prefs.enabled:
            discord.set_activity(None)
            return 15.0
        if prefs.show_project:
            project = bpy.path.display_name_from_filepath(bpy.data.filepath) or "Untitled"
        else:
            project = "a secret project ♡"
        mode = MODES.get(bpy.context.mode, "Blending")

        if prefs.phrase == "custom":  # custom text
            text = prefs.custom_text
        else:
            text = dict((p[0], p[1]) for p in PHRASES)[prefs.phrase]
        text = text.replace("{project}", project)

        discord.set_activity({
            "type": int(prefs.verb),
            "details": text,
            "state": mode,
            "timestamps": {"start": start_time},
            "assets": {
                "large_image": prefs.icon,
                "large_text": f"Blender {bpy.app.version_string}",
            },
        })
    except (OSError, struct.error, ValueError):
        discord.close()
    return 15.0


# preferences panel

class CuteRPCPrefs(bpy.types.AddonPreferences):
    bl_idname = __package__

    enabled: bpy.props.BoolProperty(name="Show on Discord", default=True)
    icon: bpy.props.EnumProperty(name="Icon", items=ICONS, default="og")
    show_project: bpy.props.BoolProperty(name="Show Project Name", default=True)
    phrase: bpy.props.EnumProperty(name="Text", items=PHRASES, default="working")
    custom_text: bpy.props.StringProperty(name="Custom Text", default="Blending {project}")
    verb: bpy.props.EnumProperty(name="Status", items=VERBS, default="0")

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "enabled")
        layout.prop(self, "icon")
        layout.prop(self, "verb")
        layout.prop(self, "phrase")
        if self.phrase == "custom":
            layout.prop(self, "custom_text")
        layout.prop(self, "show_project")


def register(): # log on
    bpy.utils.register_class(CuteRPCPrefs)
    bpy.app.timers.register(update_presence, first_interval=2.0, persistent=True)


def unregister(): # log off
    if bpy.app.timers.is_registered(update_presence):
        bpy.app.timers.unregister(update_presence)
    discord.close()
    bpy.utils.unregister_class(CuteRPCPrefs)
