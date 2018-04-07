import bpy, bmesh, uuid
bl_info = {
     "name": "SKNK Tools",
     "author": "Tokeli Zabelin",
     "version": (1, 2),
     "blender": (2, 7, 9),
     "location": "3D VIEW > Left Toolbar > Tools",
     "description": "A small collection of tools for SL creation.",
     "wiki_url": "",
     "tracker_url": "https://github.com/Tokeli/skunktools/issues",
     "category": "Object"}
       
PREFIX = "Face "
COLORS = [
    (1,0,0),(1,0.5,0),(1,1,0),(0,1,0),
    (0,0,1),(0.545,0,1),(1,0,1),(0,1,1)
]
# This will generate 8 materials for SecondLife faces
# And will use rainbow RGB.
def createSLMaterials():
    for x in range(0, 8):
        name = PREFIX + str(x)
        c = COLORS[x]
        if(bpy.data.materials.find(name) == -1):
            mat = bpy.data.materials.new(name)
            mat.diffuse_color = COLORS[x]
            mat.use_fake_user = 1
#            mat.ambient = 1 # Fullbright?

# This will clear all materials on the selected object
# And give it SL materials.
def setSLMaterials(amount):
    for obj in bpy.context.selected_objects:
        obj.data.materials.clear()
        mats = bpy.data.materials
        for x in range(0, amount):
            name = PREFIX+str(x)
            obj.data.materials.append(mats.get(name))

def mergeVertLocations(vertex, vertex2, bm, reverse=False):
    if reverse:
        vertex, vertex2 = vertex2, vertex        
    vertex2.co = vertex.co
    
def transferVertWeights(vertex, vertex2, bm, reverse=False):
    deform = bm.verts.layers.deform.active
    if reverse:
        vertex, vertex2 = vertex2, vertex
    vertex2[deform].clear()
    vertex2[deform] = vertex[deform]
    
# Function will take each vertice and its match, one at a time.
def performActionOnVertsByDistance(obj, delta, function, **kwargs):
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    selected_verts = [v for v in bm.verts if v.select]
    unselected_verts = [v for v in bm.verts if not v.select]
    
    for selected in selected_verts:
        for unselected in unselected_verts:
            distance = (selected.co - unselected.co).length
            if distance <= delta:
                function(selected, unselected, bm, **kwargs)
                
    bmesh.update_edit_mesh(obj.data)
######################################################
class SknkPanel(bpy.types.Panel):
    bl_label = "Skunk Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Tools"
    
    def draw(self, context):
        c = context
        wm = c.window_manager
        is_mesh = c.object.type == "MESH"
        has_shapes = c.object.data.shape_keys is not None       
        is_edit_mode = c.object and c.object.mode == 'EDIT' 
        layout = self.layout
        
        layout.label(text="Materials:")
        
        col = layout.column(align=True)
        row = col.row(align=True)
        row.operator("sknk.createfaces")
        row.operator("sknk.setfaces")
        row.operator("sknk.assignfaces")
        row.enabled = is_mesh
        
        row = col.row(align=True)
        row.operator("sknk.namefix")
        
        row = col.row(align=True)        
        row.operator("sknk.applyshapes")
        row.enabled = has_shapes
        row = col.row(align=True)
        row.operator("sknk.applymods")
        row.enabled = c.object.modifiers is not None
        layout.separator()
        
        #################################################################
        #################################################################
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(wm, "sknk_isreversed")
        row.prop(wm, "sknk_delta")
        op = col.operator("sknk.weldselected")
        op.is_reversed = wm.sknk_isreversed
        op.delta = wm.sknk_delta
        op = col.operator("sknk.weightselected")
        op.is_reversed = wm.sknk_isreversed
        op.delta = wm.sknk_delta
        col.enabled = is_edit_mode
        
        #################################################################
        #################################################################
        layout.separator()
        col = layout.column(align=True)
        op = col.operator("sknk.shellmatch")
        row = col.row(align=True)
        row.prop(wm, "sknk_mainlayer", text="Objects layer")
        row.prop(wm, "sknk_physicslayer", text="Physics layer")
        
        
