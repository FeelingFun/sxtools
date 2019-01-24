# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
#
#   Curvature calculation method based on work by Stepan Jirka
#   http://www.stepanjirka.com/maya-api-curvature-shader/
#
#   ShaderFX network generation based on work by Steve Theodore
#   https://github.com/theodox/sfx
#
#   Functionality summary:
#   SX Tools simplifies artist workflow in painting vertex colors
#   by presenting color sets in a layer-style interface.
#
#   Users can edit vertex color values for both an arbitrary
#   number of albedo layers, and for a set of material
#   properties.
#
#   Viewport visualization of layered vertex colors is accomplished
#   with a custom ShaderFX shader. This material is automatically
#   generated when not present in the scene.
#
#   The tool includes an export function that flattens color
#   layers but preserves selected alpha values as "layer masks"
#   that are written into the UV channels of the mesh.
#
#   When the user adjusts the layer opacity, or in any way causes
#   the components of a layer to have an alpha >0 and <1, the
#   layer is marked as an adjustment layer (A). This means it is
#   checked against AlphaToleranceValue to see if the alpha contributes
#   to a layer mask, or if it is only used to flatten layer colors.
#
# ----------------------------------------------------------------------------

import maya.cmds
import sxglobals

def start():
    # Check if SX Tools UI exists
    if maya.cmds.workspaceControl('SXToolsUI', exists=True):
        maya.cmds.deleteUI('SXToolsUI', control=True)

    scriptJobs = maya.cmds.scriptJob(listJobs=True)
    for job in scriptJobs:
        if ('sxtools' in job) and ('uiDeleted' in job):
            print('SX Tools: Old instance still shutting down!')
            return

    sxglobals.initialize()
    sxglobals.core.startSXTools()
    print('SX Tools: Plugin started')
