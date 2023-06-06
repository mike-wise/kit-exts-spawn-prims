import omni.ext
import omni.kit.commands as okc
import omni.usd
import os
import math
import time
import asyncio
import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt
from typing import Tuple, List


def delete_if_exists(primpath: str) -> None:
    stage = omni.usd.get_context().get_stage()
    if stage.GetPrimAtPath(primpath):
        okc.execute("DeletePrimsCommand", paths=[primpath])


def cross_product(v1: Gf.Vec3f, v2: Gf.Vec3f) -> Gf.Vec3f:
    x = v1[1] * v2[2] - v1[2] * v2[1]
    y = v1[2] * v2[0] - v1[0] * v2[2]
    z = v1[0] * v2[1] - v1[1] * v2[0]
    rv = Gf.Vec3f(x, y, z)
    return rv


class SphereMeshFactoryV1():

    _show_normals = False

    def __init__(self, matman, nlat: int, nlng: int, show_normals=False) -> None:
        self._stage = omni.usd.get_context().get_stage()
        self._matman = matman
        self._show_normals = show_normals
        self._total_quads = 0
        self._nlat = nlat
        self._nlong = nlng
        pass

    def MakeMarker(self, name: str, matname: str, cenpt: Gf.Vec3f, rad: float):
        print(f"MakeMarker {name}  {cenpt} {rad}")
        primpath = f"/World/markers/{name}"
        delete_if_exists(primpath)
        okc.execute('CreateMeshPrimWithDefaultXform', prim_type="Sphere", prim_path=primpath)
        sz = rad/100
        okc.execute('TransformMultiPrimsSRTCpp',
                    count=1,
                    paths=[primpath],
                    new_scales=[sz, sz, sz],
                    new_translations=[cenpt[0], cenpt[1], cenpt[2]])
        prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
        mtl = self._matman.GetMaterial(matname)
        UsdShade.MaterialBindingAPI(prim).Bind(mtl)

    def CreateMesh(self, name: str, matname: str, cenpt: Gf.Vec3f, radius: float):
        # This will create nlat*nlog quads or twice that many triangles
        # it will need nlat+1 vertices in the latitude direction and nlong vertices in the longitude direction
        # so a total of (nlat+1)*(nlong) vertices
        spheremesh = UsdGeom.Mesh.Define(self._stage, name)
        nlat = self._nlat
        nlong = self._nlong
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
                    self.MakeMarker(ptname, "red", pt, 1)
                    self.MakeMarker(nmname, "blue", npt, 1)

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
        mtl = self._matman.GetMaterial(matname)
        UsdShade.MaterialBindingAPI(spheremesh).Bind(mtl)

        self._total_quads += len(fvc)  # face vertex counts

        return spheremesh


