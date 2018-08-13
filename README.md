# SX Tools

![Layered Example](/images/sxtools_multichannel.jpg)

SX Tools is an artist toolbox for vertex color painting , OpenSubdiv creasing and game engine exporting in Autodesk Maya 2018. Its main goal is to present Maya’s color sets in a *layer stack* context more common in 2D painting workflows and provide tool actions that simplify face and vertex coloring process. It also provides limited export functionality to bring rich vertex colors to game engines.

The tool is not fully undo-safe and does not play well with construction history, so for best experience, observe the following workflow:

	Model your low-poly control cage ->
	Delete construction history ->	
	Color and crease ->
	Export to game engine

Changing the topology of your model while coloring and creasing is probably fine, but the limitations of not having construction history apply.

## Quick Start
1. Copy sxtools.py and sfx folder to Maya scripts folder
2. Load shelf_SX.mel, start SX Tools by pressing shelf icon
3. Click on empty space
4. Click on ***Set Preferences Location*** and choose a place for your preferences file
5. Shift-click on **Apply Project Defaults** to start with basic configuration
6. Import or load a mesh object
7. Click on object, press **Add Missing Color Sets**
8. Done, start painting vertex colors!

## Caveats
Viewport shading only works on Windows. The tools may still be useful on other platforms.
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

### Set Preferences Location
Allows you to pick a file in which SX Tools saves its preferences. This is useful if you wish to share palettes between computers.

### Load and Apply Preferences
If you copy a prefs file from another computer, pick it with the Set Location function, and then apply the settings with this.

### Alpha-to-mask limit
Controls the threshold between a Mask layer and an Adjustment layer. More on that later.

### Smoothing iterations
Sets the number of times the exported mesh is subdivided.

### Export preview grid spacing
Is the distance between all export objects when previewed. The objects are laid out in a grid.

Albedo colors are flattened, but the coverage masks of each layer are exported. This allows palette management in the game engine.

Once you’ve made your selections, press **Apply Project Defaults** to get started.
Shift-clicking the button starts with built-in default settings.

Creating project defaults may take a few seconds, as the tool generates custom shaders according to the channel and layer selections.
The tool also by default disables color management, enables AA, smooth wireframes and transparency depth peeling.

## Assigning Layer Sets
Import or create polygon mesh objects while SX Tools is running. A window will pop up that allows you to add the project-defined set of layers to the object (or objects). Selecting an object with the default set of layers will bring up the main tool window.


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
Is similar to popular 2D paint programs:

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
Allows the user to pick an existing layer color as both the **Apply Color** and **Paint Vertex Tool** active color.

### The layer opacity slider
Always displays the maximum opacity value found in a layer. Layers may still have other values below the max. Dragging the slider directly manipulates the alpha values of the components in the layer. This means that if the slider is dragged to 0, any variance in the values is lost - dragging the slider back up will set all component alpha values to the same constant. Alpha variance is preserved when the slider is otherwise adjusted.

### Merge Layer Up button
Does exactly that. Blend modes are respected.

### Select Layer Mask
Allows for new colors to be applied only to the currently masked areas. The selection is made as Face Vertex component type.
Shift-clicking will provide inverted selection.

### Clear Layer
Sets a layer to default value. If components are selected, only clears the selected components.
Shift-clicking will clear ALL layers.

*Mask layer vs. Adjustment layer*
A typical layer has fully opaque components that mask the elements below. These are marked with (M).
When layer opacity is below the ‘Alpha-to-mask limit’ specified in the project defaults, the layer is marked as an Adjustment layer (A). When exported, Adjustment layers only contribute their color to the final vertex color, but their alpha is discarded from any masks.


## The Tool List

### Apply Color
Applies selected color to selected layer or components. The tool respects layer opacity value and writes values only at the max opacity value of the layer. In case of an empty layer, writes with full opacity.

### Gradient Fill
Allows for a custom ramp texture to be applied to the object or objects. Different modes are gradient along XYZ, remapping an existing layer’s luminance to a gradient, or applying a ramp according to the curvature of the mesh.

### Color Noise
At value 1 creates noise between 0 and 1, so typically values below 0.1 will yield subtle results.

### Bake Occlusion
This section shows up only if Mental Ray for Maya or Arnold is installed.
Mental Ray for Maya can be downloaded from:
http://www.nvidia.com/object/download-mental-ray.html

Mental Ray provides a straight-to-vertex occlusion baking, while the Arnold implementation bakes occlusion to a texture and reads that back to vertex colors. Using Mental Ray is recommended.

With Mental Ray, SX Tools bakes both the self-occlusion-only and everything-occludes-everything passes, and presents a slider for blending between the two.

![Occlusion Blending Example](/images/AOblend.gif)

By default, each selected object is rendered separately, with an optional groundplane occluder.
With Arnold, Shift-clicking the bake button will allow objects to occlude each other.

### Apply Master Palette
![Master Palette Example](/images/sxtools_palettevariations.jpg)
Sets the first five layers of the object to the selected palette.
For palettes, check out:
https://color.adobe.com/explore/

### Swap Layers
Swaps two layers and their blend modes.

### Copy Layer
Copies the contents and the blend mode of a layer to another layer.

### Assign to Crease Set
The tool supports a workflow where creasing is limited to five values. This section provides quick creasing assignment buttons. 

## Exporting
Press the button to generate export objects. The tool will automatically lay them out in a grid, and allows for the exported data channels to be viewed in the viewport.

Export objects are by default marked with the suffix
`_paletted`
If layer1 opacity is below 1, the object is instead marked with the suffix
`_transparency`

Export objects can be written out to a selected folder in fbx format. Optionally the suffix can be disabled.

## SX Tools Components

The following nodes and attributes are created by the project setup phase:
* preferences file in a user-selected location
* sxCreaseSet0-4
* sxVertexBakeSet (when occlusion is baked)
* Maya OptionVars starting with ‘SXTools’
* defaultSXDirectionalLight, defaultSXAmbientLight
* ‘SXRamp’ and ‘SXAlphaRamp’ ramp nodes for Gradient Tool
* ‘SXShader’ , ‘SXExportShader’ and ‘SXPBShader’ materials with their respective shading groups 

To remove all optionVars created by SX Tools:
`sxtools.resetSXTools()` in Maya's scripting window


(c) 2017-2018 Jani Kahrama / Secret Exit Ltd


# Acknowledgments

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
