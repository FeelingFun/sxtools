# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
# ----------------------------------------------------------------------------

import maya.cmds
import json
import sxglobals


class Settings(object):
    def __init__(self):
        self.selectionArray = []
        self.objectArray = []
        self.shapeArray = []
        self.componentArray = []
        self.patchArray = []
        self.multiShapeArray = []
        self.bakeSet = []
        self.currentColor = (1, 1, 1)
        self.layerAlphaMax = 0
        self.material = None
        self.nodeDict = {}
        self.exportNodeDict = {}
        self.paletteDict = {}
        self.masterPaletteArray = []
        self.materialArray = []
        self.project = {}
        self.localOcclusionDict = {}
        self.globalOcclusionDict = {}
        self.frames = {
            'paneDivision': 0,
            'prefsCollapse': True,
            'setupCollapse': False,
            'skinMeshCollapse': True,
            'occlusionCollapse': True,
            'masterPaletteCollapse': True,
            'paletteCategoryCollapse': False,
            'newPaletteCollapse': True,
            'paletteSettingsCollapse': True,
            'materialsCollapse': True,
            'materialCategoryCollapse': True,
            'newMaterialCollapse': True,
            'materialSettingsCollapse': True,
            'creaseCollapse': True,
            'autoCreaseCollapse': True,
            'applyColorCollapse': True,
            'gradientCollapse': True,
            'copyLayerCollapse': True,
            'swapLayerSetsCollapse': True,
            'exportFlagsCollapse': True
        }
        self.tools = {
            'currentTool': None,
            'matchSubdivision': False,
            'displayScale': 1.0,
            'platform': 'win64',
            'lineHeight': 14.5,
            'compositeEnable': True,
            'recentPaletteIndex': 1,
            'overwriteAlpha': False,
            'noiseMonochrome': False,
            'noiseValue': 0.0,
            'bakeGroundPlane': True,
            'bakeGroundScale': 100.0,
            'bakeGroundOffset': 1.0,
            'bakeTogether': False,
            'blendSlider': 0.0,
            'categoryPreset': None,
            'materialCategoryPreset': None,
            'gradientDirection': 1,
            'gradientPreset': 1,
            'rayCount': 250,
            'bias': 0.000001,
            'comboOffset': 0.9,
            'maxDistance': 10.0,
            'minCreaseLength': 0.01,
            'convex': True,
            'concave': True,
            'creaseThresholds': (0, 0.4, 0.6),
            'sourceLayer': None,
            'targetLayer': None,
            'selectedLayer': 'layer1',
            'selectedDisplayLayer': 'layer1',
            'selectedLayerIndex': 1
        }
        self.refArray = [
            u'layer1', u'layer2', u'layer3', u'layer4', u'layer5',
            u'layer6', u'layer7', u'layer8', u'layer9', u'layer10',
            u'occlusion', u'metallic', u'smoothness', u'transmission',
            u'emission', u'composite'
        ]
        # name: ([0]index, [1](default values),
        #        [2]export channels, [3]alphaOverlayIndex,
        #        [4]overlay, [5]enabled matChannel,
        #        [6]display name)
        self.refLayerData = {
            self.refArray[0]:
                [1, (0.5, 0.5, 0.5, 1), 'U1', 0, False, False, 'layer1'],
            self.refArray[1]:
                [2, (0, 0, 0, 0), None, 0, False, False, 'layer2'],
            self.refArray[2]:
                [3, (0, 0, 0, 0), None, 0, False, False, 'layer3'],
            self.refArray[3]:
                [4, (0, 0, 0, 0), None, 0, False, False, 'layer4'],
            self.refArray[4]:
                [5, (0, 0, 0, 0), None, 0, False, False, 'layer5'],
            self.refArray[5]:
                [6, (0, 0, 0, 0), None, 0, False, False, 'layer6'],
            self.refArray[6]:
                [7, (0, 0, 0, 0), ('U7', 'V7'), 0, False, False, 'layer7'],
            self.refArray[7]:
                [8, (0, 0, 0, 0), 'U4', 1, False, False, 'gradient1'],
            self.refArray[8]:
                [9, (0, 0, 0, 0), 'V4', 2, False, False, 'gradient2'],
            self.refArray[9]:
                [10, (0, 0, 0, 0), ('UV5', 'UV6'), 0, True, False, 'overlay'],
            self.refArray[10]:
                [11, (1, 1, 1, 1), 'V1', 0, False, True, 'occlusion'],
            self.refArray[11]:
                [12, (0, 0, 0, 1), 'U3', 0, False, True, 'metallic'],
            self.refArray[12]:
                [13, (0, 0, 0, 1), 'V3', 0, False, True, 'smoothness'],
            self.refArray[13]:
                [14, (0, 0, 0, 1), 'U2', 0, False, True, 'transmission'],
            self.refArray[14]:
                [15, (0, 0, 0, 1), 'V2', 0, False, True, 'emission'],
            self.refArray[15]:
                [16, (0, 0, 0, 1), None, 0, False, False, 'composite']
        }

    def __del__(self):
        print('SX Tools: Exiting settings')

    def setPreferences(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        # default values, if the user decides to reset the tool
        if shift:
            self.project['DockPosition'] = 1
            self.project['AlphaTolerance'] = 1.0
            self.project['ExportOffset'] = 5
            self.project['LayerCount'] = 10
            self.project['MaskCount'] = 7
            self.project['ChannelCount'] = 5

            self.project['RefNames'] = self.refArray

            self.project['LayerData'] = self.refLayerData

            self.project['ExportSuffix'] = False
            self.project['paletteTarget1'] = [self.refArray[0], ]
            self.project['paletteTarget2'] = [self.refArray[1], ]
            self.project['paletteTarget3'] = [self.refArray[2], ]
            self.project['paletteTarget4'] = [self.refArray[3], ]
            self.project['paletteTarget5'] = [self.refArray[4], ]

            self.project['materialTarget'] = [self.refArray[6], ]

        if shift:
            sxglobals.setup.createSXShader(
                self.project['LayerCount'], True, True, True, True, True)
        elif not shift:
            sxglobals.setup.createSXShader(
                self.project['LayerCount'],
                self.project['LayerData']['occlusion'][5],
                self.project['LayerData']['metallic'][5],
                self.project['LayerData']['smoothness'][5],
                self.project['LayerData']['transmission'][5],
                self.project['LayerData']['emission'][5])

        sxglobals.setup.createSXExportShader()
        sxglobals.setup.createSXExportOverlayShader()
        sxglobals.setup.createSXPBShader()
        sxglobals.setup.createSubMeshMaterials()

        # Viewport and Maya prefs
        maya.cmds.colorManagementPrefs(edit=True, cmEnabled=0)
        maya.cmds.setAttr('hardwareRenderingGlobals.ssaoEnable', 0)
        maya.cmds.setAttr('hardwareRenderingGlobals.transparencyAlgorithm', 0)
        maya.cmds.setAttr('hardwareRenderingGlobals.lineAAEnable', 1)
        maya.cmds.setAttr('hardwareRenderingGlobals.multiSampleEnable', 1)
        maya.cmds.setAttr('hardwareRenderingGlobals.floatingPointRTEnable', 1)

        maya.cmds.select(clear=True)

    # this method is used to create a new sxglobals.settings.project dict
    # from the setup screen, alternate source for the same dict
    # is to read a saved one
    def createPreferences(self):
        self.project['DockPosition'] = maya.cmds.radioButtonGrp(
            'dockPrefsButtons', query=True, select=True)
        self.project['LayerData'] = {}
        self.project['RefNames'] = []
        self.project['AlphaTolerance'] = maya.cmds.floatField(
            'exportTolerance', query=True, value=True)
        self.project['ExportOffset'] = maya.cmds.intField(
            'exportOffset', query=True, value=True)
        self.project['LayerCount'] = maya.cmds.intField(
            'layerCount', query=True, value=True)

        refIndex = 0
        for k in range(0, self.project['LayerCount']):
            refIndex += 1
            layerName = 'layer' + str(k + 1)

            if k == 0:
                self.project['LayerData'][layerName] = [
                    refIndex,
                    (0.5, 0.5, 0.5, 1),
                    maya.cmds.textField('maskExport', query=True, text=True),
                    0,
                    False,
                    False,
                    maya.cmds.textField(
                        layerName + 'Display',
                        query=True,
                        text=True)]
            else:
                self.project['LayerData'][layerName] = [
                    refIndex,
                    (0, 0, 0, 0),
                    None,
                    0,
                    False,
                    False,
                    maya.cmds.textField(
                        layerName + 'Display',
                        query=True,
                        text=True)]

            self.project['RefNames'].append(layerName)

        channels = [u'occlusion', u'metallic', u'smoothness', u'transmission', u'emission']
        for channel in channels:
            if maya.cmds.checkBox(channel, query=True, value=True):
                refIndex += 1
                if channel == 'occlusion':
                    self.project['LayerData'][channel] = [
                        refIndex,
                        (1, 1, 1, 1),
                        None,
                        0,
                        False,
                        True,
                        sxglobals.settings.refLayerData[channel][6]]
                else:
                    self.project['LayerData'][channel] = [
                        refIndex,
                        (0, 0, 0, 1),
                        None,
                        0,
                        False,
                        True,
                        sxglobals.settings.refLayerData[channel][6]]

                self.project['RefNames'].append(channel)
        self.project['LayerData']['composite'] = [
            refIndex + 1,
            (0, 0, 0, 1),
            None,
            0,
            False,
            False,
            sxglobals.settings.refLayerData['composite'][6]]

        if maya.cmds.checkBox('occlusion', query=True, value=True):
            self.project['LayerData']['occlusion'][5] = True
            self.project['LayerData']['occlusion'][2] = (
                maya.cmds.textField(
                    'occlusionExport', query=True, text=True))
        else:
            self.project['LayerData']['occlusion'][5] = False
            self.project['LayerData']['occlusion'][2] = None
        if maya.cmds.checkBox('metallic', query=True, value=True):
            self.project['LayerData']['metallic'][5] = True
            self.project['LayerData']['metallic'][2] = (
                maya.cmds.textField(
                    'metallicExport', query=True, text=True))
        else:
            self.project['LayerData']['metallic'][5] = False
            self.project['LayerData']['metallic'][2] = None
        if maya.cmds.checkBox('smoothness', query=True, value=True):
            self.project['LayerData']['smoothness'][5] = True
            self.project['LayerData']['smoothness'][2] = (
                maya.cmds.textField(
                    'smoothnessExport', query=True, text=True))
        else:
            self.project['LayerData']['smoothness'][5] = False
            self.project['LayerData']['smoothness'][2] = None
        if maya.cmds.checkBox('transmission', query=True, value=True):
            self.project['LayerData']['transmission'][5] = True
            self.project['LayerData']['transmission'][2] = (
                maya.cmds.textField(
                    'transmissionExport', query=True, text=True))
        else:
            self.project['LayerData']['transmission'][5] = False
            self.project['LayerData']['transmission'][2] = None
        if maya.cmds.checkBox('emission', query=True, value=True):
            self.project['LayerData']['emission'][5] = True
            self.project['LayerData']['emission'][2] = (
                maya.cmds.textField('emissionExport', query=True, text=True))
        else:
            self.project['LayerData']['emission'][5] = False
            self.project['LayerData']['emission'][2] = None

        if (maya.cmds.textField('alphaOverlay1', query=True, text=True) in
           sxglobals.settings.project['LayerData'].keys()):
            self.project['LayerData'][maya.cmds.textField(
                'alphaOverlay1', query=True, text=True)][2] = (
                maya.cmds.textField(
                    'alphaOverlay1Export', query=True, text=True))
            self.project['LayerData'][maya.cmds.textField(
                'alphaOverlay1', query=True, text=True)][3] = 1
        # else:
        #     self.project['LayerData'][maya.cmds.textField(
        #        'alphaOverlay1', query=True, text=True)][3] = False
        if (maya.cmds.textField('alphaOverlay2', query=True, text=True) in
           sxglobals.settings.project['LayerData'].keys()):
            self.project['LayerData'][maya.cmds.textField(
                'alphaOverlay2', query=True, text=True)][2] = (
                maya.cmds.textField(
                    'alphaOverlay2Export', query=True, text=True))
            self.project['LayerData'][maya.cmds.textField(
                'alphaOverlay2', query=True, text=True)][3] = 2
        if (maya.cmds.textField('overlay', query=True, text=True) in
           sxglobals.settings.project['LayerData'].keys()):
            self.project['LayerData'][maya.cmds.textField(
                'overlay', query=True, text=True)][2] = [
                    x.strip() for x in str(maya.cmds.textField(
                        'overlayExport', query=True, text=True)).split(',')]
            self.project['LayerData'][maya.cmds.textField(
                'overlay', query=True, text=True)][4] = True

        self.project['ExportSuffix'] = maya.cmds.checkBox(
            'suffixCheck', query=True, value=True)
        self.project['paletteTarget1'] = ['layer1', ]
        self.project['paletteTarget2'] = ['layer2', ]
        self.project['paletteTarget3'] = ['layer3', ]
        self.project['paletteTarget4'] = ['layer4', ]
        self.project['paletteTarget5'] = ['layer5', ]
        self.project['materialTarget'] = ['layer7', ]
        self.project['MaskCount'] = maya.cmds.intField(
            'numMasks', query=True, value=True)

        self.project[
            'ChannelCount'] = refIndex - self.project['LayerCount']

        for i in xrange(self.project['LayerCount']):
            fieldLabel = sxglobals.settings.refArray[i] + 'Display'
            self.project['LayerData'][
                sxglobals.settings.refArray[i]][6] = maya.cmds.textField(
                fieldLabel, query=True, text=True)

    def setFile(self, mode):
        modeArray = ('Settings', 'Palettes', 'Materials')
        modeName = modeArray[mode]
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if not shift:
            filePath = maya.cmds.fileDialog2(
                fileFilter='*.json',
                cap=('Select SX Tools ' + modeName + ' File'),
                dialogStyle=2,
                fm=0)
            if filePath is not None:
                print('SX Tools: ' + modeName + ' file set to ' + filePath[0])
                maya.cmds.optionVar(
                    stringValue=('SXTools' + modeName + 'File', filePath[0]))
            else:
                print('SX Tools: No ' + modeName + 'file selected')
        else:
            self.loadFile(mode)

    def loadFile(self, mode):
        modeArray = ('Settings', 'Palettes', 'Materials')
        modeName = modeArray[mode]
        modePath = 'SXTools' + modeName + 'File'
        if maya.cmds.optionVar(exists=modePath):
            filePath = maya.cmds.optionVar(q=modePath)
            try:
                with open(filePath, 'r') as input:
                    if mode == 0:
                        self.project.clear()
                        self.project = json.load(input)
                        self.setPreferences()
                        self.frames['setupCollapse'] = True
                    elif mode == 1:
                        tempDict = {}
                        tempDict = json.load(input)
                        del self.masterPaletteArray[:]
                        self.masterPaletteArray = tempDict['Palettes']
                    elif mode == 2:
                        tempDict = {}
                        tempDict = json.load(input)
                        del self.materialArray[:]
                        self.materialArray = tempDict['Materials']
                    input.close()
                print('SX Tools: ' + modeName + ' loaded from ' + filePath)
            except ValueError:
                print('SX Tools Error: Invalid ' + modeName + ' file.')
                maya.cmds.optionVar(remove=modePath)
            except IOError:
                print('SX Tools Error: ' + modeName + ' file not found!')
                if mode == 0:
                    maya.cmds.optionVar(remove=modePath)

        else:
            print('SX Tools: No ' + modeName + ' file found')

    def saveFile(self, mode):
        modeArray = ('Settings', 'Palettes', 'Materials')
        modeName = modeArray[mode]
        modePath = 'SXTools' + modeName + 'File'
        if maya.cmds.optionVar(exists=modePath):
            filePath = maya.cmds.optionVar(q=modePath)
            with open(filePath, 'w') as output:
                if mode == 0:
                    json.dump(self.project, output, indent=4)
                elif mode == 1:
                    tempDict = {}
                    tempDict['Palettes'] = self.masterPaletteArray
                    json.dump(tempDict, output, indent=4)
                elif mode == 2:
                    tempDict = {}
                    tempDict['Materials'] = self.materialArray
                    json.dump(tempDict, output, indent=4)
                output.close()
            print('SX Tools: ' + modeName + ' saved')
        else:
            print('SX Tools Warning: ' + modeName + ' file location not set!')
