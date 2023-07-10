import omni.ext
import omni.ui as ui
import omni.kit.commands as okc
import omni.usd
import time
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from .ovut import MatMan, delete_if_exists, write_out_syspath
from .spheremesh import SphereMeshFactory
from .sphereflake import SphereFlakeFactory
import nvidia_smi

# fflake8: noqa


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
# class SfControls(ui.Window):
class SfControls():
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _stage = None
    _total_quads: int = 0
    _matman: MatMan = None
    _floor_xdim = 5
    _floor_zdim = 5
    _bounds_visible = False
    _sf_size = 50
    _vsc_test8 = False

    def __init__(self):
        print("SfControls __init__")

        self._matman = MatMan()
        self._count = 0
        self._current_material_name = "Mirror"
        self._current_bbox_material_name = "Red_Glass"
        self._matkeys = self._matman.GetMaterialNames()
        # self._window = ui.Window("Spawn Primitives", width=300, height=300)
        self._total_quads = 0
        self._sf_size = 50

        self._sf_depth_but: ui.Button = None
        self._sf_spawn_but: ui.Button = None
        self._sf_nlat_but: ui.Button = None
        self._sf_nlng_but: ui.Button = None
        self._sf_radratio_slider: ui.Slider = None

        self._matbox: ui.ComboBox = None
        self._prims = ["Sphere", "Cube", "Cone", "Torus", "Cylinder", "Plane", "Disk", "Capsule",
                       "Billboard", "SphereMesh"]
        self._curprim = self._prims[0]
        self._sf_gen_modes = SphereFlakeFactory.GetGenModes()
        self._sf_gen_mode = self._sf_gen_modes[0]
        self._sf_gen_forms = SphereFlakeFactory.GetGenForms()
        self._sf_gen_form = self._sf_gen_forms[0]
        self._genmodebox = ui.ComboBox(0, *self._sf_gen_modes).model
        self._genformbox = ui.ComboBox(0, *self._sf_gen_forms).model

        idx = self._matkeys.index(self._current_material_name)
        self._matbox = ui.ComboBox(idx, *self._matkeys).model
        idx = self._matkeys.index(self._current_bbox_material_name)
        self._matbbox = ui.ComboBox(idx, *self._matkeys).model

        self.smf = SphereMeshFactory(self._matman)
        self.sff = SphereFlakeFactory(self._matman, self.smf)

        self._write_out_syspath = False

        if self._write_out_syspath:
            write_out_syspath()

    def setup_environment(self, extent3f: Gf.Vec3f,  force: bool = False):
        ppathstr = "/World/Floor"
        if force:
            delete_if_exists(ppathstr)

        prim_path_sdf = Sdf.Path(ppathstr)

        prim: Usd.Prim = self._stage .GetPrimAtPath(prim_path_sdf)
        if not prim.IsValid():
            okc.execute('CreateMeshPrimWithDefaultXform',	prim_type="Plane", prim_path=ppathstr)

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

            # print(f"nvidia_smi.__file__:{nvidia_smi.__file__}")
            # print(f"omni.ui.__file__:{omni.ui.__file__}")
            # print(f"omni.ext.__file__:{omni.ext.__file__}")

    def ensure_stage(self):
        # print("ensure_stage")
        if self._stage is None:
            self._stage = omni.usd.get_context().get_stage()
            # print(f"ensure_stage got stage:{self._stage}")
            UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.y)
            self._total_quads = 0
            extent3f = self.sff.GetSphereFlakeBoundingBox()
            self.setup_environment(extent3f)

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

        self.ensure_stage()

