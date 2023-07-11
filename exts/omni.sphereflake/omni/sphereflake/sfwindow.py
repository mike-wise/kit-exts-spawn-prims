# import omni.ext
import omni.ui as ui
from omni.ui import color as clr
import asyncio
from ._widgets import TabGroup, BaseTab
from .sfcontrols import SfControls


class SfcWindow(ui.Window):

    darkgreen = clr("#004000")
    darkblue = clr("#000040")
    darkred = clr("#400000")
    darkyellow = clr("#404000")
    darkpurple = clr("#400040")
    darkcyan = clr("#004040")

    marg = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # super().__init__(title="SphereFlake", width=400, height=400)
        self.sfc = kwargs["sfc"]
        self.sfc.p_sfw = self
        self.BuildWindow()

    def BuildWindow(self):
        sfc = self.sfc
        print(f"SfcWindow.BuildWindow {type(sfc)}")
        with self.frame:
            with ui.VStack():
                t1 = SfcTab1("Multi", self, sfc)
                t2 = SfcTab2("SphereFlake", self, sfc)
                t3 = SfcTab3("Shapes", self, sfc)
                t4 = SfcTab4("Materials", self, sfc)
                t5 = SfcTab5("Options", self, sfc)
                self.tab_group = TabGroup([t1, t2, t3, t4, t5])
                sfc._statuslabel = ui.Label("Status: Ready")
                sfc._memlabel = ui.Button("Memory tot/used/free", clicked_fn=sfc.UpdateGpuMemory)
                ui.Button("Clear Prims",
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
        sfw = self.sfw
        sfc = self.sfc
        # print(f"SfcTab1.build_fn {type(sfc)}")
        with ui.VStack(style={"margin": sfw.marg}):
            with ui.VStack():
                with ui.HStack():
                    sfc._msf_spawn_but = ui.Button("Multi ShereFlake",
                                                   style={'background_color': sfw.darkred},
                                                   clicked_fn= # noqa : E251
                                                   lambda: asyncio.ensure_future(sfc.on_click_multi_sphereflake()))
                    with ui.VStack(width=200):
                        sfc._nsf_x_but = ui.Button(f"SF x: {sfc.sff.p_nsfx}",
                                                   style={'background_color': sfw.darkblue},
                                                   mouse_pressed_fn= # noqa : E251
                                                   lambda x, y, b, m: sfc.on_click_sfx(x, y, b, m))
                        sfc._nsf_y_but = ui.Button(f"SF y: {sfc.sff.p_nsfy}",
                                                   style={'background_color': sfw.darkblue},
                                                   mouse_pressed_fn= # noqa : E251
                                                   lambda x, y, b, m: sfc.on_click_sfy(x, y, b, m))
                        sfc._nsf_z_but = ui.Button(f"SF z: {sfc.sff.p_nsfz}",
                                                   style={'background_color': sfw.darkblue},
                                                   mouse_pressed_fn= # noqa : E251
                                                   lambda x, y, b, m: sfc.on_click_sfz(x, y, b, m))

                    sfc._tog_bounds_but = ui.Button(f"Bounds:{sfc._bounds_visible}",
                                                    style={'background_color': sfw.darkcyan},
                                                    clicked_fn=lambda: sfc.toggle_bounds())


class SfcTab2(BaseTab):

    sfc: SfControls = None

    def __init__(self, name: str, sfw: SfcWindow, sfc: SfControls):
        super().__init__(name)
        self.sfw = sfw
        self.sfc = sfc

    def build_fn(self):
        sfw = self.sfw
        sfc = self.sfc
        # print(f"SfcTab2.build_fn sfc:{type(sfc)} ")

        with ui.VStack(style={"margin": sfw.marg}):

            with ui.VStack():
                with ui.HStack():
                    sfc._sf_spawn_but = ui.Button("Spawn SphereFlake",
                                                  style={'background_color': sfw.darkred},
                                                  clicked_fn=lambda: sfc.on_click_sphereflake())
                    with ui.VStack(width=200):
                        sfc._sf_depth_but = ui.Button(f"Depth:{sfc.sff.p_depth}",
                                                      style={'background_color': sfw.darkgreen},
                                                      mouse_pressed_fn= # noqa : E251
                                                      lambda x, y, b, m: sfc.on_click_sfdepth(x, y, b, m))
                        with ui.HStack():
                            ui.Label("Radius Ratio: ",
                                     style={'background_color': sfw.darkgreen},
                                     width=50)
                            sfc._sf_radratio_slider = ui.FloatSlider(min=0.0, max=1.0, step=0.01,
                                                                     style={'background_color': sfw.darkblue}).model
                            sfc._sf_radratio_slider.set_value(sfc.sff.p_radratio)

                        # SF Gen Mode Combo Box
                        with ui.HStack():
                            ui.Label("Gen Mode:")
                            idx = sfc._sf_gen_modes.index(sfc._sf_gen_mode)
                            sfc._genmodebox = ui.ComboBox(idx, *sfc._sf_gen_modes).model

                        # SF Form Combo Box
                        with ui.HStack():
                            ui.Label("Gen Form:")
                            idx = sfc._sf_gen_forms.index(sfc._sf_gen_form)
                            sfc._genformbox = ui.ComboBox(idx, *sfc._sf_gen_forms).model

                    with ui.VStack():
                        sfc._sf_nlat_but = ui.Button(f"Nlat:{sfc.smf.p_nlat}",
                                                     style={'background_color': sfw.darkgreen},
                                                     mouse_pressed_fn= # noqa : E251
                                                     lambda x, y, b, m: sfc.on_click_nlat(x, y, b, m))
                        sfc._sf_nlng_but = ui.Button(f"Nlng:{sfc.smf.p_nlng}",
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
                sfc._sf_spawn_but = ui.Button("Spawn Prim",
                                              style={'background_color': sfw.darkred},
                                              clicked_fn=lambda: sfc.on_click_spawnprim())
                sfc._sf_primtospawn_but = ui.Button(f"{sfc._curprim}",
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
                ui.Label("Material:")
                idx = sfc._matkeys.index(sfc._current_material_name)
                sfc._matbox = ui.ComboBox(idx, *sfc._matkeys).model

            # Bounds Material Combo Box
            with ui.HStack():
                ui.Label("Bounds Material:")
                idx = sfc._matkeys.index(sfc._current_bbox_material_name)
                sfc._matbbox = ui.ComboBox(idx, *sfc._matkeys).model


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

            # Material Combo Box
            with ui.HStack():
                ui.Label("WriteLog:")
                ui.CheckBox()

