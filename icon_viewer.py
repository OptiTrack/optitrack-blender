import os

import bpy
import bpy.utils.previews


class IconsLoader:
    icons = None

    @classmethod
    def registering_icons(cls):
        if cls.icons is not None:
            return cls.icons

        # Creating a new preview collection
        icons_dict = bpy.utils.previews.new()

        # the path to icons folder
        my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")

        # Loading a preview thumbnail of a file and storing in the previews collection
        icon_ls = [
            "Motive",
            "Connect",
            "Stop",
            "Refresh",
            "RigidBody",
            "Awaiting",
            "Checkmark",
            "Pause",
            "Info",
            "Record",
            "RecordStop",
        ]
        for icon in icon_ls:
            icons_dict.load(icon, os.path.join(my_icons_dir, icon + ".png"), "IMAGE")

        cls.icons = icons_dict
        return icons_dict

    @classmethod
    def get_icon(cls, icon_name):
        if cls.icons is None:
            cls.registering_icons()
        return cls.icons.get(icon_name).icon_id

    @classmethod
    def unregistering_icons(cls):
        if cls.icons:
            bpy.utils.previews.remove(cls.icons)
            cls.icons = None
