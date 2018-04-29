import os, bpy, bmesh, uuid, string, re

avastar_loaded = False
try:
    import avastar
    avastar_loaded = True
except ImportError:
    print("Avastar not loaded, some SkunkTools functions not enabled.")
    
bl_info = {
     "name": "Skunk Tools",
     "author": "Tokeli Zabelin",
     "version": (2, 1),
     "blender": (2, 7, 9),
     "location": "3D VIEW > Left Toolbar > Tools",
     "description": "A small collection of tools for SL creation.",
     "wiki_url": "",
     "tracker_url": "https://github.com/Tokeli/skunktools/issues",
     "category": "Object"}
  
def merge_vert_locs(vertex, vertex2, bm, reverse=False):
    if reverse:
        vertex, vertex2 = vertex2, vertex        
    vertex2.co = vertex.co
    
def merge_vert_weights(vertex, vertex2, bm, reverse=False):
    deform = bm.verts.layers.deform.active
    if reverse:
        vertex, vertex2 = vertex2, vertex
    vertex2[deform].clear()
    vertex2[deform] = vertex[deform]

def get_closest_vert(target, verts, delta=0.001):
    last_distance = delta + 1.0
    closest_vert = None
    for v in verts:
        distance = (target.co - v.co).length
        if distance <= delta and distance < last_distance:
            closest_vert = v
            last_distance = distance
    return closest_vert
    
# Function will take each vertice and its match, one at a time.
def act_on_verts_by_dist(obj, delta, function, source=None, **kwargs):
    # Source = same obj if None
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    
    target_verts = [v for v in bm.verts if v.select]
    if source is None:
        source_verts = [v for v in bm.verts if not v.select]
    else:
        source_bm = bmesh.new()
        source_bm.from_mesh(source.data)
        source_bm.verts.ensure_lookup_table()
        source_verts = source_bm.verts
    for target in target_verts:
        closest_vert = get_closest_vert(target, source_verts, delta)
        if closest_vert:
                function(target, closest_vert, bm, **kwargs)
                
    bmesh.update_edit_mesh(obj.data)

# Mini-function!
put_on_layers = lambda x: tuple((i in x) for i in range(20))

def get_layer(obj):
    return next((x for x, i in enumerate(obj.layers) if i == True), 0)
# Based off code by Przemysław Bągard, heavily tweaked.
# https://github.com/przemir/apply_mod_on_shapekey_objs
def apply_mod_on_shapekey_objs(c, modifier_name):
    obj = c.active_object
    mesh = obj.data
    backup_mesh = mesh.copy()
    shapes = []
    objs = [obj]
    # Ensure the object has shape keys.
    if mesh.shape_keys:
        shapes = [o for o in mesh.shape_keys.key_blocks]
    else:
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier_name)
        return
        
    # Duplicate obj for each shape key.
    for i, shape in enumerate(shapes[1:]):
        new_obj = obj.copy()
        new_obj.data = mesh.copy()
        new_obj.animation_data_clear() # ???
        c.scene.objects.link(new_obj)
        objs.append(new_obj)
        c.scene.objects.active = new_obj
        
        # Reverse the list and then delete the shapekeys from the bottom up.
        for x in range(0, len(shapes))[::-1]:
            new_obj.active_shape_key_index = x
            if new_obj.active_shape_key.name != shape.name:
                bpy.ops.object.shape_key_remove()
        # Delete the basis key on our new one.
        new_obj.active_shape_key_index = 0
        bpy.ops.object.shape_key_remove()
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier_name)
        
    # Deselect all objects to join the shapes one-by-one.
    bpy.ops.object.select_all(action="DESELECT")
    c.scene.objects.active = obj
    obj.select = True
    # Remove all shapekeys from our base object.
    # And apply the modifier to it as well.
    obj.active_shape_key_index = 0
    bpy.ops.object.shape_key_remove(all=True)
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier_name)
    # Re-add the Basis shape to our base object.
    bpy.ops.object.shape_key_add(from_mix=False)
    
    # Join each shape to the base object, from top down.
    for i, o in enumerate(objs[1:]):
        o.select = True
        try:
            bpy.ops.object.join_shapes()
        except:
            # Hopefully this will catch vertice mismatches
            # and revert the mesh data.
            print("Could not join shapes, cancelling!")
            bpy.data.objects.remove(o, True)
            obj.data = backup_mesh
            
            return {"CANCELLED"}
            
        bpy.data.objects.remove(o, True)
        keys = mesh.shape_keys.key_blocks
        keys[i+1].name = shapes[i+1].name
        keys[i+1].interpolation = shapes[i+1].interpolation
        keys[i+1].mute = shapes[i+1].mute
        keys[i+1].slider_min = shapes[i+1].slider_min
        keys[i+1].slider_max = shapes[i+1].slider_max
        keys[i+1].value = shapes[i+1].value
        keys[i+1].vertex_group = shapes[i+1].vertex_group
        
    bpy.data.meshes.remove(backup_mesh)
    c.scene.objects.active = obj
    obj.select = True
    return {"FINISHED"}

