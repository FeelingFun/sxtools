# SX Tools

![Layered Example](/images/sxtools_multichannel.jpg)

### Overview
SX Tools is an artist toolbox for vertex coloring, OpenSubdiv creasing and game engine exporting in Autodesk Maya 2018-2019. Its main goal is to present Maya’s color sets in a *layer stack* context more common in 2D painting workflows and to provide tools that simplify the face and vertex coloring process.

The additional vertex data created by the tool in Maya is exported via UV channels to bring rich vertex colors to game engines.

The tool is not fully undo-safe and does not play well with construction history, so for best experience, observe the following workflow:

	Model your low-poly control cage ->
	Delete and disable construction history ->	
	Color and crease ->
	Export to game engine

Changing the topology of your model while coloring and creasing is probably fine, but the limitations of not having construction history apply. To avoid most hazards, simply disable construction history when using this tool. Undo still works, but no history nodes are generated. The tool will display pop-ups to encourage this.

## Goals & Purpose
The toolbox is developed to allow 3D artists to create simple and stylized visuals that side-step the "low-poly, limited palette" retro look that is common to many indie titles. The development is focused on a workflow where almost the entire modeling work is to create a simple, elegant control cage that is subdivided as the final export step. All modeling effort and vertex painting work is performed on the control cage. This keeps the source art lightweight, easy to edit, and avoids the hassle involved with texturing. Instead of beveling edges, subdiv creasing should be used whenever possible.

Another goal for SX Tools is to combine the simplicity of low-poly modeling with a physically based rendering workflow. The metallic/smoothness model used in Unity's standard PBR material is adopted by default.

In other common art pipelines a model is sculpted without concern to poly counts, then baked to normal maps that are applied to a re-topo mesh. However these meshes are still fairly complex to manage when skinning, rigging etc. The proposed workflow for this toolbox is designed to side-step many of those mentioned complexities.

### Terminology
| Term | Summary |
| --- | --- |
| Layer | SX Tools uses color sets as layers, and composites them with a custom shader. |
| Overlay (A) | A layer that is exported only as an alpha channel. Useful for palette swaps in the game engine. |
| Overlay (RGBA) | A layer that is exported as four separate UV channels. Useful for adding subtle color variance and detail to paletted layers. |
| Mask | An area of object surface covered by a layer. Each paletted surface component can only belong to a single mask. |
| Layer Stack | A full set of layers on the object, which includes at least one layer, and possible material channels and/or overlays. |
| Layer Set | A parallel layer stack. Up to 10 layer sets can be assigned to a single object. Useful for creating color variants without generating duplicate objects. |

## Quick Start
1. Copy sxtools.py, sxglobals.py, sxlib folder, and sfx folder to your Maya scripts folder
2. Load shelf_SX.mel, start SX Tools by pressing shelf icon
3. Click on empty space
4. Click on ***Set Preferences Location*** and choose a place for your preferences file
5. Shift-click on **Apply Project Defaults** to start with basic configuration
6. Import or load a mesh object
7. Click on object, press **Add Missing Color Sets**
8. Done, start painting vertex colors!
9. (At some point, set a Master Palette location.)

