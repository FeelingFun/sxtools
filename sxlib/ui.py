# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd.
#   Released under MIT license
# ----------------------------------------------------------------------------

import maya.cmds
import maya.mel as mel
import sxglobals


class UI(object):
    def __init__(self):
        self.history = False
        self.multiShapes = False
        return None

    def __del__(self):
        print('SX Tools: Exiting UI')

    def historyUI(self):
        maya.cmds.frameLayout(
            'historyWarningFrame',
            parent='canvas',
            label='WARNING: Construction history detected!',
            backgroundColor=(0.35, 0.1, 0),
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.button(
            'disableHistoryButton',
            parent='historyWarningFrame',
            label='Delete and Disable History',
            command=(
                'maya.cmds.delete(sxtools.sxglobals.settings.objectArray, ch=True)\n'
                'maya.cmds.constructionHistory(toggle=False)\n'
                'sxtools.sxglobals.core.updateSXTools()'))

    def multiShapesUI(self):
        maya.cmds.frameLayout(
            'shapeWarningFrame',
            parent='canvas',
            label='WARNING: Multiple shapes in one object!',
            backgroundColor=(0.6, 0.3, 0),
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.button(
            'disableShapesButton',
            parent='shapeWarningFrame',
            label='Delete Extra Shapes',
            command=(
                'maya.cmds.delete('
                'sxtools.sxglobals.settings.multiShapeArray, shape=True)\n'
                'sxtools.sxglobals.core.updateSXTools()'))

    def openSXPaintTool(self):
        mel.eval('PaintVertexColorTool;')
        maya.cmds.artAttrPaintVertexCtx(
            'artAttrColorPerVertexContext', edit=True, usepressure=False)
        maya.cmds.toolPropertyWindow(inMainWindow=True)

    def setupProjectUI(self):
        maya.cmds.frameLayout(
            'emptyFrame',
            label='No mesh objects selected',
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=5)

        maya.cmds.frameLayout(
            'prefsFrame',
            parent='canvas',
            width=250,
            label='Tool Preferences',
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=sxglobals.settings.frames['prefsCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['prefsCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['prefsCollapse']=False"))

        if 'dockPosition' in sxglobals.settings.project:
            dockPos = sxglobals.settings.project['dockPosition']
        else:
            dockPos = 1

        maya.cmds.radioButtonGrp(
            'dockPrefsButtons',
            parent='prefsFrame',
            vertical=True,
            labelArray2=['Dock Left', 'Dock Right'],
            select=dockPos,
            numberOfRadioButtons=2,
            onCommand1=(
                "sxtools.sxglobals.settings.project['dockPosition'] = 1\n"
                "maya.cmds.workspaceControl('SXToolsUI', edit=True,"
                " dockToControl=('Outliner', 'right'))"),
            onCommand2=(
                "sxtools.sxglobals.settings.project['dockPosition'] = 2\n"
                "maya.cmds.workspaceControl('SXToolsUI', edit=True,"
                " dockToControl=('AttributeEditor', 'left'))"))

        maya.cmds.checkBox(
            'historyToggle',
            label='Construction History Enabled',
            value=maya.cmds.constructionHistory(query=True, toggle=True),
            ann='It is strongly recommended to DISABLE HISTORY when using SX Tools.',
            onCommand='maya.cmds.constructionHistory(toggle=True)',
            offCommand='maya.cmds.constructionHistory(toggle=False)')

        maya.cmds.frameLayout(
            'setupFrame',
            parent='canvas',
            width=250,
            label='Project Setup',
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=sxglobals.settings.frames['setupCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['setupCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['setupCollapse']=False"),
            borderVisible=False)

        maya.cmds.columnLayout(
            'prefsColumn',
            parent='setupFrame',
            rowSpacing=5,
            adjustableColumn=True)

        maya.cmds.button(
            label='Select Settings File',
            parent='prefsColumn',
            statusBarMessage='Shift-click button to reload settings from file',
            command=(
                'sxtools.sxglobals.settings.setPreferencesFile()\n'
                'sxtools.sxglobals.core.updateSXTools()'))

        if maya.cmds.optionVar(exists='SXToolsPrefsFile') and len(
                str(maya.cmds.optionVar(query='SXToolsPrefsFile'))) > 0:
            maya.cmds.text(
                label='Current settings location:')
            maya.cmds.text(
                label=maya.cmds.optionVar(query='SXToolsPrefsFile'),
                ww=True)
        else:
            maya.cmds.text(
                label='WARNING: Settings file location not set!',
                backgroundColor=(0.35, 0.1, 0),
                ww=True)

        maya.cmds.text(label=' ')

        maya.cmds.rowColumnLayout(
            'refLayerRowColumns',
            parent='setupFrame',
            numberOfColumns=3,
            columnWidth=((1, 90), (2, 60), (3, 80)),
            columnAttach=[(1, 'left', 0), (2, 'left', 0), (3, 'left', 0)],
            rowSpacing=(1, 0))

        maya.cmds.text(label=' ')
        maya.cmds.text(label='Count')
        maya.cmds.text(label='Mask Export')

        # Max layers 10. Going higher causes instability.
        maya.cmds.text(label='Color layers:')
        maya.cmds.intField(
            'layerCount',
            value=10,
            minValue=1,
            maxValue=10,
            step=1,
            changeCommand=(
                "sxtools.sxglobals.ui.refreshLayerDisplayNameList()\n"
                "maya.cmds.setFocus('MayaWindow')"))
        if 'LayerCount' in sxglobals.settings.project:
            maya.cmds.intField(
                'layerCount',
                edit=True,
                value=sxglobals.settings.project['LayerCount'])

        maya.cmds.textField('maskExport', text='U3')

        maya.cmds.text(label=' ')
        maya.cmds.text(label=' ')
        maya.cmds.text(label=' ')

        maya.cmds.text(label='Channel')
        maya.cmds.text(label='Enabled')
        maya.cmds.text(label='Export UV')

        maya.cmds.text('occlusionLabel', label='Occlusion:')
        maya.cmds.checkBox('occlusion', label='', value=True)
        maya.cmds.textField('occlusionExport', text='U1')

        maya.cmds.text('specularLabel', label='Specular:')
        maya.cmds.checkBox('specular', label='', value=True)
        maya.cmds.textField('specularExport', text='V1')

        maya.cmds.text('transmissionLabel', label='Transmission:')
        maya.cmds.checkBox('transmission', label='', value=True)
        maya.cmds.textField('transmissionExport', text='U2')

        maya.cmds.text('emissionLabel', label='Emission:')
        maya.cmds.checkBox('emission', label='', value=True)
        maya.cmds.textField('emissionExport', text='V2')

        maya.cmds.text('alphaOverlay1Label', label='Overlay1 (A):')
        maya.cmds.textField('alphaOverlay1', text='layer8')
        maya.cmds.textField('alphaOverlay1Export', text='U4')

        maya.cmds.text('alphaOverlay2Label', label='Overlay2 (A):')
        maya.cmds.textField('alphaOverlay2', text='layer9')
        maya.cmds.textField('alphaOverlay2Export', text='V4')

        maya.cmds.text('overlayLabel', label='Overlay (RGBA):')
        maya.cmds.textField('overlay', text='layer10')
        maya.cmds.textField('overlayExport', text='UV5,UV6')

        if 'LayerData' in sxglobals.settings.project:
            maya.cmds.checkBox(
                'occlusion',
                edit=True,
                value=bool(sxglobals.settings.project['LayerData']['occlusion'][5]))
            maya.cmds.checkBox(
                'specular',
                edit=True,
                value=bool(sxglobals.settings.project['LayerData']['specular'][5]))
            maya.cmds.checkBox(
                'transmission',
                edit=True,
                value=bool(sxglobals.settings.project['LayerData']['transmission'][5]))
            maya.cmds.checkBox(
                'emission',
                edit=True,
                value=bool(sxglobals.settings.project['LayerData']['emission'][5]))
            maya.cmds.textField(
                'maskExport',
                edit=True,
                text=(sxglobals.settings.project['LayerData']['layer1'][2]))
            maya.cmds.textField(
                'occlusionExport',
                edit=True,
                text=(sxglobals.settings.project['LayerData']['occlusion'][2]))
            maya.cmds.textField(
                'specularExport',
                edit=True,
                text=(sxglobals.settings.project['LayerData']['specular'][2]))
            maya.cmds.textField(
                'transmissionExport',
                edit=True,
                text=(sxglobals.settings.project['LayerData']['transmission'][2]))
            maya.cmds.textField(
                'emissionExport',
                edit=True,
                text=(sxglobals.settings.project['LayerData']['emission'][2]))

            alpha1 = None
            alpha2 = None
            alpha1Export = None
            alpha2Export = None
            overlay = None
            overlayExport = None

            for key, value in sxglobals.settings.project['LayerData'].iteritems():
                if value[3] == 1:
                    alpha1 = key
                    alpha1Export = value[2]
                if value[3] == 2:
                    alpha2 = key
                    alpha2Export = value[2]
                if value[4] is True:
                    overlay = key
                    overlayExport = ', '.join(value[2])
            maya.cmds.textField(
                'alphaOverlay1',
                edit=True,
                text=alpha1)
            maya.cmds.textField(
                'alphaOverlay2',
                edit=True,
                text=alpha2)
            maya.cmds.textField(
                'alphaOverlay1Export',
                edit=True,
                text=alpha1Export)
            maya.cmds.textField(
                'alphaOverlay2Export',
                edit=True,
                text=alpha2Export)
            maya.cmds.textField(
                'overlay',
                edit=True,
                text=overlay)
            maya.cmds.textField(
                'overlayExport',
                edit=True,
                text=overlayExport)

        maya.cmds.rowColumnLayout(
            'numlayerFrames',
            parent='setupFrame',
            numberOfColumns=2,
            columnWidth=((1, 160), (2, 70)),
            columnAttach=[(1, 'left', 0), (2, 'left', 0)],
            rowSpacing=(1, 0))

        maya.cmds.text(label='Export Process Options')
        maya.cmds.text(label=' ')

        maya.cmds.text(label='Number of masks:')
        maya.cmds.intField(
            'numMasks',
            minValue=0,
            maxValue=10,
            value=7,
            step=1,
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))
        if 'MaskCount' in sxglobals.settings.project:
            maya.cmds.intField(
                'numMasks',
                edit=True,
                value=sxglobals.settings.project['MaskCount'])
        maya.cmds.text(label='Alpha-to-mask limit:')
        maya.cmds.floatField(
            'exportTolerance',
            value=1.0,
            minValue=0,
            maxValue=1,
            precision=1,
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))
        if 'AlphaTolerance' in sxglobals.settings.project:
            maya.cmds.floatField(
                'exportTolerance',
                edit=True,
                value=sxglobals.settings.project['AlphaTolerance'])
        maya.cmds.text(label='Export preview grid spacing:')
        maya.cmds.intField(
            'exportOffset',
            value=5,
            minValue=0,
            step=1,
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))
        if 'ExportOffset' in sxglobals.settings.project:
            maya.cmds.intField(
                'exportOffset',
                edit=True,
                value=sxglobals.settings.project['ExportOffset'])

        maya.cmds.text(label='Use "_paletted" export suffix:')
        maya.cmds.checkBox(
            'suffixCheck',
            label='',
            value=True,
            changeCommand=(
                "sxtools.sxglobals.settings.project['ExportSuffix'] = ("
                "maya.cmds.checkBox('suffixCheck', query=True, value=True))"))
        if 'ExportSuffix' in sxglobals.settings.project:
            maya.cmds.checkBox(
                'suffixCheck',
                edit=True,
                value=sxglobals.settings.project['ExportSuffix'])

        maya.cmds.text(label='')
        maya.cmds.text(label='')

        for i in xrange(10):
            layerName = sxglobals.settings.refLayerData[sxglobals.settings.refArray[i]][6]
            labelID = 'display'+str(i+1)
            labelText = sxglobals.settings.refArray[i] + ' display name:'
            fieldLabel = sxglobals.settings.refArray[i] + 'Display'
            if (('LayerData' in sxglobals.settings.project) and
               (layerName in sxglobals.settings.project['LayerData'].keys())):
                layerName = sxglobals.settings.project['LayerData'][layerName][6]
            maya.cmds.text(labelID, label=labelText)
            maya.cmds.textField(fieldLabel, text=layerName)

        maya.cmds.columnLayout(
            'reflayerFrame',
            parent='setupFrame',
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.text(label=' ', parent='reflayerFrame')

        if maya.cmds.optionVar(exists='SXToolsPrefsFile') and len(
                str(maya.cmds.optionVar(query='SXToolsPrefsFile'))) > 0:
            maya.cmds.text(
                label='(Shift-click below to apply built-in defaults)',
                parent='reflayerFrame')
            maya.cmds.button(
                label='Apply Project Settings',
                parent='reflayerFrame',
                statusBarMessage=(
                    'Shift-click button to use the built-in default settings'),
                command=(
                    "sxtools.sxglobals.settings.createPreferences()\n"
                    "sxtools.sxglobals.settings.setPreferences()\n"
                    "sxtools.sxglobals.settings.savePreferences()\n"
                    "sxtools.sxglobals.settings.frames['setupCollapse']=True\n"
                    "sxtools.sxglobals.core.updateSXTools()"))

        self.refreshLayerDisplayNameList()

        maya.cmds.workspaceControl(
            sxglobals.dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def refreshLayerDisplayNameList(self):
        for i in xrange(10):
            layerName = sxglobals.settings.refArray[i]
            fieldLabel = layerName + 'Display'
            if i < maya.cmds.intField('layerCount', query=True, value=True):
                if (('LayerData' in sxglobals.settings.project) and
                   (layerName in sxglobals.settings.project['LayerData'].keys())):
                    layerText = sxglobals.settings.project['LayerData'][layerName][6]
                else:
                    layerText = sxglobals.settings.refLayerData[sxglobals.settings.refArray[i]][6]
                maya.cmds.textField(
                    fieldLabel,
                    edit=True,
                    enable=True,
                    text=layerText)
            else:
                maya.cmds.textField(
                    fieldLabel,
                    edit=True,
                    enable=False)

    def exportObjectsUI(self):
        maya.cmds.frameLayout(
            'exportObjFrame',
            label=str(len(sxglobals.settings.objectArray)) + ' export objects selected',
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=2)
        maya.cmds.button(
            label='Select and show all export meshes',
            command='sxtools.sxglobals.export.viewExported()')
        maya.cmds.button(
            label='Hide exported, show source meshes',
            command=(
                "maya.cmds.setAttr('exportsLayer.visibility', 0)\n"
                "maya.cmds.setAttr('skinMeshLayer.visibility', 0)\n"
                "maya.cmds.setAttr('assetsLayer.visibility', 1)\n"
                "maya.cmds.editDisplayLayerGlobals(cdl='assetsLayer')\n"
                "maya.cmds.delete(maya.cmds.createDisplayLayer(empty=True))\n"
                "maya.cmds.select(clear=True)"))

        maya.cmds.text(label='Preview export object data:')
        maya.cmds.radioButtonGrp(
            'exportShadingButtons1',
            parent='exportObjFrame',
            vertical=True,
            columnWidth3=(80, 80, 80),
            columnAttach3=('left', 'left', 'left'),
            labelArray3=['Composite', 'Albedo', 'Layer Masks'],
            select=1,
            numberOfRadioButtons=3,
            onCommand1=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand2=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand3=("sxtools.sxglobals.export.viewExportedMaterial()"))
        maya.cmds.radioButtonGrp(
            'exportShadingButtons2',
            parent='exportObjFrame',
            vertical=True,
            shareCollection='exportShadingButtons1',
            columnWidth4=(80, 80, 80, 80),
            columnAttach4=('left', 'left', 'left', 'left'),
            labelArray4=['Occlusion', 'Specular', 'Transmission', 'Emission'],
            numberOfRadioButtons=4,
            onCommand1=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand2=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand3=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand4=("sxtools.sxglobals.export.viewExportedMaterial()"))

        maya.cmds.radioButtonGrp(
            'exportShadingButtons3',
            parent='exportObjFrame',
            vertical=True,
            shareCollection='exportShadingButtons1',
            columnWidth3=(80, 80, 80),
            columnAttach3=('left', 'left', 'left'),
            labelArray3=['Alpha Overlay 1', 'Alpha Overlay 2', 'Overlay'],
            numberOfRadioButtons=3,
            onCommand1=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand2=("sxtools.sxglobals.export.viewExportedMaterial()"),
            onCommand3=("sxtools.sxglobals.export.viewExportedMaterial()"))

        maya.cmds.button(
            label='Choose Export Path',
            width=120,
            command=(
                "sxtools.sxglobals.export.setExportPath()\n"
                "sxtools.sxglobals.core.updateSXTools()"))

        if (('SXToolsExportPath' in sxglobals.settings.project) and
           (len(sxglobals.settings.project['SXToolsExportPath']) == 0)):
            maya.cmds.text(label='No export folder selected!')
        elif 'SXToolsExportPath' in sxglobals.settings.project:
            exportPathText = (
                'Export Path: ' + sxglobals.settings.project['SXToolsExportPath'])
            maya.cmds.text(label=exportPathText, ww=True)
            maya.cmds.button(
                label='Write FBX Files',
                width=120,
                command=(
                    "sxtools.sxglobals.export.exportObjects("
                    "sxtools.sxglobals.settings.project['SXToolsExportPath'])"))
        else:
            maya.cmds.text(label='No export folder selected!')

        maya.cmds.setParent('exportObjFrame')
        maya.cmds.setParent('canvas')
        maya.cmds.workspaceControl(
            sxglobals.dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def emptyObjectsUI(self):
        sxglobals.settings.patchArray = sxglobals.layers.verifyObjectLayers(
            sxglobals.settings.shapeArray)[1]
        patchLabel = 'Objects with no layers: ' + str(len(sxglobals.settings.patchArray))
        maya.cmds.frameLayout(
            'patchFrame',
            label=patchLabel,
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.text(
            label=("Click on empty to view project defaults.\n"), align='left')

        if maya.cmds.objExists('SXShader'):
            maya.cmds.text(
                label=(
                    "Add project layers to selected objects\n"
                    "by pressing the button below.\n"),
                align="left")
            maya.cmds.button(
                label='Add missing color sets',
                command=(
                    'sxtools.sxglobals.layers.patchLayers('
                    'sxtools.sxglobals.settings.patchArray)'))
        maya.cmds.setParent('patchFrame')
        maya.cmds.setParent('canvas')
        maya.cmds.workspaceControl(
            sxglobals.dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def mismatchingObjectsUI(self):
        sxglobals.settings.patchArray = sxglobals.layers.verifyObjectLayers(
            sxglobals.settings.shapeArray)[1]
        patchLabel = 'Objects with nonstandard layers: ' + str(
            len(sxglobals.settings.patchArray))
        maya.cmds.frameLayout(
            'patchFrame',
            label=patchLabel,
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.text(
            label=(
                "To fix color layers:\n"
                "1. Open Color Set Editor\n"
                "2. Delete any redundant color sets\n"
                "3. Rename any needed color sets\n"
                "    using reference names\n"
                "4. DELETE HISTORY on selected objects\n"
                "5. Press 'Add Missing Color Sets' button\n\n"
                "Reference names:\nlayer1-nn, occlusion, specular,\n"
                "transmission, emission"
            ),
            align="left")
        maya.cmds.button(
            label='Color Set Editor',
            command="maya.mel.eval('colorSetEditor;')")
        if 'LayerData' in sxglobals.settings.project:
            maya.cmds.button(
                label='Add missing color sets',
                command=(
                    'sxtools.sxglobals.layers.patchLayers('
                    'sxtools.sxglobals.settings.patchArray)'))
        maya.cmds.setParent('patchFrame')
        maya.cmds.setParent('canvas')
        maya.cmds.workspaceControl(
            sxglobals.dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def skinMeshUI(self):
        maya.cmds.frameLayout(
            'patchFrame',
            label='Skinning Mesh Selected',
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=0)
        maya.cmds.text(
            parent='patchFrame',
            label=(
                "Create skeletons and edit skin weights on meshes with _skinned suffix.\n\n"
                "Blend shapes are also supported.\n\n"
                "Select non-skinned meshes in the Outliner."),
                align='left',
                ww=True)
        maya.cmds.setParent('patchFrame')
        maya.cmds.setParent('canvas')
        maya.cmds.workspaceControl(
            sxglobals.dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def layerViewUI(self):
        maya.cmds.frameLayout(
            'layerFrame',
            parent='canvas',
            width=250,
            marginWidth=5,
            marginHeight=2)
        maya.cmds.radioButtonGrp(
            'shadingButtons',
            parent='layerFrame',
            columnWidth3=(80, 80, 80),
            columnAttach3=('left', 'left', 'left'),
            labelArray3=['Final', 'Debug', 'Alpha'],
            select=1,
            numberOfRadioButtons=3,
            onCommand1=(
                "sxtools.sxglobals.tools.setShadingMode(0)\n"
                "maya.cmds.polyOptions(activeObjects=True,"
                "colorMaterialChannel='ambientDiffuse',"
                "colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayLight;')"),
            onCommand2=(
                "sxtools.sxglobals.tools.setShadingMode(1)\n"
                "maya.cmds.polyOptions(activeObjects=True,"
                "colorMaterialChannel='none',"
                "colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayShadedAndTextured;')"),
            onCommand3=(
                "sxtools.sxglobals.tools.setShadingMode(2)\n"
                "maya.cmds.polyOptions(activeObjects=True,"
                "colorMaterialChannel='ambientDiffuse',"
                "colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayLight;')"))
        sxglobals.tools.verifyShadingMode()

        maya.cmds.textScrollList(
            'layerList',
            height=200,
            allowMultiSelection=False,
            ann=(
                'Doubleclick to hide/unhide layer in Final shading mode\n'
                'Shift + doubleclick to hide/unhide unselected layers\n'
                '(H) - hidden layer\n'
                '(M) - mask layer\n'
                '(A) - adjustment layer'))
        sxglobals.layers.refreshLayerList()

        maya.cmds.popupMenu(
            'layerPopUp',
            parent='layerList')
        maya.cmds.menuItem(
            'copyLayerMenuItem',
            parent='layerPopUp',
            label='Copy Layer',
            command=(
                'sxtools.sxglobals.settings.tools["sourceLayer"] = '
                'sxtools.sxglobals.layers.getSelectedLayer()\n'
                'maya.cmds.menuItem("sourceNameMenuItem", edit=True,'
                'label="Source: " + '
                'str(sxtools.sxglobals.settings.tools["sourceLayer"]))'))
        maya.cmds.menuItem(
            'pasteLayerMenuItem',
            parent='layerPopUp',
            label='Paste Layer',
            command=(
                'sxtools.sxglobals.settings.tools["targetLayer"] = '
                'sxtools.sxglobals.layers.getSelectedLayer()\n'
                'sxtools.sxglobals.tools.copyLayer('
                'sxtools.sxglobals.settings.objectArray)'))
        maya.cmds.menuItem(
            'swapLayerMenuItem',
            parent='layerPopUp',
            label='Swap Layer',
            command=(
                'sxtools.sxglobals.settings.tools["targetLayer"] = '
                'sxtools.sxglobals.layers.getSelectedLayer()\n'
                'sxtools.sxglobals.tools.swapLayers('
                'sxtools.sxglobals.settings.shapeArray)'))
        maya.cmds.menuItem(
            parent='layerPopUp',
            divider=True)
        maya.cmds.menuItem(
            'mergeUpMenuItem',
            parent='layerPopUp',
            label='Merge Layer Up',
            command=(
                "sxtools.sxglobals.layers.mergeLayerDirection("
                "sxtools.sxglobals.settings.shapeArray, True)"))
        maya.cmds.menuItem(
            'mergeDownMenuItem',
            parent='layerPopUp',
            label='Merge Layer Down',
            command=(
                "sxtools.sxglobals.layers.mergeLayerDirection("
                "sxtools.sxglobals.settings.shapeArray, False)"))
        maya.cmds.menuItem(
            parent='layerPopUp',
            divider=True)
        maya.cmds.menuItem(
            'sourceNameMenuItem',
            parent='layerPopUp',
            label='Source Layer: ' + str(sxglobals.settings.tools["sourceLayer"]),
            enable=False)

        maya.cmds.rowColumnLayout(
            'layerSelectRowColumns',
            parent='layerFrame',
            numberOfColumns=2,
            columnWidth=((1, 120), (2, 120)),
            columnSpacing=([1, 0], [2, 5]),
            rowSpacing=(1, 5))

        maya.cmds.button(
            label='Select Layer Mask',
            width=100,
            height=20,
            statusBarMessage='Shift-click button to invert selection',
            command="maya.cmds.select(sxtools.sxglobals.tools.getLayerMask())")
        if len(sxglobals.settings.componentArray) > 0:
            maya.cmds.button(
                'clearButton',
                label='Clear Selected',
                statusBarMessage=(
                    'Shift-click button to clear'
                    'all layers on selected components'),
                width=100,
                height=20,
                command=(
                    "sxtools.sxglobals.tools.clearSelector()\n"
                    "sxtools.sxglobals.tools.getLayerPaletteOpacity("
                    "sxtools.sxglobals.settings.shapeArray["
                    "len(sxtools.sxglobals.settings.shapeArray)-1],"
                    "sxtools.sxglobals.layers.getSelectedLayer())\n"
                    "sxtools.sxglobals.layers.refreshLayerList()\n"
                    "sxtools.sxglobals.layers.refreshSelectedItem()"))
        else:
            maya.cmds.button(
                'clearButton',
                label='Clear Layer',
                statusBarMessage=(
                    'Shift-click button to clear'
                    'all layers on selected objects'),
                width=100,
                height=20,
                command=(
                    "sxtools.sxglobals.tools.clearSelector()\n"
                    "sxtools.sxglobals.tools.getLayerPaletteOpacity("
                    "sxtools.sxglobals.settings.shapeArray["
                    "len(sxtools.sxglobals.settings.shapeArray)-1], "
                    "sxtools.sxglobals.layers.getSelectedLayer())\n"
                    "sxtools.sxglobals.layers.refreshLayerList()\n"
                    "sxtools.sxglobals.layers.refreshSelectedItem()"))

        maya.cmds.rowColumnLayout(
            'layerRowColumns',
            parent='layerFrame',
            numberOfColumns=2,
            columnWidth=((1, 120), (2, 120)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))

        maya.cmds.text(
            'layerBlendModeLabel',
            label='layer Blend Mode:')
        maya.cmds.optionMenu(
            'layerBlendModes',
            parent='layerRowColumns',
            changeCommand='sxtools.sxglobals.tools.setLayerBlendMode()')
        maya.cmds.menuItem(
            'alphaBlend',
            label='Alpha',
            parent='layerBlendModes')
        maya.cmds.menuItem(
            'additiveBlend',
            label='Add',
            parent='layerBlendModes')
        maya.cmds.menuItem(
            'multiplyBlend',
            label='Multiply',
            parent='layerBlendModes')

        maya.cmds.text(
            'layerColorLabel',
            label='layer Colors:')
        maya.cmds.palettePort(
            'layerPalette',
            dimensions=(8, 1),
            height=10,
            actualTotal=8,
            editable=True,
            colorEditable=False,
            changeCommand=(
                'sxtools.sxglobals.settings.currentColor = maya.cmds.palettePort('
                '\"layerPalette\", query=True, rgb=True)\n'
                'sxtools.sxglobals.tools.setPaintColor('
                'sxtools.sxglobals.settings.currentColor)'))

        maya.cmds.text(
            'layerOpacityLabel',
            label='layer Opacity:')
        maya.cmds.floatSlider(
            'layerOpacitySlider',
            min=0.0,
            max=1.0,
            changeCommand=(
                "sxtools.sxglobals.tools.setLayerOpacity()\n"
                "sxtools.sxglobals.layers.refreshLayerList()\n"
                "sxtools.sxglobals.layers.refreshSelectedItem()"))
        sxglobals.tools.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshSelectedItem()

    def applyColorToolUI(self):
        maya.cmds.frameLayout(
            "applyColorFrame",
            parent="canvas",
            label="Apply Color",
            width=250,
            marginWidth=5,
            marginHeight=2,
            collapsable=True,
            collapse=sxglobals.settings.frames['applyColorCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['applyColorCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['applyColorCollapse']=False"))
        maya.cmds.button(
            parent='applyColorFrame',
            label='Paint Vertex Colors',
            width=100,
            height=20,
            command="sxtools.sxglobals.ui.openSXPaintTool()")
        maya.cmds.rowColumnLayout(
            "applyColorRowColumns",
            parent="applyColorFrame",
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, "right", 0), (2, "both", 5)],
            rowSpacing=(1, 5))
        maya.cmds.text(
            'recentPaletteLabel',
            parent='applyColorRowColumns',
            label="Recent Colors:")
        maya.cmds.palettePort(
            'recentPalette',
            parent='applyColorRowColumns',
            dimensions=(8, 1),
            width=120,
            height=10,
            actualTotal=8,
            editable=True,
            colorEditable=False,
            scc=sxglobals.settings.tools['recentPaletteIndex'],
            changeCommand='sxtools.sxglobals.tools.setApplyColor()')
        maya.cmds.text(
            'applyColorLabel',
            parent='applyColorRowColumns',
            label='Color:')
        maya.cmds.colorSliderGrp(
            'sxApplyColor',
            parent='applyColorRowColumns',
            label='',
            rgb=sxglobals.settings.currentColor,
            columnWidth3=(0, 20, 120),
            adjustableColumn3=3,
            columnAlign3=('right', 'left', 'both'),
            changeCommand=(
                "sxtools.sxglobals.settings.currentColor = ("
                "maya.cmds.colorSliderGrp("
                "'sxApplyColor', query=True, rgbValue=True))"))
        maya.cmds.text(
            'noiseValueLabel',
            parent='applyColorRowColumns',
            label='Noise Intensity:')
        maya.cmds.floatSlider(
            'noiseSlider',
            parent='applyColorRowColumns',
            step=0.2,
            min=0.0,
            max=1.0,
            width=100,
            value=sxglobals.settings.tools['noiseValue'],
            changeCommand=(
                "sxtools.sxglobals.settings.tools['noiseValue'] = ("
                "maya.cmds.floatSlider("
                "'noiseSlider', query=True, value=True))"))
        maya.cmds.text(
            'monoLabel',
            parent='applyColorRowColumns',
            label='Monochromatic:')
        maya.cmds.checkBox(
            'mono',
            parent='applyColorRowColumns',
            label='',
            value=sxglobals.settings.tools['noiseMonochrome'],
            changeCommand=(
                "sxtools.sxglobals.settings.tools['noiseMonochrome'] = ("
                "maya.cmds.checkBox('mono', query=True, value=True))"))
        maya.cmds.text(
            'overwriteAlphaLabel',
            parent='applyColorRowColumns',
            label='Overwrite Alpha:')
        maya.cmds.checkBox(
            'overwriteAlpha',
            parent='applyColorRowColumns',
            label='',
            ann=(
                'Component selections always override alpha. '
                'When applying color to an entire object, '
                'disabling Overwrite Alpha will preserve '
                'existing alpha values.'),
            value=sxglobals.settings.tools['overwriteAlpha'],
            changeCommand=(
                'sxtools.sxglobals.settings.tools["overwriteAlpha"] = ('
                'maya.cmds.checkBox('
                '"overwriteAlpha", query=True, value=True))'))
        maya.cmds.button(
            label='Apply Color',
            parent='applyColorFrame',
            height=30,
            width=100,
            command=(
                'sxtools.sxglobals.settings.currentColor = ('
                'maya.cmds.colorSliderGrp('
                '"sxApplyColor", query=True, rgbValue=True))\n'
                'sxtools.sxglobals.tools.colorFill('
                'maya.cmds.checkBox('
                '"overwriteAlpha", query=True, value=True))\n'
                'sxtools.sxglobals.tools.updateRecentPalette()'))
        sxglobals.tools.getPalette(
            'recentPalette',
            sxglobals.settings.paletteDict,
            'SXToolsRecentPalette')

    def refreshRampMenu(self):
        maya.cmds.menuItem(label='X-Axis', parent='rampDirection')
        maya.cmds.menuItem(label='Y-Axis', parent='rampDirection')
        maya.cmds.menuItem(label='Z-Axis', parent='rampDirection')
        maya.cmds.menuItem(label='Surface Luminance', parent='rampDirection')
        maya.cmds.menuItem(label='Surface Curvature', parent='rampDirection')

        presetNames = maya.cmds.nodePreset(list='SXRamp')
        presetNameArray = []
        for preset in presetNames:
            if '_Alpha' not in preset:
                presetNameArray.append(preset)

        if len(presetNameArray) > 0:
            for presetName in presetNameArray:
                maya.cmds.menuItem(label=presetName, parent='rampPresets')

            maya.cmds.optionMenu(
                'rampDirection',
                edit=True,
                select=sxglobals.settings.tools['gradientDirection'])

            maya.cmds.optionMenu(
                'rampPresets',
                edit=True,
                select=sxglobals.settings.tools['gradientPreset'])

    def gradientToolUI(self):
        # ramp nodes for gradient tool
        if maya.cmds.objExists('SXRamp') is False:
            maya.cmds.createNode('ramp', name='SXRamp', skipSelect=True)

        if maya.cmds.objExists('SXAlphaRamp') is False:
            maya.cmds.createNode('ramp', name='SXAlphaRamp', skipSelect=True)
            maya.cmds.setAttr('SXAlphaRamp.colorEntryList[0].position', 1)
            maya.cmds.setAttr('SXAlphaRamp.colorEntryList[0].color', 1, 1, 1)
            maya.cmds.setAttr('SXAlphaRamp.colorEntryList[1].position', 0)
            maya.cmds.setAttr('SXAlphaRamp.colorEntryList[1].color', 1, 1, 1)

        maya.cmds.frameLayout(
            "gradientFrame",
            parent="canvas",
            label="Gradient Fill",
            width=250,
            marginWidth=5,
            marginHeight=2,
            collapsable=True,
            collapse=sxglobals.settings.frames['gradientCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['gradientCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['gradientCollapse']=False"),
            borderVisible=False)
        maya.cmds.rowColumnLayout(
            'gradientRowColumns',
            parent='gradientFrame',
            numberOfColumns=2,
            columnWidth=((1, 80), (2, 160)),
            columnAttach=[(1, 'right', 0), (2, 'both', 5)],
            rowSpacing=(1, 2))

        maya.cmds.text(label='Fill Mode:')
        maya.cmds.optionMenu(
            'rampDirection',
            parent='gradientRowColumns',
            changeCommand=(
                'sxtools.sxglobals.settings.tools["gradientDirection"]='
                'maya.cmds.optionMenu("rampDirection", query=True, select=True)'))

        maya.cmds.text(label='Preset:')
        maya.cmds.optionMenu(
            'rampPresets',
            parent='gradientRowColumns',
            changeCommand=(
                'sxtools.sxglobals.settings.tools["gradientPreset"]='
                'maya.cmds.optionMenu("rampPresets", query=True, select=True)\n'
                'sxtools.sxglobals.tools.gradientToolManager("load")'))
        self.refreshRampMenu()

        maya.cmds.button(
            'savePreset',
            parent='gradientRowColumns',
            label='Save Preset',
            ann='Shift-click to delete preset',
            command=(
                "sxtools.sxglobals.tools.gradientToolManager('preset')\n"
                "sxtools.sxglobals.core.updateSXTools()\n"
                "sxtools.sxglobals.settings.savePreferences()"))
        maya.cmds.textField(
            'presetName',
            parent='gradientRowColumns',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Preset Name')

        maya.cmds.attrColorSliderGrp(
            'sxRampColor',
            parent='gradientFrame',
            label='Selected Color:',
            showButton=False,
            columnWidth4=(80, 20, 140, 0),
            adjustableColumn4=3,
            columnAlign4=('right', 'left', 'left', 'left'))
        maya.cmds.attrEnumOptionMenuGrp(
            'sxRampMode',
            parent='gradientFrame',
            label='Interpolation:',
            columnWidth2=(80, 160),
            columnAttach2=('right', 'left'),
            columnAlign2=('right', 'left'))
        maya.cmds.rampColorPort(
            'sxRampControl',
            parent="gradientFrame",
            height=90,
            node='SXRamp',
            selectedColorControl='sxRampColor',
            selectedInterpControl='sxRampMode')
        maya.cmds.attrColorSliderGrp(
            'sxRampAlpha',
            parent='gradientFrame',
            label='Selected Alpha:',
            showButton=False,
            columnWidth4=(80, 20, 140, 0),
            adjustableColumn4=3,
            columnAlign4=('right', 'left', 'left', 'left'))
        maya.cmds.attrEnumOptionMenuGrp(
            'sxAlphaRampMode',
            parent='gradientFrame',
            label='Interpolation:',
            columnWidth2=(80, 160),
            columnAttach2=('right', 'left'),
            columnAlign2=('right', 'left'))
        maya.cmds.rampColorPort(
            'sxRampAlphaControl',
            parent='gradientFrame',
            height=90,
            node='SXAlphaRamp',
            selectedColorControl='sxRampAlpha',
            selectedInterpControl='sxAlphaRampMode')
        maya.cmds.button(
            label='Apply Gradient',
            parent='gradientFrame',
            height=30,
            command=(
                "sxtools.sxglobals.tools.gradientToolManager("
                "maya.cmds.optionMenu('rampDirection', "
                "query=True, select=True))"))
        maya.cmds.setParent('canvas')

    def bakeOcclusionToolUI(self):
        maya.cmds.frameLayout(
            'occlusionFrame',
            parent='canvas',
            label='Bake Occlusion',
            width=250,
            marginWidth=5,
            marginHeight=2,
            collapsable=True,
            collapse=sxglobals.settings.frames['occlusionCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['occlusionCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['occlusionCollapse']=False"))
        maya.cmds.text(
            label=(
                "Occlusion groundplane is placed "
                "at the minY of the bounding box of "
                "each object being baked.\n"
                "Offset pushes the plane down."),
            align="left", ww=True)

        maya.cmds.rowColumnLayout(
            'occlusionOptionRowColumns',
            parent='occlusionFrame',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'right', 0), (2, 'both', 5)],
            rowSpacing=(1, 2))

        maya.cmds.text('rayCountLabel', label='Ray Count:')
        maya.cmds.intField(
            'rayCount',
            value=sxglobals.settings.tools['rayCount'],
            ann=(
                'The number of rays to fire from each vertex on the selection. '
                'Lower ray counts are faster but more noisy.'),
            minValue=1,
            maxValue=2000,
            changeCommand=(
                "sxtools.sxglobals.settings.tools['rayCount'] = ("
                "maya.cmds.intField('rayCount', query=True, value=True))"
            ))

        maya.cmds.text('maxDistanceLabel', label='Ray Max Distance:')
        maya.cmds.floatField(
            'maxDistance',
            value=sxglobals.settings.tools['maxDistance'],
            ann='The distance beyond which no collisions are checked.',
            precision=1,
            minValue=0.0,
            maxValue=10000.0,
            changeCommand=(
                "sxtools.sxglobals.settings.tools['maxDistance'] = ("
                "maya.cmds.floatField('maxDistance', query=True, value=True))"
            ))

        maya.cmds.text('comboOffsetLabel', label='Mesh Offset:')
        maya.cmds.floatField(
            'comboOffset',
            value=sxglobals.settings.tools['comboOffset'],
            ann='Shrinks the mesh to avoid proximity artifacts.',
            precision=3,
            minValue=0.0,
            maxValue=10.0,
            changeCommand=(
                "sxtools.sxglobals.settings.tools['comboOffset'] = ("
                "maya.cmds.floatField('comboOffset', query=True, value=True))"
            ))

        maya.cmds.text('biasLabel', label='Ray Source Offset:')
        maya.cmds.floatField(
            'bias',
            value=sxglobals.settings.tools['bias'],
            ann=(
                'Offsets the ray starting point from the mesh surface '
                'to avoid self-collision.'),
            precision=6,
            minValue=0.0,
            maxValue=10.0,
            changeCommand=(
                "sxtools.sxglobals.settings.tools['bias'] = ("
                "maya.cmds.floatField('bias', query=True, value=True))"
            ))

        maya.cmds.rowColumnLayout(
            'occlusionRowColumns',
            parent='occlusionFrame',
            numberOfColumns=4,
            columnWidth=(
                (1, 80),
                (2, 50),
                (3, 50),
                (4, 50)),
            columnAttach=[
                (1, 'left', 0),
                (2, 'left', 0),
                (3, 'left', 0),
                (4, 'left', 0)],
            rowSpacing=(1, 5))

        maya.cmds.text(label=' ')
        maya.cmds.text(label='Enabled ')
        maya.cmds.text(label='Scale')
        maya.cmds.text(label='Offset')

        maya.cmds.text(label='Groundplane:')
        maya.cmds.checkBox(
            'ground',
            label='',
            value=sxglobals.settings.tools['bakeGroundPlane'],
            changeCommand=(
                "sxtools.sxglobals.settings.tools['bakeGroundPlane'] = ("
                "maya.cmds.checkBox('ground', query=True, value=True))"))
        maya.cmds.floatField(
            'groundScale',
            value=sxglobals.settings.tools['bakeGroundScale'],
            precision=1,
            minValue=0.0,
            changeCommand=(
                "sxtools.sxglobals.settings.tools['bakeGroundScale'] = ("
                "maya.cmds.floatField('groundScale', query=True, value=True))"
            ))
        maya.cmds.floatField(
            'groundOffset',
            value=sxglobals.settings.tools['bakeGroundOffset'],
            precision=1,
            minValue=0.0,
            changeCommand=(
                "sxtools.sxglobals.settings.tools['bakeGroundOffset'] = ("
                "maya.cmds.floatField('groundOffset', query=True, value=True))"
            ))

        maya.cmds.rowColumnLayout(
            'occlusionRowColumns2',
            parent='occlusionFrame',
            numberOfColumns=2,
            columnWidth=((1, 130), (2, 110)),
            columnAttach=[(1, 'left', 0), (2, 'left', 0)],
            rowSpacing=(1, 0))

        maya.cmds.text(label='Blend local vs. global')
        maya.cmds.floatSlider(
            'blendSlider',
            step=0.2,
            min=0.0,
            max=1.0,
            width=100,
            value=sxglobals.settings.tools['blendSlider'],
            changeCommand=(
                "sxtools.sxglobals.settings.tools['blendSlider'] = ("
                "maya.cmds.floatSlider("
                "'blendSlider', query=True, value=True))\n"
                "sxtools.sxglobals.tools.blendOcclusion()"
            ))

        sxglobals.tools.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())

        maya.cmds.button(
            label='Bake Occlusion',
            parent='occlusionFrame',
            height=30,
            width=100,
            command=(
                'sxtools.sxglobals.tools.bakeBlendOcclusion()\n'
                'sxtools.sxglobals.settings.savePreferences()'))

        plugList = maya.cmds.pluginInfo(query=True, listPlugins=True)
        if 'Mayatomr' in plugList:
            maya.cmds.button(
                label='Bake Occlusion (Mental Ray)',
                parent='occlusionFrame',
                height=30,
                width=100,
                command='sxtools.sxglobals.tools.bakeBlendOcclusionMR()')

        maya.cmds.setParent('canvas')

    def refreshCategoryMenu(self):
        categoryNameArray = []
        if len(sxglobals.settings.masterPaletteArray) > 0:
            for category in sxglobals.settings.masterPaletteArray:
                categoryNameArray.append(category.keys()[0])
        if categoryNameArray is not None:
            for categoryName in categoryNameArray:
                maya.cmds.menuItem(
                    categoryName+'Option',
                    label=categoryName,
                    parent='masterCategories')
        if sxglobals.settings.tools['categoryPreset'] is not None:
            maya.cmds.optionMenu(
                'masterCategories',
                edit=True,
                select=sxglobals.settings.tools['categoryPreset'])

    def masterPaletteToolUI(self):
        if ((maya.cmds.optionVar(exists='SXToolsPalettesFile')) and
           (len(str(maya.cmds.optionVar(query='SXToolsPalettesFile'))) > 0)):
            sxglobals.settings.loadPalettes()
        maya.cmds.frameLayout(
            'masterPaletteFrame',
            parent='canvas',
            label='Apply Master Palette',
            width=250,
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=sxglobals.settings.frames['masterPaletteCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['masterPaletteCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['masterPaletteCollapse']=False"))

        maya.cmds.frameLayout(
            'paletteCategoryFrame',
            parent='masterPaletteFrame',
            label='Palette List',
            marginWidth=2,
            marginHeight=0,
            collapsable=True,
            collapse=sxglobals.settings.frames['paletteCategoryCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['paletteCategoryCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['paletteCategoryCollapse']=False"))
        if len(sxglobals.settings.masterPaletteArray) > 0:
            for categoryDict in sxglobals.settings.masterPaletteArray:
                if categoryDict.keys()[0]+'Collapse' not in sxglobals.settings.frames:
                    sxglobals.settings.frames[categoryDict.keys()[0]+'Collapse'] = True
                maya.cmds.frameLayout(
                    categoryDict.keys()[0],
                    parent='paletteCategoryFrame',
                    label=categoryDict.keys()[0],
                    marginWidth=0,
                    marginHeight=0,
                    enableBackground=True,
                    backgroundColor=[0.32, 0.32, 0.32],
                    collapsable=True,
                    collapse=(
                        sxglobals.settings.frames[categoryDict.keys()[0]+'Collapse']),
                    collapseCommand=(
                        'sxtools.sxglobals.settings.frames["' +
                        categoryDict.keys()[0]+'"+"Collapse"]=True'),
                    expandCommand=(
                        'sxtools.sxglobals.settings.frames["' +
                        categoryDict.keys()[0]+'"+"Collapse"]=False'))
                if len(categoryDict[categoryDict.keys()[0]]) > 0:
                    for i, (name) in enumerate(
                       categoryDict[categoryDict.keys()[0]].keys()):
                        stripeColor = []
                        if i % 2 == 0:
                            stripeColor = [0.22, 0.22, 0.22]
                        else:
                            stripeColor = [0.24, 0.24, 0.24]
                        maya.cmds.rowColumnLayout(
                            categoryDict.keys()[0]+name,
                            parent=categoryDict.keys()[0],
                            numberOfColumns=3,
                            enableBackground=True,
                            backgroundColor=stripeColor,
                            columnWidth=((1, 90), (2, 90), (3, 40)),
                            columnAttach=[
                                (1, 'both', 0),
                                (2, 'right', 5),
                                (3, 'right', 0)],
                            rowSpacing=(1, 0))
                        maya.cmds.text(
                            label=name,
                            align='right',
                            font='smallPlainLabelFont')
                        maya.cmds.palettePort(
                            categoryDict.keys()[0]+name+'Palette',
                            dimensions=(5, 1),
                            width=80,
                            height=20,
                            actualTotal=5,
                            editable=True,
                            colorEditable=False,
                            changeCommand=(
                                'sxtools.sxglobals.settings.currentColor = '
                                'maya.cmds.palettePort(' +
                                '\"'+categoryDict.keys()[0]+name +
                                'Palette'+'\", query=True, rgb=True)\n'
                                'sxtools.sxglobals.tools.setMasterPalette(' +
                                '\"'+categoryDict.keys()[0] +
                                '\", \"'+name+'\")\n'
                                'sxtools.sxglobals.tools.setPaintColor('
                                'sxtools.sxglobals.settings.currentColor)'))
                        sxglobals.tools.getPalette(
                            categoryDict.keys()[0]+name+'Palette',
                            categoryDict.keys()[0],
                            name)
                        maya.cmds.button(
                            categoryDict.keys()[0]+name+'Button',
                            label='Apply',
                            height=20,
                            ann='Shift-click to delete palette',
                            command=(
                                'sxtools.sxglobals.tools.paletteButtonManager(' +
                                '\"'+categoryDict.keys()[0] +
                                '\", \"'+name+'\")'))

        maya.cmds.frameLayout(
            'createPaletteFrame',
            parent='masterPaletteFrame',
            label='Edit Palettes',
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=sxglobals.settings.frames['newPaletteCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['newPaletteCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['newPaletteCollapse']=False"))

        maya.cmds.rowColumnLayout(
            'masterPaletteRowColumns',
            parent='createPaletteFrame',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'right', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))

        maya.cmds.text(label='Category:')

        maya.cmds.optionMenu(
            'masterCategories',
            parent='masterPaletteRowColumns',
            changeCommand=(
                'sxtools.sxglobals.settings.tools["categoryPreset"]='
                'maya.cmds.optionMenu('
                '"masterCategories", query=True, select=True)'))

        self.refreshCategoryMenu()

        maya.cmds.button(
            'savePaletteCategory',
            label='Save Category',
            width=100,
            ann='Shift-click to delete a category and contained palettes',
            command=(
                'sxtools.sxglobals.tools.saveMasterCategory()'))
        maya.cmds.textField(
            'saveCategoryName',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Category Name')
        maya.cmds.button(
            'saveMasterPalette',
            label='Save Palette',
            ann='The palette is saved under selected category',
            width=100,
            command=(
                'sxtools.sxglobals.tools.saveMasterPalette()\n'
                'sxtools.sxglobals.core.updateSXTools()'))
        maya.cmds.textField(
            'savePaletteName',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Palette Name')
        maya.cmds.text('masterPaletteLabel', label='Palette Colors:')
        maya.cmds.palettePort(
            'masterPalette',
            dimensions=(5, 1),
            width=120,
            height=10,
            actualTotal=5,
            editable=True,
            colorEditable=True,
            changeCommand=(
                "sxtools.sxglobals.tools.storePalette("
                "'masterPalette',"
                "sxtools.sxglobals.settings.paletteDict,"
                "'SXToolsMasterPalette')"),
            colorEdited=(
                "sxtools.sxglobals.tools.storePalette("
                "'masterPalette',"
                "sxtools.sxglobals.settings.paletteDict,"
                "'SXToolsMasterPalette')"))

        sxglobals.tools.getPalette(
            'masterPalette',
            sxglobals.settings.paletteDict,
            'SXToolsMasterPalette')

        maya.cmds.frameLayout(
            'paletteSettingsFrame',
            parent='masterPaletteFrame',
            label='Master Palette Settings',
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=sxglobals.settings.frames['paletteSettingsCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['paletteSettingsCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['paletteSettingsCollapse']=False"))

        if ((maya.cmds.optionVar(exists='SXToolsPalettesFile')) and
           (len(str(maya.cmds.optionVar(query='SXToolsPalettesFile'))) > 0)):
            # sxglobals.settings.loadPalettes()
            maya.cmds.text(
                label='Current palettes location:',
                parent='paletteSettingsFrame')
            maya.cmds.text(
                label=maya.cmds.optionVar(query='SXToolsPalettesFile'),
                parent='paletteSettingsFrame',
                ww=True)
        else:
            maya.cmds.text(
                label='WARNING: Palettes file location not set!',
                parent='paletteSettingsFrame',
                height=20,
                backgroundColor=(0.35, 0.1, 0),
                ww=True)

        maya.cmds.button(
            label='Select Palettes File',
            parent='paletteSettingsFrame',
            statusBarMessage=(
                'Shift-click button to reload palettes from file'),
            command=(
                'sxtools.sxglobals.settings.setPalettesFile()\n'
                'sxtools.sxglobals.core.updateSXTools()'))

        maya.cmds.rowColumnLayout(
            'targetRowColumns',
            parent='paletteSettingsFrame',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))

        maya.cmds.text(label='Color 1 Target(s): ')
        maya.cmds.textField(
            'masterTarget1',
            parent='targetRowColumns',
            text=', '.join(sxglobals.settings.project['paletteTarget1']),
            enterCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget1', query=True, text=True), 1)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget1', query=True, text=True), 1)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer1')
        maya.cmds.text(label='Color 2 Target(s): ')
        maya.cmds.textField(
            'masterTarget2',
            parent='targetRowColumns',
            text=', '.join(sxglobals.settings.project['paletteTarget2']),
            enterCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget2', query=True, text=True), 2)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget2', query=True, text=True), 2)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer2')
        maya.cmds.text(label='Color 3 Target(s): ')
        maya.cmds.textField(
            'masterTarget3',
            parent='targetRowColumns',
            text=', '.join(sxglobals.settings.project['paletteTarget3']),
            enterCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget3', query=True, text=True), 3)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget3', query=True, text=True), 3)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer3')
        maya.cmds.text(label='Color 4 Target(s): ')
        maya.cmds.textField(
            'masterTarget4',
            parent='targetRowColumns',
            text=', '.join(sxglobals.settings.project['paletteTarget4']),
            enterCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget4', query=True, text=True), 4)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget4', query=True, text=True), 4)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer4')
        maya.cmds.text(label='Color 5 Target(s): ')
        maya.cmds.textField(
            'masterTarget5',
            parent='targetRowColumns',
            text=', '.join(sxglobals.settings.project['paletteTarget5']),
            enterCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget5', query=True, text=True), 5)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.sxglobals.tools.checkTarget("
                "maya.cmds.textField("
                "'masterTarget5', query=True, text=True), 5)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer5')
        maya.cmds.setParent('canvas')

    def assignCreaseToolUI(self):
        if maya.cmds.objExists('SXCreaseRamp') is False:
            maya.cmds.createNode('ramp', name='SXCreaseRamp', skipSelect=True)

        maya.cmds.setAttr(
            'SXCreaseRamp.colorEntryList[0].position',
            sxglobals.settings.tools['creaseThresholds'][0])
        maya.cmds.setAttr(
            'SXCreaseRamp.colorEntryList[0].color', 0, 0, 0)
        maya.cmds.setAttr(
            'SXCreaseRamp.colorEntryList[1].position',
            sxglobals.settings.tools['creaseThresholds'][1])
        maya.cmds.setAttr(
            'SXCreaseRamp.colorEntryList[1].color', 0.5, 0.5, 0.5)
        maya.cmds.setAttr(
            'SXCreaseRamp.colorEntryList[2].position',
            sxglobals.settings.tools['creaseThresholds'][2])
        maya.cmds.setAttr(
            'SXCreaseRamp.colorEntryList[2].color', 1, 1, 1)
        maya.cmds.setAttr(
            'SXCreaseRamp.interpolation', 0)

        maya.cmds.frameLayout(
            'creaseFrame',
            parent='canvas',
            label='Assign to Crease Set',
            width=250,
            marginWidth=5,
            marginHeight=2,
            collapsable=True,
            collapse=sxglobals.settings.frames['creaseCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['creaseCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['creaseCollapse']=False"))
        maya.cmds.frameLayout(
            'autoCreaseFrame',
            parent='creaseFrame',
            label='Auto-Select Edges',
            width=240,
            marginWidth=5,
            marginHeight=2,
            collapsable=True,
            collapse=sxglobals.settings.frames['autoCreaseCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['autoCreaseCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['autoCreaseCollapse']=False"))
        maya.cmds.text(
            label=(
                'Drag gray and white colors to adjust creasing thresholds. '
                'Black is concave, white is convex.'),
            ww=True)
        maya.cmds.rampColorPort(
            'sxRampCreaseControl',
            parent='autoCreaseFrame',
            height=90,
            node='SXCreaseRamp')
        maya.cmds.checkBox(
            'convexCheck',
            parent='autoCreaseFrame',
            label='Convex Enabled',
            value=sxglobals.settings.tools['convex'],
            onCommand=('sxtools.sxglobals.settings.tools["convex"] = True'),
            offCommand=('sxtools.sxglobals.settings.tools["convex"] = False'))
        maya.cmds.checkBox(
            'concaveCheck',
            parent='autoCreaseFrame',
            label='Concave Enabled',
            value=sxglobals.settings.tools['concave'],
            onCommand=('sxtools.sxglobals.settings.tools["concave"] = True'),
            offCommand=('sxtools.sxglobals.settings.tools["concave"] = False'))
        maya.cmds.text(label='Min Edge Length:')
        maya.cmds.floatField(
            'minCreaseLength',
            parent='autoCreaseFrame',
            value=sxglobals.settings.tools['minCreaseLength'],
            minValue=0,
            maxValue=100,
            precision=3,
            ann='Edges shorter than this will not be creased.',
            changeCommand=(
                "sxtools.sxglobals.settings.tools['minCreaseLength'] = ("
                "maya.cmds.floatField('minCreaseLength', query=True, value=True))"))
        maya.cmds.button(
            parent='autoCreaseFrame',
            label='Auto-Select Edges',
            height=30,
            width=100,
            command=(
                "sxtools.sxglobals.tools.curvatureSelect("
                "sxtools.sxglobals.settings.shapeArray)"))
        maya.cmds.radioButtonGrp(
            'creaseSets',
            parent='creaseFrame',
            columnWidth4=(50, 50, 50, 50),
            columnAttach4=('left', 'left', 'left', 'left'),
            labelArray4=['25%', '50%', '75%', 'Hard'],
            numberOfRadioButtons=4,
            onCommand1="sxtools.sxglobals.tools.assignToCreaseSet('sxCrease1')",
            onCommand2="sxtools.sxglobals.tools.assignToCreaseSet('sxCrease2')",
            onCommand3="sxtools.sxglobals.tools.assignToCreaseSet('sxCrease3')",
            onCommand4="sxtools.sxglobals.tools.assignToCreaseSet('sxCrease4')")
        maya.cmds.setParent('creaseFrame')
        maya.cmds.button(
            label='Uncrease Selection',
            parent='creaseFrame',
            height=30,
            width=100,
            command=("sxtools.sxglobals.tools.assignToCreaseSet('sxCrease0')"))
        maya.cmds.setParent('canvas')

    def swapLayerSetsUI(self):
        maya.cmds.frameLayout(
            'swapLayerSetsFrame',
            parent='canvas',
            label='Manage Layer Sets',
            width=250,
            marginWidth=5,
            marginHeight=2,
            collapsable=True,
            collapse=sxglobals.settings.frames['swapLayerSetsCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['swapLayerSetsCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['swapLayerSetsCollapse']=False"))
        setNums = []
        for object in sxglobals.settings.objectArray:
            setNums.append(int(maya.cmds.getAttr(object + '.numLayerSets')))
        if all(num == setNums[0] for num in setNums):
            maya.cmds.button(
                label='Add New Layer Set',
                parent='swapLayerSetsFrame',
                height=30,
                width=100,
                command=(
                    'sxtools.sxglobals.layers.addLayerSet('
                    'sxtools.sxglobals.settings.objectArray,'
                    'sxtools.sxglobals.layers.getLayerSet('
                    'sxtools.sxglobals.settings.objectArray[0]))\n'
                    'sxtools.sxglobals.core.updateSXTools()'))
            if sxglobals.layers.getLayerSet(sxglobals.settings.objectArray[0]) > 0:
                maya.cmds.button(
                    label='Delete Current Layer Set',
                    parent='swapLayerSetsFrame',
                    height=30,
                    width=100,
                    ann=(
                        'Shift-click to remove all '
                        'other Layer Sets'),
                    command=(
                        'sxtools.sxglobals.tools.removeLayerSet('
                        'sxtools.sxglobals.settings.objectArray)\n'
                        'sxtools.sxglobals.core.updateSXTools()'))
                maya.cmds.text(
                    'layerSetLabel',
                    label=(
                        'Current Layer Set: ' +
                        str(int(maya.cmds.getAttr(
                            str(sxglobals.settings.shapeArray[0]) +
                            '.activeLayerSet'))+1) + '/' +
                        str(sxglobals.layers.getLayerSet(
                            sxglobals.settings.shapeArray[0])+1)))
                maya.cmds.intSliderGrp(
                    'layerSetSlider',
                    field=True,
                    label='Layer Set',
                    adjustableColumn=1,
                    columnWidth=((2, 40), (3, 120)),
                    columnAttach=[
                        (1, 'both', 5),
                        (2, 'both', 5),
                        (3, 'both', 0)],
                    minValue=1,
                    maxValue=(
                        sxglobals.layers.getLayerSet(
                            sxglobals.settings.shapeArray[0])+1),
                    fieldMinValue=0,
                    fieldMaxValue=(
                        sxglobals.layers.getLayerSet(
                            sxglobals.settings.shapeArray[0])+1),
                    value=(
                        maya.cmds.getAttr(
                            str(sxglobals.settings.shapeArray[0]) +
                            '.activeLayerSet')+1),
                    changeCommand=(
                        'sxtools.sxglobals.tools.swapLayerSets('
                        'sxtools.sxglobals.settings.objectArray,'
                        'maya.cmds.intSliderGrp('
                        '"layerSetSlider", query=True, value=True), True)\n'
                        'maya.cmds.text("layerSetLabel",'
                        'edit=True,'
                        'label=("Current Layer Set: "'
                        '+str(int(maya.cmds.getAttr('
                        'str(sxtools.sxglobals.settings.shapeArray[0])'
                        '+".activeLayerSet"))+1))'
                        '+"/"+str(sxtools.sxglobals.layers.getLayerSet('
                        'sxtools.sxglobals.settings.shapeArray['
                        'len(sxtools.sxglobals.settings.shapeArray)-1])+1))'))
        else:
            maya.cmds.text(
                'mismatchLayerSetLabel',
                label=(
                    '\nObjects with mismatching\nLayer Sets selected!')
            )
        maya.cmds.setParent('canvas')

    # TODO: create visibility management buttons,
    # assign joints to skinMeshLayer
    def createSkinMeshUI(self):
        maya.cmds.frameLayout(
            'skinMeshFrame',
            parent='canvas',
            label='Create Skinning Mesh',
            width=250,
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=sxglobals.settings.frames['skinMeshCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['skinMeshCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['skinMeshCollapse']=False"))

        if maya.cmds.objExists(str(sxglobals.settings.objectArray[0]).split('|')[-1].split('_var')[0] + '_skinned'):
            maya.cmds.text(
                parent='skinMeshFrame',
                label=(
                    'Skinning Mesh already exists for ' +
                    str(sxglobals.settings.objectArray[0]).split('|')[-1]),
                ww=True)
        else:
            maya.cmds.button(
                label='Create Skinning Mesh',
                parent='skinMeshFrame',
                height=30,
                command=(
                    'sxtools.sxglobals.tools.createSkinMesh('
                    'sxtools.sxglobals.settings.objectArray)'))
        maya.cmds.setParent('canvas')

    def exportFlagsUI(self):
        maya.cmds.frameLayout(
            'exportFlagsFrame',
            parent='canvas',
            label='Export Flags',
            width=250,
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=sxglobals.settings.frames['exportFlagsCollapse'],
            collapseCommand=(
                "sxtools.sxglobals.settings.frames['exportFlagsCollapse']=True"),
            expandCommand=(
                "sxtools.sxglobals.settings.frames['exportFlagsCollapse']=False"))
        maya.cmds.rowColumnLayout(
            'exportFlagsRowColumns',
            parent='exportFlagsFrame',
            numberOfColumns=2,
            columnWidth=((1, 140), (2, 100)),
            columnAttach=[(1, 'right', 0), (2, 'both', 5)],
            rowSpacing=(1, 0))
        maya.cmds.text('staticPaletteLabel', label='Static Vertex Colors:')
        maya.cmds.checkBox(
            'staticPaletteCheckbox',
            label='',
            ann=(
                'If enabled, the object vertex colors '
                'remain exactly as applied in Maya.'),
            value=(
                maya.cmds.getAttr(
                    sxglobals.settings.objectArray[0]+'.staticVertexColors')),
            onCommand=(
                'sxtools.sxglobals.tools.setExportFlags('
                'sxtools.sxglobals.settings.objectArray, True)'),
            offCommand=(
                'sxtools.sxglobals.tools.setExportFlags('
                'sxtools.sxglobals.settings.objectArray, False)'))
        maya.cmds.text(
            'smoothStepsLabel',
            label='Export Subdivision Level:')
        maya.cmds.intField(
            'smoothSteps',
            min=0,
            max=5,
            step=1,
            value=(
                maya.cmds.getAttr(
                    str(sxglobals.settings.objectArray[0]) +
                    '.subdivisionLevel')),
            changeCommand=(
                'sxtools.sxglobals.tools.setSubdivisionFlag('
                'sxtools.sxglobals.settings.objectArray,'
                'maya.cmds.intField("smoothSteps",'
                ' query=True, value=True))'))
        maya.cmds.setParent('exportFlagsFrame')
        maya.cmds.setParent('canvas')

    def exportButtonUI(self):
        maya.cmds.text(label=' ', parent='canvas')
        maya.cmds.button(
            label='Create Export Objects',
            parent='canvas',
            width=250,
            command=(
                "sxtools.sxglobals.tools.setShadingMode(0)\n"
                "maya.cmds.polyOptions(activeObjects=True,"
                "colorMaterialChannel='ambientDiffuse',"
                "colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayLight;')\n"
                "sxtools.sxglobals.export.processObjects("
                "sxtools.sxglobals.settings.selectionArray)"))
        maya.cmds.setParent('canvas')