def add_mats_to_obj(context, obj, amount=8):
    for x in range(0, amount):
        name = "Face "+str(x)
        obj.data.materials.append(bpy.data.materials.get(name))
def set_sl_materials(context, amount=8, obj=None):
        if obj is None:
            for o in context.selected_objects:
                o.data.materials.clear()
                add_mats_to_obj(context, o, amount)
        else:
            obj.data.materials.clear()
            add_mats_to_obj(context, obj, amount)
# ############################################################################
# Panel drawing +++###########################################################
# ############################################################################
class SknkPanel(bpy.types.Panel):
    bl_label = "Skunk Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Tools"
    
    def draw(self, context):
        c = context
        o = c.object
        sp = bpy.context.scene.SknkProp
        layout = self.layout
        
        layout.label(text="SecondLife Faces:")
        row = layout.row(align=True)
        row.operator("sknk.createfaces")
        row.operator("sknk.setfaces")
        row.operator("sknk.assignfaces")
        layout.separator()
        
        box = layout.box()
        box.label(text="Shapekeys And Modifiers")
        col = box.column()
        prop = col.operator("sknk.applyshapes")
        prop = col.operator("sknk.applyshapemod")
        prop = col.operator("sknk.applymods")
        row = box.row()
        row.prop(sp, "apply_copy")
        sub = row.row()
        sub.prop(sp, "apply_copy_layer")
        sub.enabled = sp.apply_copy
        layout.separator()
        
        #################################################################
        #################################################################
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Non-Destructive Remove Doubles")        
        row = col.row(align=True)
        row.prop(sp, "isreversed")
        row.prop(sp, "delta")
        op = col.operator("sknk.weldselected")
        op.is_reversed = sp.isreversed
        op.delta = sp.delta
        op = col.operator("sknk.weightselected")
        op.is_reversed = sp.isreversed
        op.delta = sp.delta
        box.prop(sp, "selected_obj_to_active")
        if sp.selected_obj_to_active:
            if len(c.selected_objects) < 2:
                box.label(text="You do not have two objects selected", icon='ERROR')
        box.enabled = c.object is not None and c.object.mode == 'EDIT'
        #################################################################
        #################################################################
        layout.separator()
        col = layout.column(align=True)
        col.label(text="Data Matching")
        op = col.operator("sknk.shellmatch")
        row = col.row(align=True)
        row.prop(sp, "mainlayer", text="Objects layer")
        row.prop(sp, "physicslayer", text="Physics layer")
        
        row = layout.row(align=True)
        row.operator("sknk.namefix")
        #################################################################
        #################################################################
        # Explicitly check for AnimProps existence in case Avastar is not
        # loaded, will cause AttrError.
        if avastar_loaded and hasattr(o,"AnimProps"):        
            # Only show if the object has Avastar functionality.
            is_arm = o and o.type=='ARMATURE' and "avastar" in o
            
            layout.separator()
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Fancy Avastar Exporter", icon='POSE_DATA')
            col.operator("sknk.export_inc_anim", icon='REC')
            col.operator("sknk.export_anim_frames", icon='KEYTYPE_KEYFRAME_VEC')
            if o.AnimProps.selected_actions:
                # In bulk mode, panic!!
                col.label(text="Exporter is in Bulk Export mode!", icon='ERROR')
            else:
                col.separator()
                has_action = is_arm and o.animation_data and o.animation_data.action
                if has_action:
                    act = o.animation_data.action
                    av_props = act.AnimProps
                    sk_props = act.SknkAnimProp
                    col.label("%s" % act.name, icon='RENDER_ANIMATION')
                    col.separator()
                    split = col.split()
                    subcol = split.column()
                    row = subcol.row(align=True)
                    row.prop(sk_props, "use_repeats", text='Amount = Frames')
                    row = subcol.row(align=True)                    
                    row.label("Amount")
                    if sk_props.use_repeats:
                        amount = sk_props.repeats
                    else:
                        amount = abs(av_props.frame_end - av_props.frame_start)+1
                    row.label(text="%d" % amount)
                    
                    row = subcol.row(align=True)
                    if sk_props.inc_fps:
                        i = av_props.fps
                        t = "%d  (%d)" % (i, i + (sk_props.inc_fps * amount))
                    else:
                        t = "%d" % av_props.fps
                    row.label(text="FPS")
                    row.label(text="%s" % t)
                    
                    row = subcol.row(align=True)
                    if sk_props.inc_startframe:
                        i = av_props.frame_start
                        t = "%d  (%d)" % (i, i + (sk_props.inc_startframe * amount))
                    else:
                        t = "%d" % av_props.frame_start
                    row.label(text="Start Frame")
                    row.label(text="%s" % t)
                    
                    row = subcol.row(align=True)
                    if sk_props.inc_endframe:
                        i = av_props.frame_end
                        t = "%d  (%d)" % (i, i + (sk_props.inc_endframe * amount))
                    else:
                        t = "%d" % av_props.frame_end
                    row.label(text="End Frame")
                    row.label(text="%s" % t)
                    
                    subcol = split.column()
                    subcol.label(text="")
                    row = subcol.row()
                    row.prop(sk_props, "repeats", text="Amount")
                    row.enabled = sk_props.use_repeats
                    subcol.prop(sk_props, "inc_fps")
                    subcol.prop(sk_props, "inc_startframe")
                    subcol.prop(sk_props, "inc_endframe")
                    col.separator()
                    
                    row = box.row(align=True)
                    row.prop(sk_props, "use_custom_name")
                    row = box.row(align=True)
                    row.prop(sk_props, "custom_name", text="", icon='SYNTAX_OFF')
                    row.enabled = sk_props.use_custom_name
                    if sk_props.use_custom_name:
                        row = box.row(align=True)
                        name = ExportModdedAnimOperator.custom_name(act)
                        row.label(name, icon='SYNTAX_ON')
                    
                    split = box.split()
                    subcol = split.column()
                    subcol.label(text="$act=action name")
                    subcol.label(text="$sf=start frame")
                    subcol.label(text="$ef=end frame")
                    subcol = split.column()
                    subcol.label(text="$p=priority")
                    subcol.label(text="$fps=fps")
                    subcol.label(text="$frm=frame amount")
                    subcol = split.column()
                    subcol.label(text="$ein=ease in")
                    subcol.label(text="$eout=ease out")
                    subcol.label(text="$lin=loop in")
                    subcol.label(text="$lout=loop out")
                    
