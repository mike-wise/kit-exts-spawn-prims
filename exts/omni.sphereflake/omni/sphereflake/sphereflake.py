import omni.ext
import omni.kit.commands as okc
import omni.usd
import carb
import time
import asyncio
import math
from pxr import Gf, Usd, UsdGeom, UsdShade
from .spheremesh import SphereMeshFactory
from . import ovut
from .ovut import MatMan

latest_sf_gen_time = 0

class SphereFlakeFactory():

    _matman: MatMan = None
    _smf: SphereMeshFactory = None
    _genmode = "UsdSphere"
    _genform = "Classic"
    _depth = 1
    _rad = 50
    _radratio = 0.3
    _start_timee = 0
    _createlist: list = []
    _bbcubelist: list = []
    _nsfx = 1
    _nsfy = 1
    _nsfz = 1
    _sf_matname = "Mirror"
    _bb_matname = "Red Glass"
    _make_bounds_visible = False

    org = Gf.Vec3f(0, 0, 0)
    xax = Gf.Vec3f(1, 0, 0)
    yax = Gf.Vec3f(0, 1, 0)
    zax = Gf.Vec3f(0, 0, 1)

    def __init__(self, matman: MatMan, smf: SphereMeshFactory) -> None:
        self._stage = omni.usd.get_context().get_stage()
        self._count = 0
        self._matman = matman
        self._smf = smf

    def GenPrep(self):
        self._smf.GenPrep()
        pass

    @staticmethod
    def GetGenModes():
        return ["UsdSphere", "DirectMesh", "AsyncMesh", "OmniSphere"]

    @staticmethod
    def GetGenForms():
        return ["Classic", "Flat-8"]

    def Clear(self):
        self._createlist = []
        self._bbcubelist = []

    def Set(self, attname: str, val: float):
        if hasattr(self, attname):
            self.__dict__[attname] = val
        else:
            carb.log.error(f"SphereFlakeFactory.Set: no attribute {attname}")

    def CalcQuadsAndPrims(self):
        nring = 9 if self._genform == "Classic" else 8
        nlat = self._smf._nlat
        nlng = self._smf._nlng
        totquads = 0
        totprims = 0
        for i in range(self._depth+1):
            nspheres = nring**(i)
            nquads = nspheres * nlat * nlng
            totquads += nquads
            totprims += nspheres
        return totquads, totprims

    def CalcTrisAndPrims(self):
        totquads, totprims = self.CalcQuadsAndPrims()
        return totquads * 2, totprims

    def GetCenterPosition(self, ix: int, nx: int,  iz: int, nz: int,  extentvec: Gf.Vec3f, gap: float = 1.1):
        ixoff = (nx-1)/2
        izoff = (nz-1)/2
        x = (ix-ixoff) * extentvec[0] * gap * 2
        y = extentvec[1]
        z = (iz-izoff) * extentvec[2] * gap * 2
        return Gf.Vec3f(x, y, z)

    @staticmethod
    def GetLastGenTime():
        global latest_sf_gen_time
        return latest_sf_gen_time

    def SpawnBBcube(self, primpath, cenpt, extent, bbmatname):
        stage = omni.usd.get_context().get_stage()
        xformPrim = UsdGeom.Xform.Define(stage, primpath)
        UsdGeom.XformCommonAPI(xformPrim).SetTranslate((cenpt[0], cenpt[1], cenpt[2]))
        UsdGeom.XformCommonAPI(xformPrim).SetScale((extent[0], extent[1], extent[2]))
        cube = UsdGeom.Cube.Define(stage, primpath)
        mtl = self._matman.GetMaterial(bbmatname)
        UsdShade.MaterialBindingAPI(cube).Bind(mtl)
        return cube

    def GetSphereFlakeBoundingBox(self):
        # sz = rad  +  (1+(radratio))**depth # old method
        sz = self._rad
        nrad = sz
        for i in range(self._depth):
            nrad = self._radratio*nrad
            sz += 2*nrad
        return Gf.Vec3f(sz, sz, sz)

    def GenerateMany(self):
        self.GenPrep()
        cpt = Gf.Vec3f(0, self._rad, 0)
        # extentvec = self.GetFlakeExtent(depth, self._rad, self._radratio)
        nx = self._nsfx
        nz = self._nsfz
        extentvec = self.GetSphereFlakeBoundingBox()
        count = self._count

        self._createlist = []
        self._bbcubelist = []
        for ix in range(nx):
            for iz in range(nz):
                count += 1
                primpath = f"/World/SphereFlake_{count}"

                cpt = self.GetCenterPosition(ix, nx, iz, nz, extentvec)

                self.Generate(primpath, cpt)
                self._createlist.append(primpath)
                bnd_cubepath = primpath+"/bounds"
                bnd_cube = self.SpawnBBcube(bnd_cubepath, cpt, extentvec, self._bb_matname)
                self._bbcubelist.append(bnd_cubepath)
                if self._make_bounds_visible:
                    UsdGeom.Imageable(bnd_cube).MakeVisible()
                else:
                    UsdGeom.Imageable(bnd_cube).MakeInvisible()
        return (count)

    def ToggleBoundsVisiblity(self):
        # print(f"ToggleBoundsVisiblity: {self._bbcubelist}")
        okc.execute('ToggleVisibilitySelectedPrims', selected_paths=self._bbcubelist)

    def Generate(self, sphflkname: str, cenpt: Gf.Vec3f):

        global latest_sf_gen_time

        self._start_timee = time.time()
        self._total_quads = 0

        self._nring = 8
        ovut.delete_if_exists(sphflkname)

        xformPrim = UsdGeom.Xform.Define(self._stage, sphflkname)
        UsdGeom.XformCommonAPI(xformPrim).SetTranslate((0, 0, 0))
        UsdGeom.XformCommonAPI(xformPrim).SetRotate((0, 0, 0))

        mxdepth = self._depth
        basept = cenpt
        matname = self._sf_matname
        self.GenRecursively(sphflkname, matname, mxdepth, self._depth, basept, cenpt, self._rad)

        elap = time.time() - self._start_timee
        # print(f"GenerateSF {sphflkname} {matname} {depth} {cenpt} totquads:{self._total_quads} in {elap:.3f} secs")

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

    def GenRing(self, sphflkname: str, ringname: str, matname: str, mxdepth: int, depth: int,
                basept: Gf.Vec3f, cenpt: Gf.Vec3f,
                nring: int, rad: float,
                thoff: float, phioff: float):
        offvek = cenpt - basept
        len = offvek.GetLength()
        if len > 0:
            lxax = ovut.cross_product(offvek, self.yax)
            if lxax.GetLength() == 0:
                lxax = ovut.cross_product(offvek, self.zax)
            lxax.Normalize()
            lzax = ovut.cross_product(offvek, lxax)
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