# Todo:
# Remove _sf_size into smf (and sff?)

    def toggle_bounds(self):
        self.ensure_stage()
        self._bounds_visible = not self._bounds_visible
        self._tog_bounds_but.text = f"Bounds:{self._bounds_visible}"
        self.sff.ToggleBoundsVisiblity()

    def on_click_billboard(self):
        self.ensure_stage()

        primpath = f"/World/Prim_Billboard_{self._count}"
        billboard = self.create_billboard(primpath)

        material = self.get_curmat_mat()
        UsdShade.MaterialBindingAPI(billboard).Bind(material)

    def on_click_spheremesh(self):
        self.ensure_stage()

        self.smf.GenPrep()

        matname = self.get_curmat_name()
        cpt = Gf.Vec3f(0, self._sf_size, 0)
        primpath = f"/World/SphereMesh_{self._count}"
        self._count += 1
        self.smf.CreateMesh(primpath, matname, cpt, self._sf_size)

    def update_radratio(self):
        if self._sf_radratio_slider is not None:
            val = self._sf_radratio_slider.get_value_as_float()
            self.sff._radratio = val

    def on_click_sphereflake(self):
        self.ensure_stage()

        start_time = time.time()

        sff = self.sff
        sff._genmode = self.get_sf_genmode()
        sff._genform = self.get_sf_genform()
        sff._rad = self._sf_size
        # print(f"slider: {type(self._sf_radratio_slider)}")
        # sff._radratio = self._sf_radratio_slider.get_value_as_float()
        self.update_radratio()
        sff._sf_matname = self.get_curmat_name()
        sff._bb_matname = self.get_curmat_bbox_name()

        cpt = Gf.Vec3f(0, self._sf_size, 0)
        primpath = f"/World/SphereFlake_{self._count}"

        self._count += 1
        sff.Generate(primpath, cpt)

        elap = time.time() - start_time
        self._statuslabel.text = f"SphereFlake took elapsed: {elap:.2f} s"
        self.UpdateNQuads()
        self.UpdateGpuMemory()

    async def gensflakes(self):

        sff = self.sff

        sff._matman = self._matman
        sff._genmode = self.get_sf_genmode()
        sff._genform = self.get_sf_genform()
        sff._rad = self._sf_size
        # print(f"slider: {type(self._sf_radratio_slider)}")
        # sff._radratio = self._sf_radratio_slider.get_value_as_float()
        self.update_radratio()

        sff._sf_matname = self.get_curmat_name()

        sff._make_bounds_visible = self._bounds_visible
        sff._bb_matname = self.get_curmat_bbox_name()

        new_count = sff.GenerateMany()

        self._count += new_count

    async def on_click_multi_sphereflake(self):
        self.ensure_stage()
        extent3f = self.sff.GetSphereFlakeBoundingBox()
        self.setup_environment(extent3f, force=True)

        start_time = time.time()
        await self.gensflakes()
        elap = time.time() - start_time

        nflakes = self.sff._nsfx * self.sff._nsfz

        self._statuslabel.text = f"{nflakes} flakes took elapsed: {elap:.2f} s"

        self.UpdateNQuads()
        self.UpdateGpuMemory()

    def spawnprim(self, primtype):
        self.ensure_stage()
        if primtype == "Billboard":
            self.on_click_billboard()
            return
        elif primtype == "SphereMesh":
            self.on_click_spheremesh()
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

    def round_increment(self, val: int, butval: bool, maxval: int, minval: int = 0):
        inc = 1 if butval else -1
        val += inc
        if val > maxval:
            val = minval
        if val < minval:
            val = maxval
        return val

    def on_click_sfdepth(self, x, y, button, modifier):
        depth = self.round_increment(self.sff._depth, button == 1, 5, 0)
        self._sf_depth_but.text = f"Depth:{depth}"
        self.sff._depth = depth
        self.UpdateNQuads()
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_nlat(self, x, y, button, modifier):
        nlat = self.round_increment(self.smf._nlat, button == 1, 16, 3)
        self._sf_nlat_but.text = f"Nlat:{nlat}"
        self.smf._nlat = nlat
        self.UpdateNQuads()
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_nlng(self, x, y, button, modifier):
        nlng = self.round_increment(self.smf._nlng, button == 1, 16, 3)
        self._sf_nlng_but.text = f"Nlng:{nlng}"
        self.smf._nlng = nlng
        self.UpdateNQuads()
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_sfx(self, x, y, button, modifier):
        nsfx = self.round_increment(self.sff._nsfx, button == 1, 20, 1)
        self._nsf_x_but.text = f"SF - x:{nsfx}"
        self.sff._nsfx = nsfx
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_sfy(self, x, y, button, modifier):
        nsfy = self.round_increment(self.sff._nsfx, button == 1, 20, 1)
        self._nsf_y_but.text = f"SF - y:{nsfy}"
        self.sff._nsfy = nsfy
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_sfz(self, x, y, button, modifier):
        nsfz = self.round_increment(self.sff._nsfz, button == 1, 20, 1)
        self._nsf_z_but.text = f"SF - z:{nsfz}"
        self.sff._nsfz = nsfz
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_spawnprim(self):
        self.spawnprim(self._curprim)

    def on_click_clearprims(self):
        self.ensure_stage()
        # check and see what we have missed
        worldprim = self._stage.GetPrimAtPath("/World")
        for child_prim in worldprim.GetAllChildren():
            cname = child_prim.GetName()
            prefix = cname.split("_")[0]
            dodelete = prefix in ["SphereFlake", "SphereMesh", "Prim"]
            if dodelete:
                # print(f"deleting {cname}")
                cpath = child_prim.GetPrimPath()
                okc.execute("DeletePrimsCommand", paths=[cpath])
        self.smf.Clear()
        self.sff.Clear()
        self._count = 0

    def on_click_changeprim(self):
        idx = self._prims.index(self._curprim) + 1
        if idx >= len(self._prims):
            idx = 0
        self._curprim = self._prims[idx]
        self._sf_primtospawn_but.text = f"{self._curprim}"

    def UpdateNQuads(self):
        ntris, nprims = self.sff.CalcTrisAndPrims()
        elap = SphereFlakeFactory.GetLastGenTime()
        if self._sf_depth_but is not None:
            self._sf_spawn_but.text = f"Spawn ShereFlake\n tris:{ntris:,} prims:{nprims:,}\ngen: {elap:.2f} s"

    def UpdateMQuads(self):
        ntris, nprims = self.sff.CalcTrisAndPrims()
        tottris = ntris*self.sff._nsfx*self.sff._nsfz
        if self._msf_spawn_but is not None:
            self._msf_spawn_but.text = f"Multi ShereFlake\ntris:{tottris:,} prims:{nprims:,}"

    def UpdateGpuMemory(self):
        nvidia_smi.nvmlInit()

        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
        # card id 0 hardcoded here, there is also a call to get all available card ids, so we could iterate

        info = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        om = float(1024*1024*1024)
        msg = f"GPU Mem tot:  {info.total/om:.2f}: used:  {info.used/om:.2f} free:  {info.free/om:.2f} GB"
        msg += f"\n Materials fetched: {self._matman.fetchCount} skipped: {self._matman.fetchCount}"
        self._memlabel.text = msg

    def get_curmat_mat(self):
        idx = self._matbox.get_item_value_model().as_int
        self._current_material_name = self._matkeys[idx]
        return self._matman.GetMaterial(self._current_material_name)

    def get_curmat_name(self):
        idx = self._matbox.get_item_value_model().as_int
        self._current_material_name = self._matkeys[idx]
        return self._current_material_name

    def get_curmat_bbox_name(self):
        idx = self._matbbox.get_item_value_model().as_int
        self._current_bbox_material_name = self._matkeys[idx]
        return self._current_bbox_material_name

    def get_curmat_bbox_mat(self):
        idx = self._matbbox.get_item_value_model().as_int
        self._current_bbox_material_name = self._matkeys[idx]
        return self._matman.GetMaterial(self._current_bbox_material_name)

    def get_sf_genmode(self):
        if not self._genmodebox:
            return self._sf_gen_modes[0]
        idx = self._genmodebox.get_item_value_model().as_int
        return self._sf_gen_modes[idx]

    def get_sf_genform(self):
        if not self._genformbox:
            return self._sf_gen_forms[0]
        idx = self._genformbox.get_item_value_model().as_int
        return self._sf_gen_forms[idx]
