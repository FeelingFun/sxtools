# --------------------------------------------------------------------
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
# --------------------------------------------------------------------

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
selectionArray = []
objectArray = []
shapeArray = []
componentArray = []
patchArray = []
bakeSet = []
currentColor = (0, 0, 0)
layerAlphaMax = 0
material = None
nodeDict = {}
exportNodeDict = {}
paletteDict = {}
masterPaletteDict = {}
projectSettings = {}
localOcclusionDict = {}
globalOcclusionDict = {}
frameStates = { 'setupFrameCollapse': False, 'toolFrameCollapse': False,
               'occlusionFrameCollapse': True, 'masterPaletteFrameCollapse': True,
               'creaseFrameCollapse': True, 'noiseFrameCollapse': True,
               'applyColorFrameCollapse': True, 'swapLayerFrameCollapse': True,
               'gradientFrameCollapse': True, 'copyLayerFrameCollapse': True }
toolStates = { 'noiseMonochrome': False, 'noiseValue': 0.500,
               'bakeGroundPlane': True, 'bakeGroundScale': 100.0,
               'bakeGroundOffset': 1.0, 'bakeTogether': False,
               'blendSlider': 0.0, 'exportSuffix': False }               
refArray = [u'layer1', u'layer2', u'layer3', u'layer4', u'layer5',
            u'layer6', u'layer7', u'layer8', u'layer9', u'layer10',
            u'occlusion', u'specular', u'transmission', u'emission']


# Setup functions
# --------------------------------------------------------------------

def setPreferences():
    modifiers = maya.cmds.getModifiers()
    shift = bool((modifiers & 1) > 0)

    # default values, if the user decides to reset the tool
    if shift == True:
        projectSettings['SXToolsAlphaTolerance'] = 1.0
        projectSettings['SXToolsSmoothExport'] = 0
        projectSettings['SXToolsExportOffset'] = 5
        projectSettings['SXToolsLayerCount'] = 8
        projectSettings['SXToolsChannelCount'] = 4

        projectSettings['SXToolsRefLayers'] = {u'layer1': (0.5, 0.5, 0.5, 1),
                                               u'layer2': (0, 0, 0, 0),
                                               u'layer3': (0, 0, 0, 0),
                                               u'layer4': (0, 0, 0, 0),
                                               u'layer5': (0, 0, 0, 0),
                                               u'layer6': (0, 0, 0, 0),
                                               u'layer7': (0, 0, 0, 0),
                                               u'layer8': (0, 0, 0, 0),
                                               u'occlusion': (1, 1, 1, 1),
                                               u'specular': (0, 0, 0, 1),
                                               u'transmission': (0, 0, 0, 1),
                                               u'emission': (0, 0, 0, 1)}
        
        projectSettings['SXToolsRefIndices'] = {u'layer1': 1,
                                                u'layer2': 2,
                                                u'layer3': 3,
                                                u'layer4': 4,
                                                u'layer5': 5,
                                                u'layer6': 6,
                                                u'layer7': 7,
                                                u'layer8': 8,
                                                u'occlusion': 9,
                                                u'specular': 10,
                                                u'transmission': 11,
                                                u'emission': 12}
                                                
        projectSettings['SXToolsRefNames'] = {1: u'layer1',
                                              2: u'layer2',
                                              3: u'layer3',
                                              4: u'layer4',
                                              5: u'layer5',
                                              6: u'layer6',
                                              7: u'layer7',
                                              8: u'layer8',
                                              9: u'occlusion',
                                              10: u'specular',
                                              11: u'transmission',
                                              12: u'emission'}
        
        projectSettings['SXToolsMatChannels'] = (1, 1, 1, 1)
        projectSettings['SXToolsExportChannels'] = ('U3', 'U1', 'V1', 'U2', 'V2')

    savePreferences()

    if shift == True:
        createSXShader(projectSettings['SXToolsLayerCount'], True, True, True, True)
    elif shift == False:
        createSXShader(projectSettings['SXToolsLayerCount'],
                       projectSettings['SXToolsMatChannels'][0],
                       projectSettings['SXToolsMatChannels'][1],
                       projectSettings['SXToolsMatChannels'][2],
                       projectSettings['SXToolsMatChannels'][3])
    createSXExportShader()
    createSXPBShader()

    # Viewport and Maya prefs
    maya.cmds.colorManagementPrefs(edit=True, cmEnabled=0)
    maya.cmds.setAttr('hardwareRenderingGlobals.transparencyAlgorithm', 3)
    maya.cmds.setAttr('hardwareRenderingGlobals.lineAAEnable', 1)
    maya.cmds.setAttr('hardwareRenderingGlobals.multiSampleEnable', 1)
    maya.cmds.setAttr('hardwareRenderingGlobals.floatingPointRTEnable', 1)

    maya.cmds.select( clear=True )
    selectionManager()


