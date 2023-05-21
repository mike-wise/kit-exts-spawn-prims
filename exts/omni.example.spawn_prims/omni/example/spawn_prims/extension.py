import omni.ext
import omni.ui as ui
import omni.kit.commands
import omni.usd
import os
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade

# flake8: noqa
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
        if self._stage == None:
            self._stage = omni.usd.get_context().get_stage()
            self.create_materials()
            # print("ensure_stage", self._stage)

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
    
    def copy_remote_material(self,matname):
        mtl = None
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

    def get_curmat(self):
        idx = self._matbox.get_item_value_model().as_int
        rv = self._matkeys[idx]
        self._current_material = "green"
        print(f"get_curmat:{idx}  {rv}")
        return rv

    def on_startup(self, ext_id):
        print("[omni.example.spawn_prims] omni example spawn_prims startup <<<<<<<<<<<<<<<<<")
        self._count = 0
        self._current_material = "green"
        self._matkeys = ["red", "green", "blue", "yellow", "cyan", "magenta", "white", "black", "sunset_texture"]

        self._window = ui.Window("Spawn Primitives", width=300, height=300)

        with self._window.frame:
            with ui.VStack():

                def on_click_billboard():
                    self.ensure_stage()
                    UsdGeom.SetStageUpAxis(self._stage, UsdGeom.Tokens.y)

                    billboard = UsdGeom.Mesh.Define(self._stage, "/World/Billboard")
                    billboard.CreatePointsAttr([(-430, -145, 0), (430, -145, 0), (430, 145, 0), (-430, 145, 0)])
                    billboard.CreateFaceVertexCountsAttr([4])
                    billboard.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
                    billboard.CreateExtentAttr([(-430, -145, 0), (430, 145, 0)])
                    texCoords = UsdGeom.PrimvarsAPI(billboard).CreatePrimvar("st",
                                        Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying)
                    texCoords.Set([(0, 0), (1, 0), (1,1), (0, 1)])

                    material = self.matlib[self.get_curmat()]
                    UsdShade.MaterialBindingAPI(billboard).Bind(material)
                    print(billboard)

                    print(f"billboard clicked (cwd:{os.getcwd()})")

                def on_click(primtype):
                    self.ensure_stage()
                    primpath = f"/World/{primtype}_{self._count}"
                    omni.kit.commands.execute('CreateMeshPrimWithDefaultXform',	prim_type=primtype, prim_path=primpath)
                    material = self.matlib[self.get_curmat()]
                    self._count += 1

                    prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
                    UsdShade.MaterialBindingAPI(prim).Bind(material)

                    print("clicked")

                ui.Button("Spawn Cube", clicked_fn=lambda: on_click("Cube"))
                ui.Button("Spawn Cone", clicked_fn=lambda: on_click("Cone"))
                ui.Button("Spawn Cylinder", clicked_fn=lambda: on_click("Cylinder"))
                ui.Button("Spawn Disk", clicked_fn=lambda: on_click("Disk"))
                ui.Button("Spawn Plane", clicked_fn=lambda: on_click("Plane"))
                ui.Button("Spawn Sphere", clicked_fn=lambda: on_click("Sphere"))
                ui.Button("Spawn Torus", clicked_fn=lambda: on_click("Torus"))
                ui.Button("Spawn USD Billboard", clicked_fn=lambda: on_click_billboard())

                self._matbox = ui.ComboBox(1, *self._matkeys).model

    def on_shutdown(self):
        print("[omni.example.spawn_prims] omni example spawn_prims shutdown")



