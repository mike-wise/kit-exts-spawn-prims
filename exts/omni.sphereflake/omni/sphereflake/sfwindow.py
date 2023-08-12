import carb.events
import omni.ui as ui
from omni.ui import color as clr
import asyncio
from ._widgets import TabGroup, BaseTab
from .sphereflake import SphereMeshFactory, SphereFlakeFactory
from .sfcontrols import SfControls
from .ovut import get_setting, save_setting


class SfcWindow(ui.Window):

    darkgreen = clr("#004000")
    darkblue = clr("#000040")
    darkred = clr("#400000")
    darkyellow = clr("#404000")
    darkpurple = clr("#400040")
    darkcyan = clr("#004040")

    marg = 2

    # Status
    _statuslabel: ui.Label = None
    _memlabel: ui.Label = None

    # Sphereflake params
    prframe: ui.CollapsableFrame = None
    drframe: ui.CollapsableFrame = None

    docollapse_prframe = False
    docollapse_drframe = False

    _sf_depth_but: ui.Button = None
    _sf_spawn_but: ui.Button = None
    _sf_nlat_but: ui.Button = None
    _sf_nlng_but: ui.Button = None
    _sf_radratio_slider_model: ui.SimpleFloatModel = None

    _genmodebox: ui.ComboBox = None
    _genmodebox_model: ui.SimpleIntModel = None

    _genformbox: ui.ComboBox = None
    _genformbox_model: ui.SimpleIntModel = None

    # Material tab
    _sf_matbox: ui.ComboBox = None
    _sf_matbox_model: ui.SimpleIntModel = None

    _sf_alt_matbox: ui.ComboBox = None
    _sf_alt_matbox_model: ui.SimpleIntModel = None

    _bb_matbox: ui.ComboBox = None
    _bb_matbox_model: ui.SimpleIntModel = None

    _sf_floor_matbox: ui.ComboBox = None
    _sf_floor_matbox_model: ui.SimpleIntModel = None

    # Options
    writelog_checkbox: ui.CheckBox = None
    writelog_checkbox_model = None
    writelog_seriesname: ui.StringField = None
    writelog_seriesname_model = None

    # state
    sfc: SfControls
    smf: SphereMeshFactory
    sff: SphereFlakeFactory

    def __init__(self, *args, **kwargs):
        super().__init__(title="SphereFlake Controls", height=300, width=300,  *args, **kwargs)
        print(f"SfcWindow.__init__ (trc)")
        self.sfc = kwargs["sfc"]
        self.sfc.sfw = self  # intentionally circular
        self.smf = self.sfc.smf
        self.sff = self.sfc.sff
        self.LoadSettings()
        self.BuildControlModels()
        self.BuildWindow()
        self.sfc.LateInit()

    def BuildControlModels(self):
        # models for controls that are used in the logic need to be built outside the build_fn
        # since that will only be called when the tab is selected and displayed

        sfc = self.sfc
        sff = sfc.sff

        # sphereflake params
        self._sf_radratio_slider_model = ui.SimpleFloatModel(sff.p_radratio)
        idx = sff.GetGenModes().index(sff.p_genmode)
        self._genmodebox_model = ui.SimpleIntModel(idx)
        idx = sff.GetGenForms().index(sff.p_genform)
        self._genformbox_model = ui.SimpleIntModel(idx)

        # materials
        matlist = sfc._matkeys
        idx = matlist.index(sff.p_sf_matname)
        self._sf_matbox_model = ui.SimpleIntModel(idx)
        idx = matlist.index(sff.p_sf_alt_matname)
        self._sf_alt_matbox_model = ui.SimpleIntModel(idx)
        idx = matlist.index(sff.p_bb_matname)
        self._bb_matbox_model = ui.SimpleIntModel(idx)
        idx = matlist.index(sfc._current_floor_material_name)
        self._sf_floor_matbox_model = ui.SimpleIntModel(idx)

        # options
        self.writelog_checkbox_model = ui.SimpleBoolModel(sfc.p_writelog)
        self.writelog_seriesname_model = ui.SimpleStringModel(sfc.p_logseriesname)

    def BuildWindow(self):
        print("SfcWindow.BuildWindow  (trc)")
        sfc = self.sfc
        with self.frame:
            with ui.VStack():
                t1 = SfcTabMulti(self)
                t2 = SfcTabSphereFlake(self)
                t3 = SfcTabShapes(self)
                t4 = SfcTabMaterials(self)
                t5 = SfcTabOptions(self)
                self.tab_group = TabGroup([t1, t2, t3, t4, t5])
                self._statuslabel = ui.Label("Status: Ready")
                self._memlabel = ui.Button("Memory tot/used/free", clicked_fn=sfc.UpdateGpuMemory)
                ui.Button("Clear Primitives",
                          style={'background_color': self.darkyellow},
                          clicked_fn=lambda: sfc.on_click_clearprims())

    def DockWindow(self, wintitle="Property"):
        print(f"Docking to {wintitle} (trc)")
        handle = ui._ui.Workspace.get_window(wintitle)
        self.dock_in(handle, ui._ui.DockPosition.SAME)
        self.deferred_dock_in(wintitle, ui._ui.DockPolicy.TARGET_WINDOW_IS_ACTIVE)

    def LoadSettings(self):
        # print("SfcWindow.LoadSettings")
        self.docollapse_prframe = get_setting("ui_pr_frame_collapsed", False)
        self.docollapse_drframe = get_setting("ui_dr_frame_collapsed", False)
        # print(f"docollapse_prframe: {self.docollapse_prframe} docollapse_drframe: {self.docollapse_drframe}")

    def SaveSettings(self):
        # print("SfcWindow.SaveSettings")
        if (self.prframe is not None):
            save_setting("ui_pr_frame_collapsed", self.prframe.collapsed)
        if (self.drframe is not None):
            save_setting("ui_dr_frame_collapsed", self.drframe.collapsed)
        # print(f"docollapse_prframe: {self.prframe.collapsed} docollapse_drframe: {self.drframe.collapsed}")


