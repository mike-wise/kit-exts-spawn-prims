import omni.ext
import omni.ui as ui
import omni.kit.commands as okc
import omni.usd
import os
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from .ovut import MatMan, SphereMeshFactory, SphereFlakeFactory

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

    def make_initial_scene(self):
        ppathstr = "/World/Floor"
        prim_path_sdf = Sdf.Path(ppathstr)
        prim: Usd.Prim = self._stage .GetPrimAtPath(prim_path_sdf)
        if not prim.IsValid():
            okc.execute('CreateMeshPrimWithDefaultXform',	prim_type="Plane", prim_path=ppathstr)
            okc.execute('TransformMultiPrimsSRTCpp',
                        count=1,
                        paths=[ppathstr],
                        new_scales=[5, 1, 5])
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
            self.make_initial_scene()

    def create_billboard(self):
        UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.y)

        billboard = UsdGeom.Mesh.Define(self._stage, "/World/Billboard")
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
        self._current_material = "Mirror"
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

        with self._window.frame:
            with ui.VStack():

                def on_click_billboard():
                    self.ensure_stage()

                    billboard = self.create_billboard()

                    material = self.get_curmat_mat()
                    UsdShade.MaterialBindingAPI(billboard).Bind(material)
                    print(billboard)

                    print(f"billboard clicked (cwd:{os.getcwd()})")

                def on_click_spheremesh():
                    self.ensure_stage()

                    sm = SphereMeshFactory(self._matman)

                    matname = self.get_curmat_name()
                    sz = 50
                    cpt = Gf.Vec3f(0, sz, 0)
                    primpath = f"/World/SphereMesh_{self._count}"
                    self._count += 1
                    sm.Create(primpath, matname, cpt, sz, 8, 8)
                    print(f"spheremesh clicked (cwd:{os.getcwd()})")

                def on_click_sphereflake():
                    self.ensure_stage()

                    sff = SphereFlakeFactory(self._matman)

                    matname = self.get_curmat_name()
                    sz = 50
                    cpt = Gf.Vec3f(0, sz, 0)
                    primpath = f"/World/SphereFlake_{self._count}"
                    self._count += 1
                    depth = self._sf_depth
                    sff.Create(primpath, matname, depth, depth, cpt, cpt, sz, nlat=self._sf_nlat, nlong=self._sf_nlng)

                    okc.execute('TransformMultiPrimsSRTCpp',
                                count=1,
                                paths=[primpath],
                                new_scales=[1, 1, 1],
                                new_translations=[0, 0, 0])
                    print(f"sphereflake clicked (cwd:{os.getcwd()})")

                def on_click(primtype):
                    self.ensure_stage()
                    primpath = f"/World/{primtype}_{self._count}"
                    okc.execute('CreateMeshPrimWithDefaultXform',	prim_type=primtype, prim_path=primpath)

                    material = self.get_curmat_mat()
                    self._count += 1

                    okc.execute('TransformMultiPrimsSRTCpp',
                                count=1,
                                paths=[primpath],
                                new_scales=[1, 1, 1],
                                new_translations=[0, 50, 0])

                    print(f"on click binding:{material}")
                    prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
                    UsdShade.MaterialBindingAPI(prim).Bind(material)

                def on_click_sfdepth():
                    self._sf_depth += 1
                    if self._sf_depth > 5:
                        self._sf_depth = 0
                    self._sf_depth_but.text = f"Depth:{self._sf_depth}"
                    UpdateNQuads()

                def on_click_nlat():
                    self._sf_nlat += 1
                    if self._sf_nlat > 10:
                        self._sf_nlat = 2
                    self._sf_nlat_but.text = f"Nlat:{self._sf_nlat}"
                    UpdateNQuads()

                def on_click_nlng():
                    self._sf_nlng += 1
                    if self._sf_nlng > 10:
                        self._sf_nlng = 3
                    self._sf_nlng_but.text = f"Nlng:{self._sf_nlng}"
                    UpdateNQuads()

                def UpdateNQuads():
                    nquads = SphereFlakeFactory.CalcQuads(self._sf_depth, 8,  self._sf_nlat, self._sf_nlng)
                    self._sf_spawn_but.text = f"Spawn ShereFlake ({nquads} quads)"

                ui.Button("Spawn Cube", clicked_fn=lambda: on_click("Cube"))
                ui.Button("Spawn Cone", clicked_fn=lambda: on_click("Cone"))
                ui.Button("Spawn Cylinder", clicked_fn=lambda: on_click("Cylinder"))
                ui.Button("Spawn Disk", clicked_fn=lambda: on_click("Disk"))
                ui.Button("Spawn Plane", clicked_fn=lambda: on_click("Plane"))
                ui.Button("Spawn Sphere", clicked_fn=lambda: on_click("Sphere"))
                ui.Button("Spawn Torus", clicked_fn=lambda: on_click("Torus"))
                ui.Button("Spawn Billboard", clicked_fn=lambda: on_click_billboard())
                ui.Button("Spawn ShereMesh", clicked_fn=lambda: on_click_spheremesh())
                with ui.HStack():
                    self._sf_spawn_but = ui.Button("Spawn ShereFlake", clicked_fn=lambda: on_click_sphereflake())
                    self._sf_depth_but = ui.Button(f"Depth:{self._sf_depth}", clicked_fn=lambda: on_click_sfdepth())
                    with ui.VStack():
                        self._sf_nlat_but = ui.Button(f"Nlat:{self._sf_nlat}", clicked_fn=lambda: on_click_nlat())
                        self._sf_nlng_but = ui.Button(f"Nlng:{self._sf_nlng}", clicked_fn=lambda: on_click_nlng())

                UpdateNQuads()

                idx = self._matkeys.index(self._current_material)
                if idx < 0:
                    idx = 0
                self._matbox = ui.ComboBox(idx, *self._matkeys).model

    def get_curmat_mat(self):
        idx = self._matbox.get_item_value_model().as_int
        key = self._matkeys[idx]
        rv = self._matman.GetMaterial(key)
        return rv

    def get_curmat_name(self):
        idx = self._matbox.get_item_value_model().as_int
        rv = self._matkeys[idx]
        return rv

    def on_shutdown(self):
        print("[omni.example.spawn_prims] omni example spawn_prims shutdown")
