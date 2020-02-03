import os, bpy, bmesh, uuid, string, re, time, mathutils
from . ago import human

avastar_loaded = False

def merge_vert_locs(vertex, vertex2, bm, source=None, reverse=False):
    if reverse:
        vertex, vertex2 = vertex2, vertex        
    #vertex2.co = vertex.co
    vertex.co = vertex2.co

# Vertex on target, vertex2 on source.
def merge_vert_weights(vertex, vertex2, bm, source=None, reverse=False):
    target_deform = bm.verts.layers.deform.active
    if source is not None:
        src_deform = source.verts.layers.deform.active
    else:
        src_deform = target_deform
    
    if reverse:
        vertex2[src_deform].clear()
        vertex2[src_deform] = vertex[target_deform]
    else:
        vertex[target_deform].clear()
        vertex[target_deform] = vertex2[src_deform]

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
    l_source = mathutils.Vector((0, 0, 0))
    o_source = mathutils.Vector((0, 0, 0))
    if source:
        l_source = source.location.copy()
        o_source = obj.location.copy()
        bpy.ops.object.mode_set(mode='OBJECT')   
        # Set the source and obj origin to 0.
        l_source = source.location.copy()
        o_source = obj.location.copy()
        source.data.transform(mathutils.Matrix.Translation(+l_source))
        source.matrix_world.translation -= l_source
        obj.data.transform(mathutils.Matrix.Translation(+o_source))
        obj.matrix_world.translation -= o_source  
        bpy.ops.object.mode_set(mode='EDIT')
    
    success = 0
    bm = bmesh.from_edit_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    source_bm = None
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
                function(target, closest_vert, bm, source_bm, **kwargs)
                success += 1
    print("Targeted {} verts to {} verts, {} found".format(len(target_verts), len(source_verts), success))
    bmesh.update_edit_mesh(obj.data)
    bm.free()
    if source_bm:
        source_bm.free()
        
    # Force freeing of free'd bmesh to prevent crash
    bpy.ops.object.mode_set(mode='OBJECT')    
    bpy.ops.object.mode_set(mode='EDIT')

    if source:
        #Put the sources back.
        bpy.ops.object.mode_set(mode='OBJECT')
        source.data.transform(mathutils.Matrix.Translation(-l_source))
        source.matrix_world.translation += l_source
        obj.data.transform(mathutils.Matrix.Translation(-o_source))
        obj.matrix_world.translation += o_source 
        bpy.ops.object.mode_set(mode='EDIT')

# Mini-function!
put_on_layers = lambda x: tuple((i in x) for i in range(20))

def get_layer(obj):
    return next((x for x, i in enumerate(obj.layers) if i == True), 0)
# Based off code by Przemysław Bągard, heavily tweaked.
# https://github.com/przemir/apply_mod_on_shapekey_objs

class Key():
    def __init__(self, key):
        self.name = key.name
        self.interpolation = key.interpolation
        self.mute = key.mute
        self.slider_min = key.slider_min
        self.slider_max = key.slider_max
        self.value = key.value
    


