import omni.ext  # this needs to be included in an extension's extension.py
from .ovut import MatMan, write_out_syspath, write_out_path
from .sphereflake import SphereMeshFactory, SphereFlakeFactory
from .sfcontrols import SfControls
from .sfwindow import SfcWindow
import omni.usd
from omni.services.core import main

# Omni imports
import omni.client
import omni.usd_resolver

import os
# import contextlib
# @contextlib.asynccontextmanager


def build_sf_set(sx: int = 0, nx: int = 1, nnx: int = 1,
                 sy: int = 0, ny: int = 1, nny: int = 1,
                 sz: int = 0, nz: int = 1, nnz: int = 1,
                 matname: str = "Mirror"):
    # to test open a browser at http://localhost:8211/docs or 8011 or maybe 8111
    stageid = omni.usd.get_context().get_stage_id()
    pid = os.getpid()
    msg = f"build_sf_set - x: {sx} {nx} {nnx} - y: {sy} {ny} {nny} - z: {sz} {nz} {nnz} mat:{matname}"
    msg += f" - stageid: {stageid} pid:{pid}"
    print(msg)
    matman = MatMan()
    smf = SphereMeshFactory(matman)
    sff = SphereFlakeFactory(matman, smf)
    sff.p_sf_matname = matname
    sff.p_nsfx = nnx
    sff.p_nsfy = nny
    sff.p_nsfz = nnz
    # sff.GenerateManySubcube(sx, sy, sz, nx, ny, nz)
    return msg


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
        _stageid = omni.usd.get_context().get_stage_id()
        self._stageid = _stageid
        pid = os.getpid()
        print(f"[omni.sphereflake] SphereflakeBenchmarkExtension on_stage - stageid: {_stageid} pid:{pid}")
        self._window_sfcon.ensure_stage()

    def WriteOutPathAndSysPath(self, basename="d:/nv/ov/sphereflake_benchmark"):
        write_out_syspath(f"{basename}_syspath.txt")
        write_out_path(f"{basename}_path.txt")

    def on_startup(self, ext_id):
        self._stageid = omni.usd.get_context().get_stage_id()
        pid = os.getpid()
        print(f"[omni.sphereflake] SphereflakeBenchmarkExtension on_startup - stageid:{self._stageid} pid:{pid}")

        # Write out syspath and path
        # self.WriteOutPathAndSysPath()

        # Register endpoints
        main.register_endpoint("get", "/sphereflake/build-sf-set", build_sf_set, tags=["Sphereflakes"])

        # Model objects
        self._matman = MatMan()
        self._smf = SphereMeshFactory(self._matman)
        self._sff = SphereFlakeFactory(self._matman, self._smf)

        # Controller objects
        self._sfc = SfControls(self._matman, self._smf, self._sff)

        # View objects
        self._window_sfcon = SfcWindow(sfc=self._sfc)

    def on_shutdown(self):
        print("[omni.sphereflake] SphereflakeBenchmarkExtension no_shutdown")
        self._window_sfcon.destroy()
        self._window_sfcon = None
        main.deregister_endpoint("get", "/sphereflake/build-sf-set")
