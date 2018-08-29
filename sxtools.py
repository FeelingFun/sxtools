# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2018  Jani Kahrama / Secret Exit Ltd
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
#   Technical notes:
#   updateSXTools()       - the main function called by a scriptJob
#                           monitoring selection changes
#   createSXShader()      - creates the necessary materials to view
#                           the color-layered object. Separate
#                           functions for export preview.
#   setPreferences()      - called to set and store the color sets
#                           needed for the project, writes the defaults
#                           to settings dictionary
#   setPrimVars()         - sets the object-specific primitive
#                           variables used for shading and exporting
#   layerToUV()           - performs the conversion of color set
#                           alpha values to "color masks" stored
#                           in mesh UV values
#   colorToUV()           - stores material properties to UV channels,
#                           note that "emission" is exported as
#                           a single-channel value
#   processObjects()      - the main export function, goes through
#                           the steps of calling the other functions
#
# ----------------------------------------------------------------------------

import maya.api.OpenMaya as OM
import maya.cmds
import maya.mel
import math
import random
from sfx import SFXNetwork
from sfx import StingrayPBSNetwork
import sfx.sfxnodes as sfxnodes
import sfx.pbsnodes as pbsnodes

dockID = 'SXTools'
settings = None
setup = None
export = None
tools = None
layers = None
ui = None
sx = None