def setPrimVars():
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    refCount = projectSettings['SXToolsLayerCount']
    
    if refLayers == 'layer1':
        refLayers = 'layer1',
    for shape in shapeArray:
        attrList = maya.cmds.listAttr(shape, ud=True )
        if attrList is None:
            maya.cmds.addAttr(shape, ln='transparency', at='double', min=0, max=1, dv=0)
            maya.cmds.addAttr(shape, ln='shadingMode', at='double', min=0, max=2, dv=0)
            maya.cmds.addAttr(shape, ln='occlusionVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(shape, ln='specularVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(shape, ln='transmissionVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(shape, ln='emissionVisibility', at='double', min=0, max=1, dv=1)
            maya.cmds.addAttr(shape, ln='occlusionBlendMode', at='double', min=0, max=2, dv=0) 
            maya.cmds.addAttr(shape, ln='specularBlendMode', at='double', min=0, max=2, dv=0) 
            maya.cmds.addAttr(shape, ln='transmissionBlendMode', at='double', min=0, max=2, dv=0) 
            maya.cmds.addAttr(shape, ln='emissionBlendMode', at='double', min=0, max=2, dv=0) 
            for k in range(0, projectSettings['SXToolsLayerCount']):
                visName = str(refLayers[k]) + 'Visibility'
                blendName = str(refLayers[k]) + 'BlendMode'
                maya.cmds.addAttr(shape, ln=visName, at='double', min=0, max=1, dv=1)
                maya.cmds.addAttr(shape, ln=blendName, at='double', min=0, max=2, dv=0)
        else:
            if ('transparency' not in attrList):
                maya.cmds.addAttr(shape, ln='transparency', at='double', min=0, max=1, dv=0)
            if ('shadingMode' not in attrList):
                maya.cmds.addAttr(shape, ln='shadingMode', at='double', min=0, max=2, dv=0)
            if ('occlusionVisibility' not in attrList):
                maya.cmds.addAttr(shape, ln='occlusionVisibility', at='double', min=0, max=1, dv=1)
            if ('specularVisibility' not in attrList):
                maya.cmds.addAttr(shape, ln='specularVisibility', at='double', min=0, max=1, dv=1)
            if ('transmissionVisibility' not in attrList):
                maya.cmds.addAttr(shape, ln='transmissionVisibility', at='double', min=0, max=1, dv=1)
            if ('emissionVisibility' not in attrList):
                maya.cmds.addAttr(shape, ln='emissionVisibility', at='double', min=0, max=1, dv=1)
            if ('occlusionBlendMode' not in attrList):
                maya.cmds.addAttr(shape, ln='occlusionBlendMode', at='double', min=0, max=2, dv=0)
            if ('specularBlendMode' not in attrList):
                maya.cmds.addAttr(shape, ln='specularBlendMode', at='double', min=0, max=2, dv=0)
            if ('transmissionBlendMode' not in attrList):
                maya.cmds.addAttr(shape, ln='transmissionBlendMode', at='double', min=0, max=2, dv=0)
            if ('emissionBlendMode' not in attrList):
                maya.cmds.addAttr(shape, ln='emissionBlendMode', at='double', min=0, max=2, dv=0)
                
            for k in range(0, projectSettings['SXToolsLayerCount']):
                blendName = str(refLayers[k]) + 'BlendMode'
                visName = str(refLayers[k]) + 'Visibility'
                if (blendName not in attrList):
                    maya.cmds.addAttr(shape, ln=blendName, at='double', min=0, max=2, dv=0)
                if (visName not in attrList):
                    maya.cmds.addAttr(shape, ln=visName, at='double', min=0, max=1, dv=1)


def refreshSetupProjectView():
    if 'SXToolsAlphaTolerance' in projectSettings:
        maya.cmds.floatField( 'exportTolerance', edit=True, value=projectSettings['SXToolsAlphaTolerance'] )

    if 'SXToolsSmoothExport' in projectSettings:
        maya.cmds.intField( 'exportSmooth', edit=True, value=projectSettings['SXToolsSmoothExport'] )

    if 'SXToolsExportOffset' in projectSettings:
        maya.cmds.intField( 'exportOffset', edit=True, value=projectSettings['SXToolsExportOffset'] )
                                  
    if 'SXToolsLayerCount' in projectSettings:
        maya.cmds.intField( 'layerCount', edit=True, value=projectSettings['SXToolsLayerCount'] )

    if 'SXToolsMatChannels' in projectSettings:
        maya.cmds.checkBox( 'occlusion', edit=True, value=int(projectSettings['SXToolsMatChannels'][0]) )
        maya.cmds.checkBox( 'specular', edit=True, value=int(projectSettings['SXToolsMatChannels'][1]) )
        maya.cmds.checkBox( 'transmission', edit=True, value=int(projectSettings['SXToolsMatChannels'][2]) )
        maya.cmds.checkBox( 'emission', edit=True, value=int(projectSettings['SXToolsMatChannels'][3]) )

    if 'SXToolsExportChannels' in projectSettings:
        maya.cmds.textField( 'maskExport', edit=True, text=(projectSettings['SXToolsExportChannels'][0]) )
        maya.cmds.textField( 'occlusionExport', edit=True, text=(projectSettings['SXToolsExportChannels'][1]) )
        maya.cmds.textField( 'specularExport', edit=True, text=(projectSettings['SXToolsExportChannels'][2]) )
        maya.cmds.textField( 'transmissionExport', edit=True, text=(projectSettings['SXToolsExportChannels'][3]) )
        maya.cmds.textField( 'emissionExport', edit=True, text=(projectSettings['SXToolsExportChannels'][4]) )


def updatePreferences():
    projectSettings['SXToolsAlphaTolerance'] = maya.cmds.floatField( 'exportTolerance', query=True, value=True )
    projectSettings['SXToolsSmoothExport'] = maya.cmds.intField( 'exportSmooth', query=True, value=True )
    projectSettings['SXToolsExportOffset'] = maya.cmds.intField( 'exportOffset', query=True, value=True )
    projectSettings['SXToolsLayerCount'] = maya.cmds.intField( 'layerCount', query=True, value=True )
    projectSettings['SXToolsMatChannels'] = ( int(maya.cmds.checkBox('occlusion', query=True, value=True)),
                                              int(maya.cmds.checkBox('specular', query=True, value=True)), 
                                              int(maya.cmds.checkBox('transmission', query=True, value=True)),
                                              int(maya.cmds.checkBox('emission', query=True, value=True)) )
    projectSettings['SXToolsExportChannels'] = ( maya.cmds.textField('maskExport', query=True, text=True),
                                                 maya.cmds.textField('occlusionExport', query=True, text=True),
                                                 maya.cmds.textField('specularExport', query=True, text=True),
                                                 maya.cmds.textField('transmissionExport', query=True, text=True),
                                                 maya.cmds.textField('emissionExport', query=True, text=True) )
    projectSettings['SXToolsRefLayers'] = {}
    projectSettings['SXToolsRefIndices'] = {}
    projectSettings['SXToolsRefNames'] = {}

    refIndex = 0
    for k in range(0, projectSettings['SXToolsLayerCount']):
        refIndex += 1
        layerName = 'layer' + str(k+1)
        
        if k == 0:
            projectSettings['SXToolsRefLayers'][layerName] = (0.5, 0.5, 0.5, 1)
        else:
            projectSettings['SXToolsRefLayers'][layerName] = (0, 0, 0, 0)
        
        projectSettings['SXToolsRefIndices'][layerName] = refIndex
        projectSettings['SXToolsRefNames'][refIndex] = layerName
        

    channels = [u'occlusion', u'specular', u'transmission', u'emission']
    for channel in channels:
        if maya.cmds.checkBox( channel, query=True, value=True ):
            refIndex += 1
            if channel == 'occlusion':
                projectSettings['SXToolsRefLayers'][channel] = (1, 1, 1, 1)
            else:
                projectSettings['SXToolsRefLayers'][channel] = (0, 0, 0, 1)
            
            projectSettings['SXToolsRefIndices'][channel] = refIndex
            projectSettings['SXToolsRefNames'][refIndex] = channel
    
    projectSettings['SXToolsChannelCount'] = refIndex - projectSettings['SXToolsLayerCount']    


def setPreferencesFile():
    modifiers = maya.cmds.getModifiers()
    shift = bool((modifiers & 1) > 0)
    if shift == False:
        filePath = maya.cmds.fileDialog2(fileFilter='*.txt', cap='Select SX Tools Settings File', dialogStyle=2, fm=0)    
        maya.cmds.optionVar(stringValue=('SXToolsPrefsFile', filePath[0]))
    else:
        loadPreferences()


def savePreferences():
    if maya.cmds.optionVar(exists='SXToolsPrefsFile'):
        filePath = maya.cmds.optionVar(q='SXToolsPrefsFile')
        with open(filePath, 'w') as output:
            output.write('SX Tools Project Settings: \r\n' + str(projectSettings) + '\r\n')
            output.write('SX Tools Master Palette Dictionary: \r\n' + str(masterPaletteDict) + '\r\n')
            output.close()
        print('SX Tools: Preferences saved')
    else:
        print('SX Tools Warning: Preferences file location not set!')


def loadPreferences():
    global projectSettings, masterPaletteDict
    
    if maya.cmds.optionVar(exists='SXToolsPrefsFile'):
        filePath = maya.cmds.optionVar(q='SXToolsPrefsFile')
        with open(filePath, 'r') as input:
            prefData = input.readlines()
            projectSettings = eval(prefData[1])
            masterPaletteDict = eval(prefData[3])
            input.close()

        print('SX Tools: Preferences loaded from ' + filePath)        
        setPreferences()
        frameStates['setupFrameCollapse']=True
    else:
        print('SX Tools: No preferences found')


def createSXShader(numLayers, occlusion=False, specular=False, transmission=False, emission=False):
    global material, nodeDict

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
    material = SFXNetwork.create(materialName)
    channels = []

    if occlusion != False:
        channels.append('occlusion')
    if specular  != False:
        channels.append('specular')
    if transmission  != False:
        channels.append('transmission')
    if emission  != False:
        channels.append('emission')

    #
    # Create common nodes
    #

    mode_node = material.add(sfxnodes.PrimitiveVariable)
    mode_node.name = 'shadingMode'
    mode_node.primvariableName = 'shadingMode'
    mode_node.posx = -3250
    mode_node.posy = 0
    
    transparency_node = material.add(sfxnodes.PrimitiveVariable)
    transparency_node.name = 'transparency'
    transparency_node.primvariableName = 'transparency'
    transparency_node.posx = -3500
    transparency_node.posy = 0
    
    transparencyCast_node = material.add(sfxnodes.FloatToBool)
    transparencyCast_node.name = 'visCast'
    transparencyCast_node.posx = -3500
    transparencyCast_node.posy = 250
    
    bcol_node = material.add(sfxnodes.Color)
    bcol_node.name = 'black'
    bcol_node.color = (0, 0, 0, 1)
    bcol_node.posx = -2500
    bcol_node.posy = -250
    bcolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='black')
    
    wcol_node = material.add(sfxnodes.Color)
    wcol_node.name = 'white'
    wcol_node.color = (1, 1, 1, 1)
    wcol_node.posx = -2500
    wcol_node.posy = -500
    wcolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='white')

    alphaValue_node = material.add(sfxnodes.Float)
    alphaValue_node.name = 'TestValue0'
    alphaValue_node.posx = -1500
    alphaValue_node.posy = 750
    alphaValue_node.value = 0
    
    addValue_node = material.add(sfxnodes.Float)
    addValue_node.name = 'TestValue1'
    addValue_node.posx = -1500
    addValue_node.posy = 1000
    addValue_node.value = 1    

    mulValue_node = material.add(sfxnodes.Float)
    mulValue_node.name = 'TestValue2'
    mulValue_node.posx = -1500
    mulValue_node.posy = 1250
    mulValue_node.value = 2  

    alphaTest_node = material.add(sfxnodes.Comparison)
    alphaTest_node.name = 'alphaTest'
    alphaTest_node.posx = -1250
    alphaTest_node.posy = 750
    
    addTest_node = material.add(sfxnodes.Comparison)
    addTest_node.name = 'addTest'
    addTest_node.posx = -1250
    addTest_node.posy = 1000    

    mulTest_node = material.add(sfxnodes.Comparison)
    mulTest_node.name = 'mulTest'
    mulTest_node.posx = -1250
    mulTest_node.posy = 1250

    alphaIf_node = material.add(sfxnodes.IfElseBasic)
    alphaIf_node.name = 'alphaIf'
    alphaIf_node.posx = -1000
    alphaIf_node.posy = 750
    
    addIf_node = material.add(sfxnodes.IfElseBasic)
    addIf_node.name = 'addIf'
    addIf_node.posx = -1000
    addIf_node.posy = 1000
    
    mulIf_node = material.add(sfxnodes.IfElseBasic)
    mulIf_node.name = 'mulIf'
    mulIf_node.posx = -1000
    mulIf_node.posy = 1250
    
    finalTest_node = material.add(sfxnodes.Comparison)
    finalTest_node.name = 'finalTest'
    finalTest_node.posx = -1250
    finalTest_node.posy = 1500
    
    debugTest_node = material.add(sfxnodes.Comparison)
    debugTest_node.name = 'debugTest'
    debugTest_node.posx = -1250
    debugTest_node.posy = 1750    

    grayTest_node = material.add(sfxnodes.Comparison)
    grayTest_node.name = 'grayTest'
    grayTest_node.posx = -1250
    grayTest_node.posy = 2000        

    visTest_node = material.add(sfxnodes.FloatToBool)
    visTest_node.name = 'visCast'
    visTest_node.posx = -2250
    visTest_node.posy = 1250

    finalIf_node = material.add(sfxnodes.IfElseBasic)
    finalIf_node.name = 'finalIf'
    finalIf_node.posx = -1000
    finalIf_node.posy = 1500
    
    debugIf_node = material.add(sfxnodes.IfElseBasic)
    debugIf_node.name = 'debugIf'
    debugIf_node.posx = -1000
    debugIf_node.posy = 1750
    
    grayIf_node = material.add(sfxnodes.IfElseBasic)
    grayIf_node.name = 'grayIf'
    grayIf_node.posx = -2000
    grayIf_node.posy = 750

    layerComp_node = material.add(sfxnodes.Add)
    layerComp_node.name = 'layerComp'
    layerComp_node.posx = -1000
    layerComp_node.posy = 0
    layerComp_node.supportmulticonnections = True
    layerCompID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='layerComp')

    shaderID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='TraditionalGameSurfaceShader')
    nodeDict['SXShader'] = shaderID

    rgbPathName = 'rgbPath'
    rgbPath_node = material.add(sfxnodes.PathDirectionList)
    rgbPath_node.posx = -2250
    rgbPath_node.posy = 0
    rgbPath_node.name = rgbPathName
    rgbPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=rgbPathName)

    alphaPathName = 'alphaPath'
    alphaPath_node = material.add(sfxnodes.PathDirectionList)
    alphaPath_node.posx = -2250
    alphaPath_node.posy = 250
    alphaPath_node.name = alphaPathName
    alphaPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=alphaPathName)
    
    vectconstName = 'alphaComp'
    vectconst_node = material.add(sfxnodes.VectorConstruct)
    vectconst_node.posx = -2250
    vectconst_node.posy = 500
    vectconst_node.name = vectconstName
    vectconstID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=vectconstName)

    ifMaskName = 'ifMask'
    ifMask_node = material.add(sfxnodes.IfElseBasic)
    ifMask_node.posx = -1750
    ifMask_node.posy = 500
    ifMask_node.name = ifMaskName
    ifMaskID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=ifMaskName)

    premulName = 'preMul'
    premul_node = material.add(sfxnodes.Multiply)
    premul_node.posx = -1500
    premul_node.posy = 250
    premul_node.name = premulName
    premulID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=premulName)

    invOneName = 'invOne'
    invOne_node = material.add(sfxnodes.InvertOneMinus)
    invOne_node.posx = -1750
    invOne_node.posy = 250
    invOne_node.name = invOneName
    invOneID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=invOneName)

    wlerpName = 'wLerp'
    wlerp_node = material.add(sfxnodes.LinearInterpolateMix)
    wlerp_node.posx = -1500
    wlerp_node.posy = 0
    wlerp_node.name = wlerpName
    wlerpID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=wlerpName)

    lerpName = 'alphaLayer'
    lerp_node = material.add(sfxnodes.LinearInterpolateMix)
    lerp_node.posx = -1250
    lerp_node.posy = 500
    lerp_node.name = lerpName
    lerpID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=lerpName)
    
    addName = 'addLayer'
    add_node = material.add(sfxnodes.Add)
    add_node.posx = -1250
    add_node.posy = 250
    add_node.name = addName
    addID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=addName)
    
    mulName = 'mulLayer'
    mul_node = material.add(sfxnodes.Multiply)
    mul_node.posx = -1250
    mul_node.posy = 0
    mul_node.name = mulName
    mulID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=mulName)    

    blendModePathName = 'blendModePath'
    blendModePath_node = material.add(sfxnodes.PathDirectionList)
    blendModePath_node.posx = -2250
    blendModePath_node.posy = 750
    blendModePath_node.name = blendModePathName
    blendModePathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=blendModePathName)

    visPathName = 'visPath'
    visPath_node = material.add(sfxnodes.IfElseBasic)
    visPath_node.posx = -750
    visPath_node.posy = 0
    visPath_node.name = visPathName
    visPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=visPathName)

    visModePathName = 'visModePath'
    visModePath_node = material.add(sfxnodes.PathDirectionList)
    visModePath_node.posx = -2250
    visModePath_node.posy = 1000
    visModePath_node.name = visModePathName
    visModePathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=visModePathName)

    repeatName = 'repeatLoop'
    repeat_node = material.add(sfxnodes.RepeatLoop)
    repeat_node.posx = -750
    repeat_node.posy = -250
    repeat_node.name = repeatName
    repeatID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=repeatName)

    repeatAlphaName = 'repeatAlphaLoop'
    repeatAlpha_node = material.add(sfxnodes.RepeatLoop)
    repeatAlpha_node.posx = -750
    repeatAlpha_node.posy = 250
    repeatAlpha_node.name = repeatAlphaName
    repeatAlphaID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=repeatAlphaName)

    alphaAdd_node = material.add(sfxnodes.Add)
    alphaAdd_node.name = 'alphaAdd'
    alphaAdd_node.posx = -1000
    alphaAdd_node.posy = 250
    alphaAddID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='alphaAdd')

    alphaVar_node = material.add(sfxnodes.Float)
    alphaVar_node.name = 'alphaVar'
    alphaVar_node.value = 0
    alphaVar_node.posx = -1000
    alphaVar_node.posy = 500
    alphaVarID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='alphaVar')

    indexName = 'layerIndex'
    index_node = material.add(sfxnodes.IntValue)
    index_node.posx = -1000
    index_node.posy = -250
    index_node.name = indexName
    indexID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=indexName)
    
    countName = 'layerCount'
    count_node = material.add(sfxnodes.IntValue)
    count_node.posx = -1250
    count_node.posy = -250
    count_node.name = countName
    count_node.value = projectSettings['SXToolsLayerCount']
    countID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=countName)
    
    outputName = 'outputVar'
    output_node = material.add(sfxnodes.Float3)
    output_node.posx = -1500
    output_node.posy = -250
    output_node.valueX = 0
    output_node.valueY = 0
    output_node.valueZ = 0
    output_node.name = outputName
    outputID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=outputName)
    
    diffCompName = 'diffuseComp'
    diffComp_node = material.add(sfxnodes.IfElseBasic)
    diffComp_node.posx = -500
    diffComp_node.posy = 0
    diffComp_node.name = diffCompName
    diffComp_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=diffCompName)
    
    transCompName = 'transparencyComp'
    transComp_node = material.add(sfxnodes.IfElseBasic)
    transComp_node.posx = -500
    transComp_node.posy = 250
    transComp_node.name = transCompName
    transCompID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=transCompName)
    nodeDict[transCompName] = transCompID

    #
    # Create requested number of layer-specific nodes
    #

    for k in range(0, numLayers):
        offset = k*250
        layerName = 'layer'+str(k+1)
        vertcol_node = material.add(sfxnodes.VertexColor)
        vertcol_node.posx = -2500
        vertcol_node.posy = 0 + offset
        vertcol_node.name = layerName
        vertcol_node.colorsetname_Vertex = layerName
        vertcolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=layerName)
        nodeDict[layerName] = vertcolID

        boolName = layerName + 'Visibility'
        bool_node = material.add(sfxnodes.PrimitiveVariable)
        bool_node.posx = -2750
        bool_node.posy = 0 + offset
        bool_node.name = boolName
        bool_node.primvariableName = boolName
        boolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=boolName)
        nodeDict[boolName] = boolID

        blendName = layerName + 'BlendMode'
        blendMode_node = material.add(sfxnodes.PrimitiveVariable)
        blendMode_node.posx = -3000
        blendMode_node.posy = 0 + offset
        blendMode_node.name = blendName
        blendMode_node.primvariableName = blendName
        blendModeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=blendName)
        nodeDict[blendName] = blendModeID


        # Create connections
        material.connect(vertcol_node.outputs.rgb, (rgbPathID, 0))
        material.connect(vertcol_node.outputs.alpha, (alphaPathID, 0))
        material.connect(bool_node.outputs.value, visModePath_node.inputs.options)
        material.connect(blendMode_node.outputs.value, blendModePath_node.inputs.options)

    material.connect(mode_node.outputs.value, finalTest_node.inputs.a)
    material.connect(mode_node.outputs.value, debugTest_node.inputs.a)
    material.connect(mode_node.outputs.value, grayTest_node.inputs.a)
    
    material.connect(transparency_node.outputs.value, transparencyCast_node.inputs.value)
    material.connect(transparencyCast_node.outputs.result, transComp_node.inputs.condition)

    material.connect(alphaValue_node.outputs.float, finalTest_node.inputs.b)
    material.connect(addValue_node.outputs.float, debugTest_node.inputs.b)
    material.connect(mulValue_node.outputs.float, grayTest_node.inputs.b)

    material.connect(alphaPath_node.outputs.result, vectconst_node.inputs.x)
    material.connect(alphaPath_node.outputs.result, vectconst_node.inputs.y)
    material.connect(alphaPath_node.outputs.result, vectconst_node.inputs.z)

    material.connect(rgbPath_node.outputs.result, (premulID, 0))
    material.connect((vectconstID, 1), (premulID, 1))
    material.connect((vectconstID, 1), invOne_node.inputs.value)

    material.connect(rgbPath_node.outputs.result, (wlerpID, 0))
    material.connect(wcol_node.outputs.rgb, (wlerpID, 1))
    material.connect(invOne_node.outputs.result, wlerp_node.inputs.mix)

    material.connect(vectconst_node.outputs.float3, ifMask_node.inputs.true)
    material.connect(rgbPath_node.outputs.result, ifMask_node.inputs.false)
    material.connect(grayTest_node.outputs.result, ifMask_node.inputs.condition)
    material.connect((ifMaskID, 0), (lerpID, 1))

    material.connect(premul_node.outputs.result, (addID, 1))
    material.connect(wlerp_node.outputs.result, (mulID, 1))

    material.connect(alphaPath_node.outputs.result, lerp_node.inputs.mix)

    material.connect(output_node.outputs.float3, (lerpID, 0))
    material.connect(output_node.outputs.float3, (addID, 0))
    material.connect(output_node.outputs.float3, (mulID, 0))

    material.connect(count_node.outputs.int, repeat_node.inputs.count)
    material.connect(index_node.outputs.int, repeat_node.inputs.index)
    material.connect(output_node.outputs.float3, repeat_node.inputs.output)


    material.connect(alphaPath_node.outputs.result, (alphaAddID, 0))
    material.connect(count_node.outputs.int, repeatAlpha_node.inputs.count)
    material.connect(index_node.outputs.int, repeatAlpha_node.inputs.index)
    material.connect(alphaVar_node.outputs.float, repeatAlpha_node.inputs.output)
    material.connect(alphaVar_node.outputs.float, (alphaAddID, 1))

    material.connect(alphaAdd_node.outputs.result, repeatAlpha_node.inputs.calculation)

    material.connect(index_node.outputs.int, rgbPath_node.inputs.index)
    material.connect(index_node.outputs.int, alphaPath_node.inputs.index)
    material.connect(index_node.outputs.int, visModePath_node.inputs.index)
    material.connect(index_node.outputs.int, blendModePath_node.inputs.index)

    material.connect(blendModePath_node.outputs.result, grayIf_node.inputs.false)
    
    material.connect(alphaValue_node.outputs.float, alphaTest_node.inputs.b)
    material.connect(addValue_node.outputs.float, addTest_node.inputs.b)
    material.connect(mulValue_node.outputs.float, mulTest_node.inputs.b)

    material.connect(bcol_node.outputs.rgb, alphaIf_node.inputs.false)
    material.connect(bcol_node.outputs.rgb, addIf_node.inputs.false)
    material.connect(bcol_node.outputs.rgb, mulIf_node.inputs.false)
    
    material.connect(lerp_node.outputs.result, alphaIf_node.inputs.true)
    material.connect(add_node.outputs.result, addIf_node.inputs.true)
    material.connect(mul_node.outputs.result, mulIf_node.inputs.true)
    
    material.connect(grayIf_node.outputs.result, alphaTest_node.inputs.a)
    material.connect(grayIf_node.outputs.result, addTest_node.inputs.a)
    material.connect(grayIf_node.outputs.result, mulTest_node.inputs.a)
    
    material.connect(alphaTest_node.outputs.result, alphaIf_node.inputs.condition)
    material.connect(addTest_node.outputs.result, addIf_node.inputs.condition)
    material.connect(mulTest_node.outputs.result, mulIf_node.inputs.condition)

    material.connect(finalTest_node.outputs.result, finalIf_node.inputs.condition)
    material.connect(debugTest_node.outputs.result, debugIf_node.inputs.condition)
    material.connect(grayTest_node.outputs.result, grayIf_node.inputs.condition)
    
    material.connect(alphaValue_node.outputs.float, grayIf_node.inputs.true)


    material.connect(alphaIf_node.outputs.result, (layerCompID, 0))
    material.connect(addIf_node.outputs.result, (layerCompID, 1))
    material.connect(mulIf_node.outputs.result, (layerCompID, 1))
        
    material.connect(layerComp_node.outputs.result, visPath_node.inputs.true)
    material.connect(output_node.outputs.float3, visPath_node.inputs.false)
    material.connect(visModePath_node.outputs.result, visTest_node.inputs.value)    
    material.connect(visTest_node.outputs.result, visPath_node.inputs.condition)
    
    material.connect(visPath_node.outputs.result, repeat_node.inputs.calculation)

    #
    # Create material channels
    #

    for channel in channels:
        offset = channels.index(channel)*500

        chancol_node = material.add(sfxnodes.VertexColor)
        chancol_node.posx = -2000
        chancol_node.posy = -1000 - offset
        chancol_node.name = channel
        chancol_node.colorsetname_Vertex = channel
        chancolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=channel)
        nodeDict[channel] = chancolID

        chanboolName = channel + 'Visibility'
        chanbool_node = material.add(sfxnodes.PrimitiveVariable)
        chanbool_node.posx = -2000
        chanbool_node.posy = -750 - offset
        chanbool_node.name = chanboolName
        chanbool_node.primvariableName = chanboolName
        chanboolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=chanboolName)
        nodeDict[chanboolName] = chanboolID
        
        chanCastName = channel + 'Cast'
        chanCast_node = material.add(sfxnodes.FloatToBool)
        chanCast_node.posx = -1750
        chanCast_node.posy = -750 - offset
        chanCast_node.name = chanCastName
        chanCastID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName=chanCastName)
        nodeDict[chanboolName] = chanCastID
        
        if3_node = material.add(sfxnodes.IfElseBasic)
        if3_node.posx = -1750
        if3_node.posy = -1000 - offset

        if4_node = material.add(sfxnodes.IfElseBasic)
        if4_node.posx = -1500
        if4_node.posy = -1000 - offset
        if4_node.name = channel + 'Comp'
        
        if channel == 'occlusion':
            material.connect(chancol_node.outputs.red, if3_node.inputs.true)
            material.connect(wcol_node.outputs.red, if3_node.inputs.false)
            material.connect(wcol_node.outputs.red, if4_node.inputs.true)
            
            occ_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='occlusionComp')
            # Connect occlusion
            material.connect((occ_nodeID, 0), (shaderID, 2))
            
        elif channel == 'specular':
            specMul_node = material.add(sfxnodes.Multiply)
            specMul_node.posx = -750
            specMul_node.posy = -500
            specMul_node.name = 'specularMultiplier'
            specMul_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='specularMultiplier')

            specPow_node = material.add(sfxnodes.Pow)
            specPow_node.posx = -750
            specPow_node.posy = -750
            specPow_node.name = 'specularPower'
            specPow_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='specularPower')
            
            smv_node = material.add(sfxnodes.Float)
            smv_node.posx = -1000
            smv_node.posy = -500
            smv_node.name = 'specularMultiplierValue'
            smv_node.value = 0.4
            smv_node.defineinheader = True
            smv_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='specularMultiplierValue')

            spv_node = material.add(sfxnodes.Float)
            spv_node.posx = -1000
            spv_node.posy = -750
            spv_node.name = 'specularPowerValue'
            spv_node.value = 20
            spv_node.defineinheader = True
            spv_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='specularPowerValue')
            
            spec_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='specularComp')
            material.connect(chancol_node.outputs.rgb, if3_node.inputs.true)
            material.connect(bcol_node.outputs.rgb, if3_node.inputs.false)
            material.connect(bcol_node.outputs.rgb, if4_node.inputs.true)
            
            # Connect specular multiplier
            material.connect((spec_nodeID, 0), (specMul_nodeID, 0))
            material.connect((smv_nodeID, 0), (specMul_nodeID, 1))

            # Connect specular power
            specRaw_nodeID = nodeDict['specular']
            material.connect(spv_node.outputs.float, specPow_node.inputs.x)
            material.connect(chancol_node.outputs.red, specPow_node.inputs.y)

            # Connect specular
            material.connect((specMul_nodeID, 0), (shaderID, 5))
            # Connect specular power
            material.connect((specPow_nodeID, 0), (shaderID, 4))

        elif channel == 'transmission':
            trans_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='transmissionComp')
            material.connect(chancol_node.outputs.rgb, if3_node.inputs.true)
            material.connect(bcol_node.outputs.rgb, if3_node.inputs.false)
            material.connect(bcol_node.outputs.rgb, if4_node.inputs.true)
            # Connect transmission
            material.connect((trans_nodeID, 0), (shaderID, 9))

        elif channel == 'emission':
            emiss_nodeID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='emissionComp')
            material.connect(chancol_node.outputs.rgb, if3_node.inputs.true)
            material.connect(bcol_node.outputs.rgb, if3_node.inputs.false)
            material.connect(repeat_node.outputs.output, if4_node.inputs.true)
            # Connect emission
            material.connect((emiss_nodeID, 0), (shaderID, 1))
            
        material.connect(chanbool_node.outputs.value, chanCast_node.inputs.value)
        material.connect(chanCast_node.outputs.result, if3_node.inputs.condition)
        material.connect(grayTest_node.outputs.result, if4_node.inputs.condition)
        material.connect(if3_node.outputs.result, if4_node.inputs.false)        

    #
    # Glue it all together
    #

    material.connect(grayTest_node.outputs.result, diffComp_node.inputs.condition)
    material.connect(repeat_node.outputs.output, diffComp_node.inputs.false)
    material.connect(repeatAlpha_node.outputs.output, transComp_node.inputs.true)
    material.connect(addValue_node.outputs.float, transComp_node.inputs.false)
    material.connect(bcol_node.outputs.rgb, diffComp_node.inputs.true)
                   
    # Connect diffuse
    material.connect((diffComp_nodeID, 0), (shaderID, 3))

    # Initialize network to show attributes in Maya AE
    maya.cmds.shaderfx(sfxnode=materialName, update=True)

    maya.cmds.createNode('shadingEngine', n='SXShaderSG')
    #maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')

    maya.cmds.setAttr('.ihi', 0)
    maya.cmds.setAttr('.dsm', s=2)
    maya.cmds.setAttr('.ro', True) #originally 'yes'

    maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo1')
    maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')
    maya.cmds.connectAttr('SXShaderSG.msg', 'SXMaterials_materialInfo1.sg')
    maya.cmds.relationship('link', ':lightLinker1', 'SXShaderSG.message', ':defaultLightSet.message')
    maya.cmds.relationship('shadowLink', ':lightLinker1', 'SXShaderSG.message', ':defaultLightSet.message')
    maya.cmds.connectAttr('SXShaderSG.pa', ':renderPartition.st', na=True)
    #maya.cmds.connectAttr('SXShader.msg', ':defaultShaderList1.s', na=True)