def render_switch_to_shape_key(self, context):
    layout = self.layout
    row = layout.row()
    row.operator("sknk.switchshape", text="Prev Shape", icon="TRIA_UP").dir = 'UP'
    row.operator("sknk.switchshape", text="Next Shape", icon="TRIA_DOWN").dir = 'DOWN'
    row.operator("sknk.switchshape")
# ############################################################################
# Actual operators ###########################################################
# ############################################################################
class MatchObjectsToShells(bpy.types.Operator):
    bl_idname = ("sknk.shellmatch")
    bl_label = "Match Physics Meshes to Objects"
    bl_description = "Match objects to their physics shells"
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects
    
    def execute(self, context):
        c = context
        sp = bpy.context.scene.SknkProp
        main_objects = []
        physics_objects = []
        # Run thru and collect our objects.
        for obj in c.selected_objects:
            if   obj.layers[sp.mainlayer - 1] == True: main_objects.append(obj)
            elif obj.layers[sp.physicslayer - 1] == True: physics_objects.append(obj)

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
    bl_description = "Match datablock name to object name"
    
    @classmethod
    def poll(cls, context):
        for o in context.selected_objects:
            if o and o.select and (o.name != o.data.name):
                return True
        return False
        
    def execute(self, context):
        c = context
        for obj in c.selected_objects:
            obj.data.name = obj.name
        return {"FINISHED"}
    
