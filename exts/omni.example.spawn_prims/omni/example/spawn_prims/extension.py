import omni.ext
import omni.ui as ui
import omni.kit.commands as okc
import omni.usd
import os
import math
import time
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from typing import Tuple

# fflake8: noqa


class SphereMeshFactory():

    def __init__(self, stage, material, show_normals=False) -> None:
        self._stage = stage
        self._material = material
        self._show_normals = show_normals
        self._total_quads = 0
        pass

    def create_marker(self, name: str, material, cenpt: Gf.Vec3f, rad: float):
        print(f"create_marker {name}  {cenpt} {rad}")
        primpath = f"/World/markers/{name}"
        self.delete_if_exists(primpath)
        okc.execute('CreateMeshPrimWithDefaultXform', prim_type="Sphere", prim_path=primpath)
        sz = rad/100
        okc.execute('TransformMultiPrimsSRTCpp',
                    count=1,
                    paths=[primpath],
                    new_scales=[sz, sz, sz],
                    new_translations=[cenpt[0], cenpt[1], cenpt[2]])
        prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
        UsdShade.MaterialBindingAPI(prim).Bind(self._material)

    _show_normals = False

    def create(self, name: str, cenpt: Gf.Vec3f, radius: float, nlat: int, nlong: int):
        # This will create nlat*nlog quads or twice that many triangles
        # it will need nlat+1 vertices in the latitude direction and nlong vertices in the longitude direction
        # so a total of (nlat+1)*(nlong) vertices
        spheremesh = UsdGeom.Mesh.Define(self._stage, name)
        vtxcnt = int(0)
        pts = []
        nrm = []
        txc = []
        fvc = []
        idx = []
        polegap = 0.01  # prevents the vertices from being exactly on the poles
        for i in range(nlat+1):
            for j in range(nlong):
                theta = polegap + (i * (math.pi-2*polegap) / float(nlat))
                phi = j * 2 * math.pi / float(nlong)
                nx = math.sin(theta) * math.cos(phi)
                ny = math.cos(theta)
                nz = math.sin(theta) * math.sin(phi)
                x = radius * nx
                y = radius * ny
                z = radius * nz
                rawpt = Gf.Vec3f(x, y, z)
                nrmvek = Gf.Vec3f(nx, ny, nz)
                pt = rawpt + cenpt
                nrm.append(nrmvek)
                pts.append(pt)
                txc.append((x, y))
                if self._show_normals:
                    ptname = f"ppt_{i}_{j}"
                    npt = Gf.Vec3f(x+nx, y+ny, z+nz)
                    nmname = f"npt_{i}_{j}"
                    self.create_marker(ptname, "red", pt, 1)
                    self.create_marker(nmname, "blue", npt, 1)

        for i in range(nlat):
            offset = i * nlong
            for j in range(nlong):
                fvc.append(int(4))
                if j < nlong - 1:
                    i1 = offset+j
                    i2 = offset+j+1
                    i3 = offset+j+nlong+1
                    i4 = offset+j+nlong
                else:
                    i1 = offset+j
                    i2 = offset
                    i3 = offset+nlong
                    i4 = offset+j+nlong
                idx.extend([i1, i2, i3, i4])
                # print(f"i:{i} j:{j} vtxcnt:{vtxcnt} i1:{i1} i2:{i2} i3:{i3} i4:{i4}")

                vtxcnt += 1

        print(len(pts), len(txc), len(fvc), len(idx))
        spheremesh.CreatePointsAttr(pts)
        spheremesh.CreateNormalsAttr(nrm)
        spheremesh.CreateFaceVertexCountsAttr(fvc)
        spheremesh.CreateFaceVertexIndicesAttr(idx)
        spheremesh.CreateExtentAttr([(-radius, -radius, -radius), (radius, radius, radius)])
        texCoords = UsdGeom.PrimvarsAPI(spheremesh).CreatePrimvar("st",
                                                                  Sdf.ValueTypeNames.TexCoord2fArray,
                                                                  UsdGeom.Tokens.varying)
        texCoords.Set(txc)

        # prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
        UsdShade.MaterialBindingAPI(spheremesh).Bind(self._material)

        self._total_quads += len(fvc)  # face vertex counts

        return spheremesh


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class PrimsExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _stage = None
    _total_quads = 0

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