def apply_mod_on_shapekey_objs(obj, modifier_name):
    c = bpy.context
    mesh = obj.data
    backup_mesh = mesh.copy()
    shapes = {}
    objs = []
    # Ensure the object has shape keys.
    if mesh.shape_keys:
        for s in mesh.shape_keys.key_blocks:
            if s.name != "Basis":
                shapes.update({s.name: Key(s)})
    else:
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=modifier_name)
        print("No keys!")
        return
        
    # Duplicate obj for each shape key.
    # Go thru and set only the correct shape to active
    # Then remove all other shapes, then remove THAT shape as the basis
    # Leaving a clean mesh to apply that one modifier to.
    
    for name in shapes:
        print("Running {}".format(name))
        new_obj = obj.copy()
        new_obj.name = name
        new_obj.data = obj.data.copy()
        c.scene.objects.link(new_obj)
        objs.append(new_obj)
        c.scene.objects.active = new_obj
        blocks = new_obj.data.shape_keys.key_blocks
        for s in new_obj.data.shape_keys.key_blocks:
            if s.name == name:
                s.value = s.slider_max
            else:
                s.value = 0
        mix_name = new_obj.active_shape_key.name + "_applied"
        new_obj.shape_key_add(name=mix_name, from_mix=True)
        
        for num, block in enumerate(new_obj.data.shape_keys.key_blocks):
                if block.name != mix_name:
                    new_obj.shape_key_remove(block)
        new_obj.shape_key_remove(new_obj.data.shape_keys.key_blocks[mix_name])
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
    keys = mesh.shape_keys.key_blocks
    print("-"*90)
    print("--- Running: "+obj.name+" "*50)
    print("-"*90)
    for o in objs:
        print("Joining: {}...".format(o.name))
        o.select = True
        try:
            bpy.ops.object.join_shapes()
        except:
            # Hopefully this will catch vertice mismatches
            # and revert the mesh data.
            print("Could not join shapes, cancelling!")
            for oo in objs:
                bpy.data.objects.remove(oo, True)
            obj.data = backup_mesh
            
            return {"CANCELLED"}
        print("Shape keys now:")
        print([o.name for o in obj.data.shape_keys.key_blocks])
        s = shapes[o.name]
        #obj.shape_key_add(s.name)
        k = obj.data.shape_keys.key_blocks[o.name]
        k.interpolation = s.interpolation
        k.mute = s.mute
        k.slider_min = s.slider_min
        k.slider_max = s.slider_max
        k.value = s.value
        print("TO: {} | FROM: {}".format(k, s.name))
        print("Joined {} - {} / {} <{} | {}> = {} ".format(
            k.name,
            k.interpolation,
            k.mute,
            k.slider_min,
            k.slider_max,
            k.value))
        #print("{} - {}".format(keys[i+1].vertex_group,shapes[i+1].vertex_group))
        #if str(shapes[i+1].vertex_group) is not None:
        #    keys[i+1].vertex_group = str(shapes[i+1].vertex_group)
        #keys[i+1].vertex_group = shapes[i+1].vertex_group.encode("ascii", "ignore").decode("utf8")
        bpy.data.objects.remove(o, True)
        
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
        
        layout.label(text="SecondLife Faces:", icon='FACESEL_HLT')
        row = layout.row(align=True)
        row.operator("sknk.createfaces")
        row.operator("sknk.setfaces")
        row.operator("sknk.assignfaces")
        layout.separator()
        
        layout.label(text="Physics Triangles:", icon='OUTLINER_DATA_MESH')
        row = layout.row(align=True)
        row.operator("sknk.degenerates")
        layout.label(text="This triangulates your mesh! Use a copy!", icon='ERROR')
        layout.separator()
        
        box = layout.box()
        box.label(text="Shapekeys And Modifiers:", icon='MODIFIER')
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
        col.label(text="Non-Destructive Remove Doubles:", icon='SNAP_ON')        
        row = col.row(align=True)
        #row.prop(sp, "isreversed")
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
        col.label(text="Data Matching:", icon='OBJECT_DATAMODE')
        op = col.operator("sknk.shellmatch")
        row = col.row(align=True)
        row.prop(sp, "match_delta")
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
            col.label(text="Fancy Avastar Exporter:", icon='POSE_DATA')
            col.operator("sknk.export_inc_anim", icon='REC')
            col.operator("sknk.export_anim_frames", icon='SPACE2')
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
                    subcol.label(text="$fn=frame name")
                    subcol = split.column()
                    subcol.label(text="$ein=ease in")
                    subcol.label(text="$eout=ease out")
                    subcol.label(text="$lin=loop in")
                    subcol.label(text="$lout=loop out")
                    box.separator()
                    #
                    row = box.row()
                    row.template_list("SknkFrameNamesList", "", sk_props, "frame_names", sk_props, "frame_names_index")
                    col = row.column()
                    subcol = col.column(align=True)
                    subcol.operator("sknk_frame_names.copy", text="", icon = 'COPYDOWN')
                    subcol.operator("sknk_frame_names.paste", text="", icon = 'PASTEDOWN')
                    subcol.separator()
                    subcol.separator()
                    subcol.operator("sknk_frame_names.create", text="",  icon = 'ZOOMIN').dir = 'THIS'
                    subcol.operator("sknk_frame_names.create", text="",  icon = 'PLUS').dir = 'NEXT'
                    subcol.separator()
                    subcol.operator("sknk_frame_names.delete", text="",  icon = 'ZOOMOUT')
                    
                    col = box.column()
                    row = col.row(align=True)
                    row.alignment = 'RIGHT'
                    row.operator("screen.keyframe_jump", text="", icon = 'BACK').next = False
                    row.operator("screen.keyframe_jump", text="", icon = 'FORWARD').next = True
                    
                    
        ####################
        # Backup list
        ####################
        layout.separator()
        row = layout.row()
        try:
            row.label("Mesh Backups:", icon='HELP')
            row = layout.row()
            row.template_list("SknkBackupsList", "", o.SknkProp, "backups", o.SknkProp, "index")
            col = row.column()
            subcol = col.column(align=True)
            subcol.operator('sknk_backup.create', text="", icon="ZOOMIN")
            subcol.operator('sknk_backup.delete', text="", icon="ZOOMOUT")
            row = layout.row()
            row.label(o.data.name)
            row = layout.row()
            if o.SknkProp.index > 0:
                row.operator("sknk_backup.apply", text="Apply", icon='SAVE_AS')
                row = layout.row()
                row.label(text="Backup is being previewed!", icon='ERROR')
        except AttributeError:
            pass
