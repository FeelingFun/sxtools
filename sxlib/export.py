# ----------------------------------------------------------------------------
#   SX Tools - Maya vertex painting toolkit
#   (c) 2017-2019  Jani Kahrama / Secret Exit Ltd
#   Released under MIT license
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
#   processObjects()      - the main export function, goes through
#                           the steps of calling the other functions
#
# ----------------------------------------------------------------------------

import maya.cmds
import maya.mel as mel
import maya.api.OpenMaya as OM
import sxglobals


class Export(object):
    def __init__(self):
        return None

    def __del__(self):
        print('SX Tools: Exiting export')

    def initUVs(self, selected, UVSetName):
        maya.cmds.polyUVSet(selected, create=True, uvSet=UVSetName)
        maya.cmds.polyUVSet(selected, currentUVSet=True, uvSet=UVSetName)
        maya.cmds.polyForceUV(selected, uni=True)

        maya.cmds.select(
            maya.cmds.polyListComponentConversion(selected, tf=True))
        maya.cmds.polyMapCut(ch=1)
        maya.cmds.select(
            maya.cmds.polyListComponentConversion(selected, tuv=True))
        maya.cmds.polyEditUV(relative=False, uValue=0, vValue=0)
        sxglobals.core.selectionManager()

    def flattenLayers(self, selected, numLayers):
        if numLayers > 1:
            for i in range(1, numLayers):
                sourceLayer = 'layer' + str(i + 1)
                sxglobals.layers.mergeLayers(
                    selected, sourceLayer, 'layer1', True)

    def dataToUV(self,
                 shape,
                 uSource,
                 vSource,
                 targetUVSet,
                 mode):
        numMasks = sxglobals.settings.project['MaskCount']
        
        selectionList = OM.MSelectionList()
        selectionList.add(shape)
        nodeDagPath = OM.MDagPath()
        nodeDagPath = selectionList.getDagPath(0)
        MFnMesh = OM.MFnMesh(nodeDagPath)

        uColorArray = OM.MColorArray()
        vColorArray = OM.MColorArray()
        uvIdArray = (OM.MIntArray(), OM.MIntArray())
        uArray = OM.MFloatArray()
        vArray = OM.MFloatArray()

        if uSource is not None:
            uColorArray = MFnMesh.getFaceVertexColors(colorSet=uSource)
            lenColorArray = len(uColorArray)
            uArray.setLength(lenColorArray)
        if vSource is not None:
            vColorArray = MFnMesh.getFaceVertexColors(colorSet=vSource)
            lenColorArray = len(vColorArray)
            vArray.setLength(lenColorArray)

        uvIdArray = MFnMesh.getAssignedUVs()

        # mode 1 - layer masks
        if mode == 1:
            axis = str.lower(str(targetUVSet[0]))
            # Iterate through all layers from top to bottom
            # to assign each vertex to correct layer mask.
            for i in range(1, numMasks + 1):
                sourceColorSet = 'layer' + str(i)
                uColorArray = MFnMesh.getFaceVertexColors(
                    colorSet=sourceColorSet)
                lenColorArray = len(uColorArray)
                uArray.setLength(lenColorArray)
                vArray.setLength(lenColorArray)
                if i == 1:
                    for k in range(lenColorArray):
                        uArray[k] = 1
                        vArray[k] = 1
                else:
                    for k in range(lenColorArray):
                        # NOTE: Alpha inadvertedly gets written with
                        # a low non-zero values when using brush tools.
                        # The tolerance threshold helps fix that.
                        if ((uColorArray[k].a >=
                           sxglobals.settings.project['AlphaTolerance']) and
                           (axis == 'u')):
                            uArray[k] = float(i)
                        elif ((uColorArray[k].a >=
                              sxglobals.settings.project['AlphaTolerance']) and
                              (axis == 'v')):
                                vArray[k] = float(i)
        # mode 2 - material channels
        elif mode == 2:
            for k in range(lenColorArray):
                uArray[k] = 0
                vArray[k] = 0
                if uColorArray[k].a > 0:
                    uArray[k] = uColorArray[k].r
                if vColorArray[k].a > 0:
                    vArray[k] = vColorArray[k].r

        # mode 3 - alpha overlays
        elif mode == 3:
            uArray.setLength(lenColorArray)
            vArray.setLength(lenColorArray)
            for k in range(lenColorArray):
                uArray[k] = 0
                vArray[k] = 0
                if uColorArray[k].a > 0:
                    uArray[k] = uColorArray[k].a
                if vColorArray[k].a > 0:
                    vArray[k] = vColorArray[k].a

        MFnMesh.setUVs(uArray, vArray, targetUVSet)
        MFnMesh.assignUVs(uvIdArray[0], uvIdArray[1], uvSet=targetUVSet)

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

            MFnMesh.setUVs(
                uArray1,
                vArray1,
                targetUVSetList[idx][0])
            MFnMesh.assignUVs(
                uvIdArray[0],
                uvIdArray[1],
                uvSet=targetUVSetList[idx][0])
            MFnMesh.setUVs(
                uArray2,
                vArray2,
                targetUVSetList[idx][1])
            MFnMesh.assignUVs(
                uvIdArray[0],
                uvIdArray[1],
                uvSet=targetUVSetList[idx][1])

    # The steps of the mesh export process:
    # 1) Duplicate objects under export folder
    # 2) Rename new objects to match originals but with a suffix
    # 3) Call the mesh processing functions
    # 4) Delete history on the processed meshes.
    # 5) Treat deforming meshes as a special case
    def processObjects(self, selectionArray):
        # Timer for evaluating script performance
        startTime0 = maya.cmds.timerX()

        sourceArray = []
        alphaOverlayArray = [None, None]
        alphaOverlayUVArray = [None, None]
        overlay = []
        overlayUVArray = []
        materials = []
        materialUVArray = []
        exportBlocks = []

        for key, value in sxglobals.settings.project['LayerData'].iteritems():
            # UV channel for palette masks
            if key == 'layer1':
                maskExport = value[2]
            # Material channels
            elif value[5] is True:
                materials.append(key)
                materialUVArray.append(value[2])
            # UV channels for alpha overlays
            elif value[3] != 0:
                if value[2][0] == 'U':
                    alphaOverlayArray[0] = key
                    alphaOverlayUVArray[0] = value[2]
                else:
                    alphaOverlayArray[1] = key
                    alphaOverlayUVArray[1] = value[2]
            # UV channels for overlay
            elif value[4] is True:
                overlay.append(key)
                overlayUVArray.append(value[2])
      
        if (str(alphaOverlayUVArray[0])[1] != str(alphaOverlayUVArray[1])[1]):
            print('SX Tools Error: Two alpha overlays must be assigned'
                  ' to the same UV Set')
            return

        # sort channels into pairs
        for idx, material in enumerate(materials):
            uSource = None
            vSource = None
            uvSet = None
            
            chanTemp = materialUVArray[idx]
            if chanTemp[0] == 'U':
                uSource = material
                vSource = materials[
                    materialUVArray.index('V'+str(chanTemp[1]))]
            else:
                vSource = material
                uSource = materials[
                    materialUVArray.index('U'+str(chanTemp[1]))]

            uvSet = 'UV' + str(chanTemp[1])
            if (uSource, vSource, uvSet) not in exportBlocks:
                exportBlocks.append((uSource, vSource, uvSet))

        numLayers = (
            sxglobals.settings.project['LayerCount'] -
            len(overlay) -
            len(alphaOverlayArray))

        # Clear existing export objects and create if necessary
        if maya.cmds.objExists('_staticExports'):
            maya.cmds.delete('_staticExports')
        maya.cmds.group(empty=True, name='_staticExports')
        maya.cmds.setAttr('_staticExports.outlinerColor', 0.25, 0.75, 0.25)
        maya.cmds.setAttr('_staticExports.useOutlinerColor', True)
        if maya.cmds.objExists('_ignore'):
            maya.cmds.delete('_ignore')
        maya.cmds.group(empty=True, name='_ignore')
        maya.cmds.setAttr('_ignore.outlinerColor', 0.25, 0.75, 0.25)
        maya.cmds.setAttr('_ignore.useOutlinerColor', True)
        rootObjs = maya.cmds.ls(assemblies=True)
        for obj in rootObjs:
            if maya.cmds.attributeQuery('exportMesh', node=obj, exists=True):
                maya.cmds.delete(obj)

        # Find the root nodes of all selected elements
        for selection in selectionArray:
            source = maya.cmds.ls(selection, l=True)[0].split("|")[1]

            if source not in sourceArray:
                sourceArray.append(source)

        # Duplicate all selected objects for export
        # TODO: Handle long names returned by duplicate names in the scene
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
            var = int(sxglobals.layers.getLayerSet(exportShape))
            if var > 0:
                sxglobals.tools.swapLayerSets([exportShape, ], 0)
            for x in xrange(1, var+1):
                variant = maya.cmds.duplicate(
                    exportShape,
                    name=str(exportShape).split('|')[-1]+'_var'+str(x))[0]
                sxglobals.tools.swapLayerSets([variant, ], x)
                varParent = maya.cmds.listRelatives(
                    exportShape, parent=True)[0]
                if ((varParent != '_staticExports') and
                   (maya.cmds.objExists(varParent+'_var'+str(x)) is False)):
                    maya.cmds.group(
                        empty=True,
                        name=varParent+'_var'+str(x),
                        parent='_staticExports')
                    varParent = varParent+'_var'+str(x)
                    maya.cmds.parent(variant, varParent)
                elif ((varParent != '_staticExports') and
                   (maya.cmds.objExists(varParent+'_var'+str(x)))):
                    varParent = varParent+'_var'+str(x)
                    maya.cmds.parent(variant, varParent)

        exportShapeArray = self.getTransforms(
            maya.cmds.listRelatives(
                '_staticExports', ad=True, type='mesh', fullPath=True))

        # Suffix the export objects
        for exportShape in exportShapeArray:
            if maya.cmds.getAttr(str(exportShape) + '.transparency') == 1:
                exportName = str(exportShape).split('|')[-1] + '_transparent'
            elif sxglobals.settings.project['ExportSuffix'] is True:
                exportName = str(exportShape).split('|')[-1] + '_paletted'
            else:
                exportName = str(exportShape).split('|')[-1]
            maya.cmds.rename(exportShape, str(exportName), ignoreShape=True)

        exportShapeArray = self.getTransforms(
            maya.cmds.listRelatives(
                '_staticExports', ad=True, type='mesh', fullPath=True))

        for exportShape in exportShapeArray:
            maya.cmds.setAttr(exportShape + '.outlinerColor', 0.25, 0.75, 0.25)
            maya.cmds.setAttr(exportShape + '.useOutlinerColor', True)
            # Check for existing additional UV sets and delete them,
            # create default UVs to UV0
            indices = maya.cmds.polyUVSet(
                exportShape, q=True, allUVSetsIndices=True)

            for i in indices:
                if i == 0:
                    name = maya.cmds.getAttr(
                        str(exportShape) + '.uvSet[' + str(i) + '].uvSetName')
                    maya.cmds.polyUVSet(
                        exportShape,
                        rename=True,
                        uvSet=name, newUVSet='UV0')
                    maya.cmds.polyUVSet(
                        exportShape,
                        currentUVSet=True, uvSet='UV0')
                    maya.cmds.polyAutoProjection(
                        exportShape,
                        lm=0, pb=0, ibd=1, cm=0, l=3,
                        sc=1, o=0, p=6, ps=0.2, ws=0)

                if i > 0:
                    name = maya.cmds.getAttr(
                        str(maya.cmds.ls(exportName)) +
                        '.uvSet[' + str(i) + '].uvSetName')
                    maya.cmds.polyUVSet(
                        exportShape,
                        delete=True,
                        uvSet=name)

            # Create UV sets
            self.initUVs(exportShape, 'UV1')
            self.initUVs(exportShape, 'UV2')
            self.initUVs(exportShape, 'UV3')
            self.initUVs(exportShape, 'UV4')
            if overlayUVArray is not None:
                for uvSet in overlayUVArray:
                    for uv in uvSet:
                        self.initUVs(exportShape, uv)

            # Bake masks
            maskUV = 'UV' + str(maskExport)[1]
            self.dataToUV(exportShape, None, None, maskUV, 1)

            # Bake material properties to UV channels
            for block in exportBlocks:
                self.dataToUV(
                    exportShape,
                    block[0],
                    block[1],
                    block[2], 2)

            # Bake alpha overlays
            if alphaOverlayArray != [None, None]:
                if str(alphaOverlayUVArray[0])[1] == str(alphaOverlayUVArray[1])[1]:
                    alphaOverlayUV = 'UV' + str(alphaOverlayUVArray[0])[1]
                self.dataToUV(
                    exportShape,
                    alphaOverlayArray[0],
                    alphaOverlayArray[1],
                    alphaOverlayUV, 3)

            # Bake overlays
            if overlay != [None]:
                self.overlayToUV(exportShape, overlay, overlayUVArray)

            # Delete history
            maya.cmds.delete(exportShape, ch=True)

            # Flatten colors to layer1
            self.flattenLayers(exportShape, numLayers)

            # Delete unnecessary color sets (leave only layer1)
            colSets = maya.cmds.polyColorSet(
                exportShape,
                query=True, allColorSets=True)
            for set in colSets:
                if str(set) != 'layer1':
                    maya.cmds.polyColorSet(
                        exportShape,
                        delete=True, colorSet=str(set))

            # Set layer1 visible for userfriendliness
            maya.cmds.polyColorSet(
                exportShape,
                currentColorSet=True, colorSet='layer1')
            maya.cmds.sets(exportShape, e=True, forceElement='SXPBShaderSG')

            # Check for skinned meshes,
            # copy replace processed meshes when appropriate
            if maya.cmds.objExists(str(exportShape).split('|')[-1].split('_var')[0] + '_skinned'):
                skinnedMesh = str(exportShape).split('|')[-1].split('_var')[0] + '_skinned'
                skinTarget = maya.cmds.duplicate(
                    skinnedMesh,
                    rr=True,
                    un=True,
                    name=str(exportShape).split('|')[-1]+'Root')[0]
                maya.cmds.setAttr(skinTarget + '.outlinerColor', 0.25, 0.75, 0.25)
                maya.cmds.setAttr(skinTarget + '.useOutlinerColor', True)
                maya.cmds.editDisplayLayerMembers('exportsLayer', skinTarget)
                maya.cmds.addAttr(
                    skinTarget,
                    ln='exportMesh',
                    at='bool',
                    dv=True)
                maya.cmds.addAttr(
                    skinTarget,
                    ln='staticVertexColors',
                    at='bool',
                    dv=maya.cmds.getAttr(exportShape+'.staticVertexColors'))
                if maya.cmds.attributeQuery('subdivisionLevel', node=skinTarget, exists=True):
                    maya.cmds.setAttr(
                        skinTarget + '.subdivisionLevel',
                        maya.cmds.getAttr(exportShape+'.subdivisionLevel'))
                else:
                    maya.cmds.addAttr(
                        skinTarget,
                        ln='subdivisionLevel',
                        at='byte',
                        min=0,
                        max=5,
                        dv=maya.cmds.getAttr(exportShape+'.subdivisionLevel'))
                maya.cmds.deleteAttr(skinTarget + '.skinnedMesh')
                maya.cmds.sets(skinTarget, e=True, forceElement='SXPBShaderSG')
                # Apply optional smoothing to original
                # for accurate attribute transfer
                # TODO: See if attributes could be transferred
                # to the OrigShape of skinTarget
                if maya.cmds.getAttr(exportShape+'.subdivisionLevel') > 0:
                    sdl = maya.cmds.getAttr(exportShape+'.subdivisionLevel')
                    maya.cmds.setAttr('sxCrease1.creaseLevel', sdl*.25)
                    maya.cmds.setAttr('sxCrease2.creaseLevel', sdl*.5)
                    maya.cmds.setAttr('sxCrease3.creaseLevel', sdl*.75)
                    maya.cmds.setAttr('sxCrease4.creaseLevel', sdl)
                    maya.cmds.polySmooth(
                        exportShape, mth=0, sdt=2, ovb=1,
                        ofb=3, ofc=0, ost=1, ocr=0,
                        dv=maya.cmds.getAttr(exportShape+'.subdivisionLevel'),
                        bnr=1, c=1, kb=1, ksb=1, khe=0,
                        kt=1, kmb=1, suv=1, peh=0,
                        sl=1, dpe=1, ps=0.1, ro=1, ch=0)
                maya.cmds.editDisplayLayerMembers(
                    'exportsLayer', exportShape)
                maya.cmds.hide(exportShape)
                maya.cmds.parent(exportShape, '_ignore')
                maya.cmds.bakePartialHistory(
                    skinTarget,
                    prePostDeformers=True,
                    postSmooth=False)
                maya.cmds.transferAttributes(
                    '|_ignore|'+str(exportShape).split('|')[-1],
                    skinTarget,
                    frontOfChain=True,
                    transferUVs=2,
                    transferColors=2,
                    sampleSpace=4,
                    colorBorders=1)

                # Set the joints on the mesh to be exported to bindPose,
                # move to same root
                skinMeshHistory = maya.cmds.listHistory(skinTarget, pdo=True)
                skinCluster = maya.cmds.ls(skinMeshHistory, type='skinCluster')
                if len(skinCluster) > 0:
                    skinInfluences = maya.cmds.skinCluster(
                        skinCluster[0], query=True, weightedInfluence=True)
                    skinJoints = []
                    for influence in skinInfluences:
                        if maya.cmds.nodeType(influence) == 'joint':
                            skinJoints.append(influence)
                    bindPose = maya.cmds.dagPose(
                        skinJoints[0], query=True, bindPose=True)
                    maya.cmds.dagPose(skinJoints, bindPose, restore=True)
                    maya.cmds.parent(skinJoints[0], skinTarget)
                
                    # Rename the root joint of the mesh to be exported
                    skinnedMeshHistory = maya.cmds.listHistory(
                        skinnedMesh, pdo=True)
                    skinnedCluster = maya.cmds.ls(
                        skinnedMeshHistory, type='skinCluster')
                    skinnedInfluences = maya.cmds.skinCluster(
                        skinnedCluster[0], query=True, weightedInfluence=True)
                    skinnedJoints = []
                    for influence in skinnedInfluences:
                        if maya.cmds.nodeType(influence) == 'joint':
                            skinnedJoints.append(influence)
                    maya.cmds.rename(skinJoints[0], skinnedJoints[0])

                # Apply smoothing if set in export flags
                if maya.cmds.getAttr(skinTarget+'.subdivisionLevel') > 0:
                    sdl = maya.cmds.getAttr(exportShape+'.subdivisionLevel')
                    maya.cmds.setAttr('sxCrease1.creaseLevel', sdl*.25)
                    maya.cmds.setAttr('sxCrease2.creaseLevel', sdl*.5)
                    maya.cmds.setAttr('sxCrease3.creaseLevel', sdl*.75)
                    maya.cmds.setAttr('sxCrease4.creaseLevel', sdl)
                    maya.cmds.polySmooth(
                        skinTarget, mth=0, sdt=2, ovb=1,
                        ofb=3, ofc=0, ost=1, ocr=0,
                        dv=maya.cmds.getAttr(skinTarget+'.subdivisionLevel'),
                        bnr=1, c=1, kb=1, ksb=1, khe=0,
                        kt=1, kmb=1, suv=1, peh=0,
                        sl=1, dpe=1, ps=0.1, ro=1, ch=0)

                maya.cmds.bakePartialHistory(
                    skinTarget,
                    prePostDeformers=True,
                    postSmooth=False)

            # For non-skinned meshes: move to origin, freeze transformations
            else:
                finalList = maya.cmds.listRelatives(
                    '_staticExports', children=True, fullPath=True)
                offsetX = 0
                offsetZ = 0
                offsetDist = sxglobals.settings.project['ExportOffset']
                for final in finalList:
                    if '_skn' not in final:
                        maya.cmds.setAttr(
                            str(final) + '.translate',
                            0, 0, 0, type='double3')
                        maya.cmds.makeIdentity(
                            final, apply=True, t=1, r=1, s=1, n=0, pn=1)
                        maya.cmds.setAttr(
                            str(final) + '.translate',
                            offsetX, 0, offsetZ, type='double3')
                        offsetX += offsetDist
                        if offsetX == offsetDist * 5:
                            offsetX = 0
                            offsetZ += offsetDist

            # Smooth mesh as last step for export
            if maya.cmds.objExists(exportShape):
                if maya.cmds.getAttr(exportShape+'.subdivisionLevel') > 0:
                    sdl = maya.cmds.getAttr(exportShape+'.subdivisionLevel')
                    maya.cmds.setAttr('sxCrease1.creaseLevel', sdl*.25)
                    maya.cmds.setAttr('sxCrease2.creaseLevel', sdl*.5)
                    maya.cmds.setAttr('sxCrease3.creaseLevel', sdl*.75)
                    maya.cmds.setAttr('sxCrease4.creaseLevel', sdl)
                    maya.cmds.polySmooth(
                        exportShape, mth=0, sdt=2, ovb=1,
                        ofb=3, ofc=0, ost=1, ocr=0,
                        dv=maya.cmds.getAttr(exportShape+'.subdivisionLevel'),
                        bnr=1, c=1, kb=1, ksb=1, khe=0,
                        kt=1, kmb=1, suv=1, peh=0,
                        sl=1, dpe=1, ps=0.1, ro=1, ch=0)

                    maya.cmds.delete(exportShape, ch=True)

        totalTime = maya.cmds.timerX(startTime=startTime0)
        print('SX Tools: Total time ' + str(totalTime))
        maya.cmds.select('_staticExports', r=True)
        sxglobals.core.selectionManager()
        maya.cmds.editDisplayLayerMembers(
            'exportsLayer', maya.cmds.ls(sl=True))
        self.viewExported()

    # Writing FBX files to a user-defined folder
    # includes finding the unique file using their fullpath names,
    # then stripping the path to create a clean name for the file.
    def exportObjects(self, exportPath):
        exportArray = maya.cmds.listRelatives(
            '_staticExports', children=True, fullPath=True)
        if exportArray is not None:
            print('SX Tools: Writing static object FBX files')
            for export in exportArray:
                maya.cmds.select(export)
                exportName = str(export).split('|')[-1] + '.fbx'
                if sxglobals.settings.project['ExportSuffix'] and str(export).endswith('_paletted'):
                    exportName = str(str(export)[:-9]).split('|')[-1] + '.fbx'
                exportString = exportPath + exportName
                print(exportString + '\n')
                maya.cmds.file(
                    exportString,
                    force=True,
                    options='v=0',
                    typ='FBX export',
                    pr=True,
                    es=True)

        # The export phase for deforming meshes
        exportArray = []
        axes = ['x', 'y', 'z']
        attrs = ['t', 'r', 's']
        rootObjs = maya.cmds.ls(assemblies=True)
        for obj in rootObjs:
            if maya.cmds.attributeQuery('exportMesh', node=obj, exists=True):
                exportArray.append(obj)
                for axis in axes:
                    for attr in attrs:
                        maya.cmds.setAttr(obj+'.'+attr+axis, lock=False)

        if len(exportArray) > 0:
            print('SX Tools: Writing deforming object FBX files')
            maya.cmds.sets(exportArray, n='deformingExportSet')
            mel.eval('gameFbxExporter;')
            maya.cmds.setAttr(
                'gameExporterPreset1.exportSetIndex', 3)
            maya.cmds.setAttr(
                'gameExporterPreset1.selectionSetName',
                'deformingExportSet',
                type='string')
            maya.cmds.setAttr(
                'gameExporterPreset1.modelFileMode', 2)
            maya.cmds.setAttr(
                'gameExporterPreset1.smoothingGroups', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.smoothMesh', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.splitVertexNormals', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.triangulate', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.tangentsBinormals', 1)
            maya.cmds.setAttr(
                'gameExporterPreset1.skinning', 1)
            maya.cmds.setAttr(
                'gameExporterPreset1.blendshapes', 1)
            maya.cmds.setAttr(
                'gameExporterPreset1.moveToOrigin', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.exportAnimation', 1)
            maya.cmds.setAttr(
                'gameExporterPreset1.inputConnections', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.embedMedia', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.viewInFBXReview', 0)
            maya.cmds.setAttr(
                'gameExporterPreset1.exportPath',
                exportPath,
                type='string')
            maya.cmds.setAttr(
                'gameExporterPreset1.exportFilename',
                '',
                type='string')
            mel.eval('gameExp_DoExport();')
            maya.cmds.deleteUI('gameExporterWindow')

    # After a selection of meshes has been processed for export,
    # the user has a button in the tool UI
    # that allows an isolated view of the results.
    def viewExported(self):
        exportObjs = ['_staticExports', ]
        rootObjs = maya.cmds.ls(assemblies=True)
        for obj in rootObjs:
            if maya.cmds.attributeQuery('exportMesh', node=obj, exists=True):
                exportObjs.append(obj)
        maya.cmds.select(exportObjs)
        maya.cmds.setAttr('exportsLayer.visibility', 1)
        maya.cmds.setAttr('skinMeshLayer.visibility', 0)
        maya.cmds.setAttr('assetsLayer.visibility', 0)
        maya.cmds.displaySmoothness(
            divisionsU=0,
            divisionsV=0,
            pointsWire=4,
            pointsShaded=1,
            polygonObject=1)
        maya.cmds.editDisplayLayerGlobals(cdl='exportsLayer')
        # hacky hack to refresh the layer editor
        maya.cmds.delete(maya.cmds.createDisplayLayer(empty=True))
        mel.eval('FrameSelectedWithoutChildren;')
        mel.eval('fitPanel -selectedNoChildren;')

    # Processed meshes no longer have the pre-vis material,
    # so the tool must present a different UI when any of these are selected.
    def checkExported(self, objects):
        if len(sxglobals.settings.objectArray) > 0:
            for obj in objects:
                root = maya.cmds.ls(obj, l=True)[0].split("|")[1]
                if root == '_staticExports':
                    return True
                elif root == '_ignore':
                    return True
                elif maya.cmds.attributeQuery('exportMesh', node=obj, exists=True):
                    return True
        else:
            return False

    def viewExportedMaterial(self):
        buttonState1 = maya.cmds.radioButtonGrp(
            'exportShadingButtons1', query=True, select=True)
        buttonState2 = maya.cmds.radioButtonGrp(
            'exportShadingButtons2', query=True, select=True)
        buttonState3 = maya.cmds.radioButtonGrp(
            'exportShadingButtons3', query=True, select=True)

        # Composite
        if buttonState1 == 1:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXPBShaderSG')
            maya.cmds.polyOptions(
                activeObjects=True,
                colorMaterialChannel='ambientDiffuse',
                colorShadedDisplay=True)
            mel.eval('DisplayLight;')

        # Albedo
        elif buttonState1 == 2:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData']['layer1'][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', True))

        # Layer Masks
        elif buttonState1 == 3:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData']['layer1'][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Occlusion
        elif buttonState2 == 1:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData']['occlusion'][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Specular
        elif buttonState2 == 2:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData']['specular'][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Transmission
        elif buttonState2 == 3:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData']['transmission'][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Emission
        elif buttonState2 == 4:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData']['emission'][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Alpha Overlay 1
        elif buttonState3 == 1:
            overlay = None
            for key, value in sxglobals.settings.project['LayerData'].iteritems():
                if value[3] == 1:
                    overlay = key
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData'][overlay][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Alpha Overlay 2
        elif buttonState3 == 2:
            overlay = None
            for key, value in sxglobals.settings.project['LayerData'].iteritems():
                if value[3] == 2:
                    overlay = key
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True,
                forceElement='SXExportShaderSG')
            chanID = sxglobals.settings.project['LayerData'][overlay][2]
            chanAxis = str(chanID[0])
            chanIndex = chanID[1]
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_bool=(
                    sxglobals.settings.exportNodeDict['colorBool'],
                    'value', False))

        # Overlay
        elif buttonState3 == 3:
            maya.cmds.sets(
                sxglobals.settings.shapeArray,
                e=True, forceElement='SXExportOverlayShaderSG')

        if (buttonState1 != 1) and (buttonState3 != 3):
            maya.cmds.shaderfx(
                sfxnode='SXExportShader',
                edit_int=(
                    sxglobals.settings.exportNodeDict['uvIndex'],
                    'value', int(chanIndex)))
            if chanAxis == 'U':
                maya.cmds.shaderfx(
                    sfxnode='SXExportShader',
                    edit_bool=(
                        sxglobals.settings.exportNodeDict['uvBool'],
                        'value', True))
            elif chanAxis == 'V':
                maya.cmds.shaderfx(
                    sfxnode='SXExportShader',
                    edit_bool=(
                        sxglobals.settings.exportNodeDict['uvBool'],
                        'value', False))

            maya.cmds.shaderfx(sfxnode='SXExportShader', update=True)

    def setExportPath(self):
        path = str(
            maya.cmds.fileDialog2(
                cap='Select Export Folder', dialogStyle=2, fm=3)[0])
        if path.endswith('/'):
            sxglobals.settings.project['SXToolsExportPath'] = path
        else:
            sxglobals.settings.project['SXToolsExportPath'] = path + '/'
        sxglobals.settings.savePreferences()

    # Converts a selection of Maya shape nodes to their transform nodes
    def getTransforms(self, shapeList, fullPath=False):
        transforms = []
        for node in shapeList:
            if 'transform' != maya.cmds.nodeType(node):
                parent = maya.cmds.listRelatives(
                    node, fullPath=True, parent=True)
                transforms.append(parent[0])
        return transforms

    def stripPrimVars(self, objects):
        attrList = maya.cmds.listAttr(objects[0], ud=True)
        for object in objects:
            for attr in attrList:
                maya.cmds.deleteAttr(object, at=attr)
