import omni.ui as ui
from omni.ui import color as clr
import asyncio
from ._widgets import TabGroup, BaseTab
from .sphereflake import SphereMeshFactory, SphereFlakeFactory
from .sfcontrols import SfControls


class SfcWindow(ui.Window):

    darkgreen = clr("#004000")
    darkblue = clr("#000040")
    darkred = clr("#400000")
    darkyellow = clr("#404000")
    darkpurple = clr("#400040")
    darkcyan = clr("#004040")
    darkcyan = clr("#004040")

    marg = 2

    _sf_depth_but: ui.Button = None
    _sf_spawn_but: ui.Button = None
    _sf_nlat_but: ui.Button = None
    _sf_nlng_but: ui.Button = None
    _sf_radratio_slider: ui.FloatSlider = None
    _statuslabel: ui.Label = None
    _memlabel: ui.Label = None
    _sf_matbox: ui.ComboBox = None
    _sf_alt_matbox: ui.ComboBox = None
    _bb_matbox: ui.ComboBox = None
    _sf_floor_matbox: ui.ComboBox = None
    _genmodebox: ui.ComboBox = None
    _genformbox: ui.ComboBox = None

    sfc: SfControls
    smf: SphereMeshFactory
    sff: SphereFlakeFactory

    def __init__(self, *args, **kwargs):
        super().__init__(title="SphereFlake Controls", height=300, width=300,  *args, **kwargs)
        self.sfc = kwargs["sfc"]
        self.sfc.sfw = self  # intentionally circular
        self.smf = self.sfc.smf
        self.sff = self.sfc.sff
        self.BuildWindow()
        self.sfc.LateInit()

    def BuildWindow(self):
        sfc = self.sfc
        smf = sfc.smf # noqa : F841
        sff = sfc.sff # noqa : F841
        print(f"SfcWindow.BuildWindow {type(sfc)}")
        with self.frame:
            with ui.VStack():
                t1 = SfcTab1("Multi", self, sfc)
                t2 = SfcTab2("SphereFlake", self, sfc)
                t3 = SfcTab3("Shapes", self, sfc)
                t4 = SfcTab4("Materials", self, sfc)
                t5 = SfcTab5("Options", self, sfc)
                self.tab_group = TabGroup([t1, t2, t3, t4, t5])
                self._statuslabel = ui.Label("Status: Ready")
                self._memlabel = ui.Button("Memory tot/used/free", clicked_fn=sfc.UpdateGpuMemory)
                ui.Button("Clear Primitives",
                          style={'background_color': self.darkyellow},
                          clicked_fn=lambda: sfc.on_click_clearprims())


    def on_close(self):
        pass