class ApplyMods(bpy.types.Operator):
    bl_idname = ("sknk.applymods")
    bl_label = "Apply non-Armature Modifiers"
    bl_description = "Applies any modifier not an armature for all selected, to prepare rigged meshes for export"
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.modifiers
        
    def execute(self, context):
        sp = context.scene.SknkProp
        already_active_obj = context.object
        for obj in context.selected_objects:
            if obj.data.shape_keys:
                self.report({'ERROR'}, "{} has shapekeys, cancelling.".format(obj.name))
                return {"CANCELLED"}
            if sp.apply_copy:
                temp_obj = obj.copy()
                temp_obj.data = obj.data.copy()
                temp_obj.animation_data_clear() # ???
                context.scene.objects.link(temp_obj)
                if sp.apply_copy_layer:
                    temp_obj.layers[:] = put_on_layers({get_layer(obj)+1})
                obj.select = False
                obj = temp_obj
                obj.select = True
            context.scene.objects.active = obj
            for modifier in obj.modifiers:
                if modifier.type != "ARMATURE":
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
        context.scene.objects.active = already_active_obj
        return {"FINISHED"}
        
class WeldSelected(bpy.types.Operator):
    bl_idname = ("sknk.weldselected")
    bl_label = "Weld Selected"
    bl_description = "Welds selected verts to unselected within delta distance."
    bl_options = {"REGISTER", "UNDO"}
        
    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode == 'EDIT'
    
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
        c = context
        source = None
        if c.scene.SknkProp.selected_obj_to_active:
            for obj in c.selected_objects:
                if obj is not c.active_object:
                    source = obj
                    break
        act_on_verts_by_dist(
            c.active_object,
            self.delta,
            merge_vert_locs,
            source=source,
            reverse=self.is_reversed)
        return {"FINISHED"}

class TransferWeightsToSelected(bpy.types.Operator):
    bl_idname = ("sknk.weightselected")
    bl_label = "Weights To Selected"
    bl_description = "Transfers weights from closest verts to selected"
    bl_options = {"REGISTER", "UNDO"}
    
    @classmethod
    def poll(cls, context):
        return context.object and context.object.mode == 'EDIT'
        
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
        c = context
        source = None
        if c.scene.SknkProp.selected_obj_to_active:
            for obj in c.selected_objects:
                if obj is not c.active_object:
                    source = obj
                    break
        act_on_verts_by_dist(
            c.active_object,
            self.delta,
            merge_vert_weights,
            source=source,
            reverse=self.is_reversed)
        return {"FINISHED"}
            
class AssignFaces(bpy.types.Operator):
    bl_idname = "sknk.assignfaces"
    bl_label = "Assign Faces"
    bl_description = "Assigns materials to faces by assigned UV texture for selected objects"
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects
        
    def execute(self, context):
        c = context
        for obj in c.selected_objects:
            me = obj.data
            uv_layer = me.uv_textures.active.data
            textures = set([])
            # Go thru all the faces to collect a list of
            # the images they all use.
            for face in uv_layer:
                if face.image is not None:
                    textures.add(face.image.name)
                
            # Sort the list alphabetically and remove duplicates.
            textures = list(set(sorted(textures, key=str.lower)))
            set_sl_materials(context, amount=len(textures), obj=obj)
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
    bl_description = "Applies current shapekeys to selected objects"
    
    @classmethod
    def poll(cls, context):
        for o in context.selected_objects:
            if o.type == 'MESH' and o.data.shape_keys:
                return True
        return False
        
    def execute(self, context):
        sp = context.scene.SknkProp
        for obj in context.selected_objects:
            if(obj.data.shape_keys is not None):
                if sp.apply_copy:
                    temp_obj = obj.copy()
                    temp_obj.data = obj.data.copy()
                    temp_obj.animation_data_clear() # ???
                    context.scene.objects.link(temp_obj)
                    if sp.apply_copy_layer:
                        temp_obj.layers[:] = put_on_layers({get_layer(obj)+1})
                    obj.select = False
                    obj = temp_obj
                    obj.select = True
                    context.scene.objects.active = obj
                obj.shape_key_add(name=str(obj.active_shape_key.name) + "applied", from_mix=True)
                for num, block in enumerate(obj.data.shape_keys.key_blocks):
                        obj.active_shape_key_index = num
                        obj.shape_key_remove(block)
        return {"FINISHED"}
            