# ############################################################################
# Actual operators ###########################################################
# ############################################################################
class MatchObjectsToShells(bpy.types.Operator):
    bl_idname = ("sknk.shellmatch")
    bl_label = "Match Physics"
    bl_description = "Match objects to their physics shells."
    def execute(self, context):
        c = context
        wm = c.window_manager
        main_objects = []
        physics_objects = []
        # Run thru and collect our objects.
        for obj in c.selected_objects:
            if   obj.layers[wm.sknk_mainlayer - 1] == True: main_objects.append(obj)
            elif obj.layers[wm.sknk_physicslayer - 1] == True: physics_objects.append(obj)

        # Generate a short UUID each time so we don't get "Object.001" issues
        # with non-selected objects.
        prefix = str(uuid.uuid4())[:5]
        for num, obj in enumerate(main_objects):
            match = False
            
            for needle in physics_objects:        
                loc_delta = (obj.location - needle.location).length
                scale_delta = (obj.dimensions - needle.dimensions).length
                
                # Floats are fuzzy. Use loc/scale both to guesstimate matching.
                if loc_delta <= 0.002 and scale_delta <= 0.002:            
                    # This object matches
                    needle.name = prefix+"_"+str(num)+"_physics"
                    needle.data.name = needle.name
                    match = True
                    break
            obj.name = (prefix if match == True else "ORPHAN")+"_"+str(num)+"_object"
            obj.data.name = obj.name
        return {"FINISHED"}
        
class NameFix(bpy.types.Operator):
    bl_idname = ("sknk.namefix")
    bl_label = "Match Names"
    bl_description = "Match datablock name to object name."
    
    def execute(self, context):
        c = bpy.context
        for obj in c.selected_objects:
            obj.data.name = obj.name
        return {"FINISHED"}
    
class ApplyMods(bpy.types.Operator):
    bl_idname = ("sknk.applymods")
    bl_label = "Apply non-Armature Modifiers"
    bl_description = "Applies any modifier not an armature for all selected, to prepare rigged meshes for export."
    
    def execute(self, context):
        c = bpy.context
        already_active_obj = c.object
        for obj in c.selected_objects:
            c.scene.objects.active = obj
            for modifier in obj.modifiers:
                if modifier.type != "ARMATURE":
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
        c.scene.objects.active = already_active_obj
        return {"FINISHED"}
        
class WeldSelected(bpy.types.Operator):
    bl_idname = ("sknk.weldselected")
    bl_label = "Weld Selected"
    bl_description = "Welds selected verts to unselected within delta distance."
    bl_options = {"REGISTER", "UNDO"}
    
    # Create a local copy of the sknk_selected_reverse prop here
    # for the redo function to work.
    is_reversed = bpy.props.BoolProperty(
        name=("Selected to Unselected"),
        default=True,
        description=("If unchecked, will make unselected verts move to selected instead"))
    delta = bpy.props.FloatProperty(
        name=("Distance"),
        default=0.001,
        min=0.00001,
        precision=4,
        step=1,
        description=("Max distance between matching verts"))
    
    def execute(self, context):
        c = bpy.context
        performActionOnVertsByDistance(
            c.active_object,
            self.delta,
            mergeVertLocations,
            reverse=self.is_reversed)
        return {"FINISHED"}

class TransferWeightsToSelected(bpy.types.Operator):
    bl_idname = ("sknk.weightselected")
    bl_label = "Weights To Selected"
    bl_description = "Transfers weights from closest verts to selected."
    bl_options = {"REGISTER", "UNDO"}
    
    is_reversed = bpy.props.BoolProperty(
        name=("Selected to Unselected"),
        default=True,
        description=("If unchecked, will make unselected verts move to selected instead"))
    delta = bpy.props.FloatProperty(
        name=("Distance"),
        default=0.001,
        min=0.00001,
        precision=4,
        step=1,
        description=("Max distance between matching verts"))
    
    
    def execute(self, context):
        c = bpy.context
        performActionOnVertsByDistance(
            c.active_object,
            self.delta,
            transferVertWeights,
            reverse=self.is_reversed)
        return {"FINISHED"}
    