class SphereMeshFactory():

    _show_normals = False

    def __init__(self, matman, nlat: int, nlng: int, show_normals: bool = False, do_text_coords: bool = True) -> None:
        self._stage = omni.usd.get_context().get_stage()
        self._matman = matman
        self._show_normals = show_normals
        self._dotexcoords = do_text_coords
        self._total_quads = 0
        self._nlat = nlat
        self._nlong = nlng
        self._nquads = nlat*nlng
        self._nverts = (nlat+1)*(nlng)
        self._normbuf = np.zeros((self._nverts, 3), dtype=np.float32)
        self._txtrbuf = np.zeros((self._nverts, 2), dtype=np.float32)
        self._facebuf = np.zeros((self._nquads, 1), dtype=np.int32)
        self._vidxbuf = np.zeros((self._nquads, 4), dtype=np.int32)
        self.MakeArrays()

    def MakeMarker(self, name: str, matname: str, cenpt: Gf.Vec3f, rad: float):
        print(f"MakeMarker {name}  {cenpt} {rad}")
        primpath = f"/World/markers/{name}"
        delete_if_exists(primpath)
        okc.execute('CreateMeshPrimWithDefaultXform', prim_type="Sphere", prim_path=primpath)
        sz = rad/100
        okc.execute('TransformMultiPrimsSRTCpp',
                    count=1,
                    paths=[primpath],
                    new_scales=[sz, sz, sz],
                    new_translations=[cenpt[0], cenpt[1], cenpt[2]])
        prim: Usd.Prim = self._stage.GetPrimAtPath(primpath)
        mtl = self._matman.GetMaterial(matname)
        UsdShade.MaterialBindingAPI(prim).Bind(mtl)

    def MakeArrays(self):
        nlat = self._nlat
        nlong = self._nlong
        for i in range(nlat):
            offset = i * nlong
            for j in range(nlong):
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
                vidx = i*nlong+j
                self._facebuf[vidx] = 4
                self._vidxbuf[vidx] = [i1, i2, i3, i4]

        polegap = 0.01  # prevents the vertices from being exactly on the poles
        for i in range(nlat+1):
            theta = polegap + (i * (math.pi-2*polegap) / float(nlat))
            st = math.sin(theta)
            ct = math.cos(theta)
            for j in range(nlong):
                phi = j * 2 * math.pi / float(nlong)
                sp = math.sin(phi)
                cp = math.cos(phi)
                nx = st*cp
                ny = ct
                nz = st*sp
                nrmvek = Gf.Vec3f(nx, ny, nz)
                vidx = i*nlong+j
                self._normbuf[vidx] = nrmvek
                self._txtrbuf[vidx] = (nx, ny)
        #  print("MakeArrays done")

    def ShowNormals(self, vertbuf):
        nlat = self._nlat
        nlong = self._nlong
        for i in range(nlat+1):
            for j in range(nlong):
                vidx = i*nlong+j
                ptname = f"ppt_{i}_{j}"
                (x, y, z) = vertbuf[vidx]
                (nx, ny, nz) = self._nromtbuf[vidx]
                pt = Gf.Vec3f(x, y, z)
                npt = Gf.Vec3f(x+nx, y+ny, z+nz)
                nmname = f"npt_{i}_{j}"
                self.MakeMarker(ptname, "red", pt, 1)
                self.MakeMarker(nmname, "blue", npt, 1)

    def CreateMesh(self, name: str, matname: str, cenpt: Gf.Vec3f, radius: float):
        # This will create nlat*nlog quads or twice that many triangles
        # it will need nlat+1 vertices in the latitude direction and nlong vertices in the longitude direction
        # so a total of (nlat+1)*(nlong) vertices

        spheremesh = UsdGeom.Mesh.Define(self._stage, name)

        # note that vertbuf is local to this function allowing it to be changed in a multithreaded environment
        vertbuf = self._normbuf*radius + cenpt

        if self._show_normals:
            self.ShowNormals(vertbuf)

        if self._dotexcoords:
            texCoords = UsdGeom.PrimvarsAPI(spheremesh).CreatePrimvar("st",
                                                                      Sdf.ValueTypeNames.TexCoord2fArray,
                                                                      UsdGeom.Tokens.varying)
            texCoords.Set(Vt.Vec2fArray.FromNumpy(self._txtrbuf))

        spheremesh.CreatePointsAttr(Vt.Vec3dArray.FromNumpy(vertbuf))
        spheremesh.CreateNormalsAttr(Vt.Vec3dArray.FromNumpy(self._normbuf))
        spheremesh.CreateFaceVertexCountsAttr(Vt.IntArrayFromBuffer(self._facebuf))
        spheremesh.CreateFaceVertexIndicesAttr(Vt.IntArrayFromBuffer(self._vidxbuf))

        mtl = self._matman.GetMaterial(matname)
        UsdShade.MaterialBindingAPI(spheremesh).Bind(mtl)

        self._total_quads += self._nquads  # face vertex counts

        return None

    async def CreateVertBuf(self, radius, cenpt):
        vertbuf = self._normbuf*radius + cenpt
        return vertbuf

    async def CreateStuff(self, spheremesh, vertbuf, normbuf, facebuf, vidxbuf):
        spheremesh.CreatePointsAttr(Vt.Vec3dArray.FromNumpy(vertbuf))
        spheremesh.CreateNormalsAttr(Vt.Vec3dArray.FromNumpy(normbuf))
        spheremesh.CreateFaceVertexCountsAttr(Vt.IntArrayFromBuffer(facebuf))
        spheremesh.CreateFaceVertexIndicesAttr(Vt.IntArrayFromBuffer(vidxbuf))
        return

    async def CreateMeshAsync(self, name: str, matname: str, cenpt: Gf.Vec3f, radius: float):
        # This will create nlat*nlog quads or twice that many triangles
        # it will need nlat+1 vertices in the latitude direction and nlong vertices in the longitude direction
        # so a total of (nlat+1)*(nlong) vertices

        spheremesh = UsdGeom.Mesh.Define(self._stage, name)

        # note that vertbuf is local to this function allowing it to be changed in a multithreaded environment
        vertbuf = await self.CreateVertBuf(radius, cenpt)

        if self._show_normals:
            self.ShowNormals(vertbuf)

        if self._dotexcoords:
            texCoords = UsdGeom.PrimvarsAPI(spheremesh).CreatePrimvar("st",
                                                                      Sdf.ValueTypeNames.TexCoord2fArray,
                                                                      UsdGeom.Tokens.varying)
            texCoords.Set(Vt.Vec2fArray.FromNumpy(self._txtrbuf))

        await self.CreateStuff(spheremesh, vertbuf, self._normbuf, self._facebuf, self._vidxbuf)

        mtl = self._matman.GetMaterial(matname)
        UsdShade.MaterialBindingAPI(spheremesh).Bind(mtl)

        self._total_quads += self._nquads  # face vertex counts

        return None