class SfcTabMulti(BaseTab):

    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, sfw: SfcWindow):
        super().__init__("Multi")
        self.sfw = sfw
        self.sfc = sfw.sfc
        # print(f"SfcTabMulti.init {type(sfc)}")

    def build_fn(self):
        print("SfcTabMulti.build_fn (trc)")
        sfw: SfcWindow = self.sfw
        sfc: SfControls = self.sfc
        sff: SphereFlakeFactory = self.sfw.sff
        # print(f"SfcTabMulti.build_fn {type(sfc)}")
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
                sfw.prframe = ui.CollapsableFrame("Partial Renders", collapsed=sfw.docollapse_prframe)
                with sfw.prframe:
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
                sfw.drframe = ui.CollapsableFrame("Distributed Renders", collapsed=sfw.docollapse_drframe)
                with sfw.drframe:
                    with ui.VStack():
                        sfw._parallel_render_but = ui.Button(f"Distributed Render {sff.p_parallelRender}",
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


class SfcTabSphereFlake(BaseTab):

    sfc: SfControls = None

    def __init__(self, sfw: SfcWindow):
        super().__init__("SphereFlake")
        self.sfw = sfw
        self.sfc = sfw.sfc

    def build_fn(self):
        print("SfcTabSphereFlake.build_fn (trc)")
        sfw = self.sfw
        sfc = self.sfc
        sff = self.sfw.sff
        smf = self.sfw.smf
        # print(f"SfcTabMulti.build_fn sfc:{type(sfc)} ")

        with ui.VStack(style={"margin": sfw.marg}):

            with ui.VStack():
                with ui.HStack():
                    sfw._sf_spawn_but = ui.Button("Spawn SphereFlake",
                                                  style={'background_color': sfw.darkred},
                                                  clicked_fn=lambda: sfc.on_click_sphereflake())
                    with ui.VStack(width=200):
                        sfw._sf_depth_but = ui.Button(f"Depth:{sff.p_depth}",
                                                      style={'background_color': sfw.darkgreen},
                                                      mouse_pressed_fn= # noqa : E251
                                                      lambda x, y, b, m: sfc.on_click_sfdepth(x, y, b, m))
                        with ui.HStack():
                            ui.Label("Radius Ratio: ",
                                     style={'background_color': sfw.darkgreen},
                                     width=50)
                            sfw._sf_radratio_slider = ui.FloatSlider(model=sfw._sf_radratio_slider_model,
                                                                     min=0.0, max=1.0, step=0.01,
                                                                     style={'background_color': sfw.darkblue}).model

                        # SF Gen Mode Combo Box
                        with ui.HStack():
                            ui.Label("Gen Mode:")
                            model = sfw._genmodebox_model
                            idx = model.as_int
                            sfw._genmodebox_model = ui.ComboBox(idx, *sff.GetGenModes()).model.get_item_value_model()

                        # SF Form Combo Box
                        with ui.HStack():
                            ui.Label("Gen Form1:")
                            model = sfw._genformbox_model
                            idx = model.as_int
                            sfw._genformbox_model = ui.ComboBox(idx, *sff.GetGenForms()).model.get_item_value_model()

                    with ui.VStack():
                        sfw._sf_nlat_but = ui.Button(f"Nlat:{smf.p_nlat}",
                                                     style={'background_color': sfw.darkgreen},
                                                     mouse_pressed_fn= # noqa : E251
                                                     lambda x, y, b, m: sfc.on_click_nlat(x, y, b, m))
                        sfw._sf_nlng_but = ui.Button(f"Nlng:{smf.p_nlng}",
                                                     style={'background_color': sfw.darkgreen},
                                                     mouse_pressed_fn= # noqa : E251
                                                     lambda x, y, b, m: sfc.on_click_nlng(x, y, b, m))


class SfcTabShapes(BaseTab):

    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, sfw: SfcWindow):
        super().__init__("Shapes")
        self.sfw = sfw
        self.sfc = sfw.sfc

    def build_fn(self):
        print("SfcTabShapes.build_fn (trc)")
        sfc = self.sfc
        sfw = self.sfw
        # print(f"SfcTabShapes.build_fn {type(sfc)}")

        with ui.VStack(style={"margin": sfw.marg}):

            with ui.HStack():
                sfw._sf_spawn_but = ui.Button("Spawn Prim",
                                              style={'background_color': sfw.darkred},
                                              clicked_fn=lambda: sfc.on_click_spawnprim())
                sfw._sf_primtospawn_but = ui.Button(f"{sfc._curprim}",
                                                    style={'background_color': sfw.darkpurple},
                                                    clicked_fn=lambda: sfc.on_click_changeprim())