def createSXExportShader():
    global exportNodeDict

    if maya.cmds.objExists('SXExportShader') == True:
        shadingGroup = maya.cmds.listConnections('SXExportShader', type='shadingEngine')
        #componentsWithExportMaterial = maya.cmds.sets(shadingGroup, q=True)
        maya.cmds.delete('SXExportShader')
    if maya.cmds.objExists('SXExportShaderSG') == True:
        maya.cmds.delete('SXExportShaderSG')

    uvChannels = projectSettings['SXToolsExportChannels']
    maskID = uvChannels[0]
    maskAxis = str(maskID[0])
    maskIndex = int(maskID[1])
    numLayers = float(projectSettings['SXToolsLayerCount'])

    materialName = 'SXExportShader'
    material = SFXNetwork.create(materialName)
    shaderID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='TraditionalGameSurfaceShader')

    black_node = material.add(sfxnodes.Color)
    black_node.name = 'black'
    black_node.color = [0, 0, 0, 1]
    black_node.posx = -250
    black_node.posy = 250

    alphaIf_node = material.add(sfxnodes.IfElseBasic)
    alphaIf_node.name = 'alphaColorIf'
    alphaIf_node.posx = -750
    alphaIf_node.posy = 0
    
    uvIf_node = material.add(sfxnodes.IfElseBasic)
    uvIf_node.name = 'uvIf'
    uvIf_node.posx = -1000
    uvIf_node.posy = 250
    
    uConst_node = material.add(sfxnodes.VectorConstruct)
    uConst_node.posx = -1250
    uConst_node.posy = 500
    uConst_node.name = 'uComp'

    vConst_node = material.add(sfxnodes.VectorConstruct)
    vConst_node.posx = -1250
    vConst_node.posy = 750
    vConst_node.name = 'vComp'

    index_node = material.add(sfxnodes.IntValue)
    index_node.posx = -2500
    index_node.posy = 500
    index_node.name = 'uvIndex'
    uvIndexID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uvIndex')
    exportNodeDict['uvIndex'] = uvIndexID

    indexRef_node = material.add(sfxnodes.IntValue)
    indexRef_node.posx = -2500
    indexRef_node.posy = 750
    indexRef_node.value = maskIndex
    indexRef_node.name = 'uvMaskIndex'

    indexBool_node = material.add(sfxnodes.BoolValue)
    indexBool_node.posx = -2500
    indexBool_node.posy = 1000
    indexBool_node.name = 'indexBool'
    indexBoolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='indexBool') 

    ifUv3_node = material.add(sfxnodes.IfElse)
    ifUv3_node.posx = -1250
    ifUv3_node.posy = 1000

    divU_node = material.add(sfxnodes.Divide)
    divU_node.posx = -1000
    divU_node.posy = 500
    divU_node.name = 'divU'
    divUID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='divU')

    divV_node = material.add(sfxnodes.Divide)
    divV_node.posx = -1000
    divV_node.posy = 750
    divV_node.name = 'divV'
    divVID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='divV')

    divVal_node = material.add(sfxnodes.Float3)
    divVal_node.posx = -2500
    divVal_node.posy = 1250
    divVal_node.valueX = numLayers
    divVal_node.valueY = numLayers
    divVal_node.valueZ = numLayers
    divVal_node.name = 'divVal'

    uv0_node = material.add(sfxnodes.StringValue)
    uv0_node.name = 'uv0String'
    uv0_node.posx = -2250
    uv0_node.posy = 500
    uv0_node.value = 'UV0'

    uv1_node = material.add(sfxnodes.StringValue)
    uv1_node.name = 'uv1String'
    uv1_node.posx = -2250
    uv1_node.posy = 750
    uv1_node.value = 'UV1'

    uv2_node = material.add(sfxnodes.StringValue)
    uv2_node.name = 'uv2String'
    uv2_node.posx = -2250
    uv2_node.posy = 1000
    uv2_node.value = 'UV2'

    uv3_node = material.add(sfxnodes.StringValue)
    uv3_node.name = 'uv3String'
    uv3_node.posx = -2250
    uv3_node.posy = 1250
    uv3_node.value = 'UV3'

    uvPath_node = material.add(sfxnodes.PathDirectionList)
    uvPath_node.posx = -2000
    uvPath_node.posy = 500

    uPath_node = material.add(sfxnodes.PathDirection)
    uPath_node.name = 'uPath'
    uPath_node.posx = -750
    uPath_node.posy = 500
    uPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uPath')

    vPath_node = material.add(sfxnodes.PathDirection)
    vPath_node.name = 'vPath'
    vPath_node.posx = -750
    vPath_node.posy = 750
    vPathID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='vPath')

    vertcol_node = material.add(sfxnodes.VertexColor)
    vertcol_node.posx = -1750
    vertcol_node.posy = 0

    uvset_node = material.add(sfxnodes.UVSet)
    uvset_node.posx = -1750
    uvset_node.posy = 500
    uvset_node.name = 'uvSet'
    uvID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uvSet')

    vectComp_node = material.add(sfxnodes.VectorComponent)
    vectComp_node.posx = -1500
    vectComp_node.posy = 500
    vectComp_node.name = 'uvSplitter'

    uvBool_node = material.add(sfxnodes.Bool)
    uvBool_node.posx = -2000
    uvBool_node.posy = 250
    uvBool_node.name = 'uvBool'
    uvBoolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='uvBool')
    exportNodeDict['uvBool'] = uvBoolID

    colorBool_node = material.add(sfxnodes.Bool)
    colorBool_node.posx = -2000
    colorBool_node.posy = 0
    colorBool_node.name = 'colorBool'
    colorBoolID = maya.cmds.shaderfx(sfxnode=materialName, getNodeIDByName='colorBool')
    exportNodeDict['colorBool'] = colorBoolID
    
    # Create connections
    material.connect(index_node.outputs.int, uvPath_node.inputs.index)
    material.connect(uv0_node.outputs.string, uvPath_node.inputs.options)
    material.connect(uv1_node.outputs.string, uvPath_node.inputs.options)
    material.connect(uv2_node.outputs.string, uvPath_node.inputs.options)
    material.connect(uv3_node.outputs.string, uvPath_node.inputs.options)
    material.connect(uvPath_node.outputs.result, (uvID, 1))
    
    material.connect(index_node.outputs.int, ifUv3_node.inputs.a)
    material.connect(indexRef_node.outputs.int, ifUv3_node.inputs.b)
    material.connect(indexBool_node.outputs.bool, ifUv3_node.inputs.true)
    material.connect((indexBoolID, 1), ifUv3_node.inputs.false)
    
    material.connect(ifUv3_node.outputs.result, (uPathID, 0))
    material.connect(ifUv3_node.outputs.result, (vPathID, 0))
    
    material.connect(uvset_node.outputs.uv, vectComp_node.inputs.vector)

    material.connect(vectComp_node.outputs.x, uConst_node.inputs.x)
    material.connect(vectComp_node.outputs.x, uConst_node.inputs.y)
    material.connect(vectComp_node.outputs.x, uConst_node.inputs.z)
    material.connect(vectComp_node.outputs.y, vConst_node.inputs.x)
    material.connect(vectComp_node.outputs.y, vConst_node.inputs.y)
    material.connect(vectComp_node.outputs.y, vConst_node.inputs.z)

    material.connect(uConst_node.outputs.float3, (divUID, 0))
    material.connect(vConst_node.outputs.float3, (divVID, 0))
    material.connect(divVal_node.outputs.float3, (divUID, 1))
    material.connect(divVal_node.outputs.float3, (divVID, 1))
    
    material.connect(divU_node.outputs.result, uPath_node.inputs.a)
    material.connect(divV_node.outputs.result, vPath_node.inputs.a)
    material.connect(uConst_node.outputs.float3, uPath_node.inputs.b)
    material.connect(vConst_node.outputs.float3, vPath_node.inputs.b)
    
    material.connect(uvBool_node.outputs.bool, uvIf_node.inputs.condition)
    material.connect(uPath_node.outputs.result, uvIf_node.inputs.true)
    material.connect(vPath_node.outputs.result, uvIf_node.inputs.false)
    
    material.connect(colorBool_node.outputs.bool, alphaIf_node.inputs.condition)
    material.connect(vertcol_node.outputs.rgb, alphaIf_node.inputs.true)
    material.connect(uvIf_node.outputs.result, alphaIf_node.inputs.false)

    material.connect(alphaIf_node.outputs.result, (shaderID, 1))
    
    material.connect(black_node.outputs.rgb, (shaderID, 3))
    material.connect(black_node.outputs.rgb, (shaderID, 5))
    material.connect(black_node.outputs.rgb, (shaderID, 6))
    material.connect(black_node.outputs.red, (shaderID, 4))
    material.connect(black_node.outputs.red, (shaderID, 7))

    # Initialize network to show attributes in Maya AE
    maya.cmds.shaderfx(sfxnode=materialName, update=True)

    maya.cmds.createNode('shadingEngine', n='SXExportShaderSG')
    maya.cmds.setAttr('.ihi', 0)
    maya.cmds.setAttr('.ro', True) #originally 'yes'

    maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo2')
    maya.cmds.connectAttr('SXExportShader.oc', 'SXExportShaderSG.ss')
    maya.cmds.connectAttr('SXExportShaderSG.msg', 'SXMaterials_materialInfo2.sg')
    maya.cmds.relationship('link', ':lightLinker1', 'SXExportShaderSG.message', ':defaultLightSet.message')
    maya.cmds.relationship('shadowLink', ':lightLinker1', 'SXExportShaderSG.message', ':defaultLightSet.message')
    maya.cmds.connectAttr('SXExportShaderSG.pa', ':renderPartition.st', na=True)
    #maya.cmds.connectAttr('SXExportShader.msg', ':defaultShaderList1.s', na=True)

"""
    if componentsWithMaterial is not None:
        maya.cmds.sets(componentsWithMaterial, e=True, forceElement='SXShaderSG')
    if componentsWithExportMaterial is not None:
        maya.cmds.sets(componentsWithExportMaterial, e=True, forceElement='SXShaderSG')
"""


def createSXPBShader():
    if maya.cmds.objExists('SXPBShader') == True:
        maya.cmds.delete('SXPBShader')
    if maya.cmds.objExists('SXPBShaderSG') == True:
        maya.cmds.delete('SXPBShaderSG')

    nodeIDs = []
    channels = ('occlusion', 'specular', 'transmission', 'emission')
    matChannels = projectSettings['SXToolsMatChannels']
    uvChannels = projectSettings['SXToolsExportChannels']
    matDict = {'occlusion': uvChannels[1], 'specular': uvChannels[2],
               'transmission': uvChannels[3], 'emission': uvChannels[4]}
    maskID = uvChannels[0]
    maskAxis = str(maskID[0])
    maskIndex = int(maskID[1])
    uvDict = {}

    pbmatName = 'SXPBShader'
    pbmat = StingrayPBSNetwork.create(pbmatName)
    nodeCount = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeCount=True)
    shaderID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='Standard_Base')
    maya.cmds.shaderfx(sfxnode=pbmatName, edit_action=(shaderID, "makeunique"))

    for i in range(nodeCount):
        nodeIDs.append(maya.cmds.shaderfx(sfxnode='SXPBShader', getNodeUIDFromIndex=i))
    for node in nodeIDs:
        maya.cmds.shaderfx(sfxnode='SXPBShader', deleteNode=node)

    shader_node = pbmat.add(pbsnodes.StandardBase)
    shader_node.posx = 0
    shader_node.posy = 0
    shader_node.name = 'StandardBase'
    shaderID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='StandardBase')

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
        if matChannels[k] == True:
            if int(matDict[channel][1]) == 1:
                uv_node = pbmat.add(pbsnodes.Texcoord1)
            elif int(matDict[channel][1]) == 2: 
                uv_node = pbmat.add(pbsnodes.Texcoord2)
            elif int(matDict[channel][1]) == 3:
                uv_node = pbmat.add(pbsnodes.Texcoord3)
            uv_node.posx = -1000
            uv_node.posy = k*250
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
    metPowID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='MetallicPower')

    roughPow_node = pbmat.add(pbsnodes.Power)
    roughPow_node.posx = -500
    roughPow_node.posy = 250
    roughPow_node.name = 'RoughnessPower'
    roughPowID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='RoughnessPower')
    
    metVal_node = pbmat.add(pbsnodes.MaterialVariable)
    metVal_node.posx = -1250
    metVal_node.posy = 250
    metVal_node.name = 'MetallicValue'
    metVal_node.type = 0
    metVal_node.defaultscalar = 0.9
    metValID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='MetallicValue')
    
    roughVal_node = pbmat.add(pbsnodes.MaterialVariable)
    roughVal_node.posx = -1250
    roughVal_node.posy = 500
    roughVal_node.name = 'RoughnessValue'
    roughVal_node.type = 0
    roughVal_node.defaultscalar = 0.4
    roughValID = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeIDByName='RoughnessValue')

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
    maya.cmds.setAttr('.ro', True) #originally 'yes'

    maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo3')
    maya.cmds.connectAttr('SXPBShader.oc', 'SXPBShaderSG.ss')
    maya.cmds.connectAttr('SXPBShaderSG.msg', 'SXMaterials_materialInfo3.sg')
    maya.cmds.relationship('link', ':lightLinker1', 'SXPBShaderSG.message', ':defaultLightSet.message')
    maya.cmds.relationship('shadowLink', ':lightLinker1', 'SXPBShaderSG.message', ':defaultLightSet.message')
    maya.cmds.connectAttr('SXPBShaderSG.pa', ':renderPartition.st', na=True)
    #maya.cmds.connectAttr('SXExportShader.msg', ':defaultShaderList1.s', na=True)


# The pre-vis material depends on lights in the scene to correctly display occlusion
def createDefaultLights():
    if len(maya.cmds.ls(type='light')) == 0:
        print('SX Tools: No lights found in scene, creating default lights.')
        maya.cmds.directionalLight(name='defaultSXDirectionalLight', rotation=(-25, 30, 0), position=(0, 50, 0))
        maya.cmds.setAttr('defaultSXDirectionalLight.useDepthMapShadows', 1)
        maya.cmds.setAttr('defaultSXDirectionalLight.dmapFilterSize', 5)
        maya.cmds.setAttr('defaultSXDirectionalLight.dmapResolution', 1024)
        maya.cmds.ambientLight(name='defaultSXAmbientLight', intensity=0.4, ambientShade=0, position=(0, 50, 0))
        maya.cmds.select( clear=True )
        selectionManager()


def createCreaseSets():
    if maya.cmds.objExists('sxCreasePartition') == False:
        maya.cmds.createNode('partition', n='sxCreasePartition')
    if maya.cmds.objExists('sxCrease0') == False:
        maya.cmds.createNode('creaseSet', n='sxCrease0')
        maya.cmds.setAttr('sxCrease0.creaseLevel', 0.0)
        maya.cmds.connectAttr( 'sxCrease0.partition', 'sxCreasePartition.sets[0]' )
    if maya.cmds.objExists('sxCrease1') == False:
        maya.cmds.createNode('creaseSet', n='sxCrease1')
        maya.cmds.setAttr('sxCrease1.creaseLevel', 0.5)
        maya.cmds.setAttr('sxCrease1.memberWireframeColor', 3)
        maya.cmds.connectAttr( 'sxCrease1.partition', 'sxCreasePartition.sets[1]' )
    if maya.cmds.objExists('sxCrease2') == False:
        maya.cmds.createNode('creaseSet', n='sxCrease2')
        maya.cmds.setAttr('sxCrease2.creaseLevel', 1.0)
        maya.cmds.setAttr('sxCrease2.memberWireframeColor', 5)
        maya.cmds.connectAttr( 'sxCrease2.partition', 'sxCreasePartition.sets[2]' )
    if maya.cmds.objExists('sxCrease3') == False:
        maya.cmds.createNode('creaseSet', n='sxCrease3')
        maya.cmds.setAttr('sxCrease3.creaseLevel', 2.0)
        maya.cmds.setAttr('sxCrease3.memberWireframeColor', 6)
        maya.cmds.connectAttr( 'sxCrease3.partition', 'sxCreasePartition.sets[3]' )
    if maya.cmds.objExists('sxCrease4') == False:
        maya.cmds.createNode('creaseSet', n='sxCrease4')
        maya.cmds.setAttr('sxCrease4.creaseLevel', 10.0)
        maya.cmds.setAttr('sxCrease4.memberWireframeColor', 7)
        maya.cmds.connectAttr( 'sxCrease4.partition', 'sxCreasePartition.sets[4]' )


def createDisplayLayers():
    if 'assetsLayer' not in maya.cmds.ls(type='displayLayer'):
        print('SX Tools: Creating assetsLayer')
        maya.cmds.createDisplayLayer(name='assetsLayer', number=1, empty=True)
    if 'exportsLayer' not in maya.cmds.ls(type='displayLayer'):
        print('SX Tools: Creating exportsLayer')
        maya.cmds.createDisplayLayer(name='exportsLayer', number=2, empty=True) 


# Functions for export processing
# --------------------------------------------------------------------

def initUVs(selected, UVSetName):
    maya.cmds.polyUVSet (selected, create=True, uvSet=UVSetName)
    maya.cmds.polyUVSet (selected, currentUVSet=True, uvSet=UVSetName)
    maya.cmds.polyForceUV (selected, uni=True)

    maya.cmds.select (maya.cmds.polyListComponentConversion(selected, tf=True))
    maya.cmds.polyMapCut (ch=1)
    maya.cmds.select (maya.cmds.polyListComponentConversion(selected, tuv=True))
    maya.cmds.polyEditUV (relative=False, uValue=0, vValue=0)
    selectionManager()

def flattenLayers(selected, numLayers):
    startTime2 = maya.cmds.timerX()
    if numLayers > 1:
        for i in range (1, numLayers):
            sourceLayer = 'layer'+str(i+1)
            mergeLayers(selected, sourceLayer, 'layer1')

    elapsedTime = maya.cmds.timerX (startTime=startTime2)


# For export, the layer colors are flattened to a single vertex color set,
# but their "layer masks" are written to UV coordinates.
# Each vertex must be assigned to one mask.
def colorToUV(selected, uSourceColorSet, vSourceColorSet, targetUVSet):
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

    elapsedTime = maya.cmds.timerX (startTime=startTime1)
    #print ('Elapsed Time for '+uSourceColorSet+' and '+vSourceColorSet+': '+str(elapsedTime)+'\n')


# The layer masks are written to UV3 using an offset value.
# This makes it simpler to separate each vertex to the correct layer in the game engine.
def layerToUV(selected, uvID, numLayers, offset):
    axis = str.lower(str(uvID[0]))
    targetUVSet = 'UV' + str(uvID[1])

    startTime1 = maya.cmds.timerX()

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
    for i in range(1, numLayers+1):
        sourceColorSet = 'layer'+str(i)
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
                if (layerArray[k].a >= projectSettings['SXToolsAlphaTolerance']) and (axis == 'u'):
                    uArray[k] = float(i)
                elif (layerArray[k].a >= projectSettings['SXToolsAlphaTolerance']) and (axis == 'v'):
                    vArray[k] = float(i)
        
    MFnMesh.setUVs(uArray, vArray, targetUVSet)
    MFnMesh.assignUVs(uvIdArray[0], uvIdArray[1], uvSet=targetUVSet)
 
    elapsedTime = maya.cmds.timerX (startTime=startTime1)
    #print ('Elapsed Time for layer baking '+str(elapsedTime)+'\n')


def channelsToUV(exportShape):
    shape = exportShape
    matList = ('occlusion', 'specular', 'transmission', 'emission')
    matArray = projectSettings['SXToolsMatChannels']
    uvArray = list(projectSettings['SXToolsExportChannels'])
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
        a = 'U' + str(k+1)
        b = 'V' + str(k+1)
        if (a in exportDict): 
            uChan = exportDict[a]
        else:
            uChan = 'zero'
        if (b in exportDict):
            vChan = exportDict[b]
        else:
            vChan = 'zero'
        uvSet = 'UV' + str(k+1)

        if not ((uChan == 'zero') and (vChan == 'zero')):
            colorToUV(shape, uChan, vChan, uvSet)


