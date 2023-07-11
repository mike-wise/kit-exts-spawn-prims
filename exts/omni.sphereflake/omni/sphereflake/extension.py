import omni.ext
from .demo import DemoWindow
from .sfcontrols import SfControls
from .sfwindow import SfcWindow

# fflake8: noqa


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class SphereflakeBenchmarkExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _window_demo = None
    _window_sfcon = None
    _sfc = None

    def on_stage(self, ext_id):
        # print(f"on_stage - stage:{omni.usd.get_context().get_stage()}")
        self._window_sfcon.ensure_stage()

    def on_startup(self, ext_id):
        # print("[omni.example.spawn_prims] omni example spawn_prims startup <<<<<<<<<<<<<<<<<")
        # print(f"on_startup - stage:{omni.usd.get_context().get_stage()}")
        # self._window_demo = DemoWindow("Demo Window", width=300, height=300)
        self._sfc = SfControls()
        self._window_sfcon = SfcWindow("Sphereflake Controls", width=300, height=300, sfc=self._sfc)

    def on_shutdown(self):
        # print("[omni.example.spawn_prims] omni example spawn_prims shutdown")
        # self._window_demo.destroy()
        # self._window_demo = None
        self._window_sfcon.destroy()
        self._window_sfcon = None
        pass
