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

    def mergeLayers(self, object, sourceLayer, targetLayer, up):
        if up is True:
            target = targetLayer
        else:
            target = sourceLayer

        selected = str(object)
        attr = '.' + str(self.getSelectedLayer()) + 'BlendMode'
        mode = int(maya.cmds.getAttr(selected + attr))

        # NOTE: polyBlendColor is used to copy existing
        # color sets to new list positions because
        # Maya's color set copy function is bugged.

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

            sourceColorArray = OM.MColorArray()
            targetColorArray = OM.MColorArray()
            sourceColorArray = MFnMesh.getFaceVertexColors(
                colorSet=sourceLayer)
            targetColorArray = MFnMesh.getFaceVertexColors(
                colorSet=targetLayer)
            faceIds = OM.MIntArray()
            vtxIds = OM.MIntArray()

            lenSel = len(sourceColorArray)

            faceIds.setLength(lenSel)
            vtxIds.setLength(lenSel)

            fvIt = OM.MItMeshFaceVertex(nodeDagPath)

            if mode == 1:
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
                    k += 1
                    fvIt.next()
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

            maya.cmds.polyColorSet(
                selected, currentColorSet=True, colorSet=str(target))
            MFnMesh.setFaceVertexColors(targetColorArray, faceIds, vtxIds)

        if up is True:
            maya.cmds.polyColorSet(
                selected,
                delete=True,
                colorSet=str(sourceLayer))
        else:
            maya.cmds.polyColorSet(
                selected,
                delete=True,
                colorSet=str(targetLayer))

    # If mesh color sets don't match the reference layers.
    # Sorts the existing color sets to the correct order,
    # and fills the missing slots with default layers.
    def patchLayers(self, objects):
        noColorSetObject = []

        refLayers = self.sortLayers(
            sxglobals.settings.project['LayerData'].keys())

        for object in objects:
            currentColorSets = maya.cmds.polyColorSet(
                object, query=True, allColorSets=True)
            if currentColorSets is not None:
                for layer in refLayers:
                    maya.cmds.select(object)
                    found = False

                    for colorSet in currentColorSets:
                        if colorSet == layer:
                            # NOTE: polyBlendColor is used to copy
                            # existing color sets to new list positions
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
                            maya.cmds.polyColorSet(
                                object,
                                delete=True,
                                colorSet='tempColorSet')
                            found = True

                    if found is False:
                        maya.cmds.polyColorSet(
                            object,
                            create=True,
                            clamped=True,
                            representation='RGBA',
                            colorSet=str(layer))
                        self.clearLayer([layer, ], [object, ])

                maya.cmds.polyColorSet(
                    object,
                    currentColorSet=True,
                    colorSet=refLayers[0])
                maya.cmds.sets(object, e=True, forceElement='SXShaderSG')
            else:
                noColorSetObject.append(object)

        if len(noColorSetObject) > 0:
            self.resetLayers(noColorSetObject)

        maya.cmds.select(sxglobals.settings.selectionArray)
        sxglobals.core.selectionManager()

    # Resulting blended layer is set to Alpha blending mode
    def mergeLayerDirection(self, shapes, up):
        sourceLayer = self.getSelectedLayer()
        if ((str(sourceLayer) == 'layer1') and
           (up is True)):
            print('SX Tools Error: Cannot merge layer1')
            return
        elif ((str(sourceLayer) == 'layer' +
              str(sxglobals.settings.project['LayerCount'])) and
              (up is False)):
            print(
                'SX Tools Error: Cannot merge ' +
                'layer'+str(sxglobals.settings.project['LayerCount']))
            return
        elif ((str(sourceLayer) == 'occlusion') or
              (str(sourceLayer) == 'specular') or
              (str(sourceLayer) == 'transmission') or
              (str(sourceLayer) == 'emission')):
            print('SX Tools Error: Cannot merge material channels')
            return

        layerIndex = sxglobals.settings.project['LayerData'][sourceLayer][0]-1
        if up is True:
            targetLayer = sxglobals.settings.project['RefNames'][layerIndex-1]
        else:
            sourceLayer = sxglobals.settings.project['RefNames'][layerIndex+1]
            targetLayer = sxglobals.settings.project['RefNames'][layerIndex]

        for shape in shapes:
            self.mergeLayers(
                shape,
                sourceLayer,
                targetLayer, up)
            self.patchLayers([shape, ])

        if up is True:
            maya.cmds.polyColorSet(
                shapes,
                currentColorSet=True,
                colorSet=str(targetLayer))
        else:
            maya.cmds.polyColorSet(
                shapes,
                currentColorSet=True,
                colorSet=str(sourceLayer))
        self.refreshLayerList()
        self.refreshSelectedItem()

    # IF mesh has no color sets at all,
    # or non-matching color set names.
    def resetLayers(self, objects):
        for object in objects:
            # Remove existing color sets, if any
            colorSets = maya.cmds.polyColorSet(
                object,
                query=True,
                allColorSets=True)
            if colorSets is not None:
                for colorSet in colorSets:
                    maya.cmds.polyColorSet(
                        object,
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
            self.clearLayer([layer, ], objects)

        maya.cmds.polyColorSet(
            object,
            currentColorSet=True,
            colorSet='layer1')
        maya.cmds.sets(object, e=True, forceElement='SXShaderSG')

    def getLayerSet(self, object):
        var = int(maya.cmds.getAttr(object + '.numLayerSets'))
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

        refLayers = self.sortLayers(sxglobals.settings.project['LayerData'].keys())
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

        maya.cmds.polyColorSet(
            objects,
            currentColorSet=True,
            colorSet='layer1')

    def clearLayer(self, layers, objList=None):
        objects = []
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
            if objList is None:
                maya.cmds.polyColorPerVertex(
                    r=color[0],
                    g=color[1],
                    b=color[2],
                    a=color[3],
                    representation=4,
                    cdo=True)
            else:
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

    # Called when the user double-clicks a layer in the tool UI
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

    # Called when the user hides or shows
    # all vertex color layers in the tool UI
    def toggleAllLayers(self):
        layers = self.sortLayers(sxglobals.settings.project['LayerData'].keys())
        for layer in layers:
            self.toggleLayer(layer)

        self.refreshLayerList()
        self.refreshSelectedItem()
        maya.cmds.shaderfx(sfxnode='SXShader', update=True)

    # Updates the tool UI to highlight the current color set
    def setColorSet(self, highlightedLayer):
        maya.cmds.polyColorSet(
            sxglobals.settings.shapeArray,
            currentColorSet=True,
            colorSet=highlightedLayer)

    # This function populates the layer list in the tool UI.
    def refreshLayerList(self):
        if maya.cmds.textScrollList('layerList', exists=True):
            maya.cmds.textScrollList('layerList', edit=True, removeAll=True)

        layers = self.sortLayers(sxglobals.settings.project['LayerData'].keys())
        states = []
        for layer in layers:
            states.append(self.verifyLayerState(layer))
        maya.cmds.textScrollList(
            'layerList',
            edit=True,
            append=states,
            numberOfRows=(
                sxglobals.settings.project['LayerCount'] +
                sxglobals.settings.project['ChannelCount']),
            selectCommand=(
                "sxtools.sxglobals.layers.setColorSet("
                "sxtools.sxglobals.layers.getSelectedLayer())\n"
                "sxtools.sxglobals.tools.getLayerPaletteOpacity("
                "sxtools.sxglobals.settings.shapeArray["
                "len(sxtools.sxglobals.settings.shapeArray)-1],"
                "sxtools.sxglobals.layers.getSelectedLayer())\n"
                "maya.cmds.text("
                "'layerBlendModeLabel',"
                "edit=True,"
                "label=str(sxtools.sxglobals.layers.getSelectedLayer())"
                "+' Blend Mode:')\n"
                "maya.cmds.text("
                "'layerOpacityLabel',"
                "edit=True,"
                "label=str(sxtools.sxglobals.layers.getSelectedLayer())"
                "+' Opacity:')\n"
                "maya.cmds.text("
                "'layerColorLabel',"
                "edit=True,"
                "label=str(sxtools.sxglobals.layers.getSelectedLayer())"
                "+' Colors:')"),
            doubleClickCommand=(
                "sxtools.sxglobals.layers.toggleLayer("
                "sxtools.sxglobals.layers.getSelectedLayer())\n"
                "maya.cmds.shaderfx(sfxnode='SXShader', update=True)"))

    def refreshSelectedItem(self):
        selectedColorSet = str(
            maya.cmds.polyColorSet(
                sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1],
                query=True,
                currentColorSet=True)[0])
        if selectedColorSet not in sxglobals.settings.project['LayerData'].keys():
            maya.cmds.polyColorSet(
                sxglobals.settings.shapeArray,
                edit=True,
                currentColorSet=True,
                colorSet='layer1')
            selectedColorSet = 'layer1'
        maya.cmds.textScrollList(
            'layerList',
            edit=True,
            selectIndexedItem=sxglobals.settings.project['LayerData'][
                selectedColorSet][0])

        maya.cmds.text(
            'layerBlendModeLabel',
            edit=True, label=str(sxglobals.layers.getSelectedLayer()) + ' Blend Mode:')
        maya.cmds.text(
            'layerColorLabel',
            edit=True, label=str(sxglobals.layers.getSelectedLayer()) + ' Colors:')
        maya.cmds.text(
            'layerOpacityLabel',
            edit=True, label=str(sxglobals.layers.getSelectedLayer()) + ' Opacity:')

    def sortLayers(self, layers):
        sortedLayers = []
        if layers is not None:
            for ref in sxglobals.settings.refArray:
                if ref in layers:
                    sortedLayers.append(ref)
        return sortedLayers

    def verifyLayerState(self, layer):
        object = sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1]
        selectionList = OM.MSelectionList()
        selectionList.add(sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1])
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        layerColors = OM.MColorArray()
        layerColors = MFnMesh.getFaceVertexColors(colorSet=layer)

        # States: visibility, mask, adjustment
        state = [False, False, False]
        state[0] = (bool(maya.cmds.getAttr(str(object) +
                    '.' + str(layer) + 'Visibility')))

        for k in range(len(layerColors)):
            if ((layerColors[k].a > 0) and
               (layerColors[k].a < sxglobals.settings.project['AlphaTolerance'])):
                state[2] = True
            elif ((layerColors[k].a >= sxglobals.settings.project['AlphaTolerance']) and
                  (layerColors[k].a <= 1)):
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

        layerName = sxglobals.settings.project['LayerData'][layer][6]
        itemString = layerName + '\t' + hidden + mask + adj
        return itemString

    # Maps the selected list item in the layerlist UI
    # to the parameters of the pre-vis material
    # and object colorsets
    def getSelectedLayer(self):
        if len(sxglobals.settings.objectArray) == 0:
            return (sxglobals.settings.project['RefNames'][0])

        selectedIndex = maya.cmds.textScrollList(
            'layerList', query=True, selectIndexedItem=True)
        if selectedIndex is None:
            maya.cmds.textScrollList(
                'layerList',
                edit=True,
                selectIndexedItem=1)
            selectedIndex = 1
        else:
            selectedIndex = int(selectedIndex[0])

        # Blend modes are only valid for color layers,
        # not material channels
        if 'layer' not in sxglobals.settings.project['RefNames'][selectedIndex-1]:
            maya.cmds.optionMenu('layerBlendModes', edit=True, enable=False)
        else:
            selected = str(sxglobals.settings.shapeArray[len(sxglobals.settings.shapeArray)-1])
            attr = (
                '.' + sxglobals.settings.project['RefNames'][selectedIndex-1] +
                'BlendMode')
            mode = maya.cmds.getAttr(selected + attr) + 1
            maya.cmds.optionMenu(
                'layerBlendModes',
                edit=True,
                select=mode,
                enable=True)

        return (sxglobals.settings.project['RefNames'][selectedIndex-1])

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
            elif set(refLayers).issubset(testLayers) is False:
                nonStdObjs.append(object)
                empty = False

        if len(nonStdObjs) > 0 and empty is True:
            return 1, nonStdObjs
        elif len(nonStdObjs) > 0 and empty is False:
            return 2, nonStdObjs
        else:
            return 0, None

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