def render_switch_to_shape_key(self, context):
    layout = self.layout
    row = layout.row()
    row.operator("sknk.switchshape", text="Prev Shape", icon="TRIA_UP").dir = 'UP'
    row.operator("sknk.switchshape", text="Next Shape", icon="TRIA_DOWN").dir = 'DOWN'
    row.operator("sknk.switchshape")
# ############################################################################
# Actual operators ###########################################################
# ############################################################################

def get_first_layer(obj):
    for x in range(20):
        if obj.layers[x] == True:
            return x
    return 0
class MatchObjectsToShells(bpy.types.Operator):
    bl_idname = ("sknk.shellmatch")
    bl_label = "Match Physics Meshes to Objects"
    bl_description = "Match objects to their physics meshes"
    
    @classmethod
    def poll(cls, context):
        return context.selected_objects
    
    def execute(self, context):
        c = context
        sp = bpy.context.scene.SknkProp
        
        for obj in c.selected_objects:
            prefix = str(uuid.uuid4())[:8]
            for target in c.selected_objects:
                if target is not obj:
                    # Will be true if they're not on the same layer
                    target_layer = get_first_layer(target)
                    obj_layer = get_first_layer(obj)
                    if target_layer != obj_layer:
                        loc_delta = (obj.location - target.location).length
                        scale_delta = (obj.dimensions - target.dimensions).length
                        if loc_delta <= sp.match_delta and scale_delta <= sp.match_delta:
                            target.name = "{}_{}".format(prefix, target_layer)
                            obj.name = "{}_{}".format(prefix, obj_layer)
                            target.data.name = target.name
                            obj.data.name = obj.name
                            target.select = False
                            obj.select = False
        return {"FINISHED"}
        
        # main_objects = []
        # physics_objects = []
        # # Run thru and collect our objects.
        # for obj in c.selected_objects:
            # if   obj.layers[sp.mainlayer - 1] == True: main_objects.append(obj)
            # elif obj.layers[sp.physicslayer - 1] == True: physics_objects.append(obj)
        # print("{} objects and {} physics selected".format(len(main_objects), len(physics_objects)))
        # # Generate a short UUID each time so we don't get "Object.001" issues
        # # with non-selected objects.
        # prefix = str(uuid.uuid4())[:5]
        # failures = 0
        # for num, obj in enumerate(main_objects):
            # match = False
            
            # for needle in physics_objects:        
                # loc_delta = (obj.location - needle.location).length
                # scale_delta = (obj.dimensions - needle.dimensions).length
                
                # # Floats are fuzzy. Use loc/scale both to guesstimate matching.
                # if loc_delta <= 0.01 and scale_delta <= 0.01:            
                    # # This object matches
                    # needle.name = prefix+"_"+str(num)+"_physics"
                    # needle.data.name = needle.name
                    # match = True
                    # needle.select = False
                    # obj.select = False
                    # break
            # obj.name = (prefix if match == True else "ORPHAN")+"_"+str(num)+"_object"
            # if not match:
                # failures += 1
            # obj.data.name = obj.name
        # print("{} orphans remaining".format(failures))
        # return {"FINISHED"}
        