latest_sf_gen_time = 0


class SphereFlakeFactory():

    org = Gf.Vec3f(0, 0, 0)
    xax = Gf.Vec3f(1, 0, 0)
    yax = Gf.Vec3f(0, 1, 0)
    zax = Gf.Vec3f(0, 0, 1)

    def __init__(self, matman, genmode: str, genform: str,  nlat: int, nlong: int, radratio: float) -> None:
        self._stage = omni.usd.get_context().get_stage()
        self._matman = matman
        self._genmode = genmode
        self._genform = genform
        self._nlat = nlat
        self._nlng = nlong
        self._radratio = radratio
        self._smf = SphereMeshFactory(self._matman,  nlat, nlong, show_normals=False)

    @staticmethod
    def CalcQuadsAndPrims(depth: int, nring: int, nlat: int, nlng: int):
        totquads = 0
        totprims = 0
        for i in range(depth+1):
            nspheres = nring**(i)
            nquads = nspheres * nlat * nlng
            totquads += nquads
            totprims += nspheres
        return totquads, totprims

    @staticmethod
    def CalcTrisAndPrims(depth: int, nring: int, nlat: int, nlng: int):
        totquads, totprims = SphereFlakeFactory.CalcQuadsAndPrims(depth, nring, nlat, nlng)
        return totquads * 2, totprims

    @staticmethod
    def GetFlakeExtent(depth: int, rad: float, radratio: float):
        sz = rad * radratio**depth
        return Gf.Vec3f(sz, sz, sz)

    @staticmethod
    def GetLastGenTime():
        global latest_sf_gen_time
        return latest_sf_gen_time
    


    def Generate(self, sphflkname: str, matname: str, mxdepth: int, depth: int, cenpt: Gf.Vec3f, rad: float):

        global latest_sf_gen_time

        self._start_time = time.time()
        self._total_quads = 0

        self._depth = depth
        self._nring = 8
        delete_if_exists(sphflkname)

        xformPrim = UsdGeom.Xform.Define(self._stage, sphflkname)
        UsdGeom.XformCommonAPI(xformPrim).SetTranslate((0, 0, 0))
        UsdGeom.XformCommonAPI(xformPrim).SetRotate((0, 0, 0))

        basept = cenpt
        self.GenRecursively(sphflkname, matname, mxdepth, depth, basept, cenpt, rad)

        elap = time.time() - self._start_time
        print(f"GenerateSF {sphflkname} {matname} {depth} {cenpt} totquads:{self._total_quads} in {elap:.3f} secs")

        latest_sf_gen_time = elap

    def GenRecursively(self, sphflkname: str, matname: str, mxdepth: int, depth: int, basept: Gf.Vec3f,
                       cenpt: Gf.Vec3f, rad: float):

        # xformPrim = UsdGeom.Xform.Define(self._stage, sphflkname)
        # UsdGeom.XformCommonAPI(xformPrim).SetTranslate((0, 0, 0))
        # UsdGeom.XformCommonAPI(xformPrim).SetRotate((0, 0, 0))

        meshname = sphflkname + "/SphereMesh"

        # spheremesh = UsdGeom.Mesh.Define(self._stage, meshname)

        if self._genmode == "AsyncMesh":
            meshname = sphflkname + "/SphereMeshAsync"
            asyncio.ensure_future(self._smf.CreateMeshAsync(meshname, matname, cenpt,  rad))
        elif self._genmode == "DirectMesh":
            meshname = sphflkname + "/SphereMesh"
            self._smf.CreateMesh(meshname, matname, cenpt,  rad)
        elif self._genmode == "OmniSphere":
            meshname = sphflkname + "/OmniSphere"
            okc.execute('CreateMeshPrimWithDefaultXform',	prim_type="Sphere", prim_path=meshname)
            sz = rad/50  # 50 is the default radius of the sphere prim
            okc.execute('TransformMultiPrimsSRTCpp',
                        count=1,
                        paths=[meshname],
                        new_scales=[sz, sz, sz],
                        new_translations=[cenpt[0], cenpt[1], cenpt[2]])
            mtl = self._matman.GetMaterial(matname)
            prim: Usd.Prim = self._stage.GetPrimAtPath(meshname)
            UsdShade.MaterialBindingAPI(prim).Bind(mtl)
        elif self._genmode == "UsdSphere":
            meshname = sphflkname + "/UsdSphere"
            xformPrim = UsdGeom.Xform.Define(self._stage, meshname)
            sz = rad
            UsdGeom.XformCommonAPI(xformPrim).SetTranslate((cenpt[0], cenpt[1], cenpt[2]))
            UsdGeom.XformCommonAPI(xformPrim).SetScale((sz, sz, sz))
            spheremesh = UsdGeom.Sphere.Define(self._stage, meshname)
            mtl = self._matman.GetMaterial(matname)
            UsdShade.MaterialBindingAPI(spheremesh).Bind(mtl)

        if depth > 0:
            form = self._genform
            if form == "Classic":
                thoff = 0
                phioff = -20*math.pi/180
                self._nring = 6
                self.GenRing(sphflkname, "r1", matname, mxdepth, depth, basept, cenpt, 6, rad, thoff, phioff)

                thoff = 30*math.pi/180
                phioff = 55*math.pi/180
                self._nring = 3
                self.GenRing(sphflkname, "r2", matname, mxdepth, depth, basept, cenpt, 3, rad, thoff, phioff)
            else:
                thoff = 0
                phioff = 0
                self._nring = 8
                self.GenRing(sphflkname, "r1", matname, mxdepth, depth, basept, cenpt, self._nring, rad, thoff, phioff)


    def GenRing(self, sphflkname: str, ringname: str, matname: str, mxdepth: int, depth: int, basept, cenpt, nring: int, rad: float,
                thoff: float, phioff: float):
        offvek = cenpt - basept
        len = offvek.GetLength()
        if len > 0:
            lxax = cross_product(offvek, self.yax)
            if lxax.GetLength() == 0:
                lxax = cross_product(offvek, self.zax)
            lxax.Normalize()
            lzax = cross_product(offvek, lxax)
            lzax.Normalize()
            lyax = offvek
            lyax.Normalize()
        else:
            lxax = self.xax
            lyax = self.yax
            lzax = self.zax
        nrad = rad * self._radratio
        offfak = 1 + self._radratio
        sphi = math.sin(phioff)
        cphi = math.cos(phioff)
        for i in range(nring):
            theta = thoff + (i*2*math.pi/nring)
            x = cphi*rad*math.sin(theta)
            y = sphi*rad
            z = cphi*rad*math.cos(theta)
            npt = x*lxax + y*lyax + z*lzax
            subname = f"{sphflkname}/{ringname}_sf_{i}"
            self.GenRecursively(subname, matname, mxdepth, depth-1, cenpt, cenpt+offfak*npt, nrad)


