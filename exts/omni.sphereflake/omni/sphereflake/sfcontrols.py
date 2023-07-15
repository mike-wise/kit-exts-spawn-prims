import omni.ext
# import omni.ui as ui
import omni.kit.commands as okc
import omni.usd
import time
import datetime
import json
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from .ovut import MatMan, delete_if_exists, write_out_syspath, truncf
from .spheremesh import SphereMeshFactory
from .sphereflake import SphereFlakeFactory
import nvidia_smi

# fflake8: noqa


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
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
    sfw = None  # We can't give this a type because it would be a circular reference
    p_writelog = True

    def __init__(self, matman: MatMan, smf: SphereMeshFactory, sff: SphereFlakeFactory):
        print("SfControls __init__")

        self._matman = matman
        self._count = 0
        self._current_material_name = "Mirror"
        self._current_bbox_material_name = "Red_Glass"
        self._matkeys = self._matman.GetMaterialNames()
        self._total_quads = 0
        self._sf_size = 50

        # self._sf_matbox: ui.ComboBox = None
        self._prims = ["Sphere", "Cube", "Cone", "Torus", "Cylinder", "Plane", "Disk", "Capsule",
                       "Billboard", "SphereMesh"]
        self._curprim = self._prims[0]
        self._sf_gen_modes = SphereFlakeFactory.GetGenModes()
        self._sf_gen_mode = self._sf_gen_modes[0]
        self._sf_gen_forms = SphereFlakeFactory.GetGenForms()
        self._sf_gen_form = self._sf_gen_forms[0]
        # self._genmodebox = ui.ComboBox(0, *self._sf_gen_modes).model
        # self._genformbox = ui.ComboBox(0, *self._sf_gen_forms).model

        self.smf = smf
        self.sff = sff

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
        self._stage = omni.usd.get_context().get_stage()
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

    # def get_bool_model(self, option_name: str):
    #     bool_model = ui.SimpleBoolModel()
    #     return bool_model

    def toggle_write_log(self):
        self.p_writelog = not self.p_writelog
        print(f"toggle_write_log is now:{self.p_writelog}")

    def toggle_bounds(self):
        self.ensure_stage()
        self._bounds_visible = not self._bounds_visible
        self.sfw._tog_bounds_but.text = f"Bounds:{self._bounds_visible}"
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
        if self.sfw._sf_radratio_slider is not None:
            val = self.sfw._sf_radratio_slider.get_value_as_float()
            self.sff.p_radratio = val

    def on_click_sphereflake(self):
        self.ensure_stage()

        start_time = time.time()

        sff = self.sff
        sff.p_genmode = self.get_sf_genmode()
        sff.p_genform = self.get_sf_genform()
        sff.p_rad = self._sf_size
        # print(f"slider: {type(self._sf_radratio_slider)}")
        # sff._radratio = self._sf_radratio_slider.get_value_as_float()
        self.update_radratio()
        sff.p_sf_matname = self.get_curmat_name()
        sff.p_bb_matname = self.get_curmat_bbox_name()

        cpt = Gf.Vec3f(0, self._sf_size, 0)
        primpath = f"/World/SphereFlake_{self._count}"

        self._count += 1
        sff.Generate(primpath, cpt)

        elap = time.time() - start_time
        self.sfw._statuslabel.text = f"SphereFlake took elapsed: {elap:.2f} s"
        self.UpdateNQuads()
        self.UpdateGpuMemory()

    async def generate_sflakes(self):

        sff = self.sff

        sff._matman = self._matman
        sff.p_genmode = self.get_sf_genmode()
        sff.p_genform = self.get_sf_genform()
        sff.p_rad = self._sf_size
        # print(f"slider: {type(self._sf_radratio_slider)}")
        # sff._radratio = self._sf_radratio_slider.get_value_as_float()
        self.update_radratio()

        sff.p_sf_matname = self.get_curmat_name()

        sff.p_make_bounds_visible = self._bounds_visible
        sff.p_bb_matname = self.get_curmat_bbox_name()

        new_count = sff.GenerateMany()

        self._count += new_count

    async def on_click_multi_sphereflake(self):
        self.ensure_stage()
        extent3f = self.sff.GetSphereFlakeBoundingBox()
        self.setup_environment(extent3f, force=True)

        start_time = time.time()
        await self.generate_sflakes()
        elap = time.time() - start_time

        nflakes = self.sff.p_nsfx * self.sff.p_nsfz

        self.sfw._statuslabel.text = f"{nflakes} flakes took elapsed: {elap:.2f} s"

        self.UpdateNQuads()
        self.UpdateGpuMemory()
        ntris, nprims = self.sff.CalcTrisAndPrims()
        gpuinfo = self._gpuinfo
        om = float(1024*1024*1024)
        # msg = f"GPU Mem tot:  {gpuinfo.total/om:.2f}: used:  {gpuinfo.used/om:.2f} free:  {gpuinfo.free/om:.2f} GB"
        if self.p_writelog:
            rundict = {"1-genmode": self.sff.p_genmode,
                       "1-genform": self.sff.p_genform,
                       "1-depth": self.sff.p_depth,
                       "1-rad": self.sff.p_rad,
                       "1-radratio": self.sff.p_radratio,
                       "1-nsfx": self.sff.p_nsfx,
                       "1-nsfy": self.sff.p_nsfy,
                       "1-nsfz": self.sff.p_nsfz,
                       "2-tris": ntris,
                       "2-prims": nprims,
                       "2-nflakes": nflakes,
                       "2-elapsed": truncf(elap, 3),
                       "3-gpu_gbmem_tot": truncf(gpuinfo.total/om, 3),
                       "3-gpu_gbmem_used": truncf(gpuinfo.used/om, 3),
                       "3-gpu_gbmem_free": truncf(gpuinfo.free/om, 3),
                       }
            self.WriteRunLog(rundict)

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

    def on_click_writerunlog(self):
        self.p_writelog = not self.p_writelog
        self.sfw._sf_writerunlog_but.text = f"Write Perf Log: {self.p_writelog}"

    def round_increment(self, val: int, butval: bool, maxval: int, minval: int = 0):
        inc = 1 if butval else -1
        val += inc
        if val > maxval:
            val = minval
        if val < minval:
            val = maxval
        return val

    def on_click_sfdepth(self, x, y, button, modifier):
        depth = self.round_increment(self.sff.p_depth, button == 1, 5, 0)
        self.sfw._sf_depth_but.text = f"Depth:{depth}"
        self.sff.p_depth = depth
        self.UpdateNQuads()
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_nlat(self, x, y, button, modifier):
        nlat = self.round_increment(self.smf.p_nlat, button == 1, 16, 3)
        self._sf_nlat_but.text = f"Nlat:{nlat}"
        self.smf.p_nlat = nlat
        self.UpdateNQuads()
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_nlng(self, x, y, button, modifier):
        nlng = self.round_increment(self.smf.p_nlng, button == 1, 16, 3)
        self._sf_nlng_but.text = f"Nlng:{nlng}"
        self.smf.p_nlng = nlng
        self.UpdateNQuads()
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_sfx(self, x, y, button, modifier):
        nsfx = self.round_increment(self.sff.p_nsfx, button == 1, 20, 1)
        self.sfw._nsf_x_but.text = f"SF - x:{nsfx}"
        self.sff.p_nsfx = nsfx
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def toggle_partial_render(self):
        self.sff.p_partialRender = not self.sff.p_partialRender
        self.sfw._partial_render_but.text = f"Partial Render: {self.sff.p_partialRender}"

    def on_click_parital_sfsx(self, x, y, button, modifier):
        tmp = self.round_increment(self.sff.p_partial_ssfx, button == 1, self.sff.p_nsfx-1, 0)
        self.sfw._part_nsf_sx_but.text = f"SF partial sx: {tmp}"
        self.sff.p_partial_ssfx = tmp
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_parital_sfsy(self, x, y, button, modifier):
        tmp = self.round_increment(self.sff.p_partial_ssfy, button == 1, self.sff.p_nsfy-1, 0)
        self.sfw._part_nsf_sy_but.text = f"SF partial sy: {tmp}"
        self.sff.p_partial_ssfy = tmp
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_parital_sfsz(self, x, y, button, modifier):
        tmp = self.round_increment(self.sff.p_partial_ssfz, button == 1, self.sff.p_nsfz-1, 0)
        self.sfw._part_nsf_sz_but.text = f"SF partial sz: {tmp}"
        self.sff.p_partial_ssfz = tmp
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_parital_sfnx(self, x, y, button, modifier):
        tmp = self.round_increment(self.sff.p_partial_nsfx, button == 1, self.sff.p_nsfx, 1)
        self.sfw._part_nsf_nx_but.text = f"SF partial nx: {tmp}"
        self.sff.p_partial_nsfx = tmp
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_parital_sfny(self, x, y, button, modifier):
        tmp = self.round_increment(self.sff.p_partial_nsfy, button == 1, self.sff.p_nsfy, 1)
        self.sfw._part_nsf_ny_but.text = f"SF partial ny: {tmp}"
        self.sff.p_partial_nsfy = tmp
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_parital_sfnz(self, x, y, button, modifier):
        tmp = self.round_increment(self.sff.p_partial_nsfz, button == 1, self.sff.p_nsfz, 1)
        self.sfw._part_nsf_nz_but.text = f"SF partial nz: {tmp}"
        self.sff.p_partial_nsfz = tmp
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_sfy(self, x, y, button, modifier):
        nsfy = self.round_increment(self.sff.p_nsfy, button == 1, 20, 1)
        self.sfw._nsf_y_but.text = f"SF - y:{nsfy}"
        self.sff.p_nsfy = nsfy
        self.UpdateMQuads()
        self.UpdateGpuMemory()

    def on_click_sfz(self, x, y, button, modifier):
        nsfz = self.round_increment(self.sff.p_nsfz, button == 1, 20, 1)
        self.sfw._nsf_z_but.text = f"SF - z:{nsfz}"
        self.sff.p_nsfz = nsfz
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
        self.sfw._sf_primtospawn_but.text = f"{self._curprim}"

    def UpdateNQuads(self):
        ntris, nprims = self.sff.CalcTrisAndPrims()
        elap = SphereFlakeFactory.GetLastGenTime()
        if self.sfw._sf_depth_but is not None:
            self.sfw._sf_spawn_but.text = f"Spawn ShereFlake\n tris:{ntris:,} prims:{nprims:,}\ngen: {elap:.2f} s"

    def UpdateMQuads(self):
        ntris, nprims = self.sff.CalcTrisAndPrims()
        tottris = ntris*self.sff.p_nsfx*self.sff.p_nsfz
        if self.sfw._msf_spawn_but is not None:
            self.sfw._msf_spawn_but.text = f"Multi ShereFlake\ntris:{tottris:,} prims:{nprims:,}"

    def UpdateGpuMemory(self):
        nvidia_smi.nvmlInit()

        handle = nvidia_smi.nvmlDeviceGetHandleByIndex(0)
        # card id 0 hardcoded here, there is also a call to get all available card ids, so we could iterate

        gpuinfo = nvidia_smi.nvmlDeviceGetMemoryInfo(handle)
        self._gpuinfo = gpuinfo
        om = float(1024*1024*1024)
        msg = f"GPU Mem tot:  {gpuinfo.total/om:.2f}: used:  {gpuinfo.used/om:.2f} free:  {gpuinfo.free/om:.2f} GB"
        refcnt = self._matman.fetchCount
        ftccnt = self._matman.fetchCount
        skpcnt = self._matman.skipCount
        msg += f"\n Materials ref:{refcnt} fetched: {ftccnt} skipped: {skpcnt}"
        self.sfw._memlabel.text = msg

    def get_curmat_mat(self):
        if self.sfw._sf_matbox is not None:
            idx = self.sfw._sf_matbox.get_item_value_model().as_int
            self._current_material_name = self._matkeys[idx]
        return self._matman.GetMaterial(self._current_material_name)

    def get_curmat_name(self):
        if self.sfw._sf_matbox is not None:
            idx = self.sfw._sf_matbox.get_item_value_model().as_int
            self._current_material_name = self._matkeys[idx]
        return self._current_material_name

    def get_curmat_bbox_name(self):
        if self.sfw._bb_matbox is not None:
            idx = self.sfw._bb_matbox.get_item_value_model().as_int
            self._current_bbox_material_name = self._matkeys[idx]
        return self._current_bbox_material_name

    def get_curmat_bbox_mat(self):
        if self.sfw._bb_matbox is not None:
            idx = self.sfw._bb_matbox.get_item_value_model().as_int
            self._current_bbox_material_name = self._matkeys[idx]
        return self._matman.GetMaterial(self._current_bbox_material_name)

    def get_sf_genmode(self):
        if self.sfw._genmodebox is None:
            return self._sf_gen_modes[0]
        idx = self.sfw._genmodebox.get_item_value_model().as_int
        return self._sf_gen_modes[idx]

    def get_sf_genform(self):
        if self.sfw._genformbox is None:
            return self._sf_gen_forms[0]
        idx = self.sfw._genformbox.get_item_value_model().as_int
        return self._sf_gen_forms[idx]

    def WriteRunLog(self, rundict=None):

        if rundict is None:
            rundict = {}
        rundict["0-date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        jline = json.dumps(rundict, sort_keys=True)

        fname = "d:/nv/ov/log.txt"
        with open(fname, "a") as f:
            f.write(f"{jline}\n")

        print("wrote log")