class NameFix(bpy.types.Operator):
    bl_idname = ("sknk.namefix")
    bl_label = "Match Names to Meshes"
    bl_description = "Match mesh name to object name"
    
    @classmethod
    def poll(cls, context):
        for o in context.selected_objects:
            if o is not None and o.type == 'MESH':
                if o.select and (o.name != o.data.name):
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
        src = None
        if c.scene.SknkProp.selected_obj_to_active:
            for obj in c.selected_objects:
                if obj != c.active_object:
                    src = obj
                    break
        act_on_verts_by_dist(
            c.active_object,
            self.delta,
            merge_vert_locs,
            source=src,
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
        src = None
        if c.scene.SknkProp.selected_obj_to_active:
            for obj in c.selected_objects:
                if obj != c.active_object:
                    src = obj
                    break
        act_on_verts_by_dist(
            c.active_object,
            self.delta,
            merge_vert_weights,
            source=src,
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
            if o.type == 'MESH':
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

class FindDegenerates(bpy.types.Operator):
    bl_idname="sknk.degenerates"
    bl_label = "Find Degenerate Tris"
    bl_description = "Find triangles that are invalid for SecondLife physics meshes"
    
    @classmethod
    def poll(cls, context):
        o = context.active_object
        if o is None:
            return False
        return o.type == 'MESH'
        
    def execute(self, context):
        obj = context.active_object
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        minX = min([v.co[0] for v in bm.verts])
        minY = min([v.co[1] for v in bm.verts])
        minZ = min([v.co[2] for v in bm.verts])

        vMin = mathutils.Vector((minX, minY, minZ))
        maxDim = max(obj.dimensions)
        if maxDim != 0.0:
            for v in bm.verts:
                v.co -= vMin
                v.co /= maxDim
        else:
            for v in bm.verts:
                v.co -= vMin


        def tri_less_than_ten(face):
            e1 = face.edges[0].calc_length()
            e2 = face.edges[1].calc_length()
            e3 = face.edges[2].calc_length()
            a = (e1 <= 10.0 * e2) and (e1 <= 10.0 * e3)
            b = (e2 <= 10.0 * e1) and (e2 <= 10.0 * e3)
            c = (e3 <= 10.0 * e1) and (e3 <= 10.0 * e2)
            if(a and b and c):
                return True
            return False
                
        for face in bm.faces:
            tolerance = 0.00000075
            verts = []
            vecs = []
            verts = [v.co for v in face.verts]
            
            # Code semi-taken from the SecondLife viewer source in llmodel.cpp
            edge1 = (verts[0] - verts[1])
            edge2 = (verts[0] - verts[2])
            edge3 = (verts[2] - verts[1])
               
            # If no edge is 10x longer than any other, weaken the tolerance.
            #if(a and b and c):
            if(tri_less_than_ten(face)):
                #face.select = True
                tolerance *= 0.0001

            # Don't have the first clue what this does.
            cross = edge1.cross(edge2)
            edge1b = (verts[1] - verts[0])
            edge2b = (verts[1] - verts[2])
            crossb = edge1b.cross(edge2b)
            
            if(cross.dot(cross) < tolerance or crossb.dot(crossb) < tolerance):
                face.select = True
            else:
                face.select = False
                
            # Check for zero-size faces.
            if(face.calc_area() == 0.0):
                face.select = True

        # Scale it back up.
        if maxDim != 0.0:
            for v in bm.verts:
                v.co *= maxDim
                v.co += vMin
        else:
            for v in bm.verts:
                v.co += vMin


        bmesh.update_edit_mesh(obj.data)
        bm.free()
        # Force edit mode back and forth because bmesh bug which will crash blender
        # because free() does not actually free until edit mode is left.
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
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
    
        ob = context.active_object
        bpy.ops.object.select_all(action='DESELECT')
        context.scene.objects.active = ob
        context.scene.objects.active.select = True
        return apply_mod_on_shapekey_objs(ob, self.my_enum)
        
 
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

def multiple_replace(string, rep_dict):
    pattern = re.compile("|".join([re.escape(k) for k in rep_dict.keys()]), re.M)
    return pattern.sub(lambda x: str(rep_dict[x.group(0)]), string)
    
class ExportModdedAnimOperator(bpy.types.Operator):
    """Weedle weedle wee"""
    bl_idname = "sknk.export_modded_anim"
    bl_label = "Export Modified Animation"
    
    def get_frame_name(av_props, frame_names):
        try:
            matches = [o.name for o in frame_names if o.frame == av_props.frame_start]
            return matches[0]
        except Exception:
            return ""
            
    def custom_name(action):
        # This uses our custom naming instead of Avastar's
        # Which has less substitutions.
        # This implementation also allows multiple substitutions
        # That work with underscores.
        av_props = action.AnimProps
        sk_props = action.SknkAnimProp
        
        mapping = {
            "$action": action.name,
            "$act": action.name,
            "$p": av_props.Priority,
            "$sf": av_props.frame_start,
            "$ef": av_props.frame_end,
            "$fps": av_props.fps,
            "$frm": abs(av_props.frame_end - av_props.frame_start)+1,
            "$frames":abs(av_props.frame_end - av_props.frame_start)+1, # Avastar compat.
            "$ein": av_props.Ease_In,
            "$eout": av_props.Ease_Out,
            "$lin": av_props.Loop_In,
            "$lout": av_props.Loop_Out,
            "$fn": ExportModdedAnimOperator.get_frame_name(av_props, sk_props.frame_names)}
            
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
# Action Frame Name List ##############################################

def frame_names_index_changed(self, context):
    o = context.object
    prop = o.animation_data.action.SknkAnimProp
    context.scene.frame_set(prop.frame_names[prop.frame_names_index].frame)
    
class FrameNameItem(bpy.types.PropertyGroup):
    frame = bpy.props.IntProperty()
    name = bpy.props.StringProperty()

class CopyFrameNames(bpy.types.Operator):
    bl_idname = "sknk_frame_names.copy"
    bl_label = "Copy FrameNames"
    
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.animation_data is not None
    
    def execute(self, c):
        o = c.object
        c.scene.SknkProp.frame_name_copy_from = c.object.animation_data.action.name
        return{'FINISHED'}
        
class PasteFrameNames(bpy.types.Operator):
    bl_idname = "sknk_frame_names.paste"
    bl_label = "Paste FrameNames"
    
    @classmethod
    def poll(self, c):
        o = c.active_object
        return o is not None \
            and o.animation_data is not None \
            and c.scene.SknkProp.frame_name_copy_from is not None
    
    def execute(self, c):
        o = c.object
        source = c.scene.SknkProp.frame_name_copy_from
        source_act = bpy.data.actions[source]
        s_prop = source_act.SknkAnimProp
        t_prop = c.object.animation_data.action.SknkAnimProp
        
        while len(t_prop.frame_names):
            t_prop.frame_names.remove(len(t_prop.frame_names) - 1)
            
        i = 0
        for o in range(len(s_prop.frame_names)):
            fn = t_prop.frame_names.add()
            fn.frame = s_prop.frame_names[o].frame
            fn.name = s_prop.frame_names[o].name
        return{'FINISHED'}
            
class SknkFrameNamesList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        # We could write some code to decide which icon to use here...
        custom_icon = 'TEXT'

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            split = row.split(percentage=0.3)
            
            split.prop(item, "frame", text="", emboss=False)
            split.prop(item, "name", text="", emboss=True)
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label("", icon = custom_icon)


class AddFrameName(bpy.types.Operator):
    bl_idname = "sknk_frame_names.create"
    bl_label = "Create FrameName"
    
    dir = bpy.props.EnumProperty(
                items=(
                    ('THIS', 'This', ""),
                    ('NEXT', 'Next', ""),))
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.animation_data is not None
    
    def execute(self, c):
        o = c.object
        p = o.animation_data.action.SknkAnimProp
        c_f = c.scene.frame_current
        
        if self.dir == 'NEXT':
            c_f += 1
            
        matches = [f for f in p.frame_names if f.frame == c_f]
        if matches == []:
            # Clear to add one, keep going down
            # until we find a frame lower than us.
            try:
                i = p.frame_names_index
                
                p.frame_names_index = 0
                while p.frame_names[p.frame_names_index].frame <= c_f:
                    p.frame_names_index += 1
            except Exception:
                pass
            new_frame_name = p.frame_names.add()
            new_frame_name.frame = c_f
            new_frame_name.name = "Unnamed"
            p.frame_names.move(len(p.frame_names) - 1, p.frame_names_index)
        c.scene.frame_set(c_f)
        return{'FINISHED'}
        
class RemoveFrameName(bpy.types.Operator):
    bl_idname = "sknk_frame_names.delete"
    bl_label = "Delete FrameName"
    
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.animation_data is not None
            
    def execute(self, c):
        prop = c.object.SknkProp
        meshes = bpy.data.meshes
        
        o = c.object
        p = o.animation_data.action.SknkAnimProp
        p.frame_names.remove(p.frame_names_index)
        if p.frame_names_index >= len(p.frame_names):
            p.frame_names_index -= 1
        return{'FINISHED'}            
# #####################################################################
# Backup Things #######################################################

def backup_index_changed(self, context):
    o = context.object
    prop = o.SknkProp
    
    if prop.index < 0:
        prop.index = 0
        
    o.data = bpy.data.meshes[prop.backups[prop.index].name]
    
class BackupItem(bpy.types.PropertyGroup):
    time = bpy.props.IntProperty()
    name = bpy.props.StringProperty()
    
class SknkBackupsList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        # We could write some code to decide which icon to use here...
        custom_icon = 'OBJECT_DATAMODE'

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            d = bpy.data.meshes[item.name]
            if index == 0:
                name = "Basis"
            else:
                name = human(item.time, abbreviate=True)
            row.label(name)
            row.label(str(len(d.vertices))+"V")
            row.label(str(len(d.materials))+"M")
            row.label(str(len(d.uv_layers))+"UV")
            if d.shape_keys is not None:
                row.label(str(len(d.shape_keys.key_blocks))+"SH")
            else:
                row.label("0SH")
            
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label("", icon = custom_icon)

class CreateBackup(bpy.types.Operator):
    bl_idname = "sknk_backup.create"
    bl_label = "Create backup"
    
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.data is not None
    
    def execute(self, c):
        o = c.object
        p = o.SknkProp
        # If this is the first, store it as the original.
        if len(p.backups) == 0:
            #p.original = o.data.name
            new_backup = o.SknkProp.backups.add()
            new_backup.time = int(time.time())
            new_backup.name = o.data.name
        else:
            data_copy = o.data.copy()
            data_copy.use_fake_user = True
            data_copy.name = str(uuid.uuid4())[:12] + "_BACKUP"
            new_backup = o.SknkProp.backups.add()
            new_backup.time = int(time.time())
            new_backup.name = data_copy.name
        return{'FINISHED'}
        
class ApplyBackup(bpy.types.Operator):
    bl_idname = "sknk_backup.apply"
    bl_label = "Apply backup"
    
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.data is not None \
            and len(o.SknkProp.backups) \
            and o.SknkProp.previewing
            
    def execute(self, c):
        o = c.object
        prop = o.SknkProp
        meshes = bpy.data.meshes
        
        try:
            old_index = prop.index
            old_mesh = meshes[prop.backups[0].name]
            prop.backups.remove(old_index)
            prop.current = -1
            prop.index = 0
            meshes.remove(meshes[old_mesh])
        except:
            return {'CANCELLED'}
        return {'FINISHED'}
   
class DeleteBackup(bpy.types.Operator):
    bl_idname = "sknk_backup.delete"
    bl_label = "Delete backup"
    
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.data is not None \
            and len(o.SknkProp.backups)
            
    def execute(self, c):
        prop = c.object.SknkProp
        meshes = bpy.data.meshes
        
        # If we are previewing the backup, remove and reset to original.
        old_index = prop.index
        old_mesh = prop.backups[old_index].name
        prop.backups.remove(old_index)
        prop.index -= 1
        # Don't delete the actual mesh!!
        if prop.index > 0:
            meshes.remove(meshes[old_mesh])
        return{'FINISHED'}
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
    match_delta =  bpy.props.FloatProperty(
        name=("Match Distance"),
        default=0.015,
        min=0.001,
        precision=3,
        step=1,
        description=("Max distance between matching objects"))
        
    isreversed = bpy.props.BoolProperty(
        name=("Selected Verts to Unselected"),
        default=True,
        description=("If unchecked, will make unselected verts move to selected instead"))
        
    selected_obj_to_active = bpy.props.BoolProperty(
        name=("Snap Active to Selected"),
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
        
    frame_name_copy_from = bpy.props.StringProperty(
        name=("FrameNames From"),
        description=("Action to copy FrameNames from"))
        
class SknkObjProp(bpy.types.PropertyGroup):
    backups = bpy.props.CollectionProperty(type = BackupItem)
    previewing = bpy.props.BoolProperty(
        name = ("Previewing backup"),
        default=False)
    current = bpy.props.IntProperty(
        name = ("Current backup"),
        default = -1)
    index = bpy.props.IntProperty(
        name = ("Current index on list"),
        default = 0,
        update = backup_index_changed)
    original = bpy.props.StringProperty()
    
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
    frame_names = bpy.props.CollectionProperty(type = FrameNameItem)
    frame_names_index = bpy.props.IntProperty(
        name = ("Current index on list"),
        default = 0,
        update = frame_names_index_changed)

def register():  
    bpy.types.DATA_PT_shape_keys.remove(render_switch_to_shape_key)
    bpy.types.DATA_PT_shape_keys.prepend(render_switch_to_shape_key)
    bpy.types.Action.SknkAnimProp = bpy.props.PointerProperty(type = SknkAnimProp)
    bpy.types.Object.SknkProp = bpy.props.PointerProperty(type = SknkObjProp)
    bpy.types.Scene.SknkProp = bpy.props.PointerProperty(type = SknkProp)
    print("Registering inner module!!!!")
    
def unregister():
    bpy.types.DATA_PT_shape_keys.remove(render_switch_to_shape_key)
    del bpy.types.Action.SknkAnimProp
    del bpy.types.Scene.SknkProp
    del bpy.types.Object.SknkProp
    