class MatMan():
    matlib = {}

    def __init__(self) -> None:
        self.CreateMaterials()
        pass

    def MakePreviewSurfaceTexMateral(self, matname: str, fname: str):
        # This is all materials
        matpath = "/World/Looks"
        mlname = f'{matpath}/boardMat_{fname.replace(".","_")}'
        stage = omni.usd.get_context().get_stage()
        material = UsdShade.Material.Define(stage, mlname)
        pbrShader = UsdShade.Shader.Define(stage, f'{mlname}/PBRShader')
        pbrShader.CreateIdAttr("UsdPreviewSurface")
        pbrShader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.4)
        pbrShader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

        material.CreateSurfaceOutput().ConnectToSource(pbrShader.ConnectableAPI(), "surface")
        stReader = UsdShade.Shader.Define(stage, f'{matpath}/stReader')
        stReader.CreateIdAttr('UsdPrimvarReader_float2')

        diffuseTextureSampler = UsdShade.Shader.Define(stage, f'{matpath}/diffuseTexture')
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

    def SplitRgb(self, rgb: str) -> Tuple[float, float, float]:
        sar = rgb.split(",")
        r = float(sar[0])
        g = float(sar[1])
        b = float(sar[2])
        return (r, g, b)

    def MakePreviewSurfaceMaterial(self, matname: str, rgb: str):
        mtl_path = Sdf.Path(f"/World/Looks/Presurf_{matname}")
        stage = omni.usd.get_context().get_stage()

        mtl = UsdShade.Material.Define(stage, mtl_path)
        shader = UsdShade.Shader.Define(stage, mtl_path.AppendPath("Shader"))
        shader.CreateIdAttr("UsdPreviewSurface")
        rgbtup = self.SplitRgb(rgb)
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(rgbtup)
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.5)
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
        mtl.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        # self.matlib[matname] = {"name": matname, "typ": "mtl", "mat": mtl}
        self.matlib[matname]["mat"] = mtl
        return mtl

    def CopyRemoteMaterial(self, matname, urlbranch):
        print("CopyRemoteMaterial")
        stage = omni.usd.get_context().get_stage()
        baseurl = 'https://omniverse-content-production.s3.us-west-2.amazonaws.com'
        url = f'{baseurl}/Materials/{urlbranch}.mdl'
        mpath = f'/World/Looks/{matname}'
        okc.execute('CreateMdlMaterialPrimCommand', mtl_url=url, mtl_name=matname, mtl_path=mpath)
        mtl: UsdShade.Material = UsdShade.Material(stage.GetPrimAtPath(mpath) )
        print(f"CopyRemoteMaterial {matname} {url} {mpath} {mtl}")
        # self.matlib[matname] = {"name": matname, "typ": "rgb", "mat": mtl}
        self.matlib[matname]["mat"] = mtl
        return mtl

    def RealizeMaterial(self, matname: str):
        typ = self.matlib[matname]["typ"]
        spec = self.matlib[matname]["spec"]
        if typ == "mtl":
            self.CopyRemoteMaterial(matname, spec)
        elif typ == "tex":
            self.MakePreviewSurfaceTexMateral(matname, spec)
        else:
            self.MakePreviewSurfaceMaterial(matname, spec)
        self.matlib[matname]["realized"] = True

    def SetupMaterial(self, matname: str, typ: str, spec: str):
        print(f"SetupMaterial {matname} {typ} {spec}")
        matpath = f"/World/Looks/{matname}"
        self.matlib[matname] = {"name": matname,
                                "typ": typ,
                                "mat": None,
                                "path": matpath,
                                "realized": False,
                                "spec": spec}

    def CreateMaterials(self):
        self.SetupMaterial("red", "rgb", "1,0,0")
        self.SetupMaterial("green", "rgb", "0,1,0")
        self.SetupMaterial("blue", "rgb", "0,0,1")
        self.SetupMaterial("yellow", "rgb", "1,1,0")
        self.SetupMaterial("cyan", "rgb", "0,1,1")
        self.SetupMaterial("magenta", "rgb", "1,0,1")
        self.SetupMaterial("white", "rgb", "1,1,1")
        self.SetupMaterial("black", "rgb", "0,0,0")
        self.SetupMaterial("Blue_Glass",  "mtl", "Base/Glass/Blue_Glass")
        self.SetupMaterial("Red_Glass", "mtl", "Base/Glass/Red_Glass")
        self.SetupMaterial("Green_Glass", "mtl", "Base/Glass/Green_Glass")
        self.SetupMaterial("Clear_Glass", "mtl", "Base/Glass/Clear_Glass")
        self.SetupMaterial("Mirror", "mtl", "Base/Glass/Mirror")
        self.SetupMaterial("sunset_texture", "tex", "sunset.png")

    def GetMaterialNames(self) -> List[str]:
        return list(self.matlib.keys())

    def GetMaterial(self, key):
        if key in self.matlib:
            if not self.matlib[key]["realized"]:
                self.RealizeMaterial(key)
            rv = self.matlib[key]["mat"]
        else:
            rv = None
        return rv