class SfcTab1(BaseTab):

    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, name: str, sfw: SfcWindow, sfc: SfControls):
        super().__init__(name)
        self.sfw = sfw
        self.sfc = sfc
        # print(f"SfcTab1.init {type(sfc)}")

    def build_fn(self):
        sfw: SfcWindow = self.sfw
        sfc: SfControls = self.sfc
        sff: SphereFlakeFactory = self.sfw.sff
        # print(f"SfcTab1.build_fn {type(sfc)}")
        with ui.VStack(style={"margin": sfw.marg}):
            with ui.VStack():
                with ui.HStack():
                    clkfn = lambda: asyncio.ensure_future(sfc.on_click_multi_sphereflake()) # noqa : E731
                    sfw._msf_spawn_but = ui.Button("Multi ShereFlake",
                                                   style={'background_color': sfw.darkred},
                                                   clicked_fn=clkfn)
                    with ui.VStack(width=200):
                        clkfn = lambda x, y, b, m: sfc.on_click_sfx(x, y, b, m) # noqa : E731
                        sfw._nsf_x_but = ui.Button(f"SF x: {sff.p_nsfx}",
                                                   style={'background_color': sfw.darkblue},
                                                   mouse_pressed_fn=clkfn)
                        clkfn = lambda x, y, b, m: sfc.on_click_sfy(x, y, b, m) # noqa : E731
                        sfw._nsf_y_but = ui.Button(f"SF y: {sff.p_nsfy}",
                                                   style={'background_color': sfw.darkblue},
                                                   mouse_pressed_fn=clkfn)
                        clkfn = lambda x, y, b, m: sfc.on_click_sfz(x, y, b, m) # noqa : E731
                        sfw._nsf_z_but = ui.Button(f"SF z: {sff.p_nsfz}",
                                                   style={'background_color': sfw.darkblue},
                                                   mouse_pressed_fn=clkfn)
                    sfw._tog_bounds_but = ui.Button(f"Bounds:{sfc._bounds_visible}",
                                                    style={'background_color': sfw.darkcyan},
                                                    clicked_fn=sfc.toggle_bounds)
                with ui.CollapsableFrame("Partial Renders"):
                    with ui.VStack():
                        sfw._partial_render_but = ui.Button(f"Partial Render {sff.p_partialRender}",
                                                            style={'background_color': sfw.darkcyan},
                                                            clicked_fn=sfc.toggle_partial_render)
                        with ui.HStack():
                            clkfn = lambda x, y, b, m: sfc.on_click_parital_sfsx(x, y, b, m) # noqa : E731
                            sfw._part_nsf_sx_but = ui.Button(f"SF partial sx: {sff.p_partial_ssfx}",
                                                             style={'background_color': sfw.darkblue},
                                                             mouse_pressed_fn=clkfn)
                            clkfn = lambda x, y, b, m: sfc.on_click_parital_sfsy(x, y, b, m) # noqa : E731
                            sfw._part_nsf_sy_but = ui.Button(f"SF partial sy: {sff.p_partial_ssfy}",
                                                             style={'background_color': sfw.darkblue},
                                                             mouse_pressed_fn=clkfn)
                            clkfn = lambda x, y, b, m: sfc.on_click_parital_sfsz(x, y, b, m) # noqa : E731
                            sfw._part_nsf_sz_but = ui.Button(f"SF partial sz: {sff.p_partial_ssfz}",
                                                             style={'background_color': sfw.darkblue},
                                                             mouse_pressed_fn=clkfn)
                        with ui.HStack():
                            clkfn = lambda x, y, b, m: sfc.on_click_parital_sfnx(x, y, b, m) # noqa : E731
                            sfw._part_nsf_nx_but = ui.Button(f"SF partial nx: {sff.p_partial_nsfx}",
                                                             style={'background_color': sfw.darkblue},
                                                             mouse_pressed_fn=clkfn)
                            clkfn = lambda x, y, b, m: sfc.on_click_parital_sfny(x, y, b, m) # noqa : E731
                            sfw._part_nsf_ny_but = ui.Button(f"SF partial ny: {sff.p_partial_nsfy}",
                                                             style={'background_color': sfw.darkblue},
                                                             mouse_pressed_fn=clkfn)
                            clkfn = lambda x, y, b, m: sfc.on_click_parital_sfnz(x, y, b, m) # noqa : E731
                            sfw._part_nsf_nz_but = ui.Button(f"SF partial nz: {sff.p_partial_nsfz}",
                                                             style={'background_color': sfw.darkblue},
                                                             mouse_pressed_fn=clkfn)
                with ui.CollapsableFrame("Parallel Renders"):
                    with ui.VStack():
                        sfw._parallel_render_but = ui.Button(f"Parallel Render {sff.p_parallelRender}",
                                                             style={'background_color': sfw.darkcyan},
                                                             clicked_fn=sfc.toggle_parallel_render)
                        with ui.HStack():
                            clkfn = lambda x, y, b, m: sfc.on_click_parallel_nxbatch(x, y, b, m) # noqa : E731
                            sfw._parallel_nxbatch_but = ui.Button(f"SF batch x: {sff.p_parallel_nxbatch}",
                                                                  style={'background_color': sfw.darkblue},
                                                                  mouse_pressed_fn=clkfn)
                            clkfn = lambda x, y, b, m: sfc.on_click_parallel_nybatch(x, y, b, m) # noqa : E731
                            sfw._parallel_nybatch_but = ui.Button(f"SF batch y: {sff.p_parallel_nybatch}",
                                                                  style={'background_color': sfw.darkblue},
                                                                  mouse_pressed_fn=clkfn)
                            clkfn = lambda x, y, b, m: sfc.on_click_parallel_nzbatch(x, y, b, m) # noqa : E731
                            sfw._parallel_nzbatch_but = ui.Button(f"SF batch z: {sff.p_parallel_nzbatch}",
                                                                  style={'background_color': sfw.darkblue},
                                                                  mouse_pressed_fn=clkfn)