## Caveats
When working on a metallic/smoothness material representation, the viewport shader is only a coarse representation. A more accurate view of the object is shown in the Export Preview mode which uses a PBR material.
**Viewport DX11 Mode on Windows is recommended.**
(Windows -> Settings/Preferences -> Preferences -> Display -> Viewport 2.0 -> Rendering engine: -> DirectX 11
Some tool actions fail if the object has history. The toolbox has a built-in warning for when history is detected.
Some tools are not undo-safe. If proper development pipeline is observed, this should not be too hazardous.

## Installation
Copy scripts to the user script folder:

Windows:

`My Documents\maya\scripts\`


OSX:

`userhome/Library/Preferences/Autodesk/maya/scripts/`

Load shelf_SX.mel into Maya shelves
Start SX Tools by clicking the shelf icon, dock the tool window according to your preference.

## Project Setup
In this screen, the number of albedo layers and material channels to be painted can be selected. Exporting to a game engine requires layer and material data to be processed into the extra UV channels of the object. The screen allows selecting which UV set and axis is used for each data channel.

![Settings Panel](/images/settings.jpg)

### Select Settings File
Allows you to pick a file in which SX Tools saves its preferences. If a file does not exist, just type a filename. This is useful if you wish to share project settings between computers. Shift-clicking on the select button will load settings from the existing file.

### Color layer count
Defines how many RGBA color layers to work with. At least one is needed.

### Mask Export
Sets the UV channel where masks are exported.

### Channels
Choose which material channels to enable, and the UV channels to export them to.

### Overlays
Type the layers you wish to export as overlays. RGBA Overlay needs two full UV sets to export. SX Tool supports two types of overlays: single-channel overlays that are intended for use with the Master Palette, and a full RGBA overlay that is commonly used as a 'last step' color detail layer that adds variance and interest to the paletted layers below.

### Alpha-to-mask limit
Controls the threshold between a Mask layer and an Adjustment layer. More on that later.

### Export preview grid spacing
Is the distance between all export objects when previewed. The objects are laid out in a grid.

### Use export suffix
A simple switch that allows exported meshes to either have the 'paletted' suffix or not. Can be useful if your game identifies meshes according to their suffixes.

### layer 1-10 display name
To help artists remember if specific layers are allocated for particular functions, the names SX Tools uses in its own layer list can be overridden.


Upon export, albedo colors are flattened, but the coverage masks of each layer are exported. This allows palette management in the game engine.

Once you’ve made your selections, press **Apply Project Defaults** to get started.
Shift-clicking the button starts with built-in default settings. A settings file and its location must be set before proceeding.

Creating project defaults may take a few seconds, as the tool generates custom shaders according to the channel and layer selections.
The tool also by default enables color management, enables AA, smooth wireframes, enables OpenSubdiv mesh preview, and transparency depth peeling.

## Assigning Layer Sets
Import or create polygon mesh objects while SX Tools is running. A message will pop up that allows you to add the project-defined set of layers to the object (or objects). Selecting an object with the default set of layers will bring up the main tool window.


# The Main Window

![SX Tools interface](/images/sxtools_UI.jpg)

NOTE: Many buttons have alternate functionality when shift-clicked.

## The Layer View
### Shading Modes
**Final** - A preview composite of all albedo layers and material channels

**Debug** - Displays only the selected layer with transparency, and without lighting

**Alpha** - Displays layer alpha channels in grayscale

### Toggle All Layers
Flips the visibility of all layers from their current state

### Blend mode selection
This is similar to popular 2D paint programs:

**Alpha** - the regular transparency blend

**Add**  - creates an additive (brighter) result

**Multiply** - darkens the layer below

![Blend Mode Demonstration](/images/blendModes.gif)

### The layer list:
* Click to select layers
* Double-click to hide/unhide layer
Layers are marked with:
(M) for Mask layer
(A) for Adjustment layer
(H) for hidden layer
A layer can have both (M) and (A) flags active at the same time, this indicates the layer has opacity values both below and above the adjustment-to-mask limit.

### The layer color palette
Allows the user to pick an existing layer color as both the **Apply Color** tool and **Paint Vertex Colors** tool active color.

### The layer opacity slider
Always displays the maximum opacity value found in a layer. Layers may still have other values below the max. Dragging the slider directly manipulates the alpha values of the components in the layer. This means that if the slider is dragged to 0, any variance in the values is lost - dragging the slider back up will set all component alpha values to the same constant. Alpha variance is preserved when the slider is otherwise adjusted.

### Select Layer Mask
Allows for new colors to be applied only to the currently masked areas. The selection is made as Face Vertex component type.
Shift-clicking will provide inverted selection.

### Clear Layer
Sets a layer to the default value. If components are selected, only clears the selected components.
Shift-clicking will clear ALL layers.

*Mask layer vs. Adjustment layer*
A typical layer has fully opaque components that mask the elements below. These are marked with (M).
When layer opacity is below the ‘Alpha-to-mask limit’ specified in the project defaults, the layer is marked as an Adjustment layer (A). When exported, Adjustment layers only contribute their color to the final vertex color, but their alpha is discarded from any masks.

## Layer View Pop-Up Menu

### Copy / Swap Layers
Right-click on the layer list to get a pop-up menu. From there it is possible to copy the contents and the blend mode of a layer to another layer, or swap two layers and their blend modes.

### Merge Layer Up / Merge Layer Down buttons
Do exactly that. Blend modes are respected.

## The Tool List

### Apply Color (and Noise)
Applies selected color to selected layer or components. The tool respects layer opacity value and writes values only at the max opacity value of the layer. In case of an empty layer, writes with full opacity. If you want to flood a layer with solid color, check the "Overwrite Alpha" checkbox.

Noise can be added with the Noise Intensity slider.

### Gradient Fill
Allows for a custom ramp texture to be applied to the object or objects. Different modes under the "Direction" pull-down menu are gradient along XYZ, remapping an existing layer’s luminance to a gradient, or applying a ramp according to the curvature of the mesh.

### Bake Occlusion
SX Tools has a built-in ambient occlusion renderer.

The presented options for Ray Count, Ray Max Distance, Mesh Offset and Ray Source Offset are only supported by the built-in renderer. To adjust the MR bake settings, edit the sxVertexBakeSet node.

An additional render button appears if Mental Ray for Maya is installed.

The built-in renderer and Mental Ray bake both the self-occlusion-only and everything-occludes-everything passes, and present a slider for blending between the two. Enabling a ground plane for the global pass is optional.

Mental Ray for Maya can be downloaded from:
https://forum.nvidia-arc.com/showthread.php?16656-Mental-Ray-for-Maya-2018-Version-1-2-1-Update
Please note that Mental Ray has been discontinued by NVIDIA, but the plugin is still offered for free, without support.
https://forum.nvidia-arc.com/showthread.php?16431-Withdrawal-of-NVIDIA-Mental-Ray-and-Mental-Ray-plugins-effective-November-20-2017&p=67166#post67166

SX Tool built-in renderer and Mental Ray both provide a straight-to-vertex occlusion baking.

Arnold support has been removed, but can be found in earlier revisions of the project. The Arnold implementation bakes occlusion to a texture and reads that back to vertex colors, which resulted in slower performance and some visual quality issues.

![Occlusion Blending Example](/images/AOblend.gif)

### Apply Master Palette
![Master Palette Example](/images/sxtools_palettevariations.jpg)
The Master Palette is a list of five colors that can be applied to any selected color layers on the object. The default setting is to map colors 1-5 to layers 1-5, but this can be changed in the Master Palette settings. Note that a palette color can be applied to multiple layers! Simply separate the layer names with a comma. Currently the tool does not support overridden display names, so "gradient1" and "gradient2" should be referred to as layer8 and layer9.

The palette is a json file that can be shared among multiple artists working on the same project.
For palettes, check out:
https://color.adobe.com/explore/

### Manage Layer Sets
Create and switch between parallel layer stacks. Allows for creation of color variants that are more extensive than simple Master Palette swaps. Whereas a the Master Palette allows for the object to have color variations, Layer Sets allow for a single object to additionally have multiple layer masks and different material channels. 

### Assign to Crease Set
The tool supports a workflow where creasing is limited to five sets. This section provides quick creasing assignment buttons. Note that the crease set values are **adaptive**, meaning the value of each crease set depends on the subdivision level of the object. This is to provide four different levels of creasing to any subdivision level. By default Maya treats crease values as absolute, and this tends to only work properly on a single (reasonably high or adaptive) subdivision level.

### Create Skinning Mesh
If you wish to use blend shapes and bind the mesh to a skeleton, **do not use deformation tools on the vertex-colored object**. The tool creates a separate mesh for deformations, and merges data from the colored and skinned meshes together for export.

### Export Flags
The Static Vertex Colors flag simply adds a boolean to the object for export. This can be useful if your game supports dynamic palette changes.

Export Subdivision Level also affects the viewport tessellation of the selected object!

## Exporting
Press the button to generate export objects. The tool will automatically lay them out in a grid, and allows for the exported data channels to be viewed in the viewport.

Export objects are by default marked with the suffix
`_paletted`
If layer1 opacity is below 1, the object is instead marked with the suffix
`_transparency`

Export objects can be written out to a selected folder in fbx format. Optionally the suffix can be disabled.

## SX Tools Components

The following files, nodes, and attributes are created by the project setup phase:
* preferences json file in a user-selected location
* palettes json file in a user-selected location
* sxCreaseSet0-4
* sxVertexBakeSet (when occlusion is baked with Mental Ray)
* Maya OptionVars starting with ‘SXTools’
* defaultSXDirectionalLight, defaultSXAmbientLight
* ‘SXRamp’ and ‘SXAlphaRamp’ ramp nodes for Gradient Tool
* ‘SXCreaseRamp’ ramp node for Crease Tool edge auto-selector
* ‘SXShader’ , ‘SXExportShader’, ‘SXExportOverlayShader’ and ‘SXPBShader’ materials with their respective shading groups
* primVars in the shape node of every edited object
* primVars in the transform nodes of objects with export flags
* multiple color sets per every edited object

To remove all optionVars created by SX Tools:
`sxtools.sxglobals.core.resetSXTools()` in Maya's scripting window


(c) 2017-2019 Jani Kahrama / Secret Exit Ltd


# Acknowledgments

Thanks to:
Rory Driscoll for tips on better sampling
Serge Scherbakov for tips on working with iterators

SX Tools builds on the following work:
### sfx
Code for programmatically working with Maya shaderfx nodes

(c) 2015-16 Steve Theodore

https://github.com/theodox/sfx

Available under MIT license.

### Vertex-to-edge curvature calculation method 
Algorithm by Stepan Jirka

http://www.stepanjirka.com/maya-api-curvature-shader/

Integrated into SX Tools under MIT license with permission from the author.
