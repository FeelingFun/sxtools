# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
# ----------------------------------------------------------------------------

import maya.cmds
import maya.api.OpenMaya as OM
import sxglobals


class LayerManagement(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting layers')

    # With hybrid vertex color compositing enabled
    # the 'composite' colorSet will be refreshed
    # after every user action
    def compositeLayers(self):
        # startTimeOcc = maya.cmds.timerX()
        if sxglobals.settings.tools['compositeEnabled']:
            numLayers = sxglobals.settings.project['LayerCount']

            maya.cmds.polyColorSet(
                sxglobals.settings.shapeArray, currentColorSet=True, colorSet='composite')

            for selected in sxglobals.settings.shapeArray:
                selectionList = OM.MSelectionList()
                selectionList.add(selected)
                nodeDagPath = OM.MDagPath()
                nodeDagPath = selectionList.getDagPath(0)
                MFnMesh = OM.MFnMesh(nodeDagPath)

                sourceColorArray = OM.MColorArray()
                targetColorArray = OM.MColorArray()
                targetColorArray = MFnMesh.getFaceVertexColors(colorSet='layer1')

                faceIds = OM.MIntArray()
                vtxIds = OM.MIntArray()

                lenSel = len(targetColorArray)

                faceIds.setLength(lenSel)
                vtxIds.setLength(lenSel)

                # generate faceID and vertexID arrays
                fvIt = OM.MItMeshFaceVertex(nodeDagPath)
                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()
                    k += 1
                    fvIt.next()

                sel = str(selected)
                shading = int(maya.cmds.getAttr(sel + '.shadingMode'))

                # Set layer1 to black if hidden
                visAttr = '.layer1Visibility'
                vis = bool(maya.cmds.getAttr(sel + visAttr))

                if not vis:
                    fvIt = OM.MItMeshFaceVertex(nodeDagPath)
                    k = 0
                    while not fvIt.isDone():
                        targetColorArray[k].r = 0.0
                        targetColorArray[k].g = 0.0
                        targetColorArray[k].b = 0.0
                        targetColorArray[k].a = 1.0
                        k += 1
                        fvIt.next()

                # accumulate targetColorArray through the remaining layers
                if shading == 0:
                    if numLayers > 1:
                        for i in range(2, numLayers+1):
                            sourceLayer = 'layer' + str(i)

                            modeAttr = '.' + sourceLayer + 'BlendMode'
                            mode = int(maya.cmds.getAttr(sel + modeAttr))

                            visAttr = '.' + sourceLayer + 'Visibility'
                            vis = bool(maya.cmds.getAttr(sel + visAttr))
                            sourceColorArray = MFnMesh.getFaceVertexColors(
                                colorSet=sourceLayer)

                            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

                            if not vis:
                                continue

                            elif mode == 0:
                                k = 0
                                while not fvIt.isDone():
                                    targetColorArray[k].r = (
                                        sourceColorArray[k].r * sourceColorArray[k].a +
                                        targetColorArray[k].r * (1 - sourceColorArray[k].a))
                                    targetColorArray[k].g = (
                                        sourceColorArray[k].g * sourceColorArray[k].a +
                                        targetColorArray[k].g * (1 - sourceColorArray[k].a))
                                    targetColorArray[k].b = (
                                        sourceColorArray[k].b * sourceColorArray[k].a +
                                        targetColorArray[k].b * (1 - sourceColorArray[k].a))
                                    #targetColorArray[k].a = 1.0
                                    k += 1
                                    fvIt.next()

                            elif mode == 1:
                                k = 0
                                while not fvIt.isDone():
                                    targetColorArray[k].r += sourceColorArray[
                                        k].r * sourceColorArray[k].a
                                    targetColorArray[k].g += sourceColorArray[
                                        k].g * sourceColorArray[k].a
                                    targetColorArray[k].b += sourceColorArray[
                                        k].b * sourceColorArray[k].a
                                    #targetColorArray[k].a = 1.0
                                    k += 1
                                    fvIt.next()

                            elif mode == 2:
                                # layer2 lerp with white using (1-alpha), multiply with layer1
                                k = 0
                                while not fvIt.isDone():
                                    sourceColorArray[k].r = (
                                        (sourceColorArray[k].r * sourceColorArray[k].a) +
                                        (1.0 * (1 - sourceColorArray[k].a)))
                                    sourceColorArray[k].g = (
                                        (sourceColorArray[k].g * sourceColorArray[k].a) +
                                        (1.0 * (1 - sourceColorArray[k].a)))
                                    sourceColorArray[k].b = (
                                        (sourceColorArray[k].b * sourceColorArray[k].a) +
                                        (1.0 * (1 - sourceColorArray[k].a)))

                                    targetColorArray[k].r = sourceColorArray[
                                        k].r * targetColorArray[k].r
                                    targetColorArray[k].g = sourceColorArray[
                                        k].g * targetColorArray[k].g
                                    targetColorArray[k].b = sourceColorArray[
                                        k].b * targetColorArray[k].b
                                    k += 1
                                    fvIt.next()
                            else:
                                print('SX Tools Error: Invalid blend mode')
                                return

                elif shading == 1:
                    targetColorArray = MFnMesh.getFaceVertexColors(colorSet=sxglobals.settings.tools['selectedLayer'])
                    fvIt = OM.MItMeshFaceVertex(nodeDagPath)
                    k = 0
                    while not fvIt.isDone():
                        if targetColorArray[k].a == 0.0:
                            targetColorArray[k].r = 0.0
                            targetColorArray[k].g = 0.0
                            targetColorArray[k].b = 0.0
                        k += 1
                        fvIt.next()

                elif shading == 2:
                    targetColorArray = MFnMesh.getFaceVertexColors(colorSet=sxglobals.settings.tools['selectedLayer'])
                    fvIt = OM.MItMeshFaceVertex(nodeDagPath)
                    k = 0
                    while not fvIt.isDone():
                        targetColorArray[k].r = targetColorArray[k].a
                        targetColorArray[k].g = targetColorArray[k].a
                        targetColorArray[k].b = targetColorArray[k].a
                        targetColorArray[k].a = 1.0
                        k += 1
                        fvIt.next()

                MFnMesh.setFaceVertexColors(targetColorArray, faceIds, vtxIds)

        # totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        # print('SX Tools: Layer compositing duration ' + str(totalTime))

    def mergeLayers(self, objects, sourceLayer, targetLayer, up):
        # startTimeOcc = maya.cmds.timerX()

        attrA = '.' + str(sourceLayer) + 'BlendMode'
        attrB = '.' + str(targetLayer) + 'BlendMode'
        color = sxglobals.settings.project['LayerData'][sourceLayer][1]

        fillColor = OM.MColor()
        fillColor.r = color[0]
        fillColor.g = color[1]
        fillColor.b = color[2]
        fillColor.a = color[3]

        for obj in objects:
            mode = int(maya.cmds.getAttr(obj + attrA))

            selectionList = OM.MSelectionList()
            selectionList.add(obj)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            sourceColorArray = OM.MColorArray()
            targetColorArray = OM.MColorArray()
            fillColorArray = OM.MColorArray()
            sourceColorArray = MFnMesh.getFaceVertexColors(
                colorSet=sourceLayer)
            targetColorArray = MFnMesh.getFaceVertexColors(
                colorSet=targetLayer)
            fillColorArray = MFnMesh.getFaceVertexColors(
                colorSet = sourceLayer)
            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            lenSel = len(sourceColorArray)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)
            k = 0
            while not fvIt.isDone():
                faceIds[k] = fvIt.faceId()
                vtxIds[k] = fvIt.vertexId()
                fillColorArray[k] = fillColor
                k += 1
                fvIt.next()

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            # alpha blend
            if mode == 0:
                k = 0
                while not fvIt.isDone():
                    targetColorArray[k].r = (
                        sourceColorArray[k].r * sourceColorArray[k].a +
                        targetColorArray[k].r * (1 - sourceColorArray[k].a))
                    targetColorArray[k].g = (
                        sourceColorArray[k].g * sourceColorArray[k].a +
                        targetColorArray[k].g * (1 - sourceColorArray[k].a))
                    targetColorArray[k].b = (
                        sourceColorArray[k].b * sourceColorArray[k].a +
                        targetColorArray[k].b * (1 - sourceColorArray[k].a))
                    targetColorArray[k].a += sourceColorArray[k].a
                    if targetColorArray[k].a > 1.0:
                       targetColorArray[k].a = 1.0
                    k += 1
                    fvIt.next()

            # additive
            elif mode == 1:
                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()

                    targetColorArray[k].r += sourceColorArray[
                        k].r * sourceColorArray[k].a
                    targetColorArray[k].g += sourceColorArray[
                        k].g * sourceColorArray[k].a
                    targetColorArray[k].b += sourceColorArray[
                        k].b * sourceColorArray[k].a
                    targetColorArray[k].a += sourceColorArray[k].a
                    if targetColorArray[k].a > 1.0:
                       targetColorArray[k].a = 1.0
                    k += 1
                    fvIt.next()

            # multiply
            elif mode == 2:
                # layer2 lerp with white using (1-alpha), multiply with layer1
                k = 0
                while not fvIt.isDone():
                    faceIds[k] = fvIt.faceId()
                    vtxIds[k] = fvIt.vertexId()

                    sourceColorArray[k].r = (
                        (sourceColorArray[k].r * sourceColorArray[k].a) +
                        (1.0 * (1 - sourceColorArray[k].a)))
                    sourceColorArray[k].g = (
                        (sourceColorArray[k].g * sourceColorArray[k].a) +
                        (1.0 * (1 - sourceColorArray[k].a)))
                    sourceColorArray[k].b = (
                        (sourceColorArray[k].b * sourceColorArray[k].a) +
                        (1.0 * (1 - sourceColorArray[k].a)))

                    targetColorArray[k].r = sourceColorArray[
                        k].r * targetColorArray[k].r
                    targetColorArray[k].g = sourceColorArray[
                        k].g * targetColorArray[k].g
                    targetColorArray[k].b = sourceColorArray[
                        k].b * targetColorArray[k].b
                    k += 1
                    fvIt.next()
            else:
                print('SX Tools Error: Invalid blend mode')
                return

            if up:
                maya.cmds.polyColorSet(
                    obj, currentColorSet=True, colorSet=targetLayer)
                MFnMesh.setFaceVertexColors(targetColorArray, faceIds, vtxIds)
                maya.cmds.polyColorSet(
                    obj, currentColorSet=True, colorSet=sourceLayer)
                MFnMesh.setFaceVertexColors(fillColorArray, faceIds, vtxIds)
            else:
                maya.cmds.polyColorSet(
                    obj, currentColorSet=True, colorSet=sourceLayer)
                MFnMesh.setFaceVertexColors(targetColorArray, faceIds, vtxIds)
                maya.cmds.polyColorSet(
                    obj, currentColorSet=True, colorSet=targetLayer)
                MFnMesh.setFaceVertexColors(fillColorArray, faceIds, vtxIds)

            maya.cmds.setAttr(str(obj) + attrA, 0)
            maya.cmds.setAttr(str(obj) + attrB, 0)

        # totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        # print('SX Tools: Mergelayers duration ' + str(totalTime))

    # If mesh color sets don't match the reference layers.
    # Sorts the existing color sets to the correct order,
    # and fills the missing slots with default layers.
    def patchLayers(self, objects):
        startTimeOcc = maya.cmds.timerX()
        noColorSetObject = []

        refLayers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        for obj in objects:
            currentColorSets = maya.cmds.polyColorSet(
                obj, query=True, allColorSets=True)
            if currentColorSets is not None:
                for layer in refLayers:
                    # maya.cmds.select(obj)
                    found = False

                    for colorSet in currentColorSets:
                        if colorSet == layer:
                            # NOTE: polyBlendColor is used to copy
                            # existing color sets to new list positions
                            # because Maya's color set copy function is broken,
                            # and either generates empty color sets,
                            # or copies from wrong indices.
                            maya.cmds.polyColorSet(
                                obj,
                                rename=True,
                                colorSet=str(colorSet),
                                newColorSet='tempColorSet')
                            maya.cmds.polyColorSet(
                                obj,
                                create=True,
                                clamped=True,
                                representation='RGBA',
                                colorSet=str(layer))
                            maya.cmds.polyBlendColor(
                                obj,
                                bcn=str(layer),
                                src='tempColorSet',
                                dst=str(layer),
                                bfn=0,
                                ch=False)
                            maya.cmds.polyColorSet(
                                obj,
                                delete=True,
                                colorSet='tempColorSet')
                            found = True

                    if not found:
                        maya.cmds.polyColorSet(
                            obj,
                            create=True,
                            clamped=True,
                            representation='RGBA',
                            colorSet=str(layer))
                        self.clearLayer([layer, ], [obj, ])

                maya.cmds.polyColorSet(
                    obj,
                    currentColorSet=True,
                    colorSet=refLayers[0])
                maya.cmds.sets(obj, e=True, forceElement='SXShaderSG')
            else:
                noColorSetObject.append(obj)

        if len(noColorSetObject) > 0:
            self.resetLayers(noColorSetObject)

        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Patchlayers duration ' + str(totalTime))
        # maya.cmds.select(sxglobals.settings.selectionArray)

    # Resulting blended layer is set to Alpha blending mode
    def mergeLayerDirection(self, shapes, up):
        startTimeOcc = maya.cmds.timerX()
        sourceLayer = sxglobals.settings.tools['selectedLayer']
        if (str(sourceLayer) == 'layer1') and up:
            print('SX Tools Error: Cannot merge layer1')
            return
        elif ((str(sourceLayer) == 'layer' +
              str(sxglobals.settings.project['LayerCount'])) and
              (not up)):
            print(
                'SX Tools Error: Cannot merge ' +
                'layer'+str(sxglobals.settings.project['LayerCount']))
            return
        elif ((str(sourceLayer) == 'occlusion') or
              (str(sourceLayer) == 'metallic') or
              (str(sourceLayer) == 'smoothness') or
              (str(sourceLayer) == 'transmission') or
              (str(sourceLayer) == 'emission')):
            print('SX Tools Error: Cannot merge material channels')
            return

        layerIndex = sxglobals.settings.project['LayerData'][sourceLayer][0]-1
        if up:
            targetLayer = sxglobals.settings.project['RefNames'][layerIndex-1]
        else:
            sourceLayer = sxglobals.settings.project['RefNames'][layerIndex+1]
            targetLayer = sxglobals.settings.project['RefNames'][layerIndex]

        self.mergeLayers(
                shapes,
                sourceLayer,
                targetLayer, up)

        self.refreshLayerList()
        totalTime = maya.cmds.timerX(startTime=startTimeOcc)
        print('SX Tools: Mergelayerdirection duration ' + str(totalTime))

    # IF mesh has no color sets at all,
    # or non-matching color set names.
    def resetLayers(self, objects):
        for obj in objects:
            # Remove existing color sets, if any
            colorSets = maya.cmds.polyColorSet(
                obj,
                query=True,
                allColorSets=True)
            if colorSets is not None:
                for colorSet in colorSets:
                    maya.cmds.polyColorSet(
                        obj,
                        delete=True,
                        colorSet=colorSet)

        # Create color sets
        refLayers = self.sortLayers(
                sxglobals.settings.project['LayerData'].keys())

        for layer in refLayers:
            maya.cmds.polyColorSet(
                objects,
                create=True,
                clamped=True,
                representation='RGBA',
                colorSet=str(layer))

        self.clearLayer(refLayers, objects)

    def getLayerSets(self, obj):
        var = int(maya.cmds.getAttr(obj + '.numLayerSets'))
        return var

    def addLayerSet(self, objects, varIdx):
        for object in objects:
            num = int(maya.cmds.getAttr(object + '.numLayerSets'))
            if num != varIdx:
                print('SX Tools Error: Selection with mismatching Layer Sets!')
                return

        if varIdx == 9:
            print('SX Tools: Maximum layer sets added!')
            return

        refLayers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())
        refLayers.remove('composite')
        targetLayers = []
        var = varIdx

        var += 1
        for layer in refLayers:
            layerName = str(layer) + '_var' + str(var)
            maya.cmds.polyColorSet(
                objects, create=True,
                colorSet=layerName)
            targetLayers.append(layerName)
        sxglobals.tools.copyFaceVertexColors(objects, refLayers, targetLayers)
        for object in objects:
            maya.cmds.setAttr(object + '.numLayerSets', var)

    def clearLayer(self, layers, objList=None):
        objects = []
        if 'composite' in layers:
            layers.remove('composite')
        for layer in layers:
            if objList is None:
                objects = sxglobals.settings.shapeArray
            else:
                objects = objList

            maya.cmds.polyColorSet(
                objects,
                currentColorSet=True,
                colorSet=layer)
            color = sxglobals.settings.project['LayerData'][layer][1]

            # Component vs. object selection
            if objList is None:
                maya.cmds.polyColorPerVertex(
                    r=color[0],
                    g=color[1],
                    b=color[2],
                    a=color[3],
                    representation=4)
            else:
                maya.cmds.polyColorPerVertex(
                    objects,
                    r=color[0],
                    g=color[1],
                    b=color[2],
                    a=color[3],
                    representation=4)

            attr = '.' + str(layer) + 'BlendMode'
            for obj in objects:
                maya.cmds.setAttr(str(obj) + attr, 0)

    def toggleLayer(self, layer):
        object = sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1]
        checkState = maya.cmds.getAttr(
            str(object) + '.' + str(layer) + 'Visibility')
        for shape in sxglobals.settings.shapeArray:
            maya.cmds.setAttr(
                str(shape) + '.' + str(layer) + 'Visibility', not checkState)
        state = self.verifyLayerState(layer)
        layerIndex = int(maya.cmds.textScrollList(
            'layerList', query=True, selectIndexedItem=True)[0])
        maya.cmds.textScrollList(
            'layerList', edit=True, removeIndexedItem=layerIndex)
        maya.cmds.textScrollList(
            'layerList', edit=True, appendPosition=(layerIndex, state))
        maya.cmds.textScrollList(
            'layerList', edit=True, selectIndexedItem=layerIndex)

    # Called when the user double-clicks a layer in the tool UI
    def toggleAllLayers(self, selLayer):
        modifiers = maya.cmds.getModifiers()
        shift = bool((modifiers & 1) > 0)

        if shift:
            layers = self.sortLayers(
                sxglobals.settings.project['LayerData'].keys())
            layers.remove('composite')
            for layer in layers:
                if layer != selLayer:
                    self.toggleLayer(layer)

        elif not shift:
            self.toggleLayer(selLayer)

        self.refreshLayerList()
        self.compositeLayers()

    # Updates the selected color set to match the highlighted layer in the UI
    def setColorSet(self, highlightedLayer):
        maya.cmds.polyColorSet(
            sxglobals.settings.shapeArray,
            currentColorSet=True,
            colorSet=highlightedLayer)

    # This function populates the layer list in the tool UI.
    # Any state change in a list item requires a list rebuild
    # since the text in a single item can not be changed
    # after creation
    def refreshLayerList(self):
        if maya.cmds.textScrollList('layerList', exists=True):
            maya.cmds.textScrollList('layerList', edit=True, removeAll=True)

        layers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())
        layers.remove('composite')
        states = []
        for layer in layers:
            states.append(self.verifyLayerState(layer))

        maya.cmds.textScrollList(
            'layerList',
            edit=True,
            append=states,
            selectIndexedItem=sxglobals.settings.tools['selectedLayerIndex'])

        maya.cmds.text(
            'layerBlendModeLabel',
            edit=True,
            label=sxglobals.settings.tools['selectedDisplayLayer'] + ' Blend Mode:')
        maya.cmds.text(
            'layerColorLabel',
            edit=True,
            label=sxglobals.settings.tools['selectedDisplayLayer'] + ' Colors:')
        maya.cmds.text(
            'layerOpacityLabel',
            edit=True,
            label=sxglobals.settings.tools['selectedDisplayLayer'] + ' Opacity:')

        self.getLayerPaletteAndOpacity(
            sxglobals.settings.shapeArray[
                len(sxglobals.settings.shapeArray)-1],
                sxglobals.settings.tools['selectedLayer'])

    def sortLayers(self, layers):
        sortedLayers = []
        if layers is not None:
            for ref in sxglobals.settings.refArray:
                if ref in layers:
                    sortedLayers.append(ref)
        return sortedLayers

    def verifyLayerState(self, layer):
        if layer == 'composite':
            return
        else:
            obj = sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1]
            selectionList = OM.MSelectionList()
            selectionList.add(obj)
            nodeDagPath = OM.MDagPath()
            nodeDagPath = selectionList.getDagPath(0)
            MFnMesh = OM.MFnMesh(nodeDagPath)

            layerColors = OM.MColorArray()
            layerColors = MFnMesh.getFaceVertexColors(colorSet=layer)

            # States: visibility, mask, adjustment
            state = [False, False, False]
            state[0] = (bool(maya.cmds.getAttr(str(obj) +
                        '.' + str(layer) + 'Visibility')))

            for k in range(len(layerColors)):
                if ((layerColors[k].a > 0) and
                   (layerColors[k].a < sxglobals.settings.project['AlphaTolerance'])):
                    state[2] = True
                elif ((layerColors[k].a >= sxglobals.settings.project['AlphaTolerance']) and
                      (layerColors[k].a <= 1)):
                    state[1] = True

            if not state[0]:
                hidden = 'H'
            else:
                hidden = ' '
            if state[1]:
                mask = 'M'
            else:
                mask = ' '
            if state[2]:
                adj = 'A'
            else:
                adj = ' '

            layerName = sxglobals.settings.project['LayerData'][layer][6]
            itemString = hidden + mask + adj + '  ' + layerName
            return itemString

    # Color sets of any selected object are checked
    # to see if they match the reference set.
    # Also verifies subdivision mode.
    def verifyObjectLayers(self, objects):
        refLayers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())
        nonStdObjs = []
        empty = False

        sxglobals.setup.setPrimVars()

        for shape in sxglobals.settings.shapeArray:
            maya.cmds.setAttr(str(shape)+'.useGlobalSmoothDrawType', False)
            maya.cmds.setAttr(str(shape)+'.smoothDrawType', 2)

        for object in objects:
            testLayers = maya.cmds.polyColorSet(
                object,
                query=True,
                allColorSets=True)
            if testLayers is None:
                nonStdObjs.append(object)
                empty = True
            elif not set(refLayers).issubset(testLayers):
                nonStdObjs.append(object)
                empty = False

        if len(nonStdObjs) > 0 and empty:
            return 1, nonStdObjs
        elif len(nonStdObjs) > 0 and not empty:
            return 2, nonStdObjs
        else:
            return 0, None

    def getLayerPaletteAndOpacity(self, obj, layer):
        selectionList = OM.MSelectionList()
        selectionList.add(obj)
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

            if (not match) and (n < 8):
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
            if maya.cmds.optionMenu('layerBlendModes', exists=True):
                maya.cmds.optionMenu('layerBlendModes', edit=True, enable=False)
            if maya.cmds.text('layerOpacityLabel', exists=True):
                maya.cmds.text('layerOpacityLabel', edit=True, enable=False)
            if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
                maya.cmds.floatSlider(
                    'layerOpacitySlider',
                    edit=True,
                    enable=False)
            return
        # Blend modes are only valid for color layers,
        # not material channels
        else:
            if maya.cmds.text('layerOpacityLabel', exists=True):
                maya.cmds.text('layerOpacityLabel', edit=True, enable=True)
            if maya.cmds.floatSlider('layerOpacitySlider', exists=True):
                maya.cmds.floatSlider(
                    'layerOpacitySlider',
                    edit=True,
                    enable=True)

            attr = (
                '.' + sxglobals.settings.project['RefNames'][sxglobals.settings.tools['selectedLayerIndex']-1] +
                'BlendMode')
            mode = maya.cmds.getAttr(str(obj) + attr) + 1
            maya.cmds.optionMenu(
                'layerBlendModes',
                edit=True,
                select=mode,
                enable=True)

    def clearLayerSets(self):
        refLayers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())
        for shape in sxglobals.settings.shapeArray:
            colorSets = maya.cmds.polyColorSet(
                shape,
                query=True,
                allColorSets=True)
            for colorSet in colorSets:
                if colorSet not in refLayers:
                    maya.cmds.polyColorSet(
                        shape,
                        delete=True,
                        colorSet=colorSet)
            maya.cmds.setAttr(str(shape)+'.activeLayerSet', 0)
            maya.cmds.setAttr(str(shape)+'.numLayerSets', 0)
        sxglobals.core.updateSXTools()

    def highlightLayer(self):
        modifiers = maya.cmds.getModifiers()
        alt = bool((modifiers & 8)> 0)

        selectedIndex = int(maya.cmds.textScrollList(
            'layerList', query=True, selectIndexedItem=True)[0])
        refLayers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        sxglobals.settings.tools['selectedLayer'] = str(refLayers[selectedIndex - 1])
        sxglobals.settings.tools['selectedDisplayLayer'] = sxglobals.settings.project['LayerData'][sxglobals.settings.tools['selectedLayer']][6]
        sxglobals.settings.tools['selectedLayerIndex'] = selectedIndex

        self.getLayerPaletteAndOpacity(
            sxglobals.settings.shapeArray[
                len(sxglobals.settings.shapeArray)-1],
                sxglobals.settings.tools['selectedLayer'])

        maya.cmds.text(
            'layerBlendModeLabel',
            edit=True,
            label=sxglobals.settings.tools['selectedDisplayLayer'] + ' Blend Mode:')
        maya.cmds.text(
            'layerOpacityLabel',
            edit=True,
            label=sxglobals.settings.tools['selectedDisplayLayer'] + ' Opacity:')
        maya.cmds.text(
            'layerColorLabel',
            edit=True,
            label=sxglobals.settings.tools['selectedDisplayLayer'] + ' Colors:')

        # if layer alt-clicked or shift-alt-clicked select mask
        if alt:
            maya.cmds.select(sxglobals.tools.getLayerMask())

        if maya.cmds.getAttr(str(sxglobals.settings.shapeArray[0]) + '.shadingMode') != 0:
            self.compositeLayers()
