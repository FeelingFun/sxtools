# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
# ----------------------------------------------------------------------------

import maya.cmds
import maya.mel as mel
import sxglobals


class Core(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting core')

    def startSXTools(self):
        sxglobals.settings.tools['platform'] = maya.cmds.about(os=True)

        if sxglobals.settings.tools['platform'] == 'win' or sxglobals.settings.tools['platform'] == 'win64':
            sxglobals.settings.tools['displayScale'] = maya.cmds.mayaDpiSetting(
                query=True, realScaleValue=True)
            if sxglobals.settings.tools['displayScale'] == 1.0:
                sxglobals.settings.tools['lineHeight'] = 16
            elif sxglobals.settings.tools['displayScale'] == 1.25:
                sxglobals.settings.tools['lineHeight'] = 14.5
            elif sxglobals.settings.tools['displayScale'] == 1.5:
                sxglobals.settings.tools['lineHeight'] = 15
            elif sxglobals.settings.tools['displayScale'] == 2.0:
                sxglobals.settings.tools['lineHeight'] = 14.5

            # Most PCs with modern graphics cards can run
            # vertex color compositing fully on the GPU
            sxglobals.settings.tools['compositor'] = 1
            sxglobals.settings.tools['compositeEnable'] = False

            if maya.cmds.optionVar(query='vp2RenderingEngine') != 'DirectX11':
                maya.cmds.optionVar(
                    stringValue=('vp2RenderingEngine', 'DirectX11'))
                print(
                    'SX Tools: ViewPort 2.0 is not in DirectX11 mode.\n'
                    'The correct mode has been set. Please restart Maya.')
                self.exitSXTools()
        else:
            sxglobals.settings.tools['displayScale'] = 1.0
            sxglobals.settings.tools['lineHeight'] = 12.5

            # On Mac (Linux untested), a simpler shader
            # with CPU color compositing is used instead
            sxglobals.settings.tools['compositor'] = 2
            sxglobals.settings.tools['compositeEnable'] = True

        sxglobals.settings.loadPreferences()
        maya.cmds.workspaceControl(
            sxglobals.dockID,
            label='SX Tools',
            uiScript=('sxtools.sxglobals.core.updateSXTools()'),
            retain=False,
            floating=False,
            dockToControl=('Outliner', 'right'),
            initialHeight=5,
            initialWidth=250 * sxglobals.settings.tools['displayScale'],
            minimumWidth=250 * sxglobals.settings.tools['displayScale'],
            widthProperty='free')

        # Background jobs to reconstruct window if selection changes,
        # and to clean up upon closing
        if 'updateSXTools' not in maya.cmds.scriptJob(listJobs=True):
            self.job1ID = maya.cmds.scriptJob(
                parent=sxglobals.dockID,
                event=[
                    'SelectionChanged',
                    'sxtools.sxglobals.core.updateSXTools()'])
            self.job2ID = maya.cmds.scriptJob(
                parent=sxglobals.dockID,
                event=[
                    'Undo',
                    'sxtools.sxglobals.core.updateSXTools()'])
            self.job3ID = maya.cmds.scriptJob(
                parent=sxglobals.dockID,
                event=[
                    'NameChanged',
                    'sxtools.sxglobals.core.updateSXTools()'])
            self.job4ID = maya.cmds.scriptJob(
                parent=sxglobals.dockID,
                event=[
                    'SceneOpened',
                    'sxtools.sxglobals.settings.frames["setupCollapse"]=False\n'
                    'sxtools.sxglobals.settings.setPreferences()\n'
                    'sxtools.sxglobals.core.updateSXTools()'])
            self.job5ID = maya.cmds.scriptJob(
                parent=sxglobals.dockID,
                event=[
                    'NewSceneOpened',
                    'sxtools.sxglobals.settings.frames["setupCollapse"]=False\n'
                    'sxtools.sxglobals.settings.setPreferences()\n'
                    'sxtools.sxglobals.core.updateSXTools()'])
        maya.cmds.scriptJob(
            runOnce=True,
            uiDeleted=[
                sxglobals.dockID,
                'sxtools.sxglobals.core.exitSXTools()'])
        maya.cmds.scriptJob(
            runOnce=True,
            event=[
                'quitApplication',
                'maya.cmds.workspaceControl("SXToolsUI", edit=True, close=True)'])

        # Set correct lighting and shading mode at start
        mel.eval('DisplayShadedAndTextured;')
        mel.eval('DisplayLight;')
        maya.cmds.modelEditor('modelPanel4', edit=True, udm=False)

    # Avoids UI refresh from being included in the undo list
    # Called by the "jobID" scriptJob whenever the user clicks a selection.
    def updateSXTools(self):
        # startTimeOcc = maya.cmds.timerX()
        maya.cmds.undoInfo(stateWithoutFlush=False)
        self.selectionManager()
        self.refreshSXTools()
        self.verifySceneState()
        maya.cmds.undoInfo(stateWithoutFlush=True)
        # totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        # print('Update ' + str(totalTime))

    def exitSXTools(self):
        scriptJobs = maya.cmds.scriptJob(listJobs=True)
        for job in scriptJobs:
            if ('sxtools' in job) and ('uiDeleted' not in job):
                index = int(job.split(':')[0])
                maya.cmds.scriptJob(kill=index)
        if sxglobals.settings:
            del sxglobals.settings
        if sxglobals.setup:
            del sxglobals.setup
        if sxglobals.export:
            del sxglobals.export
        if sxglobals.tools:
            del sxglobals.tools
        if sxglobals.layers:
            del sxglobals.layers
        if sxglobals.ui:
            del sxglobals.ui
        if sxglobals.core:
            del sxglobals.core

    def resetSXTools(self):
        varList = maya.cmds.optionVar(list=True)
        for var in varList:
            if ('SXTools' in var):
                maya.cmds.optionVar(remove=str(var))
        print('SX Tools: Settings reset')

    # The user can have various different types of objects selected.
    # The selections are filtered for the tool.
    def selectionManager(self):
        sxglobals.settings.selectionArray = maya.cmds.ls(sl=True)
        sxglobals.settings.shapeArray = maya.cmds.listRelatives(
            sxglobals.settings.selectionArray,
            type='mesh',
            allDescendents=True,
            fullPath=True)
        sxglobals.settings.objectArray = list(set(maya.cmds.ls(
            maya.cmds.listRelatives(
                sxglobals.settings.shapeArray,
                parent=True,
                fullPath=True))))
        sxglobals.settings.componentArray = maya.cmds.filterExpand(
            sxglobals.settings.selectionArray, sm=(31, 32, 34, 70))

        # If only shape nodes are selected
        onlyShapes = True
        for selection in sxglobals.settings.selectionArray:
            if 'Shape' not in str(selection):
                onlyShapes = False
        if onlyShapes:
            sxglobals.settings.shapeArray = sxglobals.settings.selectionArray
            sxglobals.settings.objectArray = maya.cmds.listRelatives(
                sxglobals.settings.shapeArray, parent=True, fullPath=True)

        # Maintain correct object selection
        # even if only components are selected
        if ((sxglobals.settings.shapeArray is None) and
           (sxglobals.settings.componentArray is not None)):
            sxglobals.settings.shapeArray = maya.cmds.ls(
                sxglobals.settings.selectionArray,
                o=True, dag=True, type='mesh', long=True)
            sxglobals.settings.objectArray = maya.cmds.listRelatives(
                sxglobals.settings.shapeArray, parent=True, fullPath=True)

        # The case when the user selects a component set
        if ((len(maya.cmds.ls(sl=True, type='objectSet')) > 0) and
           (sxglobals.settings.componentArray is not None)):
            del sxglobals.settings.componentArray[:]

        if sxglobals.settings.shapeArray is None:
            sxglobals.settings.shapeArray = []

        if sxglobals.settings.objectArray is None:
            sxglobals.settings.objectArray = []

        if sxglobals.settings.componentArray is None:
            sxglobals.settings.componentArray = []

        sxglobals.tools.checkHistory(sxglobals.settings.objectArray)

    def verifySceneState(self):
        x1 = sxglobals.setup.createDefaultLights()
        x2 = sxglobals.setup.createCreaseSets()
        x3 = sxglobals.setup.createSubMeshSets()
        x4 = sxglobals.setup.createDisplayLayers()

        if (x1 or x2 or x3 or x4):
            maya.cmds.select(clear=True)

        # Hacky hack to prevent Maya's outliner bug from
        # replicating unlimited sets per refresh
        # if not maya.cmds.objExists('sxToolsItemFilter'):
        #     maya.cmds.itemFilter('sxToolsItemFilter', bt='creaseSet')
        # maya.cmds.outlinerEditor('outlinerPanel1', edit=True, filter='sxToolsItemFilter')
        # maya.cmds.outlinerEditor('outlinerPanel1', edit=True, refresh=True)
        # maya.cmds.outlinerEditor('outlinerPanel1', edit=True, filter='')

        # Make sure selected things are using the correct material
        if maya.cmds.getAttr('assetsLayer.visibility'):
            if sxglobals.settings.tools['compositor'] == 1:
                for shape in sxglobals.settings.shapeArray:
                    mode = maya.cmds.getAttr(str(shape) + '.shadingMode')
                    if mode == 0:
                        maya.cmds.sets(
                            shape, e=True, forceElement='SXShaderSG')
                    else:
                        maya.cmds.sets(
                            shape, e=True, forceElement='SXDebugShaderSG')
            else:
                maya.cmds.sets(
                    sxglobals.settings.shapeArray, e=True, forceElement='SXShaderSG')

        # Vertex color display with the custom
        # shader requires textured mode
        maya.cmds.modelEditor(
            'modelPanel4',
            edit=True,
            useDefaultMaterial=False,
            displayLights='all',
            lights=True,
            displayTextures=True)

        # Adjust viewport crease levels based on
        # the subdivision level of the selected object
        if sxglobals.settings.tools['matchSubdivision']:
            if maya.cmds.getAttr(sxglobals.settings.objectArray[0] + '.subdivisionLevel') > 0:
                sdl = maya.cmds.getAttr(sxglobals.settings.objectArray[0] + '.subdivisionLevel')
                maya.cmds.setAttr('sxCrease1.creaseLevel', sdl * 0.25)
                maya.cmds.setAttr('sxCrease2.creaseLevel', sdl * 0.5)
                maya.cmds.setAttr('sxCrease3.creaseLevel', sdl * 0.75)
                maya.cmds.setAttr('sxCrease4.creaseLevel', 10)

    # Re-draws the UI dynamically for different selection types
    def refreshSXTools(self):
        # base canvases for all SX Tools UI
        if maya.cmds.layout('canvasPanes', exists=True):
            maya.cmds.deleteUI('canvasPanes')

        if maya.cmds.layout('topCanvas', exists=True):
            maya.cmds.deleteUI('topCanvas', lay=True)

        if maya.cmds.layout('canvas', exists=True):
            maya.cmds.deleteUI('canvas', lay=True)

        maya.cmds.paneLayout(
            'canvasPanes',
            parent=sxglobals.dockID,
            width=250,
            configuration='horizontal2',
            separatorMovedCommand='sxtools.sxglobals.ui.calculateDivision()')

        maya.cmds.scrollLayout(
            'topCanvas',
            childResizable=True,
            parent='canvasPanes',
            height=10,
            horizontalScrollBarThickness=16,
            verticalScrollBarThickness=16,
            verticalScrollBarAlwaysVisible=False)

        # If nothing selected, or defaults not set, construct setup view
        if ((len(sxglobals.settings.shapeArray) == 0) or
           not (maya.cmds.optionVar(exists='SXToolsPrefsFile')) or
           ('LayerData' not in sxglobals.settings.project)):
            sxglobals.settings.tools['compositeEnabled'] = False
            sxglobals.ui.setupProjectUI()

        # If exported objects selected, construct message
        elif sxglobals.export.checkExported(sxglobals.settings.objectArray):
            sxglobals.settings.tools['compositeEnabled'] = False
            maya.cmds.setAttr('exportsLayer.visibility', 1)
            maya.cmds.setAttr('skinMeshLayer.visibility', 0)
            maya.cmds.setAttr('assetsLayer.visibility', 0)
            maya.cmds.editDisplayLayerGlobals(cdl='exportsLayer')
            # hacky hack to refresh the layer editor
            maya.cmds.delete(maya.cmds.createDisplayLayer(empty=True))
            sxglobals.ui.exportObjectsUI()

        # If skinned meshes are selected, construct message
        elif sxglobals.tools.checkSkinMesh(sxglobals.settings.objectArray):
            sxglobals.settings.tools['compositeEnabled'] = False
            maya.cmds.setAttr('exportsLayer.visibility', 0)
            maya.cmds.setAttr('skinMeshLayer.visibility', 1)
            maya.cmds.setAttr('assetsLayer.visibility', 0)
            maya.cmds.editDisplayLayerGlobals(cdl='skinMeshLayer')
            # hacky hack to refresh the layer editor
            maya.cmds.delete(maya.cmds.createDisplayLayer(empty=True))
            sxglobals.ui.skinMeshUI()

        # If objects have empty color sets, construct error message
        elif sxglobals.layers.verifyObjectLayers(sxglobals.settings.shapeArray)[0] == 1:
            sxglobals.settings.tools['compositeEnabled'] = False
            sxglobals.ui.emptyObjectsUI()

        # If objects have mismatching color sets, construct error message
        elif sxglobals.layers.verifyObjectLayers(sxglobals.settings.shapeArray)[0] == 2:
            sxglobals.settings.tools['compositeEnabled'] = False
            sxglobals.ui.mismatchingObjectsUI()

        # Construct layer tools window
        else:
            sxglobals.settings.tools['compositeEnabled'] = True
            if sxglobals.settings.frames['paneDivision'] == 0:
                sxglobals.ui.calculateDivision()

            maya.cmds.paneLayout(
                'canvasPanes',
                edit=True,
                paneSize=(1, 100, sxglobals.settings.frames['paneDivision']))

            maya.cmds.scrollLayout(
                'canvas',
                childResizable=True,
                parent='canvasPanes',
                horizontalScrollBarThickness=16,
                verticalScrollBarThickness=16,
                verticalScrollBarAlwaysVisible=False)

            maya.cmds.editDisplayLayerMembers(
                'assetsLayer',
                sxglobals.settings.objectArray)
            maya.cmds.setAttr('exportsLayer.visibility', 0)
            maya.cmds.setAttr('skinMeshLayer.visibility', 0)
            maya.cmds.setAttr('assetsLayer.visibility', 1)
            maya.cmds.editDisplayLayerGlobals(cdl='assetsLayer')
            # hacky hack to refresh the layer editor
            maya.cmds.delete(maya.cmds.createDisplayLayer(empty=True))

            if sxglobals.ui.history:
                sxglobals.ui.historyUI()

            if sxglobals.ui.multiShapes and not sxglobals.ui.history:
                sxglobals.ui.multiShapesUI()

            sxglobals.ui.layerViewUI()
            sxglobals.ui.applyColorToolUI()
            sxglobals.ui.gradientToolUI()
            sxglobals.ui.bakeOcclusionToolUI()
            sxglobals.ui.masterPaletteToolUI()
            sxglobals.ui.assignCreaseToolUI()
            sxglobals.ui.createSkinMeshUI()
            sxglobals.ui.exportFlagsUI()
            sxglobals.ui.exportButtonUI()

            sxglobals.layers.refreshLayerList()
            sxglobals.layers.compositeLayers()

        maya.cmds.setFocus('MayaWindow')