class CreateFaces(bpy.types.Operator):
    bl_idname = "sknk.createfaces"
    bl_label = "Create Faces"
    bl_description = "Creates 8 materials to match with SL faces"
    def execute(self, context):
        colors = [
            (1,0,0),(1,0.5,0),(1,1,0),(0,1,0),
            (0,0,1),(0.545,0,1),(1,0,1),(0,1,1)]
        for x in range(0, 8):
            name = "Face "+str(x)
            if(bpy.data.materials.find(name) == -1):
                mat = bpy.data.materials.new(name)
                mat.diffuse_color = colors[x]
                mat.use_fake_user = 1
        return {"FINISHED"}
        
class SetFaces(bpy.types.Operator):
    bl_idname = "sknk.setfaces"
    bl_label = "Add Faces"
    bl_description = "Adds 8 SL faces to selected objects"
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects
        
    def execute(self, context):
        set_sl_materials(context)
        return {"FINISHED"}
        
class SwitchToShapeKey(bpy.types.Operator):
    bl_idname = "sknk.switchshape"
    bl_label = "Switch to selected Shape"
    bl_description = "Switches to selected Shape Key's maximum"
    
    dir = bpy.props.EnumProperty(
        items=(
            ('ACTIVE', 'Active', ""),
            ('UP', 'Up', ""),
            ('DOWN', 'Down', ""),))
            
    @classmethod
    def poll(cls, context):
        o = context.object
        return o.type == 'MESH' and o.data.shape_keys
        
    def execute(self, context):
        obj = context.object
        if obj.active_shape_key is not None:
            blocks = obj.data.shape_keys.key_blocks
            if self.dir == 'UP':
                if obj.active_shape_key_index <= 0:
                    obj.active_shape_key_index = len(blocks) - 1
                else:
                    obj.active_shape_key_index -= 1
            elif self.dir == 'DOWN':                
                if obj.active_shape_key_index >= len(blocks) -1:
                    obj.active_shape_key_index = 0
                else:
                    obj.active_shape_key_index += 1
            for block in obj.data.shape_keys.key_blocks:
                block.value = 0
            obj.active_shape_key.value = 1
        return {"FINISHED"}

    
class ApplyModForShapeKeys(bpy.types.Operator):
    bl_idname = "sknk.applyshapemod"
    bl_label = "Apply Modifier to Shapekeyed Object"
    bl_description = "Apply one modifier to active object, preserving shapekeys. Will not work with 'absolute' keys or with a 'relative key'"
    
    @classmethod
    def poll(cls, context):
        o = context.object
        return o and o.type == 'MESH' and o.modifiers and o.data.shape_keys
    
    def item_list(self, context):
        return [(modifier.name, modifier.name, modifier.name) for modifier in bpy.context.scene.objects.active.modifiers]
 
    my_enum = bpy.props.EnumProperty(name="Modifier name",
        items = item_list)
 
    def execute(self, context):
    
        ob = context.scene.objects.active
        bpy.ops.object.select_all(action='DESELECT')
        context.scene.objects.active = ob
        context.scene.objects.active.select = True
        return apply_mod_on_shapekey_objs(context, self.my_enum)
        
 
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def multiple_replace(string, rep_dict):
    pattern = re.compile("|".join([re.escape(k) for k in rep_dict.keys()]), re.M)
    return pattern.sub(lambda x: str(rep_dict[x.group(0)]), string)
    
