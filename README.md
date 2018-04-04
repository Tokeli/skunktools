# skunktools
Heavy WIP.

A Blender addon with a tiny collection of useful features, mainly for aiding SecondLife content creation. Slowly adding new stuff.

Don't know what I'm doing so it's a mess. 8)

### Create Faces ###
Adds 8 materials to the file, named 'Face 0' through 'Face 7', and color-coded. This is for the 8-material limit of SL objects.

### Add Faces ###
This adds the 8 Face materials to all selected objects, removing any materials that are already there.

### Assign Faces ###
If you have added a texture to a face on the mesh using the UV/Image Editor, this will assign a Face material to it. Allows you to quickly prepare meshes that might have a complicated texture setup.

This requires you to be in Blender Render mode (top of the screen), and enable Textured Solid under Shading in the right 3D sidebar.

### Match Names ###
For all selected objects, the name of the object is assigned to the datablock as well. Maybe you just want to keep track of them, but it's mainly important for uploading multiple objects at once, along with their physics, as the uploader will go by datablock name in alphabetical order.

### Match Physics ###
An advanced version of the above. For all selected objects, it will look on the set Physics Layer for a selected object in the same position. If one is found, they're both given a randomly-generated name and assigned the suffix "`_object`" and "`_physics`". Non-matching items will be named ORPHAN.

### Apply Shapekeys ###
This will simply remove all shapekeys from the selection in a way that preserves how they currently look.

### Weld Selected ###
A non-destructive form of remove doubles. In edit-mode, will snap the selected vertices TO the closest unselected one within the Distance.

### Weights to Selected ###
Remove-doubles but for vertex groups. In edit-mode, will transfer all vertex groups from the closest unselected vert, to the closest selected one, within distance.