class SfcTab2(BaseTab):

    sfc: SfControls = None

    def __init__(self, name: str, sfw: SfcWindow, sfc: SfControls):
        super().__init__(name)
        self.sfw = sfw
        self.sfc = sfc

    def build_fn(self):
        sfw = self.sfw
        sfc = self.sfc
        sff = self.sfw.sff
        smf = self.sfw.smf
        # print(f"SfcTab2.build_fn sfc:{type(sfc)} ")

        with ui.VStack(style={"margin": sfw.marg}):

            with ui.VStack():
                with ui.HStack():
                    sfw._sf_spawn_but = ui.Button("Spawn SphereFlake",
                                                  style={'background_color': sfw.darkred},
                                                  clicked_fn=lambda: sfc.on_click_sphereflake())
                    with ui.VStack(width=200):
                        sfw._sf_depth_but = ui.Button(f"Depth:{sfc.sff.p_depth}",
                                                      style={'background_color': sfw.darkgreen},
                                                      mouse_pressed_fn= # noqa : E251
                                                      lambda x, y, b, m: sfc.on_click_sfdepth(x, y, b, m))
                        with ui.HStack():
                            ui.Label("Radius Ratio: ",
                                     style={'background_color': sfw.darkgreen},
                                     width=50)
                            sfw._sf_radratio_slider = ui.FloatSlider(min=0.0, max=1.0, step=0.01,
                                                                     style={'background_color': sfw.darkblue}).model
                            sfw._sf_radratio_slider.set_value(sff.p_radratio)

                        # SF Gen Mode Combo Box
                        with ui.HStack():
                            ui.Label("Gen Mode:")
                            idx = sfc._sf_gen_modes.index(sfc._sf_gen_mode)
                            sfw._genmodebox = ui.ComboBox(idx, *sfc._sf_gen_modes).model

                        # SF Form Combo Box
                        with ui.HStack():
                            ui.Label("Gen Form:")
                            idx = sfc._sf_gen_forms.index(sfc._sf_gen_form)
                            sfw._genformbox = ui.ComboBox(idx, *sfc._sf_gen_forms).model

                    with ui.VStack():
                        sfw._sf_nlat_but = ui.Button(f"Nlat:{smf.p_nlat}",
                                                     style={'background_color': sfw.darkgreen},
                                                     mouse_pressed_fn= # noqa : E251
                                                     lambda x, y, b, m: sfc.on_click_nlat(x, y, b, m))
                        sfw._sf_nlng_but = ui.Button(f"Nlng:{smf.p_nlng}",
                                                     style={'background_color': sfw.darkgreen},
                                                     mouse_pressed_fn= # noqa : E251
                                                     lambda x, y, b, m: sfc.on_click_nlng(x, y, b, m))


class SfcTab3(BaseTab):

    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, name: str, sfw: SfcWindow, sfc: SfControls):
        super().__init__(name)
        self.sfw = sfw
        self.sfc = sfc

    def build_fn(self):
        sfc = self.sfc
        sfw = self.sfw
        # print(f"SfcTab3.build_fn {type(sfc)}")

        with ui.VStack(style={"margin": sfw.marg}):

            with ui.HStack():
                sfw._sf_spawn_but = ui.Button("Spawn Prim",
                                              style={'background_color': sfw.darkred},
                                              clicked_fn=lambda: sfc.on_click_spawnprim())
                sfw._sf_primtospawn_but = ui.Button(f"{sfc._curprim}",
                                                    style={'background_color': sfw.darkpurple},
                                                    clicked_fn=lambda: sfc.on_click_changeprim())


class SfcTab4(BaseTab):
    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, name: str, sfw: SfcWindow, sfc: SfControls):
        super().__init__(name)
        self.sfw = sfw
        self.sfc = sfc
        # print("SfcTab4.build_fn {sfc}")

    def build_fn(self):
        sfw = self.sfw
        sfc = self.sfc

        with ui.VStack(style={"margin": sfw.marg}):

            # Material Combo Box
            with ui.HStack():
                ui.Label("SF Material 1:")
                idx = sfc._matkeys.index(sfc._current_material_name)
                sfw._sf_matbox = ui.ComboBox(idx, *sfc._matkeys).model
                print("built sfw._sf_matbox")

            with ui.HStack():
                ui.Label("SF Material 2:")
                # use the alternate material name
                idx = sfc._matkeys.index(sfc._current_alt_material_name)
                sfw._sf_alt_matbox = ui.ComboBox(idx, *sfc._matkeys).model
                print("built sfw._sf_matbox")

            # Bounds Material Combo Box
            with ui.HStack():
                ui.Label("Bounds Material:")
                idx = sfc._matkeys.index(sfc._current_bbox_material_name)
                sfw._bb_matbox = ui.ComboBox(idx, *sfc._matkeys).model

            # Bounds Material Combo Box
            with ui.HStack():
                ui.Label("Floor Material:")
                idx = sfc._matkeys.index(sfc._current_floor_material_name)
                sfw._sf_floor_matbox = ui.ComboBox(idx, *sfc._matkeys).model


class SfcTab5(BaseTab):
    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, name: str, sfw: SfcWindow, sfc: SfControls):
        super().__init__(name)
        self.sfw = sfw
        self.sfc = sfc
        # print("SfcTab5.build_fn {sfc}")

    def build_fn(self):
        sfw = self.sfw
        sfc = self.sfc # noqa : F841

        with ui.VStack(style={"margin": sfw.marg}):
            ui.CheckBox(model=sfc.get_bool_model("writelog"), width=40, height=10, name="writelog", visible=True)

            with ui.CollapsableFrame("Logging", style={'background_color': sfw.darkcyan}):
                with ui.HStack():
                    sfw._sf_writerunlog_but = ui.Button(f"Write Perf Log: {sfc.p_writelog}",
                                                        clicked_fn=lambda: sfc.on_click_writerunlog())