class Settings(object):
    def __init__(self):
        self.selectionArray = []
        self.objectArray = []
        self.shapeArray = []
        self.componentArray = []
        self.patchArray = []
        self.bakeSet = []
        self.currentColor = (1, 1, 1)
        self.layerAlphaMax = 0
        self.material = None
        self.nodeDict = {}
        self.exportNodeDict = {}
        self.paletteDict = {}
        self.masterPaletteDict = {}
        self.projectSettings = {}
        self.localOcclusionDict = {}
        self.globalOcclusionDict = {}
        self.frameStates = {
            'setupFrameCollapse': False,
            'toolFrameCollapse': False,
            'occlusionFrameCollapse': True,
            'masterPaletteFrameCollapse': True,
            'creaseFrameCollapse': True,
            'noiseFrameCollapse': True,
            'applyColorFrameCollapse': True,
            'swapLayerFrameCollapse': True,
            'gradientFrameCollapse': True,
            'copyLayerFrameCollapse': True,
            'swapLayerSetsFrameCollapse': True
        }
        self.toolStates = {
            'recentPaletteIndex': 1,
            'overwriteAlpha': False,
            'noiseMonochrome': False,
            'noiseValue': 0.500,
            'bakeGroundPlane': True,
            'bakeGroundScale': 100.0,
            'bakeGroundOffset': 1.0,
            'bakeTogether': False,
            'blendSlider': 0.0,
            'paletteTarget1': ['layer1', ],
            'paletteTarget2': ['layer2', ],
            'paletteTarget3': ['layer3', ],
            'paletteTarget4': ['layer4', ],
            'paletteTarget5': ['layer5', ]
        }
        self.refArray = [
            u'layer1', u'layer2', u'layer3', u'layer4', u'layer5', u'layer6', u'layer7',
            u'layer8', u'layer9', u'layer10', u'occlusion', u'specular',
            u'transmission', u'emission'
        ]

    def setPreferences(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        # default values, if the user decides to reset the tool
        if shift is True:
            self.projectSettings['SXToolsAlphaTolerance'] = 1.0
            self.projectSettings['SXToolsSmoothExport'] = 0
            self.projectSettings['SXToolsExportOffset'] = 5
            self.projectSettings['SXToolsLayerCount'] = 10
            self.projectSettings['SXToolsChannelCount'] = 4
            self.projectSettings['SXToolsOverlays'] = ('layer9', 'layer10') 

            self.projectSettings['SXToolsRefLayers'] = {
                u'layer1': (0.5, 0.5, 0.5, 1),
                u'layer2': (0, 0, 0, 0),
                u'layer3': (0, 0, 0, 0),
                u'layer4': (0, 0, 0, 0),
                u'layer5': (0, 0, 0, 0),
                u'layer6': (0, 0, 0, 0),
                u'layer7': (0, 0, 0, 0),
                u'layer8': (0, 0, 0, 0),
                u'layer9': (0, 0, 0, 0),
                u'layer10': (0, 0, 0, 0),
                u'occlusion': (1, 1, 1, 1),
                u'specular': (0, 0, 0, 1),
                u'transmission': (0, 0, 0, 1),
                u'emission': (0, 0, 0, 1)
            }

            self.projectSettings['SXToolsRefIndices'] = {
                u'layer1': 1,
                u'layer2': 2,
                u'layer3': 3,
                u'layer4': 4,
                u'layer5': 5,
                u'layer6': 6,
                u'layer7': 7,
                u'layer8': 8,
                u'layer9': 9,
                u'layer10': 10,
                u'occlusion': 11,
                u'specular': 12,
                u'transmission': 13,
                u'emission': 14
            }

            self.projectSettings['SXToolsRefNames'] = {
                1: u'layer1',
                2: u'layer2',
                3: u'layer3',
                4: u'layer4',
                5: u'layer5',
                6: u'layer6',
                7: u'layer7',
                8: u'layer8',
                9: u'layer9',
                10: u'layer10',
                11: u'occlusion',
                12: u'specular',
                13: u'transmission',
                14: u'emission'
            }

            self.projectSettings['SXToolsMatChannels'] = (1, 1, 1, 1)
            self.projectSettings['SXToolsExportChannels'] = ('U3', 'U1', 'V1', 'U2', 'V2')
            self.projectSettings['SXToolsOverlaysExportChannels'] = (('UV4', 'UV5'), ('UV6', 'UV7'))
            self.projectSettings['SXToolsExportSuffix'] = True

        self.savePreferences()

        if shift is True:
            setup.createSXShader(self.projectSettings['SXToolsLayerCount'],
                                                        True, True, True, True)
        elif shift is False:
            setup.createSXShader(self.projectSettings['SXToolsLayerCount'],
                                                        self.projectSettings['SXToolsMatChannels'][0],
                                                        self.projectSettings['SXToolsMatChannels'][1],
                                                        self.projectSettings['SXToolsMatChannels'][2],
                                                        self.projectSettings['SXToolsMatChannels'][3])
        setup.createSXExportShader()
        setup.createSXPBShader()

        # Viewport and Maya prefs
        maya.cmds.colorManagementPrefs(edit=True, cmEnabled=0)
        maya.cmds.setAttr('hardwareRenderingGlobals.transparencyAlgorithm', 3)
        maya.cmds.setAttr('hardwareRenderingGlobals.lineAAEnable', 1)
        maya.cmds.setAttr('hardwareRenderingGlobals.multiSampleEnable', 1)
        maya.cmds.setAttr('hardwareRenderingGlobals.floatingPointRTEnable', 1)

        maya.cmds.select(clear=True)

    def updatePreferences(self):
        self.projectSettings['SXToolsAlphaTolerance'] = maya.cmds.floatField(
            'exportTolerance', query=True, value=True)
        self.projectSettings['SXToolsSmoothExport'] = maya.cmds.intField(
            'exportSmooth', query=True, value=True)
        self.projectSettings['SXToolsExportOffset'] = maya.cmds.intField(
            'exportOffset', query=True, value=True)
        self.projectSettings['SXToolsLayerCount'] = maya.cmds.intField(
            'layerCount', query=True, value=True)
        self.projectSettings['SXToolsMatChannels'] = (
            int(maya.cmds.checkBox('occlusion', query=True, value=True)),
            int(maya.cmds.checkBox('specular', query=True, value=True)),
            int(maya.cmds.checkBox('transmission', query=True, value=True)),
            int(maya.cmds.checkBox('emission', query=True, value=True)))
        self.projectSettings['SXToolsOverlays'] = (
            maya.cmds.textField('overlay1', query=True, text=True),
            maya.cmds.textField('overlay2', query=True, text=True))
        self.projectSettings['SXToolsExportChannels'] = (
            maya.cmds.textField('maskExport', query=True, text=True),
            maya.cmds.textField('occlusionExport', query=True, text=True),
            maya.cmds.textField('specularExport', query=True, text=True),
            maya.cmds.textField('transmissionExport', query=True, text=True),
            maya.cmds.textField('emissionExport', query=True, text=True))
        self.projectSettings['SXToolsOverlaysExportChannels'] = (
            str(maya.cmds.textField('overlay1Export', query=True, text=True)).split(','),
            str(maya.cmds.textField('overlay2Export', query=True, text=True)).split(','))
        self.projectSettings['SXToolsRefLayers'] = {}
        self.projectSettings['SXToolsRefIndices'] = {}
        self.projectSettings['SXToolsRefNames'] = {}
        self.projectSettings['SXToolsExportSuffix'] = maya.cmds.checkBox('suffixCheck', query=True, value=True)

        refIndex = 0
        for k in range(0, self.projectSettings['SXToolsLayerCount']):
            refIndex += 1
            layerName = 'layer' + str(k + 1)

            if k == 0:
                self.projectSettings['SXToolsRefLayers'][layerName] = (0.5, 0.5, 0.5, 1)
            else:
                self.projectSettings['SXToolsRefLayers'][layerName] = (0, 0, 0, 0)

            self.projectSettings['SXToolsRefIndices'][layerName] = refIndex
            self.projectSettings['SXToolsRefNames'][refIndex] = layerName

        channels = [u'occlusion', u'specular', u'transmission', u'emission']
        for channel in channels:
            if maya.cmds.checkBox(channel, query=True, value=True):
                refIndex += 1
                if channel == 'occlusion':
                    self.projectSettings['SXToolsRefLayers'][channel] = (1, 1, 1, 1)
                else:
                    self.projectSettings['SXToolsRefLayers'][channel] = (0, 0, 0, 1)

                self.projectSettings['SXToolsRefIndices'][channel] = refIndex
                self.projectSettings['SXToolsRefNames'][refIndex] = channel

        self.projectSettings[
            'SXToolsChannelCount'] = refIndex - self.projectSettings['SXToolsLayerCount']

    def setPreferencesFile(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)
        if shift is False:
            filePath = maya.cmds.fileDialog2(
                fileFilter='*.txt',
                cap='Select SX Tools Settings File',
                dialogStyle=2,
                fm=0)
            if filePath is not None:
                maya.cmds.optionVar(stringValue=('SXToolsPrefsFile', filePath[0]))
            else:
                print('SX Tools: No Settings file selected')
        else:
            self.loadPreferences()

    def savePreferences(self):
        if maya.cmds.optionVar(exists='SXToolsPrefsFile'):
            filePath = maya.cmds.optionVar(q='SXToolsPrefsFile')
            with open(filePath, 'w') as output:
                output.write('SX Tools Project Settings: \r\n' + str(self.projectSettings) + '\r\n')
                output.write('SX Tools Master Palette Dictionary: \r\n' + str(self.masterPaletteDict) + '\r\n')
                output.close()
            print('SX Tools: Preferences saved')
        else:
            print('SX Tools Warning: Preferences file location not set!')

    def loadPreferences(self):
        if maya.cmds.optionVar(exists='SXToolsPrefsFile'):
            filePath = maya.cmds.optionVar(q='SXToolsPrefsFile')
            with open(filePath, 'r') as input:
                prefData = input.readlines()
                self.projectSettings = eval(prefData[1])
                self.masterPaletteDict = eval(prefData[3])
                input.close()

            print('SX Tools: Preferences loaded from ' + filePath)
            self.setPreferences()
            self.frameStates['setupFrameCollapse'] = True
        else:
            print('SX Tools: No preferences found')


class SceneSetup(object):
    def __init__(self):
        return None

    def createSXShader(self, numLayers, occlusion=False, specular=False,
                                            transmission=False, emission=False):
        if maya.cmds.objExists('SXShader'):
            shadingGroup = maya.cmds.listConnections('SXShader', type='shadingEngine')
            componentsWithMaterial = maya.cmds.sets(shadingGroup, q=True)
            maya.cmds.delete('SXShader')
            print('SX Tools: Updating default materials')
        if maya.cmds.objExists('SXShaderSG'):
            maya.cmds.delete('SXShaderSG')

        else:
            print('SX Tools: Creating default materials')

        materialName = 'SXShader'
        settings.material = SFXNetwork.create(materialName)
        channels = []

        if occlusion:
            channels.append('occlusion')
        if specular:
            channels.append('specular')
        if transmission:
            channels.append('transmission')
        if emission:
            channels.append('emission')

        #
        # Create common nodes
        #

        mode_node = settings.material.add(sfxnodes.PrimitiveVariable)
        mode_node.name = 'shadingMode'
        mode_node.primvariableName = 'shadingMode'
        mode_node.posx = -3250
        mode_node.posy = 0

        transparency_node = settings.material.add(sfxnodes.PrimitiveVariable)
        transparency_node.name = 'transparency'
        transparency_node.primvariableName = 'transparency'
        transparency_node.posx = -3500
        transparency_node.posy = 0

        transparencyCast_node = settings.material.add(sfxnodes.FloatToBool)
        transparencyCast_node.name = 'visCast'
        transparencyCast_node.posx = -3500
        transparencyCast_node.posy = 250

        bcol_node = settings.material.add(sfxnodes.Color)
        bcol_node.name = 'black'
        bcol_node.color = (0, 0, 0, 1)
        bcol_node.posx = -2500
        bcol_node.posy = -250
        bcolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='black')

        wcol_node = settings.material.add(sfxnodes.Color)
        wcol_node.name = 'white'
        wcol_node.color = (1, 1, 1, 1)
        wcol_node.posx = -2500
        wcol_node.posy = -500
        wcolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='white')

        alphaValue_node = settings.material.add(sfxnodes.Float)
        alphaValue_node.name = 'TestValue0'
        alphaValue_node.posx = -1500
        alphaValue_node.posy = 750
        alphaValue_node.value = 0

        addValue_node = settings.material.add(sfxnodes.Float)
        addValue_node.name = 'TestValue1'
        addValue_node.posx = -1500
        addValue_node.posy = 1000
        addValue_node.value = 1

        mulValue_node = settings.material.add(sfxnodes.Float)
        mulValue_node.name = 'TestValue2'
        mulValue_node.posx = -1500
        mulValue_node.posy = 1250
        mulValue_node.value = 2

        alphaTest_node = settings.material.add(sfxnodes.Comparison)
        alphaTest_node.name = 'alphaTest'
        alphaTest_node.posx = -1250
        alphaTest_node.posy = 750

        addTest_node = settings.material.add(sfxnodes.Comparison)
        addTest_node.name = 'addTest'
        addTest_node.posx = -1250
        addTest_node.posy = 1000

        mulTest_node = settings.material.add(sfxnodes.Comparison)
        mulTest_node.name = 'mulTest'
        mulTest_node.posx = -1250
        mulTest_node.posy = 1250

        alphaIf_node = settings.material.add(sfxnodes.IfElseBasic)
        alphaIf_node.name = 'alphaIf'
        alphaIf_node.posx = -1000
        alphaIf_node.posy = 750

        addIf_node = settings.material.add(sfxnodes.IfElseBasic)
        addIf_node.name = 'addIf'
        addIf_node.posx = -1000
        addIf_node.posy = 1000

        mulIf_node = settings.material.add(sfxnodes.IfElseBasic)
        mulIf_node.name = 'mulIf'
        mulIf_node.posx = -1000
        mulIf_node.posy = 1250

        finalTest_node = settings.material.add(sfxnodes.Comparison)
        finalTest_node.name = 'finalTest'
        finalTest_node.posx = -1250
        finalTest_node.posy = 1500

        debugTest_node = settings.material.add(sfxnodes.Comparison)
        debugTest_node.name = 'debugTest'
        debugTest_node.posx = -1250
        debugTest_node.posy = 1750

        grayTest_node = settings.material.add(sfxnodes.Comparison)
        grayTest_node.name = 'grayTest'
        grayTest_node.posx = -1250
        grayTest_node.posy = 2000

        visTest_node = settings.material.add(sfxnodes.FloatToBool)
        visTest_node.name = 'visCast'
        visTest_node.posx = -2250
        visTest_node.posy = 1250

        finalIf_node = settings.material.add(sfxnodes.IfElseBasic)
        finalIf_node.name = 'finalIf'
        finalIf_node.posx = -1000
        finalIf_node.posy = 1500

        debugIf_node = settings.material.add(sfxnodes.IfElseBasic)
        debugIf_node.name = 'debugIf'
        debugIf_node.posx = -1000
        debugIf_node.posy = 1750

        grayIf_node = settings.material.add(sfxnodes.IfElseBasic)
        grayIf_node.name = 'grayIf'
        grayIf_node.posx = -2000
        grayIf_node.posy = 750

        layerComp_node = settings.material.add(sfxnodes.Add)
        layerComp_node.name = 'layerComp'
        layerComp_node.posx = -1000
        layerComp_node.posy = 0
        layerComp_node.supportmulticonnections = True
        layerCompID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='layerComp')

        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='TraditionalGameSurfaceShader')
        settings.nodeDict['SXShader'] = shaderID

        rgbPathName = 'rgbPath'
        rgbPath_node = settings.material.add(sfxnodes.PathDirectionList)
        rgbPath_node.posx = -2250
        rgbPath_node.posy = 0
        rgbPath_node.name = rgbPathName
        rgbPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=rgbPathName)

        alphaPathName = 'alphaPath'
        alphaPath_node = settings.material.add(sfxnodes.PathDirectionList)
        alphaPath_node.posx = -2250
        alphaPath_node.posy = 250
        alphaPath_node.name = alphaPathName
        alphaPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=alphaPathName)

        vectconstName = 'alphaComp'
        vectconst_node = settings.material.add(sfxnodes.VectorConstruct)
        vectconst_node.posx = -2250
        vectconst_node.posy = 500
        vectconst_node.name = vectconstName
        vectconstID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=vectconstName)

        ifMaskName = 'ifMask'
        ifMask_node = settings.material.add(sfxnodes.IfElseBasic)
        ifMask_node.posx = -1750
        ifMask_node.posy = 500
        ifMask_node.name = ifMaskName
        ifMaskID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=ifMaskName)

        premulName = 'preMul'
        premul_node = settings.material.add(sfxnodes.Multiply)
        premul_node.posx = -1500
        premul_node.posy = 250
        premul_node.name = premulName
        premulID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=premulName)

        invOneName = 'invOne'
        invOne_node = settings.material.add(sfxnodes.InvertOneMinus)
        invOne_node.posx = -1750
        invOne_node.posy = 250
        invOne_node.name = invOneName
        invOneID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=invOneName)

        wlerpName = 'wLerp'
        wlerp_node = settings.material.add(sfxnodes.LinearInterpolateMix)
        wlerp_node.posx = -1500
        wlerp_node.posy = 0
        wlerp_node.name = wlerpName
        wlerpID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=wlerpName)

        lerpName = 'alphaLayer'
        lerp_node = settings.material.add(sfxnodes.LinearInterpolateMix)
        lerp_node.posx = -1250
        lerp_node.posy = 500
        lerp_node.name = lerpName
        lerpID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=lerpName)

        addName = 'addLayer'
        add_node = settings.material.add(sfxnodes.Add)
        add_node.posx = -1250
        add_node.posy = 250
        add_node.name = addName
        addID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=addName)

        mulName = 'mulLayer'
        mul_node = settings.material.add(sfxnodes.Multiply)
        mul_node.posx = -1250
        mul_node.posy = 0
        mul_node.name = mulName
        mulID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=mulName)

        blendModePathName = 'blendModePath'
        blendModePath_node = settings.material.add(sfxnodes.PathDirectionList)
        blendModePath_node.posx = -2250
        blendModePath_node.posy = 750
        blendModePath_node.name = blendModePathName
        blendModePathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=blendModePathName)

        visPathName = 'visPath'
        visPath_node = settings.material.add(sfxnodes.IfElseBasic)
        visPath_node.posx = -750
        visPath_node.posy = 0
        visPath_node.name = visPathName
        visPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=visPathName)

        visModePathName = 'visModePath'
        visModePath_node = settings.material.add(sfxnodes.PathDirectionList)
        visModePath_node.posx = -2250
        visModePath_node.posy = 1000
        visModePath_node.name = visModePathName
        visModePathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=visModePathName)

        repeatName = 'repeatLoop'
        repeat_node = settings.material.add(sfxnodes.RepeatLoop)
        repeat_node.posx = -750
        repeat_node.posy = -250
        repeat_node.name = repeatName
        repeatID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=repeatName)

        repeatAlphaName = 'repeatAlphaLoop'
        repeatAlpha_node = settings.material.add(sfxnodes.RepeatLoop)
        repeatAlpha_node.posx = -750
        repeatAlpha_node.posy = 250
        repeatAlpha_node.name = repeatAlphaName
        repeatAlphaID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=repeatAlphaName)

        alphaAdd_node = settings.material.add(sfxnodes.Add)
        alphaAdd_node.name = 'alphaAdd'
        alphaAdd_node.posx = -1000
        alphaAdd_node.posy = 250
        alphaAddID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='alphaAdd')

        alphaVar_node = settings.material.add(sfxnodes.Float)
        alphaVar_node.name = 'alphaVar'
        alphaVar_node.value = 0
        alphaVar_node.posx = -1000
        alphaVar_node.posy = 500
        alphaVarID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='alphaVar')

        indexName = 'layerIndex'
        index_node = settings.material.add(sfxnodes.IntValue)
        index_node.posx = -1000
        index_node.posy = -250
        index_node.name = indexName
        indexID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=indexName)

        countName = 'layerCount'
        count_node = settings.material.add(sfxnodes.IntValue)
        count_node.posx = -1250
        count_node.posy = -250
        count_node.name = countName
        count_node.value = settings.projectSettings['SXToolsLayerCount']
        countID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=countName)

        outputName = 'outputVar'
        output_node = settings.material.add(sfxnodes.Float3)
        output_node.posx = -1500
        output_node.posy = -250
        output_node.valueX = 0
        output_node.valueY = 0
        output_node.valueZ = 0
        output_node.name = outputName
        outputID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=outputName)

        diffCompName = 'diffuseComp'
        diffComp_node = settings.material.add(sfxnodes.IfElseBasic)
        diffComp_node.posx = -500
        diffComp_node.posy = 0
        diffComp_node.name = diffCompName
        diffComp_nodeID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=diffCompName)

        transCompName = 'transparencyComp'
        transComp_node = settings.material.add(sfxnodes.IfElseBasic)
        transComp_node.posx = -500
        transComp_node.posy = 250
        transComp_node.name = transCompName
        transCompID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=transCompName)
        settings.nodeDict[transCompName] = transCompID

        #
        # Create requested number of layer-specific nodes
        #

        for k in range(0, numLayers):
            offset = k * 250
            layerName = 'layer' + str(k + 1)
            vertcol_node = settings.material.add(sfxnodes.VertexColor)
            vertcol_node.posx = -2500
            vertcol_node.posy = 0 + offset
            vertcol_node.name = layerName
            vertcol_node.colorsetname_Vertex = layerName
            vertcolID = maya.cmds.shaderfx(
                sfxnode=materialName, getNodeIDByName=layerName)
            settings.nodeDict[layerName] = vertcolID

            boolName = layerName + 'Visibility'
            bool_node = settings.material.add(sfxnodes.PrimitiveVariable)
            bool_node.posx = -2750
            bool_node.posy = 0 + offset
            bool_node.name = boolName
            bool_node.primvariableName = boolName
            boolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=boolName)
            settings.nodeDict[boolName] = boolID

            blendName = layerName + 'BlendMode'
            blendMode_node = settings.material.add(sfxnodes.PrimitiveVariable)
            blendMode_node.posx = -3000
            blendMode_node.posy = 0 + offset
            blendMode_node.name = blendName
            blendMode_node.primvariableName = blendName
            blendModeID = maya.cmds.shaderfx(
                sfxnode=materialName, getNodeIDByName=blendName)
            settings.nodeDict[blendName] = blendModeID

            # Create connections
            settings.material.connect(vertcol_node.outputs.rgb, (rgbPathID, 0))
            settings.material.connect(vertcol_node.outputs.alpha, (alphaPathID, 0))
            settings.material.connect(bool_node.outputs.value,
                                    visModePath_node.inputs.options)
            settings.material.connect(blendMode_node.outputs.value,
                                    blendModePath_node.inputs.options)

        settings.material.connect(mode_node.outputs.value, finalTest_node.inputs.a)
        settings.material.connect(mode_node.outputs.value, debugTest_node.inputs.a)
        settings.material.connect(mode_node.outputs.value, grayTest_node.inputs.a)

        settings.material.connect(transparency_node.outputs.value,
                                    transparencyCast_node.inputs.value)
        settings.material.connect(transparencyCast_node.outputs.result,
                                    transComp_node.inputs.condition)

        settings.material.connect(alphaValue_node.outputs.float,
                                    finalTest_node.inputs.b)
        settings.material.connect(addValue_node.outputs.float,
                                    debugTest_node.inputs.b)
        settings.material.connect(mulValue_node.outputs.float,
                                    grayTest_node.inputs.b)

        settings.material.connect(alphaPath_node.outputs.result,
                                    vectconst_node.inputs.x)
        settings.material.connect(alphaPath_node.outputs.result,
                                    vectconst_node.inputs.y)
        settings.material.connect(alphaPath_node.outputs.result,
                                    vectconst_node.inputs.z)

        settings.material.connect(rgbPath_node.outputs.result, (premulID, 0))
        settings.material.connect((vectconstID, 1), (premulID, 1))
        settings.material.connect((vectconstID, 1), invOne_node.inputs.value)

        settings.material.connect(rgbPath_node.outputs.result, (wlerpID, 0))
        settings.material.connect(wcol_node.outputs.rgb, (wlerpID, 1))
        settings.material.connect(invOne_node.outputs.result, wlerp_node.inputs.mix)

        settings.material.connect(vectconst_node.outputs.float3,
                                    ifMask_node.inputs.true)
        settings.material.connect(rgbPath_node.outputs.result,
                                    ifMask_node.inputs.false)
        settings.material.connect(grayTest_node.outputs.result,
                                    ifMask_node.inputs.condition)
        settings.material.connect((ifMaskID, 0), (lerpID, 1))

        settings.material.connect(premul_node.outputs.result, (addID, 1))
        settings.material.connect(wlerp_node.outputs.result, (mulID, 1))

        settings.material.connect(alphaPath_node.outputs.result,
                                    lerp_node.inputs.mix)

        settings.material.connect(output_node.outputs.float3, (lerpID, 0))
        settings.material.connect(output_node.outputs.float3, (addID, 0))
        settings.material.connect(output_node.outputs.float3, (mulID, 0))

        settings.material.connect(count_node.outputs.int, repeat_node.inputs.count)
        settings.material.connect(index_node.outputs.int, repeat_node.inputs.index)
        settings.material.connect(output_node.outputs.float3,
                                    repeat_node.inputs.output)

        settings.material.connect(alphaPath_node.outputs.result, (alphaAddID, 0))
        settings.material.connect(count_node.outputs.int,
                                    repeatAlpha_node.inputs.count)
        settings.material.connect(index_node.outputs.int,
                                    repeatAlpha_node.inputs.index)
        settings.material.connect(alphaVar_node.outputs.float,
                                    repeatAlpha_node.inputs.output)
        settings.material.connect(alphaVar_node.outputs.float, (alphaAddID, 1))

        settings.material.connect(alphaAdd_node.outputs.result,
                                    repeatAlpha_node.inputs.calculation)

        settings.material.connect(index_node.outputs.int, rgbPath_node.inputs.index)
        settings.material.connect(index_node.outputs.int,
                                    alphaPath_node.inputs.index)
        settings.material.connect(index_node.outputs.int,
                                    visModePath_node.inputs.index)
        settings.material.connect(index_node.outputs.int,
                                    blendModePath_node.inputs.index)

        settings.material.connect(blendModePath_node.outputs.result,
                                    grayIf_node.inputs.false)

        settings.material.connect(alphaValue_node.outputs.float,
                                    alphaTest_node.inputs.b)
        settings.material.connect(addValue_node.outputs.float, addTest_node.inputs.b)
        settings.material.connect(mulValue_node.outputs.float, mulTest_node.inputs.b)

        settings.material.connect(bcol_node.outputs.rgb, alphaIf_node.inputs.false)
        settings.material.connect(bcol_node.outputs.rgb, addIf_node.inputs.false)
        settings.material.connect(bcol_node.outputs.rgb, mulIf_node.inputs.false)

        settings.material.connect(lerp_node.outputs.result, alphaIf_node.inputs.true)
        settings.material.connect(add_node.outputs.result, addIf_node.inputs.true)
        settings.material.connect(mul_node.outputs.result, mulIf_node.inputs.true)

        settings.material.connect(grayIf_node.outputs.result,
                                    alphaTest_node.inputs.a)
        settings.material.connect(grayIf_node.outputs.result, addTest_node.inputs.a)
        settings.material.connect(grayIf_node.outputs.result, mulTest_node.inputs.a)

        settings.material.connect(alphaTest_node.outputs.result,
                                    alphaIf_node.inputs.condition)
        settings.material.connect(addTest_node.outputs.result,
                                    addIf_node.inputs.condition)
        settings.material.connect(mulTest_node.outputs.result,
                                    mulIf_node.inputs.condition)

        settings.material.connect(finalTest_node.outputs.result,
                                    finalIf_node.inputs.condition)
        settings.material.connect(debugTest_node.outputs.result,
                                    debugIf_node.inputs.condition)
        settings.material.connect(grayTest_node.outputs.result,
                                    grayIf_node.inputs.condition)

        settings.material.connect(alphaValue_node.outputs.float,
                                    grayIf_node.inputs.true)

        settings.material.connect(alphaIf_node.outputs.result, (layerCompID, 0))
        settings.material.connect(addIf_node.outputs.result, (layerCompID, 1))
        settings.material.connect(mulIf_node.outputs.result, (layerCompID, 1))

        settings.material.connect(layerComp_node.outputs.result,
                                    visPath_node.inputs.true)
        settings.material.connect(output_node.outputs.float3,
                                    visPath_node.inputs.false)
        settings.material.connect(visModePath_node.outputs.result,
                                    visTest_node.inputs.value)
        settings.material.connect(visTest_node.outputs.result,
                                    visPath_node.inputs.condition)

        settings.material.connect(visPath_node.outputs.result,
                                    repeat_node.inputs.calculation)

        #
        # Create material channels
        #

        for channel in channels:
            offset = channels.index(channel) * 500

            chancol_node = settings.material.add(sfxnodes.VertexColor)
            chancol_node.posx = -2000
            chancol_node.posy = -1000 - offset
            chancol_node.name = channel
            chancol_node.colorsetname_Vertex = channel
            chancolID = maya.cmds.shaderfx(
                sfxnode=materialName, getNodeIDByName=channel)
            settings.nodeDict[channel] = chancolID

            chanboolName = channel + 'Visibility'
            chanbool_node = settings.material.add(sfxnodes.PrimitiveVariable)
            chanbool_node.posx = -2000
            chanbool_node.posy = -750 - offset
            chanbool_node.name = chanboolName
            chanbool_node.primvariableName = chanboolName
            chanboolID = maya.cmds.shaderfx(
                sfxnode=materialName, getNodeIDByName=chanboolName)
            settings.nodeDict[chanboolName] = chanboolID

            chanCastName = channel + 'Cast'
            chanCast_node = settings.material.add(sfxnodes.FloatToBool)
            chanCast_node.posx = -1750
            chanCast_node.posy = -750 - offset
            chanCast_node.name = chanCastName
            chanCastID = maya.cmds.shaderfx(
                sfxnode=materialName, getNodeIDByName=chanCastName)
            settings.nodeDict[chanboolName] = chanCastID

            if3_node = settings.material.add(sfxnodes.IfElseBasic)
            if3_node.posx = -1750
            if3_node.posy = -1000 - offset

            if4_node = settings.material.add(sfxnodes.IfElseBasic)
            if4_node.posx = -1500
            if4_node.posy = -1000 - offset
            if4_node.name = channel + 'Comp'

            if channel == 'occlusion':
                settings.material.connect(chancol_node.outputs.red, if3_node.inputs.true)
                settings.material.connect(wcol_node.outputs.red, if3_node.inputs.false)
                settings.material.connect(wcol_node.outputs.red, if4_node.inputs.true)

                occ_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='occlusionComp')
                # Connect occlusion
                settings.material.connect((occ_nodeID, 0), (shaderID, 2))

            elif channel == 'specular':
                specMul_node = settings.material.add(sfxnodes.Multiply)
                specMul_node.posx = -750
                specMul_node.posy = -500
                specMul_node.name = 'specularMultiplier'
                specMul_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='specularMultiplier')

                specPow_node = settings.material.add(sfxnodes.Pow)
                specPow_node.posx = -750
                specPow_node.posy = -750
                specPow_node.name = 'specularPower'
                specPow_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='specularPower')

                smv_node = settings.material.add(sfxnodes.Float)
                smv_node.posx = -1000
                smv_node.posy = -500
                smv_node.name = 'specularMultiplierValue'
                smv_node.value = 0.4
                smv_node.defineinheader = True
                smv_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='specularMultiplierValue')

                spv_node = settings.material.add(sfxnodes.Float)
                spv_node.posx = -1000
                spv_node.posy = -750
                spv_node.name = 'specularPowerValue'
                spv_node.value = 20
                spv_node.defineinheader = True
                spv_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='specularPowerValue')

                spec_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='specularComp')
                settings.material.connect(chancol_node.outputs.rgb, if3_node.inputs.true)
                settings.material.connect(bcol_node.outputs.rgb, if3_node.inputs.false)
                settings.material.connect(bcol_node.outputs.rgb, if4_node.inputs.true)

                # Connect specular multiplier
                settings.material.connect((spec_nodeID, 0), (specMul_nodeID, 0))
                settings.material.connect((smv_nodeID, 0), (specMul_nodeID, 1))

                # Connect specular power
                specRaw_nodeID = settings.nodeDict['specular']
                settings.material.connect(spv_node.outputs.float, specPow_node.inputs.x)
                settings.material.connect(chancol_node.outputs.red, specPow_node.inputs.y)

                # Connect specular
                settings.material.connect((specMul_nodeID, 0), (shaderID, 5))
                # Connect specular power
                settings.material.connect((specPow_nodeID, 0), (shaderID, 4))

            elif channel == 'transmission':
                trans_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='transmissionComp')
                settings.material.connect(chancol_node.outputs.rgb, if3_node.inputs.true)
                settings.material.connect(bcol_node.outputs.rgb, if3_node.inputs.false)
                settings.material.connect(bcol_node.outputs.rgb, if4_node.inputs.true)
                # Connect transmission
                settings.material.connect((trans_nodeID, 0), (shaderID, 9))

            elif channel == 'emission':
                emiss_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName, getNodeIDByName='emissionComp')
                settings.material.connect(chancol_node.outputs.rgb, if3_node.inputs.true)
                settings.material.connect(bcol_node.outputs.rgb, if3_node.inputs.false)
                settings.material.connect(repeat_node.outputs.output, if4_node.inputs.true)
                # Connect emission
                settings.material.connect((emiss_nodeID, 0), (shaderID, 1))

            settings.material.connect(chanbool_node.outputs.value,
                                        chanCast_node.inputs.value)
            settings.material.connect(chanCast_node.outputs.result,
                                        if3_node.inputs.condition)
            settings.material.connect(grayTest_node.outputs.result,
                                        if4_node.inputs.condition)
            settings.material.connect(if3_node.outputs.result, if4_node.inputs.false)

        #
        # Glue it all together
        #

        settings.material.connect(grayTest_node.outputs.result,
                                    diffComp_node.inputs.condition)
        settings.material.connect(repeat_node.outputs.output,
                                    diffComp_node.inputs.false)
        settings.material.connect(repeatAlpha_node.outputs.output,
                                    transComp_node.inputs.true)
        settings.material.connect(addValue_node.outputs.float,
                                    transComp_node.inputs.false)
        settings.material.connect(bcol_node.outputs.rgb, diffComp_node.inputs.true)

        # Connect diffuse
        settings.material.connect((diffComp_nodeID, 0), (shaderID, 3))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXShaderSG')
        # maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')

        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.dsm', s=2)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo1')
        maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')
        maya.cmds.connectAttr('SXShaderSG.msg', 'SXMaterials_materialInfo1.sg')
        maya.cmds.relationship('link', ':lightLinker1', 'SXShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship('shadowLink', ':lightLinker1', 'SXShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr('SXShaderSG.pa', ':renderPartition.st', na=True)
        # maya.cmds.connectAttr('SXShader.msg', ':defaultShaderList1.s', na=True)

        # automatically assign shader to existing multi-layer meshes
        meshList = maya.cmds.ls(ni=True, typ='mesh')
        for mesh in meshList:
            if maya.cmds.attributeQuery('activeLayerSet', node=mesh, exists=True):
                maya.cmds.sets(mesh, e=True, forceElement='SXShaderSG')

    def createSXExportShader(self):
        if maya.cmds.objExists('SXExportShader'):
            shadingGroup = maya.cmds.listConnections(
                'SXExportShader', type='shadingEngine')
            # componentsWithExportMaterial = maya.cmds.sets(shadingGroup, q=True)
            maya.cmds.delete('SXExportShader')
        if maya.cmds.objExists('SXExportShaderSG'):
            maya.cmds.delete('SXExportShaderSG')

        uvChannels = settings.projectSettings['SXToolsExportChannels']
        maskID = uvChannels[0]
        maskAxis = str(maskID[0])
        maskIndex = int(maskID[1])
        numLayers = float(settings.projectSettings['SXToolsLayerCount'])

        materialName = 'SXExportShader'
        settings.material = SFXNetwork.create(materialName)
        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='TraditionalGameSurfaceShader')

        black_node = settings.material.add(sfxnodes.Color)
        black_node.name = 'black'
        black_node.color = [0, 0, 0, 1]
        black_node.posx = -250
        black_node.posy = 250

        alphaIf_node = settings.material.add(sfxnodes.IfElseBasic)
        alphaIf_node.name = 'alphaColorIf'
        alphaIf_node.posx = -750
        alphaIf_node.posy = 0

        uvIf_node = settings.material.add(sfxnodes.IfElseBasic)
        uvIf_node.name = 'uvIf'
        uvIf_node.posx = -1000
        uvIf_node.posy = 250

        uConst_node = settings.material.add(sfxnodes.VectorConstruct)
        uConst_node.posx = -1250
        uConst_node.posy = 500
        uConst_node.name = 'uComp'

        vConst_node = settings.material.add(sfxnodes.VectorConstruct)
        vConst_node.posx = -1250
        vConst_node.posy = 750
        vConst_node.name = 'vComp'

        index_node = settings.material.add(sfxnodes.IntValue)
        index_node.posx = -2500
        index_node.posy = 500
        index_node.name = 'uvIndex'
        uvIndexID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='uvIndex')
        settings.exportNodeDict['uvIndex'] = uvIndexID

        indexRef_node = settings.material.add(sfxnodes.IntValue)
        indexRef_node.posx = -2500
        indexRef_node.posy = 750
        indexRef_node.value = maskIndex
        indexRef_node.name = 'uvMaskIndex'

        indexBool_node = settings.material.add(sfxnodes.BoolValue)
        indexBool_node.posx = -2500
        indexBool_node.posy = 1000
        indexBool_node.name = 'indexBool'
        indexBoolID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='indexBool')

        ifUv3_node = settings.material.add(sfxnodes.IfElse)
        ifUv3_node.posx = -1250
        ifUv3_node.posy = 1000

        divU_node = settings.material.add(sfxnodes.Divide)
        divU_node.posx = -1000
        divU_node.posy = 500
        divU_node.name = 'divU'
        divUID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='divU')

        divV_node = settings.material.add(sfxnodes.Divide)
        divV_node.posx = -1000
        divV_node.posy = 750
        divV_node.name = 'divV'
        divVID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='divV')

        divVal_node = settings.material.add(sfxnodes.Float3)
        divVal_node.posx = -2500
        divVal_node.posy = 1250
        divVal_node.valueX = numLayers
        divVal_node.valueY = numLayers
        divVal_node.valueZ = numLayers
        divVal_node.name = 'divVal'

        uv0_node = settings.material.add(sfxnodes.StringValue)
        uv0_node.name = 'uv0String'
        uv0_node.posx = -2250
        uv0_node.posy = 500
        uv0_node.value = 'UV0'

        uv1_node = settings.material.add(sfxnodes.StringValue)
        uv1_node.name = 'uv1String'
        uv1_node.posx = -2250
        uv1_node.posy = 750
        uv1_node.value = 'UV1'

        uv2_node = settings.material.add(sfxnodes.StringValue)
        uv2_node.name = 'uv2String'
        uv2_node.posx = -2250
        uv2_node.posy = 1000
        uv2_node.value = 'UV2'

        uv3_node = settings.material.add(sfxnodes.StringValue)
        uv3_node.name = 'uv3String'
        uv3_node.posx = -2250
        uv3_node.posy = 1250
        uv3_node.value = 'UV3'

        uvPath_node = settings.material.add(sfxnodes.PathDirectionList)
        uvPath_node.posx = -2000
        uvPath_node.posy = 500

        uPath_node = settings.material.add(sfxnodes.PathDirection)
        uPath_node.name = 'uPath'
        uPath_node.posx = -750
        uPath_node.posy = 500
        uPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uPath')

        vPath_node = settings.material.add(sfxnodes.PathDirection)
        vPath_node.name = 'vPath'
        vPath_node.posx = -750
        vPath_node.posy = 750
        vPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='vPath')

        vertcol_node = settings.material.add(sfxnodes.VertexColor)
        vertcol_node.posx = -1750
        vertcol_node.posy = 0

        uvset_node = settings.material.add(sfxnodes.UVSet)
        uvset_node.posx = -1750
        uvset_node.posy = 500
        uvset_node.name = 'uvSet'
        uvID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uvSet')

        vectComp_node = settings.material.add(sfxnodes.VectorComponent)
        vectComp_node.posx = -1500
        vectComp_node.posy = 500
        vectComp_node.name = 'uvSplitter'

        uvBool_node = settings.material.add(sfxnodes.Bool)
        uvBool_node.posx = -2000
        uvBool_node.posy = 250
        uvBool_node.name = 'uvBool'
        uvBoolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uvBool')
        settings.exportNodeDict['uvBool'] = uvBoolID

        colorBool_node = settings.material.add(sfxnodes.Bool)
        colorBool_node.posx = -2000
        colorBool_node.posy = 0
        colorBool_node.name = 'colorBool'
        colorBoolID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='colorBool')
        settings.exportNodeDict['colorBool'] = colorBoolID

        # Create connections
        settings.material.connect(index_node.outputs.int, uvPath_node.inputs.index)
        settings.material.connect(uv0_node.outputs.string,
                                    uvPath_node.inputs.options)
        settings.material.connect(uv1_node.outputs.string,
                                    uvPath_node.inputs.options)
        settings.material.connect(uv2_node.outputs.string,
                                    uvPath_node.inputs.options)
        settings.material.connect(uv3_node.outputs.string,
                                    uvPath_node.inputs.options)
        settings.material.connect(uvPath_node.outputs.result, (uvID, 1))

        settings.material.connect(index_node.outputs.int, ifUv3_node.inputs.a)
        settings.material.connect(indexRef_node.outputs.int, ifUv3_node.inputs.b)
        settings.material.connect(indexBool_node.outputs.bool,
                                    ifUv3_node.inputs.true)
        settings.material.connect((indexBoolID, 1), ifUv3_node.inputs.false)

        settings.material.connect(ifUv3_node.outputs.result, (uPathID, 0))
        settings.material.connect(ifUv3_node.outputs.result, (vPathID, 0))

        settings.material.connect(uvset_node.outputs.uv, vectComp_node.inputs.vector)

        settings.material.connect(vectComp_node.outputs.x, uConst_node.inputs.x)
        settings.material.connect(vectComp_node.outputs.x, uConst_node.inputs.y)
        settings.material.connect(vectComp_node.outputs.x, uConst_node.inputs.z)
        settings.material.connect(vectComp_node.outputs.y, vConst_node.inputs.x)
        settings.material.connect(vectComp_node.outputs.y, vConst_node.inputs.y)
        settings.material.connect(vectComp_node.outputs.y, vConst_node.inputs.z)

        settings.material.connect(uConst_node.outputs.float3, (divUID, 0))
        settings.material.connect(vConst_node.outputs.float3, (divVID, 0))
        settings.material.connect(divVal_node.outputs.float3, (divUID, 1))
        settings.material.connect(divVal_node.outputs.float3, (divVID, 1))

        settings.material.connect(divU_node.outputs.result, uPath_node.inputs.a)
        settings.material.connect(divV_node.outputs.result, vPath_node.inputs.a)
        settings.material.connect(uConst_node.outputs.float3, uPath_node.inputs.b)
        settings.material.connect(vConst_node.outputs.float3, vPath_node.inputs.b)

        settings.material.connect(uvBool_node.outputs.bool,
                                    uvIf_node.inputs.condition)
        settings.material.connect(uPath_node.outputs.result, uvIf_node.inputs.true)
        settings.material.connect(vPath_node.outputs.result, uvIf_node.inputs.false)

        settings.material.connect(colorBool_node.outputs.bool,
                                    alphaIf_node.inputs.condition)
        settings.material.connect(vertcol_node.outputs.rgb, alphaIf_node.inputs.true)
        settings.material.connect(uvIf_node.outputs.result,
                                    alphaIf_node.inputs.false)

        settings.material.connect(alphaIf_node.outputs.result, (shaderID, 1))

        settings.material.connect(black_node.outputs.rgb, (shaderID, 3))
        settings.material.connect(black_node.outputs.rgb, (shaderID, 5))
        settings.material.connect(black_node.outputs.rgb, (shaderID, 6))
        settings.material.connect(black_node.outputs.red, (shaderID, 4))
        settings.material.connect(black_node.outputs.red, (shaderID, 7))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXExportShaderSG')
        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo2')
        maya.cmds.connectAttr('SXExportShader.oc', 'SXExportShaderSG.ss')
        maya.cmds.connectAttr('SXExportShaderSG.msg', 'SXMaterials_materialInfo2.sg')
        maya.cmds.relationship('link', ':lightLinker1', 'SXExportShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship('shadowLink', ':lightLinker1', 'SXExportShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr('SXExportShaderSG.pa', ':renderPartition.st', na=True)
        # maya.cmds.connectAttr('SXExportShader.msg', ':defaultShaderList1.s', na=True)

    """
    if componentsWithMaterial is not None:
    maya.cmds.sets(componentsWithMaterial, e=True, forceElement='SXShaderSG')
    if componentsWithExportMaterial is not None:
    maya.cmds.sets(componentsWithExportMaterial, e=True, forceElement='SXShaderSG')
    """

    def createSXPBShader(self):
        if maya.cmds.objExists('SXPBShader'):
            maya.cmds.delete('SXPBShader')
        if maya.cmds.objExists('SXPBShaderSG'):
            maya.cmds.delete('SXPBShaderSG')

        nodeIDs = []
        channels = ('occlusion', 'specular', 'transmission', 'emission')
        matChannels = settings.projectSettings['SXToolsMatChannels']
        uvChannels = settings.projectSettings['SXToolsExportChannels']
        matDict = {
            'occlusion': uvChannels[1],
            'specular': uvChannels[2],
            'transmission': uvChannels[3],
            'emission': uvChannels[4]
        }
        maskID = uvChannels[0]
        maskAxis = str(maskID[0])
        maskIndex = int(maskID[1])
        uvDict = {}

        pbmatName = 'SXPBShader'
        pbmat = StingrayPBSNetwork.create(pbmatName)
        nodeCount = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeCount=True)
        shaderID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='Standard_Base')
        maya.cmds.shaderfx(sfxnode=pbmatName, edit_action=(shaderID, "makeunique"))

        for i in range(nodeCount):
            nodeIDs.append(
                maya.cmds.shaderfx(sfxnode='SXPBShader', getNodeUIDFromIndex=i))
        for node in nodeIDs:
            maya.cmds.shaderfx(sfxnode='SXPBShader', deleteNode=node)

        shader_node = pbmat.add(pbsnodes.StandardBase)
        shader_node.posx = 0
        shader_node.posy = 0
        shader_node.name = 'StandardBase'
        shaderID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='StandardBase')

        vertCol_node = pbmat.add(pbsnodes.VertexColor0)
        vertCol_node.posx = -1000
        vertCol_node.posy = -250
        vertCol_node.name = 'vertCol'
        vertColID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='vertCol')

        black_node = pbmat.add(pbsnodes.ConstantVector3)
        black_node.posx = -1250
        black_node.posy = 0
        black_node.name = 'black'
        blackID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='black')

        k = 0
        for channel in channels:
            if matChannels[k] is True:
                if int(matDict[channel][1]) == 1:
                    uv_node = pbmat.add(pbsnodes.Texcoord1)
                elif int(matDict[channel][1]) == 2:
                    uv_node = pbmat.add(pbsnodes.Texcoord2)
                elif int(matDict[channel][1]) == 3:
                    uv_node = pbmat.add(pbsnodes.Texcoord3)
                uv_node.posx = -1000
                uv_node.posy = k * 250
                uv_node.name = channel
                uvID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName=channel)
                uvDict[channel] = uvID
            else:
                uvDict[channel] = blackID
            k += 1

        invert_node = pbmat.add(pbsnodes.Invert)
        invert_node.posx = -750
        invert_node.posy = 250
        invert_node.name = 'inv'
        invertID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='inv')

        metPow_node = pbmat.add(pbsnodes.Power)
        metPow_node.posx = -500
        metPow_node.posy = 0
        metPow_node.name = 'MetallicPower'
        metPowID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='MetallicPower')

        roughPow_node = pbmat.add(pbsnodes.Power)
        roughPow_node.posx = -500
        roughPow_node.posy = 250
        roughPow_node.name = 'RoughnessPower'
        roughPowID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='RoughnessPower')

        metVal_node = pbmat.add(pbsnodes.MaterialVariable)
        metVal_node.posx = -1250
        metVal_node.posy = 250
        metVal_node.name = 'MetallicValue'
        metVal_node.type = 0
        metVal_node.defaultscalar = 0.9
        metValID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='MetallicValue')

        roughVal_node = pbmat.add(pbsnodes.MaterialVariable)
        roughVal_node.posx = -1250
        roughVal_node.posy = 500
        roughVal_node.name = 'RoughnessValue'
        roughVal_node.type = 0
        roughVal_node.defaultscalar = 0.4
        roughValID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='RoughnessValue')

        # Create connections
        pbmat.connect(vertCol_node.outputs.rgba, (shaderID, 1))

        pbmat.connect((uvDict['occlusion'], 0), (shaderID, 8))
        if matDict['occlusion'][0] == 'U':
            shader_node.activesocket = 8
            shader_node.socketswizzlevalue = 'x'
        elif matDict['occlusion'][0] == 'V':
            shader_node.activesocket = 8
            shader_node.socketswizzlevalue = 'y'

        pbmat.connect((uvDict['specular'], 0), metPow_node.inputs.x)
        pbmat.connect((uvDict['specular'], 0), invert_node.inputs.value)
        if matDict['specular'][0] == 'U':
            metPow_node.activesocket = 0
            metPow_node.socketswizzlevalue = 'x'
            invert_node.activesocket = 0
            invert_node.socketswizzlevalue = 'x'
        elif matDict['specular'][0] == 'V':
            metPow_node.activesocket = 0
            metPow_node.socketswizzlevalue = 'y'
            invert_node.activesocket = 0
            invert_node.socketswizzlevalue = 'y'

        pbmat.connect((uvDict['emission'], 0), (shaderID, 7))
        if matDict['emission'][0] == 'U':
            shader_node.activesocket = 7
            shader_node.socketswizzlevalue = 'xxx'
        elif matDict['emission'][0] == 'V':
            shader_node.activesocket = 7
            shader_node.socketswizzlevalue = 'yyy'

        pbmat.connect(invert_node.outputs.result, roughPow_node.inputs.x)
        pbmat.connect(metVal_node.outputs.result, metPow_node.inputs.y)
        pbmat.connect(roughVal_node.outputs.result, roughPow_node.inputs.y)

        pbmat.connect(metPow_node.outputs.result, (shaderID, 5))
        pbmat.connect(roughPow_node.outputs.result, (shaderID, 6))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=pbmatName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXPBShaderSG')
        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo3')
        maya.cmds.connectAttr('SXPBShader.oc', 'SXPBShaderSG.ss')
        maya.cmds.connectAttr('SXPBShaderSG.msg', 'SXMaterials_materialInfo3.sg')
        maya.cmds.relationship('link', ':lightLinker1', 'SXPBShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship('shadowLink', ':lightLinker1', 'SXPBShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr('SXPBShaderSG.pa', ':renderPartition.st', na=True)
        # maya.cmds.connectAttr('SXExportShader.msg', ':defaultShaderList1.s', na=True)

    # The pre-vis material depends on lights in the scene to correctly display occlusion

    def createDefaultLights(self):
        if len(maya.cmds.ls(type='light')) == 0:
            print('SX Tools: No lights found in scene, creating default lights.')
            maya.cmds.directionalLight(
                name='defaultSXDirectionalLight',
                rotation=(-25, 30, 0),
                position=(0, 50, 0))
            maya.cmds.setAttr('defaultSXDirectionalLight.useDepthMapShadows', 1)
            maya.cmds.setAttr('defaultSXDirectionalLight.dmapFilterSize', 5)
            maya.cmds.setAttr('defaultSXDirectionalLight.dmapResolution', 1024)
            maya.cmds.ambientLight(
                name='defaultSXAmbientLight',
                intensity=0.4,
                ambientShade=0,
                position=(0, 50, 0))
            maya.cmds.select(clear=True)
            sx.selectionManager()

    def createCreaseSets(self):
        if maya.cmds.objExists('sxCreasePartition') is False:
            maya.cmds.createNode('partition', n='sxCreasePartition')
        if maya.cmds.objExists('sxCrease0') is False:
            maya.cmds.createNode('creaseSet', n='sxCrease0')
            maya.cmds.setAttr('sxCrease0.creaseLevel', 0.0)
            maya.cmds.connectAttr('sxCrease0.partition', 'sxCreasePartition.sets[0]')
        if maya.cmds.objExists('sxCrease1') is False:
            maya.cmds.createNode('creaseSet', n='sxCrease1')
            maya.cmds.setAttr('sxCrease1.creaseLevel', 0.5)
            maya.cmds.setAttr('sxCrease1.memberWireframeColor', 3)
            maya.cmds.connectAttr('sxCrease1.partition', 'sxCreasePartition.sets[1]')
        if maya.cmds.objExists('sxCrease2') is False:
            maya.cmds.createNode('creaseSet', n='sxCrease2')
            maya.cmds.setAttr('sxCrease2.creaseLevel', 1.0)
            maya.cmds.setAttr('sxCrease2.memberWireframeColor', 5)
            maya.cmds.connectAttr('sxCrease2.partition', 'sxCreasePartition.sets[2]')
        if maya.cmds.objExists('sxCrease3') is False:
            maya.cmds.createNode('creaseSet', n='sxCrease3')
            maya.cmds.setAttr('sxCrease3.creaseLevel', 2.0)
            maya.cmds.setAttr('sxCrease3.memberWireframeColor', 6)
            maya.cmds.connectAttr('sxCrease3.partition', 'sxCreasePartition.sets[3]')
        if maya.cmds.objExists('sxCrease4') is False:
            maya.cmds.createNode('creaseSet', n='sxCrease4')
            maya.cmds.setAttr('sxCrease4.creaseLevel', 10.0)
            maya.cmds.setAttr('sxCrease4.memberWireframeColor', 7)
            maya.cmds.connectAttr('sxCrease4.partition', 'sxCreasePartition.sets[4]')

    def createDisplayLayers(self):
        if 'assetsLayer' not in maya.cmds.ls(type='displayLayer'):
            print('SX Tools: Creating assetsLayer')
            maya.cmds.createDisplayLayer(name='assetsLayer', number=1, empty=True)
        if 'exportsLayer' not in maya.cmds.ls(type='displayLayer'):
            print('SX Tools: Creating exportsLayer')
            maya.cmds.createDisplayLayer(name='exportsLayer', number=2, empty=True)

    def setPrimVars(self):
        refLayers = layers.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())
        refCount = settings.projectSettings['SXToolsLayerCount']

        if refLayers == 'layer1':
            refLayers = 'layer1',

        attrList = maya.cmds.listAttr(settings.shapeArray, ud=True)
        if attrList is None:
            maya.cmds.addAttr(
                settings.shapeArray, ln='activeLayerSet', at='double', min=0, max=9, dv=0)
            maya.cmds.addAttr(
                settings.shapeArray, ln='transparency', at='double', min=0, max=1, dv=0)
            maya.cmds.addAttr(settings.shapeArray, ln='shadingMode', at='double', min=0, max=2, dv=0)
            maya.cmds.addAttr(
                settings.shapeArray, ln='occlusionVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(
                settings.shapeArray, ln='specularVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(
                settings.shapeArray, ln='transmissionVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(
                settings.shapeArray, ln='emissionVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(
                settings.shapeArray, ln='occlusionBlendMode', at='double', min=0, max=2, dv=0)
            maya.cmds.addAttr(
                settings.shapeArray, ln='specularBlendMode', at='double', min=0, max=2, dv=0)
            maya.cmds.addAttr(
                settings.shapeArray, ln='transmissionBlendMode', at='double', min=0, max=2, dv=0)
            maya.cmds.addAttr(
                settings.shapeArray, ln='emissionBlendMode', at='double', min=0, max=2, dv=0)
            for k in range(0, settings.projectSettings['SXToolsLayerCount']):
                visName = str(refLayers[k]) + 'Visibility'
                blendName = str(refLayers[k]) + 'BlendMode'
                maya.cmds.addAttr(settings.shapeArray, ln=visName, at='double', min=0, max=1, dv=1)
                maya.cmds.addAttr(settings.shapeArray, ln=blendName, at='double', min=0, max=2, dv=0)
        else:
            if ('activeLayerSet' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='activeLayerSet', at='double', min=0, max=10, dv=0)
            if ('transparency' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='transparency', at='double', min=0, max=1, dv=0)
            if ('shadingMode' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='shadingMode', at='double', min=0, max=2, dv=0)
            if ('occlusionVisibility' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='occlusionVisibility', at='double', min=0, max=1, dv=1)
            if ('specularVisibility' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='specularVisibility', at='double', min=0, max=1, dv=1)
            if ('transmissionVisibility' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='transmissionVisibility', at='double', min=0, max=1, dv=1)
            if ('emissionVisibility' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='emissionVisibility', at='double', min=0, max=1, dv=1)
            if ('occlusionBlendMode' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='occlusionBlendMode', at='double', min=0, max=2, dv=0)
            if ('specularBlendMode' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='specularBlendMode', at='double', min=0, max=2, dv=0)
            if ('transmissionBlendMode' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='transmissionBlendMode', at='double', min=0, max=2, dv=0)
            if ('emissionBlendMode' not in attrList):
                maya.cmds.addAttr(
                    settings.shapeArray, ln='emissionBlendMode', at='double', min=0, max=2, dv=0)

            for k in range(0, settings.projectSettings['SXToolsLayerCount']):
                blendName = str(refLayers[k]) + 'BlendMode'
                visName = str(refLayers[k]) + 'Visibility'
                if (blendName not in attrList):
                    maya.cmds.addAttr(settings.shapeArray, ln=blendName, at='double', min=0, max=2, dv=0)
                if (visName not in attrList):
                    maya.cmds.addAttr(settings.shapeArray, ln=visName, at='double', min=0, max=1, dv=1)


