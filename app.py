import sys
if '--virtual-env' in sys.argv:
  virtualEnvPath = sys.argv[sys.argv.index('--virtual-env') + 1]
  # Linux
  #virtualEnv = virtualEnvPath + '/bin/activate_this.py'
  # Windows
  virtualEnv = virtualEnvPath + '/Scripts/activate_this.py'
  if sys.version_info.major < 3:
    execfile(virtualEnv, dict(__file__=virtualEnv))
  else:
    exec(open(virtualEnv).read(), {'__file__': virtualEnv})

import asyncio

import paraview.web.venv
from pathlib import Path
from paraview import simple

from trame.app import get_server, asynchronous
from trame.widgets import vuetify, paraview, plotly
from trame.ui.vuetify import SinglePageWithDrawerLayout
import subprocess
import plotly.graph_objects as go


monoalg_command = "./runmonoalg.sh"
########################### Configuando paraview #######################
# -----------------------------------------------------------------------------
# ParaView pipeline
# -----------------------------------------------------------------------------
from paraview import simple

simple.LoadDistributedPlugin("AcceleratedAlgorithms", remote=False, ns=globals())

# Rendering setup
view = simple.GetRenderView()
view.OrientationAxesVisibility = 0
view = simple.Render()
simple.ResetCamera()
view.CenterOfRotation = view.CameraFocalPoint
########################################## Fim #################################

#Inicializa o servidor
server = get_server()
state, ctrl = server.state, server.controller

animationscene = simple.GetAnimationScene()
timekeeper = animationscene.TimeKeeper
metadata = None
time_values = []

# Custom Classes for our problem
class CardContainer(vuetify.VCard):
    def __init__(self, **kwargs):
        super().__init__(variant="outlined", **kwargs)
        with self:
            with vuetify.VCardTitle():
                self.header = vuetify.VRow(
                    classes="align-center pa-0 ma-0", style="min-height: 40px;"
                )
            vuetify.VDivider()
            self.content = vuetify.VCardText()

class PlotSelectionOverTime(CardContainer):
    def __init__(self, run=None):
        super().__init__(
            classes="ma-4 flex-sm-grow-1", style="width: calc(100% - 504px);"
        )
        ctrl = self.server.controller

        with self.header as header:
            header.add_child("Plot Selection Over Time")

        with self.content as content:
            content.classes = "d-flex flex-shrink-1 pb-0"
            # classes UI
            _chart =  plotly.Figure(
                style="width: 100%; height: 200px;",
                v_show=("task_active === 'classification' && !input_needed",),
                display_mode_bar=False,
            ) 
            ctrl.classification_chart_update = _chart.update

            # similarity UI
            vuetify.VProgressCircular(
                "{{ Math.round(model_viz_similarity) }} %",
                v_show=("task_active === 'similarity' && !input_needed",),
                size=192,
                width=15,
                color="teal",
                model_value=("model_viz_similarity", 0),
            )


# Load function, runs every time server starts
def load_data(**kwargs):
    global time_values, representation, reader
    reader = simple.PVDReader(FileName="C:/Users/lucas/venv/MonoAlgWeb-trame/MonoAlg3D_C/outputs/temp/simulation_result.pvd")
    reader.CellArrays = ['Scalars_']
    reader.UpdatePipeline()
    representation = simple.Show(reader, view)
    time_values = list(timekeeper.TimestepValues)
    
    state.time_value = time_values[0]
    state.times = len(time_values)-1
    state.time = 0
    state.play = False
    state.animationStep = 10 #default = 1
    simple.ResetCamera()
    view.CenterOfRotation = view.CameraFocalPoint

@ctrl.add("on_server_reload")
def print_item(item):
    print("Clicked on", item)

@state.change("time")
def update_time(time, **kwargs):
    if len(time_values) == 0:
        return  
    
    if time >= len(time_values):
        time = 0
        state.time = time
        state.play = False
    time_value = time_values[time]
    timekeeper.Time = time_value
    state.time_value = time_value
    
    ctrl.view_update_image()


@state.change("play")
@asynchronous.task 
async def update_play(**kwargs):
    while state.play:
        with state:
            state.time += int(state.animationStep)
            update_time(state.time)

        await asyncio.sleep(0.1)

def update_frame():
    #Eu tenho o valor do tempo, de verdade
    #preciso tranformar na iteração
    dt = time_values[1] - time_values[0]
    state.time = int(float(state.time_value)/dt)
    html_view.update_image()
    pass

@state.change("position")
def update_contour(position , **kwargs):
    # animationscene = simple.GetAnimationScene()
    animationscene.AnimationTime = position
    html_view.update_image()
    pass

def subTime():
    state.time -= int(state.animationStep)
    html_view.update_image()
    pass

def addTime():
    state.time += int(state.animationStep)
    html_view.update_image()
    pass

def lastTime():
    state.time = state.times
    html_view.update_image()
    pass

def firstTime():
    state.time = 0
    html_view.update_image()
    pass

def addClip():
    clip = simple.Clip(registrationName="Clip1",Input=reader)
    clip.ClipType = "Plane"
    clip.HyperTreeGridClipper = 'Plane'
    clip.Scalars = ['CELLS', 'Scalars_']
    clip.Value = -85.2300033569336
    clip.Invert = 1
    clip.Crinkleclip = 0
    clip.Exact = 0

    clip.ClipType.Origin = [16375.0, 15125.0, 13875.0]
    clip.ClipType.Normal = [1.0, 0.0, 0.0]
    clip.ClipType.Offset = 0.0

    clip.HyperTreeGridClipper.Origin = [16375.0, 15125.0, 13875.0]
    clip.HyperTreeGridClipper.Normal = [1.0, 0.0, 0.0]
    clip.HyperTreeGridClipper.Offset = 0.0

    simple.Hide(reader, view)
    representation = simple.Show(clip, view)
    html_view.update_image()