# The steps of the mesh export process:
# 1) Duplicate objects under export folder
# 2) Rename new objects to match originals but with a suffix
# 3) Call the mesh processing functions 4) Delete history on the processed meshes.
def processObjects(sourceArray):
    # Timer for evaluating script performance
    startTime0 = maya.cmds.timerX()
    
    # Clear existing static exports folder and create if necessary
    if maya.cmds.objExists ('_staticExports') == True:
        maya.cmds.delete('_staticExports')
    maya.cmds.group(empty=True, name='_staticExports')
    
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    numLayers = projectSettings['SXToolsLayerCount']
    maskExport = projectSettings['SXToolsExportChannels'][0]
    exportSmoothValue = projectSettings['SXToolsSmoothExport']
    exportOffsetValue = projectSettings['SXToolsExportOffset']

    sourceNamesArray = maya.cmds.ls(sourceArray, dag=True, tr=True)    
    exportArray = maya.cmds.duplicate(sourceArray, renameChildren=True)
    
    # Parent export objects under new group, the tricky bit here is renaming the new objects to the old names.
    # For tracking objects correctly when they might not have unique names, we use "long" and "fullpath" options.
    for export in exportArray:
        if maya.cmds.listRelatives(export, parent=True) is None:
            maya.cmds.parent(export, '_staticExports')

    exportNamesArray = maya.cmds.ls(maya.cmds.listRelatives('_staticExports'), dag=True, tr=True)   
                                 
    # Rename export objects
    for i in range (len(sourceNamesArray)):
        maya.cmds.rename(exportNamesArray[i], sourceNamesArray[i])
    
    exportShapeArray = getTransforms(maya.cmds.listRelatives('_staticExports', ad=True, type='mesh', fullPath=True))
    for exportShape in exportShapeArray: 
        # Create duplicate object for export
        if maya.cmds.getAttr(str(exportShape)+'.transparency') == 1:
            exportName = str(exportShape).split('|')[-1]+'_transparent'
        else:
            exportName = str(exportShape).split('|')[-1]+'_paletted'
        maya.cmds.rename(exportShape, str(exportName), ignoreShape=True)
    
    exportShapeArray = getTransforms(maya.cmds.listRelatives('_staticExports', ad=True, type='mesh', fullPath=True)) 
    for exportShape in exportShapeArray:
        # Check for existing additional UV sets and delete them, create default UVs to UV0 
        indices = maya.cmds.polyUVSet(exportShape, q=True, allUVSetsIndices=True)
    
        for i in indices:
            if i == 0:
                name = maya.cmds.getAttr(str(exportName)+'.uvSet['+str(i)+'].uvSetName')
                maya.cmds.polyUVSet(exportShape, rename=True, uvSet=name, newUVSet='UV0')
                maya.cmds.polyUVSet(exportShape, currentUVSet=True, uvSet='UV0')
                maya.cmds.polyAutoProjection(exportShape, lm=0, pb=0, ibd=1, cm=0, l=3, sc=1, o=0, p=6, ps=0.2, ws=0)
        
            if i > 0:
                name = maya.cmds.getAttr(str(maya.cmds.ls(exportName))+'.uvSet['+str(i)+'].uvSetName')
                maya.cmds.polyUVSet(exportShape, delete=True, uvSet=name)
    
        # Create UV sets for color set data
        initUVs(exportShape, 'UV1')
        initUVs(exportShape, 'UV2')
        initUVs(exportShape, 'UV3')
        
        # Bake material properties to UV channels
        channelsToUV(exportShape)
        
        # Bake masks
        layerToUV(exportShape, maskExport, numLayers, 1)
         
        # Delete history
        maya.cmds.delete(exportShape, ch=True)
        
        # Flatten colors to layer1
        #maya.cmds.select(exportShape)
        flattenLayers(exportShape, numLayers)
        
        # Delete unnecessary color sets (leave only layer1)
        colSets = maya.cmds.polyColorSet(exportShape, query=True, allColorSets=True)
        for set in colSets:
            if str(set) != 'layer1':
                maya.cmds.polyColorSet (exportShape, delete=True, colorSet=str(set))
        
        # Set layer1 visible for userfriendliness
        maya.cmds.polyColorSet (exportShape, currentColorSet=True, colorSet='layer1')
        maya.cmds.sets (exportShape, e=True, forceElement='SXPBShaderSG')
                
        # Smooth mesh as last step for export
        if exportSmoothValue > 0:
            maya.cmds.polySmooth (exportShape, mth=0, sdt=2, ovb=1, ofb=3, ofc=0, ost=1,
                             ocr=0, dv=exportSmoothValue, bnr=1, c=1, kb=1, ksb=1,
                             khe=0, kt=1, kmb=1, suv=1, peh=0, sl=1, dpe=1, ps=0.1, ro=1, ch=0)
            
        # Move to origin, freeze transformations
        finalList = maya.cmds.listRelatives('_staticExports', children=True, fullPath=True)
        offsetX = 0
        offsetZ = 0
        offsetDist = exportOffsetValue
        for final in finalList:
            maya.cmds.setAttr(str(final)+'.translate', 0, 0, 0, type='double3')
            maya.cmds.makeIdentity(final, apply=True, t=1, r=1, s=1, n=0, pn=1)
            maya.cmds.setAttr(str(final)+'.translate', offsetX, 0, offsetZ, type='double3')
            offsetX += offsetDist
            if offsetX == offsetDist*5:
                offsetX = 0
                offsetZ += offsetDist
    
    totalTime = maya.cmds.timerX (startTime=startTime0)
    print ('SX Tools: Total time ' + str(totalTime))
    maya.cmds.select('_staticExports', r=True)
    selectionManager()
    maya.cmds.editDisplayLayerMembers( 'exportsLayer', maya.cmds.ls(sl=True) )
    viewExported()


# Writing FBX files to a user-defined folder includes finding the unique file
# using their fullpath names, then stripping the path to create a clean name for the file.
def exportObjects(exportPath):
    print( 'SX Tools: Writing FBX files, please hold.')
    exportArray = maya.cmds.listRelatives('_staticExports', children=True, fullPath=True )
    for export in exportArray:
        maya.cmds.select(export)
        if toolStates['exportSuffix'] is True:
            exportName = str(export).split('|')[-1]+'.fbx'
        else:
            if str(export).endswith('_paletted'):
                exportName = str(str(export)[:-9]).split('|')[-1]+'.fbx'
            else:
                exportName = str(export).split('|')[-1]+'.fbx'
        exportString = exportPath + exportName
        print(exportString+'\n')
        maya.cmds.file(exportString, force=True, options='v=0', typ='FBX export', pr=True, es=True)


# Tool action functions
# --------------------------------------------------------------------

def assignToCreaseSet(setName):
    creaseSets = ('sxCrease0', 'sxCrease1', 'sxCrease2', 'sxCrease3', 'sxCrease4')
    for component in componentArray:
        if ((maya.cmds.filterExpand(component, sm=31) is not None)
            or (maya.cmds.filterExpand(component, sm=32) is not None)):

            for set in creaseSets:
                if maya.cmds.sets(component, isMember=set):
                    maya.cmds.sets(component, remove=set)
            maya.cmds.sets(component, forceElement=setName)
        else:
            edgeList = maya.cmds.polyListComponentConversion(component, te=True)
            for set in creaseSets:
                if maya.cmds.sets(edgeList, isMember=set):
                    maya.cmds.sets(edgeList, remove=set)
            maya.cmds.sets(edgeList, forceElement=setName)


def bakeOcclusion():      
    bbox = []
    global bakeSet
    bakeSet = shapeArray
    modifiers = maya.cmds.getModifiers()

    if int(projectSettings['SXToolsMatChannels'][0]) == 1:
        setColorSet('occlusion')

    if toolStates['bakeGroundPlane'] == True:
        maya.cmds.polyPlane( name='sxGroundPlane', w=toolStates['bakeGroundScale'], h=toolStates['bakeGroundScale'], sx=1, sy=1, ax=(0, 1, 0), cuv=2, ch=0 )
        maya.cmds.select(bakeSet)
        selectionManager()

    if maya.cmds.objExists('sxVertexBakeSet') == False:
        maya.cmds.createNode( 'vertexBakeSet', n='sxVertexBakeSet', skipSelect=True )
        maya.cmds.partition( 'sxVertexBakeSet', n='vertexBakePartition' )

        maya.cmds.addAttr( 'sxVertexBakeSet', ln='filterSize', sn='fs', min=-1 )
        maya.cmds.setAttr( 'sxVertexBakeSet.filterSize', 0.001 )
        maya.cmds.addAttr( 'sxVertexBakeSet', ln='filterNormalTolerance', sn='fns', min=0, max=180 )
        maya.cmds.setAttr( 'sxVertexBakeSet.filterNormalTolerance', 5 )
        maya.cmds.setAttr( 'sxVertexBakeSet.colorMode', 3 )
        maya.cmds.setAttr( 'sxVertexBakeSet.occlusionRays', 256 )
        maya.cmds.setAttr( 'sxVertexBakeSet.colorBlending', 0)

    if toolStates['bakeTogether'] == True:
        if toolStates['bakeGroundPlane'] == True:
            bbox = maya.cmds.exactWorldBoundingBox( bakeSet )
            maya.cmds.setAttr( 'sxGroundPlane.translateY', (bbox[1] - toolStates['bakeGroundOffset']) )
        maya.cmds.convertLightmapSetup( camera='persp', vm=True, bo='sxVertexBakeSet' )
    else:
        for bake in bakeSet:
            maya.cmds.setAttr( (str(bake) + '.visibility'), False )

        #bake separately
        for bake in bakeSet:
            if toolStates['bakeGroundPlane'] == True:
                bbox = maya.cmds.exactWorldBoundingBox( bake )
                bakeTx = getTransforms([bake,])
                groundPos = maya.cmds.getAttr( str(bakeTx[0])+'.translate' )[0]
                maya.cmds.setAttr( 'sxGroundPlane.translateX', groundPos[0] )
                maya.cmds.setAttr( 'sxGroundPlane.translateY', (bbox[1] - toolStates['bakeGroundOffset']) )
                maya.cmds.setAttr( 'sxGroundPlane.translateZ', groundPos[2] )

            maya.cmds.setAttr( (str(bake) + '.visibility'), True )
            maya.cmds.select(bake)
            selectionManager()
            maya.cmds.convertLightmapSetup( camera='persp', vm=True, bo='sxVertexBakeSet' )
            maya.cmds.setAttr( (str(bake) + '.visibility'), False )

        for bake in bakeSet:
            maya.cmds.setAttr( (str(bake) + '.visibility'), True )
        
    if toolStates['bakeGroundPlane'] == True:
        maya.cmds.delete('sxGroundPlane')
    
    maya.cmds.select(bakeSet)
    selectionManager()


def bakeBlendOcclusion():
    print('SX Tools: Baking local occlusion pass')
    toolStates['bakeGroundPlane'] = False
    toolStates['bakeTogether'] = False
    bakeOcclusion()

    for shape in shapeArray:
        selectionList = OM.MSelectionList()
        selectionList.add(shape)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColorArrayLocal = OM.MColorArray()
        layerColorArrayLocal = MFnMesh.getFaceVertexColors(colorSet = 'occlusion')
        localOcclusionDict[shape] = layerColorArrayLocal 

    print('SX Tools: Baking global occlusion pass')        
    toolStates['bakeGroundPlane'] = True
    toolStates['bakeTogether'] = True 
    bakeOcclusion()

    for shape in shapeArray:
        selectionList = OM.MSelectionList()
        selectionList.add(shape)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColorArrayGlobal = OM.MColorArray()
        layerColorArrayGlobal = MFnMesh.getFaceVertexColors(colorSet = 'occlusion')
        globalOcclusionDict[shape] = layerColorArrayGlobal
    
    toolStates['blendSlider'] = 1.0


def blendOcclusion():
    sliderValue = toolStates['blendSlider']

    for bake in bakeSet:
        selectionList = OM.MSelectionList()
        selectionList.add(bake)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColorArrayLocal = OM.MColorArray()
        layerColorArrayLocal = localOcclusionDict[bake]
        layerColorArrayGlobal = OM.MColorArray()
        layerColorArrayGlobal = globalOcclusionDict[bake]
        layerColorArray = OM.MColorArray()
        layerColorArray = MFnMesh.getFaceVertexColors(colorSet = 'occlusion')

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
            layerColorArray[k].r = (1-sliderValue)*layerColorArrayLocal[k].r + sliderValue*layerColorArrayGlobal[k].r
            layerColorArray[k].g = (1-sliderValue)*layerColorArrayLocal[k].g + sliderValue*layerColorArrayGlobal[k].g
            layerColorArray[k].b = (1-sliderValue)*layerColorArrayLocal[k].b + sliderValue*layerColorArrayGlobal[k].b
            k += 1
            fvIt.next()

        MFnMesh.setFaceVertexColors(layerColorArray, faceIds, vtxIds)

    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())


def bakeOcclusionArnold():
    bakePath = maya.cmds.textField('bakepath', query=True, text=True)
    if bakePath is None:
        bakePath = 'C:/'
    # check if path has a slash, add if necessary

        #create AO material
    if maya.cmds.objExists('aiSXAO') == False:
        maya.cmds.shadingNode('aiAmbientOcclusion', asShader=True, name='aiSXAO')
        maya.cmds.setAttr('aiSXAO.samples', 8)
        maya.cmds.setAttr('aiSXAO.falloff', 0.1)
        maya.cmds.setAttr('aiSXAO.invertNormals', 0)
        maya.cmds.setAttr('aiSXAO.nearClip', 0.01)
        maya.cmds.setAttr('aiSXAO.farClip', 100)
        maya.cmds.setAttr('aiSXAO.selfOnly', 0)
        print('SX Tools: Creating occlusion material')
        
    if maya.cmds.objExists('SXAOTexture') == False:
        maya.cmds.shadingNode('file', asTexture=True, name='SXAOTexture')
    
    bbox = []
    bakeSet = shapeArray
    modifiers = maya.cmds.getModifiers()
    shift = bool((modifiers & 1) > 0)

    if int(projectSettings['SXToolsMatChannels'][0]) == 1:
        setColorSet('occlusion')

    if toolStates['bakeGroundPlane'] == True:
        maya.cmds.polyPlane( name='sxGroundPlane', w=toolStates['bakeGroundScale'], h=toolStates['bakeGroundScale'], sx=1, sy=1, ax=(0, 1, 0), cuv=2, ch=0 )
        maya.cmds.select(bakeSet)
        selectionManager()

    for bake in bakeSet:
        #create uvAO uvset
        uvList = maya.cmds.polyUVSet(bake, q=True, allUVSets=True)
        if 'uvAO' not in uvList:
            maya.cmds.polyAutoProjection(bake, lm=0, pb=0, ibd=1, cm=1, l=2, sc=1, o=0, p=6, uvSetName='uvAO', ps=0.2, ws=0)

    #bake everything together
    if shift == True:
        if toolStates['bakeGroundPlane'] == True:
            bbox = maya.cmds.exactWorldBoundingBox( bakeSet )
            maya.cmds.setAttr( 'sxGroundPlane.translateY', (bbox[1] - toolStates['bakeGroundOffset']) )
        maya.cmds.arnoldRenderToTexture(bakeSet, resolution=512, shader='aiSXAO', aa_samples=1,
                                        normal_offset=0.001, filter='closest', folder=bakePath, uv_set='uvAO')

    #bake each object separately
    elif shift == False:
        for bake in bakeSet:
            maya.cmds.setAttr( (str(bake) + '.visibility'), False )

        for bake in bakeSet:
            if toolStates['bakeGroundPlane'] == True:
                bbox = maya.cmds.exactWorldBoundingBox( bake )
                bakeTx = getTransforms([bake,])
                groundPos = maya.cmds.getAttr( str(bakeTx[0])+'.translate' )[0]
                maya.cmds.setAttr( 'sxGroundPlane.translateX', groundPos[0] )
                maya.cmds.setAttr( 'sxGroundPlane.translateY', (bbox[1] - toolStates['bakeGroundOffset']) )
                maya.cmds.setAttr( 'sxGroundPlane.translateZ', groundPos[2] )

            maya.cmds.setAttr( (str(bake) + '.visibility'), True )
            maya.cmds.arnoldRenderToTexture(bake, resolution=512, shader='aiSXAO', aa_samples=1,
                                            normal_offset=0.001, filter='closest', folder=bakePath, uv_set='uvAO')
            maya.cmds.setAttr( (str(bake) + '.visibility'), False )

        for bake in bakeSet:
            maya.cmds.setAttr( (str(bake) + '.visibility'), True )
        
    if toolStates['bakeGroundPlane'] == True:
        maya.cmds.delete('sxGroundPlane')
 
    #apply baked maps to occlusion layers
    for bake in bakeSet:
        bakeFileName = bakePath + '/' + str(bake).split('|')[-1] + '.exr'
        maya.cmds.setAttr('SXAOTexture.fileTextureName', bakeFileName, type='string')
        maya.cmds.setAttr('SXAOTexture.filterType', 0)
        maya.cmds.setAttr('SXAOTexture.aiFilter', 0)
        #maya.cmds.setAttr('SXAOTexture.hdrMapping', 'HDR_LINEAR_MAPPING')
        applyTexture('SXAOTexture', 'uvAO', False)
 
    #TODO: Fix HDR mapping, fix UV alpha seams
          
    maya.cmds.select(bakeSet)
    selectionManager()


def applyTexture(texture, uvSetName, applyAlpha):
    colors = []
    color = []
    uCoords = []
    vCoords = []
        
    for shape in shapeArray:
        maya.cmds.polyUVSet (shape, currentUVSet=True, uvSet=uvSetName)
                
        components = maya.cmds.ls(maya.cmds.polyListComponentConversion(shape, tv=True), fl=True)

        for component in components:
            fvs = maya.cmds.ls(maya.cmds.polyListComponentConversion(component, tvf=True), fl=True)
            uvs = maya.cmds.ls(maya.cmds.polyListComponentConversion(fvs, tuv=True), fl=True)
            for uv in uvs:
                uvCoord = maya.cmds.polyEditUV(uv, query=True)
                colors.append(maya.cmds.colorAtPoint(texture, o='RGBA', u=uvCoord[0], v=uvCoord[1]))
            for tmpColor in colors:
                if tmpColor[3] == 1:
                    color = tmpColor

            if applyAlpha == False:
                if 1 <= color[3] > 0:
                    maya.cmds.polyColorPerVertex(component,
                                            r=color[0]/color[3],
                                            g=color[1]/color[3],
                                            b=color[2]/color[3],
                                            a=1)
                else:
                    maya.cmds.polyColorPerVertex(component,
                                            r=color[0],
                                            g=color[1],
                                            b=color[2],
                                            a=1)
            else:
                if 1<= color[3] > 0:
                    maya.cmds.polyColorPerVertex(component,
                                            r=color[0]/color[3],
                                            g=color[1]/color[3],
                                            b=color[2]/color[3],
                                            a=color[3])
                else:
                    maya.cmds.polyColorPerVertex(component,
                                            r=color[0],
                                            g=color[1],
                                            b=color[2],
                                            a=color[3])

    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
    refreshLayerList()
    refreshSelectedItem()
    

def calculateCurvature(objects):
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
                angle = math.acos(vtxNormals[i].normal()*edge.normal())
                curvature = (angle / math.pi - 0.5) / edge.length()
                vtxCurvature += curvature

            vtxCurvature = (vtxCurvature / numConnected + 0.5)
            if vtxCurvature > 1.0:
                vtxCurvature = 1.0
            outColor = maya.cmds.colorAtPoint( 'SXRamp', o='RGB', u=(0), v=(vtxCurvature) )
            outAlpha = maya.cmds.colorAtPoint( 'SXAlphaRamp', o='A', u=(0), v=(vtxCurvature) )

            vtxColors[i].r = outColor[0]
            vtxColors[i].g = outColor[1]
            vtxColors[i].b = outColor[2]
            vtxColors[i].a = outAlpha[0]
            
            vtxIt.next()
        
        MFnMesh.setVertexColors(vtxColors, vtxIds)

    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
    refreshLayerList()
    refreshSelectedItem()


def applyMasterPalette(objects):
    for object in objects:
        for i in range(0, 5):
            layers = maya.cmds.polyColorSet( query=True, allColorSets=True )
            maya.cmds.palettePort( 'masterPalette', edit=True, scc=i ) 
            currentColor = maya.cmds.palettePort( 'masterPalette', query=True, rgb=True )
            maya.cmds.polyColorSet(currentColorSet=True, colorSet=str(layers[i]))        
            maya.cmds.polyColorPerVertex(r=currentColor[0], g=currentColor[1], b=currentColor[2])


def gradientFill(axis):
    if len(componentArray) > 0:
        components = maya.cmds.ls(maya.cmds.polyListComponentConversion(componentArray, tvf=True), fl=True)
        # tempFaceArray is constructed because polyEvaluate doesn't work on face vertices
        tempFaceArray = maya.cmds.ls(maya.cmds.polyListComponentConversion(componentArray, tf=True), fl=True)
        maya.cmds.select(tempFaceArray)
        objectBounds = maya.cmds.polyEvaluate(bc=True, ae=True)
    else:
        components = maya.cmds.ls(maya.cmds.polyListComponentConversion(shapeArray, tv=True), fl=True)
        objectBounds = maya.cmds.polyEvaluate(shapeArray, b=True, ae=True)
                            
    objectBoundsXmin = objectBounds[0][0]
    objectBoundsXmax = objectBounds[0][1]
    objectBoundsYmin = objectBounds[1][0]
    objectBoundsYmax = objectBounds[1][1]
    objectBoundsZmin = objectBounds[2][0]
    objectBoundsZmax = objectBounds[2][1]
        
    for component in components:
        compPos = maya.cmds.xform( component, query=True, worldSpace=True, translation=True )
        if axis == 1:
            ratioRaw = (compPos[0] - objectBoundsXmin) / (objectBoundsXmax - objectBoundsXmin)
            ratio = max(min(ratioRaw, 1), 0)
            compColor = maya.cmds.colorAtPoint( 'SXRamp', o='RGB', u=(ratio), v=(ratio) )
            compAlpha = maya.cmds.colorAtPoint( 'SXAlphaRamp', o='A', u=(ratio), v=(ratio) )
            maya.cmds.polyColorPerVertex(component,
                                    r=compColor[0],
                                    g=compColor[1],
                                    b=compColor[2],
                                    a=compAlpha[0] )
        elif axis == 2:
            ratioRaw = (compPos[1] - objectBoundsYmin) / (objectBoundsYmax - objectBoundsYmin)
            ratio = max(min(ratioRaw, 1), 0)
            compColor = maya.cmds.colorAtPoint( 'SXRamp', o='RGB', u=(ratio), v=(ratio) )
            compAlpha = maya.cmds.colorAtPoint( 'SXAlphaRamp', o='A', u=(ratio), v=(ratio) )
            maya.cmds.polyColorPerVertex(component,
                                    r=compColor[0],
                                    g=compColor[1],
                                    b=compColor[2],
                                    a=compAlpha[0] )
        elif axis == 3:
            ratioRaw = (compPos[2] - objectBoundsZmin) / (objectBoundsZmax - objectBoundsZmin)
            ratio = max(min(ratioRaw, 1), 0)
            compColor = maya.cmds.colorAtPoint( 'SXRamp', o='RGB', u=(ratio), v=(ratio) )
            compAlpha = maya.cmds.colorAtPoint( 'SXAlphaRamp', o='A', u=(ratio), v=(ratio) )
            maya.cmds.polyColorPerVertex(component,
                                    r=compColor[0],
                                    g=compColor[1],
                                    b=compColor[2],
                                    a=compAlpha[0] )
    
    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
    refreshLayerList()
    refreshSelectedItem()