class Export(object):
    def __init__(self):
        return None

    def initUVs(self, selected, UVSetName):
        maya.cmds.polyUVSet(selected, create=True, uvSet=UVSetName)
        maya.cmds.polyUVSet(selected, currentUVSet=True, uvSet=UVSetName)
        maya.cmds.polyForceUV(selected, uni=True)

        maya.cmds.select(maya.cmds.polyListComponentConversion(selected, tf=True))
        maya.cmds.polyMapCut(ch=1)
        maya.cmds.select(maya.cmds.polyListComponentConversion(selected, tuv=True))
        maya.cmds.polyEditUV(relative=False, uValue=0, vValue=0)
        sx.selectionManager()

    def flattenLayers(self, selected, numLayers):
        startTime2 = maya.cmds.timerX()
        if numLayers > 1:
            for i in range(1, numLayers):
                sourceLayer = 'layer' + str(i + 1)
                layers.mergeLayers(selected, sourceLayer, 'layer1', True)

        elapsedTime = maya.cmds.timerX(startTime=startTime2)

    # For export, the layer colors are flattened to a single vertex color set,
    # but their "layer masks" are written to UV coordinates.
    # Each vertex must be assigned to one mask.
    def colorToUV(self, selected, uSourceColorSet, vSourceColorSet, targetUVSet):
        startTime1 = maya.cmds.timerX()

        selectionList = OM.MSelectionList()
        selectionList.add(selected)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        uColorArray = OM.MColorArray()
        vColorArray = OM.MColorArray()
        uvIdArray = (OM.MIntArray(), OM.MIntArray())
        uArray = OM.MFloatArray()
        vArray = OM.MFloatArray()

        if uSourceColorSet != 'zero':
            uColorArray = MFnMesh.getFaceVertexColors(colorSet=uSourceColorSet)
            lenColorArray = len(uColorArray)
        if vSourceColorSet != 'zero':
            vColorArray = MFnMesh.getFaceVertexColors(colorSet=vSourceColorSet)
            lenColorArray = len(uColorArray)
        uvIdArray = MFnMesh.getAssignedUVs()

        uArray.setLength(lenColorArray)
        vArray.setLength(lenColorArray)

        for k in range(lenColorArray):
            if uColorArray[k].a > 0:
                uArray[k] = uColorArray[k].r
            elif vColorArray[k].r <= 0:
                uArray[k] = 0

            if vColorArray[k].a > 0:
                vArray[k] = vColorArray[k].r
            elif vColorArray[k].a <= 0:
                vArray[k] = 0

        MFnMesh.setUVs(uArray, vArray, targetUVSet)
        MFnMesh.assignUVs(uvIdArray[0], uvIdArray[1], uvSet=targetUVSet)

        elapsedTime = maya.cmds.timerX(startTime=startTime1)
        # print ('Elapsed Time for '+uSourceColorSet+' and '+vSourceColorSet+': '+str(elapsedTime)+'\n')

    def overlayToUV(self, selected, layers, targetUVSetList):
        for idx, layer in enumerate(layers):
            selectionList = OM.MSelectionList()
            selectionList.add(selected)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            colorArray = OM.MColorArray()
            uvIdArray = (OM.MIntArray(), OM.MIntArray())
            uArray1 = OM.MFloatArray()
            vArray1 = OM.MFloatArray()
            uArray2 = OM.MFloatArray()
            vArray2 = OM.MFloatArray()
            
            colorArray = MFnMesh.getFaceVertexColors(colorSet=layer)
            lenColorArray = len(colorArray)
            uvIdArray = MFnMesh.getAssignedUVs()

            uArray1.setLength(lenColorArray)
            vArray1.setLength(lenColorArray)
            uArray2.setLength(lenColorArray)
            vArray2.setLength(lenColorArray)

            for k in range(lenColorArray):
                uArray1[k] = colorArray[k].r
                vArray1[k] = colorArray[k].g
                uArray2[k] = colorArray[k].b
                vArray2[k] = colorArray[k].a

            MFnMesh.setUVs(uArray1, vArray1, targetUVSetList[idx][0])
            MFnMesh.assignUVs(uvIdArray[0], uvIdArray[1], uvSet=targetUVSetList[idx][0])
            MFnMesh.setUVs(uArray2, vArray2, targetUVSetList[idx][1])
            MFnMesh.assignUVs(uvIdArray[0], uvIdArray[1], uvSet=targetUVSetList[idx][1])

    # The layer masks are written to UV3 using an offset value.
    # This makes it simpler to separate each vertex to the correct layer in the game engine.

    def layerToUV(self, selected, uvID, numLayers, offset):
        axis = str.lower(str(uvID[0]))
        targetUVSet = 'UV' + str(uvID[1])

        # startTime1 = maya.cmds.timerX()

        selectionList = OM.MSelectionList()
        selectionList.add(selected)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerArray = OM.MColorArray()
        uArray = OM.MFloatArray()
        vArray = OM.MFloatArray()
        uvIdArray = MFnMesh.getAssignedUVs(uvSet='UV1')

        # Iterate through all layers from top to bottom to assign each vertex to correct layer mask.
        for i in range(1, numLayers + 1):
            sourceColorSet = 'layer' + str(i)
            if i == 1:
                layerArray = MFnMesh.getFaceVertexColors(sourceColorSet)
                lenLayerArray = len(layerArray)
                uArray.setLength(lenLayerArray)
                vArray.setLength(lenLayerArray)
                for k in range(lenLayerArray):
                    uArray[k] = 1
                    vArray[k] = 1
            else:
                layerArray = MFnMesh.getFaceVertexColors(sourceColorSet)
                for k in range(lenLayerArray):
                    # NOTE: Alpha inadvertedly gets written with a low non-zero values when using brush tools.
                    # The tolerance threshold helps fix that.
                    if (layerArray[k].a >=
                                    settings.projectSettings['SXToolsAlphaTolerance']) and (axis == 'u'):
                        uArray[k] = float(i)
                    elif (layerArray[k].a >= settings.projectSettings['SXToolsAlphaTolerance']
                                            ) and (axis == 'v'):
                        vArray[k] = float(i)

        MFnMesh.setUVs(uArray, vArray, targetUVSet)
        MFnMesh.assignUVs(uvIdArray[0], uvIdArray[1], uvSet=targetUVSet)

        # elapsedTime = maya.cmds.timerX(startTime=startTime1)
        # print ('Elapsed Time for layer baking '+str(elapsedTime)+'\n')

    def channelsToUV(self, exportShape):
        shape = exportShape
        matList = ('occlusion', 'specular', 'transmission', 'emission')
        matArray = settings.projectSettings['SXToolsMatChannels']
        uvArray = list(settings.projectSettings['SXToolsExportChannels'])
        # remove layermask export channel
        uvArray.pop(0)
        exportDict = {}

        # filter disabled channels
        k = 3
        for i in reversed(matArray):
            if int(i) == 0:
                uvArray.pop(matArray.index(i))
            elif int(i) == 1:
                exportDict[uvArray[k]] = matList[k]
            k -= 1

        for k in range(0, 3):
            a = 'U' + str(k + 1)
            b = 'V' + str(k + 1)
            if (a in exportDict):
                uChan = exportDict[a]
            else:
                uChan = 'zero'
            if (b in exportDict):
                vChan = exportDict[b]
            else:
                vChan = 'zero'
            uvSet = 'UV' + str(k + 1)

            if not ((uChan == 'zero') and (vChan == 'zero')):
                self.colorToUV(shape, uChan, vChan, uvSet)

    # The steps of the mesh export process:
    # 1) Duplicate objects under export folder
    # 2) Rename new objects to match originals but with a suffix
    # 3) Call the mesh processing functions 
    # 4) Delete history on the processed meshes.
    def processObjects(self, selectionArray):
        # Timer for evaluating script performance
        startTime0 = maya.cmds.timerX()

        sourceArray = []
        refLayers = layers.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())
        maskExport = settings.projectSettings['SXToolsExportChannels'][0]
        exportSmoothValue = settings.projectSettings['SXToolsSmoothExport']
        exportOffsetValue = settings.projectSettings['SXToolsExportOffset']
        overlayArray = settings.projectSettings['SXToolsOverlays']
        overlayUVArray = settings.projectSettings['SXToolsOverlaysExportChannels']
        numLayers = settings.projectSettings['SXToolsLayerCount']-len(overlayArray)

        # Clear existing static exports folder and create if necessary
        if maya.cmds.objExists('_staticExports'):
            maya.cmds.delete('_staticExports')
        maya.cmds.group(empty=True, name='_staticExports')

        # Find the root nodes of all selected elements
        for selection in selectionArray:
            source = maya.cmds.ls(selection, l=True)[0].split("|")[1]
            if source not in sourceArray:
                sourceArray.append(source)

        # Duplicate all selected objects for export
        sourceNamesArray = maya.cmds.ls(sourceArray, dag=True, tr=True)
        exportArray = maya.cmds.duplicate(sourceArray, renameChildren=True)

        # Parent export objects under new group,
        # the tricky bit here is renaming the new objects to the old names.
        # For tracking objects correctly when they might not have unique names,
        # we use "long" and "fullpath" options.
        for export in exportArray:
            if maya.cmds.listRelatives(export, parent=True) is None:
                maya.cmds.parent(export, '_staticExports')

        exportNamesArray = maya.cmds.ls(
            maya.cmds.listRelatives('_staticExports'), dag=True, tr=True)

        # Rename export objects
        for i in range(len(sourceNamesArray)):
            maya.cmds.rename(exportNamesArray[i], sourceNamesArray[i])

        exportShapeArray = self.getTransforms(
            maya.cmds.listRelatives(
                '_staticExports', ad=True, type='mesh', fullPath=True))

        # Check for additional Layer Sets on the objects,
        # create additional entries for export
        for exportShape in exportShapeArray:
            var = int(layers.getLayerSet(exportShape))
            if var > 0:
                tools.swapLayerSets([exportShape, ], 0)                
            for x in xrange(1, var+1):
                variant = maya.cmds.duplicate(exportShape, name=str(exportShape).split('|')[-1]+'_var'+str(x))[0]
                tools.swapLayerSets([variant, ], x)

        exportShapeArray = self.getTransforms(
            maya.cmds.listRelatives(
                '_staticExports', ad=True, type='mesh', fullPath=True))
        
        # Suffix the export objects        
        for exportShape in exportShapeArray:
            if maya.cmds.getAttr(str(exportShape) + '.transparency') == 1:
                exportName = str(exportShape).split('|')[-1] + '_transparent'
            elif settings.projectSettings['SXToolsExportSuffix'] is True:
                exportName = str(exportShape).split('|')[-1] + '_paletted'
            else:
                exportName = str(exportShape).split('|')[-1]
            maya.cmds.rename(exportShape, str(exportName), ignoreShape=True)

        exportShapeArray = self.getTransforms(
            maya.cmds.listRelatives(
                '_staticExports', ad=True, type='mesh', fullPath=True))

        for exportShape in exportShapeArray:
            # Check for existing additional UV sets and delete them,
            # create default UVs to UV0
            indices = maya.cmds.polyUVSet(exportShape, q=True, allUVSetsIndices=True)

            for i in indices:
                if i == 0:
                    name = maya.cmds.getAttr(
                        str(exportName) + '.uvSet[' + str(i) + '].uvSetName')
                    maya.cmds.polyUVSet(exportShape, rename=True, uvSet=name, newUVSet='UV0')
                    maya.cmds.polyUVSet(exportShape, currentUVSet=True, uvSet='UV0')
                    maya.cmds.polyAutoProjection(
                        exportShape, lm=0, pb=0, ibd=1, cm=0, l=3, sc=1, o=0, p=6, ps=0.2, ws=0)

                if i > 0:
                    name = maya.cmds.getAttr(
                        str(maya.cmds.ls(exportName)) + '.uvSet[' + str(i) + '].uvSetName')
                    maya.cmds.polyUVSet(exportShape, delete=True, uvSet=name)

            # Create UV sets for color set data
            self.initUVs(exportShape, 'UV1')
            self.initUVs(exportShape, 'UV2')
            self.initUVs(exportShape, 'UV3')
            if overlayUVArray is not None:
                for uvSet in overlayUVArray:
                    for uv in uvSet:
                        self.initUVs(exportShape, uv)

            # Bake material properties to UV channels
            self.channelsToUV(exportShape)

            # Bake masks
            self.layerToUV(exportShape, maskExport, numLayers, 1)
            
            # Bake overlays
            self.overlayToUV(exportShape, overlayArray, overlayUVArray)
            
            # Delete history
            maya.cmds.delete(exportShape, ch=True)

            # Flatten colors to layer1
            # maya.cmds.select(exportShape)
            self.flattenLayers(exportShape, numLayers)

            # Delete unnecessary color sets (leave only layer1)
            colSets = maya.cmds.polyColorSet(exportShape, query=True, allColorSets=True)
            for set in colSets:
                if str(set) != 'layer1':
                    maya.cmds.polyColorSet(exportShape, delete=True, colorSet=str(set))

            # Set layer1 visible for userfriendliness
            maya.cmds.polyColorSet(exportShape, currentColorSet=True, colorSet='layer1')
            maya.cmds.sets(exportShape, e=True, forceElement='SXPBShaderSG')
            
            # Smooth mesh as last step for export
            if exportSmoothValue > 0:
                maya.cmds.polySmooth(
                    exportShape, mth=0, sdt=2, ovb=1,
                    ofb=3, ofc=0, ost=1, ocr=0,
                    dv=exportSmoothValue, bnr=1,
                    c=1, kb=1, ksb=1, khe=0,
                    kt=1, kmb=1, suv=1, peh=0,
                    sl=1, dpe=1, ps=0.1, ro=1, ch=0)

            # Move to origin, freeze transformations
            finalList = maya.cmds.listRelatives(
                '_staticExports', children=True, fullPath=True)
            offsetX = 0
            offsetZ = 0
            offsetDist = exportOffsetValue
            for final in finalList:
                maya.cmds.setAttr(str(final) + '.translate', 0, 0, 0, type='double3')
                maya.cmds.makeIdentity(final, apply=True, t=1, r=1, s=1, n=0, pn=1)
                maya.cmds.setAttr(
                    str(final) + '.translate', offsetX, 0, offsetZ, type='double3')
                offsetX += offsetDist
                if offsetX == offsetDist * 5:
                    offsetX = 0
                    offsetZ += offsetDist

        totalTime = maya.cmds.timerX(startTime=startTime0)
        print('SX Tools: Total time ' + str(totalTime))
        maya.cmds.select('_staticExports', r=True)
        sx.selectionManager()
        maya.cmds.editDisplayLayerMembers('exportsLayer', maya.cmds.ls(sl=True))
        self.viewExported()

    # Writing FBX files to a user-defined folder
    # includes finding the unique file using their fullpath names,
    # then stripping the path to create a clean name for the file.
    def exportObjects(self, exportPath):
        print('SX Tools: Writing FBX files, please hold.')
        exportArray = maya.cmds.listRelatives(
            '_staticExports', children=True, fullPath=True)
        for export in exportArray:
            maya.cmds.select(export)
            if settings.projectSettings['SXToolsExportSuffix'] is True:
                exportName = str(export).split('|')[-1] + '.fbx'
            else:
                if str(export).endswith('_paletted'):
                    exportName = str(str(export)[:-9]).split('|')[-1] + '.fbx'
                else:
                    exportName = str(export).split('|')[-1] + '.fbx'
            exportString = exportPath + exportName
            print(exportString + '\n')
            maya.cmds.file(
                exportString,
                force=True,
                options='v=0',
                typ='FBX export',
                pr=True,
                es=True)

    # After a selection of meshes has been processed for export,
    # the user has a button in the tool UI
    # that allows an isolated view of the results.
    def viewExported(self):
        maya.cmds.select('_staticExports')
        maya.cmds.setAttr('exportsLayer.visibility', 1)
        maya.cmds.setAttr('assetsLayer.visibility', 0)
        maya.mel.eval('FrameSelectedWithoutChildren;')
        maya.mel.eval('fitPanel -selectedNoChildren;')

    # Processed meshes no longer have the pre-vis material,
    # so the tool must present a different UI when any of these are selected.
    def checkExported(self, objects):
        if len(settings.objectArray) > 0:
            for obj in objects:
                root = maya.cmds.ls(obj, l=True)[0].split("|")[1]
                if root == '_staticExports':
                    return True
                    break
        else:
            return False

    def viewExportedMaterial(self):
        buttonState1 = maya.cmds.radioButtonGrp(
            'exportShadingButtons1', query=True, select=True)
        buttonState2 = maya.cmds.radioButtonGrp(
            'exportShadingButtons2', query=True, select=True)
        matChannels = settings.projectSettings['SXToolsMatChannels']
        uvChannels = settings.projectSettings['SXToolsExportChannels']

        # Composite
        if buttonState1 == 1:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXPBShaderSG')
            maya.cmds.polyOptions(
                activeObjects=True,
                colorMaterialChannel='ambientDiffuse',
                colorShadedDisplay=True)
            maya.mel.eval('DisplayLight;')

        # Albedo
        elif buttonState1 == 2:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXExportShaderSG')
            chanID = uvChannels[0]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(settings.exportNodeDict['colorBool'], 'value', True))

        # Layer Masks
        elif buttonState1 == 3:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXExportShaderSG')
            chanID = uvChannels[0]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(settings.exportNodeDict['colorBool'], 'value', False))

        # Occlusion
        elif buttonState2 == 1:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXExportShaderSG')
            chanID = uvChannels[1]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(settings.exportNodeDict['colorBool'], 'value', False))

        # Specular
        elif buttonState2 == 2:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXExportShaderSG')
            chanID = uvChannels[2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(settings.exportNodeDict['colorBool'], 'value', False))

        # Transmission
        elif buttonState2 == 3:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXExportShaderSG')
            chanID = uvChannels[3]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(settings.exportNodeDict['colorBool'], 'value', False))

        # Emission
        elif buttonState2 == 4:
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXExportShaderSG')
            chanID = uvChannels[4]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(settings.exportNodeDict['colorBool'], 'value', False))

        if buttonState1 != 1:
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_int=(settings.exportNodeDict['uvIndex'], 'value', int(chanIndex)))
            if chanAxis == 'U':
                maya.cmds.shaderfx(
                    sfxnode='SXExportShader',
                    edit_bool=(settings.exportNodeDict['uvBool'], 'value', True))
            elif chanAxis == 'V':
                maya.cmds.shaderfx(
                    sfxnode='SXExportShader',
                    edit_bool=(settings.exportNodeDict['uvBool'], 'value', False))

            maya.cmds.shaderfx(sfxnode='SXExportShader', update=True)

    def setExportPath(self):
        path = str(
            maya.cmds.fileDialog2(cap='Select Export Folder', dialogStyle=2, fm=3)[0])
        if path.endswith('/'):
            settings.projectSettings['SXToolsExportPath'] = path
        else:
            settings.projectSettings['SXToolsExportPath'] = path + '/'
        settings.savePreferences()

    # Converts a selection of Maya shape nodes to their transform nodes
    def getTransforms(self, shapeList, fullPath=False):
        transforms = []
        for node in shapeList:
            if 'transform' != maya.cmds.nodeType(node):
                parent = maya.cmds.listRelatives(node, fullPath=True, parent=True)
                transforms.append(parent[0])
        return transforms

    def stripPrimVars(self, objects):
        attrList = maya.cmds.listAttr(objects[0], ud=True)
        print attrList
        for object in objects:
            for attr in attrList:
                print attr
                print object
                maya.cmds.deleteAttr(object, at=attr)


