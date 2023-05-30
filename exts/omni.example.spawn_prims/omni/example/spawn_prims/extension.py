import omni.ext
import omni.ui as ui
import omni.kit.commands as okc
import omni.usd
import os
import time
import asyncio
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from .ovut import MatMan, SphereMeshFactory, SphereFlakeFactory, delete_if_exists

# fflake8: noqa


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class PrimsExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _stage = None
    _total_quads: int = 0
    _matman: MatMan = None
    _floor_xdim = 5
    _floor_zdim = 5

    def setup_environment(self, force: bool = False):
        ppathstr = "/World/Floor"
        if force:
            delete_if_exists(ppathstr)

        prim_path_sdf = Sdf.Path(ppathstr)

        prim: Usd.Prim = self._stage .GetPrimAtPath(prim_path_sdf)
        if not prim.IsValid():
            okc.execute('CreateMeshPrimWithDefaultXform',	prim_type="Plane", prim_path=ppathstr)
            self._floor_xdim = 4 + self._nsf_x
            self._floor_zdim = 4 + self._nsf_z
            okc.execute('TransformMultiPrimsSRTCpp',
                        count=1,
                        paths=[ppathstr],
                        new_scales=[self._floor_xdim, 1, self._floor_zdim])
            baseurl = 'https://omniverse-content-production.s3.us-west-2.amazonaws.com'
            okc.execute('CreateDynamicSkyCommand',
                        sky_url=f'{baseurl}/Assets/Skies/2022_1/Skies/Dynamic/CumulusLight.usd',
                        sky_path='/Environment/sky')

    def ensure_stage(self):
        print("ensure_stage")
        if self._stage is None:
            self._stage = omni.usd.get_context().get_stage()
            print(f"ensure_stage:{self._stage}")
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

    def on_startup(self, ext_id):
        print("[omni.example.spawn_prims] omni example spawn_prims startup <<<<<<<<<<<<<<<<<")
        print(f"on_startup - stage:{omni.usd.get_context().get_stage()}")
        self._matman = MatMan()
        self._count = 0
        self._current_material_name = "Mirror"
        self._matkeys = self._matman.GetMaterialNames()
        self._window = ui.Window("Spawn Primitives", width=300, height=300)
        self._total_quads = 0
        self._sf_depth = 3
        self._sf_nlat = 8
        self._sf_nlng = 8
        self._sf_depth_but: ui.Button = None
        self._sf_spawn_but: ui.Button = None
        self._sf_nlat_but: ui.Button = None
        self._sf_nlng_but: ui.Button = None
        self._matbox: ui.ComboBox = None
        self._curprim = "Sphere"
        self._prims = ["Sphere", "Cube", "Cone", "Torus", "Cylinder", "Plane", "Disk", "Capsule"]
        self._prims_created = []
        self._nsf_x = 1
        self._nsf_z = 1
        self._sf_gen_modes = ["DirectMesh", "AsyncMesh", "UsdSphere"]
        self._sf_gen_mode = "DirectMesh"

        with self._window.frame:
            with ui.VStack():

                def on_click_billboard():
                    self.ensure_stage()

                    primpath = f"/World/Billboard_{self._count}"
                    billboard = self.create_billboard(primpath)
                    self._prims_created.append(primpath)

                    material = self.get_curmat_mat()
                    UsdShade.MaterialBindingAPI(billboard).Bind(material)

                def on_click_spheremesh():
                    self.ensure_stage()

                    sm = SphereMeshFactory(self._matman, self._sf_nlat, self._sf_nlng)

                    matname = self.get_curmat_name()
                    sz = 50
                    cpt = Gf.Vec3f(0, sz, 0)
                    primpath = f"/World/SphereMesh_{self._count}"
                    self._count += 1
                    sm.CreateMesh(primpath, matname, cpt, sz)
                    self._prims_created.append(primpath)

                def on_click_sphereflake():                   
                    self.ensure_stage()
                    genmode = self.get_sf_genmode()

                    sff = SphereFlakeFactory(self._matman, genmode,  nlat=self._sf_nlat, nlong=self._sf_nlng)

                    genmode = self.get_sf_genmode()

                    matname = self.get_curmat_name()
                    sz = 50
                    cpt = Gf.Vec3f(0, sz, 0)
                    primpath = f"/World/SphereFlake_{self._count}"

                    self._count += 1
                    depth = self._sf_depth
                    sff.Generate(primpath, matname, depth, depth, cpt, sz)

                    self._prims_created.append(primpath)
                    UpdateNQuads()

                async def gensflakes():
                    genmode = self.get_sf_genmode()
                    sff = SphereFlakeFactory(self._matman, genmode,  nlat=self._sf_nlat, nlong=self._sf_nlng)
                    await asyncio.sleep(1)

                    matname = self.get_curmat_name()
                    sz = 50
                    cpt = Gf.Vec3f(0, sz, 0)
                    depth = self._sf_depth
                    ixoff = (float(self._nsf_x) / 2) - 0.5
                    izoff = (float(self._nsf_z) / 2) - 0.5
                    print(f"ixoff:{ixoff} izoff:{izoff} type(ixoff):{type(ixoff)} type(izoff):{type(izoff)}")
                    for ix in range(self._nsf_x):
                        for iz in range(self._nsf_z):
                            self._count += 1
                            primpath = f"/World/SphereFlake_{self._count}"
                            cpt = Gf.Vec3f((ix-ixoff)*sz*3, sz, (iz-izoff)*sz*3)
                            sff.Generate(primpath, matname, depth, depth, cpt, sz)
                            self._prims_created.append(primpath)
                            # await asyncio.sleep(1)

                async def on_click_multi_sphereflake():
                    self.ensure_stage()
                    self.setup_environment(force=True)

                    start_time = time.time()
                    await gensflakes()
                    elap = time.time() - start_time

                    nflakes = self._nsf_x * self._nsf_z

                    self._statuslable.text = f"{nflakes} flakes took elapsed: {elap:.2f} s"

                    UpdateNQuads()
                    print(f"sphereflake clicked (cwd:{os.getcwd()})")

                def spawnprim(primtype):
                    self.ensure_stage()
                    primpath = f"/World/{primtype}_{self._count}"
                    self._prims_created.append(primpath)
                    okc.execute('CreateMeshPrimWithDefaultXform',	prim_type=primtype, prim_path=primpath)

                    material = self.get_curmat_mat()
                    self._count += 1

                    okc.execute('TransformMultiPrimsSRTCpp',
                                count=1,
                                paths=[primpath],
                                new_scales=[1, 1, 1],
                                new_translations=[0, 50, 0])
                    prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
                    UsdShade.MaterialBindingAPI(prim).Bind(material)

                def on_click_sfdepth():
                    self._sf_depth += 1
                    if self._sf_depth > 5:
                        self._sf_depth = 0
                    self._sf_depth_but.text = f"Depth:{self._sf_depth}"
                    UpdateNQuads()
                    UpdateMQuads()

                def on_click_nlat():
                    self._sf_nlat += 1
                    if self._sf_nlat > 16:
                        self._sf_nlat = 2
                    self._sf_nlat_but.text = f"Nlat:{self._sf_nlat}"
                    UpdateNQuads()
                    UpdateMQuads()

                def on_click_nlng():
                    self._sf_nlng += 1
                    if self._sf_nlng > 16:
                        self._sf_nlng = 3
                    self._sf_nlng_but.text = f"Nlng:{self._sf_nlng}"
                    UpdateNQuads()
                    UpdateMQuads()

                def on_click_sfx():
                    self._nsf_x += 1
                    if self._nsf_x > 16:
                        self._nsf_x = 1
                    self._nsf_x_but.text = f"SF - x:{self._nsf_x}"
                    UpdateMQuads()

                def on_click_sfz():
                    self._nsf_z += 1
                    if self._nsf_z > 16:
                        self._nsf_z = 1
                    self._nsf_z_but.text = f"SF - z:{self._nsf_z}"
                    UpdateMQuads()

                def on_click_spawnprim():
                    spawnprim(self._curprim)

                def on_click_clearprims():
                    for primpath in self._prims_created:
                        delete_if_exists(primpath)
                    self._prims_created = []

                def on_click_changeprim():
                    idx = self._prims.index(self._curprim)
                    idx += 1
                    if idx >= len(self._prims):
                        idx = 0
                    self._curprim = self._prims[idx]
                    self._sf_primtospawn_but.text = f"{self._curprim}"

                def UpdateNQuads():
                    ntris = SphereFlakeFactory.CalcTris(self._sf_depth, 8,  self._sf_nlat, self._sf_nlng)
                    elap = SphereFlakeFactory.GetLastGenTime()
                    self._sf_spawn_but.text = f"Spawn ShereFlake\n{ntris} tris\nGenElap: {elap:.2f} s"

                def UpdateMQuads():
                    ntris = SphereFlakeFactory.CalcTris(self._sf_depth, 8,  self._sf_nlat, self._sf_nlng)
                    tottris = ntris*self._nsf_x*self._nsf_z
                    self._msf_spawn_but.text = f"Multi ShereFlake\n{tottris} tris"

                ui.Button("Clear Prims", clicked_fn=lambda: on_click_clearprims())
                with ui.HStack():
                    self._sf_spawn_but = ui.Button("Spawn Prim", clicked_fn=lambda: on_click_spawnprim())
                    self._sf_primtospawn_but = ui.Button(f"{self._curprim}", clicked_fn=lambda: on_click_changeprim())
                ui.Button("Spawn Billboard", clicked_fn=lambda: on_click_billboard())
                ui.Button("Spawn ShereMesh", clicked_fn=lambda: on_click_spheremesh())
                with ui.VStack():
                    with ui.HStack():
                        self._sf_spawn_but = ui.Button("Spawn ShereFlake", clicked_fn=lambda: on_click_sphereflake())
                        self._sf_depth_but = ui.Button(f"Depth:{self._sf_depth}", clicked_fn=lambda: on_click_sfdepth())
                        with ui.VStack():
                            self._sf_nlat_but = ui.Button(f"Nlat:{self._sf_nlat}", clicked_fn=lambda: on_click_nlat())
                            self._sf_nlng_but = ui.Button(f"Nlng:{self._sf_nlng}", clicked_fn=lambda: on_click_nlng())
                            
                    with ui.HStack():
                        self._msf_spawn_but = ui.Button("Multi ShereFlake", clicked_fn=
                                                        lambda: asyncio.ensure_future(on_click_multi_sphereflake()))
                        with ui.VStack():
                            self._nsf_x_but = ui.Button(f"SF x: {self._nsf_x}", clicked_fn=lambda: on_click_sfx())
                            self._nsf_z_but = ui.Button(f"SF z: {self._nsf_z}", clicked_fn=lambda: on_click_sfz())
                UpdateNQuads()
                UpdateMQuads()

                # Material Combo Box
                idx = self._matkeys.index(self._current_material_name)
                if idx < 0:
                    idx = 0
                self._matbox = ui.ComboBox(idx, *self._matkeys).model

                # SF Gen Mode Combo Box
                idx = self._sf_gen_modes.index(self._sf_gen_mode)
                if idx < 0:
                    idx = 0
                self._genmodebox = ui.ComboBox(idx, *self._sf_gen_modes).model

                self._statuslable = ui.Label("Status: Ready")

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
    
    def get_sf_genmode(self):
        idx = self._genmodebox.get_item_value_model().as_int
        self._sf_genmode = self._sf_gen_modes[idx]
        rv = self._sf_genmode
        return rv    

    def on_shutdown(self):
        print("[omni.example.spawn_prims] omni example spawn_prims shutdown")
