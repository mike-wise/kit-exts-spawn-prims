import omni.ext
from .ovut import MatMan
from .sphereflake import SphereMeshFactory, SphereFlakeFactory
from .sfcontrols import SfControls
from .sfwindow import SfcWindow

# fflake8: noqa


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class SphereflakeBenchmarkExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _window_sfcon = None
    _matman: MatMan = None
    _smf: SphereMeshFactory = None
    _sff: SphereFlakeFactory = None
    _sfc: SfControls = None

    def on_stage(self, ext_id):
        self._window_sfcon.ensure_stage()

    def on_startup(self, ext_id):

        # Model objects
        self._matman = MatMan()
        self._smf = SphereMeshFactory(self._matman)
        self._sff = SphereFlakeFactory(self._matman, self._smf)

        # Controller objects
        self._sfc = SfControls(self._matman, self._smf, self._sff)

        # View objects
        self._window_sfcon = SfcWindow(sfc=self._sfc)

    def on_shutdown(self):
        self._window_sfcon.destroy()
        self._window_sfcon = None
        pass