class ExportModdedAnimOperator(bpy.types.Operator):
    """Weedle weedle wee"""
    bl_idname = "sknk.export_modded_anim"
    bl_label = "Export Modified Animation"
    
    def custom_name(action):
        # This uses our custom naming instead of Avastar's
        # Which has less substitutions.
        # This implementation also allows multiple substitutions
        # That work with underscores.
        av_props = action.AnimProps
        sk_props = action.SknkAnimProp
        
        mapping = {
            "$act": action.name,
            "$action": action.name,
            "$p": av_props.Priority,
            "$sf": av_props.frame_start,
            "$ef": av_props.frame_end,
            "$fps": av_props.fps,
            "$frm": abs(av_props.frame_end - av_props.frame_start)+1,
            "$frames":abs(av_props.frame_end - av_props.frame_start)+1, # Avastar compat.
            "$ein": av_props.Ease_In,
            "$eout": av_props.Ease_Out,
            "$lin": av_props.Loop_In,
            "$lout": av_props.Loop_Out}
            
        pre_name = sk_props.custom_name
        if pre_name == "":
            pre_name = av_props.Basename
        name = multiple_replace(pre_name, mapping)
        return name
        
    @classmethod
    def poll(cls, context):
        o = context.object
        if not o or not hasattr(o,"AnimProps"):
            return False
        if o.type == 'ARMATURE' and o.AnimProps.selected_actions:
            return False # In Bulk Export mode, might cause black hole.
        return avastar_loaded and o.animation_data and o.animation_data.action
    
    def invoke(self, context, event):
        # We have custom info to send so we have to run the file selector
        # on ourselves instead of the actual exporter.
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
        
class ExportIncrementAnim(ExportModdedAnimOperator):
    """Exports an animation multiple times, incrementing chosen
    attributes each time. Choose a directory to export files
    to."""
    bl_idname = "sknk.export_inc_anim"
    bl_label = "Export Incremented Animation"

    ext = ""
    directory = bpy.props.StringProperty(subtype="DIR_PATH",default="//")
    filter_glob = bpy.props.StringProperty(options={'HIDDEN'})
    
    def execute(self, context):
        o = context.object
        act = o.animation_data.action
        av_props = act.AnimProps
        sk_props = act.SknkAnimProp
    
        fps = av_props.fps
        start = av_props.frame_start
        end = av_props.frame_end
        if sk_props.use_repeats:
            amount = sk_props.repeats
        else:
            amount = abs(av_props.frame_end - av_props.frame_start)+1
        for i in range(1, amount+1):
            # We need the mode from the object's AnimProp to determine
            # the file extension
            mode = o.AnimProps.Mode
            if mode == "bvh" or mode == "anim":
                ext = "."+mode
            else:
                return {'CANCELLED'}
            
            # We use the dir/name functions in Avastar to get our filename
            # With our substitutions in it.
            if not sk_props.use_custom_name:
                _, file = avastar.ButtonExportAnim.get_export_name(o)
            else:
                file = ExportModdedAnimOperator.custom_name(act)
            path = bpy.path.abspath(os.path.join(self.directory, file+ext))
            bpy.ops.avastar.export_single_anim(filepath=path)
            
            # Modify the object's AnimProp data for the next round.
            av_props.fps = fps + (sk_props.inc_fps * i)
            av_props.frame_start = start + (sk_props.inc_startframe * i)
            av_props.frame_end = end + (sk_props.inc_endframe * i)
        av_props.fps = fps
        av_props.frame_start = start
        av_props.frame_end = end
        return {'FINISHED'}

               
