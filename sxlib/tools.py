# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
#
#   Curvature calculation method based on work by Stepan Jirka
#   http://www.stepanjirka.com/maya-api-curvature-shader/
# ----------------------------------------------------------------------------

import maya.cmds
import maya.api.OpenMaya as OM
import math
import random
import sxglobals

class ToolActions(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting tools')

    def assignToCreaseSet(self, setName):
        creaseSets = (
            'sxCrease0',
            'sxCrease1',
            'sxCrease2',
            'sxCrease3',
            'sxCrease4')
        if ((maya.cmds.filterExpand(
                sxglobals.settings.componentArray, sm=31) is not None) or
            (maya.cmds.filterExpand(
                sxglobals.settings.componentArray, sm=32) is not None)):

            for set in creaseSets:
                if maya.cmds.sets(sxglobals.settings.componentArray, isMember=set):
                    maya.cmds.sets(sxglobals.settings.componentArray, remove=set)
            maya.cmds.sets(sxglobals.settings.componentArray, forceElement=setName)
        else:
            edgeList = maya.cmds.polyListComponentConversion(
                sxglobals.settings.componentArray, te=True)
            for set in creaseSets:
                if maya.cmds.sets(edgeList, isMember=set):
                    maya.cmds.sets(edgeList, remove=set)
            maya.cmds.sets(edgeList, forceElement=setName)

    def rayRandomizer(self):
        u1 = random.uniform(0, 1)
        u2 = random.uniform(0, 1)
        r = math.sqrt(u1)
        theta = 2*math.pi*u2

        x = r * math.cos(theta)
        y = r * math.sin(theta)

        return OM.MVector(x, y, math.sqrt(max(0, 1 - u1)))

    def bakeOcclusion(self, rayCount=250, bias=0.000001, max=10.0, weighted=True, comboOffset=0.9):
        bboxCoords = []
        newBboxCoords = []
        sxglobals.settings.bakeSet = sxglobals.settings.shapeArray
        contribution = 1.0/float(rayCount)

        if sxglobals.settings.project['LayerData']['occlusion'][5] is True:
            sxglobals.layers.setColorSet('occlusion')

        # generate global pass combo mesh
        if len(sxglobals.settings.bakeSet) > 1:
            globalMesh = maya.cmds.polyUnite(maya.cmds.duplicate(sxglobals.settings.bakeSet, renameChildren=True), ch=False, name='comboOcclusionObject')
            maya.cmds.polyMoveFacet(globalMesh, lsx=comboOffset, lsy=comboOffset, lsz=comboOffset)
            if sxglobals.settings.tools['bakeGroundPlane'] is False:
                sxglobals.settings.bakeSet.append(globalMesh[0])
        else:
            globalMesh = maya.cmds.duplicate(sxglobals.settings.bakeSet[0], name='comboOcclusionObject')
            if sxglobals.settings.tools['bakeGroundPlane'] is False:
                sxglobals.settings.bakeSet.append(globalMesh[0])

        if sxglobals.settings.tools['bakeGroundPlane'] is True:
            bbox = []
            maya.cmds.polyPlane(
                name='sxGroundPlane',
                w=sxglobals.settings.tools['bakeGroundScale'],
                h=sxglobals.settings.tools['bakeGroundScale'],
                sx=1, sy=1, ax=(0, 1, 0), cuv=0, ch=0)

            if len(sxglobals.settings.bakeSet) > 1:
                bbox = maya.cmds.exactWorldBoundingBox('comboOcclusionObjectShape')
            else:
                bbox = maya.cmds.exactWorldBoundingBox(sxglobals.settings.bakeSet[0])
            maya.cmds.setAttr(
                'sxGroundPlane.translateY',
                (bbox[1] - sxglobals.settings.tools['bakeGroundOffset']))

            bakeTx = sxglobals.export.getTransforms([sxglobals.settings.bakeSet[0], ])
            groundPos = maya.cmds.getAttr(
                str(bakeTx[0]) + '.translate')[0]
            maya.cmds.setAttr('sxGroundPlane.translateX', groundPos[0])
            maya.cmds.setAttr(
                'sxGroundPlane.translateY',
                (bbox[1] - sxglobals.settings.tools['bakeGroundOffset']))
            maya.cmds.setAttr('sxGroundPlane.translateZ', groundPos[2])

            globalMesh = maya.cmds.polyUnite(('comboOcclusionObject', 'sxGroundPlane'), ch=False, name='comboOcclusionObject')
            sxglobals.settings.bakeSet.append(globalMesh[0])

        for bake in sxglobals.settings.bakeSet:
            selectionList = OM.MSelectionList()
            nodeDagPath = OM.MDagPath()
            vtxPoints = OM.MPointArray()
            vtxColors = OM.MColorArray()
            vtxIds = OM.MIntArray()
            vtxFloatNormals = OM.MFloatVectorArray()
            vtxNormal = OM.MVector()

            selectionList.add(bake)
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)
            accelGrid = MFnMesh.autoUniformGridParams()
            vtxPoints = MFnMesh.getPoints(OM.MSpace.kWorld)
            vtxFloatNormals = MFnMesh.getVertexNormals(weighted, OM.MSpace.kWorld)
            numVtx = MFnMesh.numVertices

            vtxColors.setLength(numVtx)
            vtxIds.setLength(numVtx)

            hemiSphere = OM.MVectorArray()
            hemiSphere.setLength(rayCount)
            for idx in xrange(rayCount):
                hemiSphere[idx] = self.rayRandomizer()

            vtxIt = OM.MItMeshVertex(nodeDagPath)
            while not vtxIt.isDone():
                i = vtxIt.index()
                vtxIds[i] = i
                vtxNormal = vtxIt.getNormal()
                point = OM.MFloatPoint(vtxPoints[i])
                point = point + bias*vtxFloatNormals[i]
                occValue = 1.0
                forward = OM.MVector(OM.MVector.kZaxisVector)
                rotQuat = forward.rotateTo(vtxNormal)
                sampleRays = OM.MFloatVectorArray()
                sampleRays.setLength(rayCount)

                for e in xrange(rayCount):
                    sampleRays[e] = OM.MFloatVector(hemiSphere[e].rotateBy(rotQuat))
                for e in xrange(rayCount):
                    result = MFnMesh.anyIntersection(point, sampleRays[e], OM.MSpace.kWorld, max, False, accelParams=accelGrid, tolerance=0.001)
                    if result[2] != -1:
                        occValue = occValue - contribution

                vtxColors[i].r = occValue
                vtxColors[i].g = occValue
                vtxColors[i].b = occValue
                vtxColors[i].a = 1.0

                vtxIt.next()

            MFnMesh.setVertexColors(vtxColors, vtxIds)
            MFnMesh.freeCachedIntersectionAccelerator()

            # assign global mesh colors to individual pieces
            if bake == globalMesh[0]:
                sxglobals.settings.bakeSet.remove(bake)
                bboxCoords.sort()
                if len(sxglobals.settings.bakeSet) > 1 or sxglobals.settings.tools['bakeGroundPlane'] is True:
                    newObjs = maya.cmds.polySeparate(globalMesh, ch=False)
                else:
                    newObjs = (globalMesh[0], )
                for newObj in newObjs:
                    bbx = maya.cmds.exactWorldBoundingBox(newObj)
                    if sxglobals.settings.tools['bakeGroundPlane'] is True:
                        if (math.fabs(bbx[3] - bbx[0]) == sxglobals.settings.tools['bakeGroundScale']) and (bbx[1] - bbx[4]) == 0:
                            #print 'hey groundplane', newObj, bbx
                            maya.cmds.delete(newObj)
                            newObjs.remove(newObj)
                            continue
                    bbSize = math.fabs((bbx[3]-bbx[0])*(bbx[4]-bbx[1])*(bbx[5]-bbx[3]))
                    bbId = (bbx[0]+10*bbx[1]+100*bbx[2]+bbx[3]+10*bbx[4]+100*bbx[5])
                    newBboxCoords.append((bbId, bbSize, bbx[0], bbx[1], bbx[2], newObj))

                newBboxCoords.sort()

                for idx, obj in enumerate(newBboxCoords):
                    selectionList = OM.MSelectionList()
                    selectionList.add(obj[5])
                    nodeDagPath = selectionList.getDagPath(0)
                    MFnMesh = OM.MFnMesh(nodeDagPath)
                    globalColorArray = OM.MColorArray()
                    globalColorArray = MFnMesh.getFaceVertexColors(colorSet='occlusion')
                    sxglobals.settings.globalOcclusionDict[bboxCoords[idx][5]] = globalColorArray

                maya.cmds.delete(globalMesh)
            else:
                localColorArray = OM.MColorArray()
                localColorArray = MFnMesh.getFaceVertexColors(colorSet='occlusion')
                sxglobals.settings.localOcclusionDict[bake] = localColorArray
                # calculate bounding box and use it to sort shapes
                bbx = maya.cmds.exactWorldBoundingBox(bake)
                bbSize = math.fabs((bbx[3]-bbx[0])*(bbx[4]-bbx[1])*(bbx[5]-bbx[3]))
                bbId = (bbx[0]+10*bbx[1]+100*bbx[2]+bbx[3]+10*bbx[4]+100*bbx[5])
                bboxCoords.append((bbId, bbSize, bbx[0], bbx[1], bbx[2], bake))

        maya.cmds.select(sxglobals.settings.bakeSet)
        sxglobals.core.selectionManager()


    def bakeOcclusionMR(self):
        bbox = []
        sxglobals.settings.bakeSet = sxglobals.settings.shapeArray

        if sxglobals.settings.project['LayerData']['occlusion'][5] is True:
            sxglobals.layers.setColorSet('occlusion')

        if sxglobals.settings.tools['bakeGroundPlane'] is True:
            maya.cmds.polyPlane(
                name='sxGroundPlane',
                w=sxglobals.settings.tools['bakeGroundScale'],
                h=sxglobals.settings.tools['bakeGroundScale'],
                sx=1, sy=1, ax=(0, 1, 0), cuv=2, ch=0)
            maya.cmds.select(sxglobals.settings.bakeSet)
            sxglobals.core.selectionManager()

        if maya.cmds.objExists('sxVertexBakeSet') is False:
            maya.cmds.createNode(
                'vertexBakeSet',
                n='sxVertexBakeSet',
                skipSelect=True)
            maya.cmds.partition(
                'sxVertexBakeSet',
                n='vertexBakePartition')

            maya.cmds.addAttr(
                'sxVertexBakeSet',
                ln='filterSize', sn='fs', min=-1)
            maya.cmds.setAttr(
                'sxVertexBakeSet.filterSize', 0.001)
            maya.cmds.addAttr(
                'sxVertexBakeSet',
                ln='filterNormalTolerance',
                sn='fns', min=0, max=180)
            maya.cmds.setAttr('sxVertexBakeSet.filterNormalTolerance', 5)
            maya.cmds.setAttr('sxVertexBakeSet.colorMode', 3)
            maya.cmds.setAttr('sxVertexBakeSet.occlusionRays', 256)
            maya.cmds.setAttr('sxVertexBakeSet.colorBlending', 0)

        if sxglobals.settings.tools['bakeTogether'] is True:
            if sxglobals.settings.tools['bakeGroundPlane'] is True:
                bbox = maya.cmds.exactWorldBoundingBox(sxglobals.settings.bakeSet)
                maya.cmds.setAttr(
                    'sxGroundPlane.translateY',
                    (bbox[1] - sxglobals.settings.tools['bakeGroundOffset']))
            maya.cmds.convertLightmapSetup(
                camera='persp', vm=True, bo='sxVertexBakeSet')
        else:
            for bake in sxglobals.settings.bakeSet:
                maya.cmds.setAttr((str(bake) + '.visibility'), False)

            # bake separately
            for bake in sxglobals.settings.bakeSet:
                if sxglobals.settings.tools['bakeGroundPlane'] is True:
                    bbox = maya.cmds.exactWorldBoundingBox(bake)
                    bakeTx = sxglobals.export.getTransforms([bake, ])
                    groundPos = maya.cmds.getAttr(
                        str(bakeTx[0]) + '.translate')[0]
                    maya.cmds.setAttr('sxGroundPlane.translateX', groundPos[0])
                    maya.cmds.setAttr(
                        'sxGroundPlane.translateY',
                        (bbox[1] - sxglobals.settings.tools['bakeGroundOffset']))
                    maya.cmds.setAttr('sxGroundPlane.translateZ', groundPos[2])

                maya.cmds.setAttr((str(bake) + '.visibility'), True)
                maya.cmds.select(bake)
                sxglobals.core.selectionManager()
                maya.cmds.convertLightmapSetup(
                    camera='persp', vm=True, bo='sxVertexBakeSet')
                maya.cmds.setAttr((str(bake) + '.visibility'), False)

            for bake in sxglobals.settings.bakeSet:
                maya.cmds.setAttr((str(bake) + '.visibility'), True)

        if sxglobals.settings.tools['bakeGroundPlane'] is True:
            maya.cmds.delete('sxGroundPlane')

        maya.cmds.select(sxglobals.settings.bakeSet)
        sxglobals.core.selectionManager()

    def bakeBlendOcclusion(self):
        startTimeOcc = maya.cmds.timerX()
        print('SX Tools: Baking ambient occlusion')
        self.bakeOcclusion(sxglobals.settings.tools['rayCount'], sxglobals.settings.tools['bias'], sxglobals.settings.tools['maxDistance'], True, sxglobals.settings.tools['comboOffset'])
        sxglobals.settings.tools['blendSlider'] = 0.5
        self.blendOcclusion()
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Occlusion baking time: ' + str(totalTime))

    def bakeBlendOcclusionMR(self):
        startTimeOcc = maya.cmds.timerX()
        print('SX Tools: Baking ambient occlusion')
        ground = sxglobals.settings.tools['bakeGroundPlane']
        sxglobals.settings.tools['bakeGroundPlane'] = False
        sxglobals.settings.tools['bakeTogether'] = False
        self.bakeOcclusionMR()

        for shape in sxglobals.settings.shapeArray:
            selectionList = OM.MSelectionList()
            selectionList.add(shape)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            localColorArray = OM.MColorArray()
            localColorArray = MFnMesh.getFaceVertexColors(colorSet='occlusion')
            sxglobals.settings.localOcclusionDict[shape] = localColorArray

        sxglobals.settings.tools['bakeGroundPlane'] = ground
        sxglobals.settings.tools['bakeTogether'] = True
        self.bakeOcclusionMR()

        for shape in sxglobals.settings.shapeArray:
            selectionList = OM.MSelectionList()
            selectionList.add(shape)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            globalColorArray = OM.MColorArray()
            globalColorArray = MFnMesh.getFaceVertexColors(
                colorSet='occlusion')
            sxglobals.settings.globalOcclusionDict[shape] = globalColorArray

        sxglobals.settings.tools['blendSlider'] = 1.0
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Occlusion baking time: ' + str(totalTime))

    def blendOcclusion(self):
        sliderValue = sxglobals.settings.tools['blendSlider']

        for bake in sxglobals.settings.bakeSet:
            selectionList = OM.MSelectionList()
            nodeDagPath = OM.MDagPath()
            localColorArray = OM.MColorArray()
            globalColorArray = OM.MColorArray()
            layerColorArray = OM.MColorArray()
            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()
            selectionList.add(bake)
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            localColorArray = sxglobals.settings.localOcclusionDict[bake]
            globalColorArray = sxglobals.settings.globalOcclusionDict[bake]
            layerColorArray = MFnMesh.getFaceVertexColors(colorSet='occlusion')
            lenSel = len(layerColorArray)
            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            #print bake, len(localColorArray), len(globalColorArray)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()
                layerColorArray[k].r = (
                    (1-sliderValue) * localColorArray[k].r +
                    sliderValue * globalColorArray[k].r)
                layerColorArray[k].g = (
                    (1-sliderValue) * localColorArray[k].g +
                    sliderValue * globalColorArray[k].g)
                layerColorArray[k].b = (
                    (1-sliderValue) * localColorArray[k].b +
                    sliderValue * globalColorArray[k].b)
                k += 1
                fvIt.next()

            maya.cmds.polyColorSet(
                bake, currentColorSet=True, colorSet='occlusion')
            MFnMesh.setFaceVertexColors(layerColorArray, faceIds, vtxIds)

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())


    def applyTexture(self, texture, uvSetName, applyAlpha):
        colors = []
        color = []

        maya.cmds.polyUVSet(
            sxglobals.settings.shapeArray,
            currentUVSet=True,
            uvSet=uvSetName)
        components = maya.cmds.ls(
            maya.cmds.polyListComponentConversion(
                sxglobals.settings.shapeArray, tv=True), fl=True)

        for component in components:
            fvs = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(
                    component, tvf=True), fl=True)
            uvs = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(
                    fvs, tuv=True), fl=True)
            for uv in uvs:
                uvCoord = maya.cmds.polyEditUV(uv, query=True)
                colors.append(
                    maya.cmds.colorAtPoint(
                        texture, o='RGBA', u=uvCoord[0], v=uvCoord[1]))
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
                        component,
                        r=color[0],
                        g=color[1],
                        b=color[2],
                        a=color[3])

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()

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

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()

    def applyMasterPalette(self, objects):
        for i in xrange(1, 6):
            targetLayers = sxglobals.settings.project['paletteTarget'+str(i)]
            maya.cmds.palettePort('masterPalette', edit=True, scc=i-1)
            for layer in targetLayers:
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
                # clear empty vertices of RGB info
                if layer != 'layer1':
                    maskList = []
                    vertFaceList = maya.cmds.ls(
                        maya.cmds.polyListComponentConversion(
                            objects, tvf=True), fl=True)

                    for vertFace in vertFaceList:
                        if maya.cmds.polyColorPerVertex(
                           vertFace, query=True, a=True)[0] == 0:
                            maskList.append(vertFace)

                    if len(maskList) == 0:
                        maskList = vertFaceList

                    maya.cmds.select(maskList)
                    sxglobals.layers.clearLayer([layer, ])

        maya.cmds.select(objects)
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()

    def gradientFill(self, axis):
        selectionCache = sxglobals.settings.selectionArray
        layer = sxglobals.layers.getSelectedLayer()
        mod = OM.MDGModifier()
        colorRep = OM.MFnMesh.kRGBA
        space = OM.MSpace.kWorld

        if len(sxglobals.settings.componentArray) > 0:
            components = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(
                    sxglobals.settings.componentArray, tvf=True), fl=True)
            # tempArray is constructed because
            # polyEvaluate doesn't work on face vertices
            tempArray = maya.cmds.ls(maya.cmds.polyListComponentConversion(
                    sxglobals.settings.componentArray, tv=True), fl=True)
            maya.cmds.select(tempArray)
            objectBounds = maya.cmds.polyEvaluate(bc=True, ae=True)
        else:
            objectBounds = maya.cmds.polyEvaluate(
                sxglobals.settings.shapeArray, b=True, ae=True)

        objectBoundsXmin = objectBounds[0][0]
        objectBoundsXmax = objectBounds[0][1]
        objectBoundsYmin = objectBounds[1][0]
        objectBoundsYmax = objectBounds[1][1]
        objectBoundsZmin = objectBounds[2][0]
        objectBoundsZmax = objectBounds[2][1]


        # Build face vert lists for the full meshes of the objects with component selections
        selectionList = OM.MSelectionList()
        for sl in sxglobals.settings.selectionArray:
            selectionList.add(sl)
        selDagPath = OM.MDagPath()
        selectionIter = OM.MItSelectionList(selectionList)

        while not selectionIter.isDone():
            selDagPath = selectionIter.getDagPath()
            MFnMesh = OM.MFnMesh(selDagPath)

            fvColors = OM.MColorArray()
            fvColors = MFnMesh.getFaceVertexColors(colorSet=layer)

            vtxIds = OM.MIntArray()
            fvIds = OM.MIntArray()
            faceIds = OM.MIntArray()

            lenSel = len(fvColors)
            faceIds.setLength(lenSel)
            fvIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(selDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                fvIds[k] = fvIt.faceVertexId()
                vtxIds[k] = fvIt.vertexId()
                k += 1
                fvIt.next()

            if len(sxglobals.settings.componentArray) > 0:
                # Convert component selection to face verts, fill matching vert ids with color
                selection = OM.MSelectionList()
                for component in components:
                    selection.add(component)

                selDag = OM.MDagPath()
                fVert = OM.MObject()

                # Match component selection with components of full mesh and modify fvColors array
                (selDag, fVert) = selectionIter.getComponent()
                MFnMesh = OM.MFnMesh(selDag)
                fvIt = OM.MItMeshFaceVertex(selDag, fVert)
                while not fvIt.isDone():
                    faceId = fvIt.faceId()
                    fvId = fvIt.faceVertexId()
                    vtxId = fvIt.vertexId()
                    for idx in xrange(lenSel):
                        if faceId == faceIds[idx] and fvId == fvIds[idx] and vtxId == vtxIds[idx] and selDag == selDagPath:
                            ratioRaw = None
                            ratio = None
                            fvPos = fvIt.position(space)
                            if axis == 1:
                                ratioRaw = (
                                    (fvPos[0] - objectBoundsXmin) /
                                    (objectBoundsXmax - objectBoundsXmin))
                            elif axis == 2:
                                ratioRaw = (
                                    (fvPos[1] - objectBoundsYmin) /
                                    (objectBoundsYmax - objectBoundsYmin))
                            elif axis == 3:
                                ratioRaw = (
                                    (fvPos[2] - objectBoundsZmin) /
                                    (objectBoundsZmax - objectBoundsZmin))
                            ratio = max(min(ratioRaw, 1), 0)
                            outColor = maya.cmds.colorAtPoint(
                                'SXRamp', o='RGB', u=(ratio), v=(ratio))
                            outAlpha = maya.cmds.colorAtPoint(
                                'SXAlphaRamp', o='A', u=(ratio), v=(ratio))
                            if outAlpha[0] > 0:
                                fvColors[idx].r = outColor[0]
                                fvColors[idx].g = outColor[1]
                                fvColors[idx].b = outColor[2]
                            else:
                                fvColors[idx].r = outAlpha[0]
                                fvColors[idx].g = outAlpha[0]
                                fvColors[idx].b = outAlpha[0]
                            fvColors[idx].a = outAlpha[0]

                            continue
                    fvIt.next()
            else:
                fvIt = OM.MItMeshFaceVertex(selDagPath)

                k = 0
                while not fvIt.isDone():
                    ratioRaw = None
                    ratio = None
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()
                    fvPos = fvIt.position(space)
                    if axis == 1:
                        ratioRaw = (
                            (fvPos[0] - objectBoundsXmin) /
                            (objectBoundsXmax - objectBoundsXmin))
                    elif axis == 2:
                        ratioRaw = (
                            (fvPos[1] - objectBoundsYmin) /
                            (objectBoundsYmax - objectBoundsYmin))
                    elif axis == 3:
                        ratioRaw = (
                            (fvPos[2] - objectBoundsZmin) /
                            (objectBoundsZmax - objectBoundsZmin))
                    ratio = max(min(ratioRaw, 1), 0)
                    outColor = maya.cmds.colorAtPoint(
                        'SXRamp', o='RGB', u=(ratio), v=(ratio))
                    outAlpha = maya.cmds.colorAtPoint(
                        'SXAlphaRamp', o='A', u=(ratio), v=(ratio))
                    if outAlpha[0] > 0:
                        fvColors[k].r = outColor[0]
                        fvColors[k].g = outColor[1]
                        fvColors[k].b = outColor[2]
                    else:
                        fvColors[k].r = outAlpha[0]
                        fvColors[k].g = outAlpha[0]
                        fvColors[k].b = outAlpha[0]
                    fvColors[k].a = outAlpha[0]
                    k += 1
                    fvIt.next()

            MFnMesh.setFaceVertexColors(fvColors, faceIds, vtxIds, mod, colorRep)
            mod.doIt()
            selectionIter.next()

        maya.cmds.select(selectionCache)
        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()

    def colorFill(self, overwriteAlpha=False):
        layer = sxglobals.layers.getSelectedLayer()
        fillColor = OM.MColor()
        mod = OM.MDGModifier()
        colorRep = OM.MFnMesh.kRGBA
        fillColor.r = sxglobals.settings.currentColor[0]
        fillColor.g = sxglobals.settings.currentColor[1]
        fillColor.b = sxglobals.settings.currentColor[2]
        fillColor.a = 1.0

        # Build face vert lists for the full meshes of the objects with component selections
        selectionList = OM.MSelectionList()
        for sl in sxglobals.settings.selectionArray:
            selectionList.add(sl)
        selDagPath = OM.MDagPath()
        selectionIter = OM.MItSelectionList(selectionList)

        while not selectionIter.isDone():
            selDagPath = selectionIter.getDagPath()
            MFnMesh = OM.MFnMesh(selDagPath)

            fvColors = OM.MColorArray()
            fvColors = MFnMesh.getFaceVertexColors(colorSet=layer)

            vtxIds = OM.MIntArray()
            fvIds = OM.MIntArray()
            faceIds = OM.MIntArray()

            lenSel = len(fvColors)
            faceIds.setLength(lenSel)
            fvIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(selDagPath)

            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                fvIds[k] = fvIt.faceVertexId()
                vtxIds[k] = fvIt.vertexId()
                k += 1
                fvIt.next()

            if selectionIter.hasComponents():
                # Convert component selection to face verts, fill matching vert ids with color
                components = maya.cmds.ls(
                    maya.cmds.polyListComponentConversion(
                        sxglobals.settings.componentArray, tvf=True), fl=True)
                #maya.cmds.ConvertSelectionToVertexFaces()

                selection = OM.MSelectionList()
                for component in components:
                    selection.add(component)
                #selectionList = OM.MGlobal.getActiveSelectionList()

                selDag = OM.MDagPath()
                fVert = OM.MObject()

                # Match component selection with components of full mesh and modify fvColors array
                (selDag, fVert) = selectionIter.getComponent()
                MFnMesh = OM.MFnMesh(selDag)
                fvIt = OM.MItMeshFaceVertex(selDag, fVert)
                while not fvIt.isDone():
                    faceId = fvIt.faceId()
                    fvId = fvIt.faceVertexId()
                    vtxId = fvIt.vertexId()
                    for idx in xrange(lenSel):
                        if faceId == faceIds[idx] and fvId == fvIds[idx] and vtxId == vtxIds[idx] and selDag == selDagPath:
                            if (overwriteAlpha is True):
                                fvColors[idx] = fillColor
                            elif (overwriteAlpha is False) and (sxglobals.settings.layerAlphaMax == 0):
                                fvColors[idx] = fillColor
                            elif (overwriteAlpha is False) and (sxglobals.settings.layerAlphaMax != 0):
                                fvColors[idx].r = fillColor.r
                                fvColors[idx].g = fillColor.g
                                fvColors[idx].b = fillColor.b
                            else:
                                fvColors[idx] = fillColor
                            continue
                    fvIt.next()
            else:
                if (overwriteAlpha is True):
                    fvColors = [fillColor] * lenSel
                elif (overwriteAlpha is False) and (sxglobals.settings.layerAlphaMax == 0):
                    fvColors = [fillColor] * lenSel
                elif (overwriteAlpha is False) and (sxglobals.settings.layerAlphaMax != 0):
                    for idx in xrange(lenSel):
                        fvColors[idx].r = fillColor.r
                        fvColors[idx].g = fillColor.g
                        fvColors[idx].b = fillColor.b
                else:
                    fvColors = [fillColor] * lenSel

            MFnMesh.setFaceVertexColors(fvColors, faceIds, vtxIds, mod, colorRep)
            mod.doIt()
            selectionIter.next()

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()

    def colorNoise(self, objects):
        for object in objects:
            mono = sxglobals.settings.tools['noiseMonochrome']
            color = sxglobals.settings.tools['noiseColor']
            value = max(color[0], color[1], color[2])
            layer = sxglobals.layers.getSelectedLayer()

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
                    vtxColors[i].r += random.uniform(-color[0], color[0])
                    vtxColors[i].g += random.uniform(-color[1], color[1])
                    vtxColors[i].b += random.uniform(-color[2], color[2])

                vtxIt.next()

            MFnMesh.setVertexColors(vtxColors, vtxIds)

    def remapRamp(self, objects):
        for object in objects:
            layer = sxglobals.layers.getSelectedLayer()

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
                luminance = ((fvCol.r +
                              fvCol.r +
                              fvCol.b +
                              fvCol.g +
                              fvCol.g +
                              fvCol.g) / 6)
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

            MFnMesh.setFaceVertexColors(
                layerColors, faceIds, vtxIds, mod, colorRep)

    def swapLayers(self, shapes):
        refLayers = sxglobals.layers.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        layerA = maya.cmds.textField('layersrc', query=True, text=True)
        layerB = maya.cmds.textField('layertgt', query=True, text=True)

        for shape in shapes:
            # selected = str(sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1])

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

                self.getLayerPaletteOpacity(
                    sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
                    sxglobals.layers.getSelectedLayer())
                sxglobals.layers.refreshLayerList()
                sxglobals.layers.refreshSelectedItem()
                maya.cmds.shaderfx(sfxnode='SXShader', update=True)
            else:
                print('SXTools Error: Invalid layers on ' + str(shape))

    def copyLayer(self, objects):
        refLayers = sxglobals.layers.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        layerA = maya.cmds.textField('layersrc', query=True, text=True)
        layerB = maya.cmds.textField('layertgt', query=True, text=True)

        if (layerA in refLayers) and (layerB in refLayers):
            for idx, obj in enumerate(objects):
                selected = str(sxglobals.settings.shapeArray[idx])
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

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def verifyShadingMode(self):
        if len(sxglobals.settings.shapeArray) > 0:
            object = sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1]
            mode = int(maya.cmds.getAttr(object + '.shadingMode') + 1)

            objectLabel = 'Selected Objects: ' + str(len(sxglobals.settings.objectArray))
            maya.cmds.frameLayout('layerFrame', edit=True, label=objectLabel)
            maya.cmds.radioButtonGrp('shadingButtons', edit=True, select=mode)
            return mode

    def setShadingMode(self, mode):
        for shape in sxglobals.settings.shapeArray:
            maya.cmds.setAttr(str(shape) + '.shadingMode', mode)
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    # check for non-safe history
    # and double shapes under one transform
    def checkHistory(self, objList):
        del sxglobals.settings.multiShapeArray[:]
        sxglobals.ui.history = False
        sxglobals.ui.multiShapes = False

        for obj in objList:
            if maya.cmds.attributeQuery('exportMesh', node=obj, exists=True):
                print('SX Tools: Deforming export mesh selected')
                return
            if '_skinned' in obj:
                print('SX Tools: Skinning Mesh Selected')
                return

            histList = maya.cmds.listHistory(obj)
            shapeList = maya.cmds.listRelatives(
                obj, shapes=True, fullPath=True)

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
                if 'exportsLayer' in str(hist):
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
                print('SX Tools: History found: ' + str(histList))
                sxglobals.ui.history = True

            if len(shapeList) > 1:
                print('SX Tools: Multiple shape nodes in ' + str(obj))
                sxglobals.ui.multiShapes = True
                for shape in shapeList:
                    if '|' in shape:
                        shapeShort = shape.rsplit('|', 1)[1]
                    if objName not in shapeShort:
                        sxglobals.settings.multiShapeArray.append(shape)

    # Called from a button the tool UI
    # that clears either the selected layer
    # or the selected components in a layer
    def clearSelector(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)
        if shift is True:
            sxglobals.layers.clearLayer(
                sxglobals.layers.sortLayers(sxglobals.settings.project['LayerData'].keys()),
                sxglobals.settings.shapeArray)
        elif shift is False:
            if len(sxglobals.settings.componentArray) > 0:
                sxglobals.layers.clearLayer(
                    [sxglobals.layers.getSelectedLayer(), ])
            else:
                sxglobals.layers.clearLayer(
                    [sxglobals.layers.getSelectedLayer(), ],
                    sxglobals.settings.shapeArray)

    def setLayerOpacity(self):
        alphaMax = sxglobals.settings.layerAlphaMax

        for shape in sxglobals.settings.shapeArray:
            layer = sxglobals.layers.getSelectedLayer()
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
                if ((alphaMax == 0) and
                    (testColor.r > 0 or
                     testColor.g > 0 or
                     testColor.b > 0)):
                    layerColorArray[k].a = sliderAlpha
                elif (testColor.a > 0 or
                      testColor.r > 0 or
                      testColor.g > 0 or
                      testColor.b > 0):
                        layerColorArray[k].a = (layerColorArray[k].a /
                                                alphaMax * sliderAlpha)
                k += 1
                fvIt.next()

            MFnMesh.setFaceVertexColors(layerColorArray, faceIds, vtxIds)

            if (str(layer) == 'layer1') and (sliderAlpha < 1):
                maya.cmds.setAttr(str(shape) + '.transparency', 1)
                if alphaMax == 1:
                    maya.cmds.shaderfx(
                        sfxnode='SXShader',
                        makeConnection=(
                            sxglobals.settings.nodeDict['transparencyComp'], 0,
                            sxglobals.settings.nodeDict['SXShader'], 0))
                maya.cmds.shaderfx(sfxnode='SXShader', update=True)
            elif (str(layer) == 'layer1') and (sliderAlpha == 1):
                maya.cmds.setAttr(str(shape) + '.transparency', 0)
                if alphaMax < 1:
                    maya.cmds.shaderfx(
                        sfxnode='SXShader',
                        breakConnection=(
                            sxglobals.settings.nodeDict['transparencyComp'], 0,
                            sxglobals.settings.nodeDict['SXShader'], 0))
                maya.cmds.shaderfx(sfxnode='SXShader', update=True)

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())

    def getLayerMask(self):
        maskList = []

        vertFaceList = maya.cmds.ls(
            maya.cmds.polyListComponentConversion(
                sxglobals.settings.shapeArray, tvf=True), fl=True)

        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift is True:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(
                   vertFace, query=True, a=True)[0] == 0:
                    maskList.append(vertFace)
        elif shift is False:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(
                   vertFace, query=True, a=True)[0] > 0:
                    maskList.append(vertFace)

        if len(maskList) == 0:
            print('SX Tools: No layer mask found')
            return sxglobals.settings.selectionArray

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
            maya.cmds.floatSlider(
                'layerOpacitySlider',
                edit=True,
                value=alphaMax)
            sxglobals.settings.layerAlphaMax = alphaMax

        for k in range(0, 8):
            maya.cmds.palettePort(
                'layerPalette',
                edit=True,
                rgb=(
                    k,
                    layerPaletteArray[k].r,
                    layerPaletteArray[k].g,
                    layerPaletteArray[k].b))
            maya.cmds.palettePort('layerPalette', edit=True, redraw=True)

        if 'layer' not in layer:
            if maya.cmds.text('layerOpacityLabel', exists=True):
                maya.cmds.text('layerOpacityLabel', edit=True, enable=False)
            if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
                maya.cmds.floatSlider(
                    'layerOpacitySlider',
                    edit=True,
                    enable=False)
            return
        else:
            if maya.cmds.text('layerOpacityLabel', exists=True):
                maya.cmds.text('layerOpacityLabel', edit=True, enable=True)
            if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
                maya.cmds.floatSlider(
                    'layerOpacitySlider',
                    edit=True,
                    enable=True)

    def setPaintColor(self, color):
        maya.cmds.colorSliderGrp(
            'sxApplyColor', edit=True, rgbValue=color)
        if maya.cmds.artAttrPaintVertexCtx(
                'artAttrColorPerVertexContext', exists=True):
            numChannels = maya.cmds.artAttrPaintVertexCtx(
                'artAttrColorPerVertexContext',
                query=True,
                paintNumChannels=True)
            if numChannels == 3:
                maya.cmds.artAttrPaintVertexCtx(
                    'artAttrColorPerVertexContext',
                    edit=True,
                    usepressure=False,
                    colorRGBValue=[
                        color[0],
                        color[1],
                        color[2]
                    ])
            elif numChannels == 4:
                maya.cmds.artAttrPaintVertexCtx(
                    'artAttrColorPerVertexContext',
                    edit=True,
                    usepressure=False,
                    colorRGBAValue=[
                        color[0],
                        color[1],
                        color[2], 1
                    ])

    def setApplyColor(self):
        sxglobals.settings.tools['recentPaletteIndex'] = maya.cmds.palettePort(
            'recentPalette', query=True, scc=True)
        sxglobals.settings.currentColor = maya.cmds.palettePort(
            'recentPalette', query=True, rgb=True)
        maya.cmds.colorSliderGrp(
            'sxApplyColor', edit=True, rgbValue=sxglobals.settings.currentColor)

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
                    rgb=(
                        k,
                        swapColorArray[k - 1][0],
                        swapColorArray[k - 1][1],
                        swapColorArray[k - 1][2]))

            maya.cmds.palettePort(
                'recentPalette',
                edit=True, scc=0)
            maya.cmds.palettePort(
                'recentPalette',
                edit=True,
                rgb=(
                    0,
                    addedColor[0],
                    addedColor[1],
                    addedColor[2]))
            maya.cmds.palettePort(
                'recentPalette',
                edit=True, redraw=True)
        else:
            idx = swapColorArray.index(addedColor)
            maya.cmds.palettePort(
                'recentPalette',
                edit=True, scc=idx)

        self.storePalette(
            'recentPalette',
            sxglobals.settings.paletteDict,
            'SXToolsRecentPalette')

    def storePalette(self, paletteUI, category, preset):
        currentCell = maya.cmds.palettePort(
            paletteUI,
            query=True,
            scc=True)
        paletteLength = maya.cmds.palettePort(
            paletteUI,
            query=True,
            actualTotal=True)
        paletteArray = []
        for i in range(0, paletteLength):
            maya.cmds.palettePort(
                paletteUI,
                edit=True,
                scc=i)
            paletteArray.append(
                maya.cmds.palettePort(
                    paletteUI,
                    query=True,
                    rgb=True))

        if category == sxglobals.settings.paletteDict:
            category[preset] = paletteArray
        else:
            for i, cat in enumerate(sxglobals.settings.masterPaletteArray):
                if cat.keys()[0] == category:
                    sxglobals.settings.masterPaletteArray[i][
                        category][preset] = paletteArray

        maya.cmds.palettePort(
            paletteUI,
            edit=True,
            scc=currentCell)

    def getPalette(self, paletteUI, category, preset):
        if (category == sxglobals.settings.paletteDict):
            if (preset in category):
                presetColors = category[preset]
            else:
                return
        else:
            for i, cat in enumerate(sxglobals.settings.masterPaletteArray):
                if cat.keys()[0] == category:
                    presetColors = sxglobals.settings.masterPaletteArray[i][
                        category][preset]

        for idx, color in enumerate(presetColors):
            maya.cmds.palettePort(
                paletteUI,
                edit=True,
                rgb=(idx, color[0], color[1], color[2]))
        maya.cmds.palettePort(paletteUI, edit=True, redraw=True)

    def deleteCategory(self, category):
        for i, cat in enumerate(sxglobals.settings.masterPaletteArray):
            if cat.keys()[0] == category:
                sxglobals.settings.masterPaletteArray.pop(i)
        sxglobals.settings.tools['categoryPreset'] = None

    def deletePalette(self, category, preset):
        for i, cat in enumerate(sxglobals.settings.masterPaletteArray):
            if cat.keys()[0] == category:
                sxglobals.settings.masterPaletteArray[i][category].pop(preset)

    def saveMasterCategory(self):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift is True:
            category = maya.cmds.optionMenu(
                'masterCategories',
                query=True,
                value=True)
            if category is not None:
                self.deleteCategory(category)
                maya.cmds.deleteUI(category)
                maya.cmds.deleteUI(category+'Option')
                sxglobals.settings.savePalettes()
            else:
                print('SX Tools Error: No category to delete!')

        elif shift is False:
            itemList = maya.cmds.optionMenu(
                'masterCategories',
                query=True,
                ils=True)
            category = maya.cmds.textField(
                'saveCategoryName', query=True, text=True).replace(' ', '_')
            if ((len(category) > 0) and
               ((itemList is None) or (category not in itemList))):
                categoryDict = {}
                categoryDict[category] = {}
                sxglobals.settings.masterPaletteArray.append(categoryDict)
                maya.cmds.menuItem(
                    category,
                    label=category,
                    parent='masterCategories')
                itemList = maya.cmds.optionMenu(
                    'masterCategories',
                    query=True,
                    ils=True)
                idx = itemList.index(category) + 1
                sxglobals.settings.tools['categoryPreset'] = idx
                maya.cmds.optionMenu(
                    'masterCategories',
                    edit=True,
                    select=idx)
                sxglobals.settings.savePalettes()
                sxglobals.core.updateSXTools()
            else:
                print('SX Tools Error: Invalid preset name!')

    def paletteButtonManager(self, category, preset):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift is True:
            self.deletePalette(category, preset)
            maya.cmds.deleteUI(category+preset)
            sxglobals.settings.savePalettes()
        elif shift is False:
            self.setMasterPalette(category, preset)
            self.applyMasterPalette(sxglobals.settings.objectArray)

    def saveMasterPalette(self):
        category = maya.cmds.optionMenu(
            'masterCategories',
            query=True,
            value=True)
        preset = maya.cmds.textField(
            'savePaletteName', query=True, text=True).replace(' ', '_')

        if len(preset) > 0:
            self.storePalette(
                'masterPalette',
                category,
                preset)
            sxglobals.settings.savePalettes()
        else:
            print('SX Tools Error: Invalid preset name!')

    def setMasterPalette(self, category, preset):
        self.getPalette(
            'masterPalette',
            category,
            preset)
        self.storePalette(
            'masterPalette',
            sxglobals.settings.paletteDict,
            'SXToolsMasterPalette')

    def checkTarget(self, targets, index):
        refLayers = sxglobals.layers.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        splitList = []
        targetList = []
        splitList = targets.split(',')
        for item in splitList:
            targetList.append(item.strip())

        if set(targetList).issubset(refLayers) is False:
            print('SX Tools Error: Invalid layer target!')
            maya.cmds.textField(
                'masterTarget'+str(index),
                edit=True,
                text=''.join(sxglobals.settings.project['paletteTarget'+str(index)]))
            return
        sxglobals.settings.project['paletteTarget'+str(index)] = targetList
        sxglobals.settings.savePreferences()

    def gradientToolManager(self, mode):
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
            name = maya.cmds.textField(
                'presetName', query=True, text=True).replace(' ', '_')
            if len(name) > 0:
                maya.cmds.nodePreset(save=('SXRamp', name))
            elif len(name) == 0:
                print('SXTools: Invalid preset name!')
        elif mode == 5:
            self.calculateCurvature(sxglobals.settings.objectArray)
        elif mode == 4:
            self.remapRamp(sxglobals.settings.objectArray)
        else:
            self.gradientFill(mode)

    def clearRamp(self, rampName):
        indexList = maya.cmds.getAttr(
            rampName + '.colorEntryList', multiIndices=True)
        for index in indexList:
            index = str(index).split('L')[-1]
            maya.cmds.removeMultiInstance(
                rampName + '.colorEntryList[' + index + ']')

    def setLayerBlendMode(self):
        mode = maya.cmds.optionMenu(
            'layerBlendModes',
            query=True,
            select=True) - 1
        attr = '.' + sxglobals.layers.getSelectedLayer() + 'BlendMode'
        for shape in sxglobals.settings.shapeArray:
            maya.cmds.setAttr(str(shape) + attr, mode)
            maya.cmds.shaderfx(sfxnode='SXShader', update=True)
        sxglobals.layers.getSelectedLayer()

    def swapLayerSets(self, objects, targetSet, offset=False):
        if offset is True:
            targetSet -= 1
        if (targetSet > sxglobals.layers.getLayerSet(objects[0])) or (targetSet < 0):
            print('SX Tools Error: Selected layer set does not exist!')
            return
        refLayers = sxglobals.layers.sortLayers(sxglobals.settings.project['LayerData'].keys())

        for object in objects:
            attr = '.activeLayerSet'
            currentMode = int(maya.cmds.getAttr(object + attr))
            objLayers = maya.cmds.polyColorSet(
                object,
                query=True,
                allColorSets=True)
            for layer in refLayers:
                if (str(layer)+'_var'+str(currentMode)) in objLayers:
                    maya.cmds.polyColorSet(
                        object,
                        delete=True,
                        colorSet=(str(layer)+'_var'+str(currentMode)))
                maya.cmds.polyColorSet(
                    object,
                    rename=True,
                    colorSet=layer,
                    newColorSet=(str(layer)+'_var'+str(currentMode)))
                maya.cmds.polyColorSet(
                    object,
                    rename=True,
                    colorSet=(
                        str(layer)+'_var'+str(targetSet)),
                    newColorSet=layer)
            maya.cmds.setAttr(object + attr, targetSet)

        maya.cmds.polyColorSet(
            objects,
            currentColorSet=True,
            colorSet='layer1')

        self.getLayerPaletteOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.layers.getSelectedLayer())
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def removeLayerSet(self, objects):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift is True:
            sxglobals.layers.clearLayerSets()
        else:
            refLayers = sxglobals.layers.sortLayers(sxglobals.settings.project['LayerData'].keys())
            actives = []
            numSets = []
            active = None
            num = None
            target = None
            previous = None
            for object in objects:
                actives.append(
                    int(maya.cmds.getAttr(object + '.activeLayerSet')))
                numSets.append(
                    int(maya.cmds.getAttr(object + '.numLayerSets')))
            if ((all(active == actives[0] for active in actives) is False) or
               (all(num == numSets[0] for num in numSets) is False)):
                print('SX Tools Error: Selection with mismatching Layer Sets!')
                return

            active = actives[0]
            num = numSets[0]
            if (active == 0) and (num == 0):
                print('SX Tools Error: Objects must have one Layer Set')
                return

            if (active == 0):
                target = 1
                previous = 0
            else:
                target = 0
                previous = active

            self.swapLayerSets(objects, target)

            for layer in refLayers:
                maya.cmds.polyColorSet(
                    objects,
                    delete=True,
                    colorSet=(str(layer)+'_var'+str(previous)))

            attr = '.numLayerSets'
            for object in objects:
                maya.cmds.setAttr(
                    object + attr, (maya.cmds.getAttr(object + attr) - 1))

            objLayers = maya.cmds.polyColorSet(
                objects[0],
                query=True,
                allColorSets=True)

            if previous == 0:
                for object in objects:
                    maya.cmds.setAttr(object + '.activeLayerSet', 0)
                for layer in objLayers:
                    if '_var' in layer:
                        currentIndex = int(layer[-1])
                        newSet = str(layer).split(
                            '_var')[0]+'_var'+str(currentIndex-1)
                        maya.cmds.polyColorSet(
                            objects,
                            rename=True,
                            colorSet=layer,
                            newColorSet=newSet)
            else:
                for layer in objLayers:
                    if ('_var' in layer) and (int(layer[-1]) > previous):
                        currentIndex = int(layer[-1])
                        newSet = str(layer).split(
                            '_var')[0]+'_var'+str(currentIndex-1)
                        maya.cmds.polyColorSet(
                            objects,
                            rename=True,
                            colorSet=layer,
                            newColorSet=newSet)

    def copyFaceVertexColors(self, objects, sourceLayers, targetLayers):
        for object in objects:
            selectionList = OM.MSelectionList()
            selectionList.add(object)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerAColors = OM.MColorArray()
            layerAColors = MFnMesh.getFaceVertexColors(colorSet='layer1')

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

            for source, target in zip(sourceLayers, targetLayers):
                maya.cmds.polyColorSet(
                    object,
                    currentColorSet=True,
                    colorSet=target)
                layerAColors = MFnMesh.getFaceVertexColors(colorSet=source)
                MFnMesh.setFaceVertexColors(layerAColors, faceIds, vtxIds)

    def createSkinMesh(self, objects):
        skinMeshArray = []
        for obj in objects:
            skinMesh = maya.cmds.duplicate(
                obj, renameChildren=True, name=obj+'_skinned')
            skinShape = maya.cmds.listRelatives(
                skinMesh,
                type='mesh',
                allDescendents=True,
                fullPath=True)
            sxglobals.export.stripPrimVars(skinShape)
            maya.cmds.setAttr(
                skinMesh[0] + '.translate',
                0, 0, 0, type='double3')
            maya.cmds.makeIdentity(
                skinMesh, apply=True, t=1, r=1, s=1, n=0, pn=1)
            if maya.cmds.attributeQuery('staticVertexColors', node=skinMesh[0], exists=True):
                maya.cmds.deleteAttr(skinMesh[0]+'.staticVertexColors')
            if maya.cmds.attributeQuery('subdivisionLevel', node=skinMesh[0], exists=True):
                maya.cmds.deleteAttr(skinMesh[0]+'.subdivisionLevel')
            maya.cmds.addAttr(skinMesh,
                ln='skinnedMesh',
                at='bool', dv=True)
            colSets = maya.cmds.polyColorSet(
                skinMesh,
                query=True, allColorSets=True)
            for set in colSets:
                if str(set) != 'layer1':
                    maya.cmds.polyColorSet(
                        skinMesh,
                        delete=True, colorSet=str(set))
                else:
                    maya.cmds.polyColorSet(
                        skinMesh,
                        currentColorSet=True,
                        colorSet='layer1')
                    maya.cmds.polyColorPerVertex(
                        skinMesh[0],
                        r=0.5,
                        g=0.5,
                        b=0.5,
                        a=1,
                        representation=4,
                        cdo=True)
            name = maya.cmds.getAttr(
                skinMesh[0] + '.uvSet[0].uvSetName')
            maya.cmds.polyUVSet(
                skinMesh,
                rename=True,
                uvSet=name, newUVSet='UV0')
            maya.cmds.polyUVSet(
                skinMesh,
                currentUVSet=True, uvSet='UV0')
            maya.cmds.polyAutoProjection(
                skinMesh,
                lm=0, pb=0, ibd=1, cm=0, l=3,
                sc=1, o=0, p=6, ps=0.2, ws=0)
            maya.cmds.setAttr(skinMesh[0] + '.outlinerColor', 0.75,0.25,1)
            maya.cmds.setAttr(skinMesh[0] + '.useOutlinerColor', True)
            skinMeshArray.append(skinMesh[0])

        maya.cmds.delete(skinMeshArray, ch=True)
        maya.cmds.sets(skinMeshArray, e=True, forceElement='initialShadingGroup')
        maya.cmds.editDisplayLayerMembers(
            'skinMeshLayer',
            skinMeshArray)
        maya.cmds.setAttr('exportsLayer.visibility', 0)
        maya.cmds.setAttr('skinMeshLayer.visibility', 1)
        maya.cmds.setAttr('assetsLayer.visibility', 0)
        maya.cmds.editDisplayLayerGlobals(cdl='skinMeshLayer')
        # hacky hack to refresh the layer editor
        maya.cmds.delete(maya.cmds.createDisplayLayer(empty=True))

    def checkSkinMesh(self, objects):
        if len(sxglobals.settings.objectArray) > 0:
            for obj in objects:
                if maya.cmds.attributeQuery('skinnedMesh', node=obj, exists=True):
                    return True
            return False
        else:
            return False

    def setExportFlags(self, objects, flag):
        for obj in objects:
            maya.cmds.setAttr(obj+'.staticVertexColors', flag)

    def setSubdivisionFlag(self, objects, flag):
        if flag > 0:
            maya.cmds.setAttr('sxCrease1.creaseLevel', flag*.25)
            maya.cmds.setAttr('sxCrease2.creaseLevel', flag*.5)
            maya.cmds.setAttr('sxCrease3.creaseLevel', flag*.75)
            maya.cmds.setAttr('sxCrease4.creaseLevel', flag)

        for obj in objects:
            maya.cmds.setAttr(obj+'.subdivisionLevel', flag)
            objShape = maya.cmds.listRelatives(obj, shapes=True)[0]
            maya.cmds.setAttr(objShape+'.smoothLevel', flag)