class AssignFaces(bpy.types.Operator):
    bl_idname = "sknk.assignfaces"
    bl_label = "Assign Faces"
    bl_description = "Assigns materials to faces by assigned UV texture for selected objects."
    
    def execute(self, context):
        c = bpy.context
        for obj in c.selected_objects:
            me = obj.data
            uv_layer = me.uv_textures.active.data
            #setSLMaterials()
            textures = set([])
            # Go thru all the faces to collect a list of
            # the images they all use.
            for face in uv_layer:
                if face.image is not None:
                    textures.add(face.image.name)
                
            # Sort the list alphabetically and remove duplicates.
            textures = list(set(sorted(textures, key=str.lower)))
            setSLMaterials(len(textures))
            # Go thru the polygons on the object
            for poly in obj.data.polygons:
                img = uv_layer[poly.index].image
                index = 0
                if img is not None:
                    index = textures.index(img.name)
                poly.material_index = index 
        return {"FINISHED"}
            
class ApplyShapes(bpy.types.Operator):
    bl_idname = "sknk.applyshapes"
    bl_label = "Apply Shapekeys"
    bl_description = "Applies current shapekeys to selected objects."
    
    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if(obj.data.shape_keys is not None):
                obj.shape_key_add(name=str(obj.active_shape_key.name) + "applied", from_mix=True)
                for num, block in enumerate(obj.data.shape_keys.key_blocks):
                        obj.active_shape_key_index = num
                        obj.shape_key_remove(block)
        return {"FINISHED"}
            
class CreateFaces(bpy.types.Operator):
    bl_idname = "sknk.createfaces"
    bl_label = "Create Faces"
    bl_description = "Creates 8 materials to match with SL faces."
    def execute(self, context):
        createSLMaterials()
        return {"FINISHED"}
        
class SetFaces(bpy.types.Operator):
    bl_idname = "sknk.setfaces"
    bl_label = "Add Faces"
    bl_description = "Adds 8 SL faces to selected objects."
    
    def execute(self, context):
        setSLMaterials(8)
        return {"FINISHED"}
        
class SwitchToShapeKey(bpy.types.Operator):
    bl_idname = "sknk.switchshape"
    bl_label = "Switch to selected Shape"
    bl_description = "Switches to selected Shape Key's maximum."
    
    def execute(self, context):
        obj = bpy.context.object
        if obj.active_shape_key is not None:
            for block in obj.data.shape_keys.key_blocks:
                block.value = 0
            obj.active_shape_key.value = 1
        return {"FINISHED"}
        
def render_switch_to_shape_key(self, context):
    layout = self.layout
    row = layout.row()
    row.operator("sknk.switchshape")
# #####################################################################
# Cleanup and startup #################################################

def init_properties():
    bpy.types.WindowManager.sknk_mainlayer = bpy.props.IntProperty(
        name=("SKNK: Main object layer"),
        default=1,
        min=1,
        max=20,
        description=("Layer of normal objects"))
        
    bpy.types.WindowManager.sknk_physicslayer = bpy.props.IntProperty(
        name=("SKNK: Physics object layer"),
        default=2,
        min=1,
        max=20,
        description=("Layer of physics shells"))
        
    bpy.types.WindowManager.sknk_isreversed = bpy.props.BoolProperty(
        name=("Selected to Unselected"),
        default=True,
        description=("If unchecked, will make unselected verts move to selected instead"))
    bpy.types.WindowManager.sknk_delta = bpy.props.FloatProperty(
        name=("Distance"),
        default=0.001,
        min=0.00001,
        precision=4,
        step=1,
        description=("Max distance between matching verts"))
        
        
    
        
def clear_properties():
    props = ['sknk_mainlayer', 'sknk_physicslayer', 'sknk_isreversed', 'sknk_delta']
    for p in props:
        if bpy.context.window_manager.get(p) != None:
            del bpy.context.window_manager[p]
        try:
            x = getattr(bpy.types.WindowManager, p)
            del x
        except:
            pass
        
def register():  
    bpy.utils.register_module(__name__)  
    bpy.types.DATA_PT_shape_keys.prepend(render_switch_to_shape_key)
    init_properties()
    
def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.DATA_PT_shape_keys.remove(render_switch_to_shape_key)
    clear_properties()
    
if __name__ == "__main__":  
    register()  