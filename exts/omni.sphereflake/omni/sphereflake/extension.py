import omni.ext
import omni.ui as ui
from omni.ui import color as clr
import omni.kit.commands as okc
import omni.usd
import time
import asyncio
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from .ovut import MatMan, delete_if_exists, write_out_syspath
from .spheremesh import SphereMeshFactory
from .sphereflake import SphereFlakeFactory
import nvidia_smi

# fflake8: noqa


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class SphereflakeBenchmarkExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _stage = None
    _total_quads: int = 0
    _matman: MatMan = None
    _floor_xdim = 5
    _floor_zdim = 5
    _bounds_visible = False
    _sf_size = 50
    _sf_radratio = 0.3
    _vsc_test8 = False

    def setup_environment(self, force: bool = False):
        ppathstr = "/World/Floor"
        if force:
            delete_if_exists(ppathstr)

        prim_path_sdf = Sdf.Path(ppathstr)

        prim: Usd.Prim = self._stage .GetPrimAtPath(prim_path_sdf)
        if not prim.IsValid():
            okc.execute('CreateMeshPrimWithDefaultXform',	prim_type="Plane", prim_path=ppathstr)
            # extent3f = SphereFlakeFactory.GetFlakeExtent(self.sff._depth, self._sf_size, self._sf_radratio)
            extent3f = self.sff.GetSnowFlakeBoundingBox()
            # self._floor_xdim = 4 + self._nsf_x
            # self._floor_zdim = 4 + self._nsf_z
            self._floor_xdim = extent3f[0] / 10
            self._floor_zdim = extent3f[2] / 10
            okc.execute('TransformMultiPrimsSRTCpp',
                        count=1,
                        paths=[ppathstr],
                        new_scales=[self._floor_xdim, 1, self._floor_zdim])
            baseurl = 'https://omniverse-content-production.s3.us-west-2.amazonaws.com'
            okc.execute('CreateDynamicSkyCommand',
                        sky_url=f'{baseurl}/Assets/Skies/2022_1/Skies/Dynamic/CumulusLight.usd',
                        sky_path='/Environment/sky')

            print(f"nvidia_smi.__file__:{nvidia_smi.__file__}")
            print(f"omni.ui.__file__:{omni.ui.__file__}")
            print(f"omni.ext.__file__:{omni.ext.__file__}")

    def ensure_stage(self):
        # print("ensure_stage")
        if self._stage is None:
            self._stage = omni.usd.get_context().get_stage()
            # print(f"ensure_stage got stage:{self._stage}")
            UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.y)
            self._total_quads = 0
            self.setup_environment()

    def create_billboard(self, primpath: str):
        UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.y)

        billboard = UsdGeom.Mesh.Define(self._stage, primpath)
        billboard.CreatePointsAttr([(-430, -145, 0), (430, -145, 0), (430, 145, 0), (-430, 145, 0)])
        billboard.CreateFaceVertexCountsAttr([4])
        billboard.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        billboard.CreateExtentAttr([(-430, -145, 0), (430, 145, 0)])
        texCoords = UsdGeom.PrimvarsAPI(billboard).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                                 UsdGeom.Tokens.varying)
        texCoords.Set([(0, 0), (1, 0), (1, 1), (0, 1)])
        return billboard

    def on_stage(self, ext_id):
        print(f"on_stage - stage:{omni.usd.get_context().get_stage()}")
        self.ensure_stage()

