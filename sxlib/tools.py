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
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift:
            self.clearCreases()
        else:
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
                        maya.cmds.sets(
                            sxglobals.settings.componentArray, remove=set)
                maya.cmds.polyCrease(sxglobals.settings.componentArray, op=1)
                maya.cmds.sets(
                    sxglobals.settings.componentArray, forceElement=setName)
            elif len(sxglobals.settings.componentArray) == 0:
                edgeList = maya.cmds.ls(maya.cmds.polyListComponentConversion(
                    sxglobals.settings.objectArray, te=True), fl=True)
                for set in creaseSets:
                    if maya.cmds.sets(edgeList, isMember=set):
                        maya.cmds.sets(edgeList, remove=set)
                maya.cmds.polyCrease(edgeList, op=1)
                maya.cmds.sets(
                    edgeList, forceElement=setName)
            else:
                edgeList = maya.cmds.polyListComponentConversion(
                    sxglobals.settings.componentArray, te=True)
                for set in creaseSets:
                    if maya.cmds.sets(edgeList, isMember=set):
                        maya.cmds.sets(edgeList, remove=set)
                maya.cmds.polyCrease(edgeList, op=1)
                maya.cmds.sets(
                    edgeList, forceElement=setName)

    def clearCreases(self):
        creaseSets = (
            'sxCrease0',
            'sxCrease1',
            'sxCrease2',
            'sxCrease3',
            'sxCrease4')
        edgeList = maya.cmds.ls(maya.cmds.polyListComponentConversion(
            sxglobals.settings.objectArray, te=True), fl=True)
        vertList = maya.cmds.ls(maya.cmds.polyListComponentConversion(
            sxglobals.settings.objectArray, tv=True), fl=True)
        for set in creaseSets:
            if maya.cmds.sets(edgeList, isMember=set):
                maya.cmds.sets(edgeList, remove=set)
            if maya.cmds.sets(vertList, isMember=set):
                maya.cmds.sets(vertList, remove=set)

        maya.cmds.polyCrease(sxglobals.settings.objectArray, op=2)
        maya.cmds.sets(edgeList, forceElement='sxCrease0')

    def assignToSubMeshSet(self, setName):
        subMeshSets = (
            'sxSubMesh0',
            'sxSubMesh1',
            'sxSubMesh2')
        if (maya.cmds.filterExpand(
                sxglobals.settings.componentArray, sm=34) is not None):
            for set in subMeshSets:
                if maya.cmds.sets(sxglobals.settings.componentArray, isMember=set):
                    maya.cmds.sets(
                        sxglobals.settings.componentArray, remove=set)
            maya.cmds.sets(
                sxglobals.settings.componentArray, forceElement=setName)
        else:
            print('SX Tools: Only polygon faces can be assigned to submesh sets')

    # Apply selected crease value to any convex or concave edge
    # beyond a user-adjusted threshold
    def curvatureSelect(self, objects):
        convexThreshold = maya.cmds.getAttr(
            'SXCreaseRamp.colorEntryList[2].position')
        concaveThreshold = maya.cmds.getAttr(
            'SXCreaseRamp.colorEntryList[1].position')

        objectList = objects[:]
        selection = OM.MSelectionList()
        selEdges = []
        curvArrays = []

        # self.clearCreases()

        # Generate curvature values per object
        for obj in objectList:
            selection.add(obj)
            curvArrays.append(
                self.calculateCurvature([obj, ],
                True,
                normalize=True))

        maya.cmds.select(clear=True)
        selIter = OM.MItSelectionList(selection)
        k = 0
        while not selIter.isDone():
            vtxValues = OM.MColorArray()
            dagPath = OM.MDagPath()
            lengthArray = []
            compDict = {}
            compDict['convexSet'] = OM.MSelectionList()
            compDict['concaveSet'] = OM.MSelectionList()
            item = OM.MObject()

            vtxValues = curvArrays[k][1]
            dagPath = curvArrays[k][0]

            vtxIter = OM.MItMeshVertex(dagPath)
            while not vtxIter.isDone():
                i = vtxIter.index()
                item = vtxIter.currentItem()

                # Assign convex verts to set
                if sxglobals.settings.tools['convex']:
                    if (vtxValues[i].r >= convexThreshold):
                        compDict['convexSet'].add((dagPath, item))
                        vtxIter.next()
                        continue

                # Assign concave verts to set
                if sxglobals.settings.tools['concave']:
                    if (vtxValues[i].r <= concaveThreshold):
                        compDict['concaveSet'].add((dagPath, item))
                        vtxIter.next()
                        continue

                vtxIter.next()

            for key in compDict:
                OM.MGlobal.setActiveSelectionList(compDict[key], listAdjustment=OM.MGlobal.kReplaceList)
                selList = maya.cmds.ls(
                    maya.cmds.polyListComponentConversion(
                        fv=True, te=True, internal=True),
                    fl=True)
                assignList = selList[:]
                # remove edges based on min length
                for sel in selList:
                    edgeVerts = maya.cmds.ls(
                        maya.cmds.polyListComponentConversion(
                            sel, fe=True, tv=True),
                        fl=True)
                    points = maya.cmds.xform(
                        edgeVerts, q=True, t=True, ws=True)
                    length = math.sqrt(
                        math.pow(points[0] - points[3], 2) +
                        math.pow(points[1] - points[4], 2) +
                        math.pow(points[2] - points[5], 2))
                    lengthArray.append(length)
                    if length < sxglobals.settings.tools['minCreaseLength']:
                        assignList.remove(sel)
                if len(assignList) > 0:
                    selEdges.extend(assignList)
            print('SX Tools:')
            print(objects[k] + ' min edge length:' + str(min(lengthArray)))
            print(objects[k] + ' max edge length:' + str(max(lengthArray)))
            k += 1
            selIter.next()

        maya.cmds.select(selEdges)

    def calculateCurvature(self, objects, returnColors=False, normalize=False):
        objCurvatures = []
        objColors = []
        objIds = []
        sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])

        for obj in objects:
            selectionList = OM.MSelectionList()
            selectionList.add(obj)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            vtxPoints = OM.MPointArray()
            vtxPoints = MFnMesh.getPoints(OM.MSpace.kWorld)
            numVtx = MFnMesh.numVertices

            vtxNormals = OM.MVectorArray()
            vtxColors = OM.MColorArray()
            vtxIds = OM.MIntArray()

            vtxCurvatures = []

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
                edges = OM.MVectorArray()
                edges.setLength(numConnected)
                edgeWeights = [None] * numConnected
                # normEdgeWeights = [None] * numConnected
                angles = [None] * numConnected

                for e in xrange(numConnected):
                    edges[e] = (vtxPoints[connectedVertices[e]] - vtxPoints[i])
                    edgeWeights[e] = edges[e].length()
                    angles[e] = math.acos(vtxNormals[i].normal() * edges[e].normal())

                # normalize edge weights against max
                # normEdgeWeights = [float(i)/max(edgeWeights) for i in edgeWeights]

                vtxCurvature = 0.0
                for e in xrange(numConnected):
                    curvature = (angles[e] / math.pi - 0.5)  #  * or / float(normEdgeWeights[e])
                    vtxCurvature += curvature

                vtxCurvature = (vtxCurvature / float(numConnected))  # + 0.5
                if vtxCurvature > 1.0:
                    vtxCurvature = 1.0

                vtxCurvatures.append(vtxCurvature)
                vtxIt.next()

            objCurvatures.append(vtxCurvatures)
            objColors.append(vtxColors)
            objIds.append(vtxIds)

        # Normalize convex and concave separately
        # to maximize artist ability to crease
        if normalize:
            #vtxCurvatures = [float(i)/max(vtxCurvatures) for i in vtxCurvatures]
            maxArray = []
            minArray = []
            for vtxCurvatures in objCurvatures:
                minArray.append(min(vtxCurvatures))
                maxArray.append(max(vtxCurvatures))
            minCurv = min(minArray)
            maxCurv = max(maxArray)

            for vtxCurvatures in objCurvatures:
                for k in xrange(len(vtxCurvatures)):
                    if vtxCurvatures[k] < 0:
                        vtxCurvatures[k] = (vtxCurvatures[k] / float(minCurv)) * -0.5 + 0.5
                    else:
                        vtxCurvatures[k] = (vtxCurvatures[k] / float(maxCurv)) * 0.5 + 0.5
        else:
            for vtxCurvatures in objCurvatures:
                for k in xrange(len(vtxCurvatures)):
                    vtxCurvatures[k] = (vtxCurvatures[k] + 0.5)

        for idx, obj in enumerate(objects):
            selectionList = OM.MSelectionList()
            selectionList.add(obj)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            if returnColors:
                for i in xrange(len(objCurvatures[idx])):
                    objColors[idx][i].r = objCurvatures[idx][i]
                    objColors[idx][i].g = objCurvatures[idx][i]
                    objColors[idx][i].b = objCurvatures[idx][i]
                    objColors[idx][i].a = 1.0

                return (nodeDagPath, objColors[idx])
            else:
                for i in xrange(len(objCurvatures[idx])):
                    outColor = maya.cmds.colorAtPoint(
                        'SXRamp', o='RGB', u=(0), v=(objCurvatures[idx][i]))
                    outAlpha = maya.cmds.colorAtPoint(
                        'SXAlphaRamp', o='A', u=(0), v=(objCurvatures[idx][i]))

                    objColors[idx][i].r = outColor[0]
                    objColors[idx][i].g = outColor[1]
                    objColors[idx][i].b = outColor[2]
                    objColors[idx][i].a = outAlpha[0]

                MFnMesh.setVertexColors(objColors[idx], objIds[idx])

    def rayRandomizer(self):
        u1 = random.uniform(0, 1)
        u2 = random.uniform(0, 1)
        r = math.sqrt(u1)
        theta = 2*math.pi*u2

        x = r * math.cos(theta)
        y = r * math.sin(theta)

        return OM.MVector(x, y, math.sqrt(max(0, 1 - u1)))

    def bakeOcclusion(self, rayCount=250, bias=0.000001, max=10.0, weighted=True, comboOffset=0.9):
        sxglobals.settings.localOcclusionDict.clear()
        sxglobals.settings.globalOcclusionDict.clear()
        bboxCoords = []
        newBboxCoords = []
        selectionCache = sxglobals.settings.selectionArray
        sxglobals.settings.bakeSet = sxglobals.settings.shapeArray
        contribution = 1.0/float(rayCount)

        if sxglobals.settings.project['LayerData']['occlusion'][5]:
            sxglobals.layers.setColorSet('occlusion')
            layer = 'occlusion'

        # track merged and separated meshes
        # that may have been parts of a combo mesh
        # by adding a temp colorset
        for bake in sxglobals.settings.bakeSet:
            setName = 'AO_'+str(bake)
            maya.cmds.polyColorSet(
                bake,
                create=True,
                clamped=True,
                representation='A',
                colorSet=setName)
            maya.cmds.polyColorSet(bake, currentColorSet=True, colorSet=setName)
            maya.cmds.polyColorPerVertex(bake, a=1.0, nun=True)
            maya.cmds.polyColorSet(bake, currentColorSet=True, colorSet=layer)

        # generate global pass combo mesh
        if len(sxglobals.settings.bakeSet) > 1:
            globalMesh = maya.cmds.polyUnite(
                maya.cmds.duplicate(sxglobals.settings.bakeSet, renameChildren=True),
                ch=False,
                name='comboOcclusionObject')
            maya.cmds.polyMoveFacet(
                globalMesh,
                lsx=comboOffset,
                lsy=comboOffset,
                lsz=comboOffset)
            if not sxglobals.settings.tools['bakeGroundPlane']:
                sxglobals.settings.bakeSet.append(globalMesh[0])
        else:
            globalMesh = maya.cmds.duplicate(
                sxglobals.settings.bakeSet[0],
                name='comboOcclusionObject')
            if not sxglobals.settings.tools['bakeGroundPlane']:
                sxglobals.settings.bakeSet.append(globalMesh[0])

        if sxglobals.settings.tools['bakeGroundPlane']:
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

            globalMesh = maya.cmds.polyUnite(
                ('comboOcclusionObject', 'sxGroundPlane'),
                ch=False,
                name='comboOcclusionObject')
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
                    sampleRays[e] = OM.MFloatVector(
                        hemiSphere[e].rotateBy(rotQuat))
                for e in xrange(rayCount):
                    result = MFnMesh.anyIntersection(
                        point,
                        sampleRays[e],
                        OM.MSpace.kWorld,
                        max,
                        False,
                        accelParams=accelGrid,
                        tolerance=0.001)
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
                if len(sxglobals.settings.bakeSet) > 1 or sxglobals.settings.tools['bakeGroundPlane']:
                    newObjs = maya.cmds.polySeparate(globalMesh, ch=False)
                    # merge objects that were combined before bake
                    allSets = maya.cmds.polyColorSet(
                        newObjs[0],
                        query=True,
                        allColorSets=True)
                    AOSets = []
                    for colorSet in allSets:
                        if 'AO_' in colorSet:
                            AOSets.append(colorSet)

                    AOList = OM.MSelectionList()
                    AODag = OM.MDagPath()
                    AOCol = OM.MColor()
                    for newObj in newObjs:
                        AOList.add(newObj)
                    comboParts = {}
                    for AOSet in AOSets:
                        comboParts[AOSet] = []

                    AOIter = OM.MItSelectionList(AOList)
                    while not AOIter.isDone():
                        idArray = OM.MColorArray()
                        AODag = AOIter.getDagPath()
                        AOMesh = OM.MFnMesh(AODag)
                        for AOSet in AOSets:
                            idArray = AOMesh.getVertexColors(AOSet)
                            AOCol = idArray[0]
                            if AOCol.a == 1:
                                comboParts[AOSet].append(str(AODag))
                                break
                        AOIter.next()
                    for key in comboParts:
                        if len(comboParts[key]) > 1:
                            newCombo = maya.cmds.polyUnite(comboParts[key])
                            maya.cmds.parent(newCombo[0], globalMesh[0])
                            newObjs.append(newCombo[0])
                            for item in comboParts[key]:
                                newObjs.remove(item)
                else:
                    newObjs = (globalMesh[0], )
                for newObj in newObjs:
                    bbx = maya.cmds.exactWorldBoundingBox(newObj)
                    if sxglobals.settings.tools['bakeGroundPlane']:
                        # ignore groundplane
                        if (math.fabs(bbx[3] - bbx[0]) == sxglobals.settings.tools['bakeGroundScale']) and (bbx[1] - bbx[4]) == 0:
                            continue
                    bbSize = math.fabs(
                        (bbx[3]-bbx[0]) *
                        (bbx[4]-bbx[1]) *
                        (bbx[5]-bbx[3]))
                    bbId = (
                        bbx[0] + 10 * bbx[1] + 100 * bbx[2] +
                        bbx[3] + 10 * bbx[4] + 100 * bbx[5])
                    newBboxCoords.append(
                        (bbId, bbSize, bbx[0], bbx[1], bbx[2], newObj))

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
                bbSize = math.fabs(
                    (bbx[3] - bbx[0]) *
                    (bbx[4] - bbx[1]) *
                    (bbx[5]-bbx[3]))
                bbId = (
                    bbx[0] + 10 * bbx[1] + 100 * bbx[2] +
                    bbx[3] + 10 * bbx[4] + 100 * bbx[5])
                bboxCoords.append(
                    (bbId, bbSize, bbx[0], bbx[1], bbx[2], bake))

        # remove redundant tracker colorsets
        for bake in sxglobals.settings.bakeSet:
            objSets = maya.cmds.polyColorSet(
                bake,
                query=True,
                allColorSets=True)
            for AOSet in AOSets:
                if AOSet in objSets:
                    maya.cmds.polyColorSet(
                        bake,
                        delete=True,
                        colorSet=AOSet)

        maya.cmds.select(selectionCache)

    def bakeOcclusionMR(self):
        bbox = []
        sxglobals.settings.bakeSet = sxglobals.settings.shapeArray

        if sxglobals.settings.project['LayerData']['occlusion'][5]:
            sxglobals.layers.setColorSet('occlusion')

        if sxglobals.settings.tools['bakeGroundPlane']:
            maya.cmds.polyPlane(
                name='sxGroundPlane',
                w=sxglobals.settings.tools['bakeGroundScale'],
                h=sxglobals.settings.tools['bakeGroundScale'],
                sx=1, sy=1, ax=(0, 1, 0), cuv=2, ch=0)
            maya.cmds.select(sxglobals.settings.bakeSet)
            sxglobals.core.selectionManager()

        if not maya.cmds.objExists('sxVertexBakeSet'):
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

        if sxglobals.settings.tools['bakeTogether']:
            if sxglobals.settings.tools['bakeGroundPlane']:
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
                if sxglobals.settings.tools['bakeGroundPlane']:
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

        if sxglobals.settings.tools['bakeGroundPlane']:
            maya.cmds.delete('sxGroundPlane')

        maya.cmds.select(sxglobals.settings.bakeSet)

    def bakeBlendOcclusion(self):
        startTimeOcc = maya.cmds.timerX()
        self.bakeOcclusion(
            sxglobals.settings.tools['rayCount'],
            sxglobals.settings.tools['bias'],
            sxglobals.settings.tools['maxDistance'],
            True,
            sxglobals.settings.tools['comboOffset'])
        sxglobals.settings.tools['blendSlider'] = 0.5
        self.blendOcclusion()
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Occlusion baking duration ' + str(totalTime))

    def bakeBlendOcclusionMR(self):
        startTimeOcc = maya.cmds.timerX()
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

        sxglobals.settings.tools['blendSlider'] = 0.5
        self.blendOcclusion()
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Occlusion baking duration ' + str(totalTime))

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

        sxglobals.layers.getLayerPaletteAndOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.settings.tools['selectedLayer'])

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

            if not applyAlpha:
                if 1 <= color[3] > 0:
                    maya.cmds.polyColorPerVertex(
                        component,
                        r=color[0] / float(color[3]),
                        g=color[1] / float(color[3]),
                        b=color[2] / float(color[3]),
                        a=1)
                else:
                    maya.cmds.polyColorPerVertex(
                        component, r=color[0], g=color[1], b=color[2], a=1)
            else:
                if 1 <= color[3] > 0:
                    maya.cmds.polyColorPerVertex(
                        component,
                        r=color[0] / float(color[3]),
                        g=color[1] / float(color[3]),
                        b=color[2] / float(color[3]),
                        a=color[3])
                else:
                    maya.cmds.polyColorPerVertex(
                        component,
                        r=color[0],
                        g=color[1],
                        b=color[2],
                        a=color[3])

        sxglobals.layers.refreshLayerList()
        sxglobals.layers.compositeLayers()

    def openSXPaintTool(self):
        if sxglobals.settings.tools['compositor'] == 1:
            sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])
            maya.mel.eval('PaintVertexColorTool;')
            maya.cmds.artAttrPaintVertexCtx(
                'artAttrColorPerVertexContext',
                edit=True,
                usepressure=False,
                paintNumChannels=4,
                paintRGBA=True,
                paintVertexFace=False)
            maya.cmds.toolPropertyWindow(inMainWindow=True)
            maya.cmds.setToolTo('artAttrColorPerVertexContext')

        elif sxglobals.settings.tools['compositor'] == 2:
            sxglobals.settings.tools['currentTool'] = 'SXPaint'
            sxglobals.settings.tools['compositeEnabled'] = False
            sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])
            maya.mel.eval('PaintVertexColorTool;')
            maya.cmds.artAttrPaintVertexCtx(
                'artAttrColorPerVertexContext',
                edit=True,
                usepressure=False,
                paintNumChannels=4,
                paintRGBA=True,
                paintVertexFace=False)
            maya.cmds.toolPropertyWindow(inMainWindow=True)
            maya.cmds.setToolTo('artAttrColorPerVertexContext')
            maya.cmds.radioButtonGrp(
                'shadingButtons',
                edit = True,
                select=2)
            self.setShadingMode(1)
            maya.cmds.polyOptions(
                activeObjects=True,
                colorMaterialChannel='none',
                colorShadedDisplay=True)
            maya.cmds.modelEditor(
                'modelPanel4',
                edit=True,
                useDefaultMaterial=False,
                displayLights='all',
                lights=True,
                displayTextures=True)

    def applyMasterPalette(self, objects):
        startTimeOcc = maya.cmds.timerX()

        selectionList = OM.MSelectionList()
        for obj in objects:
            selectionList.add(obj)
        selDagPath = OM.MDagPath()
        fvColors = OM.MColorArray()
        vtxIds = OM.MIntArray()
        fvIds = OM.MIntArray()
        faceIds = OM.MIntArray()
        fillColor = OM.MColor()
        mod = OM.MDGModifier()
        colorRep = OM.MFnMesh.kRGBA

        for i in xrange(1, 6):
            targetLayers = sxglobals.settings.project['paletteTarget'+str(i)]
            maya.cmds.palettePort('masterPalette', edit=True, scc=i-1)
            fillColor.r = maya.cmds.palettePort(
                'masterPalette', query=True, rgb=True)[0]
            fillColor.g = maya.cmds.palettePort(
                'masterPalette', query=True, rgb=True)[1]
            fillColor.b = maya.cmds.palettePort(
                'masterPalette', query=True, rgb=True)[2]

            for layer in targetLayers:
                maya.cmds.polyColorSet(
                    objects,
                    currentColorSet=True,
                    colorSet=layer)

                selectionIter = OM.MItSelectionList(selectionList)
                while not selectionIter.isDone():
                    selDagPath = selectionIter.getDagPath()
                    mesh = OM.MFnMesh(selDagPath)
                    fvColors.clear()
                    fvColors = mesh.getFaceVertexColors(colorSet=layer)
                    selLen = len(fvColors)
                    vtxIds.setLength(selLen)
                    fvIds.setLength(selLen)
                    faceIds.setLength(selLen)

                    meshIter = OM.MItMeshFaceVertex(selDagPath)
                    j = 0
                    while not meshIter.isDone():
                        vtxIds[j] = meshIter.vertexId()
                        faceIds[j] = meshIter.faceId()
                        fvIds[j] = meshIter.faceVertexId()

                        if fvColors[j].a == 0 and layer != 'layer1':
                            fvColors[j].r = 0.0
                            fvColors[j].g = 0.0
                            fvColors[j].b = 0.0
                        else:
                            fvColors[j].r = fillColor.r
                            fvColors[j].g = fillColor.g
                            fvColors[j].b = fillColor.b

                        j += 1
                        meshIter.next()

                    mesh.setFaceVertexColors(fvColors, faceIds, vtxIds, mod, colorRep)
                    selectionIter.next()

        mod.doIt()
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Apply Master Palette duration ' + str(totalTime))
        sxglobals.layers.refreshLayerList()
        sxglobals.layers.compositeLayers()

    def calculateBoundingBox(self, selection):
        selectionList = OM.MSelectionList()
        for sl in selection:
            selectionList.add(sl)

        selDagPath = OM.MDagPath()
        fVert = OM.MObject()
        compDagPath = OM.MDagPath()
        space = OM.MSpace.kWorld

        xmin = None
        xmax = None
        ymin = None
        ymax = None
        zmin = None
        zmax = None

        selectionIter = OM.MItSelectionList(selectionList)
        while not selectionIter.isDone():
            # Gather full mesh data to compare selection against
            selDagPath = selectionIter.getDagPath()

            if selectionIter.hasComponents():
                (compDagPath, fVert) = selectionIter.getComponent()
                fvIt = OM.MItMeshFaceVertex(selDagPath, fVert)
                k = 0
                while not fvIt.isDone():
                    fvPos = fvIt.position(space)
                    if k == 0:
                        if not xmin:
                            xmin = fvPos[0]
                        if not xmax:
                            xmax = fvPos[0]
                        if not ymin:
                            ymin = fvPos[1]
                        if not ymax:
                            ymax = fvPos[1]
                        if not zmin:
                            zmin = fvPos[2]
                        if not zmax:
                            zmax = fvPos[2]
                    else:
                        if fvPos[0] < xmin:
                            xmin = fvPos[0]
                        elif fvPos[0] > xmax:
                            xmax = fvPos[0]

                        if fvPos[1] < ymin:
                            ymin = fvPos[1]
                        elif fvPos[1] > ymax:
                            ymax = fvPos[1]

                        if fvPos[2] < zmin:
                            zmin = fvPos[2]
                        elif fvPos[2] > zmax:
                            zmax = fvPos[2]
                    k += 1
                    fvIt.next()
            else:
                fvIt = OM.MItMeshFaceVertex(selDagPath)
                k = 0
                while not fvIt.isDone():
                    fvPos = fvIt.position(space)
                    if k == 0:
                        if not xmin:
                            xmin = fvPos[0]
                        if not xmax:
                            xmax = fvPos[0]
                        if not ymin:
                            ymin = fvPos[1]
                        if not ymax:
                            ymax = fvPos[1]
                        if not zmin:
                            zmin = fvPos[2]
                        if not zmax:
                            zmax = fvPos[2]
                    else:
                        if fvPos[0] < xmin:
                            xmin = fvPos[0]
                        elif fvPos[0] > xmax:
                            xmax = fvPos[0]

                        if fvPos[1] < ymin:
                            ymin = fvPos[1]
                        elif fvPos[1] > ymax:
                            ymax = fvPos[1]

                        if fvPos[2] < zmin:
                            zmin = fvPos[2]
                        elif fvPos[2] > zmax:
                            zmax = fvPos[2]
                    k += 1
                    fvIt.next()

            selectionIter.next()
        return ((xmin,xmax), (ymin,ymax), (zmin,zmax))

    def gradientFill(self, axis):
        startTimeOcc = maya.cmds.timerX()
        layer = sxglobals.settings.tools['selectedLayer']
        space = OM.MSpace.kWorld
        mod = OM.MDGModifier()
        colorRep = OM.MFnMesh.kRGBA

        sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])

        if len(sxglobals.settings.componentArray) > 0:
            # Convert component selection to face vertices,
            # fill position-matching verts with color
            selection = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(
                    sxglobals.settings.selectionArray, tvf=True), fl=True)
        else:
            selection = sxglobals.settings.shapeArray

        objectBounds = self.calculateBoundingBox(selection)
        xmin = objectBounds[0][0]
        xmax = objectBounds[0][1]
        ymin = objectBounds[1][0]
        ymax = objectBounds[1][1]
        zmin = objectBounds[2][0]
        zmax = objectBounds[2][1]

        selectionList = OM.MSelectionList()
        for sl in selection:
            selectionList.add(sl)

        selDagPath = OM.MDagPath()
        fVert = OM.MObject()
        fvColors = OM.MColorArray()
        vtxIds = OM.MIntArray()
        fvIds = OM.MIntArray()
        faceIds = OM.MIntArray()
        compDagPath = OM.MDagPath()

        selectionIter = OM.MItSelectionList(selectionList)
        while not selectionIter.isDone():
            # Gather full mesh data to compare selection against
            selDagPath = selectionIter.getDagPath()
            mesh = OM.MFnMesh(selDagPath)
            # fvColors.clear()
            fvColors = mesh.getFaceVertexColors(colorSet=layer)
            selLen = len(fvColors)
            vtxIds.setLength(selLen)
            fvIds.setLength(selLen)
            faceIds.setLength(selLen)

            meshIter = OM.MItMeshFaceVertex(selDagPath)
            i = 0
            while not meshIter.isDone():
                vtxIds[i] = meshIter.vertexId()
                faceIds[i] = meshIter.faceId()
                fvIds[i] = meshIter.faceVertexId()
                i += 1
                meshIter.next()

            if selectionIter.hasComponents():
                (compDagPath, fVert) = selectionIter.getComponent()
                # Iterate through selected face vertices on current selection
                fvIt = OM.MItMeshFaceVertex(selDagPath, fVert)
                while not fvIt.isDone():
                    faceId = fvIt.faceId()
                    fvId = fvIt.faceVertexId()
                    vtxId = fvIt.vertexId()
                    for idx in xrange(selLen):
                        if (faceId == faceIds[idx] and
                           fvId == fvIds[idx] and
                           vtxId == vtxIds[idx] and
                           compDagPath == selDagPath):
                            ratioRaw = None
                            ratio = None
                            fvPos = fvIt.position(space)
                            if axis == 1:
                                ratioRaw = (
                                    (fvPos[0] - xmin) /
                                    float(xmax - xmin))
                            elif axis == 2:
                                ratioRaw = (
                                    (fvPos[1] - ymin) /
                                    float(ymax - ymin))
                            elif axis == 3:
                                ratioRaw = (
                                    (fvPos[2] - zmin) /
                                    float(zmax - zmin))
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
                            break
                    fvIt.next()
            else:
                fvIt = OM.MItMeshFaceVertex(selDagPath)
                k = 0
                while not fvIt.isDone():
                    ratioRaw = None
                    ratio = None
                    # faceIds[k] = fvIt.faceId()
                    # vtxIds[k] = fvIt.vertexId()
                    fvPos = fvIt.position(space)
                    if axis == 1:
                        ratioRaw = (
                            (fvPos[0] - xmin) /
                            float(xmax - xmin))
                    elif axis == 2:
                        ratioRaw = (
                            (fvPos[1] - ymin) /
                            float(ymax - ymin))
                    elif axis == 3:
                        ratioRaw = (
                            (fvPos[2] - zmin) /
                            float(zmax - zmin))
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

            # sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])
            mesh.setFaceVertexColors(fvColors, faceIds, vtxIds, mod, colorRep)
            selectionIter.next()

        mod.doIt()
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Gradient Fill duration ' + str(totalTime))

    def colorFill(self, overwriteAlpha=False):
        startTimeOcc = maya.cmds.timerX()
        layer = sxglobals.settings.tools['selectedLayer']
        sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])
        fillColor = OM.MColor()
        mod = OM.MDGModifier()
        colorRep = OM.MFnMesh.kRGBA
        fillColor.r = sxglobals.settings.currentColor[0]
        fillColor.g = sxglobals.settings.currentColor[1]
        fillColor.b = sxglobals.settings.currentColor[2]
        fillColor.a = 1.0

        if len(sxglobals.settings.componentArray) > 0:
            # Convert component selection to face vertices,
            # fill position-matching verts with color
            selection = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(
                    sxglobals.settings.selectionArray, tvf=True), fl=True)
        else:
            selection = sxglobals.settings.shapeArray

        selectionList = OM.MSelectionList()
        for sl in selection:
            selectionList.add(sl)
        selDagPath = OM.MDagPath()
        fVert = OM.MObject()
        fvColors = OM.MColorArray()
        vtxIds = OM.MIntArray()
        fvIds = OM.MIntArray()
        faceIds = OM.MIntArray()
        compDagPath = OM.MDagPath()

        selectionIter = OM.MItSelectionList(selectionList)
        while not selectionIter.isDone():
            # Gather full mesh data to compare selection against
            selDagPath = selectionIter.getDagPath()
            mesh = OM.MFnMesh(selDagPath)
            fvColors.clear()
            fvColors = mesh.getFaceVertexColors(colorSet=layer)
            selLen = len(fvColors)
            vtxIds.setLength(selLen)
            fvIds.setLength(selLen)
            faceIds.setLength(selLen)

            meshIter = OM.MItMeshFaceVertex(selDagPath)
            i = 0
            while not meshIter.isDone():
                vtxIds[i] = meshIter.vertexId()
                faceIds[i] = meshIter.faceId()
                fvIds[i] = meshIter.faceVertexId()
                i += 1
                meshIter.next()

            if selectionIter.hasComponents():
                (compDagPath, fVert) = selectionIter.getComponent()
                # Iterate through selected vertices on current selection
                fvIt = OM.MItMeshFaceVertex(selDagPath, fVert)
                while not fvIt.isDone():
                    faceId = fvIt.faceId()
                    fvId = fvIt.faceVertexId()
                    vtxId = fvIt.vertexId()
                    for idx in xrange(selLen):
                        if (faceId == faceIds[idx] and
                           fvId == fvIds[idx] and
                           vtxId == vtxIds[idx] and
                           compDagPath == selDagPath):
                            fvColors[idx] = fillColor
                            break
                    fvIt.next()
            else:
                if overwriteAlpha:
                    for idx in xrange(selLen):
                        fvColors[idx] = fillColor
                elif (not overwriteAlpha) and (sxglobals.settings.layerAlphaMax == 0):
                    for idx in xrange(selLen):
                        fvColors[idx] = fillColor
                elif (not overwriteAlpha) and (sxglobals.settings.layerAlphaMax != 0):
                    for idx in xrange(selLen):
                        fvColors[idx].r = fillColor.r
                        fvColors[idx].g = fillColor.g
                        fvColors[idx].b = fillColor.b
                else:
                    fvColors = [fillColor] * selLen

            mesh.setFaceVertexColors(fvColors, faceIds, vtxIds, mod, colorRep)
            mod.doIt()
            selectionIter.next()

        if sxglobals.settings.tools['noiseValue'] > 0:
            self.colorNoise()

        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Apply Color duration ' + str(totalTime))

        sxglobals.layers.refreshLayerList()
        sxglobals.layers.compositeLayers()

    def colorNoise(self):
        mono = sxglobals.settings.tools['noiseMonochrome']
        color = sxglobals.settings.currentColor
        value = sxglobals.settings.tools['noiseValue']
        layer = sxglobals.settings.tools['selectedLayer']

        if len(sxglobals.settings.componentArray) > 0:
            # Convert component selection to vertices,
            # fill position-matching verts with color
            selection = maya.cmds.polyListComponentConversion(
                    sxglobals.settings.selectionArray, tv=True, internal=True)
        else:
            selection = sxglobals.settings.shapeArray

        selectionList = OM.MSelectionList()
        for sl in selection:
            selectionList.add(sl)
        # selectionList = OM.MGlobal.getActiveSelectionList()
        selDagPath = OM.MDagPath()
        vert = OM.MObject()
        vtxColors = OM.MColorArray()
        vtxPosArray = OM.MPointArray()
        vtxIds = OM.MIntArray()
        compDagPath = OM.MDagPath()

        selectionIter = OM.MItSelectionList(selectionList)
        while not selectionIter.isDone():
            # Gather full mesh data to compare selection against
            selDagPath = selectionIter.getDagPath()
            mesh = OM.MFnMesh(selDagPath)
            vtxColors.clear()
            vtxColors = mesh.getVertexColors(colorSet=layer)
            selLen = len(vtxColors)
            vtxIds.setLength(selLen)
            vtxPosArray.setLength(selLen)
            changedCols = OM.MColorArray()
            changedIds = OM.MIntArray()

            meshIter = OM.MItMeshVertex(selDagPath)
            while not meshIter.isDone():
                i = meshIter.index()
                vtxIds[i] = meshIter.index()
                vtxPosArray[i] = meshIter.position()
                meshIter.next()

            if selectionIter.hasComponents():
                (compDagPath, vert) = selectionIter.getComponent()
                # Iterate through selected vertices on current selection
                vtxIt = OM.MItMeshVertex(selDagPath, vert)
                while not vtxIt.isDone():
                    vtxPos = vtxIt.position()
                    for idx in xrange(selLen):
                        if (vtxPos == vtxPosArray[idx] and
                           compDagPath == selDagPath):
                            if mono:
                                randomOffset = 1 - random.uniform(0, value)
                                vtxColors[idx].r *= randomOffset
                                vtxColors[idx].g *= randomOffset
                                vtxColors[idx].b *= randomOffset
                            else:
                                vtxColors[idx].r += random.uniform(-color[0]*value, color[0]*value)
                                vtxColors[idx].g += random.uniform(-color[1]*value, color[1]*value)
                                vtxColors[idx].b += random.uniform(-color[2]*value, color[2]*value)
                            changedCols.append(vtxColors[idx])
                            changedIds.append(idx)
                            break
                    vtxIt.next()
                mesh.setVertexColors(changedCols, changedIds)
                selectionIter.next()
            else:
                vtxColors = OM.MColorArray()
                vtxColors = mesh.getVertexColors(colorSet=layer)
                vtxIds = OM.MIntArray()

                lenSel = len(vtxColors)
                vtxIds.setLength(lenSel)

                vtxIt = OM.MItMeshVertex(selDagPath)
                while not vtxIt.isDone():
                    idx = vtxIt.index()
                    vtxIds[idx] = vtxIt.index()
                    if mono:
                        randomOffset = 1 - random.uniform(0, value)
                        vtxColors[idx].r *= randomOffset
                        vtxColors[idx].g *= randomOffset
                        vtxColors[idx].b *= randomOffset
                    else:
                        vtxColors[idx].r += random.uniform(-color[0]*value, color[0]*value)
                        vtxColors[idx].g += random.uniform(-color[1]*value, color[1]*value)
                        vtxColors[idx].b += random.uniform(-color[2]*value, color[2]*value)
                    vtxIt.next()
                mesh.setVertexColors(vtxColors, vtxIds)
                selectionIter.next()

    def remapRamp(self):
        startTimeOcc = maya.cmds.timerX()
        layer = sxglobals.settings.tools['selectedLayer']
        sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])
        fvCol = OM.MColor()

        if len(sxglobals.settings.componentArray) > 0:
            # Convert component selection to face vertices,
            # fill position-matching verts with color
            selection = maya.cmds.ls(
                maya.cmds.polyListComponentConversion(
                    sxglobals.settings.selectionArray, tvf=True), fl=True)
        else:
            selection = sxglobals.settings.shapeArray

        selectionList = OM.MSelectionList()
        for sl in selection:
            selectionList.add(sl)
        selDagPath = OM.MDagPath()
        fVert = OM.MObject()
        fvColors = OM.MColorArray()
        vtxIds = OM.MIntArray()
        fvIds = OM.MIntArray()
        faceIds = OM.MIntArray()
        compDagPath = OM.MDagPath()

        selectionIter = OM.MItSelectionList(selectionList)
        while not selectionIter.isDone():
            # Gather full mesh data to compare selection against
            selDagPath = selectionIter.getDagPath()
            mesh = OM.MFnMesh(selDagPath)
            fvColors.clear()
            fvColors = mesh.getFaceVertexColors(colorSet=layer)
            selLen = len(fvColors)
            vtxIds.setLength(selLen)
            fvIds.setLength(selLen)
            faceIds.setLength(selLen)

            meshIter = OM.MItMeshFaceVertex(selDagPath)
            i = 0
            while not meshIter.isDone():
                vtxIds[i] = meshIter.vertexId()
                faceIds[i] = meshIter.faceId()
                fvIds[i] = meshIter.faceVertexId()
                i += 1
                meshIter.next()

            if selectionIter.hasComponents():
                (compDagPath, fVert) = selectionIter.getComponent()
                # Iterate through selected facevertices on current selection
                fvIt = OM.MItMeshFaceVertex(selDagPath, fVert)
                while not fvIt.isDone():
                    faceId = fvIt.faceId()
                    fvId = fvIt.faceVertexId()
                    vtxId = fvIt.vertexId()
                    for idx in xrange(selLen):
                        if (faceId == faceIds[idx] and
                           fvId == fvIds[idx] and
                           vtxId == vtxIds[idx] and
                           compDagPath == selDagPath):
                            fvCol = fvColors[idx]
                            luminance = ((fvCol.r +
                                          fvCol.r +
                                          fvCol.b +
                                          fvCol.g +
                                          fvCol.g +
                                          fvCol.g) / float(6.0))
                            outColor = maya.cmds.colorAtPoint(
                                'SXRamp', o='RGB', u=luminance, v=luminance)
                            outAlpha = maya.cmds.colorAtPoint(
                                'SXAlphaRamp', o='A', u=luminance, v=luminance)
                            fvColors[idx].r = outColor[0]
                            fvColors[idx].g = outColor[1]
                            fvColors[idx].b = outColor[2]
                            fvColors[idx].a = outAlpha[0]
                            break
                    fvIt.next()
            else:
                fvIt = OM.MItMeshFaceVertex(selDagPath)
                k = 0
                while not fvIt.isDone():
                    fvCol = fvColors[k]
                    luminance = ((fvCol.r +
                                  fvCol.r +
                                  fvCol.b +
                                  fvCol.g +
                                  fvCol.g +
                                  fvCol.g) / float(6.0))
                    outColor = maya.cmds.colorAtPoint(
                        'SXRamp', o='RGB', u=luminance, v=luminance)
                    outAlpha = maya.cmds.colorAtPoint(
                        'SXAlphaRamp', o='A', u=luminance, v=luminance)
                    fvColors[k].r = outColor[0]
                    fvColors[k].g = outColor[1]
                    fvColors[k].b = outColor[2]
                    fvColors[k].a = outAlpha[0]
                    k += 1
                    fvIt.next()

            mesh.setFaceVertexColors(fvColors, faceIds, vtxIds)
            selectionIter.next()

        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print(
            'SX Tools: Surface luminance remap duration ' + str(totalTime))

    def copyLayer(self, shapes, mode=1):
        refLayers = sxglobals.layers.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        layerA = sxglobals.settings.tools['sourceLayer']
        layerB = sxglobals.settings.tools['targetLayer']

        if (layerA in refLayers) and (layerB in refLayers):
            for shape in shapes:
                attrA = '.' + layerA + 'BlendMode'
                modeA = maya.cmds.getAttr(str(shape) + attrA)
                attrB = '.' + layerB + 'BlendMode'

                selectionList = OM.MSelectionList()
                selectionList.add(shape)
                nodeDagPath = OM.MDagPath()
                nodeDagPath = selectionList.getDagPath(0)
                MFnMesh = OM.MFnMesh(nodeDagPath)

                layerAColors = OM.MColorArray()
                layerAColors = MFnMesh.getFaceVertexColors(colorSet=layerA)

                if mode == 2:
                    modeB = maya.cmds.getAttr(str(shape) + attrB)
                    layerBColors = OM.MColorArray()
                    layerBColors = MFnMesh.getFaceVertexColors(colorSet=layerB)
                    temp = OM.MColorArray()
                    temp = layerBColors

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

                maya.cmds.polyColorSet(shape, currentColorSet=True, colorSet=layerB)
                MFnMesh.setFaceVertexColors(layerAColors, faceIds, vtxIds)

                maya.cmds.setAttr(str(shape) + attrB, modeA)

                if mode == 2:
                    maya.cmds.polyColorSet(shape, currentColorSet=True, colorSet=layerA)
                    MFnMesh.setFaceVertexColors(temp, faceIds, vtxIds)

                    maya.cmds.setAttr(str(shape) + attrA, modeB)

            sxglobals.layers.refreshLayerList()
            sxglobals.layers.compositeLayers()

        else:
            print('SXTools Error: Invalid layers!')

    # Updates tool title bar and returns active shading mode
    def verifyShadingMode(self):
        if len(sxglobals.settings.shapeArray) > 0:
            obj = sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1]
            mode = int(maya.cmds.getAttr(obj + '.shadingMode') + 1)

            objectLabel = (
                'Selected Objects: ' +
                str(len(sxglobals.settings.objectArray)) +
                '   |   ' +
                'Layer Set: ' +
                str(int(maya.cmds.getAttr(
                    str(sxglobals.settings.shapeArray[0]) +
                       '.activeLayerSet'))+1) + '/' +
                       str(sxglobals.layers.getLayerSets(
                            sxglobals.settings.shapeArray[0])+1))

            maya.cmds.frameLayout('layerFrame', edit=True, label=objectLabel)
            maya.cmds.radioButtonGrp('shadingButtons', edit=True, select=mode)
            return mode

    def setShadingMode(self, mode):
        for shape in sxglobals.settings.shapeArray:
            maya.cmds.setAttr(str(shape) + '.shadingMode', mode)

        if sxglobals.settings.tools['compositor'] == 1:
            if mode == 0:
                maya.cmds.sets(
                    sxglobals.settings.shapeArray, e=True, forceElement='SXShaderSG')
                for shape in sxglobals.settings.shapeArray:
                    maya.cmds.setAttr(str(shape) + '.materialBlend', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColors', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColorChannel', 'None', type='string')

                maya.cmds.modelEditor(
                    'modelPanel4',
                    edit=True,
                    useDefaultMaterial=False,
                    displayLights='all',
                    lights=True,
                    displayTextures=True)

            elif mode == 1:
                maya.cmds.sets(
                    sxglobals.settings.shapeArray, e=True, forceElement='SXDebugShaderSG')
                for shape in sxglobals.settings.shapeArray:
                    maya.cmds.setAttr(str(shape) + '.materialBlend', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColors', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColorChannel', 'None', type='string')

            elif mode == 2:
                maya.cmds.sets(
                    sxglobals.settings.shapeArray, e=True, forceElement='SXDebugShaderSG')
                for shape in sxglobals.settings.shapeArray:
                    maya.cmds.setAttr(str(shape) + '.materialBlend', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColors', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColorChannel', 'None', type='string')

        elif sxglobals.settings.tools['compositor'] == 2:
            if mode == 0:
                sxglobals.settings.tools['compositeEnabled']=True
                for shape in sxglobals.settings.shapeArray:
                    maya.cmds.setAttr(str(shape) + '.materialBlend', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColors', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColorChannel', 'Ambient+Diffuse', type='string')
                maya.cmds.modelEditor(
                    'modelPanel4',
                    edit=True,
                    useDefaultMaterial=False,
                    displayLights='all',
                    lights=True,
                    displayTextures=True)

                # kludgy kludge for deadling with
                # paint vertex tool output in sw compositing
                if sxglobals.settings.tools['currentTool'] == 'SXPaint':
                    maya.cmds.setToolTo('selectSuperContext')
                    sxglobals.settings.tools['currentTool'] = 'Select'
                    sxglobals.layers.refreshLayerList()

            elif mode == 1 or mode == 2:
                for shape in sxglobals.settings.shapeArray:
                    maya.cmds.setAttr(str(shape) + '.materialBlend', 0)
                    maya.cmds.setAttr(str(shape) + '.displayColors', 1)
                    maya.cmds.setAttr(str(shape) + '.displayColorChannel', 'None', type='string')

        sxglobals.layers.compositeLayers()

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
                if 'sxSubMesh' in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'set' in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'groupId' in str(hist):
                    histList.remove(hist)
            for hist in reversed(histList):
                if 'topoSymmetrySet' in str(hist):
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
        if shift:
            if len(sxglobals.settings.componentArray) > 0:
                sxglobals.layers.clearLayer(
                    sxglobals.layers.sortLayers(
                        sxglobals.settings.project['LayerData'].keys()))
            else:
                sxglobals.layers.clearLayer(
                    sxglobals.layers.sortLayers(
                        sxglobals.settings.project['LayerData'].keys()),
                        sxglobals.settings.shapeArray)
        elif not shift:
            if len(sxglobals.settings.componentArray) > 0:
                sxglobals.layers.clearLayer(
                    [sxglobals.settings.tools['selectedLayer'], ])
            else:
                sxglobals.layers.clearLayer(
                    [sxglobals.settings.tools['selectedLayer'], ],
                    sxglobals.settings.shapeArray)

    def setLayerOpacity(self):
        alphaMax = sxglobals.settings.layerAlphaMax
        sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])

        for shape in sxglobals.settings.shapeArray:
            layer = sxglobals.settings.tools['selectedLayer']
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

            # TODO: Support for transparency in layer1 with sw compositing
            if (str(layer) == 'layer1') and (sliderAlpha < 1):
                maya.cmds.setAttr(str(shape) + '.transparency', 1)
                if alphaMax == 1:
                    maya.cmds.shaderfx(
                        sfxnode='SXShader',
                        makeConnection=(
                            sxglobals.settings.nodeDict['transparencyComp'], 0,
                            sxglobals.settings.nodeDict['SXShader'], 0))
                # maya.cmds.shaderfx(sfxnode='SXShader', update=True)
            elif (str(layer) == 'layer1') and (sliderAlpha == 1):
                maya.cmds.setAttr(str(shape) + '.transparency', 0)
                if alphaMax < 1:
                    maya.cmds.shaderfx(
                        sfxnode='SXShader',
                        breakConnection=(
                            sxglobals.settings.nodeDict['transparencyComp'], 0,
                            sxglobals.settings.nodeDict['SXShader'], 0))
                # maya.cmds.shaderfx(sfxnode='SXShader', update=True)

        sxglobals.layers.getLayerPaletteAndOpacity(
            sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
            sxglobals.settings.tools['selectedLayer'])

    def getLayerMask(self):
        maskList = []

        sxglobals.layers.setColorSet(sxglobals.settings.tools['selectedLayer'])

        vertFaceList = maya.cmds.ls(
            maya.cmds.polyListComponentConversion(
                sxglobals.settings.shapeArray, tvf=True), fl=True)

        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(
                   vertFace, query=True, a=True)[0] == 0:
                    maskList.append(vertFace)
        elif not shift:
            for vertFace in vertFaceList:
                if maya.cmds.polyColorPerVertex(
                   vertFace, query=True, a=True)[0] > 0:
                    maskList.append(vertFace)

        if len(maskList) == 0:
            print('SX Tools: No layer mask found')
            return sxglobals.settings.selectionArray

        return maskList

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
                        color[2]])
            elif numChannels == 4:
                maya.cmds.artAttrPaintVertexCtx(
                    'artAttrColorPerVertexContext',
                    edit=True,
                    usepressure=False,
                    colorRGBAValue=[
                        color[0],
                        color[1],
                        color[2], 1])

    def setApplyColor(self):
        sxglobals.settings.tools['recentPaletteIndex'] = maya.cmds.palettePort(
            'recentPalette', query=True, scc=True)
        sxglobals.settings.currentColor = maya.cmds.palettePort(
            'recentPalette', query=True, rgb=True)
        maya.cmds.colorSliderGrp(
            'sxApplyColor',
            edit=True,
            rgbValue=sxglobals.settings.currentColor)

    def updateRecentPalette(self):
        addedColor = maya.cmds.colorSliderGrp(
            'sxApplyColor', query=True, rgbValue=True)
        swapColorArray = []

        for k in range(0, 7):
            maya.cmds.palettePort('recentPalette', edit=True, scc=k)
            swapColorArray.append(
                maya.cmds.palettePort('recentPalette', query=True, rgb=True))

        if not addedColor in swapColorArray:
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

        if shift:
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

        elif not shift:
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

        if shift:
            self.deletePalette(category, preset)
            maya.cmds.deleteUI(category+preset)
            sxglobals.settings.savePalettes()
        elif not shift:
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

        if not set(targetList).issubset(refLayers):
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
            self.clearRamp('SXAlphaRamp')
            name = maya.cmds.optionMenu('rampPresets', query=True, value=True)
            alphaName = maya.cmds.optionMenu('rampPresets', query=True, value=True) + '_Alpha'
            maya.cmds.nodePreset(load=('SXRamp', name))
            maya.cmds.nodePreset(load=('SXAlphaRamp', alphaName))
        elif mode == 'preset' and shift:
            presetNameArray = maya.cmds.nodePreset(list='SXRamp')
            if len(presetNameArray) > 0:
                maya.cmds.nodePreset(delete=('SXRamp', maya.cmds.optionMenu(
                    'rampPresets', query=True, value=True)))
                maya.cmds.nodePreset(delete=('SXAlphaRamp', maya.cmds.optionMenu(
                    'rampPresets', query=True, value=True) + '_Alpha'))
                if len(presetNameArray) > 1:
                    sxglobals.settings.tools['gradientPreset'] = 1
                else:
                    sxglobals.settings.tools['gradientPreset'] = 0
            elif len(presetNameArray) == 0:
                print('SXTools: Preset list empty!')
        elif mode == 'preset' and not shift:
            name = maya.cmds.textField(
                'presetName', query=True, text=True).replace(' ', '_')
            alphaName = maya.cmds.textField(
                'presetName', query=True, text=True).replace(' ', '_') + '_Alpha'
            if len(name) > 0:
                maya.cmds.nodePreset(save=('SXRamp', name))
                maya.cmds.nodePreset(save=('SXAlphaRamp', alphaName))
            elif len(name) == 0:
                print('SXTools: Invalid preset name!')
        elif mode == 5 and shift:
            self.calculateCurvature(
                sxglobals.settings.objectArray,
                normalize=True)
            sxglobals.layers.refreshLayerList()
            sxglobals.layers.compositeLayers()
        elif mode == 5:
            self.calculateCurvature(
                sxglobals.settings.objectArray,
                normalize=False)
            sxglobals.layers.refreshLayerList()
            sxglobals.layers.compositeLayers()
        elif mode == 4:
            self.remapRamp()
            sxglobals.layers.refreshLayerList()
            sxglobals.layers.compositeLayers()
        else:
            self.gradientFill(mode)
            sxglobals.layers.refreshLayerList()
            sxglobals.layers.compositeLayers()

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
        attr = '.' + sxglobals.settings.tools['selectedLayer'] + 'BlendMode'
        for shape in sxglobals.settings.shapeArray:
            maya.cmds.setAttr(str(shape) + attr, mode)

        #sxglobals.layers.setSelectedLayer()
        sxglobals.layers.compositeLayers()

    def swapLayerSets(self, objects, targetSet, offset=False):
        if offset:
            targetSet -= 1
        if (targetSet > sxglobals.layers.getLayerSets(objects[0])) or (targetSet < 0):
            print('SX Tools Error: Selected layer set does not exist!')
            return
        refLayers = sxglobals.layers.sortLayers(
            sxglobals.settings.project['LayerData'].keys())
        refLayers.remove('composite')

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

        # self.getLayerPaletteAndOpacity(
        #     sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
        #     sxglobals.settings.tools['selectedLayer'])
        # sxglobals.layers.refreshLayerList()
        # sxglobals.export.compositeLayers()
        # maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    def removeLayerSet(self, objects):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift:
            sxglobals.layers.clearLayerSets()
        else:
            refLayers = sxglobals.layers.sortLayers(
                sxglobals.settings.project['LayerData'].keys())
            refLayers.remove('composite')
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
            if (not (all(active == actives[0] for active in actives)) or
               not (all(num == numSets[0] for num in numSets))):
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
            maya.cmds.addAttr(
                skinMesh,
                ln='skinnedMesh',
                at='bool',
                dv=True)
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
                        representation=4)
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
            maya.cmds.setAttr(skinMesh[0] + '.outlinerColor', 0.75, 0.25, 1)
            maya.cmds.setAttr(skinMesh[0] + '.useOutlinerColor', True)
            skinMeshArray.append(skinMesh[0])

        maya.cmds.delete(skinMeshArray, ch=True)
        maya.cmds.sets(
            skinMeshArray,
            e=True,
            forceElement='initialShadingGroup')
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

    def setSubMeshFlags(self, objects, flag):
        for obj in objects:
            maya.cmds.setAttr(obj+'.subMeshes', flag)

    def setSubdivisionFlag(self, objects, flag):
        if flag > 0:
            maya.cmds.setAttr('sxCrease1.creaseLevel', flag * 0.25)
            maya.cmds.setAttr('sxCrease2.creaseLevel', flag * 0.5)
            maya.cmds.setAttr('sxCrease3.creaseLevel', flag * 0.75)
            maya.cmds.setAttr('sxCrease4.creaseLevel', 10)

        for obj in objects:
            maya.cmds.setAttr(obj+'.subdivisionLevel', flag)
            objShape = maya.cmds.listRelatives(obj, shapes=True)[0]
            maya.cmds.setAttr(objShape+'.smoothLevel', flag)

    def setCreaseBevelFlag(self, objects, flag):
        for obj in objects:
            maya.cmds.setAttr(obj+'.creaseBevels', flag)

    def setSmoothingFlag(self, objects, flag):
        for obj in objects:
            maya.cmds.setAttr(obj+'.smoothingAngle', flag)

    def setHardEdgeFlag(self, objects, flag):
        for obj in objects:
            maya.cmds.setAttr(obj+'.hardEdges', flag)