def colorFill():
    alphaMax = layerAlphaMax
    
    if alphaMax != 0:
        fillAlpha = alphaMax
    else:
        fillAlpha = 1
        
    fillColor = maya.cmds.colorSliderGrp('sxApplyColor', query=True, rgbValue=True)
    if len(componentArray) > 0:
        maya.cmds.polyColorPerVertex(componentArray,
                                r=fillColor[0],
                                g=fillColor[1],
                                b=fillColor[2],
                                a=fillAlpha,
                                representation=4, cdo=True)
    else:
        maya.cmds.polyColorPerVertex(shapeArray,
                                r=fillColor[0],
                                g=fillColor[1],
                                b=fillColor[2],
                                a=fillAlpha,
                                representation=4, cdo=True)        
    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
    refreshLayerList()
    refreshSelectedItem()


def colorNoise(objects):
    for object in objects:
        mono = toolStates['noiseMonochrome']
        value = toolStates['noiseValue']
        layer = getSelectedLayer()

        selectionList = OM.MSelectionList()
        selectionList.add(object)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        vtxColors = OM.MColorArray()
        vtxColors = MFnMesh.getVertexColors(colorSet = layer)
        vtxIds = OM.MIntArray()
        
        lenSel = len(vtxColors)
        vtxIds.setLength(lenSel)
       
        vtxIt = OM.MItMeshVertex(nodeDagPath)

        while not vtxIt.isDone():
            i = vtxIt.index()
            vtxIds[i] = vtxIt.index()

            if mono == True:
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


def remapRamp(object):
    layer = getSelectedLayer()

    selectionList = OM.MSelectionList()
    selectionList.add(object)
    nodeDagPath = OM.MDagPath()
    nodeDagPath = selectionList.getDagPath(0)
    MFnMesh = OM.MFnMesh(nodeDagPath)

    layerColors = OM.MColorArray()
    layerColors = MFnMesh.getFaceVertexColors(colorSet = layer)

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
        luminance = (fvCol.r + fvCol.r + fvCol.b + fvCol.g + fvCol.g + fvCol.g)/6
        outColor = maya.cmds.colorAtPoint( 'SXRamp', o='RGB', u=luminance, v=luminance )
        outAlpha = maya.cmds.colorAtPoint( 'SXAlphaRamp', o='A', u=luminance, v=luminance )
        layerColors[k].r = outColor[0]
        layerColors[k].g = outColor[1]
        layerColors[k].b = outColor[2]
        layerColors[k].a = outAlpha[0]
                
        k += 1
        fvIt.next()

    MFnMesh.setFaceVertexColors(layerColors, faceIds, vtxIds, mod, colorRep)  


def swapLayers(object):
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    
    layerA = maya.cmds.textField('layerA', query=True, text=True)
    layerB = maya.cmds.textField('layerB', query=True, text=True)

    selected = str(shapeArray[len(shapeArray)-1])

    if (layerA in refLayers) and (layerB in refLayers):

        attrA = '.'+layerA+'BlendMode'
        modeA = maya.cmds.getAttr(selected+attrA)
        attrB = '.'+layerB+'BlendMode'
        modeB = maya.cmds.getAttr(selected+attrB)

        selectionList = OM.MSelectionList()
        selectionList.add(object)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerAColors = OM.MColorArray()
        layerAColors = MFnMesh.getFaceVertexColors(colorSet = layerA)
        layerBColors = OM.MColorArray()
        layerBColors = MFnMesh.getFaceVertexColors(colorSet = layerB)
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
        
        maya.cmds.setAttr(selected+attrA, modeB)
        maya.cmds.setAttr(selected+attrB, modeA)

        getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
        refreshLayerList()
        refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)
    else:
        print('SXTools Error: Invalid layers!')


def copyLayer(objects):
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    
    layerA = maya.cmds.textField('layersrc', query=True, text=True)
    layerB = maya.cmds.textField('layertgt', query=True, text=True)

    if (layerA in refLayers) and (layerB in refLayers): 
        for idx, obj in enumerate(objects):
            selected = str(shapeArray[idx])
            attrA = '.'+layerA+'BlendMode'
            modeA = maya.cmds.getAttr(selected+attrA)
            attrB = '.'+layerB+'BlendMode'

            selectionList = OM.MSelectionList()
            selectionList.add(obj)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerAColors = OM.MColorArray()
            layerAColors = MFnMesh.getFaceVertexColors(colorSet = layerA)

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
            
            maya.cmds.setAttr(selected+attrB, modeA)
    else:
        print('SXTools Error: Invalid layers!')

    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
    refreshLayerList()
    refreshSelectedItem()
    maya.cmds.shaderfx(sfxnode='SXShader', update=True)


# Layer management functions
# --------------------------------------------------------------------

def mergeLayers(object, sourceLayer, targetLayer):
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())

    selected = str(object)
    attr = '.'+str(getSelectedLayer())+'BlendMode'
    mode = int(maya.cmds.getAttr(selected+attr))
    
    # NOTE: polyBlendColor is used to copy existing color sets
    # to new list positions because Maya's color set copy function is bugged.

    if mode == 0:
        maya.cmds.polyBlendColor (selected, bcn=str(targetLayer), src=str(sourceLayer), dst=str(targetLayer), bfn=0, ch=False)
    else:
        selectionList = OM.MSelectionList()
        selectionList.add(object)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        sourceLayerColorArray = OM.MColorArray()
        targetLayerColorArray = OM.MColorArray()
        sourceLayerColorArray = MFnMesh.getFaceVertexColors(colorSet = sourceLayer)
        targetLayerColorArray = MFnMesh.getFaceVertexColors(colorSet = targetLayer)
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

                targetLayerColorArray[k].r += sourceLayerColorArray[k].r * sourceLayerColorArray[k].a 
                targetLayerColorArray[k].g += sourceLayerColorArray[k].g * sourceLayerColorArray[k].a 
                targetLayerColorArray[k].b += sourceLayerColorArray[k].b * sourceLayerColorArray[k].a
                targetLayerColorArray[k].a += sourceLayerColorArray[k].a
                k += 1
                fvIt.next()
        elif mode == 2:
            #layer2 lerp with white using (1-alpha), multiply with layer1
            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()

                sourceLayerColorArray[k].r = ((sourceLayerColorArray[k].r
                                               * sourceLayerColorArray[k].a)
                                               + (1.0 * (1-sourceLayerColorArray[k].a)))
                sourceLayerColorArray[k].g = ((sourceLayerColorArray[k].g
                                               * sourceLayerColorArray[k].a)
                                               + (1.0 * (1-sourceLayerColorArray[k].a)))
                sourceLayerColorArray[k].b = ((sourceLayerColorArray[k].b
                                               * sourceLayerColorArray[k].a)
                                               + (1.0 * (1-sourceLayerColorArray[k].a)))
                
                targetLayerColorArray[k].r = sourceLayerColorArray[k].r * targetLayerColorArray[k].r
                targetLayerColorArray[k].g = sourceLayerColorArray[k].g * targetLayerColorArray[k].g
                targetLayerColorArray[k].b = sourceLayerColorArray[k].b * targetLayerColorArray[k].b
                k += 1
                fvIt.next()
        else:
            print('SX Tools Error: Invalid blend mode')
            return

        maya.cmds.polyColorSet(selected, currentColorSet=True, colorSet=str(targetLayer))
        MFnMesh.setFaceVertexColors(targetLayerColorArray, faceIds, vtxIds)      

    maya.cmds.polyColorSet(selected, delete=True, colorSet=str(sourceLayer) )


# If mesh color sets don't match the reference layers.
# Sorts the existing color sets to the correct order,
# and fills the missing slots with default layers.
def patchLayers(objects):
    noColorSetObject = []

    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())

    for object in objects:
        currentColorSets = maya.cmds.polyColorSet(object, query=True, allColorSets=True)
        if currentColorSets is not None:
            for layer in refLayers:
                maya.cmds.select(object)
                found = False

                for colorSet in currentColorSets:
                    if colorSet == layer:
                        # NOTE: polyBlendColor is used to copy existing color sets to new list positions
                        # because Maya's color set copy function is broken, and either generates empty color sets,
                        # or copies from wrong indices.
                        maya.cmds.polyColorSet(object, rename=True, colorSet=str(colorSet), newColorSet='tempColorSet' )
                        maya.cmds.polyColorSet(object, create=True, clamped=True, representation='RGBA', colorSet=str(layer))
                        maya.cmds.polyBlendColor (object, bcn=str(layer), src='tempColorSet', dst=str(layer), bfn=0, ch=False)
                        maya.cmds.polyColorSet(object, delete=True, colorSet='tempColorSet' )
                        found = True
                  
                if found == False:
                    maya.cmds.polyColorSet(object, create=True, clamped=True, representation='RGBA', colorSet=str(layer))
                    clearSelectedLayer([object,], layer)
    
            maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=refLayers[0])
            maya.cmds.sets(object, e=True, forceElement='SXShaderSG')
        else:
            noColorSetObject.append(object)
    
    if len(noColorSetObject) > 0:
        resetLayers(noColorSetObject)

    maya.cmds.select(selectionArray)
    selectionManager()


def mergeLayerUp():
    sourceLayer = getSelectedLayer()
    if len(shapeArray) > 1:
        print 'SX Tools: Merge Layer should not be performed with multi-selection'
        return
    elif str(sourceLayer) == 'layer1':
        print('SX Tools Error: Cannot merge layer1')
        return
    elif ((str(sourceLayer) == 'occlusion') or
          (str(sourceLayer) == 'specular') or
          (str(sourceLayer) == 'transmission') or
          (str(sourceLayer) == 'emission')):
        print('SX Tools Error: Cannot merge material channels')
        return

    layerIndex = projectSettings['SXToolsRefIndices'][sourceLayer]
    targetLayer = projectSettings['SXToolsRefNames'][layerIndex-1]

    mergeLayers(shapeArray[len(shapeArray)-1], sourceLayer, targetLayer)
    patchLayers([shapeArray[len(shapeArray)-1]],)
    maya.cmds.polyColorSet(currentColorSet=True, colorSet=str(targetLayer))
    refreshLayerList()
    refreshSelectedItem()

# IF mesh has no color sets at all,
# or non-matching color set names.
def resetLayers(objects):
    for object in objects:
        # Remove existing color sets, if any
        colorSets = maya.cmds.polyColorSet(object, query=True, allColorSets=True)
        if colorSets is not None:
            for colorSet in colorSets:
                maya.cmds.polyColorSet(object, delete=True, colorSet=colorSet)

        # Create color sets        
        for layer in sortLayers(projectSettings['SXToolsRefLayers'].keys()):
            maya.cmds.polyColorSet(object, create=True, clamped=True, representation='RGBA', colorSet=str(layer))
            clearSelectedLayer([object,], layer)
            maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=str(layer))

        maya.cmds.polyColorSet(object, currentColorSet=True, colorSet='layer1')
        maya.cmds.sets(object, e=True, forceElement='SXShaderSG')


def clearSelectedLayer(objects, layer):
    for object in objects:
        maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=layer)
        
        color = projectSettings['SXToolsRefLayers'][layer] 
        maya.cmds.polyColorPerVertex(object, r=color[0], g=color[1], b=color[2], a=color[3], representation=4, cdo=True)
        attr = '.'+str(layer)+'BlendMode'
        maya.cmds.setAttr(str(object)+attr, 0)
    if maya.cmds.objExists('SXShader'):
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)


def clearSelectedComponents(layer):
    object = shapeArray[len(shapeArray)-1]
    maya.cmds.polyColorSet(object, currentColorSet=True, colorSet=layer)

    color = projectSettings['SXToolsRefLayers'][layer]
    maya.cmds.polyColorPerVertex(r=color[0], g=color[1], b=color[2], a=color[3], representation=4, cdo=True)
    attr = '.'+str(layer)+'BlendMode'
    maya.cmds.setAttr(str(object)+attr, 0)
    if maya.cmds.objExists('SXShader'):
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)


def clearAllLayers():
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    for layer in refLayers:
        clearSelectedLayer(shapeArray, layer)


# Called when the user double-clicks a layer in the tool UI
def toggleLayer(layer):
    object = shapeArray[len(shapeArray)-1]
    checkState = maya.cmds.getAttr(str(object)+'.'+str(layer)+'Visibility')
    for shape in shapeArray:
        maya.cmds.setAttr(str(shape)+'.'+str(layer)+'Visibility', not checkState)
        state = verifyLayerState(layer)
        layerIndex = int(maya.cmds.textScrollList('layerList', query=True, selectIndexedItem=True)[0])
        maya.cmds.textScrollList('layerList', edit=True, removeIndexedItem=layerIndex)
        maya.cmds.textScrollList('layerList', edit=True, appendPosition=(layerIndex, state))
        maya.cmds.textScrollList('layerList', edit=True, selectIndexedItem=layerIndex)


# Called when the user hides or shows all vertex color layers in the tool UI
def toggleAllLayers():
    layers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    for layer in layers:
        toggleLayer(layer)

    refreshLayerList()
    refreshSelectedItem()
    maya.cmds.shaderfx(sfxnode='SXShader', update=True)


# Updates the tool UI to highlight the current color set
def setColorSet(highlightedLayer):
    for shape in shapeArray:
        maya.cmds.polyColorSet(shape, currentColorSet=True, colorSet=highlightedLayer)


# This function populates the layer list in the tool UI.
def refreshLayerList():
    if maya.cmds.textScrollList('layerList', exists=True):
        maya.cmds.textScrollList('layerList', edit=True, removeAll=True)
    
    layers = sortLayers(projectSettings['SXToolsRefLayers'].keys())    
    
    for layer in layers:
        state = verifyLayerState(layer)
        maya.cmds.textScrollList( 'layerList', edit=True,
                            append=state, numberOfRows=(projectSettings['SXToolsLayerCount']+projectSettings['SXToolsChannelCount']),
                            selectCommand=("sxtools.setColorSet(sxtools.getSelectedLayer())\n"
                                           "sxtools.getLayerPaletteOpacity(sxtools.shapeArray[len(sxtools.shapeArray)-1], sxtools.getSelectedLayer())\n"
                                           "maya.cmds.text( 'layerOpacityLabel', edit=True, label=str(sxtools.getSelectedLayer())+' opacity:' )\n"
                                           "maya.cmds.text( 'layerColorLabel', edit=True, label=str(sxtools.getSelectedLayer())+' colors:' )"),
                            doubleClickCommand=("sxtools.toggleLayer(sxtools.getSelectedLayer())\n"
                                                "maya.cmds.shaderfx(sfxnode='SXShader', update=True)") )


def refreshSelectedItem():
    selectedColorSet = str(maya.cmds.polyColorSet(shapeArray[len(shapeArray)-1], query=True, currentColorSet=True)[0])
    maya.cmds.textScrollList( 'layerList', edit=True, selectIndexedItem=projectSettings['SXToolsRefIndices'][selectedColorSet] )


def sortLayers(layers):
    global refArray
    sortedLayers = []
        
    if layers is not None:
        layerCount = len(layers)
        for ref in refArray:
            if ref in layers:
                sortedLayers.append(ref)
    
    return sortedLayers


def verifyLayerState(layer):
    object = shapeArray[len(shapeArray)-1]
    selectionList = OM.MSelectionList()
    selectionList.add(shapeArray[len(shapeArray)-1])
    nodeDagPath = OM.MDagPath()
    nodeDagPath = selectionList.getDagPath(0)
    MFnMesh = OM.MFnMesh(nodeDagPath)

    layerColors = OM.MColorArray()
    layerColors = MFnMesh.getFaceVertexColors(colorSet=layer)

    # States: visibility, mask, adjustment
    state = [False, False, False]

    state[0] = maya.cmds.getAttr(str(object)+'.'+str(layer)+'Visibility')
    
    for k in range(len(layerColors)):
        if (layerColors[k].a > 0 and layerColors[k].a < projectSettings['SXToolsAlphaTolerance']):
            state[2] = True
        elif (layerColors[k].a >= projectSettings['SXToolsAlphaTolerance'] and layerColors[k].a <= 1):
            state[1] = True

    if state[0] == False:
        hidden = '(H)'
    else:
        hidden = ''
    if state[1] == True:
        mask = '(M)'
    else:
        mask = ''
    if state[2] == True:
        adj = '(A)'
    else:
        adj = ''
        
    itemString = layer + '\t' + hidden + mask + adj
    return itemString
    

# Maps the selected list item in the layerlist UI to the parameters of the pre-vis material
# and object colorsets
def getSelectedLayer():
    if len(objectArray) == 0:
        return (projectSettings['SXToolsRefNames'][1])

    selectedIndex = maya.cmds.textScrollList('layerList', query=True, selectIndexedItem=True)
    if selectedIndex is None:
        maya.cmds.textScrollList('layerList', edit=True, selectIndexedItem=1)
        selectedIndex = 1
    else:
        selectedIndex = int(selectedIndex[0])

    # Blend modes are only valid for color layers, not material channels
    if 'layer' not in projectSettings['SXToolsRefNames'][selectedIndex]:
        maya.cmds.optionMenu( 'layerBlendModes', edit=True, enable=False )
    else:
        selected = str(shapeArray[len(shapeArray)-1])
        attr = '.'+projectSettings['SXToolsRefNames'][selectedIndex]+'BlendMode'
        mode = maya.cmds.getAttr(selected+attr)+1
        maya.cmds.optionMenu( 'layerBlendModes', edit=True, select=mode, enable=True )

    return (projectSettings['SXToolsRefNames'][selectedIndex]) 


# Color sets of any selected object are checked to see if they match the reference set.
def verifyObjectLayers(objects):
    refLayers = sortLayers(projectSettings['SXToolsRefLayers'].keys())
    nonStdObjs = []
    empty = False

    setPrimVars()

    for object in objects:
        testLayers = maya.cmds.polyColorSet(object, query=True, allColorSets=True)
        if testLayers is None:
            nonStdObjs.append(object)
            empty = True
        elif refLayers == 'layer1' and len(testLayers) == 1 and str(testLayers[0]) == refLayers:
            return 0, None
        elif testLayers != refLayers:
            nonStdObjs.append(object)
            empty = False

    if len(nonStdObjs) > 0 and empty == True:
        return 1, nonStdObjs
    elif len(nonStdObjs) > 0 and empty == False:
        return 2, nonStdObjs
    else:
        return 0, None


def verifyShadingMode():
    if len(shapeArray) > 0:
        object = shapeArray[len(shapeArray)-1]
        mode = int(maya.cmds.getAttr(object+'.shadingMode')+1)
        
        objectLabel = 'Selected Objects: '+str(len(shapeArray))
        maya.cmds.frameLayout( 'layerFrame', edit=True, label=objectLabel )
        maya.cmds.radioButtonGrp( 'shadingButtons', edit=True, select=mode )
        return mode