class SfcTabMaterials(BaseTab):
    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, sfw: SfcWindow):
        super().__init__("Materials")
        self.sfw = sfw
        self.sfc = sfw.sfc
        # print("SfcTabMaterials.build_fn {sfc}")

    def build_fn(self):
        print("SfcTabMaterials.build_fn (trc)")
        sfw = self.sfw
        sfc = self.sfc

        with ui.VStack(style={"margin": sfw.marg}):

            # Material Combo Box
            with ui.HStack():
                ui.Label("SF Material 1:")
                idx = sfc._matkeys.index(sfc._current_material_name)
                sfw._sf_matbox = ui.ComboBox(idx, *sfc._matkeys)
                sfw._sf_matbox_model = sfw._sf_matbox.model.get_item_value_model()

                print("built sfw._sf_matbox")

            with ui.HStack():
                ui.Label("SF Material 2:")
                # use the alternate material name
                idx = sfc._matkeys.index(sfc._current_alt_material_name)
                sfw._sf_alt_matbox = ui.ComboBox(idx, *sfc._matkeys)
                sfw._sf_alt_matbox_model = sfw._sf_alt_matbox.model.get_item_value_model()
                print("built sfw._sf_matbox")

            # Bounds Material Combo Box
            with ui.HStack():
                ui.Label("Bounds Material:")
                idx = sfc._matkeys.index(sfc._current_bbox_material_name)
                sfw._bb_matbox = ui.ComboBox(idx, *sfc._matkeys)
                sfw._bb_matbox_model = sfw._bb_matbox.model.get_item_value_model()

            # Bounds Material Combo Box
            with ui.HStack():
                ui.Label("Floor Material:")
                idx = sfc._matkeys.index(sfc._current_floor_material_name)
                sfw._sf_floor_matbox = ui.ComboBox(idx, *sfc._matkeys)
                sfw._sf_floor_matbox_model = sfw._sf_floor_matbox.model.get_item_value_model()


class SfcTabOptions(BaseTab):
    sfw: SfcWindow
    sfc: SfControls

    def __init__(self, sfw: SfcWindow):
        super().__init__("Options")
        self.sfw = sfw
        self.sfc = sfw.sfc
        # print("SfcTabOptions.build_fn {sfc}")

    def build_fn(self):
        print("SfcTabOptions.build_fn (trc)")
        sfw = self.sfw
        sfc = self.sfc # noqa : F841

        with ui.VStack(style={"margin": sfw.marg}):
            with ui.HStack():
                ui.Label("Write Perf Log: ")
                sfw.writelog_checkbox = ui.CheckBox(model=sfw.writelog_checkbox_model,
                                                    width=40, height=10, name="writelog", visible=True)
            with ui.HStack():
                ui.Label("Log Series Name:")
                sfw.writelog_seriesname = ui.StringField(model=sfw.writelog_seriesname_model,
                                                         width=200, height=20, visible=True)
