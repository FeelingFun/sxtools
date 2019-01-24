# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
#
#   Technical notes:
#   settings              - an instance containing the user's active
#                           object or component selections, 
#                           the project configuration, and
#                           methods for saving and loading prefs
#   setup                 - creates the necessary materials and shaders
#                           to view the color-layered object. Also creates
#                           primVars on layered objects to enable
#                           multi-layered vertex coloring and exporting.
#   export                - contains methods to prepare objects for
#                           game engines. Flattens color layers and bakes
#                           the data to UV channels.
#   tools                 - a collection of actions performed by the tool
#                           such as occlusion baking, applying gradients etc.
#   layers                - methods required for working with
#                           vertex color layers
#   ui                    - the layouts of the SX Tool UI elements and 
#                           context-sensitive selection modes
#   core                  - the core loop, filters user input and refreshes
#                           the user interface
# ----------------------------------------------------------------------------

def initialize():
    from sxlib.settings import Settings
    from sxlib.setup import SceneSetup
    from sxlib.export import Export
    from sxlib.tools import ToolActions
    from sxlib.layers import LayerManagement
    from sxlib.ui import UI
    from sxlib.core import Core
    
    global dockID, settings, setup, export, tools, layers, ui, core
    dockID = 'SXToolsUI'
    settings = Settings()
    setup = SceneSetup()
    export = Export()
    tools = ToolActions()
    layers = LayerManagement()
    ui = UI()
    core = Core()