def setShadingMode(mode):
    for shape in shapeArray:
        maya.cmds.setAttr(str(shape)+'.shadingMode', mode)
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)


def checkHistory(objList):
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
  
    if history == True:
        print('SX Tools: History found: ' + str(histList))
        maya.cmds.columnLayout('warningLayout', parent='canvas', rowSpacing=5, adjustableColumn=True)
        maya.cmds.text( label='WARNING: Objects with construction history!',
                  backgroundColor=(0.35, 0.1, 0), ww=True )
        maya.cmds.button( label='Delete History',
                          command='maya.cmds.delete(sxtools.objectArray, ch=True)\nsxtools.updateSXTools()' )


# After a selection of meshes has been processed for export,
# the user has a button in the tool UI that allows an isolated view of the results.
def viewExported():
    maya.cmds.select('_staticExports')
    maya.cmds.setAttr( 'exportsLayer.visibility', 1 )
    maya.cmds.setAttr( 'assetsLayer.visibility', 0 )
    maya.mel.eval('FrameSelectedWithoutChildren;')
    maya.mel.eval('fitPanel -selectedNoChildren;')


# Processed meshes no longer have the pre-vis material,
# so the tool must present a different UI when any of these are selected.
def checkExported(objects):
    if len(objectArray) > 0:
        for obj in objects:
            parent = maya.cmds.listRelatives(str(obj), parent=True)
            if parent is not None:
                if str(parent[0]) == '_staticExports':
                    return True
                    break
                elif str(obj).endswith('_paletted') == True:
                    return True
                    break
                elif str(obj).endswith('_transparent') == True:
                    return True
                    break
            elif parent is None:
                if str(obj) == '_staticExports':
                    return True
                    break
    else:
        return False


def viewExportedMaterial():
    global exportNodeDict

    buttonState1 = maya.cmds.radioButtonGrp( 'exportShadingButtons1', query=True, select=True)
    buttonState2 = maya.cmds.radioButtonGrp( 'exportShadingButtons2', query=True, select=True)
    matChannels = projectSettings['SXToolsMatChannels']
    uvChannels = projectSettings['SXToolsExportChannels']

    # Composite
    if buttonState1 == 1:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXPBShaderSG')
            maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='ambientDiffuse', colorShadedDisplay=True)
            maya.mel.eval('DisplayLight;')

    # Albedo
    elif buttonState1 == 2:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXExportShaderSG')
        chanID = uvChannels[0]
        chanAxis = str(chanID[0])
        chanIndex = chanID[1]
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['colorBool'], 'value', True)) 

    # Layer Masks
    elif buttonState1 == 3:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXExportShaderSG')
        chanID = uvChannels[0]
        chanAxis = str(chanID[0])
        chanIndex = chanID[1]
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['colorBool'], 'value', False))

    # Occlusion
    elif buttonState2 == 1:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXExportShaderSG')
        chanID = uvChannels[1]
        chanAxis = str(chanID[0])
        chanIndex = chanID[1]
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['colorBool'], 'value', False))

    # Specular
    elif buttonState2 == 2:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXExportShaderSG')
        chanID = uvChannels[2]
        chanAxis = str(chanID[0])
        chanIndex = chanID[1]
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['colorBool'], 'value', False))

    # Transmission
    elif buttonState2 == 3:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXExportShaderSG')
        chanID = uvChannels[3]
        chanAxis = str(chanID[0])
        chanIndex = chanID[1]
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['colorBool'], 'value', False))

    # Emission
    elif buttonState2 == 4:
        for shape in shapeArray:
            maya.cmds.sets(e=True, forceElement='SXExportShaderSG')
        chanID = uvChannels[4]
        chanAxis = str(chanID[0])
        chanIndex = chanID[1]
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['colorBool'], 'value', False))

    if buttonState1 != 1:
        maya.cmds.shaderfx(sfxnode='SXExportShader', edit_int=( exportNodeDict['uvIndex'], 'value', int(chanIndex)))
        if chanAxis == 'U':
            maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['uvBool'], 'value', True))
        elif chanAxis == 'V':
            maya.cmds.shaderfx(sfxnode='SXExportShader', edit_bool=( exportNodeDict['uvBool'], 'value', False))
        
        maya.cmds.shaderfx(sfxnode='SXExportShader', update=True)


# Called from a button the tool UI that clears either the selected layer or the selected components in a layer
def clearSelector():
    modifiers = maya.cmds.getModifiers()
    shift = bool((modifiers & 1) > 0)
    if shift == True:
        clearAllLayers()
    elif shift == False:
        if len(componentArray) > 0:
            clearSelectedComponents(getSelectedLayer())
        else:
            clearSelectedLayer(shapeArray, getSelectedLayer())


# Converts a selection of Maya shape nodes to their transform nodes
def getTransforms(shapeList, fullPath=False):
    transforms = []
    for node in shapeList:
        if 'transform' != maya.cmds.nodeType( node ):
            parent = maya.cmds.listRelatives( node, fullPath=True, parent=True )
            transforms.append( parent[0] )
    return transforms


def setLayerOpacity():
    alphaMax = layerAlphaMax
    
    for shape in shapeArray:
        layer = getSelectedLayer()
        sliderAlpha = maya.cmds.floatSlider('layerOpacitySlider', query=True, value=True)

        selectionList = OM.MSelectionList()
        selectionList.add(shape)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColorArray = OM.MColorArray()
        layerColorArray = MFnMesh.getFaceVertexColors(colorSet = layer)
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
                layerColorArray[k].a = layerColorArray[k].a/alphaMax*sliderAlpha
            k += 1
            fvIt.next()

        MFnMesh.setFaceVertexColors(layerColorArray, faceIds, vtxIds)

        if (str(layer) == 'layer1') and (sliderAlpha < 1):
            maya.cmds.setAttr(str(shape)+'.transparency', 1)
            if alphaMax == 1:
                maya.cmds.shaderfx(sfxnode='SXShader', makeConnection=(nodeDict['transparencyComp'], 0, nodeDict['SXShader'], 0))
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)
        elif (str(layer) == 'layer1') and (sliderAlpha == 1):
            maya.cmds.setAttr(str(shape)+'.transparency', 0)
            if alphaMax < 1:
                maya.cmds.shaderfx(sfxnode='SXShader', breakConnection=(nodeDict['transparencyComp'], 0, nodeDict['SXShader'], 0))
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)            

    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())


def getLayerMask():
    maskList = []

    for shape in shapeArray:
        vertFaceList = maya.cmds.ls(maya.cmds.polyListComponentConversion(shape, tvf=True), fl=True)
        
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift == True:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(vertFace, query=True, a=True)[0] == 0:
                    maskList.append(vertFace)
        elif shift == False:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(vertFace, query=True, a=True)[0] > 0:
                    maskList.append(vertFace)
                    
        if len(maskList) == 0:
            print('SX Tools: No layer mask found')
            return selectionArray
        
    return maskList


def getLayerPaletteOpacity(object,layer):            
    global layerAlphaMax

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
                    
        if (match == False) and (n < 8):
            layerPaletteArray[n] = layerColorArray[k]
            n += 1
            

        if layerColorArray[k].a > alphaMax:
            alphaMax = layerColorArray[k].a
            
    if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
        maya.cmds.floatSlider('layerOpacitySlider', edit=True, value=alphaMax)
        layerAlphaMax = alphaMax

    for k in range(0, 8):           
        maya.cmds.palettePort( 'layerPalette', edit=True,
                         rgb=(k, layerPaletteArray[k].r,
                              layerPaletteArray[k].g,
                              layerPaletteArray[k].b) )
        maya.cmds.palettePort( 'layerPalette', edit=True, redraw=True )

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

                
def setPaintColor():
    global currentColor
    currentColor = maya.cmds.palettePort( 'layerPalette', query=True, rgb=True )    
    maya.cmds.colorSliderGrp('sxApplyColor', edit=True, rgbValue=currentColor)
    if maya.cmds.artAttrPaintVertexCtx('artAttrColorPerVertexContext', exists=True):
        numChannels = maya.cmds.artAttrPaintVertexCtx('artAttrColorPerVertexContext',
                                                 query=True, paintNumChannels=True)
        if numChannels == 3:
            maya.cmds.artAttrPaintVertexCtx('artAttrColorPerVertexContext',
                                       edit=True, usepressure=False,
                                       colorRGBValue=[currentColor[0],
                                                      currentColor[1],
                                                      currentColor[2]])
        elif numChannels == 4:
            maya.cmds.artAttrPaintVertexCtx('artAttrColorPerVertexContext',
                                       edit=True, usepressure=False,
                                       colorRGBAValue=[currentColor[0],
                                                       currentColor[1],
                                                       currentColor[2], 1])


def setApplyColor():
    global currentColor
    currentColor = maya.cmds.palettePort( 'recentPalette', query=True, rgb=True )
    maya.cmds.colorSliderGrp('sxApplyColor', edit=True, rgbValue=currentColor)


def getCurrentColor():
    global currentColor
    maya.cmds.colorSliderGrp('sxApplyColor', edit=True, rgbValue=currentColor)


def updateRecentPalette():
    addedColor = maya.cmds.colorSliderGrp('sxApplyColor', query=True, rgbValue=True)
    swapColorArray = []
    
    for k in range(0, 7):
        maya.cmds.palettePort( 'recentPalette', edit=True, scc=k )
        swapColorArray.append(maya.cmds.palettePort('recentPalette', query=True, rgb=True))

    if (addedColor in swapColorArray) == False:
        for k in range(7, 0, -1):
            maya.cmds.palettePort( 'recentPalette', edit=True,
                             rgb=(k, swapColorArray[k-1][0],
                                  swapColorArray[k-1][1],
                                  swapColorArray[k-1][2]) )
            
        maya.cmds.palettePort( 'recentPalette', edit=True, scc=0 )         
        maya.cmds.palettePort( 'recentPalette', edit=True, rgb=(0, addedColor[0], addedColor[1], addedColor[2]) )
        maya.cmds.palettePort( 'recentPalette', edit=True, redraw=True )
    else:
        idx = swapColorArray.index(addedColor)
        maya.cmds.palettePort( 'recentPalette', edit=True, scc=idx )
        
    storePalette('recentPalette', paletteDict, 'SXToolsRecentPalette')


def storePalette(paletteUI, targetDict, preset):
    currentCell = maya.cmds.palettePort( paletteUI, query=True, scc=True )
    paletteLength = maya.cmds.palettePort( paletteUI, query=True, actualTotal=True )
    paletteArray = []
    for i in range(0, paletteLength):
        maya.cmds.palettePort( paletteUI, edit=True, scc=i ) 
        currentColor = maya.cmds.palettePort( paletteUI, query=True, rgb=True )
        paletteArray.append(currentColor)
        
    targetDict[preset] = paletteArray
                                  
    maya.cmds.palettePort( paletteUI, edit=True, scc=currentCell ) 


def getPalette(paletteUI, targetDict, preset):
    if preset in targetDict:
        presetColors = targetDict[preset]
        
        for idx, color in enumerate(presetColors):
            maya.cmds.palettePort( paletteUI, edit=True,
                             rgb=(idx, color[0], color[1], color[2]) )
        maya.cmds.palettePort( paletteUI, edit=True, redraw=True )


def deletePalette(targetDict, preset):
    del targetDict[preset]
    if toolStates['palettePreset'] == preset:
        toolStates['palettePreset'] = None


def saveMasterPalette():    
    modifiers = maya.cmds.getModifiers()
    shift = bool((modifiers & 1) > 0)

    if shift == True:
        preset = maya.cmds.optionMenu( 'masterPalettes', query=True, value=True )
        if preset is not None:
            deletePalette(masterPaletteDict, preset)
            maya.cmds.deleteUI(preset)
            savePreferences()
            getMasterPaletteItem()
        else:
            print 'SX Tools Error: No preset to delete!'

    elif shift == False:
        itemList = maya.cmds.optionMenu( 'masterPalettes', query=True, ils=True )
        preset = maya.cmds.textField( 'savePaletteName', query=True, text=True )
        if (len(preset) > 0) and ((itemList is None) or (preset not in itemList)):
            toolStates['palettePreset'] = preset
            storePalette('masterPalette', masterPaletteDict, preset)
            maya.cmds.menuItem(preset, label=preset, parent='masterPalettes' )
            itemList = maya.cmds.optionMenu( 'masterPalettes', query=True, ils=True )
            idx =  itemList.index(preset) + 1
            maya.cmds.optionMenu( 'masterPalettes', edit=True, select=idx )
            savePreferences()
        else:
            print 'SX Tools Error: Invalid preset name!'


def getMasterPaletteItem():
    if len(masterPaletteDict) > 0:
        preset = maya.cmds.optionMenu( 'masterPalettes', query=True, value=True )
        getPalette('masterPalette', masterPaletteDict, preset)
        toolStates['palettePreset'] = preset
        storePalette('masterPalette', paletteDict, 'SXToolsMasterPalette')


def gradientToolManager(mode, group=1):
    modifiers = maya.cmds.getModifiers()
    shift = bool((modifiers & 1) > 0)

    if mode =='load':
        clearRamp('SXRamp')
        name = maya.cmds.optionMenu('rampPresets', query=True, value=True)
        maya.cmds.nodePreset( load=('SXRamp', name))
    elif mode == 'preset' and shift == True:
        presetNameArray = maya.cmds.nodePreset( list='SXRamp' )
        if len(presetNameArray) > 0:
            maya.cmds.nodePreset( delete=('SXRamp', maya.cmds.optionMenu('rampPresets', query=True, value=True)) )
        elif len(presetNameArray) == 0:
            print 'SXTools: Preset list empty!'
    elif mode == 'preset' and shift == False:
        name = maya.cmds.textField('presetName', query=True, text=True)
        if len(name) > 0:
            maya.cmds.nodePreset( save=('SXRamp', name) )
        elif len(name) == 0:
            print 'SXTools: Invalid preset name!'
    elif group == 1:
        if mode == 2:
            projectSettings['SXToolsGradientDirection'] = 5
            calculateCurvature(objectArray)
        elif mode == 1:
            projectSettings['SXToolsGradientDirection'] = 4
            remapRamp(shapeArray[len(shapeArray)-1])
    else:
        projectSettings['SXToolsGradientDirection'] = mode
        gradientFill(mode)


def clearRamp(rampName):
    indexList = maya.cmds.getAttr( rampName + '.colorEntryList', multiIndices=True)
    for index in indexList:
        index = str(index).split('L')[-1]
        maya.cmds.removeMultiInstance( rampName + '.colorEntryList[' + index + ']' )


def refreshMasterPaletteMenu():
    paletteNameArray = masterPaletteDict.keys()
    if paletteNameArray != 0:
        for paletteName in paletteNameArray:
            maya.cmds.menuItem(paletteName, label=paletteName, parent='masterPalettes' )

        if ('palettePreset' in toolStates) and (toolStates['palettePreset'] is not None):        
            itemList = maya.cmds.optionMenu( 'masterPalettes', query=True, ils=True )
            idx =  itemList.index(toolStates['palettePreset']) + 1
            maya.cmds.optionMenu( 'masterPalettes', edit=True, select=idx )


def refreshRampMenu():
    presetNameArray = maya.cmds.nodePreset( list='SXRamp' )
    if presetNameArray != 0:
        for presetName in presetNameArray:
            maya.cmds.menuItem( label=presetName, parent='rampPresets' )
   

def setLayerBlendMode():
    mode = maya.cmds.optionMenu( 'layerBlendModes', query=True, select=True) - 1
    attr = '.'+getSelectedLayer()+'BlendMode'
    for shape in shapeArray:
        maya.cmds.setAttr(str(shape)+attr, mode)
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)
    getSelectedLayer()


def setExportPath():
    path = str(maya.cmds.fileDialog2(cap='Select Export Folder', dialogStyle=2, fm=3)[0])
    if path.endswith('/'):
        projectSettings['SXToolsExportPath'] = path
    else:
        projectSettings['SXToolsExportPath'] = path+'/'
    savePreferences()


def resetSXTools():
    varList = maya.cmds.optionVar(list=True)
    for var in varList:
        if ('SXTools' in var):
            maya.cmds.optionVar(remove=str(var))
    print 'SX Tools: Settings reset'


# UI layout functions
# --------------------------------------------------------------------

# NOTE: For usability benefits, a custom paint tool context could be implemented.
def openSXPaintTool():
    maya.mel.eval('PaintVertexColorTool;')
    maya.cmds.artAttrPaintVertexCtx('artAttrColorPerVertexContext', edit=True, usepressure=False)
    maya.cmds.toolPropertyWindow(inMainWindow=True)


def setupProjectUI():
    global shapeArray
    
    maya.cmds.frameLayout( 'emptyFrame', label='No mesh objects selected',
                     parent='canvas', width=250,
                     marginWidth=10, marginHeight=5)
    
    maya.cmds.frameLayout( 'setupFrame', parent='canvas', width=250,
             label='Project Setup', marginWidth=5, marginHeight=5,
             collapsable=True, collapse=frameStates['setupFrameCollapse'],
             collapseCommand="sxtools.frameStates['setupFrameCollapse']=True",
             expandCommand="sxtools.frameStates['setupFrameCollapse']=False",
             borderVisible=False )

    maya.cmds.columnLayout( 'prefsColumn', parent='setupFrame',
                      rowSpacing=5, adjustableColumn=True )

    maya.cmds.button(label='Select Settings File', parent='prefsColumn',
                     statusBarMessage='Shift-click button to reload settings from file',
                     command='sxtools.setPreferencesFile()\n'
                             'sxtools.updateSXTools()')

    if maya.cmds.optionVar(exists='SXToolsPrefsFile') and len(str(maya.cmds.optionVar(query='SXToolsPrefsFile'))) > 0:
        maya.cmds.text(label='Current settings location:')
        maya.cmds.text(label=maya.cmds.optionVar(query='SXToolsPrefsFile'))
    else:
        maya.cmds.text( label='WARNING: Settings file location not set!',
                  backgroundColor=(0.35, 0.1, 0), ww=True )
        
    maya.cmds.text(label=' ')

    maya.cmds.rowColumnLayout( 'refLayerRowColumns', parent='setupFrame',
                 numberOfColumns=3,
                 columnWidth=((1, 90), (2, 70), (3, 70)),
                 columnAttach=[(1, 'left', 0 ), (2, 'left', 0), (3, 'left', 0)],
                 rowSpacing=(1, 0))

    maya.cmds.text(label=' ')
    maya.cmds.text(label='Count')
    maya.cmds.text(label='Export UV')

    # Max layers 10. Going higher causes instability.
    maya.cmds.text( label='Color layers:' )
    maya.cmds.intField( 'layerCount', value=8,
                  minValue=1, maxValue=10, step=1,
                  enterCommand=("maya.cmds.setFocus('MayaWindow')"))
        
    maya.cmds.textField( 'maskExport', text='U3' )

    maya.cmds.text(label=' ')
    maya.cmds.text(label=' ')
    maya.cmds.text(label=' ')
    
    maya.cmds.text(label='Channel')
    maya.cmds.text(label='Enabled')
    maya.cmds.text(label='Export UV')

    maya.cmds.text( 'occlusionLabel', label='Occlusion:' )
    maya.cmds.checkBox( 'occlusion', label='', value=True )
    maya.cmds.textField( 'occlusionExport', text='U1' )

    maya.cmds.text( 'specularLabel', label='Specular:' )
    maya.cmds.checkBox( 'specular', label='', value=True )
    maya.cmds.textField( 'specularExport', text='V1' )

    maya.cmds.text( 'transmissionLabel', label='Transmission:' )
    maya.cmds.checkBox( 'transmission', label='', value=True )
    maya.cmds.textField( 'transmissionExport', text='U2' )

    maya.cmds.text( 'emissionLabel', label='Emission:' )
    maya.cmds.checkBox( 'emission', label='', value=True )
    maya.cmds.textField( 'emissionExport', text='V2' )

    maya.cmds.rowColumnLayout( 'numLayerColumns', parent='setupFrame',
                 numberOfColumns=2,
                 columnWidth=((1, 160), (2, 70)),
                 columnAttach=[(1, 'left', 0 ), (2, 'left', 0)],
                 rowSpacing=(1, 0))

    maya.cmds.text( label='Export Process Options' )
    maya.cmds.text( label=' ' )
    maya.cmds.text( label='Alpha-to-mask limit:' )

    maya.cmds.floatField( 'exportTolerance', value=1.0,
                    minValue=0, maxValue=1, precision=1,
                    enterCommand=("maya.cmds.setFocus('MayaWindow')"))

    maya.cmds.text( label='Smoothing iterations:' )
    maya.cmds.intField( 'exportSmooth', value=0,
                  minValue=0, maxValue=3, step=1,
                  enterCommand=("maya.cmds.setFocus('MayaWindow')"))

    maya.cmds.text( label='Export preview grid spacing:' )
    maya.cmds.intField( 'exportOffset', value=5,
                  minValue=0, step=1,
                  enterCommand=("maya.cmds.setFocus('MayaWindow')"))

    maya.cmds.columnLayout( 'refLayerColumn', parent='setupFrame',
                      rowSpacing=5, adjustableColumn=True )
    maya.cmds.text(label=' ', parent='refLayerColumn')
    
    if maya.cmds.optionVar(exists='SXToolsPrefsFile') and len(str(maya.cmds.optionVar(query='SXToolsPrefsFile'))) > 0:
        maya.cmds.text(label='(Shift-click below to apply built-in defaults)', parent='refLayerColumn')
        maya.cmds.button( label='Apply Project Settings', parent='refLayerColumn',
                    statusBarMessage='Shift-click button to use the built-in default settings',
                    command=("sxtools.updatePreferences()\n"
                             "sxtools.setPreferences()\n"
                             "sxtools.frameStates['setupFrameCollapse']=True\n"
                             "sxtools.updateSXTools()") )
    
    refreshSetupProjectView()

    maya.cmds.workspaceControl( dockID, edit=True, resizeHeight=5, resizeWidth=250 )