def playAnimation():
    if state.play:
        state.play = False
    else:
        state.play = True

def runMonoAlg3D():
    #Colocar os campos 
    with open("./MonoAlg3D_C/example_configs/custom.ini", 'w') as file:
        file.write("[main]\nnum_threads=6\ndt_pde=0.02\nsimulation_time=" + str(state.simulation_time) + "\n")
        file.write("abort_on_no_activity=false\nuse_adaptivity=false\n[update_monodomain]\nmain_function=update_monodomain_default\n[save_result]\nprint_rate=50\noutput_dir=./outputs/temp\nmain_function=save_as_vtu\ninit_function=init_save_as_vtk_or_vtu\nend_function=end_save_as_vtk_or_vtu\nsave_pvd=true\nfile_prefix=V\n[assembly_matrix]\ninit_function=set_initial_conditions_fvm\nsigma_x=0.0000176\nsigma_y=0.0001334\nsigma_z=0.0000176\nlibrary_file=shared_libs/libdefault_matrix_assembly.so\nmain_function=homogeneous_sigma_assembly_matrix\n[linear_system_solver]\ntolerance=1e-16\nuse_gpu=yes\nmax_iterations=200\nlibrary_file=shared_libs/libdefault_linear_system_solver.so\nmain_function=conjugate_gradient\ninit_function=init_conjugate_gradient\nend_function=end_conjugate_gradient\n[alg]\nrefinement_bound = 0.11\nderefinement_bound = 0.10\nrefine_each = 1\nderefine_each = 1\n[domain]\nname=Plain Mesh\nnum_layers=1\nstart_dx=100.0\nstart_dy=100.0\nstart_dz=100.0\nside_length=10000\nmain_function=initialize_grid_with_square_mesh\n[ode_solver]\ndt=0.02\nuse_gpu=yes\ngpu_id=0\nlibrary_file=shared_libs/libten_tusscher_3_epi.so\n")
        file.write("[stim_1]\nstart =" + str(state.S1) +"\nduration=2.0\ncurrent=-50.0\nmin_x=250.0\nmax_x=500.0\nmin_y=0.0\nmax_y=1000.0\nmain_function=stim_x_y_limits")
        if(state.S2!=0):
            file.write("\n[stim_2]\nstart =" + str(state.S2) +"\nduration=2.0\ncurrent=-50.0\nmin_x=0.0\nmax_x=250.0\nmin_y=0.0\nmax_y=1000.0\nmain_function=stim_x_y_limits")

    saida = subprocess.check_output(monoalg_command, shell=True, universal_newlines=True)
    print(saida)
    pass

with SinglePageWithDrawerLayout(server) as layout:
    with layout.drawer:
        vuetify.VTextField(v_model=("simulation_time", 1000))
        vuetify.VTextField(v_model=("S1", 5))
        vuetify.VTextField(v_model=("S2" , 500))

        vuetify.VBtn("Executar", click=runMonoAlg3D)    
    with layout.toolbar:
        vuetify.VSpacer()
   
        #Barra de carregamento abaixo do header
        vuetify.VProgressLinear(
            indeterminate=True,
            absolute=True,
            bottom=True,
            active=("trame__busy",),
        )

        #Estava tentando colocar um icone, mas não consigo.
        #https://vuetifyjs.com/en/api/v-btn/#props

        vuetify.VTextField(v_model=("animationStep", 10), hint="Animation Step", style="width= 25px; height: 100%")
        vuetify.VBtn("F", click=firstTime)
        vuetify.VBtn("-",
                    click=subTime,
                    )
        #não consegui diminuir a largura dele
        vuetify.VTextField(v_model=("time_value", 0), change=update_frame, number = True, hint="Real Time (ms)", style="width: 25px; height: 100%") #Esse style não funciona no texto, mas funciona em outros elementos 
        vuetify.VBtn("+",
                     click=addTime) 
        vuetify.VBtn("*", click=playAnimation)
        vuetify.VBtn("L", click=lastTime)

        vuetify.VBtn("Clip", click=addClip)
    
    #Isso é a parte inferior e maior da página (onde tudo é plotado por enquanto)
    with layout.content:
        with vuetify.VContainer(fluid=True,classes="pa-0 fill-height"):
            with vuetify.VCol(style="max-width: 50%",classes="ma-0 fill-height", align ="start", cols=6, sm=6):
                html_view = paraview.VtkRemoteLocalView(
                    view,
                    namespace="demo",
                )
            with vuetify.VCol(style="max-width: 50%",classes="ma-0 fill-height", align ="start", cols=6, sm=6):
                x = [i for i in range(100)]
                y = [x[i]**2 for i in range(100)]
                fig = go.Figure()

                fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='x²'))

                fig.update_layout(
                    title='Gráfico de x²',
                    xaxis_title='x',
                    yaxis_title='x²',
                )

                plot_view = plotly.Figure(fig)
                plot_view.update(fig)

                
                
                
        

#Chama função de carregar dados quando o servidor inicia
ctrl.on_server_ready.add(load_data)

#Inicia o servidor
server.start()