# Todo:
# Remove _nsf_x and _nsf_z into sff
# Remove sf_radratio into sff
# Remove _sf_size into smf (and sff?)

    def on_startup(self, ext_id):
        print("[omni.example.spawn_prims] omni example spawn_prims startup <<<<<<<<<<<<<<<<<")
        print(f"on_startup - stage:{omni.usd.get_context().get_stage()}")
        self._matman = MatMan()
        self._count = 0
        self._current_material_name = "Mirror"
        self._current_bbox_material_name = "Red_Glass"
        self._matkeys = self._matman.GetMaterialNames()
        self._window = ui.Window("Spawn Primitives", width=300, height=300)
        self._total_quads = 0
        self._sf_size = 50
        self._sf_radratio = 0.3

        self._sf_depth_but: ui.Button = None
        self._sf_spawn_but: ui.Button = None
        self._sf_nlat_but: ui.Button = None
        self._sf_nlng_but: ui.Button = None
        self._sf_radratio_slider: ui.Slider = None

        self._matbox: ui.ComboBox = None
        self._curprim = "Sphere"
        self._prims = ["Sphere", "Cube", "Cone", "Torus", "Cylinder", "Plane", "Disk", "Capsule",
                       "Billboard", "SphereMesh"]
        self._nsf_x = 1
        self._nsf_z = 1
        self._sf_gen_modes = ["DirectMesh", "AsyncMesh", "OmniSphere", "UsdSphere"]
        self._sf_gen_mode = "UsdSphere"
        self._sf_gen_forms = ["Classic", "Flat-8"]
        self._sf_gen_form = "Classic"
        self._sf_test2 = False
        self._write_out_syspath = False

        self.smf = SphereMeshFactory(self._matman)
        self.sff = SphereFlakeFactory(self._matman, self.smf)

        with self._window.frame:
            with ui.VStack():

                def toggle_bounds():
                    self.ensure_stage()
                    self._bounds_visible = not self._bounds_visible
                    self.sff.SetBoundsVisibility(self._bounds_visible)

                def on_click_billboard():
                    self.ensure_stage()

                    primpath = f"/World/Prim_Billboard_{self._count}"
                    billboard = self.create_billboard(primpath)

                    material = self.get_curmat_mat()
                    UsdShade.MaterialBindingAPI(billboard).Bind(material)

                def on_click_spheremesh():
                    self.ensure_stage()

                    self.smf.GenPrep()

                    matname = self.get_curmat_name()
                    cpt = Gf.Vec3f(0, self._sf_size, 0)
                    primpath = f"/World/SphereMesh_{self._count}"
                    self._count += 1
                    self.smf.CreateMesh(primpath, matname, cpt, self._sf_size)

                def on_click_sphereflake():
                    self.ensure_stage()

                    start_time = time.time()

                    sff = self.sff
                    sff._genmode = self.get_sf_genmode()
                    sff._genform = self.get_sf_genform()
                    sff._rad = self._sf_size
                    sff._radratio = self._sf_radratio_slider.get_value_as_float()
                    sff.GenPrep()

                    cpt = Gf.Vec3f(0, self._sf_size, 0)
                    primpath = f"/World/SphereFlake_{self._count}"

                    self._count += 1
                    depth = self.sff._depth
                    print(f"SphereFlake depth: {depth}")
                    sfmname = self.get_curmat_name()
                    sff.Generate(primpath, sfmname, depth, cpt)

                    elap = time.time() - start_time
                    self._statuslabel.text = f"SphereFlake took elapsed: {elap:.2f} s"
                    UpdateNQuads()
                    UpdateGpuMemory()

                async def gensflakes():

                    sff = self.sff
                    sff._matman = self._matman
                    sff._genmode = self.get_sf_genmode()
                    sff._genform = self.get_sf_genform()
                    sff._rad = self._sf_size
                    sff._radratio = self._sf_radratio
                    sff.GenPrep()

                    depth = self.sff._depth
                    sfmname = self.get_curmat_name()
                    bbmname = self.get_curmat_bbox_name()
                    new_count = sff.GenerateMany(depth, self._nsf_x, self._nsf_z,
                                                 sfmname, bbmname, self._bounds_visible)

                    self._count += new_count

                async def on_click_multi_sphereflake():
                    self.ensure_stage()
                    self.setup_environment(force=True)

                    start_time = time.time()
                    await gensflakes()
                    elap = time.time() - start_time

                    nflakes = self._nsf_x * self._nsf_z

                    self._statuslabel.text = f"{nflakes} flakes took elapsed: {elap:.2f} s"

                    UpdateNQuads()
                    UpdateGpuMemory()

                def spawnprim(primtype):
                    self.ensure_stage()
                    if primtype == "Billboard":
                        on_click_billboard()
                        return
                    elif primtype == "SphereMesh":
                        on_click_spheremesh()
                        return
                    primpath = f"/World/Prim_{primtype}_{self._count}"
                    okc.execute('CreateMeshPrimWithDefaultXform', prim_type=primtype, prim_path=primpath)

                    material = self.get_curmat_mat()
                    self._count += 1

                    okc.execute('TransformMultiPrimsSRTCpp',
                                count=1,
                                paths=[primpath],
                                new_scales=[1, 1, 1],
                                new_translations=[0, 50, 0])
                    prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
                    UsdShade.MaterialBindingAPI(prim).Bind(material)

                def on_click_sfdepth(x, y, button, modifier):
                    depth = self.sff._depth
                    depth += 1 if button == 1 else -1
                    if depth > 5:
                        depth = 0
                    self._sf_depth_but.text = f"Depth:{depth}"
                    self.sff._depth = depth
                    UpdateNQuads()
                    UpdateMQuads()
                    UpdateGpuMemory()

                def on_click_nlat(x, y, button, modifier):
                    nlat = self.smf._nlat
                    nlat += 1 if button == 1 else -1
                    if nlat > 16:
                        nlat = 2
                    self._sf_nlat_but.text = f"Nlat:{nlat}"
                    self.smf._nlat = nlat
                    UpdateNQuads()
                    UpdateMQuads()
                    UpdateGpuMemory()

                def on_click_nlng(x, y, button, modifier):
                    nlng = self.smf._nlng
                    nlng += 1 if button == 1 else -1
                    if nlng > 16:
                        nlng = 3
                    self._sf_nlng_but.text = f"Nlng:{nlng}"
                    self.smf._nlng = nlng
                    UpdateNQuads()
                    UpdateMQuads()
                    UpdateGpuMemory()

                def on_click_sfx(x, y, button, modifier):
                    self._nsf_x += 1 if button == 1 else -1
                    if self._nsf_x > 16:
                        self._nsf_x = 1
                    self._nsf_x_but.text = f"SF - x:{self._nsf_x}"
                    UpdateMQuads()
                    UpdateGpuMemory()

                def on_click_sfz(x, y, button, modifier):
                    self._nsf_z += 1 if button == 1 else -1
                    if self._nsf_z > 16:
                        self._nsf_z = 1
                    self._nsf_z_but.text = f"SF - z:{self._nsf_z}"
                    UpdateMQuads()
                    UpdateGpuMemory()

                def on_click_spawnprim():
                    spawnprim(self._curprim)

                def on_click_clearprims():
                    self.ensure_stage()
                    # check and see what we have missed
                    worldprim = self._stage.GetPrimAtPath("/World")
                    for child_prim in worldprim.GetAllChildren():
                        cname = child_prim.GetName()
                        prefix = cname.split("_")[0]
                        dodelete = prefix in ["SphereFlake", "SphereMesh", "Prim"]
                        if dodelete:
                            print(f"deleting {cname}")
                            cpath = child_prim.GetPrimPath()
                            okc.execute("DeletePrimsCommand", paths=[cpath])
                    self.smf.Clear()
                    self.sff.Clear()
                    self._count = 0

                def on_click_changeprim():
                    idx = self._prims.index(self._curprim)
                    idx += 1
                    if idx >= len(self._prims):
                        idx = 0
                    self._curprim = self._prims[idx]
                    self._sf_primtospawn_but.text = f"{self._curprim}"

                def UpdateNQuads():
                    genform = self.get_sf_genform()
                    nring = 9 if genform == "Classic" else 8
                    depth = self.sff._depth
                    nlat = self.smf._nlat
                    nlng = self.smf._nlng
                    ntris, nprims = SphereFlakeFactory.CalcTrisAndPrims(depth, nring, nlat, nlng)
                    elap = SphereFlakeFactory.GetLastGenTime()
                    self._sf_spawn_but.text = f"Spawn ShereFlake\n tris:{ntris:,} prims:{nprims:,}\ngen: {elap:.2f} s"

                def UpdateMQuads():
                    genform = self.get_sf_genform()
                    nring = 9 if genform == "Classic" else 8
                    depth = self.sff._depth
                    nlat = self.smf._nlat
                    nlng = self.smf._nlng
                    ntris, nprims = SphereFlakeFactory.CalcTrisAndPrims(depth, nring, nlat, nlng)
                    tottris = ntris*self._nsf_x*self._nsf_z
                    self._msf_spawn_but.text = f"Multi ShereFlake\ntris:{tottris:,} prims:{nprims:,}"

                def UpdateGpuMemory():
                    nvidia_smi.nvmlInit()

                    handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
                    # card id 0 hardcoded here, there is also a call to get all available card ids, so we could iterate

                    info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
                    om = float(1024*1024*1024)
                    msg = f"Mem GB tot:{info.total/om:.2f}: used:{info.used/om:.2f} free:{info.free/om:.2f}"
                    self._memlabel.text = msg

                if self._write_out_syspath:
                    write_out_syspath()

                # Material Combo Box
                idx = self._matkeys.index(self._current_material_name)
                if idx < 0:
                    idx = 0
                self._matbox = ui.ComboBox(idx, *self._matkeys).model

                # Bounds Material Combo Box
                idx = self._matkeys.index(self._current_bbox_material_name)
                if idx < 0:
                    idx = 0
                self._matbbox = ui.ComboBox(idx, *self._matkeys).model

                # SF Gen Mode Combo Box
                idx = self._sf_gen_modes.index(self._sf_gen_mode)
                if idx < 0:
                    idx = 0
                self._genmodebox = ui.ComboBox(idx, *self._sf_gen_modes).model

                # SF Form Combo Box
                idx = self._sf_gen_forms.index(self._sf_gen_form)
                if idx < 0:
                    idx = 0
                self._genformbox = ui.ComboBox(idx, *self._sf_gen_forms).model
                darkgreen = clr("#004000")
                darkblue = clr("#000040")
                darkred = clr("#400000")
                darkyellow = clr("#404000")
                darkpurple = clr("#400040")
                darkcyan = clr("#004040")

                ui.Button("Clear Prims",
                          style={'background_color': darkyellow},
                          clicked_fn=lambda: on_click_clearprims())
                ui.Button()
                with ui.HStack():
                    self._sf_spawn_but = ui.Button("Spawn Prim",
                                                   style={'background_color': darkred},
                                                   clicked_fn=lambda: on_click_spawnprim())
                    self._sf_primtospawn_but = ui.Button(f"{self._curprim}",
                                                         style={'background_color': darkpurple},
                                                         clicked_fn=lambda: on_click_changeprim())
                    self._tog_bounds = ui.Button("Toggle Bounds",
                                                 style={'background_color': darkcyan},
                                                 clicked_fn=lambda: toggle_bounds())

                with ui.VStack():
                    with ui.HStack():
                        self._sf_spawn_but = ui.Button("Spawn SphereFlake",
                                                       style={'background_color': darkred},
                                                       clicked_fn=lambda: on_click_sphereflake())
                        self._sf_depth_but = ui.Button(f"Depth:{self.sff._depth}",
                                                       style={'background_color': darkgreen},
                                                       mouse_pressed_fn=lambda x, y, b, m: on_click_sfdepth(x, y, b, m))
                        with ui.VStack():
                            nlat = self.smf._nlat
                            self._sf_nlat_but = ui.Button(f"Nlat:{nlat}",
                                                          style={'background_color': darkgreen},
                                                          mouse_pressed_fn=lambda x, y, b, m: on_click_nlat(x, y, b, m))
                            nlng = self.smf._nlng
                            self._sf_nlng_but = ui.Button(f"Nlng:{nlng}",
                                                          style={'background_color': darkgreen},
                                                          mouse_pressed_fn=lambda x, y, b, m: on_click_nlng(x, y, b, m))

                    with ui.HStack():
                        self._msf_spawn_but = ui.Button("Multi ShereFlake",
                                                        style={'background_color': darkred},
                                                        clicked_fn= # noqa : E251
                                                        lambda: asyncio.ensure_future(on_click_multi_sphereflake()))
                        with ui.VStack():
                            self._nsf_x_but = ui.Button(f"SF x: {self._nsf_x}",
                                                        style={'background_color': darkblue},
                                                        mouse_pressed_fn=lambda x, y, b, m: on_click_sfx(x, y, b, m))
                            self._nsf_z_but = ui.Button(f"SF z: {self._nsf_z}",
                                                        style={'background_color': darkblue},
                                                        mouse_pressed_fn=lambda x, y, b, m: on_click_sfz(x, y, b, m))
                            with ui.HStack():
                                ui.Label("Radius Ratio: ",
                                         style={'background_color': darkblue},
                                         width=50)
                                self._sf_radratio_slider = ui.FloatSlider(min=0.0, max=1.0, step=0.01,
                                                                          style={'background_color': darkblue}).model
                                self._sf_radratio_slider.set_value(self._sf_radratio)
                UpdateNQuads()
                UpdateMQuads()

                self._statuslabel = ui.Label("Status: Ready")
                self._memlabel = ui.Button("Memory tot/used/free", clicked_fn=UpdateGpuMemory)

    def get_curmat_mat(self):
        idx = self._matbox.get_item_value_model().as_int
        self._current_material_name = self._matkeys[idx]
        rv = self._matman.GetMaterial(self._current_material_name)
        return rv

    def get_curmat_name(self):
        idx = self._matbox.get_item_value_model().as_int
        self._current_material_name = self._matkeys[idx]
        rv = self._current_material_name
        return rv

    def get_curmat_bbox_name(self):
        idx = self._matbbox.get_item_value_model().as_int
        self._current_bbox_material_name = self._matkeys[idx]
        rv = self._current_bbox_material_name
        return rv

    def get_curmat_bbox_mat(self):
        idx = self._matbbox.get_item_value_model().as_int
        self._current_bbox_material_name = self._matkeys[idx]
        rv = self._matman.GetMaterial(self._current_bbox_material_name)
        return rv

    def get_sf_genmode(self):
        idx = self._genmodebox.get_item_value_model().as_int
        self._sf_genmode = self._sf_gen_modes[idx]
        rv = self._sf_genmode
        return rv

    def get_sf_genform(self):
        idx = self._genformbox.get_item_value_model().as_int
        self._sf_genform = self._sf_gen_forms[idx]
        rv = self._sf_genform
        return rv

    def on_shutdown(self):
        print("[omni.example.spawn_prims] omni example spawn_prims shutdown")