def exportObjectsUI():
    maya.cmds.frameLayout( 'exportObjFrame', label=str(len(objectArray))+' export objects selected',
                     parent='canvas', width=250,
                     marginWidth=10, marginHeight=5)
    maya.cmds.columnLayout( 'exportedColumn', rowSpacing=5, adjustableColumn=True )
    maya.cmds.button(label='Select and show all export meshes',
                command='sxtools.viewExported()')
    maya.cmds.button(label='Hide exported, show source meshes',
                command=("maya.cmds.setAttr( 'exportsLayer.visibility', 0 )\n"
                         "maya.cmds.setAttr( 'assetsLayer.visibility', 1 )"))
    
    maya.cmds.text( label='Preview export object data:' )        
    maya.cmds.radioButtonGrp( 'exportShadingButtons1', parent='exportedColumn', vertical=True,
                        columnWidth3=(80, 80, 80),
                        columnAttach3=('left', 'left', 'left'),
                        labelArray3=['Composite', 'Albedo', 'Layer Masks'],
                        select=1, numberOfRadioButtons=3,
                        onCommand1=("sxtools.viewExportedMaterial()"),
                        onCommand2=("sxtools.viewExportedMaterial()"),
                        onCommand3=("sxtools.viewExportedMaterial()") )
    maya.cmds.radioButtonGrp( 'exportShadingButtons2', parent='exportedColumn', vertical=True,
                        shareCollection='exportShadingButtons1',
                        columnWidth4=(80, 80, 80, 80),
                        columnAttach4=('left', 'left', 'left', 'left'),
                        labelArray4=['Occlusion', 'Specular', 'Transmission', 'Emission'],
                        numberOfRadioButtons=4,
                        onCommand1=("sxtools.viewExportedMaterial()"),
                        onCommand2=("sxtools.viewExportedMaterial()"),
                        onCommand3=("sxtools.viewExportedMaterial()"),
                        onCommand4=("sxtools.viewExportedMaterial()") )
    
    maya.cmds.button( label='Choose Export Path', width=120,
                      command=("sxtools.setExportPath()\n"
                               "sxtools.updateSXTools()"))
    
    if (('SXToolsExportPath' in projectSettings) and (len(projectSettings['SXToolsExportPath']) == 0)):
        maya.cmds.text( label='No export folder selected!' )
    elif 'SXToolsExportPath' in projectSettings:
        exportPathText=('Export Path: ' + projectSettings['SXToolsExportPath'])
        maya.cmds.text( label=exportPathText )
        maya.cmds.button( label='Export Objects in _staticExports', width=120,
                          command=("sxtools.exportObjects(sxtools.projectSettings['SXToolsExportPath'])") )
        maya.cmds.rowColumnLayout( 'exportSuffixRowColumns', parent='exportedColumn',
             numberOfColumns=2,
             columnWidth=((1, 120), (2, 120)),
             columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
             rowSpacing=(1, 5))
        maya.cmds.text( label='Add _paletted suffix')
        maya.cmds.checkBox( 'suffixCheck', label='', value=toolStates['exportSuffix'], changeCommand=("sxtools.toolStates['exportSuffix'] = maya.cmds.checkBox('suffixCheck', query=True, value=True)") )
    else:
        maya.cmds.text( label='No export folder selected!' )
    
    maya.cmds.setParent( 'exportObjFrame' )
    maya.cmds.setParent( 'canvas' )
    maya.cmds.workspaceControl( dockID, edit=True, resizeHeight=5, resizeWidth=250 )


def emptyObjectsUI():
    global objectArray, shapeArray, patchArray
    
    patchArray = verifyObjectLayers(shapeArray)[1]
    patchLabel = 'Objects with no layers: '+str(len(patchArray))
    maya.cmds.frameLayout( 'patchFrame', label=patchLabel, parent='canvas',
                     width=250, marginWidth=10, marginHeight=5)
    maya.cmds.columnLayout( 'patchColumn', adjustableColumn=True, rowSpacing=5 )
    maya.cmds.text( label=("Click on empty to view project defaults.\n"), align='left' )
    
    if maya.cmds.objExists('SXShader'):
        maya.cmds.text( label= ("Add project layers to selected objects\n"
                          "by pressing the button below.\n"), align="left" )
        maya.cmds.button( label='Add missing color sets',
                    command='sxtools.patchLayers(sxtools.patchArray)' )
    maya.cmds.setParent( 'patchFrame' )
    maya.cmds.setParent( 'canvas' )
    checkHistory(objectArray)
    maya.cmds.workspaceControl( dockID, edit=True, resizeHeight=5, resizeWidth=250 )


def mismatchingObjectsUI():
    global objectArray, shapeArray, patchArray
    
    patchArray = verifyObjectLayers(shapeArray)[1]
    patchLabel = 'Objects with nonstandard layers: '+str(len(patchArray))
    maya.cmds.frameLayout( 'patchFrame', label=patchLabel, parent='canvas',
                     width=250, marginWidth=10, marginHeight=5)
    maya.cmds.columnLayout( 'patchColumn', adjustableColumn=True, rowSpacing=5 )
    maya.cmds.text( label=("To fix color layers:\n"
                      "1. Open Color Set Editor\n"
                      "2. Delete any redundant color sets\n"
                      "3. Rename any needed color sets\n"
                      "    using reference names\n"
                      "4. DELETE HISTORY on selected objects\n" 
                      "5. Press 'Add Missing Color Sets' button\n\n"
                      "Reference names:\nlayer1-nn, occlusion, specular,\ntransmission, emission"), align="left" )
    maya.cmds.button( label='Color Set Editor',
                command="maya.mel.eval('colorSetEditor;')" )
    if 'SXToolsRefLayers' in projectSettings:
        maya.cmds.button( label='Add missing color sets',
                    command="sxtools.patchLayers(sxtools.patchArray)" )
    maya.cmds.setParent( 'patchFrame' )
    maya.cmds.setParent( 'canvas' )
    checkHistory(objectArray)
    maya.cmds.workspaceControl( dockID, edit=True, resizeHeight=5, resizeWidth=250 )


def layerViewUI():
    maya.cmds.frameLayout( 'layerFrame', parent='canvas',
                     width=250, marginWidth=5, marginHeight=5 )
    maya.cmds.columnLayout('layerColumn', parent='layerFrame',
                      adjustableColumn=True, rowSpacing=5)
    maya.cmds.radioButtonGrp( 'shadingButtons', parent='layerColumn',
                         columnWidth3=(80, 80, 80),
                         columnAttach3=('left', 'left', 'left'),
                         labelArray3=['Final', 'Debug', 'Alpha'],
                         select=1, numberOfRadioButtons=3,
                         onCommand1=("sxtools.setShadingMode(0)\n"
                                     "maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='ambientDiffuse', colorShadedDisplay=True)\n"
                                     "maya.mel.eval('DisplayLight;')"),
                         onCommand2=("sxtools.setShadingMode(1)\n"
                                     "maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='none', colorShadedDisplay=True)\n"
                                     "maya.mel.eval('DisplayShadedAndTextured;')"),
                         onCommand3=("sxtools.setShadingMode(2)\n"
                                     "maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='ambientDiffuse', colorShadedDisplay=True)\n"
                                     "maya.mel.eval('DisplayLight;')") )
    verifyShadingMode()
    maya.cmds.button( label='Toggle all layers', command='sxtools.toggleAllLayers()' )
    
    maya.cmds.optionMenu( 'layerBlendModes', parent='layerColumn', label='Layer Blend Mode:',
            changeCommand='sxtools.setLayerBlendMode()' )
    maya.cmds.menuItem( 'alphaBlend', label='Alpha', parent='layerBlendModes' )
    maya.cmds.menuItem( 'additiveBlend', label='Add', parent='layerBlendModes' )
    maya.cmds.menuItem( 'multiplyBlend', label='Multiply', parent='layerBlendModes' )
    
    maya.cmds.textScrollList( 'layerList', allowMultiSelection=False,
                        ann=('Doubleclick to hide/unhide layer in Final shading mode\n'
                             '(H) - hidden layer\n'
                             '(M) - mask layer\n'
                             '(A) - adjustment layer'))
    refreshLayerList()
    refreshSelectedItem()
    maya.cmds.rowColumnLayout( 'layerRowColumns', parent='layerColumn',
                         numberOfColumns=2,
                         columnWidth=((1, 100), (2, 140)),
                         columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
                         rowSpacing=(1, 5))
    maya.cmds.text( 'layerColorLabel', label=str(getSelectedLayer())+' colors:' )
    maya.cmds.palettePort( 'layerPalette', dimensions=(8, 1), width=120,
                     height=10, actualTotal=8, editable=True, colorEditable=False,
                     changeCommand='sxtools.setPaintColor()' )
    maya.cmds.text( 'layerOpacityLabel', label=str(getSelectedLayer())+' opacity:' )
    maya.cmds.floatSlider('layerOpacitySlider', min=0.0, max=1.0, width=100,
                     changeCommand=("sxtools.setLayerOpacity()\n"
                                    "sxtools.refreshLayerList()\n"
                                    "sxtools.refreshSelectedItem()") )
    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())
    maya.cmds.button( 'mergeLayerUp', label='Merge layer up', parent='layerColumn', width=100,
                command=("sxtools.mergeLayerUp()") )
    maya.cmds.rowColumnLayout( 'layerSelectRowColumns', parent='layerColumn',
                 numberOfColumns=2,
                 columnWidth=((1, 120), (2, 120)), 
                 columnSpacing=([1, 0], [2,5]),
                 rowSpacing=(1, 5))
    maya.cmds.button(label='Select Layer Mask', width=100,
                statusBarMessage='Shift-click button to invert selection',
                command="maya.cmds.select(sxtools.getLayerMask())")
    if len(componentArray) > 0:
        maya.cmds.button('clearButton', label='Clear Selected',
                    statusBarMessage='Shift-click button to clear all layers on selected components',
                    width=100 ,
                    command=("sxtools.clearSelector()\n"
                             "sxtools.getLayerPaletteOpacity(sxtools.shapeArray[len(sxtools.shapeArray)-1], sxtools.getSelectedLayer())\n"
                             "sxtools.refreshLayerList()\n"
                             "sxtools.refreshSelectedItem()") )
    else:
        maya.cmds.button('clearButton', label='Clear Layer',
                    statusBarMessage='Shift-click button to clear all layers on selected objects',
                    width=100,
                    command=("sxtools.clearSelector()\n"
                             "sxtools.getLayerPaletteOpacity(sxtools.shapeArray[len(sxtools.shapeArray)-1], sxtools.getSelectedLayer())\n"
                             "sxtools.refreshLayerList()\n"
                             "sxtools.refreshSelectedItem()") )


def applyColorToolUI():
    maya.cmds.frameLayout( "applyColorFrame", parent="toolFrame",
                     label="Apply Color", marginWidth=5, marginHeight=0,
                     collapsable=True, collapse=frameStates['applyColorFrameCollapse'],
                     collapseCommand="sxtools.frameStates['applyColorFrameCollapse']=True",
                     expandCommand="sxtools.frameStates['applyColorFrameCollapse']=False" )
    maya.cmds.columnLayout( "applyColorColumn", parent="applyColorFrame", rowSpacing=5, adjustableColumn=True )
    maya.cmds.rowColumnLayout( "applyColorRowColumns", parent="applyColorColumn",
                         numberOfColumns=2,
                         columnWidth=((1, 100), (2, 140)),
                         columnAttach=[(1, "left", 0 ), (2, "both", 5)],
                         rowSpacing=(1, 5))
    maya.cmds.text( 'recentPaletteLabel', label="Recent Colors:" )
    maya.cmds.palettePort( 'recentPalette', dimensions=(8, 1), width=120,
                     height=10, actualTotal=8, editable=True, colorEditable=False,
                     changeCommand='sxtools.setApplyColor()' ) 
    maya.cmds.colorSliderGrp('sxApplyColor', parent='applyColorColumn',
                            label='Color:',
                            columnWidth3=(80, 20, 60), adjustableColumn3=3,
                            columnAlign3=('left', 'left', 'left' ),
                            changeCommand="sxtools.currentColor = maya.cmds.colorSliderGrp('sxApplyColor', query=True, rgbValue=True)" )
    maya.cmds.setParent( "applyColorFrame" )
    maya.cmds.button(label="Apply Color", parent='applyColorColumn',
                height=30, width=100,
                command=('sxtools.colorFill()\nsxtools.updateRecentPalette()'))
    maya.cmds.setParent( "toolFrame" )
    getCurrentColor()
    getPalette('recentPalette', paletteDict, 'SXToolsRecentPalette')


def gradientToolUI():
    # ramp nodes for gradient tool
    if maya.cmds.objExists('SXRamp') == False:
        maya.cmds.createNode('ramp', name='SXRamp', skipSelect=True)

    if maya.cmds.objExists('SXAlphaRamp') == False:
        maya.cmds.createNode('ramp', name='SXAlphaRamp', skipSelect=True)
        maya.cmds.setAttr('SXAlphaRamp.colorEntryList[0].position', 1)
        maya.cmds.setAttr('SXAlphaRamp.colorEntryList[0].color', 1, 1, 1)
        maya.cmds.setAttr('SXAlphaRamp.colorEntryList[1].position', 0)
        maya.cmds.setAttr('SXAlphaRamp.colorEntryList[1].color', 1, 1, 1)

    maya.cmds.frameLayout( "gradientFrame", parent="toolFrame",
                     label="Gradient Fill", marginWidth=5, marginHeight=0,
                     collapsable=True, collapse=frameStates['gradientFrameCollapse'],
                     collapseCommand="sxtools.frameStates['gradientFrameCollapse']=True",
                     expandCommand="sxtools.frameStates['gradientFrameCollapse']=False",
                     borderVisible=False )
    maya.cmds.columnLayout( "gradientColumn", parent="gradientFrame",
                      rowSpacing=0, adjustableColumn=True )
    maya.cmds.optionMenu( 'rampPresets', parent='gradientColumn', label='Presets:',
                    changeCommand="sxtools.gradientToolManager('load')" )
    refreshRampMenu()
    maya.cmds.rowColumnLayout( 'gradientRowColumns', parent='gradientColumn',
                         numberOfColumns=2,
                         columnWidth=((1, 100), (2, 140)),
                         columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
                         rowSpacing=(1, 5))
    maya.cmds.button( 'savePreset', label='Save Preset', width=100,
                ann='Shift-click to delete preset',
                command="sxtools.gradientToolManager('preset')\nsxtools.updateSXTools()\nsxtools.savePreferences()" )
    maya.cmds.textField('presetName', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                   placeholderText='Preset Name')
    maya.cmds.attrColorSliderGrp('sxRampColor', parent='gradientColumn',
                            label='Selected Color:', showButton=False,
                            columnWidth4=(80, 20, 60, 0), adjustableColumn4=3,
                            columnAlign4=('left', 'left', 'left', 'left' ))
    maya.cmds.attrEnumOptionMenuGrp('sxRampMode', parent='gradientColumn',
                               label='Interpolation:', columnWidth2=(80, 100),
                               columnAttach2=('left', 'left'), columnAlign2=('left', 'left'))
    maya.cmds.rampColorPort( 'sxRampControl', parent="gradientColumn",
                       node='SXRamp', height=90,
                       selectedColorControl='sxRampColor',
                       selectedInterpControl='sxRampMode' )
    maya.cmds.attrColorSliderGrp('sxRampAlpha', parent='gradientColumn',
                            label='Selected Alpha:', showButton=False,
                            columnWidth4=(80, 20, 60, 0), adjustableColumn4=3,
                            columnAlign4=('left', 'left', 'left', 'left' ))
    maya.cmds.attrEnumOptionMenuGrp('sxAlphaRampMode', parent='gradientColumn',
                               label='Interpolation:', columnWidth2=(80, 100),
                               columnAttach2=('left', 'left'), columnAlign2=('left', 'left'))
    maya.cmds.rampColorPort( 'sxRampAlphaControl', parent='gradientColumn',
                       node='SXAlphaRamp', height=90,
                       selectedColorControl='sxRampAlpha',
                       selectedInterpControl='sxAlphaRampMode' )
    maya.cmds.radioButtonGrp( 'gradientDirection', parent='gradientColumn',
                        columnWidth3=(80, 80, 80),
                        columnAttach3=('left', 'left', 'left'),
                        labelArray3=['X', 'Y', 'Z'],
                        numberOfRadioButtons=3 )
    maya.cmds.radioButtonGrp( 'gradientMode', parent='gradientColumn',
                        columnWidth2=(120, 120), shareCollection='gradientDirection',
                        columnAttach2=('left', 'left'),
                        labelArray2=['Luminance', 'Curvature'],
                        numberOfRadioButtons=2 )
    maya.cmds.button(label='Apply Gradient', parent='gradientColumn',
                height=30, width=100,
                command=("sxtools.gradientToolManager(maya.cmds.radioButtonGrp('gradientDirection', query=True, select=True), 0)\n"
                         "sxtools.gradientToolManager(maya.cmds.radioButtonGrp('gradientMode', query=True, select=True), 1)"))
    maya.cmds.setParent( 'toolFrame' )

    if 'SXToolsGradientDirection' in projectSettings:
        gradientDirection = projectSettings['SXToolsGradientDirection']
        if gradientDirection <= 3:
            maya.cmds.radioButtonGrp( 'gradientDirection', edit=True, select=gradientDirection )
        elif gradientDirection > 3:
            maya.cmds.radioButtonGrp( 'gradientMode', edit=True, select=(gradientDirection-3) )
    else:
        maya.cmds.radioButtonGrp( 'gradientDirection', edit=True, select=1 )