class ToolActions(object):
    def __init__(self):
        return None

    def assignToCreaseSet(self, setName):
        creaseSets = ('sxCrease0', 'sxCrease1', 'sxCrease2', 'sxCrease3', 'sxCrease4')
        if ((maya.cmds.filterExpand(settings.componentArray, sm=31) is not None) or
                        (maya.cmds.filterExpand(settings.componentArray, sm=32) is not None)):

            for set in creaseSets:
                if maya.cmds.sets(settings.componentArray, isMember=set):
                    maya.cmds.sets(settings.componentArray, remove=set)
            maya.cmds.sets(settings.componentArray, forceElement=setName)
        else:
            edgeList = maya.cmds.polyListComponentConversion(settings.componentArray, te=True)
            for set in creaseSets:
                if maya.cmds.sets(edgeList, isMember=set):
                    maya.cmds.sets(edgeList, remove=set)
            maya.cmds.sets(edgeList, forceElement=setName)

    def bakeOcclusion(self):
        bbox = []
        settings.bakeSet = settings.shapeArray
        modifiers = maya.cmds.getModifiers()

        if int(settings.projectSettings['SXToolsMatChannels'][0]) == 1:
            layers.setColorSet('occlusion')

        if settings.toolStates['bakeGroundPlane'] is True:
            maya.cmds.polyPlane(
                name='sxGroundPlane',
                w=settings.toolStates['bakeGroundScale'],
                h=settings.toolStates['bakeGroundScale'],
                sx=1,
                sy=1,
                ax=(0, 1, 0),
                cuv=2,
                ch=0)
            maya.cmds.select(settings.bakeSet)
            sx.selectionManager()

        if maya.cmds.objExists('sxVertexBakeSet') is False:
            maya.cmds.createNode('vertexBakeSet', n='sxVertexBakeSet', skipSelect=True)
            maya.cmds.partition('sxVertexBakeSet', n='vertexBakePartition')

            maya.cmds.addAttr('sxVertexBakeSet', ln='filterSize', sn='fs', min=-1)
            maya.cmds.setAttr('sxVertexBakeSet.filterSize', 0.001)
            maya.cmds.addAttr(
                'sxVertexBakeSet', ln='filterNormalTolerance', sn='fns', min=0, max=180)
            maya.cmds.setAttr('sxVertexBakeSet.filterNormalTolerance', 5)
            maya.cmds.setAttr('sxVertexBakeSet.colorMode', 3)
            maya.cmds.setAttr('sxVertexBakeSet.occlusionRays', 256)
            maya.cmds.setAttr('sxVertexBakeSet.colorBlending', 0)

        if settings.toolStates['bakeTogether'] is True:
            if settings.toolStates['bakeGroundPlane'] is True:
                bbox = maya.cmds.exactWorldBoundingBox(settings.bakeSet)
                maya.cmds.setAttr('sxGroundPlane.translateY',
                (bbox[1] - settings.toolStates['bakeGroundOffset']))
            maya.cmds.convertLightmapSetup(
                camera='persp', vm=True, bo='sxVertexBakeSet')
        else:
            for bake in settings.bakeSet:
                maya.cmds.setAttr((str(bake) + '.visibility'), False)

            # bake separately
            for bake in settings.bakeSet:
                if settings.toolStates['bakeGroundPlane'] is True:
                    bbox = maya.cmds.exactWorldBoundingBox(bake)
                    bakeTx = export.getTransforms([bake, ])
                    groundPos = maya.cmds.getAttr(str(bakeTx[0]) + '.translate')[0]
                    maya.cmds.setAttr('sxGroundPlane.translateX', groundPos[0])
                    maya.cmds.setAttr('sxGroundPlane.translateY',
                    (bbox[1] - settings.toolStates['bakeGroundOffset']))
                    maya.cmds.setAttr('sxGroundPlane.translateZ', groundPos[2])

                maya.cmds.setAttr((str(bake) + '.visibility'), True)
                maya.cmds.select(bake)
                sx.selectionManager()
                maya.cmds.convertLightmapSetup(
                    camera='persp', vm=True, bo='sxVertexBakeSet')
                maya.cmds.setAttr((str(bake) + '.visibility'), False)

            for bake in settings.bakeSet:
                maya.cmds.setAttr((str(bake) + '.visibility'), True)

        if settings.toolStates['bakeGroundPlane'] is True:
            maya.cmds.delete('sxGroundPlane')

        maya.cmds.select(settings.bakeSet)
        sx.selectionManager()

    def bakeBlendOcclusion(self):
        print('SX Tools: Baking local occlusion pass')
        settings.toolStates['bakeGroundPlane'] = False
        settings.toolStates['bakeTogether'] = False
        self.bakeOcclusion()

        for shape in settings.shapeArray:
            selectionList = OM.MSelectionList()
            selectionList.add(shape)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerColorArrayLocal = OM.MColorArray()
            layerColorArrayLocal = MFnMesh.getFaceVertexColors(colorSet='occlusion')
            settings.localOcclusionDict[shape] = layerColorArrayLocal

        print('SX Tools: Baking global occlusion pass')
        settings.toolStates['bakeGroundPlane'] = True
        settings.toolStates['bakeTogether'] = True
        self.bakeOcclusion()

        for shape in settings.shapeArray:
            selectionList = OM.MSelectionList()
            selectionList.add(shape)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerColorArrayGlobal = OM.MColorArray()
            layerColorArrayGlobal = MFnMesh.getFaceVertexColors(colorSet='occlusion')
            settings.globalOcclusionDict[shape] = layerColorArrayGlobal

        settings.toolStates['blendSlider'] = 1.0

    def blendOcclusion(self):
        sliderValue = settings.toolStates['blendSlider']

        for bake in settings.bakeSet:
            selectionList = OM.MSelectionList()
            selectionList.add(bake)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerColorArrayLocal = OM.MColorArray()
            layerColorArrayLocal = settings.localOcclusionDict[bake]
            layerColorArrayGlobal = OM.MColorArray()
            layerColorArrayGlobal = settings.globalOcclusionDict[bake]
            layerColorArray = OM.MColorArray()
            layerColorArray = MFnMesh.getFaceVertexColors(colorSet='occlusion')

            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            testColor = OM.MColor()

            lenSel = len(layerColorArray)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()
                testColor = fvIt.getColor('occlusion')
                layerColorArray[k].r = (
                    1 - sliderValue
                ) * layerColorArrayLocal[k].r + sliderValue * layerColorArrayGlobal[k].r
                layerColorArray[k].g = (
                    1 - sliderValue
                ) * layerColorArrayLocal[k].g + sliderValue * layerColorArrayGlobal[k].g
                layerColorArray[k].b = (
                    1 - sliderValue
                ) * layerColorArrayLocal[k].b + sliderValue * layerColorArrayGlobal[k].b
                k += 1
                fvIt.next()

            maya.cmds.polyColorSet(bake, currentColorSet=True, colorSet='occlusion')
            MFnMesh.setFaceVertexColors(layerColorArray, faceIds, vtxIds)

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
            layers.getSelectedLayer())

    def bakeOcclusionArnold(self):
        bakePath = maya.cmds.textField('bakepath', query=True, text=True)
        if bakePath is None:
            bakePath = 'C:/'
        # check if path has a slash, add if necessary

        # create AO material
        if maya.cmds.objExists('aiSXAO') is False:
            maya.cmds.shadingNode('aiAmbientOcclusion', asShader=True, name='aiSXAO')
            maya.cmds.setAttr('aiSXAO.samples', 8)
            maya.cmds.setAttr('aiSXAO.falloff', 0.1)
            maya.cmds.setAttr('aiSXAO.invertNormals', 0)
            maya.cmds.setAttr('aiSXAO.nearClip', 0.01)
            maya.cmds.setAttr('aiSXAO.farClip', 100)
            maya.cmds.setAttr('aiSXAO.selfOnly', 0)
            print('SX Tools: Creating occlusion material')

        if maya.cmds.objExists('SXAOTexture') is False:
            maya.cmds.shadingNode('file', asTexture=True, name='SXAOTexture')

        bbox = []
        settings.bakeSet = settings.shapeArray
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if int(settings.projectSettings['SXToolsMatChannels'][0]) == 1:
            layers.setColorSet('occlusion')

        if settings.toolStates['bakeGroundPlane'] is True:
            maya.cmds.polyPlane(
                name='sxGroundPlane',
                w=settings.toolStates['bakeGroundScale'],
                h=settings.toolStates['bakeGroundScale'],
                sx=1,
                sy=1,
                ax=(0, 1, 0),
                cuv=2,
                ch=0)
            maya.cmds.select(settings.bakeSet)
            sx.selectionManager()

        for bake in settings.bakeSet:
            # create uvAO uvset
            uvList = maya.cmds.polyUVSet(bake, q=True, allUVSets=True)
            if 'uvAO' not in uvList:
                maya.cmds.polyAutoProjection(
                    bake,
                    lm=0,
                    pb=0,
                    ibd=1,
                    cm=1,
                    l=2,
                    sc=1,
                    o=0,
                    p=6,
                    uvSetName='uvAO',
                    ps=0.2,
                    ws=0)

        # bake everything together
        if shift is True:
            if settings.toolStates['bakeGroundPlane'] is True:
                bbox = maya.cmds.exactWorldBoundingBox(settings.bakeSet)
                maya.cmds.setAttr('sxGroundPlane.translateY',
                (bbox[1] - settings.toolStates['bakeGroundOffset']))
            maya.cmds.arnoldRenderToTexture(
                settings.bakeSet,
                resolution=512,
                shader='aiSXAO',
                aa_samples=1,
                normal_offset=0.001,
                filter='closest',
                folder=bakePath,
                uv_set='uvAO')

        # bake each object separately
        elif shift is False:
            for bake in settings.bakeSet:
                maya.cmds.setAttr((str(bake) + '.visibility'), False)

            for bake in settings.bakeSet:
                if settings.toolStates['bakeGroundPlane'] is True:
                    bbox = maya.cmds.exactWorldBoundingBox(bake)
                    bakeTx = export.getTransforms([
                        bake,
                    ])
                    groundPos = maya.cmds.getAttr(str(bakeTx[0]) + '.translate')[0]
                    maya.cmds.setAttr('sxGroundPlane.translateX', groundPos[0])
                    maya.cmds.setAttr('sxGroundPlane.translateY',
                    (bbox[1] - settings.toolStates['bakeGroundOffset']))
                    maya.cmds.setAttr('sxGroundPlane.translateZ', groundPos[2])

                maya.cmds.setAttr((str(bake) + '.visibility'), True)
                maya.cmds.arnoldRenderToTexture(
                    bake,
                    resolution=512,
                    shader='aiSXAO',
                    aa_samples=1,
                    normal_offset=0.001,
                    filter='closest',
                    folder=bakePath,
                    uv_set='uvAO')
                maya.cmds.setAttr((str(bake) + '.visibility'), False)

            for bake in settings.bakeSet:
                maya.cmds.setAttr((str(bake) + '.visibility'), True)

        if settings.toolStates['bakeGroundPlane'] is True:
            maya.cmds.delete('sxGroundPlane')

        # apply baked maps to occlusion layers
        for bake in settings.bakeSet:
            bakeFileName = bakePath + '/' + str(bake).split('|')[-1] + '.exr'
            maya.cmds.setAttr(
                'SXAOTexture.fileTextureName', bakeFileName, type='string')
            maya.cmds.setAttr('SXAOTexture.filterType', 0)
            maya.cmds.setAttr('SXAOTexture.aiFilter', 0)
            # maya.cmds.setAttr('SXAOTexture.hdrMapping', 'HDR_LINEAR_MAPPING')
            self.applyTexture('SXAOTexture', 'uvAO', False)

        # TODO: Fix HDR mapping, fix UV alpha seams

        maya.cmds.select(settings.bakeSet)
        sx.selectionManager()

    def applyTexture(self, texture, uvSetName, applyAlpha):
        colors = []
        color = []
        uCoords = []
        vCoords = []

        maya.cmds.polyUVSet(settings.shapeArray, currentUVSet=True, uvSet=uvSetName)
        components = maya.cmds.ls(
            maya.cmds.polyListComponentConversion(settings.shapeArray, tv=True), fl=True)

        for component in components:
            fvs = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(component, tvf=True), fl=True)
            uvs = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(fvs, tuv=True), fl=True)
            for uv in uvs:
                uvCoord = maya.cmds.polyEditUV(uv, query=True)
                colors.append(
                    maya.cmds.colorAtPoint(texture, o='RGBA', u=uvCoord[0], v=uvCoord[1]))
            for tmpColor in colors:
                if tmpColor[3] == 1:
                    color = tmpColor

            if applyAlpha is False:
                if 1 <= color[3] > 0:
                    maya.cmds.polyColorPerVertex(
                        component,
                        r=color[0] / color[3],
                        g=color[1] / color[3],
                        b=color[2] / color[3],
                        a=1)
                else:
                    maya.cmds.polyColorPerVertex(
                        component, r=color[0], g=color[1], b=color[2], a=1)
            else:
                if 1 <= color[3] > 0:
                    maya.cmds.polyColorPerVertex(
                        component,
                        r=color[0] / color[3],
                        g=color[1] / color[3],
                        b=color[2] / color[3],
                        a=color[3])
                else:
                    maya.cmds.polyColorPerVertex(
                        component, r=color[0], g=color[1], b=color[2], a=color[3])

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())
        layers.refreshLayerList()
        layers.refreshSelectedItem()

    def calculateCurvature(self, objects):
        for object in objects:
            selectionList = OM.MSelectionList()
            selectionList.add(object)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            vtxPoints = OM.MPointArray()
            vtxPoints = MFnMesh.getPoints(OM.MSpace.kWorld)
            numVtx = MFnMesh.numVertices

            vtxNormals = OM.MVectorArray()
            vtxColors = OM.MColorArray()
            vtxIds = OM.MIntArray()

            vtxNormals.setLength(numVtx)
            vtxColors.setLength(numVtx)
            vtxIds.setLength(numVtx)

            vtxIt = OM.MItMeshVertex(nodeDagPath)

            while not vtxIt.isDone():
                i = vtxIt.index()
                vtxIds[i] = vtxIt.index()
                vtxNormals[i] = vtxIt.getNormal()

                connectedVertices = OM.MIntArray()
                connectedVertices = vtxIt.getConnectedVertices()
                numConnected = len(connectedVertices)

                vtxCurvature = 0.0

                for e in range(0, numConnected):

                    edge = OM.MVector
                    edge = (vtxPoints[connectedVertices[e]] - vtxPoints[i])
                    angle = math.acos(vtxNormals[i].normal() * edge.normal())
                    curvature = (angle / math.pi - 0.5) / edge.length()
                    vtxCurvature += curvature

                vtxCurvature = (vtxCurvature / numConnected + 0.5)
                if vtxCurvature > 1.0:
                    vtxCurvature = 1.0
                outColor = maya.cmds.colorAtPoint(
                    'SXRamp', o='RGB', u=(0), v=(vtxCurvature))
                outAlpha = maya.cmds.colorAtPoint(
                    'SXAlphaRamp', o='A', u=(0), v=(vtxCurvature))

                vtxColors[i].r = outColor[0]
                vtxColors[i].g = outColor[1]
                vtxColors[i].b = outColor[2]
                vtxColors[i].a = outAlpha[0]

                vtxIt.next()

            MFnMesh.setVertexColors(vtxColors, vtxIds)

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())
        layers.refreshLayerList()
        layers.refreshSelectedItem()

    def applyMasterPalette(self, objects):
        for i in xrange(1, 6):
            targetLayers = settings.toolStates['paletteTarget'+str(i)]
            maya.cmds.palettePort('masterPalette', edit=True, scc=i-1)
            for layer in targetLayers:
                state = layers.verifyLayerState(layer)
                if ('(H)' in state) or ('(M)' in state) or ('(A)' in state):
                    maya.cmds.polyColorSet(
                        objects,
                        currentColorSet=True,
                        colorSet=layer)
                    maya.cmds.polyColorPerVertex(
                        objects,
                        r=maya.cmds.palettePort(
                        'masterPalette', query=True, rgb=True)[0],
                        g=maya.cmds.palettePort(
                        'masterPalette', query=True, rgb=True)[1],
                        b=maya.cmds.palettePort(
                        'masterPalette', query=True, rgb=True)[2])
        sx.updateSXTools()

    def gradientFill(self, axis):
        if len(settings.componentArray) > 0:
            components = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(settings.componentArray, tvf=True),
                fl=True)
            # tempFaceArray is constructed because
            # polyEvaluate doesn't work on face vertices
            tempFaceArray = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(settings.componentArray, tf=True),
                fl=True)
            maya.cmds.select(tempFaceArray)
            objectBounds = maya.cmds.polyEvaluate(bc=True, ae=True)
        else:
            components = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(settings.shapeArray, tv=True),
                fl=True)
            objectBounds = maya.cmds.polyEvaluate(settings.shapeArray, b=True, ae=True)

        objectBoundsXmin = objectBounds[0][0]
        objectBoundsXmax = objectBounds[0][1]
        objectBoundsYmin = objectBounds[1][0]
        objectBoundsYmax = objectBounds[1][1]
        objectBoundsZmin = objectBounds[2][0]
        objectBoundsZmax = objectBounds[2][1]

        if len(settings.componentArray) > 0:
            compPos = [float] * len(components)
            ratioRaw = [float] * len(components)
            ratio = [float] * len(components)
            compColor = [float] * len(components)
            compAlpha = [float] * len(components)

            for i in range(len(components)):
                compPos[i] = maya.cmds.xform(components[i], query=True, worldSpace=True, translation=True)            
                if axis == 1:
                    ratioRaw[i] = (compPos[i][0]-objectBoundsXmin)/(objectBoundsXmax-objectBoundsXmin)
                elif axis == 2:
                    ratioRaw[i] = (compPos[i][1]-objectBoundsYmin)/(objectBoundsYmax-objectBoundsYmin)
                elif axis == 3:
                    ratioRaw[i] = (compPos[i][2]-objectBoundsZmin)/(objectBoundsZmax-objectBoundsZmin)                
                ratio[i] = max(min(ratioRaw[i], 1), 0)
                compColor[i] = maya.cmds.colorAtPoint('SXRamp', o='RGB', u=(ratio[i]), v=(ratio[i]))
                compAlpha[i] = maya.cmds.colorAtPoint('SXAlphaRamp', o='A', u=(ratio[i]), v=(ratio[i]))[0]
                maya.cmds.polyColorPerVertex(components[i], rgb=compColor[i], a=compAlpha[i])
        else:
            for object in settings.objectArray:
                layer = layers.getSelectedLayer()

                selectionList = OM.MSelectionList()
                selectionList.add(object)
                nodeDagPath = OM.MDagPath()
                nodeDagPath = selectionList.getDagPath(0)
                MFnMesh = OM.MFnMesh(nodeDagPath)
                space = OM.MSpace.kWorld
                layerColors = OM.MColorArray()
                layerColors = MFnMesh.getFaceVertexColors(colorSet=layer)
                faceIds = OM.MIntArray()
                vtxIds = OM.MIntArray()
                mod = OM.MDGModifier()
                colorRep = MFnMesh.kRGBA

                lenSel = len(layerColors)

                faceIds.setLength(lenSel)
                vtxIds.setLength(lenSel)

                fvIt = OM.MItMeshFaceVertex(nodeDagPath)

                k = 0
                while not fvIt.isDone():
                    ratioRaw = None
                    ratio = None
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()
                    fvPos = fvIt.position(space)
                    if axis == 1:
                        ratioRaw = (fvPos[0]-objectBoundsXmin)/(objectBoundsXmax-objectBoundsXmin)
                    elif axis == 2:
                        ratioRaw = (fvPos[1]-objectBoundsYmin)/(objectBoundsYmax-objectBoundsYmin)
                    elif axis == 3:
                        ratioRaw = (fvPos[2]-objectBoundsZmin)/(objectBoundsZmax-objectBoundsZmin)
                    ratio = max(min(ratioRaw, 1), 0)
                    outColor = maya.cmds.colorAtPoint('SXRamp', o='RGB', u=(ratio), v=(ratio))
                    outAlpha = maya.cmds.colorAtPoint('SXAlphaRamp', o='A', u=(ratio), v=(ratio))
                    layerColors[k].r = outColor[0]
                    layerColors[k].g = outColor[1]
                    layerColors[k].b = outColor[2]
                    layerColors[k].a = outAlpha[0]
                    k += 1
                    fvIt.next()

                MFnMesh.setFaceVertexColors(layerColors, faceIds, vtxIds, mod, colorRep)

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())
        layers.refreshLayerList()
        layers.refreshSelectedItem()

    def colorFill(self, overwriteAlpha=False):
        alphaMax = settings.layerAlphaMax
        fillColor = settings.currentColor
        #maya.cmds.colorSliderGrp('sxApplyColor', query=True, rgbValue=True)

        if (len(settings.componentArray) > 0) and (overwriteAlpha is True):
            maya.cmds.polyColorPerVertex(
                settings.componentArray,
                r=fillColor[0],
                g=fillColor[1],
                b=fillColor[2],
                a=1,
                representation=4,
                cdo=True)
        elif (len(settings.componentArray) == 0) and (overwriteAlpha is True):
            maya.cmds.polyColorPerVertex(
                settings.shapeArray,
                r=fillColor[0],
                g=fillColor[1],
                b=fillColor[2],
                a=1,
                representation=4,
                cdo=True)            
        elif (len(settings.componentArray) > 0) and (settings.layerAlphaMax != 0):
            maya.cmds.polyColorPerVertex(
                settings.componentArray,
                r=fillColor[0],
                g=fillColor[1],
                b=fillColor[2],
                representation=3,
                cdo=True)
        elif (len(settings.componentArray) > 0) and (settings.layerAlphaMax == 0):
            maya.cmds.polyColorPerVertex(
                settings.componentArray,
                r=fillColor[0],
                g=fillColor[1],
                b=fillColor[2],
                a=1,
                representation=4,
                cdo=True)
        elif (len(settings.componentArray) == 0) and (settings.layerAlphaMax != 0):
            maya.cmds.polyColorPerVertex(
                settings.shapeArray,
                r=fillColor[0],
                g=fillColor[1],
                b=fillColor[2],
                representation=3,
                cdo=True)
        else:
            maya.cmds.polyColorPerVertex(
                settings.shapeArray,
                r=fillColor[0],
                g=fillColor[1],
                b=fillColor[2],
                a=1,
                representation=4,
                cdo=True)

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())
        layers.refreshLayerList()
        layers.refreshSelectedItem()

    def colorNoise(self, objects):
        for object in objects:
            mono = settings.toolStates['noiseMonochrome']
            value = settings.toolStates['noiseValue']
            layer = layers.getSelectedLayer()

            selectionList = OM.MSelectionList()
            selectionList.add(object)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            vtxColors = OM.MColorArray()
            vtxColors = MFnMesh.getVertexColors(colorSet=layer)
            vtxIds = OM.MIntArray()

            lenSel = len(vtxColors)
            vtxIds.setLength(lenSel)

            vtxIt = OM.MItMeshVertex(nodeDagPath)

            while not vtxIt.isDone():
                i = vtxIt.index()
                vtxIds[i] = vtxIt.index()

                if mono is True:
                    randomOffset = random.uniform(-value, value)
                    vtxColors[i].r += randomOffset
                    vtxColors[i].g += randomOffset
                    vtxColors[i].b += randomOffset
                else:
                    vtxColors[i].r += random.uniform(-value, value)
                    vtxColors[i].g += random.uniform(-value, value)
                    vtxColors[i].b += random.uniform(-value, value)

                vtxIt.next()

            MFnMesh.setVertexColors(vtxColors, vtxIds)

    def remapRamp(self, objects):
        for object in objects:
            layer = layers.getSelectedLayer()

            selectionList = OM.MSelectionList()
            selectionList.add(object)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerColors = OM.MColorArray()
            layerColors = MFnMesh.getFaceVertexColors(colorSet=layer)

            fvCol = OM.MColor()
            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            mod = OM.MDGModifier()
            colorRep = MFnMesh.kRGBA

            lenSel = len(layerColors)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()
                fvCol = layerColors[k]
                luminance = (fvCol.r + fvCol.r + fvCol.b + fvCol.g + fvCol.g + fvCol.g) / 6
                outColor = maya.cmds.colorAtPoint(
                    'SXRamp', o='RGB', u=luminance, v=luminance)
                outAlpha = maya.cmds.colorAtPoint(
                    'SXAlphaRamp', o='A', u=luminance, v=luminance)
                layerColors[k].r = outColor[0]
                layerColors[k].g = outColor[1]
                layerColors[k].b = outColor[2]
                layerColors[k].a = outAlpha[0]
                k += 1
                fvIt.next()

            MFnMesh.setFaceVertexColors(layerColors, faceIds, vtxIds, mod, colorRep)

    def swapLayers(self, shapes):
        refLayers = layers.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())

        layerA = maya.cmds.textField('layerA', query=True, text=True)
        layerB = maya.cmds.textField('layerB', query=True, text=True)

        for shape in shapes:
