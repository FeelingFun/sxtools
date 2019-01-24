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
        self.project = {}
        self.localOcclusionDict = {}
        self.globalOcclusionDict = {}
        self.frames = {
            'prefsCollapse': True,
            'setupCollapse': False,
            'skinMeshCollapse': True,
            'occlusionCollapse': True,
            'masterPaletteCollapse': True,
            'paletteCategoryCollapse': False,
            'newPaletteCollapse': True,
            'paletteSettingsCollapse': True,
            'creaseCollapse': True,
            'noiseCollapse': True,
            'applyColorCollapse': True,
            'gradientCollapse': True,
            'copyLayerCollapse': True,
            'swapLayerSetsCollapse': True,
            'exportFlagsCollapse': True
        }
        self.tools = {
            'recentPaletteIndex': 1,
            'overwriteAlpha': False,
            'noiseMonochrome': False,
            'noiseValue': 0.500,
            'bakeGroundPlane': True,
            'bakeGroundScale': 100.0,
            'bakeGroundOffset': 1.0,
            'bakeTogether': False,
            'blendSlider': 0.0,
            'categoryPreset': None,
            'gradientDirection': 1,
            'rayCount': 250,
            'bias': 0.000001,
            'comboOffset': 0.9,
            'maxDistance': 10.0,
        }
        self.refArray = [
            u'layer1', u'layer2', u'layer3', u'layer4', u'layer5',
            u'layer6', u'layer7', u'layer8', u'layer9', u'layer10',
            u'occlusion', u'specular', u'transmission', u'emission'
        ]
        # name: ([0]index, [1](default values),
        #        [2]export channels, [3]alphaOverlayIndex,
        #        [4]overlay, [5]enabled matChannel,
        #        [6]display name)
        self.refLayerData = {
            self.refArray[0]:
                [1, (0.5, 0.5, 0.5, 1), 'U3', 0, False, False, 'layer1'],
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
                [7, (0, 0, 0, 0), ('V3', 'U7', 'V7'), 0, False, False, 'layer7'],
            self.refArray[7]:
                [8, (0, 0, 0, 0), 'U4', 1, False, False, 'gradient1'],
            self.refArray[8]:
                [9, (0, 0, 0, 0), 'V4', 2, False, False, 'gradient2'],
            self.refArray[9]:
                [10, (0, 0, 0, 0), ('UV5', 'UV6'), 0, True, False, 'overlay'],
            self.refArray[10]:
                [11, (1, 1, 1, 1), 'U1', 0, False, True, 'occlusion'],
            self.refArray[11]:
                [12, (0, 0, 0, 1), 'V1', 0, False, True, 'specular'],
            self.refArray[12]:
                [13, (0, 0, 0, 1), 'U2', 0, False, True, 'transmission'],
            self.refArray[13]:
                [14, (0, 0, 0, 1), 'V2', 0, False, True, 'emission']
        }

    def __del__(self):
        print('SX Tools: Exiting settings')

    def setPreferences(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        # default values, if the user decides to reset the tool
        if shift is True:
            self.project['dockPosition'] = 1,
            self.project['AlphaTolerance'] = 1.0
            self.project['ExportOffset'] = 5
            self.project['LayerCount'] = 10
            self.project['MaskCount'] = 7
            self.project['ChannelCount'] = 4

            self.project['RefNames'] = self.refArray

            self.project['LayerData'] = self.refLayerData

            self.project['ExportSuffix'] = True
            self.project['paletteTarget1'] = [self.refArray[0], ]
            self.project['paletteTarget2'] = [self.refArray[1], ]
            self.project['paletteTarget3'] = [self.refArray[2], ]
            self.project['paletteTarget4'] = [self.refArray[3], ]
            self.project['paletteTarget5'] = [self.refArray[4], ]

        if shift is True:
            sxglobals.setup.createSXShader(
                self.project['LayerCount'], True, True, True, True)
        elif shift is False:
            sxglobals.setup.createSXShader(
                self.project['LayerCount'],
                self.project['LayerData']['occlusion'][5],
                self.project['LayerData']['specular'][5],
                self.project['LayerData']['transmission'][5],
                self.project['LayerData']['emission'][5])
        sxglobals.setup.createSXExportShader()
        sxglobals.setup.createSXExportOverlayShader()
        sxglobals.setup.createSXPBShader()

        # Viewport and Maya prefs
        maya.cmds.colorManagementPrefs(edit=True, cmEnabled=0)
        maya.cmds.setAttr('hardwareRenderingGlobals.transparencyAlgorithm', 3)
        maya.cmds.setAttr('hardwareRenderingGlobals.lineAAEnable', 1)
        maya.cmds.setAttr('hardwareRenderingGlobals.multiSampleEnable', 1)
        maya.cmds.setAttr('hardwareRenderingGlobals.floatingPointRTEnable', 1)

        maya.cmds.select(clear=True)

    # this method is used to create a new sxglobals.settings.project dict from the setup
    # screen, alternate source for the same dict is to read a saved one
    def createPreferences(self):
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

        channels = [u'occlusion', u'specular', u'transmission', u'emission']
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

        if maya.cmds.checkBox('occlusion', query=True, value=True):
            self.project['LayerData']['occlusion'][5] = True
            self.project['LayerData']['occlusion'][2] = (
                maya.cmds.textField(
                    'occlusionExport', query=True, text=True))
        else:
            self.project['LayerData']['occlusion'][5] = False
            self.project['LayerData']['occlusion'][2] = None
        if maya.cmds.checkBox('specular', query=True, value=True):
            self.project['LayerData']['specular'][5] = True
            self.project['LayerData']['specular'][2] = (
                maya.cmds.textField(
                    'specularExport', query=True, text=True))
        else:
            self.project['LayerData']['specular'][5] = False
            self.project['LayerData']['specular'][2] = None
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
                'overlay', query=True, text=True)][2] = (
                str(maya.cmds.textField(
                    'overlayExport', query=True, text=True)).split(','))
            self.project['LayerData'][maya.cmds.textField(
                'overlay', query=True, text=True)][4] = True

        self.project['ExportSuffix'] = maya.cmds.checkBox(
            'suffixCheck', query=True, value=True)
        self.project['paletteTarget1'] = ['layer1', ]
        self.project['paletteTarget2'] = ['layer2', ]
        self.project['paletteTarget3'] = ['layer3', ]
        self.project['paletteTarget4'] = ['layer4', ]
        self.project['paletteTarget5'] = ['layer5', ]
        self.project['MaskCount'] = maya.cmds.intField(
            'numMasks', query=True, value=True)

        self.project[
            'ChannelCount'] = refIndex - self.project['LayerCount']

        for i in xrange(self.project['LayerCount']):
            fieldLabel = sxglobals.settings.refArray[i] + 'Display'
            self.project['LayerData'][
                sxglobals.settings.refArray[i]][6] = maya.cmds.textField(
                fieldLabel, query=True, text=True)

    def setPreferencesFile(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)
        if shift is False:
            filePath = maya.cmds.fileDialog2(
                fileFilter='*.json',
                cap='Select SX Tools Settings File',
                dialogStyle=2,
                fm=0)
            if filePath is not None:
                maya.cmds.optionVar(
                    stringValue=('SXToolsPrefsFile', filePath[0]))
            else:
                print('SX Tools: No Settings file selected')
        else:
            self.loadPreferences()

    def savePreferences(self):
        if maya.cmds.optionVar(exists='SXToolsPrefsFile'):
            filePath = maya.cmds.optionVar(q='SXToolsPrefsFile')
            with open(filePath, 'w') as output:
                json.dump(self.project, output, indent=4)
                output.close()
            print('SX Tools: Settings saved')
        else:
            print('SX Tools Warning: Settings file location not set!')

    def loadPreferences(self):
        if maya.cmds.optionVar(exists='SXToolsPrefsFile'):
            filePath = maya.cmds.optionVar(q='SXToolsPrefsFile')
            try:
                with open(filePath, 'r') as input:
                    self.project.clear()
                    self.project = json.load(input)
                    input.close()
                print('SX Tools: Settings loaded from ' + filePath)
                self.setPreferences()
                self.frames['setupCollapse'] = True
            except ValueError:
                print('SX Tools Error: Invalid settings file.')
                maya.cmds.optionVar(remove='SXToolsPrefsFile')
            except IOError:
                print('SX Tools Error: Settings file not found!')
                maya.cmds.optionVar(remove='SXToolsPrefsFile')
        else:
            print('SX Tools: No settings file found')

    def setPalettesFile(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)
        if shift is False:
            filePath = maya.cmds.fileDialog2(
                fileFilter='*.json',
                cap='Select SX Tools Palettes File',
                dialogStyle=2,
                fm=0)
            if filePath is not None:
                print('SX Tools: Palettes file set to '+ filePath[0])
                maya.cmds.optionVar(
                    stringValue=('SXToolsPalettesFile', filePath[0]))
            else:
                print('SX Tools: No Palette file selected')
        else:
            self.loadPalettes()

    def savePalettes(self):
        if maya.cmds.optionVar(exists='SXToolsPalettesFile'):
            filePath = maya.cmds.optionVar(q='SXToolsPalettesFile')
            tempDict = {}
            tempDict['Palettes'] = self.masterPaletteArray

            with open(filePath, 'w') as output:
                json.dump(tempDict, output, indent=4)
                output.close()
            print('SX Tools: Palettes saved')
        else:
            print('SX Tools Warning: Palettes file location not set!')

    def loadPalettes(self):
        if maya.cmds.optionVar(exists='SXToolsPalettesFile'):
            try:
                filePath = maya.cmds.optionVar(q='SXToolsPalettesFile')
                with open(filePath, 'r') as input:
                    tempDict = {}
                    tempDict = json.load(input)
                    input.close()

                del self.masterPaletteArray[:]
                self.masterPaletteArray = tempDict['Palettes']
            except ValueError:
                print('SX Tools Error: Invalid palettes file!')
                maya.cmds.optionVar(remove='SXToolsPalettesFile')
            except IOError:
                print('SX Tools Error: Palettes file not found!')
                # maya.cmds.optionVar(remove='SXToolsPalettesFile')
        else:
            print('SX Tools: No palettes found')