def colorNoiseToolUI():
    maya.cmds.frameLayout( 'noiseFrame', parent='toolFrame',
                     label='Color Noise', marginWidth=5, marginHeight=0,
                     collapsable=True, collapse=frameStates['noiseFrameCollapse'],
                     collapseCommand="sxtools.frameStates['noiseFrameCollapse']=True",
                     expandCommand="sxtools.frameStates['noiseFrameCollapse']=False",
                     borderVisible=False )
    maya.cmds.columnLayout( 'noiseColumn', parent='noiseFrame', rowSpacing=0, adjustableColumn=True )
    maya.cmds.rowColumnLayout( 'noiseRowColumns', parent='noiseColumn',
                 numberOfColumns=2,
                 columnWidth=((1, 100), (2, 140)),
                 columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
                 rowSpacing=(1, 5))
    maya.cmds.text( 'monoLabel', label='Monochromatic:' )
    maya.cmds.checkBox( 'mono', label='', value=toolStates['noiseMonochrome'], 
                        changeCommand=("sxtools.toolStates['noiseMonochrome'] = maya.cmds.checkBox('mono', query=True, value=True)") )
    maya.cmds.text( 'noiseValueLabel', label='Noise Value (0-1):' )
    maya.cmds.floatField( 'noiseValue',  precision=3, value=toolStates['noiseValue'], minValue=0.0, maxValue=1.0,
                          changeCommand=("sxtools.toolStates['noiseValue'] = maya.cmds.floatField('noiseValue', query=True, value=True)") )
    maya.cmds.button(label='Apply Noise', parent='noiseColumn',
                height=30, width=100,
                command="sxtools.colorNoise(sxtools.objectArray)\n"
                        "maya.cmds.floatSlider('layerOpacitySlider', edit=True, value=1.0)\n"
                        "sxtools.setLayerOpacity()\n"
                        "sxtools.refreshLayerList()\n"
                        "sxtools.refreshSelectedItem()")
    maya.cmds.setParent( 'toolFrame' )


def bakeOcclusionToolUI():
    maya.cmds.frameLayout( 'occlusionFrame', parent='toolFrame',
                     label='Bake Occlusion', marginWidth=5, marginHeight=0,
                     collapsable=True, collapse=frameStates['occlusionFrameCollapse'],
                     collapseCommand="sxtools.frameStates['occlusionFrameCollapse']=True",
                     expandCommand="sxtools.frameStates['occlusionFrameCollapse']=False" )
    maya.cmds.columnLayout( 'occlusionColumn', parent='occlusionFrame', rowSpacing=5, adjustableColumn=True )
    maya.cmds.text( label=("\nOcclusion groundplane is placed\n"
                      "at the minY of the bounding box of\n"
                      "each object being baked.\n"
                      "Offset pushes the plane down.\n"), align="left" )
    maya.cmds.rowColumnLayout( 'occlusionRowColumns', parent='occlusionColumn',
                 numberOfColumns=4,
                 columnWidth=((1, 80), (2, 50), (3, 50), (4, 50)),
                 columnAttach=[(1, 'left', 0 ), (2, 'left', 0), (3, 'left', 0), (4, 'left', 0)],
                 rowSpacing=(1, 0))

    maya.cmds.text(label=' ')
    maya.cmds.text(label=' ')
    maya.cmds.text(label='Scale')
    maya.cmds.text(label='Offset')

    maya.cmds.text( 'groundLabel', label='Groundplane:' )
    maya.cmds.text( label='')
    # maya.cmds.checkBox( 'ground', label='', value=toolStates['bakeGroundPlane'],
    #                     changeCommand=("sxtools.toolStates['bakeGroundPlane'] = maya.cmds.checkBox('ground', query=True, value=True)") )
    maya.cmds.floatField( 'groundScale', value=toolStates['bakeGroundScale'], precision=1, minValue=0.0,
                          changeCommand=("sxtools.toolStates['bakeGroundScale'] = maya.cmds.floatField('groundScale', query=True, value=True)") )
    maya.cmds.floatField( 'groundOffset', value=toolStates['bakeGroundOffset'], precision=1, minValue=0.0,
                          changeCommand=("sxtools.toolStates['bakeGroundOffset'] = maya.cmds.floatField('groundOffset', query=True, value=True)") )
    
    maya.cmds.rowColumnLayout( 'occlusionRowColumns2', parent='occlusionColumn',
                 numberOfColumns=2,
                 columnWidth=((1, 130), (2, 110)),
                 columnAttach=[(1, 'left', 0 ), (2, 'left', 0)],
                 rowSpacing=(1, 0))
    
    maya.cmds.text(label='Blend local vs. global')
    maya.cmds.floatSlider('blendSlider', min=0.0, max=1.0, width=100,
                          value=toolStates['blendSlider'], changeCommand=("sxtools.toolStates['blendSlider']=maya.cmds.floatSlider('blendSlider', query=True, value=True)\nsxtools.blendOcclusion()") )

    getLayerPaletteOpacity(shapeArray[len(shapeArray)-1], getSelectedLayer())


    plugList = maya.cmds.pluginInfo( query=True, listPlugins=True )
    if 'Mayatomr' in plugList:
        maya.cmds.button(label='Bake Occlusion (Mental Ray)', parent='occlusionColumn',
                    height=30, width=100, command='sxtools.bakeBlendOcclusion()')
    if 'mtoa' in plugList:
        maya.cmds.rowColumnLayout( 'occlusionRowColumns3', parent='occlusionColumn',
                     numberOfColumns=2,
                     columnWidth=((1, 130), (2, 110)),
                     columnAttach=[(1, 'left', 0 ), (2, 'left', 0)],
                     rowSpacing=(1, 0))    
        maya.cmds.text( 'bake label', label='Bake folder:' )
        maya.cmds.textField('bakepath', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                       placeholderText='C:/')
        maya.cmds.button(label='Bake Occlusion (Arnold)', parent='occlusionColumn',
                    height=30, width=100, ann='Shift-click to bake all objects together',
                    command="sxtools.bakeOcclusionArnold()")               
                
    maya.cmds.setParent('toolFrame')


def masterPaletteToolUI():
    maya.cmds.frameLayout( 'masterPaletteFrame', parent='toolFrame',
                     label='Apply Master Palette', marginWidth=5, marginHeight=0,
                     collapsable=True, collapse=frameStates['masterPaletteFrameCollapse'],
                     collapseCommand="sxtools.frameStates['masterPaletteFrameCollapse']=True",
                     expandCommand="sxtools.frameStates['masterPaletteFrameCollapse']=False" )
    maya.cmds.columnLayout( 'masterPaletteColumn', parent='masterPaletteFrame', rowSpacing=5, adjustableColumn=True )
    maya.cmds.optionMenu( 'masterPalettes', parent='masterPaletteColumn', label='Presets:',
                    changeCommand='sxtools.getMasterPaletteItem()' )
    refreshMasterPaletteMenu()
    maya.cmds.rowColumnLayout( 'masterPaletteRowColumns', parent='masterPaletteColumn',
                         numberOfColumns=2,
                         columnWidth=((1, 100), (2, 140)),
                         columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
                         rowSpacing=(1, 5))
    maya.cmds.button( 'saveMasterPalette', label='Save Preset', width=100,
                ann='Shift-click to delete preset',
                command='sxtools.saveMasterPalette()' )
    maya.cmds.textField('savePaletteName', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                   placeholderText='Preset Name')
    maya.cmds.text( 'masterPaletteLabel', label='Palette Colors:' )
    maya.cmds.palettePort( 'masterPalette', dimensions=(5, 1), width=120,
                     height=10, actualTotal=5,
                     editable=True, colorEditable=True,
                     changeCommand="sxtools.storePalette('masterPalette', sxtools.paletteDict, 'SXToolsMasterPalette')\nsxtools.toolStates['palettePreset']=None",
                     colorEdited="sxtools.storePalette('masterPalette', sxtools.paletteDict, 'SXToolsMasterPalette')" )
    maya.cmds.button(label='Apply Master Palette', parent='masterPaletteColumn',
                height=30, width=100,
                command=('sxtools.applyMasterPalette(sxtools.objectArray)'))
    maya.cmds.setParent( 'toolFrame' )
    
    if ('palettePreset' in toolStates) and (toolStates['palettePreset'] is None):
        getPalette('masterPalette', paletteDict, 'SXToolsMasterPalette')
    else:
        getMasterPaletteItem()


def swapLayerToolUI():
    maya.cmds.frameLayout( 'swapLayerFrame', parent='toolFrame',
             label='Swap Layers', marginWidth=5, marginHeight=0,
             collapsable=True, collapse=frameStates['swapLayerFrameCollapse'],
             collapseCommand="sxtools.frameStates['swapLayerFrameCollapse']=True",
             expandCommand="sxtools.frameStates['swapLayerFrameCollapse']=False" )
    maya.cmds.columnLayout( 'swapLayerColumn', parent='swapLayerFrame', rowSpacing=5, adjustableColumn=True )
    maya.cmds.rowColumnLayout( 'swapLayerRowColumns', parent='swapLayerColumn',
                         numberOfColumns=2,
                         columnWidth=((1, 100), (2, 140)),
                         columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
                         rowSpacing=(1, 5))
    maya.cmds.text( 'layerALabel', label='Layer A:' )
    maya.cmds.textField('layerA', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                   placeholderText='Layer A Name')
    maya.cmds.text( 'layerBLabel', label='Layer B:' )
    maya.cmds.textField('layerB', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                   placeholderText='Layer B Name')
    maya.cmds.setParent( 'swapLayerFrame' )
    maya.cmds.button(label='Swap Layers', parent='swapLayerColumn',
                height=30, width=100,
                command=('sxtools.swapLayers(sxtools.selectionArray[0])'))
    maya.cmds.setParent( 'toolFrame' )


def copyLayerToolUI():
    maya.cmds.frameLayout( 'copyLayerFrame', parent='toolFrame',
             label='Copy Layer', marginWidth=5, marginHeight=0,
             collapsable=True, collapse=frameStates['copyLayerFrameCollapse'],
             collapseCommand="sxtools.frameStates['copyLayerFrameCollapse']=True",
             expandCommand="sxtools.frameStates['copyLayerFrameCollapse']=False" )
    maya.cmds.columnLayout( 'copyLayerColumn', parent='copyLayerFrame', rowSpacing=5, adjustableColumn=True )
    maya.cmds.rowColumnLayout( 'copyLayerRowColumns', parent='copyLayerColumn',
                         numberOfColumns=2,
                         columnWidth=((1, 100), (2, 140)),
                         columnAttach=[(1, 'left', 0 ), (2, 'both', 5)],
                         rowSpacing=(1, 5))
    maya.cmds.text( 'source layer', label='Source Layer:' )
    maya.cmds.textField('layersrc', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                   placeholderText='Source Layer Name')
    maya.cmds.text( 'target layer', label='Target Layer:' )
    maya.cmds.textField('layertgt', enterCommand=("maya.cmds.setFocus('MayaWindow')"),
                   placeholderText='Target Layer Name')
    maya.cmds.setParent( 'copyLayerFrame' )
    maya.cmds.button(label='Copy Layer', parent='copyLayerColumn',
                height=30, width=100,
                command=('sxtools.copyLayer(sxtools.objectArray)'))
    maya.cmds.setParent( 'toolFrame' )


def assignCreaseToolUI():
    maya.cmds.frameLayout( 'creaseFrame', parent='toolFrame',
                     label='Assign to Crease Set', marginWidth=5, marginHeight=0,
                     collapsable=True, collapse=frameStates['creaseFrameCollapse'],
                     collapseCommand="sxtools.frameStates['creaseFrameCollapse']=True",
                     expandCommand="sxtools.frameStates['creaseFrameCollapse']=False" )
    maya.cmds.columnLayout( 'creaseColumn', parent='creaseFrame', rowSpacing=5, adjustableColumn=True )
    maya.cmds.radioButtonGrp( 'creaseSets', parent='creaseColumn',
                        columnWidth4=(50, 50, 50, 50 ),
                        columnAttach4=('left', 'left', 'left', 'left'),
                        labelArray4=['[0.5]', '[1.0]', '[2.0]', '[Hard]' ], numberOfRadioButtons=4,
                        onCommand1="sxtools.assignToCreaseSet('sxCrease1')",
                        onCommand2="sxtools.assignToCreaseSet('sxCrease2')",
                        onCommand3="sxtools.assignToCreaseSet('sxCrease3')",
                        onCommand4="sxtools.assignToCreaseSet('sxCrease4')" )
    maya.cmds.setParent( 'creaseFrame' )
    maya.cmds.button(label='Uncrease Selection', parent='creaseColumn',
                height=30, width=100,
                command=("sxtools.assignToCreaseSet('sxCrease0')"))
    maya.cmds.setParent( 'toolFrame' )


# Core functions
# --------------------------------------------------------------------

def startSXTools():
    # Check if SX Tools UI exists
    if maya.cmds.workspaceControl(dockID, exists=True):
        maya.cmds.deleteUI(dockID, control=True)

    global job1ID, job2ID, job3ID, job4ID, job5ID

    platform = maya.cmds.about(os=True)

    if platform == 'win' or platform == 'win64':
        displayScalingValue = maya.cmds.mayaDpiSetting( query=True, realScaleValue=True )
    else:
        displayScalingValue = 1.0

    loadPreferences()  

    maya.cmds.workspaceControl( dockID, label='SX Tools', uiScript='sxtools.updateSXTools()',
                          retain=False, floating=True,
                          initialHeight=5, initialWidth=250*displayScalingValue,
                          minimumWidth=250*displayScalingValue )

    # Background jobs to reconstruct window if selection changes,
    # and to clean up upon closing
    job1ID = maya.cmds.scriptJob(event=['SelectionChanged', 'sxtools.updateSXTools()'])
    job2ID = maya.cmds.scriptJob(event=['NameChanged', 'sxtools.updateSXTools()'])
    job3ID = maya.cmds.scriptJob(event=['SceneOpened', 'sxtools.frameStates["setupFrameCollapse"]=False\n'
                                                       'sxtools.setPreferences()'])
    job4ID = maya.cmds.scriptJob(event=['NewSceneOpened', 'sxtools.frameStates["setupFrameCollapse"]=False\n'
                                                          'sxtools.setPreferences()'])
    job5ID = maya.cmds.scriptJob(runOnce=True, event=['quitApplication', 'maya.cmds.deleteUI(sxtools.dockID)'])
    
    maya.cmds.scriptJob(runOnce=True, uiDeleted=[dockID, 'maya.cmds.scriptJob(kill=sxtools.job1ID)\n'
                                                         'maya.cmds.scriptJob(kill=sxtools.job2ID)\n'
                                                         'maya.cmds.scriptJob(kill=sxtools.job3ID)\n'
                                                         'maya.cmds.scriptJob(kill=sxtools.job4ID)\n'
                                                         'maya.cmds.scriptJob(kill=sxtools.job5ID)'])
    
    # Set correct lighting and shading mode at start
    maya.mel.eval('DisplayShadedAndTextured;')
    maya.mel.eval('DisplayLight;')
    maya.cmds.modelEditor('modelPanel4', edit=True, udm=False)


# Avoids UI refresh from being included in the undo list
# Called by the "jobID" scriptJob whenever the user clicks a selection.
def updateSXTools():
    maya.cmds.undoInfo( stateWithoutFlush=False )
    selectionManager()
    refreshSXTools()
    maya.cmds.undoInfo( stateWithoutFlush=True )
    
    
## The user can have various different types of objects selected. The selections are filtered for the tool.
def selectionManager():
    global selectionArray, objectArray, shapeArray, componentArray, patchArray

    selectionArray = maya.cmds.ls(sl=True)
    shapeArray =  maya.cmds.listRelatives(selectionArray, type='mesh', allDescendents=True, fullPath=True)
    objectArray = maya.cmds.listRelatives(shapeArray, parent=True, fullPath=True)
    #componentArray = list(set(maya.cmds.ls(sl=True, o=False)) - set(maya.cmds.ls(sl=True, o=True)))
    componentArray = maya.cmds.filterExpand(selectionArray, sm=(31,32,34,70))

    # If only shape nodes are selected
    onlyShapes = True
    for selection in selectionArray:
        if 'Shape' not in str(selection):
            onlyShapes = False
    if onlyShapes == True:
        shapeArray = selectionArray
        objectArray = maya.cmds.listRelatives(shapeArray, parent=True, fullPath=True)

    # Maintain correct object selection even if only components are selected
    if (shapeArray is None and componentArray is not None):
        shapeArray = maya.cmds.ls(selectionArray, o=True, dag=True, type='mesh', long=True)
        objectArray = maya.cmds.listRelatives(shapeArray, parent=True, fullPath=True)
 
    # The case when the user selects a component set
    if (len(maya.cmds.ls(sl=True, type='objectSet')) > 0) and componentArray is not None:
        del componentArray[:]
    
    if shapeArray is None:
        shapeArray = []
    
    if objectArray is None:
        objectArray = []
    
    if componentArray is None:
        componentArray = []
        
    
# The main function of the tool, updates the UI dynamically for different selection types.
def refreshSXTools():
    global frameStates, selectionArray, objectArray, shapeArray, componentArray, patchArray

    createDefaultLights()
    createCreaseSets()
    createDisplayLayers()

    # base canvas for all SX Tools UI
    if maya.cmds.scrollLayout('canvas', exists=True):
        maya.cmds.deleteUI('canvas', lay=True)

    maya.cmds.scrollLayout( 'canvas', minChildWidth=250, childResizable=True, parent=dockID,
                      horizontalScrollBarThickness=16, verticalScrollBarThickness=16,
                      verticalScrollBarAlwaysVisible=False )

    # If nothing selected, or defaults not set, construct setup view
    if (len(shapeArray) == 0) or (maya.cmds.optionVar(exists='SXToolsPrefsFile') == False) or (len(projectSettings) == 0):
        setupProjectUI()

    # If exported objects selected, construct message
    elif checkExported(objectArray) == True:
        exportObjectsUI()

    # If objects have empty color sets, construct error message
    elif verifyObjectLayers(shapeArray)[0] == 1:
        emptyObjectsUI()

    # If objects have mismatching color sets, construct error message
    elif verifyObjectLayers(shapeArray)[0] == 2:
        mismatchingObjectsUI()

    # Construct layer tools window
    else:
        maya.cmds.editDisplayLayerMembers( 'assetsLayer', objectArray )
        maya.cmds.setAttr( 'exportsLayer.visibility', 0 )
        maya.cmds.setAttr( 'assetsLayer.visibility', 1 )

        layerViewUI()

        maya.cmds.frameLayout( 'toolFrame', parent='canvas', label='Tools',
                         width=250, marginWidth=5, marginHeight=5,
                         collapsable=True, collapse=frameStates['toolFrameCollapse'],
                         collapseCommand=("sxtools.frameStates['toolFrameCollapse']=True\n"
                                          "maya.cmds.workspaceControl( sxtools.dockID, edit=True, resizeHeight=5, resizeWidth=250 )"),
                         expandCommand="sxtools.frameStates['toolFrameCollapse']=False" )

        maya.cmds.setParent( "toolFrame" )
        maya.cmds.button(label='Paint Vertex Colors', height=30, width=100,
                    command="sxtools.openSXPaintTool()")

        applyColorToolUI()
        gradientToolUI()
        colorNoiseToolUI()
        plugList = maya.cmds.pluginInfo( query=True, listPlugins=True )
        if ('Mayatomr' in plugList) or ('mtoa' in plugList):
            bakeOcclusionToolUI()
        masterPaletteToolUI()
        swapLayerToolUI()
        copyLayerToolUI()
        assignCreaseToolUI()
        
        maya.cmds.columnLayout( 'processColumn', parent='canvas',
                          width=250, rowSpacing=5, adjustableColumn=True )
        maya.cmds.text(label=' ', parent='processColumn')
        maya.cmds.button( label='Create Export Objects', parent='processColumn', 
                    command="sxtools.processObjects(sxtools.selectionArray)")
        maya.cmds.setParent( 'canvas' )
        checkHistory(objectArray)

        # Make sure selected things are using the correct material
        maya.cmds.sets(shapeArray, e=True, forceElement='SXShaderSG')
        if verifyShadingMode() == 0:
            maya.cmds.polyOptions(activeObjects=True, colorMaterialChannel='ambientDiffuse', colorShadedDisplay=True)
            maya.mel.eval('DisplayLight;')
            maya.cmds.modelEditor('modelPanel4', edit=True, udm=False)

    maya.cmds.setFocus('MayaWindow')
