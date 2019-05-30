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

    def createSXShader(self,
                       numLayers,
                       occlusion=False,
                       metallic=False,
                       smoothness=False,
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
        if metallic:
            channels.append('metallic')
        if smoothness:
            channels.append('smoothness')
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
            chanbool_nodeID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=chanboolName)
            sxglobals.settings.nodeDict[chanboolName] = chanbool_nodeID

            chanMulName = channel + 'Mul'
            chanMul_node = sxglobals.settings.material.add(sfxnodes.Multiply)
            chanMul_node.posx = -1500
            chanMul_node.posy = -750 - offset
            chanMul_node.name = chanMulName
            chanMul_nodeID = maya.cmds.shaderfx(
                sfxnode=materialName,
                getNodeIDByName=chanMulName)

            if channel == 'occlusion':
                chanLerpName = channel + 'Lerp'
                chanLerp_node = sxglobals.settings.material.add(sfxnodes.LinearInterpolateMix)
                chanLerp_node.posx = -1500
                chanLerp_node.posy = -750 - offset
                chanLerp_node.name = chanLerpName
                chanLerp_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName=chanLerpName)
                occ_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='occlusionLerp')
                sxglobals.settings.material.connect(
                    wcol_node.outputs.red,
                    (chanLerp_nodeID, 0))
                sxglobals.settings.material.connect(
                    chancol_node.outputs.red,
                    (chanLerp_nodeID, 1))
                sxglobals.settings.material.connect(
                    (chanbool_nodeID, 0),
                    (chanLerp_nodeID, 2))

            elif channel == 'metallic':
                met_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='metallicMul')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    (chanMul_nodeID, 0))
                sxglobals.settings.material.connect(
                    (chanbool_nodeID, 0),
                    (chanMul_nodeID, 1))

            elif channel == 'smoothness':
                smoothPow_node = sxglobals.settings.material.add(sfxnodes.Pow)
                smoothPow_node.posx = -750
                smoothPow_node.posy = -1000 - offset
                smoothPow_node.name = 'smoothnessPower'
                smoothPow_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='smoothnessPower')

                rpv_node = sxglobals.settings.material.add(sfxnodes.Float)
                rpv_node.posx = -1000
                rpv_node.posy = -1000 - offset
                rpv_node.name = 'smoothnessPowerValue'
                rpv_node.value = 1000
                rpv_node.defineinheader = False
                # spv_nodeID = maya.cmds.shaderfx(
                #     sfxnode=materialName,
                #     getNodeIDByName='smoothnessPowerValue')

                smooth_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='smoothnessMul')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.red,
                    (chanMul_nodeID, 0))
                sxglobals.settings.material.connect(
                    (chanbool_nodeID, 0),
                    (chanMul_nodeID, 1))

                # Connect smoothness power
                # smoothRaw_nodeID = sxglobals.settings.nodeDict['smoothness']
                sxglobals.settings.material.connect(
                    rpv_node.outputs.float,
                    smoothPow_node.inputs.x)
                sxglobals.settings.material.connect(
                    (smooth_nodeID, 0),
                    smoothPow_node.inputs.y)

            elif channel == 'transmission':
                trans_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='transmissionMul')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    (chanMul_nodeID, 0))
                sxglobals.settings.material.connect(
                    (chanbool_nodeID, 0),
                    (chanMul_nodeID, 1))

            elif channel == 'emission':
                emiss_nodeID = maya.cmds.shaderfx(
                    sfxnode=materialName,
                    getNodeIDByName='emissionMul')
                sxglobals.settings.material.connect(
                    chancol_node.outputs.rgb,
                    (chanMul_nodeID, 0))
                sxglobals.settings.material.connect(
                    (chanbool_nodeID, 0),
                    (chanMul_nodeID, 1))

        # Connect emission
        sxglobals.settings.material.connect(
            (emiss_nodeID, 0),
            (shaderID, 1))
        # Connect occlusion
        sxglobals.settings.material.connect(
            (occ_nodeID, 0),
            (shaderID, 2))
        # Connect smoothness power      
        sxglobals.settings.material.connect(
            (smoothPow_nodeID, 0),
            (shaderID, 4))
        # Connect smoothness
        sxglobals.settings.material.connect(
            (met_nodeID, 0),
            (shaderID, 5))
        # Connect metallic
        sxglobals.settings.material.connect(
            (met_nodeID, 0),
            (shaderID, 6))
        # Connect transmission
        sxglobals.settings.material.connect(
            (trans_nodeID, 0),
            (shaderID, 9))

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

        divBool_node = sxglobals.settings.material.add(sfxnodes.BoolValue)
        divBool_node.posx = -2500
        divBool_node.posy = 1000
        divBool_node.name = 'divBool'
        divBoolID = maya.cmds.shaderfx(
            sfxnode=materialName, getNodeIDByName='divBool')
        sxglobals.settings.exportNodeDict['divBool'] = divBoolID

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
            divBool_node.outputs.bool,
            (uPathID, 0))
        sxglobals.settings.material.connect(
            divBool_node.outputs.bool,
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
        channels = ('occlusion', 'metallic', 'smoothness', 'transmission', 'emission')
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

        inv_node = pbmat.add(pbsnodes.Invert)
        inv_node.posx = -750
        inv_node.posy = 0
        inv_node.name = 'invert'
        invID = maya.cmds.shaderfx(
            sfxnode=pbmatName,
            getNodeIDByName='invert')

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
            (uvDict['metallic'], 0),
            (shaderID, 5))
        if sxglobals.settings.project['LayerData']['metallic'][2][0] == 'U':
            shader_node.activesocket = 5
            shader_node.socketswizzlevalue = 'x'
        elif sxglobals.settings.project['LayerData']['metallic'][2][0] == 'V':
            shader_node.activesocket = 5
            shader_node.socketswizzlevalue = 'y'


        pbmat.connect(
            (uvDict['smoothness'], 0),
            (invID, 0))
        pbmat.connect(
            (invID, 0),
            (shaderID, 6))
        if sxglobals.settings.project['LayerData']['smoothness'][2][0] == 'U':
            inv_node.activesocket = 0
            inv_node.socketswizzlevalue = 'x'
        elif sxglobals.settings.project['LayerData']['smoothness'][2][0] == 'V':
            inv_node.activesocket = 0
            inv_node.socketswizzlevalue = 'y'

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
            (uvDict['transmission'], 0),
            (shaderID, 10))
        if sxglobals.settings.project['LayerData']['transmission'][2][0] == 'U':
            shader_node.activesocket = 10
            shader_node.socketswizzlevalue = 'x'
        elif sxglobals.settings.project['LayerData']['transmission'][2][0] == 'V':
            shader_node.activesocket = 10
            shader_node.socketswizzlevalue = 'y'

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
                'defaultSXDirectionalLight.useRayTraceShadows', 1)
            maya.cmds.setAttr(
                'defaultSXDirectionalLight.lightAngle', 10.0)
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
            if ('metallicVisibility' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='metallicVisibility',
                    at='double', min=0, max=1, dv=1)
            if ('smoothnessVisibility' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='smoothnessVisibility',
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
            if ('metallicBlendMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='metallicBlendMode',
                    at='double', min=0, max=2, dv=0)
            if ('smoothnessBlendMode' not in attrList):
                maya.cmds.addAttr(
                    shape,
                    ln='smoothnessBlendMode',
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