# Start of matman
    matlib = {}

    def make_preview_surface_tex_material(self, matname: str, fname: str):
        # This is all materials
        matpath = "/World/Looks"
        mlname = f'{matpath}/boardMat_{fname.replace(".","_")}'
        material = UsdShade.Material.Define(self._stage, mlname)
        pbrShader = UsdShade.Shader.Define(self._stage, f'{mlname}/PBRShader')
        pbrShader.CreateIdAttr("UsdPreviewSurface")
        pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
        pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

        material.CreateSurfaceOutput().ConnectToSource(pbrShader.ConnectableAPI(), "surface")
        stReader = UsdShade.Shader.Define(self._stage, f'{matpath}/stReader')
        stReader.CreateIdAttr('UsdPrimvarReader_float2')

        diffuseTextureSampler = UsdShade.Shader.Define(self._stage, f'{matpath}/diffuseTexture')
        diffuseTextureSampler.CreateIdAttr('UsdUVTexture')
        ASSETS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
        # print(f"ASSETS_DIRECTORY {ASSETS_DIRECTORY}")                    
        texfile = f"{ASSETS_DIRECTORY}\\{fname}"
        # print(texfile)
        # print(os.path.exists(texfile))
        diffuseTextureSampler.CreateInput('file', Sdf.ValueTypeNames.Asset).Set(texfile)
        diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(stReader.ConnectableAPI(),
                                                                                           'result')
        diffuseTextureSampler.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
        pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            diffuseTextureSampler.ConnectableAPI(), 'rgb')

        stInput = material.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
        stInput.Set('st')

        stReader.CreateInput('varname', Sdf.ValueTypeNames.Token).ConnectToSource(stInput)
        self.matlib[matname]["mat"] = material
        return material

    def splitrgb(self, rgb: str) -> Tuple[float, float, float]:
        sar = rgb.split(",")
        r = float(sar[0])
        g = float(sar[1])
        b = float(sar[2])
        return (r, g, b)

    def make_preview_surface_material(self, matname: str, rgb:str ):
        mtl_path = Sdf.Path(f"/World/Looks/Presurf_{matname}")
        mtl = UsdShade.Material.Define(self._stage, mtl_path)
        shader = UsdShade.Shader.Define(self._stage, mtl_path.AppendPath("Shader"))
        shader.CreateIdAttr("UsdPreviewSurface")
        rgbtup = self.splitrgb(rgb)
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(rgbtup)
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        mtl.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        # self.matlib[matname] = {"name": matname, "typ": "mtl", "mat": mtl}
        self.matlib[matname]["mat"] = mtl
        return mtl

    def copy_remote_material(self, matname, urlbranch):
        print("copy_remote_material")
        baseurl = 'https://omniverse-content-production.s3.us-west-2.amazonaws.com'
        url = f'{baseurl}/Materials/{urlbranch}.mdl'
        mpath = f'/World/Looks/{matname}'
        okc.execute('CreateMdlMaterialPrimCommand', mtl_url=url, mtl_name=matname, mtl_path=mpath)
        print(f"stagetype 1 {self._stage}")
        mtl: UsdShade.Material = UsdShade.Material(self._stage.GetPrimAtPath(mpath) )
        print(f"copy_remote_material {matname} {url} {mpath} {mtl}")
        # self.matlib[matname] = {"name": matname, "typ": "rgb", "mat": mtl}
        self.matlib[matname]["mat"] = mtl
        if matname not in self._matkeys:
            self._matkeys.append(matname)
        return mtl

    def realize_material(self, matname: str):
        typ = self.matlib[matname]["typ"]
        spec = self.matlib[matname]["spec"]
        if typ == "mtl":
            self.copy_remote_material(matname, spec)
        elif typ == "tex":
            self.make_preview_surface_tex_material(matname, spec)
        else:
            self.make_preview_surface_material(matname, spec)
        self.matlib[matname]["realized"] = True

    def setup_material(self, matname: str, typ: str, spec: str):
        print(f"setup_material {matname} {typ} {spec}")
        matpath = f"/World/Looks/{matname}"
        self.matlib[matname] = {"name": matname,
                                "typ": typ,
                                "mat": None,
                                "path": matpath,
                                "realized": False,
                                "spec": spec}

    def create_materials(self):
        self.setup_material("red", "rgb", "1,0,0")
        self.setup_material("green", "rgb", "0,1,0")
        self.setup_material("blue", "rgb", "0,0,1")
        self.setup_material("yellow", "rgb", "1,1,0")
        self.setup_material("cyan", "rgb", "0,1,1")
        self.setup_material("magenta", "rgb", "1,0,1")
        self.setup_material("white", "rgb", "1,1,1")
        self.setup_material("black", "rgb", "0,0,0")
        self.setup_material("Blue_Glass",  "mtl", "Base/Glass/Blue_Glass")
        self.setup_material("Red_Glass", "mtl", "Base/Glass/Red_Glass")
        self.setup_material("Green_Glass", "mtl", "Base/Glass/Green_Glass")
        self.setup_material("Clear_Glass", "mtl", "Base/Glass/Clear_Glass")
        self.setup_material("Mirror", "mtl", "Base/Glass/Mirror")
        self.setup_material("sunset_texture", "tex", "sunset.png")

    def get_curmat_mat(self):
        idx = self._matbox.get_item_value_model().as_int
        key = self._matkeys[idx]
        rv = self.get_material(key)
        return rv
    
    def get_material(self, key):
        if key in self.matlib:
            if not self.matlib[key]["realized"]:
                self.realize_material(key)
            rv = self.matlib[key]["mat"]
        else:
            rv = None
        return rv

    def get_curmat_name(self):
        idx = self._matbox.get_item_value_model().as_int
        rv = self._matkeys[idx]
        print(f"get_curmat:{idx}  {rv}")
        return rv

    def get_curmat_path(self):
        idx = self._matbox.get_item_value_model().as_int
        matname = self._matkeys[idx]
        rv = f"/World/Looks/{matname}"
        print(f"get_curmat_path:{idx}  {rv}")
        return rv