#            selected = str(settings.shapeArray[len(settings.shapeArray)-1])

            if (layerA in refLayers) and (layerB in refLayers):
                attrA = '.' + layerA + 'BlendMode'
                modeA = maya.cmds.getAttr(str(shape) + attrA)
                attrB = '.' + layerB + 'BlendMode'
                modeB = maya.cmds.getAttr(str(shape) + attrB)

                selectionList = OM.MSelectionList()
                selectionList.add(shape)
                nodeDagPath = OM.MDagPath()
                nodeDagPath = selectionList.getDagPath(0)
                MFnMesh = OM.MFnMesh(nodeDagPath)

                layerAColors = OM.MColorArray()
                layerAColors = MFnMesh.getFaceVertexColors(colorSet=layerA)
                layerBColors = OM.MColorArray()
                layerBColors = MFnMesh.getFaceVertexColors(colorSet=layerB)
                layerTempColors = OM.MColorArray()
                layerTempColors = layerBColors

                faceIds = OM.MIntArray()
                vtxIds = OM.MIntArray()

                lenSel = len(layerAColors)

                faceIds.setLength(lenSel)
                vtxIds.setLength(lenSel)

                fvIt = OM.MItMeshFaceVertex(nodeDagPath)

                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()
                    k += 1
                    fvIt.next()

                maya.cmds.polyColorSet(currentColorSet=True, colorSet=layerB)
                MFnMesh.setFaceVertexColors(layerAColors, faceIds, vtxIds)
                maya.cmds.polyColorSet(currentColorSet=True, colorSet=layerA)
                MFnMesh.setFaceVertexColors(layerTempColors, faceIds, vtxIds)

                maya.cmds.setAttr(str(shape) + attrA, modeB)
                maya.cmds.setAttr(str(shape) + attrB, modeA)

                self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                        layers.getSelectedLayer())
                layers.refreshLayerList()
                layers.refreshSelectedItem()
                maya.cmds.shaderfx(sfxnode='SXShader', update=True)
            else:
                print('SXTools Error: Invalid layers on ' + str(shape))

    def copyLayer(self, objects):
        refLayers = layers.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())

        layerA = maya.cmds.textField('layersrc', query=True, text=True)
        layerB = maya.cmds.textField('layertgt', query=True, text=True)

        if (layerA in refLayers) and (layerB in refLayers):
            for idx, obj in enumerate(objects):
                selected = str(settings.shapeArray[idx])
                attrA = '.' + layerA + 'BlendMode'
                modeA = maya.cmds.getAttr(selected + attrA)
                attrB = '.' + layerB + 'BlendMode'

                selectionList = OM.MSelectionList()
                selectionList.add(obj)
                nodeDagPath = OM.MDagPath()
                nodeDagPath = selectionList.getDagPath(0)
                MFnMesh = OM.MFnMesh(nodeDagPath)

                layerAColors = OM.MColorArray()
                layerAColors = MFnMesh.getFaceVertexColors(colorSet=layerA)

                faceIds = OM.MIntArray()
                vtxIds = OM.MIntArray()

                lenSel = len(layerAColors)

                faceIds.setLength(lenSel)
                vtxIds.setLength(lenSel)

                fvIt = OM.MItMeshFaceVertex(nodeDagPath)

                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()
                    k += 1
                    fvIt.next()

                maya.cmds.polyColorSet(currentColorSet=True, colorSet=layerB)
                MFnMesh.setFaceVertexColors(layerAColors, faceIds, vtxIds)

                maya.cmds.setAttr(selected + attrB, modeA)
        else:
            print('SXTools Error: Invalid layers!')

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())
        layers.refreshLayerList()
        layers.refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def verifyShadingMode(self):
        if len(settings.shapeArray) > 0:
            object = settings.shapeArray[len(settings.shapeArray)-1]
            mode = int(maya.cmds.getAttr(object + '.shadingMode') + 1)

            objectLabel = 'Selected Objects: ' + str(len(settings.shapeArray))
            maya.cmds.frameLayout('layerFrame', edit=True, label=objectLabel)
            maya.cmds.radioButtonGrp('shadingButtons', edit=True, select=mode)
            return mode

    def setShadingMode(self, mode):
        for shape in settings.shapeArray:
            maya.cmds.setAttr(str(shape) + '.shadingMode', mode)
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def checkHistory(self, objList):
        history = False
        for obj in objList:
            histList = maya.cmds.listHistory(obj)
            objName = str(obj).rstrip('0123456789')
            if '|' in objName:
                objName = objName.rsplit('|', 1)[1]

            for hist in reversed(histList):
                if objName in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'assetsLayer' in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'sxCrease' in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'set' in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'groupId' in str(hist):
                    histList.remove(hist)

            if len(histList) > 0:
                history = True

        if history is True:
            print('SX Tools: History found: ' + str(histList))
            maya.cmds.columnLayout(
                'warningLayout', parent='canvas', rowSpacing=5, adjustableColumn=True)
            maya.cmds.text(
                label='WARNING: Objects with construction history!',
                backgroundColor=(0.35, 0.1, 0),
                ww=True)
            maya.cmds.button(
                label='Delete History',
                command='maya.cmds.delete(sxtools.settings.objectArray, ch=True)\n'
                                'sxtools.sx.updateSXTools()')

    # Called from a button the tool UI
    # that clears either the selected layer
    # or the selected components in a layer
    def clearSelector(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)
        if shift is True:
            layers.clearAllLayers()
        elif shift is False:
            if len(settings.componentArray) > 0:
                layers.clearSelectedComponents(layers.getSelectedLayer())
            else:
                layers.clearSelectedLayer(settings.shapeArray, layers.getSelectedLayer())

    def setLayerOpacity(self):
        alphaMax = settings.layerAlphaMax

        for shape in settings.shapeArray:
            layer = layers.getSelectedLayer()
            sliderAlpha = maya.cmds.floatSlider(
                'layerOpacitySlider', query=True, value=True)

            selectionList = OM.MSelectionList()
            selectionList.add(shape)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerColorArray = OM.MColorArray()
            layerColorArray = MFnMesh.getFaceVertexColors(colorSet=layer)
            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            testColor = OM.MColor()

            lenSel = len(layerColorArray)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()
                testColor = fvIt.getColor(layer)
                if (alphaMax == 0) and (testColor.r > 0 or testColor.g > 0 or testColor.b > 0):
                    layerColorArray[k].a = sliderAlpha
                elif testColor.a > 0 or testColor.r > 0 or testColor.g > 0 or testColor.b > 0:
                    layerColorArray[k].a = layerColorArray[k].a / alphaMax * sliderAlpha
                k += 1
                fvIt.next()

            MFnMesh.setFaceVertexColors(layerColorArray, faceIds, vtxIds)

            if (str(layer) == 'layer1') and (sliderAlpha < 1):
                maya.cmds.setAttr(str(shape) + '.transparency', 1)
                if alphaMax == 1:
                    maya.cmds.shaderfx(
                        sfxnode='SXShader',
                        makeConnection=(settings.nodeDict['transparencyComp'], 0, settings.nodeDict['SXShader'], 0))
                maya.cmds.shaderfx(sfxnode='SXShader', update=True)
            elif (str(layer) == 'layer1') and (sliderAlpha == 1):
                maya.cmds.setAttr(str(shape) + '.transparency', 0)
                if alphaMax < 1:
                    maya.cmds.shaderfx(
                        sfxnode='SXShader',
                        breakConnection=(settings.nodeDict['transparencyComp'], 0, settings.nodeDict['SXShader'], 0))
                maya.cmds.shaderfx(sfxnode='SXShader', update=True)

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())

    def getLayerMask(self):
        maskList = []

        vertFaceList = maya.cmds.ls(
            maya.cmds.polyListComponentConversion(settings.shapeArray, tvf=True), fl=True)

        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift is True:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(vertFace, query=True, a=True)[0] == 0:
                    maskList.append(vertFace)
        elif shift is False:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(vertFace, query=True, a=True)[0] > 0:
                    maskList.append(vertFace)

        if len(maskList) == 0:
            print('SX Tools: No layer mask found')
            return settings.selectionArray

        return maskList

    def getLayerPaletteOpacity(self, object, layer):
        selectionList = OM.MSelectionList()
        selectionList.add(object)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColorArray = OM.MColorArray()
        layerColorArray = MFnMesh.getFaceVertexColors(colorSet=layer)
        black = OM.MColor()
        black = (0, 0, 0, 1)

        layerPaletteArray = OM.MColorArray()
        layerPaletteArray.setLength(8)
        for k in range(0, 8):
            layerPaletteArray[k] = black

        n = 0
        alphaMax = 0
        for k in range(len(layerColorArray)):
            match = False
            for p in range(0, 8):
                if ((layerColorArray[k].r == layerPaletteArray[p].r) and
                                (layerColorArray[k].g == layerPaletteArray[p].g) and
                                (layerColorArray[k].b == layerPaletteArray[p].b)):
                    match = True

            if (match is False) and (n < 8):
                layerPaletteArray[n] = layerColorArray[k]
                n += 1

            if layerColorArray[k].a > alphaMax:
                alphaMax = layerColorArray[k].a

        if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
            maya.cmds.floatSlider('layerOpacitySlider', edit=True, value=alphaMax)
            settings.layerAlphaMax = alphaMax

        for k in range(0, 8):
            maya.cmds.palettePort(
                'layerPalette',
                edit=True,
                rgb=(k, layerPaletteArray[k].r, layerPaletteArray[k].g,
                                    layerPaletteArray[k].b))
            maya.cmds.palettePort('layerPalette', edit=True, redraw=True)

        if 'layer' not in layer:
            if maya.cmds.text('layerOpacityLabel', exists=True):
                maya.cmds.text('layerOpacityLabel', edit=True, enable=False)
            if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
                maya.cmds.floatSlider('layerOpacitySlider', edit=True, enable=False)
            return
        else:
            if maya.cmds.text('layerOpacityLabel', exists=True):
                maya.cmds.text('layerOpacityLabel', edit=True, enable=True)
            if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
                maya.cmds.floatSlider('layerOpacitySlider', edit=True, enable=True)

    def setPaintColor(self):
        settings.currentColor = maya.cmds.palettePort(
            'layerPalette', query=True, rgb=True)
        maya.cmds.colorSliderGrp(
            'sxApplyColor', edit=True, rgbValue=settings.currentColor)
        if maya.cmds.artAttrPaintVertexCtx(
                'artAttrColorPerVertexContext', exists=True):
            numChannels = maya.cmds.artAttrPaintVertexCtx(
                'artAttrColorPerVertexContext', query=True, paintNumChannels=True)
            if numChannels == 3:
                maya.cmds.artAttrPaintVertexCtx(
                    'artAttrColorPerVertexContext',
                    edit=True,
                    usepressure=False,
                    colorRGBValue=[
                        settings.currentColor[0], settings.currentColor[1],
                        settings.currentColor[2]
                    ])
            elif numChannels == 4:
                maya.cmds.artAttrPaintVertexCtx(
                    'artAttrColorPerVertexContext',
                    edit=True,
                    usepressure=False,
                    colorRGBAValue=[
                        settings.currentColor[0], settings.currentColor[1],
                        settings.currentColor[2], 1
                    ])

    def setApplyColor(self):
        settings.toolStates['recentPaletteIndex'] = maya.cmds.palettePort(
            'recentPalette', query=True, scc=True)
        settings.currentColor = maya.cmds.palettePort(
            'recentPalette', query=True, rgb=True)
        maya.cmds.colorSliderGrp(
            'sxApplyColor', edit=True, rgbValue=settings.currentColor)

    def updateRecentPalette(self):
        addedColor = maya.cmds.colorSliderGrp(
            'sxApplyColor', query=True, rgbValue=True)
        swapColorArray = []

        for k in range(0, 7):
            maya.cmds.palettePort('recentPalette', edit=True, scc=k)
            swapColorArray.append(
                maya.cmds.palettePort('recentPalette', query=True, rgb=True))

        if (addedColor in swapColorArray) is False:
            for k in range(7, 0, -1):
                maya.cmds.palettePort(
                    'recentPalette',
                    edit=True,
                    rgb=(k, swapColorArray[k - 1][0], swapColorArray[k - 1][1],
                                        swapColorArray[k - 1][2]))

            maya.cmds.palettePort('recentPalette', edit=True, scc=0)
            maya.cmds.palettePort(
                'recentPalette',
                edit=True,
                rgb=(0, addedColor[0], addedColor[1], addedColor[2]))
            maya.cmds.palettePort('recentPalette', edit=True, redraw=True)
        else:
            idx = swapColorArray.index(addedColor)
            maya.cmds.palettePort('recentPalette', edit=True, scc=idx)

        self.storePalette('recentPalette', settings.paletteDict, 'SXToolsRecentPalette')

    def storePalette(self, paletteUI, targetDict, preset):
        currentCell = maya.cmds.palettePort(paletteUI, query=True, scc=True)
        paletteLength = maya.cmds.palettePort(
            paletteUI, query=True, actualTotal=True)
        paletteArray = []
        for i in range(0, paletteLength):
            maya.cmds.palettePort(paletteUI, edit=True, scc=i)
            paletteArray.append(maya.cmds.palettePort(paletteUI, query=True, rgb=True))

        targetDict[preset] = paletteArray

        maya.cmds.palettePort(paletteUI, edit=True, scc=currentCell)

    def getPalette(self, paletteUI, targetDict, preset):
        if preset in targetDict:
            presetColors = targetDict[preset]

            for idx, color in enumerate(presetColors):
                maya.cmds.palettePort(
                    paletteUI, edit=True, rgb=(idx, color[0], color[1], color[2]))
            maya.cmds.palettePort(paletteUI, edit=True, redraw=True)

    def deletePalette(self, targetDict, preset):
        del targetDict[preset]
        if settings.toolStates['palettePreset'] == preset:
            settings.toolStates['palettePreset'] = None

    def saveMasterPalette(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift is True:
            preset = maya.cmds.optionMenu('masterPalettes', query=True, value=True)
            if preset is not None:
                self.deletePalette(settings.masterPaletteDict, preset)
                maya.cmds.deleteUI(preset)
                settings.savePreferences()
                self.getMasterPaletteItem()
            else:
                print('SX Tools Error: No preset to delete!')

        elif shift is False:
            itemList = maya.cmds.optionMenu('masterPalettes', query=True, ils=True)
            preset = maya.cmds.textField('savePaletteName', query=True, text=True).replace(' ', '_')
            if (len(preset) > 0) and ((itemList is None) or (preset not in itemList)):
                settings.toolStates['palettePreset'] = preset
                self.storePalette('masterPalette', settings.masterPaletteDict, preset)
                maya.cmds.menuItem(preset, label=preset, parent='masterPalettes')
                itemList = maya.cmds.optionMenu('masterPalettes', query=True, ils=True)
                idx = itemList.index(preset) + 1
                maya.cmds.optionMenu('masterPalettes', edit=True, select=idx)
                settings.savePreferences()
            else:
                print('SX Tools Error: Invalid preset name!')

    def getMasterPaletteItem(self):
        if len(settings.masterPaletteDict) > 0:
            preset = maya.cmds.optionMenu('masterPalettes', query=True, value=True)
            self.getPalette('masterPalette', settings.masterPaletteDict, preset)
            settings.toolStates['palettePreset'] = preset
            self.storePalette('masterPalette', settings.paletteDict, 'SXToolsMasterPalette')

    def checkTarget(self, targets, index):
        refLayers = layers.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())

        splitList = []
        targetList = []
        splitList = targets.split(',')
        for item in splitList:
            targetList.append(item.strip())

        if set(targetList).issubset(refLayers) is False:
            print('SX Tools Error: Invalid layer target!')
            maya.cmds.textField('masterTarget'+str(index), edit=True, text=''.join(settings.toolStates['paletteTarget'+str(index)]))
            return
        settings.toolStates['paletteTarget'+str(index)] = targetList

    def gradientToolManager(self, mode, group=1):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if mode == 'load':
            self.clearRamp('SXRamp')
            name = maya.cmds.optionMenu('rampPresets', query=True, value=True)
            maya.cmds.nodePreset(load=('SXRamp', name))
        elif mode == 'preset' and shift is True:
            presetNameArray = maya.cmds.nodePreset(list='SXRamp')
            if len(presetNameArray) > 0:
                maya.cmds.nodePreset(delete=('SXRamp', maya.cmds.optionMenu(
                    'rampPresets', query=True, value=True)))
            elif len(presetNameArray) == 0:
                print('SXTools: Preset list empty!')
        elif mode == 'preset' and shift is False:
            name = maya.cmds.textField('presetName', query=True, text=True).replace(' ', '_')
            if len(name) > 0:
                maya.cmds.nodePreset(save=('SXRamp', name))
            elif len(name) == 0:
                print('SXTools: Invalid preset name!')
        elif group == 1:
            if mode == 2:
                settings.projectSettings['SXToolsGradientDirection'] = 5
                self.calculateCurvature(settings.objectArray)
            elif mode == 1:
                settings.projectSettings['SXToolsGradientDirection'] = 4
                self.remapRamp(settings.objectArray)
        else:
            settings.projectSettings['SXToolsGradientDirection'] = mode
            self.gradientFill(mode)

    def clearRamp(self, rampName):
        indexList = maya.cmds.getAttr(
            rampName + '.colorEntryList', multiIndices=True)
        for index in indexList:
            index = str(index).split('L')[-1]
            maya.cmds.removeMultiInstance(rampName + '.colorEntryList[' + index + ']')

    def refreshMasterPaletteMenu(self):
        paletteNameArray = settings.masterPaletteDict.keys()
        if paletteNameArray != 0:
            for paletteName in paletteNameArray:
                maya.cmds.menuItem(paletteName, label=paletteName, parent='masterPalettes')

            if ('palettePreset' in settings.toolStates) and (
                    settings.toolStates['palettePreset'] is not None):
                itemList = maya.cmds.optionMenu('masterPalettes', query=True, ils=True)
                idx = itemList.index(settings.toolStates['palettePreset']) + 1
                maya.cmds.optionMenu('masterPalettes', edit=True, select=idx)

    def refreshRampMenu(self):
        presetNameArray = maya.cmds.nodePreset(list='SXRamp')
        if presetNameArray != 0:
            for presetName in presetNameArray:
                maya.cmds.menuItem(label=presetName, parent='rampPresets')

    def setLayerBlendMode(self):
        mode = maya.cmds.optionMenu('layerBlendModes', query=True, select=True) - 1
        attr = '.' + layers.getSelectedLayer() + 'BlendMode'
        for shape in settings.shapeArray:
            maya.cmds.setAttr(str(shape) + attr, mode)
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)
        layers.getSelectedLayer()

    def swapLayerSets(self, objects, targetSet):
        for object in objects:
            attr = '.activeLayerSet'
            currentMode = int(maya.cmds.getAttr(str(object) + attr))
            # Create color sets
            refLayers = layers.sortLayers(settings.projectSettings['SXToolsRefLayers'].keys())
            for layer in refLayers:
                oldColors = str(layer) + '_var' + str(currentMode)
                self.copyFaceVertexColors([object, ], layer, oldColors)
                newColors = str(layer) + '_var' + str(targetSet)
                self.copyFaceVertexColors([object, ], newColors, layer)

            maya.cmds.setAttr(object + attr, targetSet)
            maya.cmds.polyColorSet(object, currentColorSet=True, colorSet='layer1')

        self.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                layers.getSelectedLayer())
        layers.refreshLayerList()
        layers.refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def copyFaceVertexColors(self, objects, layerA, layerB):
        maya.cmds.polyColorSet(objects, currentColorSet=True, colorSet=layerB)
        for object in objects:
            selectionList = OM.MSelectionList()
            selectionList.add(object)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerAColors = OM.MColorArray()
            layerAColors = MFnMesh.getFaceVertexColors(colorSet=layerA)

            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            lenSel = len(layerAColors)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()
                k += 1
                fvIt.next()

            MFnMesh.setFaceVertexColors(layerAColors, faceIds, vtxIds)

