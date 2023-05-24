import omni.ext
import omni.ui as ui
import omni.kit.commands as okc
import omni.usd
import os
import math
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade


# fflake8: noqa
# Functions and vars are available to other extension as usual in python: `example.python_ext.some_public_function(x)`
def some_public_function(x: int):
    print("[omni.example.spawn_prims] some_public_function was called with x: ", x)
    return x ** x


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class PrimsExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    _stage = None

    def ensure_stage(self):
        print("ensure_stage")
        if self._stage is None:
            self._stage = omni.usd.get_context().get_stage()
            print(f"ensure_stage:{self._stage}")
            UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.y)
            self.create_materials()
        ppathstr = "/World/Floor"
        prim_path_sdf = Sdf.Path(ppathstr)
        prim: Usd.Prim = self._stage .GetPrimAtPath(prim_path_sdf)
        if not prim.IsValid():
            okc.execute('CreateMeshPrimWithDefaultXform',	prim_type="Plane", prim_path=ppathstr)
            okc.execute('TransformMultiPrimsSRTCpp',
                        count=1,
                        paths=[ppathstr],
                        new_scales=[5, 1, 5])

    def make_preview_surface_tex_material(self, fname):
        # This is all materials
        matpath = "/World/Looks"
        matname = f'{matpath}/boardMat_{fname.replace(".","_")}'
        material = UsdShade.Material.Define(self._stage, matname)
        pbrShader = UsdShade.Shader.Define(self._stage, f'{matname}/PBRShader')
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
        diffuseTextureSampler.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(stReader.ConnectableAPI(), 'result')
        diffuseTextureSampler.CreateOutput('rgb', Sdf.ValueTypeNames.Float3)
        pbrShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(diffuseTextureSampler.ConnectableAPI(), 'rgb')                    

        stInput = material.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
        stInput.Set('st')

        stReader.CreateInput('varname',Sdf.ValueTypeNames.Token).ConnectToSource(stInput)
        return material

    def make_preview_surface_material(self, name: str, r, g, b):
        mtl_path = Sdf.Path(f"/World/Looks/Presurf_{name}")
        mtl = UsdShade.Material.Define(self._stage, mtl_path)
        shader = UsdShade.Shader.Define(self._stage, mtl_path.AppendPath("Shader"))
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set((r, g, b))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        mtl.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        return mtl
    
    def copy_remote_material(self, matname, urlbranch):
        url = f'http://omniverse-content-production.s3-us-west-2.amazonaws.com/Materials/{urlbranch}.mdl'
        mpath = f'/World/Looks/{matname}'
        okc.execute('CreateMdlMaterialPrimCommand', mtl_url=url, mtl_name=matname, mtl_path=mpath)
        print(f"stagetype 1 {self._stage}")
        mtl: UsdShade.Material = UsdShade.Material(self._stage.GetPrimAtPath(mpath) )
        print(f"copy_remote_material {matname} {url} {mpath} {mtl}")
        return mtl

    matlib = {}

    def create_materials(self):
        self.ensure_stage()
        self.matlib["red"] = self.make_preview_surface_material("red", 1, 0, 0)
        self.matlib["green"] = self.make_preview_surface_material("green", 0, 1, 0)
        self.matlib["blue"] = self.make_preview_surface_material("blue", 0, 0, 1)
        self.matlib["yellow"] = self.make_preview_surface_material("yellow", 1, 1, 0)
        self.matlib["cyan"] = self.make_preview_surface_material("cyan", 0, 1, 1)
        self.matlib["magenta"] = self.make_preview_surface_material("magenta", 1, 0, 1)
        self.matlib["white"] = self.make_preview_surface_material("white", 1, 1, 1)
        self.matlib["black"] = self.make_preview_surface_material("black", 0, 0, 0)
        self.matlib["sunset_texture"] = self.make_preview_surface_tex_material("sunset.png")
        self.matlib["Blue_Glass"] = self.copy_remote_material("Blue_Glass", "Base/Glass/Blue_Glass")
        self.matlib["Red_Glass"] = self.copy_remote_material("Red_Glass", "Base/Glass/Red_Glass")
        self.matlib["Green_Glass"] = self.copy_remote_material("Green_Glass", "Base/Glass/Green_Glass")
        self.matlib["Clear_Glass"] = self.copy_remote_material("Clear_Glass", "Base/Glass/Clear_Glass")

    def get_curmat_mat(self):
        idx = self._matbox.get_item_value_model().as_int
        key = self._matkeys[idx]
        if key in self.matlib:
            rv = self.matlib[key]
        else:
            rv = None

        print(f"get_curmat_mat:{idx} {key} {rv}")
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
        texCoords = UsdGeom.PrimvarsAPI(billboard).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
        texCoords.Set([(0, 0), (1, 0), (1, 1), (0, 1)])
        return billboard

    def create_marker(self, name: str, matname: str, cenpt: Gf.Vec3f, rad: float):
        print(f"create_marker {name} {matname} {cenpt} {rad}")
        primpath = f"/World/markers/{name}"
        self.delete_if_exists(primpath)
        okc.execute('CreateMeshPrimWithDefaultXform', prim_type="Sphere", prim_path=primpath)
        sz = rad/100
        okc.execute('TransformMultiPrimsSRTCpp',
                    count=1,
                    paths=[primpath],
                    new_scales=[sz, sz, sz],
                    new_translations=[cenpt[0], cenpt[1], cenpt[2]])
        material = self.matlib[matname]
        prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
        UsdShade.MaterialBindingAPI(prim).Bind(material)

    def cross_product(self, v1: Gf.Vec3f, v2: Gf.Vec3f) -> Gf.Vec3f:
        x = v1[1] * v2[2] - v1[2] * v2[1]
        y = v1[2] * v2[0] - v1[0] * v2[2]
        z = v1[0] * v2[1] - v1[1] * v2[0]
        rv = Gf.Vec3f(x, y, z)
        return rv

    def create_spheremesh(self, name: str, matname: str, cenpt: Gf.Vec3f, radius: float, nlat: int, nlong: int, shownormals: bool = False):

        spheremesh = UsdGeom.Mesh.Define(self._stage, name)
        vtxcnt = int(0)
        pts = []
        nrm = []
        txc = []
        vcs = []
        idx = []
        polegap = 0.01
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
                if shownormals:
                    ptname = f"ppt_{i}_{j}"
                    npt = Gf.Vec3f(x+nx, y+ny, z+nz)
                    nmname = f"npt_{i}_{j}"
                    self.create_marker(ptname, "red", pt, 1)
                    self.create_marker(nmname, "blue", npt, 1)

        for i in range(nlat):
            offset = i * nlong
            for j in range(nlong):
                vcs.append(int(4))
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
                #print(f"i:{i} j:{j} vtxcnt:{vtxcnt} i1:{i1} i2:{i2} i3:{i3} i4:{i4}")

                vtxcnt += 1

        print(len(pts), len(txc), len(vcs), len(idx))
        spheremesh.CreatePointsAttr(pts)
        spheremesh.CreateNormalsAttr(nrm)
        spheremesh.CreateFaceVertexCountsAttr(vcs)
        spheremesh.CreateFaceVertexIndicesAttr(idx)
        spheremesh.CreateExtentAttr([(-radius, -radius, -radius), (radius, radius, radius)])
        texCoords = UsdGeom.PrimvarsAPI(spheremesh).CreatePrimvar("st",
                                  Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
        texCoords.Set(txc)

        material = self.matlib[matname]
        # prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
        UsdShade.MaterialBindingAPI(spheremesh).Bind(material)

        return spheremesh

    xax = Gf.Vec3f(1, 0, 0)
    yax = Gf.Vec3f(0, 1, 0)
    zax = Gf.Vec3f(0, 0, 1)

    def create_sphereflake(self, name: str, matname: str, depth: int, basept: Gf.Vec3f, cenpt: Gf.Vec3f, rad: float):
        print(f"create_sphereflake {name} {matname} {depth} {cenpt} {rad}")
        basename = name + "/base"
        self.delete_if_exists(basename)

        self.create_spheremesh(basename, matname, cenpt,  rad, 8, 8)

        offvek = cenpt - basept
        len = offvek.GetLength()
        if len > 0:
            lxax = self.cross_product(offvek, self.xax)
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
                subname = f"{basename}/sub_{i}"
                self.create_sphereflake(subname, matname, depth-1, cenpt, cenpt+npt, nrad)

    def on_startup(self, ext_id):
        print("[omni.example.spawn_prims] omni example spawn_prims startup <<<<<<<<<<<<<<<<<")
        self._count = 0
        self._current_material = "Clear_Glass"
        self._matkeys = ["Clear_Glass", "Blue_Glass", "red", "green", "blue", "yellow", "cyan", "magenta", "white", "black", 
                         "sunset_texture", "Red_Glass", "Green_Glass"]

        self._window = ui.Window("Spawn Primitives", width=300, height=300)

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
                    spheremesh = self.create_spheremesh("/World/SphereMesh", matname, Gf.Vec3f(0, 0, 0), 50, 8, 8)
                    print(f"spheremesh clicked (cwd:{os.getcwd()})")                    

                def on_click_sphereflake():
                    self.ensure_stage()

                    matname: str = self.get_curmat_name()
                    cpt = Gf.Vec3f(0, 0, 0)
                    sphereflake= self.create_sphereflake("/World/SphereFlake", matname, 3, cpt, cpt, 50)
                    print(f"sphereflake clicked (cwd:{os.getcwd()})")                    

                def on_click(primtype):
                    self.ensure_stage()
                    primpath = f"/World/{primtype}_{self._count}"
                    okc.execute('CreateMeshPrimWithDefaultXform',	prim_type=primtype, prim_path=primpath)

                    material = self.get_curmat_mat()
                    self._count += 1

                    prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
                    okc.execute('TransformMultiPrimsSRTCpp',
                                count=1,
                                paths=[primpath],
                                new_scales=[1, 1, 1],
                                new_translations=[0, 50, 0])

                    print(f"on click binding:{material}")
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

                self._matbox = ui.ComboBox(0, *self._matkeys).model

    def on_shutdown(self):
        print("[omni.example.spawn_prims] omni example spawn_prims shutdown")
