# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
#
#   ShaderFX network generation based on work by Steve Theodore
#   https://github.com/theodox/sfx
# ----------------------------------------------------------------------------

import maya.cmds
from sfx import SFXNetwork
from sfx import StingrayPBSNetwork
import sfx.sfxnodes as sfxnodes
import sfx.pbsnodes as pbsnodes
import sxglobals


class SceneSetup(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting setup')

    def createSXShaderLite(self,
                       numLayers,
                       occlusion=False,
                       specular=False,
                       transmission=False,
                       emission=False):
        if maya.cmds.objExists('SXShader'):
            maya.cmds.delete('SXShader')
            print('SX Tools: Updating default materials')
        if maya.cmds.objExists('SXShaderSG'):
            maya.cmds.delete('SXShaderSG')

        else:
            print('SX Tools: Creating default materials')

        materialName = 'SXShader'
        sxglobals.settings.material = SFXNetwork.create(materialName)
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

        bcol_node = sxglobals.settings.material.add(sfxnodes.Color)
        bcol_node.name = 'black'
        bcol_node.color = (0, 0, 0, 1)
        bcol_node.posx = -2500
        bcol_node.posy = -250
        # bcolID = maya.cmds.shaderfx(
        #     sfxnode=materialName, getNodeIDByName='black')

        wcol_node = sxglobals.settings.material.add(sfxnodes.Color)
        wcol_node.name = 'white'
        wcol_node.color = (1, 1, 1, 1)
        wcol_node.posx = -2500
        wcol_node.posy = -500
        # wcolID = maya.cmds.shaderfx(
        #     sfxnode=materialName, getNodeIDByName='white')

        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='TraditionalGameSurfaceShader')
        sxglobals.settings.nodeDict['SXShader'] = shaderID

        #
        # Create requested number of layer-specific nodes
        #

        layerName = 'composite'
        vertcol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
        vertcol_node.posx = -2500
        vertcol_node.posy = 0
        vertcol_node.name = layerName
        vertcol_node.colorsetname_Vertex = layerName
        vertcolID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=layerName)
        sxglobals.settings.nodeDict[layerName] = vertcolID

        # Connect diffuse
        sxglobals.settings.material.connect(
            vertcol_node.outputs.rgb,
            (shaderID, 3))

        #
        # Create material channels
        #

        for channel in channels:
            offset = channels.index(channel) * 500

            chancol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
            chancol_node.posx = -2000
            chancol_node.posy = -1000 - offset
            chancol_node.name = channel
            chancol_node.colorsetname_Vertex = channel
            chancolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=channel)
            sxglobals.settings.nodeDict[channel] = chancolID

            chanboolName = channel + 'Visibility'
            chanbool_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
            chanbool_node.posx = -2000
            chanbool_node.posy = -750 - offset
            chanbool_node.name = chanboolName
            chanbool_node.primvariableName = chanboolName
            chanboolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=chanboolName)
            sxglobals.settings.nodeDict[chanboolName] = chanboolID

            chanCastName = channel + 'Cast'
            chanCast_node = sxglobals.settings.material.add(sfxnodes.FloatToBool)
            chanCast_node.posx = -1750
            chanCast_node.posy = -750 - offset
            chanCast_node.name = chanCastName
            chanCastID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=chanCastName)
            sxglobals.settings.nodeDict[chanboolName] = chanCastID

            if3_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
            if3_node.posx = -1750
            if3_node.posy = -1000 - offset
            if3_node.name = channel + 'Comp'

            if channel == 'occlusion':
                sxglobals.settings.material.connect(
                    chancol_node.outputs.red,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    wcol_node.outputs.red,
                    if3_node.inputs.false)

                occ_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='occlusionComp')
                # Connect occlusion
                sxglobals.settings.material.connect(
                    (occ_nodeID, 0),
                    (shaderID, 2))

            elif channel == 'specular':
                specMul_node = sxglobals.settings.material.add(sfxnodes.Multiply)
                specMul_node.posx = -750
                specMul_node.posy = -500
                specMul_node.name = 'specularMultiplier'
                specMul_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularMultiplier')

                specPow_node = sxglobals.settings.material.add(sfxnodes.Pow)
                specPow_node.posx = -750
                specPow_node.posy = -750
                specPow_node.name = 'specularPower'
                specPow_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularPower')

                smv_node = sxglobals.settings.material.add(sfxnodes.Float)
                smv_node.posx = -1000
                smv_node.posy = -500
                smv_node.name = 'specularMultiplierValue'
                smv_node.value = 0.4
                smv_node.defineinheader = True
                smv_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularMultiplierValue')

                spv_node = sxglobals.settings.material.add(sfxnodes.Float)
                spv_node.posx = -1000
                spv_node.posy = -750
                spv_node.name = 'specularPowerValue'
                spv_node.value = 20
                spv_node.defineinheader = True
                # spv_nodeID = maya.cmds.shaderfx(
                #     sfxnode=materialName,
                #     getNodeIDByName='specularPowerValue')

                spec_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularComp')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if3_node.inputs.false)

                # Connect specular multiplier
                sxglobals.settings.material.connect(
                    (spec_nodeID, 0),
                    (specMul_nodeID, 0))
                sxglobals.settings.material.connect(
                    (smv_nodeID, 0),
                    (specMul_nodeID, 1))

                # Connect specular power
                # specRaw_nodeID = sxglobals.settings.nodeDict['specular']
                sxglobals.settings.material.connect(
                    spv_node.outputs.float,
                    specPow_node.inputs.x)
                sxglobals.settings.material.connect(
                    chancol_node.outputs.red,
                    specPow_node.inputs.y)

                # Connect specular
                sxglobals.settings.material.connect(
                    (specMul_nodeID, 0),
                    (shaderID, 5))
                # Connect specular power
                sxglobals.settings.material.connect(
                    (specPow_nodeID, 0),
                    (shaderID, 4))

            elif channel == 'transmission':
                trans_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='transmissionComp')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if3_node.inputs.false)
                # Connect transmission
                sxglobals.settings.material.connect(
                    (trans_nodeID, 0),
                    (shaderID, 9))

            elif channel == 'emission':
                emiss_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='emissionComp')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if3_node.inputs.false)
                # Connect emission
                sxglobals.settings.material.connect(
                    (emiss_nodeID, 0),
                    (shaderID, 1))

            sxglobals.settings.material.connect(
                chanbool_node.outputs.value,
                chanCast_node.inputs.value)
            sxglobals.settings.material.connect(
                chanCast_node.outputs.result,
                if3_node.inputs.condition)

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXShaderSG')
        # maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')

        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.dsm', s=2)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo1')
        maya.cmds.connectAttr(
            'SXShader.oc',
            'SXShaderSG.ss')
        maya.cmds.connectAttr(
            'SXShaderSG.msg',
            'SXMaterials_materialInfo1.sg')
        maya.cmds.relationship(
            'link', ':lightLinker1',
            'SXShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship(
            'shadowLink', ':lightLinker1',
            'SXShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr('SXShaderSG.pa', ':renderPartition.st', na=True)
        # maya.cmds.connectAttr(
        #    'SXShader.msg', ':defaultShaderList1.s', na=True)

        # automatically assign shader to existing multi-layer meshes
        meshList = maya.cmds.ls(ni=True, typ='mesh')
        for mesh in meshList:
            if maya.cmds.attributeQuery(
               'activeLayerSet', node=mesh, exists=True):
                maya.cmds.sets(mesh, e=True, forceElement='SXShaderSG')

    def createSXShader(self,
                       numLayers,
                       occlusion=False,
                       specular=False,
                       transmission=False,
                       emission=False):
        if maya.cmds.objExists('SXShader'):
            maya.cmds.delete('SXShader')
            print('SX Tools: Updating default materials')
        if maya.cmds.objExists('SXShaderSG'):
            maya.cmds.delete('SXShaderSG')

        else:
            print('SX Tools: Creating default materials')

        materialName = 'SXShader'
        sxglobals.settings.material = SFXNetwork.create(materialName)
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

        mode_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
        mode_node.name = 'shadingMode'
        mode_node.primvariableName = 'shadingMode'
        mode_node.posx = -3250
        mode_node.posy = 0

        transparency_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
        transparency_node.name = 'transparency'
        transparency_node.primvariableName = 'transparency'
        transparency_node.posx = -3500
        transparency_node.posy = 0

        transparencyCast_node = sxglobals.settings.material.add(sfxnodes.FloatToBool)
        transparencyCast_node.name = 'visCast'
        transparencyCast_node.posx = -3500
        transparencyCast_node.posy = 250

        bcol_node = sxglobals.settings.material.add(sfxnodes.Color)
        bcol_node.name = 'black'
        bcol_node.color = (0, 0, 0, 1)
        bcol_node.posx = -2500
        bcol_node.posy = -250
        # bcolID = maya.cmds.shaderfx(
        #     sfxnode=materialName, getNodeIDByName='black')

        wcol_node = sxglobals.settings.material.add(sfxnodes.Color)
        wcol_node.name = 'white'
        wcol_node.color = (1, 1, 1, 1)
        wcol_node.posx = -2500
        wcol_node.posy = -500
        # wcolID = maya.cmds.shaderfx(
        #     sfxnode=materialName, getNodeIDByName='white')

        alphaValue_node = sxglobals.settings.material.add(sfxnodes.Float)
        alphaValue_node.name = 'TestValue0'
        alphaValue_node.posx = -1500
        alphaValue_node.posy = 750
        alphaValue_node.value = 0

        addValue_node = sxglobals.settings.material.add(sfxnodes.Float)
        addValue_node.name = 'TestValue1'
        addValue_node.posx = -1500
        addValue_node.posy = 1000
        addValue_node.value = 1

        mulValue_node = sxglobals.settings.material.add(sfxnodes.Float)
        mulValue_node.name = 'TestValue2'
        mulValue_node.posx = -1500
        mulValue_node.posy = 1250
        mulValue_node.value = 2

        alphaTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        alphaTest_node.name = 'alphaTest'
        alphaTest_node.posx = -1250
        alphaTest_node.posy = 750

        addTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        addTest_node.name = 'addTest'
        addTest_node.posx = -1250
        addTest_node.posy = 1000

        mulTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        mulTest_node.name = 'mulTest'
        mulTest_node.posx = -1250
        mulTest_node.posy = 1250

        alphaIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        alphaIf_node.name = 'alphaIf'
        alphaIf_node.posx = -1000
        alphaIf_node.posy = 750

        addIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        addIf_node.name = 'addIf'
        addIf_node.posx = -1000
        addIf_node.posy = 1000

        mulIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        mulIf_node.name = 'mulIf'
        mulIf_node.posx = -1000
        mulIf_node.posy = 1250

        finalTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        finalTest_node.name = 'finalTest'
        finalTest_node.posx = -1250
        finalTest_node.posy = 1500

        debugTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        debugTest_node.name = 'debugTest'
        debugTest_node.posx = -1250
        debugTest_node.posy = 1750

        grayTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        grayTest_node.name = 'grayTest'
        grayTest_node.posx = -1250
        grayTest_node.posy = 2000

        visTest_node = sxglobals.settings.material.add(sfxnodes.FloatToBool)
        visTest_node.name = 'visCast'
        visTest_node.posx = -2250
        visTest_node.posy = 1250

        finalIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        finalIf_node.name = 'finalIf'
        finalIf_node.posx = -1000
        finalIf_node.posy = 1500

        debugIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        debugIf_node.name = 'debugIf'
        debugIf_node.posx = -1000
        debugIf_node.posy = 1750

        grayIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        grayIf_node.name = 'grayIf'
        grayIf_node.posx = -2000
        grayIf_node.posy = 750

        layerComp_node = sxglobals.settings.material.add(sfxnodes.Add)
        layerComp_node.name = 'layerComp'
        layerComp_node.posx = -1000
        layerComp_node.posy = 0
        layerComp_node.supportmulticonnections = True
        layerCompID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='layerComp')

        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='TraditionalGameSurfaceShader')
        sxglobals.settings.nodeDict['SXShader'] = shaderID

        rgbPathName = 'rgbPath'
        rgbPath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        rgbPath_node.posx = -2250
        rgbPath_node.posy = 0
        rgbPath_node.name = rgbPathName
        rgbPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=rgbPathName)

        alphaPathName = 'alphaPath'
        alphaPath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        alphaPath_node.posx = -2250
        alphaPath_node.posy = 250
        alphaPath_node.name = alphaPathName
        alphaPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=alphaPathName)

        vectconstName = 'alphaComp'
        vectconst_node = sxglobals.settings.material.add(sfxnodes.VectorConstruct)
        vectconst_node.posx = -2250
        vectconst_node.posy = 500
        vectconst_node.name = vectconstName
        vectconstID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=vectconstName)

        ifMaskName = 'ifMask'
        ifMask_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        ifMask_node.posx = -1750
        ifMask_node.posy = 500
        ifMask_node.name = ifMaskName
        ifMaskID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=ifMaskName)

        premulName = 'preMul'
        premul_node = sxglobals.settings.material.add(sfxnodes.Multiply)
        premul_node.posx = -1500
        premul_node.posy = 250
        premul_node.name = premulName
        premulID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=premulName)

        invOneName = 'invOne'
        invOne_node = sxglobals.settings.material.add(sfxnodes.InvertOneMinus)
        invOne_node.posx = -1750
        invOne_node.posy = 250
        invOne_node.name = invOneName
        # invOneID = maya.cmds.shaderfx(
        #     sfxnode=materialName, getNodeIDByName=invOneName)

        wlerpName = 'wLerp'
        wlerp_node = sxglobals.settings.material.add(sfxnodes.LinearInterpolateMix)
        wlerp_node.posx = -1500
        wlerp_node.posy = 0
        wlerp_node.name = wlerpName
        wlerpID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=wlerpName)

        lerpName = 'alphaLayer'
        lerp_node = sxglobals.settings.material.add(sfxnodes.LinearInterpolateMix)
        lerp_node.posx = -1250
        lerp_node.posy = 500
        lerp_node.name = lerpName
        lerpID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=lerpName)

        addName = 'addLayer'
        add_node = sxglobals.settings.material.add(sfxnodes.Add)
        add_node.posx = -1250
        add_node.posy = 250
        add_node.name = addName
        addID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=addName)

        mulName = 'mulLayer'
        mul_node = sxglobals.settings.material.add(sfxnodes.Multiply)
        mul_node.posx = -1250
        mul_node.posy = 0
        mul_node.name = mulName
        mulID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=mulName)

        blendModePathName = 'blendModePath'
        blendModePath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        blendModePath_node.posx = -2250
        blendModePath_node.posy = 750
        blendModePath_node.name = blendModePathName
        # blendModePathID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=blendModePathName)

        visPathName = 'visPath'
        visPath_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        visPath_node.posx = -750
        visPath_node.posy = 0
        visPath_node.name = visPathName
        # visPathID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=visPathName)

        visModePathName = 'visModePath'
        visModePath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        visModePath_node.posx = -2250
        visModePath_node.posy = 1000
        visModePath_node.name = visModePathName
        # visModePathID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=visModePathName)

        repeatName = 'repeatLoop'
        repeat_node = sxglobals.settings.material.add(sfxnodes.RepeatLoop)
        repeat_node.posx = -750
        repeat_node.posy = -250
        repeat_node.name = repeatName
        # repeatID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=repeatName)

        repeatAlphaName = 'repeatAlphaLoop'
        repeatAlpha_node = sxglobals.settings.material.add(sfxnodes.RepeatLoop)
        repeatAlpha_node.posx = -750
        repeatAlpha_node.posy = 250
        repeatAlpha_node.name = repeatAlphaName
        # repeatAlphaID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=repeatAlphaName)

        alphaAdd_node = sxglobals.settings.material.add(sfxnodes.Add)
        alphaAdd_node.name = 'alphaAdd'
        alphaAdd_node.posx = -1000
        alphaAdd_node.posy = 250
        alphaAddID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='alphaAdd')

        alphaVar_node = sxglobals.settings.material.add(sfxnodes.Float)
        alphaVar_node.name = 'alphaVar'
        alphaVar_node.value = 0
        alphaVar_node.posx = -1000
        alphaVar_node.posy = 500
        # alphaVarID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName='alphaVar')

        indexName = 'layerIndex'
        index_node = sxglobals.settings.material.add(sfxnodes.IntValue)
        index_node.posx = -1000
        index_node.posy = -250
        index_node.name = indexName
        # indexID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=indexName)

        countName = 'layerCount'
        count_node = sxglobals.settings.material.add(sfxnodes.IntValue)
        count_node.posx = -1250
        count_node.posy = -250
        count_node.name = countName
        count_node.value = sxglobals.settings.project['LayerCount']
        # countID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=countName)

        outputName = 'outputVar'
        output_node = sxglobals.settings.material.add(sfxnodes.Float3)
        output_node.posx = -1500
        output_node.posy = -250
        output_node.valueX = 0
        output_node.valueY = 0
        output_node.valueZ = 0
        output_node.name = outputName
        # outputID = maya.cmds.shaderfx(
        #     sfxnode=materialName,
        #     getNodeIDByName=outputName)

        diffCompName = 'diffuseComp'
        diffComp_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        diffComp_node.posx = -500
        diffComp_node.posy = 0
        diffComp_node.name = diffCompName
        diffComp_nodeID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=diffCompName)

        transCompName = 'transparencyComp'
        transComp_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        transComp_node.posx = -500
        transComp_node.posy = 250
        transComp_node.name = transCompName
        transCompID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName=transCompName)
        sxglobals.settings.nodeDict[transCompName] = transCompID

        #
        # Create requested number of layer-specific nodes
        #

        for k in range(0, numLayers):
            offset = k * 250
            layerName = 'layer' + str(k + 1)
            vertcol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
            vertcol_node.posx = -2500
            vertcol_node.posy = 0 + offset
            vertcol_node.name = layerName
            vertcol_node.colorsetname_Vertex = layerName
            vertcolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=layerName)
            sxglobals.settings.nodeDict[layerName] = vertcolID

            boolName = layerName + 'Visibility'
            bool_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
            bool_node.posx = -2750
            bool_node.posy = 0 + offset
            bool_node.name = boolName
            bool_node.primvariableName = boolName
            boolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=boolName)
            sxglobals.settings.nodeDict[boolName] = boolID

            blendName = layerName + 'BlendMode'
            blendMode_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
            blendMode_node.posx = -3000
            blendMode_node.posy = 0 + offset
            blendMode_node.name = blendName
            blendMode_node.primvariableName = blendName
            blendModeID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=blendName)
            sxglobals.settings.nodeDict[blendName] = blendModeID

            # Create connections
            sxglobals.settings.material.connect(
                vertcol_node.outputs.rgb,
                (rgbPathID, 0))
            sxglobals.settings.material.connect(
                vertcol_node.outputs.alpha,
                (alphaPathID, 0))
            sxglobals.settings.material.connect(
                bool_node.outputs.value,
                visModePath_node.inputs.options)
            sxglobals.settings.material.connect(
                blendMode_node.outputs.value,
                blendModePath_node.inputs.options)

        sxglobals.settings.material.connect(
            mode_node.outputs.value,
            finalTest_node.inputs.a)
        sxglobals.settings.material.connect(
            mode_node.outputs.value,
            debugTest_node.inputs.a)
        sxglobals.settings.material.connect(
            mode_node.outputs.value,
            grayTest_node.inputs.a)

        sxglobals.settings.material.connect(
            transparency_node.outputs.value,
            transparencyCast_node.inputs.value)
        sxglobals.settings.material.connect(
            transparencyCast_node.outputs.result,
            transComp_node.inputs.condition)

        sxglobals.settings.material.connect(
            alphaValue_node.outputs.float,
            finalTest_node.inputs.b)
        sxglobals.settings.material.connect(
            addValue_node.outputs.float,
            debugTest_node.inputs.b)
        sxglobals.settings.material.connect(
            mulValue_node.outputs.float,
            grayTest_node.inputs.b)

        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            vectconst_node.inputs.x)
        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            vectconst_node.inputs.y)
        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            vectconst_node.inputs.z)

        sxglobals.settings.material.connect(
            rgbPath_node.outputs.result,
            (premulID, 0))
        sxglobals.settings.material.connect(
            (vectconstID, 1),
            (premulID, 1))
        sxglobals.settings.material.connect(
            (vectconstID, 1),
            invOne_node.inputs.value)

        sxglobals.settings.material.connect(
            rgbPath_node.outputs.result,
            (wlerpID, 0))
        sxglobals.settings.material.connect(
            wcol_node.outputs.rgb,
            (wlerpID, 1))
        sxglobals.settings.material.connect(
            invOne_node.outputs.result,
            wlerp_node.inputs.mix)

        sxglobals.settings.material.connect(
            vectconst_node.outputs.float3,
            ifMask_node.inputs.true)
        sxglobals.settings.material.connect(
            rgbPath_node.outputs.result,
            ifMask_node.inputs.false)
        sxglobals.settings.material.connect(
            grayTest_node.outputs.result,
            ifMask_node.inputs.condition)
        sxglobals.settings.material.connect(
            (ifMaskID, 0),
            (lerpID, 1))

        sxglobals.settings.material.connect(
            premul_node.outputs.result,
            (addID, 1))
        sxglobals.settings.material.connect(
            wlerp_node.outputs.result,
            (mulID, 1))

        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            lerp_node.inputs.mix)

        sxglobals.settings.material.connect(
            output_node.outputs.float3,
            (lerpID, 0))
        sxglobals.settings.material.connect(
            output_node.outputs.float3,
            (addID, 0))
        sxglobals.settings.material.connect(
            output_node.outputs.float3,
            (mulID, 0))

        sxglobals.settings.material.connect(
            count_node.outputs.int,
            repeat_node.inputs.count)
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            repeat_node.inputs.index)
        sxglobals.settings.material.connect(
            output_node.outputs.float3,
            repeat_node.inputs.output)

        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            (alphaAddID, 0))
        sxglobals.settings.material.connect(
            count_node.outputs.int,
            repeatAlpha_node.inputs.count)
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            repeatAlpha_node.inputs.index)
        sxglobals.settings.material.connect(
            alphaVar_node.outputs.float,
            repeatAlpha_node.inputs.output)
        sxglobals.settings.material.connect(
            alphaVar_node.outputs.float,
            (alphaAddID, 1))

        sxglobals.settings.material.connect(
            alphaAdd_node.outputs.result,
            repeatAlpha_node.inputs.calculation)

        sxglobals.settings.material.connect(
            index_node.outputs.int,
            rgbPath_node.inputs.index)
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            alphaPath_node.inputs.index)
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            visModePath_node.inputs.index)
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            blendModePath_node.inputs.index)

        sxglobals.settings.material.connect(
            blendModePath_node.outputs.result,
            grayIf_node.inputs.false)

        sxglobals.settings.material.connect(
            alphaValue_node.outputs.float,
            alphaTest_node.inputs.b)
        sxglobals.settings.material.connect(
            addValue_node.outputs.float,
            addTest_node.inputs.b)
        sxglobals.settings.material.connect(
            mulValue_node.outputs.float,
            mulTest_node.inputs.b)

        sxglobals.settings.material.connect(
            bcol_node.outputs.rgb,
            alphaIf_node.inputs.false)
        sxglobals.settings.material.connect(
            bcol_node.outputs.rgb,
            addIf_node.inputs.false)
        sxglobals.settings.material.connect(
            bcol_node.outputs.rgb,
            mulIf_node.inputs.false)

        sxglobals.settings.material.connect(
            lerp_node.outputs.result,
            alphaIf_node.inputs.true)
        sxglobals.settings.material.connect(
            add_node.outputs.result,
            addIf_node.inputs.true)
        sxglobals.settings.material.connect(
            mul_node.outputs.result,
            mulIf_node.inputs.true)

        sxglobals.settings.material.connect(
            grayIf_node.outputs.result,
            alphaTest_node.inputs.a)
        sxglobals.settings.material.connect(
            grayIf_node.outputs.result,
            addTest_node.inputs.a)
        sxglobals.settings.material.connect(
            grayIf_node.outputs.result,
            mulTest_node.inputs.a)

        sxglobals.settings.material.connect(
            alphaTest_node.outputs.result,
            alphaIf_node.inputs.condition)
        sxglobals.settings.material.connect(
            addTest_node.outputs.result,
            addIf_node.inputs.condition)
        sxglobals.settings.material.connect(
            mulTest_node.outputs.result,
            mulIf_node.inputs.condition)

        sxglobals.settings.material.connect(
            finalTest_node.outputs.result,
            finalIf_node.inputs.condition)
        sxglobals.settings.material.connect(
            debugTest_node.outputs.result,
            debugIf_node.inputs.condition)
        sxglobals.settings.material.connect(
            grayTest_node.outputs.result,
            grayIf_node.inputs.condition)

        sxglobals.settings.material.connect(
            alphaValue_node.outputs.float,
            grayIf_node.inputs.true)

        sxglobals.settings.material.connect(
            alphaIf_node.outputs.result,
            (layerCompID, 0))
        sxglobals.settings.material.connect(
            addIf_node.outputs.result,
            (layerCompID, 1))
        sxglobals.settings.material.connect(
            mulIf_node.outputs.result,
            (layerCompID, 1))

        sxglobals.settings.material.connect(
            layerComp_node.outputs.result,
            visPath_node.inputs.true)
        sxglobals.settings.material.connect(
            output_node.outputs.float3,
            visPath_node.inputs.false)
        sxglobals.settings.material.connect(
            visModePath_node.outputs.result,
            visTest_node.inputs.value)
        sxglobals.settings.material.connect(
            visTest_node.outputs.result,
            visPath_node.inputs.condition)

        sxglobals.settings.material.connect(
            visPath_node.outputs.result,
            repeat_node.inputs.calculation)

        #
        # Create material channels
        #

        for channel in channels:
            offset = channels.index(channel) * 500

            chancol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
            chancol_node.posx = -2000
            chancol_node.posy = -1000 - offset
            chancol_node.name = channel
            chancol_node.colorsetname_Vertex = channel
            chancolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=channel)
            sxglobals.settings.nodeDict[channel] = chancolID

            chanboolName = channel + 'Visibility'
            chanbool_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
            chanbool_node.posx = -2000
            chanbool_node.posy = -750 - offset
            chanbool_node.name = chanboolName
            chanbool_node.primvariableName = chanboolName
            chanboolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=chanboolName)
            sxglobals.settings.nodeDict[chanboolName] = chanboolID

            chanCastName = channel + 'Cast'
            chanCast_node = sxglobals.settings.material.add(sfxnodes.FloatToBool)
            chanCast_node.posx = -1750
            chanCast_node.posy = -750 - offset
            chanCast_node.name = chanCastName
            chanCastID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=chanCastName)
            sxglobals.settings.nodeDict[chanboolName] = chanCastID

            if3_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
            if3_node.posx = -1750
            if3_node.posy = -1000 - offset

            if4_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
            if4_node.posx = -1500
            if4_node.posy = -1000 - offset
            if4_node.name = channel + 'Comp'

            if channel == 'occlusion':
                sxglobals.settings.material.connect(
                    chancol_node.outputs.red,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    wcol_node.outputs.red,
                    if3_node.inputs.false)
                sxglobals.settings.material.connect(
                    wcol_node.outputs.red,
                    if4_node.inputs.true)

                occ_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='occlusionComp')
                # Connect occlusion
                sxglobals.settings.material.connect(
                    (occ_nodeID, 0),
                    (shaderID, 2))

            elif channel == 'specular':
                specMul_node = sxglobals.settings.material.add(sfxnodes.Multiply)
                specMul_node.posx = -750
                specMul_node.posy = -500
                specMul_node.name = 'specularMultiplier'
                specMul_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularMultiplier')

                specPow_node = sxglobals.settings.material.add(sfxnodes.Pow)
                specPow_node.posx = -750
                specPow_node.posy = -750
                specPow_node.name = 'specularPower'
                specPow_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularPower')

                smv_node = sxglobals.settings.material.add(sfxnodes.Float)
                smv_node.posx = -1000
                smv_node.posy = -500
                smv_node.name = 'specularMultiplierValue'
                smv_node.value = 0.4
                smv_node.defineinheader = True
                smv_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularMultiplierValue')

                spv_node = sxglobals.settings.material.add(sfxnodes.Float)
                spv_node.posx = -1000
                spv_node.posy = -750
                spv_node.name = 'specularPowerValue'
                spv_node.value = 20
                spv_node.defineinheader = True
                # spv_nodeID = maya.cmds.shaderfx(
                #     sfxnode=materialName,
                #     getNodeIDByName='specularPowerValue')

                spec_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='specularComp')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if3_node.inputs.false)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if4_node.inputs.true)

                # Connect specular multiplier
                sxglobals.settings.material.connect(
                    (spec_nodeID, 0),
                    (specMul_nodeID, 0))
                sxglobals.settings.material.connect(
                    (smv_nodeID, 0),
                    (specMul_nodeID, 1))

                # Connect specular power
                # specRaw_nodeID = sxglobals.settings.nodeDict['specular']
                sxglobals.settings.material.connect(
                    spv_node.outputs.float,
                    specPow_node.inputs.x)
                sxglobals.settings.material.connect(
                    chancol_node.outputs.red,
                    specPow_node.inputs.y)

                # Connect specular
                sxglobals.settings.material.connect(
                    (specMul_nodeID, 0),
                    (shaderID, 5))
                # Connect specular power
                sxglobals.settings.material.connect(
                    (specPow_nodeID, 0),
                    (shaderID, 4))

            elif channel == 'transmission':
                trans_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='transmissionComp')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if3_node.inputs.false)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if4_node.inputs.true)
                # Connect transmission
                sxglobals.settings.material.connect(
                    (trans_nodeID, 0),
                    (shaderID, 9))

            elif channel == 'emission':
                emiss_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='emissionComp')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    if3_node.inputs.true)
                sxglobals.settings.material.connect(
                    bcol_node.outputs.rgb,
                    if3_node.inputs.false)
                sxglobals.settings.material.connect(
                    repeat_node.outputs.output,
                    if4_node.inputs.true)
                # Connect emission
                sxglobals.settings.material.connect(
                    (emiss_nodeID, 0),
                    (shaderID, 1))

            sxglobals.settings.material.connect(
                chanbool_node.outputs.value,
                chanCast_node.inputs.value)
            sxglobals.settings.material.connect(
                chanCast_node.outputs.result,
                if3_node.inputs.condition)
            sxglobals.settings.material.connect(
                grayTest_node.outputs.result,
                if4_node.inputs.condition)
            sxglobals.settings.material.connect(
                if3_node.outputs.result,
                if4_node.inputs.false)

        #
        # Glue it all together
        #

        sxglobals.settings.material.connect(
            grayTest_node.outputs.result,
            diffComp_node.inputs.condition)
        sxglobals.settings.material.connect(
            repeat_node.outputs.output,
            diffComp_node.inputs.false)
        sxglobals.settings.material.connect(
            repeatAlpha_node.outputs.output,
            transComp_node.inputs.true)
        sxglobals.settings.material.connect(
            addValue_node.outputs.float,
            transComp_node.inputs.false)
        sxglobals.settings.material.connect(
            bcol_node.outputs.rgb,
            diffComp_node.inputs.true)

        # Connect diffuse
        sxglobals.settings.material.connect(
            (diffComp_nodeID, 0),
            (shaderID, 3))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXShaderSG')
        # maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')

        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.dsm', s=2)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo1')
        maya.cmds.connectAttr(
            'SXShader.oc',
            'SXShaderSG.ss')
        maya.cmds.connectAttr(
            'SXShaderSG.msg',
            'SXMaterials_materialInfo1.sg')
        maya.cmds.relationship(
            'link', ':lightLinker1',
            'SXShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship(
            'shadowLink', ':lightLinker1',
            'SXShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr('SXShaderSG.pa', ':renderPartition.st', na=True)
        # maya.cmds.connectAttr(
        #    'SXShader.msg', ':defaultShaderList1.s', na=True)

        # automatically assign shader to existing multi-layer meshes
        meshList = maya.cmds.ls(ni=True, typ='mesh')
        for mesh in meshList:
            if maya.cmds.attributeQuery(
               'activeLayerSet', node=mesh, exists=True):
                maya.cmds.sets(mesh, e=True, forceElement='SXShaderSG')

    def createSXDebugShader(self,
                       numLayers,
                       occlusion=False,
                       specular=False,
                       transmission=False,
                       emission=False):
        if maya.cmds.objExists('SXDebugShader'):
            maya.cmds.delete('SXDebugShader')

        if maya.cmds.objExists('SXDebugShaderSG'):
            maya.cmds.delete('SXDebugShaderSG')

        materialName = 'SXDebugShader'
        sxglobals.settings.material = SFXNetwork.create(materialName)
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

        mode_node = sxglobals.settings.material.add(sfxnodes.PrimitiveVariable)
        mode_node.name = 'shadingMode'
        mode_node.primvariableName = 'shadingMode'
        mode_node.posx = -3250
        mode_node.posy = 0

        bcol_node = sxglobals.settings.material.add(sfxnodes.Color)
        bcol_node.name = 'black'
        bcol_node.color = (0, 0, 0, 1)
        bcol_node.posx = -2500
        bcol_node.posy = -250

        mulValue_node = sxglobals.settings.material.add(sfxnodes.Float)
        mulValue_node.name = 'TestValue2'
        mulValue_node.posx = -1500
        mulValue_node.posy = 1250
        mulValue_node.value = 2

        grayTest_node = sxglobals.settings.material.add(sfxnodes.Comparison)
        grayTest_node.name = 'grayTest'
        grayTest_node.posx = -1250
        grayTest_node.posy = 2000

        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='TraditionalGameSurfaceShader')
        sxglobals.settings.nodeDict['SXShader'] = shaderID

        rgbPathName = 'rgbPath'
        rgbPath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        rgbPath_node.posx = -2250
        rgbPath_node.posy = 0
        rgbPath_node.name = rgbPathName
        rgbPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=rgbPathName)

        alphaPathName = 'alphaPath'
        alphaPath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        alphaPath_node.posx = -2250
        alphaPath_node.posy = 250
        alphaPath_node.name = alphaPathName
        alphaPathID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=alphaPathName)

        vectconstName = 'alphaComp'
        vectconst_node = sxglobals.settings.material.add(sfxnodes.VectorConstruct)
        vectconst_node.posx = -2250
        vectconst_node.posy = 500
        vectconst_node.name = vectconstName
        vectconstID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=vectconstName)

        ifMaskName = 'ifMask'
        ifMask_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        ifMask_node.posx = -1750
        ifMask_node.posy = 500
        ifMask_node.name = ifMaskName
        ifMaskID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName=ifMaskName)

        rgbMul_node = sxglobals.settings.material.add(sfxnodes.Multiply)
        rgbMul_node.posx = -2000
        rgbMul_node.posy = 250
        rgbMul_node.name = 'rgbMultiplier'
        rgbMul_nodeID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='rgbMultiplier')

        indexName = 'layerIndex'
        index_node = sxglobals.settings.material.add(sfxnodes.IntValue)
        index_node.posx = -1000
        index_node.posy = -250
        index_node.name = indexName
        index_nodeID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='layerIndex')
        sxglobals.settings.nodeDict['layerIndex'] = index_nodeID

        maya.cmds.shaderfx(
            sfxnode=materialName,
            edit_bool=(index_nodeID, 'exposesetting', True))

        #
        # Create requested number of layer-specific nodes
        #

        for k in range(0, numLayers):
            offset = k * 250
            layerName = 'layer' + str(k + 1)
            vertcol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
            vertcol_node.posx = -2500
            vertcol_node.posy = 0 + offset
            vertcol_node.name = layerName
            vertcol_node.colorsetname_Vertex = layerName
            vertcolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=layerName)
            sxglobals.settings.nodeDict[layerName] = vertcolID

            # Create connections
            sxglobals.settings.material.connect(
                vertcol_node.outputs.rgb,
                (rgbPathID, 0))
            sxglobals.settings.material.connect(
                vertcol_node.outputs.alpha,
                (alphaPathID, 0))

        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            vectconst_node.inputs.x)
        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            vectconst_node.inputs.y)
        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            vectconst_node.inputs.z)

        sxglobals.settings.material.connect(
            vectconst_node.outputs.float3,
            ifMask_node.inputs.true)

        sxglobals.settings.material.connect(
            rgbPath_node.outputs.result,
            (rgbMul_nodeID, 0))

        sxglobals.settings.material.connect(
            alphaPath_node.outputs.result,
            (rgbMul_nodeID, 1))

        sxglobals.settings.material.connect(
            rgbMul_node.outputs.result,
            ifMask_node.inputs.false)

        sxglobals.settings.material.connect(
            mode_node.outputs.value,
            grayTest_node.inputs.a)

        sxglobals.settings.material.connect(
            mulValue_node.outputs.float,
            grayTest_node.inputs.b)

        sxglobals.settings.material.connect(
            grayTest_node.outputs.result,
            ifMask_node.inputs.condition)

        sxglobals.settings.material.connect(
            index_node.outputs.int,
            rgbPath_node.inputs.index)
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            alphaPath_node.inputs.index)

        #
        # Create material channels
        #

        for channel in channels:
            offset = channels.index(channel) * 500

            chancol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
            chancol_node.posx = -2000
            chancol_node.posy = -1000 - offset
            chancol_node.name = channel
            chancol_node.colorsetname_Vertex = channel
            chancolID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=channel)
            sxglobals.settings.nodeDict[channel] = chancolID

            sxglobals.settings.material.connect(
                chancol_node.outputs.rgb,
                (rgbPathID, 0))

            sxglobals.settings.material.connect(
                chancol_node.outputs.alpha,
                (alphaPathID, 0))


        # Glue it all together:

        # Connect emission
        sxglobals.settings.material.connect(
            (ifMaskID, 0),
            (shaderID, 1))

        # Connect diffuse
        sxglobals.settings.material.connect(
            bcol_node.outputs.rgb,
            (shaderID, 3))

        # Connect specular
        sxglobals.settings.material.connect(
            bcol_node.outputs.rgb,
            (shaderID, 5))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXDebugShaderSG')
        # maya.cmds.connectAttr('SXShader.oc', 'SXShaderSG.ss')

        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.dsm', s=2)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo5')
        maya.cmds.connectAttr(
            'SXDebugShader.oc',
            'SXDebugShaderSG.ss')
        maya.cmds.connectAttr(
            'SXDebugShaderSG.msg',
            'SXMaterials_materialInfo5.sg')
        maya.cmds.relationship(
            'link', ':lightLinker1',
            'SXDebugShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship(
            'shadowLink', ':lightLinker1',
            'SXDebugShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr('SXDebugShaderSG.pa', ':renderPartition.st', na=True)

    def createSXExportShader(self):
        if maya.cmds.objExists('SXExportShader'):
            maya.cmds.delete('SXExportShader')
        if maya.cmds.objExists('SXExportShaderSG'):
            maya.cmds.delete('SXExportShaderSG')

        maskID = sxglobals.settings.project['LayerData']['layer1'][2]
        maskIndex = int(maskID[1])
        numLayers = float(sxglobals.settings.project['LayerCount'])

        materialName = 'SXExportShader'
        sxglobals.settings.material = SFXNetwork.create(materialName)
        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='TraditionalGameSurfaceShader')

        black_node = sxglobals.settings.material.add(sfxnodes.Color)
        black_node.name = 'black'
        black_node.color = [0, 0, 0, 1]
        black_node.posx = -250
        black_node.posy = 250

        alphaIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        alphaIf_node.name = 'alphaColorIf'
        alphaIf_node.posx = -750
        alphaIf_node.posy = 0

        uvIf_node = sxglobals.settings.material.add(sfxnodes.IfElseBasic)
        uvIf_node.name = 'uvIf'
        uvIf_node.posx = -1000
        uvIf_node.posy = 250

        uConst_node = sxglobals.settings.material.add(sfxnodes.VectorConstruct)
        uConst_node.posx = -1250
        uConst_node.posy = 500
        uConst_node.name = 'uComp'

        vConst_node = sxglobals.settings.material.add(sfxnodes.VectorConstruct)
        vConst_node.posx = -1250
        vConst_node.posy = 750
        vConst_node.name = 'vComp'

        index_node = sxglobals.settings.material.add(sfxnodes.IntValue)
        index_node.posx = -2500
        index_node.posy = 500
        index_node.name = 'uvIndex'
        uvIndexID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='uvIndex')
        sxglobals.settings.exportNodeDict['uvIndex'] = uvIndexID

        indexRef_node = sxglobals.settings.material.add(sfxnodes.IntValue)
        indexRef_node.posx = -2500
        indexRef_node.posy = 750
        indexRef_node.value = maskIndex
        indexRef_node.name = 'uvMaskIndex'

        indexBool_node = sxglobals.settings.material.add(sfxnodes.BoolValue)
        indexBool_node.posx = -2500
        indexBool_node.posy = 1000
        indexBool_node.name = 'indexBool'
        indexBoolID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='indexBool')

        ifUv3_node = sxglobals.settings.material.add(sfxnodes.IfElse)
        ifUv3_node.posx = -1250
        ifUv3_node.posy = 1000

        divU_node = sxglobals.settings.material.add(sfxnodes.Divide)
        divU_node.posx = -1000
        divU_node.posy = 500
        divU_node.name = 'divU'
        divUID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='divU')

        divV_node = sxglobals.settings.material.add(sfxnodes.Divide)
        divV_node.posx = -1000
        divV_node.posy = 750
        divV_node.name = 'divV'
        divVID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='divV')

        divVal_node = sxglobals.settings.material.add(sfxnodes.Float3)
        divVal_node.posx = -2500
        divVal_node.posy = 1250
        divVal_node.valueX = numLayers
        divVal_node.valueY = numLayers
        divVal_node.valueZ = numLayers
        divVal_node.name = 'divVal'

        uv0_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv0_node.name = 'uv0String'
        uv0_node.posx = -2250
        uv0_node.posy = 500
        uv0_node.value = 'UV0'

        uv1_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv1_node.name = 'uv1String'
        uv1_node.posx = -2250
        uv1_node.posy = 750
        uv1_node.value = 'UV1'

        uv2_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv2_node.name = 'uv2String'
        uv2_node.posx = -2250
        uv2_node.posy = 1000
        uv2_node.value = 'UV2'

        uv3_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv3_node.name = 'uv3String'
        uv3_node.posx = -2250
        uv3_node.posy = 1250
        uv3_node.value = 'UV3'

        uv4_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv4_node.name = 'uv4String'
        uv4_node.posx = -2250
        uv4_node.posy = 1500
        uv4_node.value = 'UV4'

        uvPath_node = sxglobals.settings.material.add(sfxnodes.PathDirectionList)
        uvPath_node.posx = -2000
        uvPath_node.posy = 500

        uPath_node = sxglobals.settings.material.add(sfxnodes.PathDirection)
        uPath_node.name = 'uPath'
        uPath_node.posx = -750
        uPath_node.posy = 500
        uPathID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='uPath')

        vPath_node = sxglobals.settings.material.add(sfxnodes.PathDirection)
        vPath_node.name = 'vPath'
        vPath_node.posx = -750
        vPath_node.posy = 750
        vPathID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='vPath')

        vertcol_node = sxglobals.settings.material.add(sfxnodes.VertexColor)
        vertcol_node.posx = -1750
        vertcol_node.posy = 0

        uvset_node = sxglobals.settings.material.add(sfxnodes.UVSet)
        uvset_node.posx = -1750
        uvset_node.posy = 500
        uvset_node.name = 'uvSet'
        uvID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='uvSet')

        vectComp_node = sxglobals.settings.material.add(sfxnodes.VectorComponent)
        vectComp_node.posx = -1500
        vectComp_node.posy = 500
        vectComp_node.name = 'uvSplitter'

        uvBool_node = sxglobals.settings.material.add(sfxnodes.Bool)
        uvBool_node.posx = -2000
        uvBool_node.posy = 250
        uvBool_node.name = 'uvBool'
        uvBoolID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='uvBool')
        sxglobals.settings.exportNodeDict['uvBool'] = uvBoolID

        colorBool_node = sxglobals.settings.material.add(sfxnodes.Bool)
        colorBool_node.posx = -2000
        colorBool_node.posy = 0
        colorBool_node.name = 'colorBool'
        colorBoolID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='colorBool')
        sxglobals.settings.exportNodeDict['colorBool'] = colorBoolID

        # Create connections
        sxglobals.settings.material.connect(
            index_node.outputs.int,
            uvPath_node.inputs.index)
        sxglobals.settings.material.connect(
            uv0_node.outputs.string,
            uvPath_node.inputs.options)
        sxglobals.settings.material.connect(
            uv1_node.outputs.string,
            uvPath_node.inputs.options)
        sxglobals.settings.material.connect(
            uv2_node.outputs.string,
            uvPath_node.inputs.options)
        sxglobals.settings.material.connect(
            uv3_node.outputs.string,
            uvPath_node.inputs.options)
        sxglobals.settings.material.connect(
            uv4_node.outputs.string,
            uvPath_node.inputs.options)
        sxglobals.settings.material.connect(
            uvPath_node.outputs.result,
            (uvID, 1))

        sxglobals.settings.material.connect(
            index_node.outputs.int,
            ifUv3_node.inputs.a)
        sxglobals.settings.material.connect(
            indexRef_node.outputs.int,
            ifUv3_node.inputs.b)
        sxglobals.settings.material.connect(
            indexBool_node.outputs.bool,
            ifUv3_node.inputs.true)
        sxglobals.settings.material.connect(
            (indexBoolID, 1),
            ifUv3_node.inputs.false)

        sxglobals.settings.material.connect(
            ifUv3_node.outputs.result,
            (uPathID, 0))
        sxglobals.settings.material.connect(
            ifUv3_node.outputs.result,
            (vPathID, 0))

        sxglobals.settings.material.connect(
            uvset_node.outputs.uv,
            vectComp_node.inputs.vector)

        sxglobals.settings.material.connect(
            vectComp_node.outputs.x,
            uConst_node.inputs.x)
        sxglobals.settings.material.connect(
            vectComp_node.outputs.x,
            uConst_node.inputs.y)
        sxglobals.settings.material.connect(
            vectComp_node.outputs.x,
            uConst_node.inputs.z)
        sxglobals.settings.material.connect(
            vectComp_node.outputs.y,
            vConst_node.inputs.x)
        sxglobals.settings.material.connect(
            vectComp_node.outputs.y,
            vConst_node.inputs.y)
        sxglobals.settings.material.connect(
            vectComp_node.outputs.y,
            vConst_node.inputs.z)

        sxglobals.settings.material.connect(
            uConst_node.outputs.float3,
            (divUID, 0))
        sxglobals.settings.material.connect(
            vConst_node.outputs.float3,
            (divVID, 0))
        sxglobals.settings.material.connect(
            divVal_node.outputs.float3,
            (divUID, 1))
        sxglobals.settings.material.connect(
            divVal_node.outputs.float3,
            (divVID, 1))

        sxglobals.settings.material.connect(
            divU_node.outputs.result,
            uPath_node.inputs.a)
        sxglobals.settings.material.connect(
            divV_node.outputs.result,
            vPath_node.inputs.a)
        sxglobals.settings.material.connect(
            uConst_node.outputs.float3,
            uPath_node.inputs.b)
        sxglobals.settings.material.connect(
            vConst_node.outputs.float3,
            vPath_node.inputs.b)

        sxglobals.settings.material.connect(
            uvBool_node.outputs.bool,
            uvIf_node.inputs.condition)
        sxglobals.settings.material.connect(
            uPath_node.outputs.result,
            uvIf_node.inputs.true)
        sxglobals.settings.material.connect(
            vPath_node.outputs.result,
            uvIf_node.inputs.false)

        sxglobals.settings.material.connect(
            colorBool_node.outputs.bool,
            alphaIf_node.inputs.condition)
        sxglobals.settings.material.connect(
            vertcol_node.outputs.rgb,
            alphaIf_node.inputs.true)
        sxglobals.settings.material.connect(
            uvIf_node.outputs.result,
            alphaIf_node.inputs.false)

        sxglobals.settings.material.connect(
            alphaIf_node.outputs.result,
            (shaderID, 1))

        sxglobals.settings.material.connect(
            black_node.outputs.rgb,
            (shaderID, 3))
        sxglobals.settings.material.connect(
            black_node.outputs.rgb,
            (shaderID, 5))
        sxglobals.settings.material.connect(
            black_node.outputs.rgb,
            (shaderID, 6))
        sxglobals.settings.material.connect(
            black_node.outputs.red,
            (shaderID, 4))
        sxglobals.settings.material.connect(
            black_node.outputs.red,
            (shaderID, 7))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXExportShaderSG')
        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo2')
        maya.cmds.connectAttr(
            'SXExportShader.oc',
            'SXExportShaderSG.ss')
        maya.cmds.connectAttr(
            'SXExportShaderSG.msg',
            'SXMaterials_materialInfo2.sg')
        maya.cmds.relationship(
            'link', ':lightLinker1',
            'SXExportShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship(
            'shadowLink', ':lightLinker1',
            'SXExportShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr(
            'SXExportShaderSG.pa',
            ':renderPartition.st', na=True)
        # maya.cmds.connectAttr(
        #   'SXExportShader.msg', ':defaultShaderList1.s', na=True)

    def createSXExportOverlayShader(self):
        if maya.cmds.objExists('SXExportOverlayShader'):
            maya.cmds.delete('SXExportOverlayShader')
        if maya.cmds.objExists('SXExportOverlayShaderSG'):
            maya.cmds.delete('SXExportOverlayShaderSG')

        UV1 = None
        UV2 = None
        for value in sxglobals.settings.project['LayerData'].values():
            if value[4]:
                UV1 = value[2][0]
                UV2 = value[2][1]
        if UV1 is None:
            print(
                'SX Tools: No overlay layer specified,'
                'skipping SXExportOverlayShader')
            return

        materialName = 'SXExportOverlayShader'
        sxglobals.settings.material = SFXNetwork.create(materialName)
        shaderID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='TraditionalGameSurfaceShader')

        black_node = sxglobals.settings.material.add(sfxnodes.Color)
        black_node.name = 'black'
        black_node.color = [0, 0, 0, 1]
        black_node.posx = -250
        black_node.posy = 250

        uv1_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv1_node.name = 'uv1String'
        uv1_node.posx = -2250
        uv1_node.posy = -250
        uv1_node.value = UV1

        uv2_node = sxglobals.settings.material.add(sfxnodes.StringValue)
        uv2_node.name = 'uv2String'
        uv2_node.posx = -2250
        uv2_node.posy = 250
        uv2_node.value = UV2

        uvset1_node = sxglobals.settings.material.add(sfxnodes.UVSet)
        uvset1_node.posx = -2000
        uvset1_node.posy = -250
        uvset1_node.name = 'uvSet1'
        uv1ID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='uvSet1')

        uvset2_node = sxglobals.settings.material.add(sfxnodes.UVSet)
        uvset2_node.posx = -2000
        uvset2_node.posy = 250
        uvset2_node.name = 'uvSet2'
        uv2ID = maya.cmds.shaderfx(
            sfxnode=materialName,
            getNodeIDByName='uvSet2')

        vectComp1_node = sxglobals.settings.material.add(sfxnodes.VectorComponent)
        vectComp1_node.posx = -1750
        vectComp1_node.posy = -250
        vectComp1_node.name = 'uvSplitter1'

        vectComp2_node = sxglobals.settings.material.add(sfxnodes.VectorComponent)
        vectComp2_node.posx = -1750
        vectComp2_node.posy = 250
        vectComp2_node.name = 'uvSplitter2'

        rgbConst_node = sxglobals.settings.material.add(sfxnodes.VectorConstruct)
        rgbConst_node.posx = -1500
        rgbConst_node.posy = 0
        rgbConst_node.name = 'rgbCombiner'

        # Create connections
        sxglobals.settings.material.connect(
            uv1_node.outputs.string,
            (uv1ID, 1))
        sxglobals.settings.material.connect(
            uv2_node.outputs.string,
            (uv2ID, 1))
        sxglobals.settings.material.connect(
            uvset1_node.outputs.uv,
            vectComp1_node.inputs.vector)
        sxglobals.settings.material.connect(
            uvset2_node.outputs.uv,
            vectComp2_node.inputs.vector)
        sxglobals.settings.material.connect(
            vectComp1_node.outputs.x,
            rgbConst_node.inputs.x)
        sxglobals.settings.material.connect(
            vectComp1_node.outputs.y,
            rgbConst_node.inputs.y)
        sxglobals.settings.material.connect(
            vectComp2_node.outputs.x,
            rgbConst_node.inputs.z)

        sxglobals.settings.material.connect(
            rgbConst_node.outputs.float3,
            (shaderID, 3))

        sxglobals.settings.material.connect(
            black_node.outputs.rgb,
            (shaderID, 1))
        sxglobals.settings.material.connect(
            black_node.outputs.rgb,
            (shaderID, 5))
        sxglobals.settings.material.connect(
            black_node.outputs.rgb,
            (shaderID, 6))
        sxglobals.settings.material.connect(
            black_node.outputs.red,
            (shaderID, 4))
        sxglobals.settings.material.connect(
            black_node.outputs.red,
            (shaderID, 7))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=materialName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXExportOverlayShaderSG')
        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo3')
        maya.cmds.connectAttr(
            'SXExportOverlayShader.oc',
            'SXExportOverlayShaderSG.ss')
        maya.cmds.connectAttr(
            'SXExportOverlayShaderSG.msg',
            'SXMaterials_materialInfo3.sg')
        maya.cmds.relationship(
            'link', ':lightLinker1',
            'SXExportOverlayShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship(
            'shadowLink', ':lightLinker1',
            'SXExportOverlayShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr(
            'SXExportOverlayShaderSG.pa',
            ':renderPartition.st', na=True)
        # maya.cmds.connectAttr(
        #   'SXExportShader.msg', ':defaultShaderList1.s', na=True)

    def createSXPBShader(self):
        if maya.cmds.objExists('SXPBShader'):
            maya.cmds.delete('SXPBShader')
        if maya.cmds.objExists('SXPBShaderSG'):
            maya.cmds.delete('SXPBShaderSG')

        nodeIDs = []
        channels = ('occlusion', 'specular', 'transmission', 'emission')
        uvDict = {}

        pbmatName = 'SXPBShader'
        pbmat = StingrayPBSNetwork.create(pbmatName)
        nodeCount = maya.cmds.shaderfx(sfxnode=pbmatName, getNodeCount=True)
        shaderID = maya.cmds.shaderfx(
            sfxnode=pbmatName, getNodeIDByName='Standard_Base')
        maya.cmds.shaderfx(
            sfxnode=pbmatName,
            edit_action=(shaderID, "makeunique"))

        for i in range(nodeCount):
            nodeIDs.append(
                maya.cmds.shaderfx(
                    sfxnode='SXPBShader',
                    getNodeUIDFromIndex=i))
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
        # vertColID = maya.cmds.shaderfx(
        #     sfxnode=pbmatName,
        #     getNodeIDByName='vertCol')

        black_node = pbmat.add(pbsnodes.ConstantVector3)
        black_node.posx = -1250
        black_node.posy = 0
        black_node.name = 'black'
        blackID = maya.cmds.shaderfx(
            sfxnode=pbmatName,
            getNodeIDByName='black')

        for idx, channel in enumerate(channels):
            if sxglobals.settings.project['LayerData'][channel][5]:
                if int(sxglobals.settings.project['LayerData'][channel][2][1]) == 1:
                    uv_node = pbmat.add(pbsnodes.Texcoord1)
                elif int(sxglobals.settings.project['LayerData'][channel][2][1]) == 2:
                    uv_node = pbmat.add(pbsnodes.Texcoord2)
                elif int(sxglobals.settings.project['LayerData'][channel][2][1]) == 3:
                    uv_node = pbmat.add(pbsnodes.Texcoord3)
                uv_node.posx = -1000
                uv_node.posy = idx * 250
                uv_node.name = channel
                uvID = maya.cmds.shaderfx(
                    sfxnode=pbmatName,
                    getNodeIDByName=channel)
                uvDict[channel] = uvID
            else:
                uvDict[channel] = blackID

        invert_node = pbmat.add(pbsnodes.Invert)
        invert_node.posx = -750
        invert_node.posy = 250
        invert_node.name = 'inv'
        # invertID = maya.cmds.shaderfx(
        #     sfxnode=pbmatName,
        #     getNodeIDByName='inv')

        metPow_node = pbmat.add(pbsnodes.Power)
        metPow_node.posx = -500
        metPow_node.posy = 0
        metPow_node.name = 'MetallicPower'
        # metPowID = maya.cmds.shaderfx(
        #     sfxnode=pbmatName,
        #     getNodeIDByName='MetallicPower')

        roughPow_node = pbmat.add(pbsnodes.Power)
        roughPow_node.posx = -500
        roughPow_node.posy = 250
        roughPow_node.name = 'RoughnessPower'
        # roughPowID = maya.cmds.shaderfx(
        #     sfxnode=pbmatName,
        #     getNodeIDByName='RoughnessPower')

        metVal_node = pbmat.add(pbsnodes.MaterialVariable)
        metVal_node.posx = -1250
        metVal_node.posy = 250
        metVal_node.name = 'MetallicValue'
        metVal_node.type = 0
        metVal_node.defaultscalar = 0.9
        # metValID = maya.cmds.shaderfx(
        #     sfxnode=pbmatName,
        #     getNodeIDByName='MetallicValue')

        roughVal_node = pbmat.add(pbsnodes.MaterialVariable)
        roughVal_node.posx = -1250
        roughVal_node.posy = 500
        roughVal_node.name = 'RoughnessValue'
        roughVal_node.type = 0
        roughVal_node.defaultscalar = 0.4
        # roughValID = maya.cmds.shaderfx(
        #     sfxnode=pbmatName,
        #     getNodeIDByName='RoughnessValue')

        # Create connections
        pbmat.connect(
            vertCol_node.outputs.rgba,
            (shaderID, 1))

        pbmat.connect(
            (uvDict['occlusion'], 0),
            (shaderID, 8))
        if sxglobals.settings.project['LayerData']['occlusion'][2][0] == 'U':
            shader_node.activesocket = 8
            shader_node.socketswizzlevalue = 'x'
        elif sxglobals.settings.project['LayerData']['occlusion'][2][0] == 'V':
            shader_node.activesocket = 8
            shader_node.socketswizzlevalue = 'y'

        pbmat.connect(
            (uvDict['specular'], 0),
            metPow_node.inputs.x)
        pbmat.connect(
            (uvDict['specular'], 0),
            invert_node.inputs.value)
        if sxglobals.settings.project['LayerData']['specular'][2][0] == 'U':
            metPow_node.activesocket = 0
            metPow_node.socketswizzlevalue = 'x'
            invert_node.activesocket = 0
            invert_node.socketswizzlevalue = 'x'
        elif sxglobals.settings.project['LayerData']['specular'][2][0] == 'V':
            metPow_node.activesocket = 0
            metPow_node.socketswizzlevalue = 'y'
            invert_node.activesocket = 0
            invert_node.socketswizzlevalue = 'y'

        pbmat.connect(
            (uvDict['emission'], 0),
            (shaderID, 7))
        if sxglobals.settings.project['LayerData']['emission'][2][0] == 'U':
            shader_node.activesocket = 7
            shader_node.socketswizzlevalue = 'xxx'
        elif sxglobals.settings.project['LayerData']['emission'][2][0] == 'V':
            shader_node.activesocket = 7
            shader_node.socketswizzlevalue = 'yyy'

        pbmat.connect(
            invert_node.outputs.result,
            roughPow_node.inputs.x)
        pbmat.connect(
            metVal_node.outputs.result,
            metPow_node.inputs.y)
        pbmat.connect(
            roughVal_node.outputs.result,
            roughPow_node.inputs.y)

        pbmat.connect(
            metPow_node.outputs.result,
            (shaderID, 5))
        pbmat.connect(
            roughPow_node.outputs.result,
            (shaderID, 6))

        # Initialize network to show attributes in Maya AE
        maya.cmds.shaderfx(sfxnode=pbmatName, update=True)

        maya.cmds.createNode('shadingEngine', n='SXPBShaderSG')
        maya.cmds.setAttr('.ihi', 0)
        maya.cmds.setAttr('.ro', True)  # originally 'yes'

        maya.cmds.createNode('materialInfo', n='SXMaterials_materialInfo4')
        maya.cmds.connectAttr(
            'SXPBShader.oc',
            'SXPBShaderSG.ss')
        maya.cmds.connectAttr(
            'SXPBShaderSG.msg',
            'SXMaterials_materialInfo4.sg')
        maya.cmds.relationship(
            'link', ':lightLinker1',
            'SXPBShaderSG.message', ':defaultLightSet.message')
        maya.cmds.relationship(
            'shadowLink', ':lightLinker1',
            'SXPBShaderSG.message', ':defaultLightSet.message')
        maya.cmds.connectAttr(
            'SXPBShaderSG.pa',
            ':renderPartition.st', na=True)
        # maya.cmds.connectAttr(
        #   'SXExportShader.msg', ':defaultShaderList1.s', na=True)

    # The pre-vis material depends on lights in the scene
    # to correctly display occlusion

    def createSubMeshMaterials(self):
        if maya.cmds.objExists('sxSubMeshShader1'):
            maya.cmds.delete('sxSubMeshShader1')
        if maya.cmds.objExists('sxSubMeshShader1SG'):
            maya.cmds.delete('sxSubMeshShader1SG')
        if maya.cmds.objExists('sxSubMeshShader2'):
            maya.cmds.delete('sxSubMeshShader2')
        if maya.cmds.objExists('sxSubMeshShader2SG'):
            maya.cmds.delete('sxSubMeshShader2SG')
        if maya.cmds.objExists('sxSubMeshShader3'):
            maya.cmds.delete('sxSubMeshShader3')
        if maya.cmds.objExists('sxSubMeshShader3SG'):
            maya.cmds.delete('sxSubMeshShader3SG')

        maya.cmds.shadingNode('surfaceShader', asShader=True, name='sxSubMeshShader1')
        maya.cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name='sxSubMeshShader1SG')
        maya.cmds.connectAttr('sxSubMeshShader1.outColor', 'sxSubMeshShader1SG.surfaceShader')
        maya.cmds.setAttr('sxSubMeshShader1.outColor', 1, 0, 0)

        maya.cmds.shadingNode('surfaceShader', asShader=True, name='sxSubMeshShader2')
        maya.cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name='sxSubMeshShader2SG')
        maya.cmds.connectAttr('sxSubMeshShader2.outColor', 'sxSubMeshShader2SG.surfaceShader')
        maya.cmds.setAttr('sxSubMeshShader2.outColor', 0, 1, 0)

        maya.cmds.shadingNode('surfaceShader', asShader=True, name='sxSubMeshShader3')
        maya.cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name='sxSubMeshShader3SG')
        maya.cmds.connectAttr('sxSubMeshShader3.outColor', 'sxSubMeshShader3SG.surfaceShader')
        maya.cmds.setAttr('sxSubMeshShader3.outColor', 0, 0, 1)

    def createDefaultLights(self):
        setUpdated = False
        if len(maya.cmds.ls(type='light')) == 0:
            print('SX Tools: No lights found, creating default lights.')
            maya.cmds.directionalLight(
                name='defaultSXDirectionalLight',
                rotation=(-25, 30, 0),
                position=(0, 50, 0))
            maya.cmds.setAttr(
                'defaultSXDirectionalLight.useDepthMapShadows', 1)
            maya.cmds.setAttr(
                'defaultSXDirectionalLight.dmapFilterSize', 5)
            maya.cmds.setAttr(
                'defaultSXDirectionalLight.dmapResolution', 1024)
            maya.cmds.ambientLight(
                name='defaultSXAmbientLight',
                intensity=0.4,
                ambientShade=0,
                position=(0, 50, 0))
            setUpdated = True
        return setUpdated

    def createCreaseSets(self):
        numCreaseSets = 5
        setUpdated = False
        if not maya.cmds.objExists('sxCreasePartition'):
            maya.cmds.createNode(
                'partition',
                n='sxCreasePartition')
            setUpdated = True

        for i in xrange(numCreaseSets):
            setName = 'sxCrease' + str(i)
            if not maya.cmds.objExists(setName):
                maya.cmds.createNode(
                    'creaseSet',
                    n=setName)
                maya.cmds.setAttr(
                    setName + '.creaseLevel', i * 0.25)
                maya.cmds.connectAttr(
                    setName + '.partition',
                    'sxCreasePartition.sets[' + str(i) + ']')
                setUpdated = True

        if setUpdated:
            maya.cmds.setAttr(
                'sxCrease' + str(numCreaseSets - 1) + '.creaseLevel', 10)

        return setUpdated

    def createSubMeshSets(self):
        setUpdated = False
        if not maya.cmds.objExists('sxSubMeshPartition'):
            maya.cmds.createNode(
                'partition',
                n='sxSubMeshPartition')
            setUpdated = True
        if not maya.cmds.objExists('sxSubMesh0'):
            maya.cmds.createNode(
                'objectSet',
                n='sxSubMesh0')
            maya.cmds.connectAttr(
                'sxSubMesh0.partition',
                'sxSubMeshPartition.sets[0]')
            setUpdated = True
        if not maya.cmds.objExists('sxSubMesh1'):
            maya.cmds.createNode(
                'objectSet',
                n='sxSubMesh1')
            maya.cmds.connectAttr(
                'sxSubMesh1.partition',
                'sxSubMeshPartition.sets[1]')
            setUpdated = True
        if not maya.cmds.objExists('sxSubMesh2'):
            maya.cmds.createNode(
                'objectSet',
                n='sxSubMesh2')
            maya.cmds.connectAttr(
                'sxSubMesh2.partition',
                'sxSubMeshPartition.sets[2]')
            setUpdated = True
        return setUpdated

    def createDisplayLayers(self):
        setUpdated = False
        if 'assetsLayer' not in maya.cmds.ls(type='displayLayer'):
            print('SX Tools: Creating assetsLayer')
            maya.cmds.createDisplayLayer(
                name='assetsLayer', number=1, empty=True)
            setUpdated = True
        if 'skinMeshLayer' not in maya.cmds.ls(type='displayLayer'):
            print('SX Tools: Creating skinMeshLayer')
            maya.cmds.createDisplayLayer(
                name='skinMeshLayer', number=2, empty=True)
            setUpdated = True
        if 'exportsLayer' not in maya.cmds.ls(type='displayLayer'):
            print('SX Tools: Creating exportsLayer')
            maya.cmds.createDisplayLayer(
                name='exportsLayer', number=3, empty=True)
            setUpdated = True
        return setUpdated

    def setPrimVars(self):
        refLayers = sxglobals.layers.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        if refLayers == 'layer1':
            refLayers = 'layer1',

        for obj in sxglobals.settings.objectArray:
            flagList = maya.cmds.listAttr(obj, ud=True)
            if flagList is None:
                flagList = []
            if ('staticVertexColors' not in flagList):
                maya.cmds.addAttr(
                    obj,
                    ln='staticVertexColors',
                    at='bool', dv=False)
            if ('subdivisionLevel' not in flagList):
                maya.cmds.addAttr(
                    obj,
                    ln='subdivisionLevel',
                    at='byte', min=0, max=5, dv=0)
            if ('subMeshes' not in flagList):
                maya.cmds.addAttr(
                    obj,
                    ln='subMeshes',
                    at='bool', dv=False)
            if ('hardEdges' not in flagList):
                maya.cmds.addAttr(
                    obj,
                    ln='hardEdges',
                    at='bool', dv=True)
            if ('creaseBevels' not in flagList):
                maya.cmds.addAttr(
                    obj,
                    ln='creaseBevels',
                    at='bool', dv=False)
            if ('smoothingAngle' not in flagList):
                maya.cmds.addAttr(
                    obj,
                    ln='smoothingAngle',
                    at='byte', min=0, max=180, dv=80)

        for shape in sxglobals.settings.shapeArray:
            attrList = maya.cmds.listAttr(shape, ud=True)
            if attrList is None:
                attrList = []
            if ('activeLayerSet' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='activeLayerSet',
                    at='double', min=0, max=10, dv=0)
            if ('numLayerSets' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='numLayerSets',
                    at='double', min=0, max=9, dv=0)
            if ('transparency' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='transparency',
                    at='double', min=0, max=1, dv=0)
            if ('shadingMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='shadingMode',
                    at='double', min=0, max=2, dv=0)
            if ('occlusionVisibility' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='occlusionVisibility',
                    at='double', min=0, max=1, dv=1)
            if ('specularVisibility' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='specularVisibility',
                    at='double', min=0, max=1, dv=1)
            if ('transmissionVisibility' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='transmissionVisibility',
                    at='double', min=0, max=1, dv=1)
            if ('emissionVisibility' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='emissionVisibility',
                    at='double', min=0, max=1, dv=1)
            if ('occlusionBlendMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='occlusionBlendMode',
                    at='double', min=0, max=2, dv=0)
            if ('specularBlendMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='specularBlendMode',
                    at='double', min=0, max=2, dv=0)
            if ('transmissionBlendMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='transmissionBlendMode',
                    at='double', min=0, max=2, dv=0)
            if ('emissionBlendMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='emissionBlendMode',
                    at='double', min=0, max=2, dv=0)

            for k in range(0, sxglobals.settings.project['LayerCount']):
                blendName = str(refLayers[k]) + 'BlendMode'
                visName = str(refLayers[k]) + 'Visibility'
                if (blendName not in attrList):
                    maya.cmds.addAttr(
                        shape,
                        ln=blendName,
                        at='double', min=0, max=2, dv=0)
                if (visName not in attrList):
                    maya.cmds.addAttr(
                        shape,
                        ln=visName,
                        at='double', min=0, max=1, dv=1)