class LayerManagement(object):
    def __init__(self):
        return None

    def mergeLayers(self, object, sourceLayer, targetLayer, up):
        if up is True:
            target = targetLayer
        else:
            target = sourceLayer
        refLayers = self.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())

        selected = str(object)
        attr = '.' + str(self.getSelectedLayer()) + 'BlendMode'
        mode = int(maya.cmds.getAttr(selected + attr))

        # NOTE: polyBlendColor is used to copy existing color sets
        # to new list positions because Maya's color set copy function is bugged.

        if mode == 0:
            maya.cmds.polyBlendColor(
                selected,
                bcn=str(targetLayer),
                src=str(sourceLayer),
                dst=str(target),
                bfn=0,
                ch=False)
        else:
            selectionList = OM.MSelectionList()
            selectionList.add(object)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            sourceLayerColorArray = OM.MColorArray()
            targetLayerColorArray = OM.MColorArray()
            sourceLayerColorArray = MFnMesh.getFaceVertexColors(colorSet=sourceLayer)
            targetLayerColorArray = MFnMesh.getFaceVertexColors(colorSet=targetLayer)
            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            lenSel = len(sourceLayerColorArray)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            if mode == 1:
                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()

                    targetLayerColorArray[k].r += sourceLayerColorArray[
                        k].r * sourceLayerColorArray[k].a
                    targetLayerColorArray[k].g += sourceLayerColorArray[
                        k].g * sourceLayerColorArray[k].a
                    targetLayerColorArray[k].b += sourceLayerColorArray[
                        k].b * sourceLayerColorArray[k].a
                    targetLayerColorArray[k].a += sourceLayerColorArray[k].a
                    k += 1
                    fvIt.next()
            elif mode == 2:
                # layer2 lerp with white using (1-alpha), multiply with layer1
                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()

                    sourceLayerColorArray[k].r = (
                        (sourceLayerColorArray[k].r * sourceLayerColorArray[k].a) +
                        (1.0 * (1 - sourceLayerColorArray[k].a)))
                    sourceLayerColorArray[k].g = (
                        (sourceLayerColorArray[k].g * sourceLayerColorArray[k].a) +
                        (1.0 * (1 - sourceLayerColorArray[k].a)))
                    sourceLayerColorArray[k].b = (
                        (sourceLayerColorArray[k].b * sourceLayerColorArray[k].a) +
                        (1.0 * (1 - sourceLayerColorArray[k].a)))

                    targetLayerColorArray[k].r = sourceLayerColorArray[
                        k].r * targetLayerColorArray[k].r
                    targetLayerColorArray[k].g = sourceLayerColorArray[
                        k].g * targetLayerColorArray[k].g
                    targetLayerColorArray[k].b = sourceLayerColorArray[
                        k].b * targetLayerColorArray[k].b
                    k += 1
                    fvIt.next()
            else:
                print('SX Tools Error: Invalid blend mode')
                return

            maya.cmds.polyColorSet(
                selected, currentColorSet=True, colorSet=str(target))
            MFnMesh.setFaceVertexColors(targetLayerColorArray, faceIds, vtxIds)

        if up is True:
            maya.cmds.polyColorSet(selected, delete=True, colorSet=str(sourceLayer))
        else:
            maya.cmds.polyColorSet(selected, delete=True, colorSet=str(targetLayer))            

    # If mesh color sets don't match the reference layers.
    # Sorts the existing color sets to the correct order,
    # and fills the missing slots with default layers.
    def patchLayers(self, objects):
        noColorSetObject = []

        refLayers = self.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())

        for object in objects:
            currentColorSets = maya.cmds.polyColorSet(
                object, query=True, allColorSets=True)
            if currentColorSets is not None:
                for layer in refLayers:
                    maya.cmds.select(object)
                    found = False

                    for colorSet in currentColorSets:
                        if colorSet == layer:
                            # NOTE: polyBlendColor is used to copy existing color sets
                            # to new list positions
                            # because Maya's color set copy function is broken,
                            # and either generates empty color sets,
                            # or copies from wrong indices.
                            maya.cmds.polyColorSet(
                                object,
                                rename=True,
                                colorSet=str(colorSet),
                                newColorSet='tempColorSet')
                            maya.cmds.polyColorSet(
                                object,
                                create=True,
                                clamped=True,
                                representation='RGBA',
                                colorSet=str(layer))
                            maya.cmds.polyBlendColor(
                                object,
                                bcn=str(layer),
                                src='tempColorSet',
                                dst=str(layer),
                                bfn=0,
                                ch=False)
                            maya.cmds.polyColorSet(object, delete=True, colorSet='tempColorSet')
                            found = True

                    if found is False:
                        maya.cmds.polyColorSet(
                            object,
                            create=True,
                            clamped=True,
                            representation='RGBA',
                            colorSet=str(layer))
                        self.clearSelectedLayer([
                            object,
                        ], layer)

                maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=refLayers[0])
                maya.cmds.sets(object, e=True, forceElement='SXShaderSG')
            else:
                noColorSetObject.append(object)

        if len(noColorSetObject) > 0:
            self.resetLayers(noColorSetObject)

        maya.cmds.select(settings.selectionArray)
        sx.selectionManager()

    # Resulting blended layer is set to Alpha blending mode
    def mergeLayerDirection(self, up):
        sourceLayer = self.getSelectedLayer()
        if len(settings.shapeArray) > 1:
            print('SX Tools: Merge Layer requires a single object')
            return
        elif str(sourceLayer) == 'layer1' and up is True:
            print('SX Tools Error: Cannot merge layer1')
            return
        elif str(sourceLayer) == 'layer'+str(settings.projectSettings['SXToolsLayerCount']) and up is False:
            print('SX Tools Error: Cannot merge ' + 'layer'+str(settings.projectSettings['SXToolsLayerCount']))
            return
        elif (
            (str(sourceLayer) == 'occlusion') or (str(sourceLayer) == 'specular') or
            (str(sourceLayer) == 'transmission') or (str(sourceLayer) == 'emission')):
            print('SX Tools Error: Cannot merge material channels')
            return

        layerIndex = settings.projectSettings['SXToolsRefIndices'][sourceLayer]
        if up is True:
            targetLayer = settings.projectSettings['SXToolsRefNames'][layerIndex-1]
        else:
            sourceLayer = settings.projectSettings['SXToolsRefNames'][layerIndex+1]
            targetLayer = settings.projectSettings['SXToolsRefNames'][layerIndex]
        self.mergeLayers(settings.shapeArray[len(settings.shapeArray)-1], sourceLayer, targetLayer, up)
        self.patchLayers(
            [settings.shapeArray[len(settings.shapeArray)-1]], )
        if up is True:
            maya.cmds.polyColorSet(currentColorSet=True, colorSet=str(targetLayer))
        else:
            maya.cmds.polyColorSet(currentColorSet=True, colorSet=str(sourceLayer))
        self.refreshLayerList()
        self.refreshSelectedItem()

    # IF mesh has no color sets at all,
    # or non-matching color set names.
    def resetLayers(self, objects):
        for object in objects:
            # Remove existing color sets, if any
            colorSets = maya.cmds.polyColorSet(object, query=True, allColorSets=True)
            if colorSets is not None:
                for colorSet in colorSets:
                    maya.cmds.polyColorSet(object, delete=True, colorSet=colorSet)

        # Create color sets
        refLayers = self.sortLayers(
                settings.projectSettings['SXToolsRefLayers'].keys())
        for layer in refLayers:
            maya.cmds.polyColorSet(
                objects,
                create=True,
                clamped=True,
                representation='RGBA',
                colorSet=str(layer))
            self.clearSelectedLayer(objects, layer)
            # maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=str(layer))

        maya.cmds.polyColorSet(object, currentColorSet=True, colorSet='layer1')
        maya.cmds.sets(object, e=True, forceElement='SXShaderSG')

    def getLayerSet(self, object):
        values = []
        var = 0

        # Find current index
        colorSets = maya.cmds.polyColorSet(object, query=True, allColorSets=True)
        for colorSet in colorSets:
            if '_var' in str(colorSet):
                values.append(str(colorSet).split('_var')[1])

        if len(values) > 0:
            var = int(max(values))
        
        return var

    def addLayerSet(self, objects, varIdx):
        if varIdx == 9:
            print('SX Tools: Maximum layer sets added!')
            return

        refLayers = self.sortLayers(settings.projectSettings['SXToolsRefLayers'].keys())
        var = varIdx
        if var == 0:
            for layer in refLayers:
                layerName = str(layer) + '_var' + str(var)
                maya.cmds.polyColorSet(objects, copy=True,
                colorSet=layer, newColorSet=layerName)
                tools.copyFaceVertexColors(objects, layer, layerName)
            var += 1
            for layer in refLayers:
                layerName = str(layer) + '_var' + str(var)
                maya.cmds.polyColorSet(objects, copy=True,
                colorSet=layer, newColorSet=layerName)
                tools.copyFaceVertexColors(objects, layer, layerName)
        else:
            var += 1
            for layer in refLayers:
                layerName = str(layer) + '_var' + str(var)
                maya.cmds.polyColorSet(objects, copy=True,
                colorSet=layer, newColorSet=layerName)
                tools.copyFaceVertexColors(objects, layer, layerName)    

        maya.cmds.polyColorSet(objects, currentColorSet=True, colorSet='layer1')

    def clearSelectedLayer(self, objects, layer):
        maya.cmds.polyColorSet(objects, currentColorSet=True, colorSet=layer)
        color = settings.projectSettings['SXToolsRefLayers'][layer]
        maya.cmds.polyColorPerVertex(
            objects,
            r=color[0],
            g=color[1],
            b=color[2],
            a=color[3],
            representation=4,
            cdo=True)
        attr = '.' + str(layer) + 'BlendMode'
        for object in objects:
            maya.cmds.setAttr(str(object) + attr, 0)
        if maya.cmds.objExists('SXShader'):
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def clearSelectedComponents(self, layer):
        object = settings.shapeArray[len(settings.shapeArray)-1]
        maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=layer)

        color = settings.projectSettings['SXToolsRefLayers'][layer]
        maya.cmds.polyColorPerVertex(
            r=color[0], g=color[1], b=color[2], a=color[3], representation=4, cdo=True)
        attr = '.' + str(layer) + 'BlendMode'
        maya.cmds.setAttr(str(object) + attr, 0)
        if maya.cmds.objExists('SXShader'):
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def clearAllLayers(self):
        refLayers = self.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())
        for layer in refLayers:
            self.clearSelectedLayer(settings.shapeArray, layer)

    # Called when the user double-clicks a layer in the tool UI
    def toggleLayer(self, layer):
        object = settings.shapeArray[len(settings.shapeArray)-1]
        checkState = maya.cmds.getAttr(str(object) + '.' + str(layer) + 'Visibility')
        for shape in settings.shapeArray:
            maya.cmds.setAttr(
                str(shape) + '.' + str(layer) + 'Visibility', not checkState)
        state = self.verifyLayerState(layer)
        layerIndex = int(
            maya.cmds.textScrollList('layerList', query=True, selectIndexedItem=True)[
                0])
        maya.cmds.textScrollList(
            'layerList', edit=True, removeIndexedItem=layerIndex)
        maya.cmds.textScrollList(
            'layerList', edit=True, appendPosition=(layerIndex, state))
        maya.cmds.textScrollList(
            'layerList', edit=True, selectIndexedItem=layerIndex)

    # Called when the user hides or shows all vertex color layers in the tool UI
    def toggleAllLayers(self):
        layers = self.sortLayers(settings.projectSettings['SXToolsRefLayers'].keys())
        for layer in layers:
            self.toggleLayer(layer)

        self.refreshLayerList()
        self.refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    # Updates the tool UI to highlight the current color set
    def setColorSet(self, highlightedLayer):
        maya.cmds.polyColorSet(
            settings.shapeArray, currentColorSet=True, colorSet=highlightedLayer)

    # This function populates the layer list in the tool UI.
    def refreshLayerList(self):
        if maya.cmds.textScrollList('layerList', exists=True):
            maya.cmds.textScrollList('layerList', edit=True, removeAll=True)

        layers = self.sortLayers(settings.projectSettings['SXToolsRefLayers'].keys())

        for layer in layers:
            state = self.verifyLayerState(layer)
            maya.cmds.textScrollList(
                'layerList',
                edit=True,
                append=state,
                numberOfRows=(settings.projectSettings['SXToolsLayerCount'] +
                                                                        settings.projectSettings['SXToolsChannelCount']),
                selectCommand=(
                    "sxtools.layers.setColorSet(sxtools.layers.getSelectedLayer())\n"
                    "sxtools.tools.getLayerPaletteOpacity(sxtools.settings.shapeArray[len(sxtools.settings.shapeArray)-1], sxtools.layers.getSelectedLayer())\n"
                    "maya.cmds.text( 'layerOpacityLabel', edit=True, label=str(sxtools.layers.getSelectedLayer())+' opacity:' )\n"
                    "maya.cmds.text( 'layerColorLabel', edit=True, label=str(sxtools.layers.getSelectedLayer())+' colors:' )"
                ),
                doubleClickCommand=(
                    "sxtools.layers.toggleLayer(sxtools.layers.getSelectedLayer())\n"
                    "maya.cmds.shaderfx(sfxnode='SXShader', update=True)"))

    def refreshSelectedItem(self):
        selectedColorSet = str(
            maya.cmds.polyColorSet(
                settings.shapeArray[len(settings.shapeArray)-1],
                query=True,
                currentColorSet=True)[0])
        if selectedColorSet not in settings.projectSettings['SXToolsRefLayers'].keys():
            maya.cmds.polyColorSet(settings.shapeArray, edit=True, currentColorSet=True, colorSet='layer1')
            selectedColorSet = 'layer1'
        maya.cmds.textScrollList(
            'layerList',
            edit=True,
            selectIndexedItem=settings.projectSettings['SXToolsRefIndices'][
                selectedColorSet])

    def sortLayers(self, layers):
        sortedLayers = []

        if layers is not None:
            layerCount = len(layers)
            for ref in settings.refArray:
                if ref in layers:
                    sortedLayers.append(ref)

        return sortedLayers

    def verifyLayerState(self, layer):
        object = settings.shapeArray[len(settings.shapeArray)-1]
        selectionList = OM.MSelectionList()
        selectionList.add(settings.shapeArray[len(settings.shapeArray)-1])
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColors = OM.MColorArray()
        layerColors = MFnMesh.getFaceVertexColors(colorSet=layer)

        # States: visibility, mask, adjustment
        state = [False, False, False]
        state[0] = bool(maya.cmds.getAttr(str(object) + '.' + str(layer) + 'Visibility'))

        for k in range(len(layerColors)):
            if (layerColors[k].a > 0 and
                            layerColors[k].a < settings.projectSettings['SXToolsAlphaTolerance']):
                state[2] = True
            elif (
                    layerColors[k].a >= settings.projectSettings['SXToolsAlphaTolerance'] and
                    layerColors[k].a <= 1):
                state[1] = True

        if state[0] is False:
            hidden = '(H)'
        else:
            hidden = ''
        if state[1] is True:
            mask = '(M)'
        else:
            mask = ''
        if state[2] is True:
            adj = '(A)'
        else:
            adj = ''

        itemString = layer + '\t' + hidden + mask + adj
        return itemString

    # Maps the selected list item in the layerlist UI
    # to the parameters of the pre-vis material
    # and object colorsets
    def getSelectedLayer(self):
        if len(settings.objectArray) == 0:
            return (settings.projectSettings['SXToolsRefNames'][1])

        selectedIndex = maya.cmds.textScrollList(
            'layerList', query=True, selectIndexedItem=True)
        if selectedIndex is None:
            maya.cmds.textScrollList('layerList', edit=True, selectIndexedItem=1)
            selectedIndex = 1
        else:
            selectedIndex = int(selectedIndex[0])

        # Blend modes are only valid for color layers, not material channels
        if 'layer' not in settings.projectSettings['SXToolsRefNames'][selectedIndex]:
            maya.cmds.optionMenu('layerBlendModes', edit=True, enable=False)
        else:
            selected = str(settings.shapeArray[len(settings.shapeArray)-1])
            attr = '.' + settings.projectSettings['SXToolsRefNames'][selectedIndex] + 'BlendMode'
            mode = maya.cmds.getAttr(selected + attr) + 1
            maya.cmds.optionMenu('layerBlendModes', edit=True, select=mode, enable=True)

        return (settings.projectSettings['SXToolsRefNames'][selectedIndex])

    # Color sets of any selected object are checked
    # to see if they match the reference set.
    # Also verifies subdivision mode.
    def verifyObjectLayers(self, objects):
        refLayers = self.sortLayers(
            settings.projectSettings['SXToolsRefLayers'].keys())
        nonStdObjs = []
        empty = False

        setup.setPrimVars()
        
        for shape in settings.shapeArray:
          maya.cmds.setAttr(str(shape)+'.useGlobalSmoothDrawType', False)
          maya.cmds.setAttr(str(shape)+'.smoothDrawType', 2)

        for object in objects:
            testLayers = maya.cmds.polyColorSet(object, query=True, allColorSets=True)
            if testLayers is None:
                nonStdObjs.append(object)
                empty = True
            elif set(refLayers).issubset(testLayers) is False:
                nonStdObjs.append(object)
                empty = False

        if len(nonStdObjs) > 0 and empty is True:
            return 1, nonStdObjs
        elif len(nonStdObjs) > 0 and empty is False:
            return 2, nonStdObjs
        else:
            return 0, None