class ExportAnimByFrames(ExportModdedAnimOperator):
    """Export a separate animation for each keyframe in the action"""
    bl_idname = "sknk.export_anim_frames"
    bl_label = "Export Each Anim Frame"

    ext = ""
    directory = bpy.props.StringProperty(subtype="DIR_PATH",default="//")
    filter_glob = bpy.props.StringProperty(options={'HIDDEN'})
    
    def execute(self, context):
        o = context.object
        act = o.animation_data.action
        av_props = act.AnimProps
        sk_props = act.SknkAnimProp
    
        start = av_props.frame_start
        end = av_props.frame_end
        if sk_props.use_repeats:
            amount = sk_props.repeats
        else:
            amount = abs(av_props.frame_end - av_props.frame_start)+1
        # Set end frame to be same as start frame.
        # As it exports a single frame each time.
        av_props.frame_end = start
        for i in range(1, amount+1):
            # We need the mode from the object's AnimProp to determine
            # the file extension
            mode = o.AnimProps.Mode
            if mode == "bvh" or mode == "anim":
                ext = "."+mode
            else:
                return {'CANCELLED'}
            
            # We use the dir/name functions in Avastar to get our filename
            # With our substitutions in it.
            if not sk_props.use_custom_name:
                _, file = avastar.ButtonExportAnim.get_export_name(o)
            else:
                file = ExportModdedAnimOperator.custom_name(act)
            path = bpy.path.abspath(os.path.join(self.directory, file+ext))
            bpy.ops.avastar.export_single_anim(filepath=path)
            
            # Modify the object's AnimProp data for the next round.
            av_props.frame_start = start + i
            av_props.frame_end = start + i
        av_props.frame_start = start
        av_props.frame_end = end
        return {'FINISHED'}
# #####################################################################
# Cleanup and startup #################################################

class SknkProp(bpy.types.PropertyGroup):    
    mainlayer = bpy.props.IntProperty(
        name=("SKNK: Main object layer"),
        default=1,
        min=1,
        max=20,
        description=("Layer of normal objects"))
        
    physicslayer = bpy.props.IntProperty(
        name=("SKNK: Physics object layer"),
        default=2,
        min=1,
        max=20,
        description=("Layer of physics shells"))
        
    isreversed = bpy.props.BoolProperty(
        name=("Selected Verts to Unselected"),
        default=True,
        description=("If unchecked, will make unselected verts move to selected instead"))
        
    selected_obj_to_active = bpy.props.BoolProperty(
        name=("Selected Obj to Active"),
        default=False,
        description=("Snap vertices from active object, to selected object, instead of vertices on same mesh"))
        
    apply_copy = bpy.props.BoolProperty(
        name=("Apply to Copy"),
        default=False,
        description=("Create a copy of object to perform actions on"))
        
    apply_copy_layer = bpy.props.BoolProperty(
        name=("Copy to Layer Above"),
        default=True,
        description=("Send copy to the layer above this one"))
        
    delta = bpy.props.FloatProperty(
        name=("Distance"),
        default=0.001,
        min=0.00001,
        precision=4,
        step=1,
        description=("Max distance between matching verts"))
        
class SknkAnimProp(bpy.types.PropertyGroup):
    """
    how many to increment FPS each time
    how many to increment end_frame each time
    """
    inc_fps = bpy.props.IntProperty(
        name="Incr. FPS",
        description="Amount to add to FPS each export",
        default = 0
        )
    use_repeats = bpy.props.BoolProperty(
        name=("Use Repeats"),
        default=False,
        description=("Use repeats instead of frame amount"))
    repeats = bpy.props.IntProperty(
        name="Repeats",
        description="How many iterations to run",
        default = 0
        )
    inc_startframe = bpy.props.IntProperty(
        name="Incr. StartFrame",
        description="Amount to add to StartFrame each export. Automatically adjusts LoopIn",
        default = 0
        )
    inc_endframe = bpy.props.IntProperty(
        name="Incr. EndFrame",
        description="Amount to add to EndFrame each export. Automatically adjusts LoopOut",
        default = 0
        )
    use_custom_name = bpy.props.BoolProperty(
        name=("Use Custom Name"),
        default=False,
        description=("Use custom name instead of Avastar one"))
    custom_name = bpy.props.StringProperty()
                
                
def register():  
    bpy.utils.register_module(__name__)
    bpy.types.DATA_PT_shape_keys.remove(render_switch_to_shape_key)
    bpy.types.DATA_PT_shape_keys.prepend(render_switch_to_shape_key)
    bpy.types.Action.SknkAnimProp = bpy.props.PointerProperty(type = SknkAnimProp)
    bpy.types.Scene.SknkProp = bpy.props.PointerProperty(type = SknkProp)
    
def unregister():
    bpy.types.DATA_PT_shape_keys.remove(render_switch_to_shape_key)
    bpy.utils.unregister_module(__name__)
    del bpy.types.Action.SknkAnimProp
    del bpy.types.Scene.SknkProp
    
if __name__ == "__main__":  
    register()  