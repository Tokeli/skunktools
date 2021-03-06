# skunktools
A Blender addon with a tiny collection of useful features, mainly for aiding SecondLife content creation. Slowly adding new stuff.
Confirmed working with Blender 2.77+ and Avastar 2.1.0+, but may work with earlier versions.

Don't know what I'm doing so it's a mess. 8)

---

## Installation ##
Click the green button in the upper right that says 'Clone or Download', then 'Download Zip'.

In Blender, File -> Preferences -> Addons -> Install From File, and select the zip-file. Do not unzip it!

---
## Location ##
Most tools are in a new panel in the Tools tab in the 3D View sidebar. (Hit T in 3D view).

---

### Create Faces ###
Adds 8 materials to the file, named 'Face 0' through 'Face 7', and color-coded. This is for the 8-material limit of SL objects.

### Add Faces ###
This adds the 8 Face materials to all selected objects, removing any materials that are already there.

### Assign Faces ###
If you have added a texture to a face on the mesh using the UV/Image Editor, this will assign a Face material to it. Allows you to quickly prepare meshes that might have a complicated texture setup.

This requires you to be in Blender Render mode (top of the screen), and enable Textured Solid under Shading in the right 3D sidebar.

---

### Find Degenerate Tris ###
Specifically for SecondLife, this tries to identify triangles that will prevent your physics mesh from uploading. This requires your object being triangulated, so make a copy and CTRL+T it in edit mode.

Code ported from llfloatermodelpreview.cpp and llmodel.cpp of the Firestorm viewer, but I don't have a clue what I'm doing so it's not a 100% match, but will show a good enough idea.

---

### Paste Transforms ###
In some SecondLife viewers is a copy function in the build panel, to copy pos/loc/rot in a <1, 1, 1> format.

This panel lets you easily copy/paste these from SecondLife to Blender objects.

Due to limitations, you may have to flip into edit mode to make the panel update your clipboard.

---

### Apply Shapekeys ###
This will simply remove all shapekeys from selected objects, preserving how they currently look.

### Apply non-Armature Modifiers ###
This will apply all modifiers on selected objects that aren't an Armature, so they stay rigged.

---

### Non-Destructive Remove Doubles ###
Snaps selected vertices to unselected ones nearby, without removing them. If 'Snap Active to Selected' is on, selected vertices will snap to vertices on one other selected object, and not the same mesh.

The 'weights to selected' function will do the same, except copy weights from the closest unselected vertices.

---

### Export Incremented Animation ###
This is an extra function for the Avastar addon, specifically for SecondLife animations. It lets you export an animation over an over, incrementing the FPS, or start/end frames each time, without manual changes.

You must have an armature selected and it must have an active action for the panel to appear. The settings from the Avastar Animation Export panel are used. Choose an output folder on activation.

### Export Each Anim Frame ###
This is also for Avastar. Export each frame of an action as a separate 1-frame animation, same requirements as above.

---

### Match Names ###
For all selected objects, the name of the object is assigned to the mesh data as well. Maybe you just want to keep track of them, but it's mainly important for uploading multiple objects at once with their physics, as the uploader will go by mesh data name in alphabetical order.

### Match Physics ###
An advanced version of the above. For all selected objects, it will look on the set Physics Layer for a selected object in the same position. If one is found, they're both given a randomly-generated name and assigned the suffix "`_object`" and "`_physics`". Non-matching items will be named ORPHAN.

---