class UI(object):
    def __init__(self):
        return None

    def openSXPaintTool(self):
        maya.mel.eval('PaintVertexColorTool;')
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
            'setupFrame',
            parent='canvas',
            width=250,
            label='Project Setup',
            marginWidth=5,
            marginHeight=5,
            collapsable=True,
            collapse=settings.frameStates['setupFrameCollapse'],
            collapseCommand="sxtools.settings.frameStates['setupFrameCollapse']=True",
            expandCommand="sxtools.settings.frameStates['setupFrameCollapse']=False",
            borderVisible=False)

        maya.cmds.columnLayout(
            'prefsColumn', parent='setupFrame', rowSpacing=5, adjustableColumn=True)

        maya.cmds.button(
            label='Select Settings File',
            parent='prefsColumn',
            statusBarMessage='Shift-click button to reload settings from file',
            command='sxtools.settings.setPreferencesFile()\n'
            'sxtools.sx.updateSXTools()')

        if maya.cmds.optionVar(exists='SXToolsPrefsFile') and len(
                str(maya.cmds.optionVar(query='SXToolsPrefsFile'))) > 0:
            maya.cmds.text(label='Current settings location:')
            maya.cmds.text(label=maya.cmds.optionVar(query='SXToolsPrefsFile'))
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
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))

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

        # maya.cmds.text('specularRGBLabel', label='Specular (RGB):')
        # maya.cmds.checkBox('specularRGB', label='', value=True)
        # maya.cmds.textField('specularRGBExport', text='V1, UV2')

        maya.cmds.text('transmissionLabel', label='Transmission:')
        maya.cmds.checkBox('transmission', label='', value=True)
        maya.cmds.textField('transmissionExport', text='U2')

        maya.cmds.text('emissionLabel', label='Emission:')
        maya.cmds.checkBox('emission', label='', value=True)
        maya.cmds.textField('emissionExport', text='V2')

        # maya.cmds.text('emissionRGBLabel', label='Emission (RGB):')
        # maya.cmds.checkBox('emissionRGB', label='', value=True)
        # maya.cmds.textField('emissionRGBExport', text='UV3, UV4')

        maya.cmds.text('overlay1Label', label='Overlay1 (RGBA):')
        maya.cmds.textField('overlay1', text='layer9')
        maya.cmds.textField('overlay1Export', text='UV4,UV5')

        maya.cmds.text('overlay2Label', label='Overlay2 (RGBA):')
        maya.cmds.textField('overlay2', text='layer10')
        maya.cmds.textField('overlay2Export', text='UV6,UV7')

        maya.cmds.rowColumnLayout(
            'numLayerColumns',
            parent='setupFrame',
            numberOfColumns=2,
            columnWidth=((1, 160), (2, 70)),
            columnAttach=[(1, 'left', 0), (2, 'left', 0)],
            rowSpacing=(1, 0))

        maya.cmds.text(label='Export Process Options')
        maya.cmds.text(label=' ')
        maya.cmds.text(label='Alpha-to-mask limit:')

        maya.cmds.floatField(
            'exportTolerance',
            value=1.0,
            minValue=0,
            maxValue=1,
            precision=1,
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))

        maya.cmds.text(label='Smoothing iterations:')
        maya.cmds.intField(
            'exportSmooth',
            value=0,
            minValue=0,
            maxValue=3,
            step=1,
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))

        maya.cmds.text(label='Export preview grid spacing:')
        maya.cmds.intField(
            'exportOffset',
            value=5,
            minValue=0,
            step=1,
            enterCommand=("maya.cmds.setFocus('MayaWindow')"))

        maya.cmds.text(label='Use "_paletted" export suffix:')
        maya.cmds.checkBox(
            'suffixCheck',
            label='',
            value=True,
            changeCommand=(
                "sxtools.settings.projectSettings['SXToolsExportSuffix'] = maya.cmds.checkBox('suffixCheck', query=True, value=True)"
            ))

        maya.cmds.columnLayout(
            'refLayerColumn', parent='setupFrame', rowSpacing=5, adjustableColumn=True)
        maya.cmds.text(label=' ', parent='refLayerColumn')

        if maya.cmds.optionVar(exists='SXToolsPrefsFile') and len(
                str(maya.cmds.optionVar(query='SXToolsPrefsFile'))) > 0:
            maya.cmds.text(
                label='(Shift-click below to apply built-in defaults)',
                parent='refLayerColumn')
            maya.cmds.button(
                label='Apply Project Settings',
                parent='refLayerColumn',
                statusBarMessage='Shift-click button to use the built-in default settings',
                command=("sxtools.settings.updatePreferences()\n"
                        "sxtools.settings.setPreferences()\n"
                        "sxtools.settings.frameStates['setupFrameCollapse']=True\n"
                        "sxtools.sx.updateSXTools()"))

        self.refreshSetupProjectView()

        maya.cmds.workspaceControl(
            dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def refreshSetupProjectView(self):
        if 'SXToolsAlphaTolerance' in settings.projectSettings:
            maya.cmds.floatField(
                'exportTolerance',
                edit=True,
                value=settings.projectSettings['SXToolsAlphaTolerance'])

        if 'SXToolsSmoothExport' in settings.projectSettings:
            maya.cmds.intField(
                'exportSmooth',
                edit=True,
                value=settings.projectSettings['SXToolsSmoothExport'])

        if 'SXToolsExportOffset' in settings.projectSettings:
            maya.cmds.intField(
                'exportOffset',
                edit=True,
                value=settings.projectSettings['SXToolsExportOffset'])

        if 'SXToolsLayerCount' in settings.projectSettings:
            maya.cmds.intField(
                'layerCount',
                edit=True,
                value=settings.projectSettings['SXToolsLayerCount'])

        if 'SXToolsMatChannels' in settings.projectSettings:
            maya.cmds.checkBox(
                'occlusion',
                edit=True,
                value=int(settings.projectSettings['SXToolsMatChannels'][0]))
            maya.cmds.checkBox(
                'specular',
                edit=True,
                value=int(settings.projectSettings['SXToolsMatChannels'][1]))
            maya.cmds.checkBox(
                'transmission',
                edit=True,
                value=int(settings.projectSettings['SXToolsMatChannels'][2]))
            maya.cmds.checkBox(
                'emission',
                edit=True,
                value=int(settings.projectSettings['SXToolsMatChannels'][3]))

        if 'SXToolsExportChannels' in settings.projectSettings:
            maya.cmds.textField(
                'maskExport',
                edit=True,
                text=(settings.projectSettings['SXToolsExportChannels'][0]))
            maya.cmds.textField(
                'occlusionExport',
                edit=True,
                text=(settings.projectSettings['SXToolsExportChannels'][1]))
            maya.cmds.textField(
                'specularExport',
                edit=True,
                text=(settings.projectSettings['SXToolsExportChannels'][2]))
            maya.cmds.textField(
                'transmissionExport',
                edit=True,
                text=(settings.projectSettings['SXToolsExportChannels'][3]))
            maya.cmds.textField(
                'emissionExport',
                edit=True,
                text=(settings.projectSettings['SXToolsExportChannels'][4]))

    def exportObjectsUI(self):
        maya.cmds.frameLayout(
            'exportObjFrame',
            label=str(len(settings.objectArray)) + ' export objects selected',
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.columnLayout('exportedColumn', rowSpacing=5, adjustableColumn=True)
        maya.cmds.button(
            label='Select and show all export meshes',
            command='sxtools.export.viewExported()')
        maya.cmds.button(
            label='Hide exported, show source meshes',
            command=("maya.cmds.setAttr( 'exportsLayer.visibility', 0 )\n"
                    "maya.cmds.setAttr( 'assetsLayer.visibility', 1 )"))

        maya.cmds.text(label='Preview export object data:')
        maya.cmds.radioButtonGrp(
            'exportShadingButtons1',
            parent='exportedColumn',
            vertical=True,
            columnWidth3=(80, 80, 80),
            columnAttach3=('left', 'left', 'left'),
            labelArray3=['Composite', 'Albedo', 'Layer Masks'],
            select=1,
            numberOfRadioButtons=3,
            onCommand1=("sxtools.export.viewExportedMaterial()"),
            onCommand2=("sxtools.export.viewExportedMaterial()"),
            onCommand3=("sxtools.export.viewExportedMaterial()"))
        maya.cmds.radioButtonGrp(
            'exportShadingButtons2',
            parent='exportedColumn',
            vertical=True,
            shareCollection='exportShadingButtons1',
            columnWidth4=(80, 80, 80, 80),
            columnAttach4=('left', 'left', 'left', 'left'),
            labelArray4=['Occlusion', 'Specular', 'Transmission', 'Emission'],
            numberOfRadioButtons=4,
            onCommand1=("sxtools.export.viewExportedMaterial()"),
            onCommand2=("sxtools.export.viewExportedMaterial()"),
            onCommand3=("sxtools.export.viewExportedMaterial()"),
            onCommand4=("sxtools.export.viewExportedMaterial()"))

        maya.cmds.button(
            label='Choose Export Path',
            width=120,
            command=(
                "sxtools.export.setExportPath()\n"
                "sxtools.sx.updateSXTools()")
                )

        if (('SXToolsExportPath' in settings.projectSettings) and
                        (len(settings.projectSettings['SXToolsExportPath']) == 0)):
            maya.cmds.text(label='No export folder selected!')
        elif 'SXToolsExportPath' in settings.projectSettings:
            exportPathText = (
                'Export Path: ' + settings.projectSettings['SXToolsExportPath'])
            maya.cmds.text(label=exportPathText)
            maya.cmds.button(
                label='Export Objects in _staticExports',
                width=120,
                command=(
                    "sxtools.export.exportObjects(sxtools.settings.projectSettings['SXToolsExportPath'])"
                ))
        else:
            maya.cmds.text(label='No export folder selected!')

        maya.cmds.setParent('exportObjFrame')
        maya.cmds.setParent('canvas')
        maya.cmds.workspaceControl(
            dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def emptyObjectsUI(self):
        settings.patchArray = layers.verifyObjectLayers(settings.shapeArray)[1]
        patchLabel = 'Objects with no layers: ' + str(len(settings.patchArray))
        maya.cmds.frameLayout(
            'patchFrame',
            label=patchLabel,
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.columnLayout('patchColumn', adjustableColumn=True, rowSpacing=5)
        maya.cmds.text(
            label=("Click on empty to view project defaults.\n"), align='left')

        if maya.cmds.objExists('SXShader'):
            maya.cmds.text(
                label=("Add project layers to selected objects\n"
                                            "by pressing the button below.\n"),
                align="left")
            maya.cmds.button(
                label='Add missing color sets',
                command='sxtools.layers.patchLayers(sxtools.settings.patchArray)')
        maya.cmds.setParent('patchFrame')
        maya.cmds.setParent('canvas')
        tools.checkHistory(settings.objectArray)
        maya.cmds.workspaceControl(
            dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def mismatchingObjectsUI(self):
        settings.patchArray = layers.verifyObjectLayers(settings.shapeArray)[1]
        patchLabel = 'Objects with nonstandard layers: ' + str(
            len(settings.patchArray))
        maya.cmds.frameLayout(
            'patchFrame',
            label=patchLabel,
            parent='canvas',
            width=250,
            marginWidth=10,
            marginHeight=5)
        maya.cmds.columnLayout('patchColumn', adjustableColumn=True, rowSpacing=5)
        maya.cmds.text(
            label=(
                "To fix color layers:\n"
                "1. Open Color Set Editor\n"
                "2. Delete any redundant color sets\n"
                "3. Rename any needed color sets\n"
                "    using reference names\n"
                "4. DELETE HISTORY on selected objects\n"
                "5. Press 'Add Missing Color Sets' button\n\n"
                "Reference names:\nlayer1-nn, occlusion, specular,\ntransmission, emission"
            ),
            align="left")
        maya.cmds.button(
            label='Color Set Editor', command="maya.mel.eval('colorSetEditor;')")
        if 'SXToolsRefLayers' in settings.projectSettings:
            maya.cmds.button(
                label='Add missing color sets',
                command="sxtools.layers.patchLayers(sxtools.settings.patchArray)")
        maya.cmds.setParent('patchFrame')
        maya.cmds.setParent('canvas')
        tools.checkHistory(settings.objectArray)
        maya.cmds.workspaceControl(
            dockID, edit=True, resizeHeight=5, resizeWidth=250)

    def layerViewUI(self):
        maya.cmds.frameLayout(
            'layerFrame', parent='canvas', width=250, marginWidth=5, marginHeight=5)
        maya.cmds.columnLayout(
            'layerColumn', parent='layerFrame', adjustableColumn=True, rowSpacing=5)
        maya.cmds.radioButtonGrp(
            'shadingButtons',
            parent='layerColumn',
            columnWidth3=(80, 80, 80),
            columnAttach3=('left', 'left', 'left'),
            labelArray3=['Final', 'Debug', 'Alpha'],
            select=1,
            numberOfRadioButtons=3,
            onCommand1=(
                "sxtools.tools.setShadingMode(0)\n"
                "maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='ambientDiffuse', colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayLight;')"),
            onCommand2=(
                "sxtools.tools.setShadingMode(1)\n"
                "maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='none', colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayShadedAndTextured;')"),
            onCommand3=(
                "sxtools.tools.setShadingMode(2)\n"
                "maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='ambientDiffuse', colorShadedDisplay=True)\n"
                "maya.mel.eval('DisplayLight;')"))
        tools.verifyShadingMode()
        maya.cmds.button(
            label='Toggle all layers', command='sxtools.layers.toggleAllLayers()')

        maya.cmds.optionMenu(
            'layerBlendModes',
            parent='layerColumn',
            label='Layer Blend Mode:',
            changeCommand='sxtools.tools.setLayerBlendMode()')
        maya.cmds.menuItem('alphaBlend', label='Alpha', parent='layerBlendModes')
        maya.cmds.menuItem('additiveBlend', label='Add', parent='layerBlendModes')
        maya.cmds.menuItem(
            'multiplyBlend', label='Multiply', parent='layerBlendModes')

        maya.cmds.textScrollList(
            'layerList',
            allowMultiSelection=False,
            ann=('Doubleclick to hide/unhide layer in Final shading mode\n'
                                '(H) - hidden layer\n'
                                '(M) - mask layer\n'
                                '(A) - adjustment layer'))
        layers.refreshLayerList()
        layers.refreshSelectedItem()
        maya.cmds.rowColumnLayout(
            'layerRowColumns',
            parent='layerColumn',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))
        maya.cmds.text(
            'layerColorLabel', label=str(layers.getSelectedLayer()) + ' colors:')
        maya.cmds.palettePort(
            'layerPalette',
            dimensions=(8, 1),
            width=120,
            height=10,
            actualTotal=8,
            editable=True,
            colorEditable=False,
            changeCommand='sxtools.tools.setPaintColor()')
        maya.cmds.text(
            'layerOpacityLabel', label=str(layers.getSelectedLayer()) + ' opacity:')
        maya.cmds.floatSlider(
            'layerOpacitySlider',
            min=0.0,
            max=1.0,
            width=100,
            changeCommand=("sxtools.tools.setLayerOpacity()\n"
                            "sxtools.layers.refreshLayerList()\n"
                            "sxtools.layers.refreshSelectedItem()"))
        tools.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                                                    layers.getSelectedLayer())
        maya.cmds.rowColumnLayout(
            'layerSelectRowColumns',
            parent='layerColumn',
            numberOfColumns=2,
            columnWidth=((1, 120), (2, 120)),
            columnSpacing=([1, 0], [2, 5]),
            rowSpacing=(1, 5))
        maya.cmds.button(
            'mergeLayerUp',
            label='Merge Layer Up',
            parent='layerSelectRowColumns',
            width=100,
            command=("sxtools.layers.mergeLayerDirection(True)"))
        maya.cmds.button(
            'mergeLayerDown',
            label='Merge Layer Down',
            parent='layerSelectRowColumns',
            width=100,
            command=("sxtools.layers.mergeLayerDirection(False)"))
        maya.cmds.button(
            label='Select Layer Mask',
            width=100,
            statusBarMessage='Shift-click button to invert selection',
            command="maya.cmds.select(sxtools.tools.getLayerMask())")
        if len(settings.componentArray) > 0:
            maya.cmds.button(
                'clearButton',
                label='Clear Selected',
                statusBarMessage='Shift-click button to clear all layers on selected components',
                width=100,
                command=(
                    "sxtools.tools.clearSelector()\n"
                    "sxtools.tools.getLayerPaletteOpacity(sxtools.settings.shapeArray[len(sxtools.settings.shapeArray)-1], sxtools.layers.getSelectedLayer())\n"
                    "sxtools.layers.refreshLayerList()\n"
                    "sxtools.layers.refreshSelectedItem()"))
        else:
            maya.cmds.button(
                'clearButton',
                label='Clear Layer',
                statusBarMessage='Shift-click button to clear all layers on selected objects',
                width=100,
                command=(
                    "sxtools.tools.clearSelector()\n"
                    "sxtools.tools.getLayerPaletteOpacity(sxtools.settings.shapeArray[len(sxtools.settings.shapeArray)-1], sxtools.layers.getSelectedLayer())\n"
                    "sxtools.layers.refreshLayerList()\n"
                    "sxtools.layers.refreshSelectedItem()"))

    def applyColorToolUI(self):
        maya.cmds.frameLayout(
            "applyColorFrame",
            parent="toolFrame",
            label="Apply Color",
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['applyColorFrameCollapse'],
            collapseCommand="sxtools.settings.frameStates['applyColorFrameCollapse']=True",
            expandCommand="sxtools.settings.frameStates['applyColorFrameCollapse']=False")
        maya.cmds.columnLayout(
            "applyColorColumn",
            parent="applyColorFrame",
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.rowColumnLayout(
            "applyColorRowColumns",
            parent="applyColorColumn",
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, "left", 0), (2, "both", 5)],
            rowSpacing=(1, 5))
        maya.cmds.text('recentPaletteLabel', label="Recent Colors:")
        maya.cmds.palettePort(
            'recentPalette',
            dimensions=(8, 1),
            width=120,
            height=10,
            actualTotal=8,
            editable=True,
            colorEditable=False,
            scc=settings.toolStates['recentPaletteIndex'],
            changeCommand='sxtools.tools.setApplyColor()')
        maya.cmds.colorSliderGrp(
            'sxApplyColor',
            parent='applyColorColumn',
            label='Color:',
            rgb=settings.currentColor,
            columnWidth3=(80, 20, 60),
            adjustableColumn3=3,
            columnAlign3=('left', 'left', 'left'),
            changeCommand="sxtools.settings.currentColor=maya.cmds.colorSliderGrp('sxApplyColor', query=True, rgbValue=True)"
        )
        maya.cmds.setParent('applyColorColumn')
        maya.cmds.checkBox(
            'overwriteAlpha',
            label='Overwrite Alpha',
            value=settings.toolStates['overwriteAlpha'],
            changeCommand=(
                'sxtools.settings.toolStates["overwriteAlpha"]=maya.cmds.checkBox("overwriteAlpha", query=True, value=True)')
                )
        maya.cmds.button(
            label='Apply Color',
            parent='applyColorColumn',
            height=30,
            width=100,
            command=('sxtools.settings.currentColor=maya.cmds.colorSliderGrp("sxApplyColor", query=True, rgbValue=True)\n'
            'sxtools.tools.colorFill(maya.cmds.checkBox("overwriteAlpha", query=True, value=True))\n'
            'sxtools.tools.updateRecentPalette()')
            )
        maya.cmds.setParent("toolFrame")
        tools.getPalette('recentPalette', settings.paletteDict, 'SXToolsRecentPalette')

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
            parent="toolFrame",
            label="Gradient Fill",
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['gradientFrameCollapse'],
            collapseCommand="sxtools.settings.frameStates['gradientFrameCollapse']=True",
            expandCommand="sxtools.settings.frameStates['gradientFrameCollapse']=False",
            borderVisible=False)
        maya.cmds.columnLayout(
            "gradientColumn",
            parent="gradientFrame",
            rowSpacing=0,
            adjustableColumn=True)
        maya.cmds.optionMenu(
            'rampPresets',
            parent='gradientColumn',
            label='Presets:',
            changeCommand="sxtools.tools.gradientToolManager('load')")
        tools.refreshRampMenu()
        maya.cmds.rowColumnLayout(
            'gradientRowColumns',
            parent='gradientColumn',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))
        maya.cmds.button(
            'savePreset',
            label='Save Preset',
            width=100,
            ann='Shift-click to delete preset',
            command=(
                "sxtools.tools.gradientToolManager('preset')\n"
                "sxtools.sx.updateSXTools()\n"
                "sxtools.settings.savePreferences()")
        )
        maya.cmds.textField(
            'presetName',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Preset Name')
        maya.cmds.attrColorSliderGrp(
            'sxRampColor',
            parent='gradientColumn',
            label='Selected Color:',
            showButton=False,
            columnWidth4=(80, 20, 60, 0),
            adjustableColumn4=3,
            columnAlign4=('left', 'left', 'left', 'left'))
        maya.cmds.attrEnumOptionMenuGrp(
            'sxRampMode',
            parent='gradientColumn',
            label='Interpolation:',
            columnWidth2=(80, 100),
            columnAttach2=('left', 'left'),
            columnAlign2=('left', 'left'))
        maya.cmds.rampColorPort(
            'sxRampControl',
            parent="gradientColumn",
            node='SXRamp',
            height=90,
            selectedColorControl='sxRampColor',
            selectedInterpControl='sxRampMode')
        maya.cmds.attrColorSliderGrp(
            'sxRampAlpha',
            parent='gradientColumn',
            label='Selected Alpha:',
            showButton=False,
            columnWidth4=(80, 20, 60, 0),
            adjustableColumn4=3,
            columnAlign4=('left', 'left', 'left', 'left'))
        maya.cmds.attrEnumOptionMenuGrp(
            'sxAlphaRampMode',
            parent='gradientColumn',
            label='Interpolation:',
            columnWidth2=(80, 100),
            columnAttach2=('left', 'left'),
            columnAlign2=('left', 'left'))
        maya.cmds.rampColorPort(
            'sxRampAlphaControl',
            parent='gradientColumn',
            node='SXAlphaRamp',
            height=90,
            selectedColorControl='sxRampAlpha',
            selectedInterpControl='sxAlphaRampMode')
        maya.cmds.radioButtonGrp(
            'gradientDirection',
            parent='gradientColumn',
            columnWidth3=(80, 80, 80),
            columnAttach3=('left', 'left', 'left'),
            labelArray3=['X', 'Y', 'Z'],
            numberOfRadioButtons=3)
        maya.cmds.radioButtonGrp(
            'gradientMode',
            parent='gradientColumn',
            columnWidth2=(120, 120),
            shareCollection='gradientDirection',
            columnAttach2=('left', 'left'),
            labelArray2=['Luminance', 'Curvature'],
            numberOfRadioButtons=2)
        maya.cmds.button(
            label='Apply Gradient',
            parent='gradientColumn',
            height=30,
            width=100,
            command=(
                "sxtools.tools.gradientToolManager(maya.cmds.radioButtonGrp('gradientDirection', query=True, select=True), 0)\n"
                "sxtools.tools.gradientToolManager(maya.cmds.radioButtonGrp('gradientMode', query=True, select=True), 1)"
            ))
        maya.cmds.setParent('toolFrame')

        if 'SXToolsGradientDirection' in settings.projectSettings:
            gradientDirection = settings.projectSettings['SXToolsGradientDirection']
            if gradientDirection <= 3:
                maya.cmds.radioButtonGrp(
                    'gradientDirection', edit=True, select=gradientDirection)
            elif gradientDirection > 3:
                maya.cmds.radioButtonGrp(
                    'gradientMode', edit=True, select=(gradientDirection - 3))
        else:
            maya.cmds.radioButtonGrp('gradientDirection', edit=True, select=1)

    def colorNoiseToolUI(self):
        maya.cmds.frameLayout(
            'noiseFrame',
            parent='toolFrame',
            label='Color Noise',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['noiseFrameCollapse'],
            collapseCommand="sxtools.settings.frameStates['noiseFrameCollapse']=True",
            expandCommand="sxtools.settings.frameStates['noiseFrameCollapse']=False",
            borderVisible=False)
        maya.cmds.columnLayout(
            'noiseColumn', parent='noiseFrame', rowSpacing=0, adjustableColumn=True)
        maya.cmds.rowColumnLayout(
            'noiseRowColumns',
            parent='noiseColumn',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))
        maya.cmds.text('monoLabel', label='Monochromatic:')
        maya.cmds.checkBox(
            'mono',
            label='',
            value=settings.toolStates['noiseMonochrome'],
            changeCommand=(
                "sxtools.settings.toolStates['noiseMonochrome'] = maya.cmds.checkBox('mono', query=True, value=True)"
            ))
        maya.cmds.text('noiseValueLabel', label='Noise Value (0-1):')
        maya.cmds.floatField(
            'noiseValue',
            precision=3,
            value=settings.toolStates['noiseValue'],
            minValue=0.0,
            maxValue=1.0,
            changeCommand=(
                "sxtools.settings.toolStates['noiseValue'] = maya.cmds.floatField('noiseValue', query=True, value=True)"
            ))
        maya.cmds.button(
            label='Apply Noise',
            parent='noiseColumn',
            height=30,
            width=100,
            command="sxtools.tools.colorNoise(sxtools.settings.objectArray)\n"
            "maya.cmds.floatSlider('layerOpacitySlider', edit=True, value=1.0)\n"
            "sxtools.tools.setLayerOpacity()\n"
            "sxtools.layers.refreshLayerList()\n"
            "sxtools.layers.refreshSelectedItem()")
        maya.cmds.setParent('toolFrame')

    def bakeOcclusionToolUI(self):
        maya.cmds.frameLayout(
            'occlusionFrame',
            parent='toolFrame',
            label='Bake Occlusion',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['occlusionFrameCollapse'],
            collapseCommand=
            "sxtools.settings.frameStates['occlusionFrameCollapse']=True",
            expandCommand=
            "sxtools.settings.frameStates['occlusionFrameCollapse']=False")
        maya.cmds.columnLayout(
            'occlusionColumn',
            parent='occlusionFrame',
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.text(
            label=("\nOcclusion groundplane is placed\n"
                                        "at the minY of the bounding box of\n"
                                        "each object being baked.\n"
                                        "Offset pushes the plane down.\n"),
            align="left")
        maya.cmds.rowColumnLayout(
            'occlusionRowColumns',
            parent='occlusionColumn',
            numberOfColumns=4,
            columnWidth=((1, 80), (2, 50), (3, 50), (4, 50)),
            columnAttach=[(1, 'left', 0), (2, 'left', 0), (3, 'left', 0), (4, 'left', 0)],
            rowSpacing=(1, 0))

        maya.cmds.text(label=' ')
        maya.cmds.text(label=' ')
        maya.cmds.text(label='Scale')
        maya.cmds.text(label='Offset')

        maya.cmds.text('groundLabel', label='Groundplane:')
        maya.cmds.text(label='')
        # maya.cmds.checkBox( 'ground', label='', value=settings.toolStates['bakeGroundPlane'],
        #                     changeCommand=("sxtools.settings.toolStates['bakeGroundPlane'] = maya.cmds.checkBox('ground', query=True, value=True)") )
        maya.cmds.floatField(
            'groundScale',
            value=settings.toolStates['bakeGroundScale'],
            precision=1,
            minValue=0.0,
            changeCommand=(
                "sxtools.settings.toolStates['bakeGroundScale'] = maya.cmds.floatField('groundScale', query=True, value=True)"
            ))
        maya.cmds.floatField(
            'groundOffset',
            value=settings.toolStates['bakeGroundOffset'],
            precision=1,
            minValue=0.0,
            changeCommand=(
                "sxtools.settings.toolStates['bakeGroundOffset'] = maya.cmds.floatField('groundOffset', query=True, value=True)"
            ))

        maya.cmds.rowColumnLayout(
            'occlusionRowColumns2',
            parent='occlusionColumn',
            numberOfColumns=2,
            columnWidth=((1, 130), (2, 110)),
            columnAttach=[(1, 'left', 0), (2, 'left', 0)],
            rowSpacing=(1, 0))

        maya.cmds.text(label='Blend local vs. global')
        maya.cmds.floatSlider(
            'blendSlider',
            min=0.0,
            max=1.0,
            width=100,
            value=settings.toolStates['blendSlider'],
            changeCommand=(
                "sxtools.settings.toolStates['blendSlider']=maya.cmds.floatSlider('blendSlider', query=True, value=True)\nsxtools.tools.blendOcclusion()"
            ))

        tools.getLayerPaletteOpacity(settings.shapeArray[len(settings.shapeArray)-1],
                                    layers.getSelectedLayer())

        plugList = maya.cmds.pluginInfo(query=True, listPlugins=True)
        if 'Mayatomr' in plugList:
            maya.cmds.button(
                label='Bake Occlusion (Mental Ray)',
                parent='occlusionColumn',
                height=30,
                width=100,
                command='sxtools.tools.bakeBlendOcclusion()')
        if 'mtoa' in plugList:
            maya.cmds.rowColumnLayout(
                'occlusionRowColumns3',
                parent='occlusionColumn',
                numberOfColumns=2,
                columnWidth=((1, 130), (2, 110)),
                columnAttach=[(1, 'left', 0), (2, 'left', 0)],
                rowSpacing=(1, 0))
            maya.cmds.text('bake label', label='Bake folder:')
            maya.cmds.textField(
                'bakepath',
                enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                placeholderText='C:/')
            maya.cmds.button(
                label='Bake Occlusion (Arnold)',
                parent='occlusionColumn',
                height=30,
                width=100,
                ann='Shift-click to bake all objects together',
                command="sxtools.tools.bakeOcclusionArnold()")

        maya.cmds.setParent('toolFrame')

    def masterPaletteToolUI(self):
        maya.cmds.frameLayout(
            'masterPaletteFrame',
            parent='toolFrame',
            label='Apply Master Palette',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['masterPaletteFrameCollapse'],
            collapseCommand=
            "sxtools.settings.frameStates['masterPaletteFrameCollapse']=True",
            expandCommand=
            "sxtools.settings.frameStates['masterPaletteFrameCollapse']=False")
        maya.cmds.columnLayout(
            'masterPaletteColumn',
            parent='masterPaletteFrame',
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.optionMenu(
            'masterPalettes',
            parent='masterPaletteColumn',
            label='Presets:',
            changeCommand='sxtools.tools.getMasterPaletteItem()')
        tools.refreshMasterPaletteMenu()
        maya.cmds.rowColumnLayout(
            'masterPaletteRowColumns',
            parent='masterPaletteColumn',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))
        maya.cmds.button(
            'saveMasterPalette',
            label='Save Palette',
            width=100,
            ann='Shift-click to delete palette',
            command='sxtools.tools.saveMasterPalette()')
        maya.cmds.textField(
            'savePaletteName',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Preset Name')
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
                "sxtools.tools.storePalette('masterPalette', sxtools.settings.paletteDict, 'SXToolsMasterPalette')\n"
                "sxtools.settings.toolStates['palettePreset']=None"),
            colorEdited=
            "sxtools.tools.storePalette('masterPalette', sxtools.settings.paletteDict, 'SXToolsMasterPalette')"
        )
        maya.cmds.text(label='Color 1 Target(s): ')
        maya.cmds.textField(
            'masterTarget1',
            parent='masterPaletteRowColumns',
            text=', '.join(settings.toolStates['paletteTarget1']),
            enterCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget1', query=True, text=True), 1)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget1', query=True, text=True), 1)\n"
                "maya.cmds.setFocus('MayaWindow')"),            
            placeholderText='layer1')
        maya.cmds.text(label='Color 2 Target(s): ')
        maya.cmds.textField(
            'masterTarget2',
            parent='masterPaletteRowColumns',
            text=', '.join(settings.toolStates['paletteTarget2']),
            enterCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget2', query=True, text=True), 2)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget2', query=True, text=True), 2)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer2')
        maya.cmds.text(label='Color 3 Target(s): ')
        maya.cmds.textField(
            'masterTarget3',
            parent='masterPaletteRowColumns',
            text=', '.join(settings.toolStates['paletteTarget3']),
            enterCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget3', query=True, text=True), 3)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget3', query=True, text=True), 3)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer3')
        maya.cmds.text(label='Color 4 Target(s): ')
        maya.cmds.textField(
            'masterTarget4',
            parent='masterPaletteRowColumns',
            text=', '.join(settings.toolStates['paletteTarget4']),
            enterCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget4', query=True, text=True), 4)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget4', query=True, text=True), 4)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer4')
        maya.cmds.text(label='Color 5 Target(s): ')
        maya.cmds.textField(
            'masterTarget5',
            parent='masterPaletteRowColumns',
            text=', '.join(settings.toolStates['paletteTarget5']),
            enterCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget5', query=True, text=True), 5)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            changeCommand=(
                "sxtools.tools.checkTarget(maya.cmds.textField('masterTarget5', query=True, text=True), 5)\n"
                "maya.cmds.setFocus('MayaWindow')"),
            placeholderText='layer5')
        maya.cmds.button(
            label='Apply Master Palette',
            parent='masterPaletteColumn',
            height=30,
            width=100,
            command=('sxtools.tools.applyMasterPalette(sxtools.settings.objectArray)'))
        maya.cmds.setParent('toolFrame')

        if ('palettePreset' in settings.toolStates) and (
                settings.toolStates['palettePreset'] is None):
            tools.getPalette('masterPalette', settings.paletteDict, 'SXToolsMasterPalette')
        else:
            tools.getMasterPaletteItem()

    def swapLayerToolUI(self):
        maya.cmds.frameLayout(
            'swapLayerFrame',
            parent='toolFrame',
            label='Swap Layers',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['swapLayerFrameCollapse'],
            collapseCommand=
            "sxtools.settings.frameStates['swapLayerFrameCollapse']=True",
            expandCommand=
            "sxtools.settings.frameStates['swapLayerFrameCollapse']=False")
        maya.cmds.columnLayout(
            'swapLayerColumn',
            parent='swapLayerFrame',
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.rowColumnLayout(
            'swapLayerRowColumns',
            parent='swapLayerColumn',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))
        maya.cmds.text('layerALabel', label='Layer A:')
        maya.cmds.textField(
            'layerA',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Layer A Name')
        maya.cmds.text('layerBLabel', label='Layer B:')
        maya.cmds.textField(
            'layerB',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Layer B Name')
        maya.cmds.setParent('swapLayerFrame')
        maya.cmds.button(
            label='Swap Layers',
            parent='swapLayerColumn',
            height=30,
            width=100,
            command=('sxtools.tools.swapLayers(sxtools.settings.shapeArray)'))
        maya.cmds.setParent('toolFrame')

    def copyLayerToolUI(self):
        maya.cmds.frameLayout(
            'copyLayerFrame',
            parent='toolFrame',
            label='Copy Layer',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['copyLayerFrameCollapse'],
            collapseCommand=
            "sxtools.settings.frameStates['copyLayerFrameCollapse']=True",
            expandCommand=
            "sxtools.settings.frameStates['copyLayerFrameCollapse']=False")
        maya.cmds.columnLayout(
            'copyLayerColumn',
            parent='copyLayerFrame',
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.rowColumnLayout(
            'copyLayerRowColumns',
            parent='copyLayerColumn',
            numberOfColumns=2,
            columnWidth=((1, 100), (2, 140)),
            columnAttach=[(1, 'left', 0), (2, 'both', 5)],
            rowSpacing=(1, 5))
        maya.cmds.text('source layer', label='Source Layer:')
        maya.cmds.textField(
            'layersrc',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Source Layer Name')
        maya.cmds.text('target layer', label='Target Layer:')
        maya.cmds.textField(
            'layertgt',
            enterCommand=("maya.cmds.setFocus('MayaWindow')"),
            placeholderText='Target Layer Name')
        maya.cmds.setParent('copyLayerFrame')
        maya.cmds.button(
            label='Copy Layer',
            parent='copyLayerColumn',
            height=30,
            width=100,
            command=('sxtools.tools.copyLayer(sxtools.settings.objectArray)'))
        maya.cmds.setParent('toolFrame')

    def assignCreaseToolUI(self):
        maya.cmds.frameLayout(
            'creaseFrame',
            parent='toolFrame',
            label='Assign to Crease Set',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['creaseFrameCollapse'],
            collapseCommand="sxtools.settings.frameStates['creaseFrameCollapse']=True",
            expandCommand="sxtools.settings.frameStates['creaseFrameCollapse']=False")
        maya.cmds.columnLayout(
            'creaseColumn', parent='creaseFrame', rowSpacing=5, adjustableColumn=True)
        maya.cmds.radioButtonGrp(
            'creaseSets',
            parent='creaseColumn',
            columnWidth4=(50, 50, 50, 50),
            columnAttach4=('left', 'left', 'left', 'left'),
            labelArray4=['[0.5]', '[1.0]', '[2.0]', '[Hard]'],
            numberOfRadioButtons=4,
            onCommand1="sxtools.tools.assignToCreaseSet('sxCrease1')",
            onCommand2="sxtools.tools.assignToCreaseSet('sxCrease2')",
            onCommand3="sxtools.tools.assignToCreaseSet('sxCrease3')",
            onCommand4="sxtools.tools.assignToCreaseSet('sxCrease4')")
        maya.cmds.setParent('creaseFrame')
        maya.cmds.button(
            label='Uncrease Selection',
            parent='creaseColumn',
            height=30,
            width=100,
            command=("sxtools.tools.assignToCreaseSet('sxCrease0')"))
        maya.cmds.setParent('toolFrame')

    def swapLayerSetsUI(self):
        maya.cmds.frameLayout(
            'swapLayerSetsFrame',
            parent='toolFrame',
            label='Swap Layer Sets',
            marginWidth=5,
            marginHeight=0,
            collapsable=True,
            collapse=settings.frameStates['swapLayerSetsFrameCollapse'],
            collapseCommand=
            "sxtools.settings.frameStates['swapLayerSetsFrameCollapse']=True",
            expandCommand="sxtools.settings.frameStates['swapLayerSetsFrameCollapse']=False")
        maya.cmds.columnLayout(
            'swapLayerSetsColumn',
            parent='swapLayerSetsFrame',
            rowSpacing=5,
            adjustableColumn=True)
        maya.cmds.button(
            label='Add New Layer Set',
            parent='swapLayerSetsColumn',
            height=30,
            width=100,
            command=(
                'sxtools.layers.addLayerSet(sxtools.settings.objectArray, sxtools.layers.getLayerSet(sxtools.settings.objectArray[0]))\n'
                'sxtools.sx.updateSXTools()'))
        maya.cmds.text('layerSetLabel', label=('Current Layer Set: ' + str(int(maya.cmds.getAttr(str(settings.shapeArray[0]) + '.activeLayerSet')))))
        if layers.getLayerSet(settings.objectArray[0]) > 0:
            maya.cmds.intSlider(
                'swapLayerSetsSlider',
                width=100,
                annotation='Choose Layer Set',
                parent='swapLayerSetsColumn',
                min=0,
                max=layers.getLayerSet(settings.objectArray[0]),
                value=maya.cmds.getAttr(str(settings.shapeArray[0]) + '.activeLayerSet'),
                changeCommand=(
                'sxtools.tools.swapLayerSets(sxtools.settings.objectArray, maya.cmds.intSlider("swapLayerSetsSlider", query=True, value=True))\n'
                'maya.cmds.text("layerSetLabel", edit=True, label=("Current Layer Set: " + str(int(maya.cmds.getAttr(str(sxtools.settings.shapeArray[0]) + ".activeLayerSet")))))'),
                dragCommand=(
                'sxtools.tools.swapLayerSets(sxtools.settings.objectArray, maya.cmds.intSlider("swapLayerSetsSlider", query=True, value=True))\n'
                'maya.cmds.text("layerSetLabel", edit=True, label=("Current Layer Set: " + str(int(maya.cmds.getAttr(str(sxtools.settings.shapeArray[0]) + ".activeLayerSet")))))')
            )

        maya.cmds.setParent('toolFrame')


class Core(object):
    def __init__(self):
        return None

    def startSXTools(self):
        global dockID

        platform = maya.cmds.about(os=True)

        if platform == 'win' or platform == 'win64':
            displayScalingValue = maya.cmds.mayaDpiSetting(
                query=True, realScaleValue=True)
        else:
            displayScalingValue = 1.0

        settings.loadPreferences()

        print('SX Tools: Prefs loaded')

        maya.cmds.workspaceControl(
            dockID,
            label='SX Tools',
            uiScript='sxtools.sx.updateSXTools()',
            retain=False,
            floating=True,
            initialHeight=5,
            initialWidth=250 * displayScalingValue,
            minimumWidth=250 * displayScalingValue)

        print('SX Tools: Canvas initialized')

        # Background jobs to reconstruct window if selection changes,
        # and to clean up upon closing
        if 'updateSXTools' not in maya.cmds.scriptJob(listJobs=True):
            print('SX Tools: Creating Script Jobs')
            self.job1ID = maya.cmds.scriptJob(event=[
                'SelectionChanged',
                'sxtools.sx.updateSXTools()'])
            self.job2ID = maya.cmds.scriptJob(event=[
                'Undo',
                'sxtools.sx.updateSXTools()'])
            self.job3ID = maya.cmds.scriptJob(event=[
                'NameChanged',
                'sxtools.sx.updateSXTools()'])
            self.job4ID = maya.cmds.scriptJob(event=[
                'SceneOpened',
                'sxtools.settings.frameStates["setupFrameCollapse"]=False\n'
                'sxtools.settings.setPreferences()\n'
                'sxtools.sx.updateSXTools()'
            ])
            self.job5ID = maya.cmds.scriptJob(event=[
                'NewSceneOpened',
                'sxtools.settings.frameStates["setupFrameCollapse"]=False\n'
                'sxtools.settings.setPreferences()\n'
                'sxtools.sx.updateSXTools()'
            ])

        maya.cmds.scriptJob(
            runOnce=True,
            uiDeleted=[dockID, 'sxtools.sx.exitSXTools()'])

        # Set correct lighting and shading mode at start
        maya.mel.eval('DisplayShadedAndTextured;')
        maya.mel.eval('DisplayLight;')
        maya.cmds.modelEditor('modelPanel4', edit=True, udm=False)

    # Avoids UI refresh from being included in the undo list
    # Called by the "jobID" scriptJob whenever the user clicks a selection.
    def updateSXTools(self):
        maya.cmds.undoInfo(stateWithoutFlush=False)
        self.selectionManager()
        self.refreshSXTools()
        maya.cmds.undoInfo(stateWithoutFlush=True)

    def exitSXTools(self):
        global settings, setup, export, tools, layers, ui, sx
        scriptJobs = maya.cmds.scriptJob(listJobs=True)
        for job in scriptJobs:
            if ('sxtools' in job) and ('uiDeleted' not in job):
                index = int(job.split(':')[0])
                maya.cmds.scriptJob(kill=index)
        if settings:
            del settings
        if setup:
            del setup
        if export:
            del export
        if tools:
            del tools
        if layers:
            del layers
        if ui:
            del ui
        if sx:
            del sx

    def resetSXTools(self):
        varList = maya.cmds.optionVar(list=True)
        for var in varList:
            if ('SXTools' in var):
                maya.cmds.optionVar(remove=str(var))
        print('SX Tools: Settings reset')

    # The user can have various different types of objects selected.
    # The selections are filtered for the tool.
    def selectionManager(self):
        settings.selectionArray = maya.cmds.ls(sl=True)
        settings.shapeArray = maya.cmds.listRelatives(
            settings.selectionArray, type='mesh', allDescendents=True, fullPath=True)
        settings.objectArray = maya.cmds.listRelatives(
            settings.shapeArray, parent=True, fullPath=True)
        # settings.componentArray = list(set(maya.cmds.ls(sl=True, o=False)) - set(maya.cmds.ls(sl=True, o=True)))
        settings.componentArray = maya.cmds.filterExpand(
            settings.selectionArray, sm=(31, 32, 34, 70))

        # If only shape nodes are selected
        onlyShapes = True
        for selection in settings.selectionArray:
            if 'Shape' not in str(selection):
                onlyShapes = False
        if onlyShapes is True:
            settings.shapeArray = settings.selectionArray
            settings.objectArray = maya.cmds.listRelatives(
                settings.shapeArray, parent=True, fullPath=True)

        # Maintain correct object selection even if only components are selected
        if (settings.shapeArray is None and settings.componentArray is not None):
            settings.shapeArray = maya.cmds.ls(
                settings.selectionArray, o=True, dag=True, type='mesh', long=True)
            settings.objectArray = maya.cmds.listRelatives(
                settings.shapeArray, parent=True, fullPath=True)

        # The case when the user selects a component set
        if (len(maya.cmds.ls(sl=True, type='objectSet')) >
                        0) and settings.componentArray is not None:
            del settings.componentArray[:]

        if settings.shapeArray is None:
            settings.shapeArray = []

        if settings.objectArray is None:
            settings.objectArray = []

        if settings.componentArray is None:
            settings.componentArray = []

    # The main function of the tool,
    # updates the UI dynamically for different selection types.
    def refreshSXTools(self):
        setup.createDefaultLights()
        setup.createCreaseSets()
        setup.createDisplayLayers()

        # base canvas for all SX Tools UI
        if maya.cmds.scrollLayout('canvas', exists=True):
            maya.cmds.deleteUI('canvas', lay=True)

        maya.cmds.scrollLayout(
            'canvas',
            minChildWidth=250,
            childResizable=True,
            parent=dockID,
            horizontalScrollBarThickness=16,
            verticalScrollBarThickness=16,
            verticalScrollBarAlwaysVisible=False)

        # If nothing selected, or defaults not set, construct setup view
        if (len(settings.shapeArray) == 0) or (
                maya.cmds.optionVar(exists='SXToolsPrefsFile') is False) or (
                    len(settings.projectSettings) == 0):
            ui.setupProjectUI()

        # If exported objects selected, construct message
        elif export.checkExported(settings.objectArray) is True:
            ui.exportObjectsUI()

        # If objects have empty color sets, construct error message
        elif layers.verifyObjectLayers(settings.shapeArray)[0] == 1:
            ui.emptyObjectsUI()

        # If objects have mismatching color sets, construct error message
        elif layers.verifyObjectLayers(settings.shapeArray)[0] == 2:
            ui.mismatchingObjectsUI()

        # Construct layer tools window
        else:
            maya.cmds.editDisplayLayerMembers('assetsLayer', settings.objectArray)
            maya.cmds.setAttr('exportsLayer.visibility', 0)
            maya.cmds.setAttr('assetsLayer.visibility', 1)

            ui.layerViewUI()

            maya.cmds.frameLayout(
                'toolFrame',
                parent='canvas',
                label='Tools',
                width=250,
                marginWidth=5,
                marginHeight=5,
                collapsable=True,
                collapse=settings.frameStates['toolFrameCollapse'],
                collapseCommand=(
                    "sxtools.settings.frameStates['toolFrameCollapse']=True\n"
                    "maya.cmds.workspaceControl( sxtools.dockID, edit=True, resizeHeight=5, resizeWidth=250 )"
                ),
                expandCommand="sxtools.settings.frameStates['toolFrameCollapse']=False")

            maya.cmds.setParent("toolFrame")
            maya.cmds.button(
                label='Paint Vertex Colors',
                height=30,
                width=100,
                command="sxtools.ui.openSXPaintTool()")

            ui.applyColorToolUI()
            ui.gradientToolUI()
            ui.colorNoiseToolUI()
            plugList = maya.cmds.pluginInfo(query=True, listPlugins=True)
            if ('Mayatomr' in plugList) or ('mtoa' in plugList):
                ui.bakeOcclusionToolUI()
            ui.masterPaletteToolUI()
            ui.swapLayerToolUI()
            ui.copyLayerToolUI()
            ui.assignCreaseToolUI()
            ui.swapLayerSetsUI()

            maya.cmds.columnLayout(
                'processColumn',
                parent='canvas',
                width=250,
                rowSpacing=5,
                adjustableColumn=True)
            maya.cmds.text(label=' ', parent='processColumn')
            maya.cmds.button(
                label='Create Export Objects',
                parent='processColumn',
                command="sxtools.export.processObjects(sxtools.settings.selectionArray)")
            maya.cmds.setParent('canvas')
            tools.checkHistory(settings.objectArray)

            # Make sure selected things are using the correct material
            maya.cmds.sets(settings.shapeArray, e=True, forceElement='SXShaderSG')
            if tools.verifyShadingMode() == 0:
                maya.cmds.polyOptions(
                    activeObjects=True,
                    colorMaterialChannel='ambientDiffuse',
                    colorShadedDisplay=True)
                maya.mel.eval('DisplayLight;')
                maya.cmds.modelEditor('modelPanel4', edit=True, udm=False)

        maya.cmds.setFocus('MayaWindow')


def start():
    # Check if SX Tools UI exists
    if maya.cmds.workspaceControl(dockID, exists=True):
        maya.cmds.deleteUI(dockID, control=True)

    scriptJobs = maya.cmds.scriptJob(listJobs=True)
    for job in scriptJobs:
        if ('sxtools' in job) and ('uiDeleted' in job):
            print('SX Tools: Old instance still shutting down!')
            return

    global settings, setup, export, tools, layers, ui, sx

    settings = Settings()
    setup = SceneSetup()
    export = Export()
    tools = ToolActions()
    layers = LayerManagement()
    ui = UI()
    sx = Core()

    sx.startSXTools()
    print('SX Tools: Plugin started')