# end of matman

    def delete_if_exists(self, primpath):
        if self._stage.GetPrimAtPath(primpath):
            okc.execute("DeletePrimsCommand", paths=[primpath])  

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

    def cross_product(self, v1: Gf.Vec3f, v2: Gf.Vec3f) -> Gf.Vec3f:
        x = v1[1] * v2[2] - v1[2] * v2[1]
        y = v1[2] * v2[0] - v1[0] * v2[2]
        z = v1[0] * v2[1] - v1[1] * v2[0]
        rv = Gf.Vec3f(x, y, z)
        return rv

    org = Gf.Vec3f(0, 0, 0)
    xax = Gf.Vec3f(1, 0, 0)
    yax = Gf.Vec3f(0, 1, 0)
    zax = Gf.Vec3f(0, 0, 1)

    def create_sphereflake(self, sphflkname: str, matname: str, mxdepth: int, depth: int, basept: Gf.Vec3f, cenpt: Gf.Vec3f, rad: float, nlat: int=8, nlong: int=8 ):

        self.delete_if_exists(sphflkname)
        if depth == mxdepth:
            self._total_quads = 0
            self._start_time = time.time()

        xformPrim = UsdGeom.Xform.Define(self._stage, sphflkname)
        UsdGeom.XformCommonAPI(xformPrim).SetTranslate((0, 0, 0))
        UsdGeom.XformCommonAPI(xformPrim).SetRotate((0, 0, 0))

        meshname = sphflkname + "/SphereMesh"
        material = self.get_material(matname)

        sm = SphereMeshFactory(self._stage, material, show_normals=False)

        sm.create(meshname, cenpt,  rad, nlat, nlong)

        offvek = cenpt - basept
        len = offvek.GetLength()
        if len > 0:
            lxax = self.cross_product(offvek, self.yax)
            if lxax.GetLength() == 0:
                lxax = self.cross_product(offvek, self.zax)
            lxax.Normalize()
            lzax = self.cross_product(offvek, lxax)
            lzax.Normalize()
            lyax = offvek
            lyax.Normalize()
        else:
            lxax = self.xax
            lyax = self.yax
            lzax = self.zax

        if depth > 0:
            for i in range(8):
                theta = i * math.pi / 4
                x = rad * math.sin(theta)
                y = 0
                z = rad * math.cos(theta)
                nrad = rad / 4
                npt = x*lxax + y*lyax + z*lzax
                subname = f"{sphflkname}/sf_{i}"
                self.create_sphereflake(subname, matname, mxdepth, depth-1, cenpt, cenpt+1.25*npt, nrad)

        if depth == mxdepth:
            elap = time.time() - self._start_time
            print(f"create_sphereflake {sphflkname} {matname} {depth} {cenpt} {rad} totquads:{self._total_quads} in {elap:.3f} secs")

    def on_startup(self, ext_id):
        print("[omni.example.spawn_prims] omni example spawn_prims startup <<<<<<<<<<<<<<<<<")
        print(f"on_startup - stage:{omni.usd.get_context().get_stage()}")
        self._count = 0
        self.create_materials()
        self._current_material = "Mirror"
        # self._matkeys = [self._current_material]
        self._matkeys = list(self.matlib.keys())
        self._window = ui.Window("Spawn Primitives", width=300, height=300)
        self._total_quads = 0

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

                    matname = self.get_curmat_name()
                    matname = "Blue_Glass"
                    self.create_spheremesh("/World/SphereMesh", matname, Gf.Vec3f(0, 0, 0), 50, 8, 8)
                    print(f"spheremesh clicked (cwd:{os.getcwd()})")                  

                def on_click_sphereflake():
                    self.ensure_stage()

                    matname: str = self.get_curmat_name()
                    sz = 50
                    cpt = Gf.Vec3f(0, sz, 0)
                    primpath = "/World/SphereFlake"
                    depth = 3
                    self.create_sphereflake(primpath, matname, depth, depth, cpt, cpt, sz)
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

                ui.Button("Spawn Cube", clicked_fn=lambda: on_click("Cube"))
                ui.Button("Spawn Cone", clicked_fn=lambda: on_click("Cone"))
                ui.Button("Spawn Cylinder", clicked_fn=lambda: on_click("Cylinder"))
                ui.Button("Spawn Disk", clicked_fn=lambda: on_click("Disk"))
                ui.Button("Spawn Plane", clicked_fn=lambda: on_click("Plane"))
                ui.Button("Spawn Sphere", clicked_fn=lambda: on_click("Sphere"))
                ui.Button("Spawn Torus", clicked_fn=lambda: on_click("Torus"))
                ui.Button("Spawn Billboard", clicked_fn=lambda: on_click_billboard())
                ui.Button("Spawn ShereMesh", clicked_fn=lambda: on_click_spheremesh())
                ui.Button("Spawn ShereFlake", clicked_fn=lambda: on_click_sphereflake())

                idx = self._matkeys.index(self._current_material)
                if idx < 0:
                    idx = 0
                self._matbox = ui.ComboBox(idx, *self._matkeys).model

    def on_shutdown(self):
        print("[omni.example.spawn_prims] omni example spawn_prims shutdown")
