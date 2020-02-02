import bpy, uuid, time
import bpy.props as prop

class BackupItem(bpy.types.PropertyGroup):
    time = bpy.props.IntProperty()
    name = bpy.props.StringProperty()
    
class ListBackups(bpy.types.PropertyGroup):
    backups = prop.CollectionProperty(type = BackupItem)
    
class SknkBackupsList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        # We could write some code to decide which icon to use here...
        custom_icon = 'OBJECT_DATAMODE'

        # Make sure your code supports all 3 layout types
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(item.time)
            row.label(item.name)
            
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
        data_copy = o.data.copy()
        data_copy.use_fake_user = True
        data_copy.name = str(uuid.uuid4())[:12]
        new_backup = o.SknkProp.backups.add()
        new_backup.time = int(time.time())
        return{'FINISHED'}

class DeleteBackup(bpy.types.Operator):
    bl_idname = "sknk_backup.delete"
    bl_label = "Delete backup"
    
    @classmethod
    def poll(self, context):
        o = context.active_object
        return o is not None \
            and o.data is not None
            
    def execute(self, c):
        prop = c.object.SknkProp
        meshes = bpy.data.meshes
        meshes.remove(meshes[prop.backups[prop.index].name])
        prop.backups.remove(prop.index)
        return{'FINISHED'}