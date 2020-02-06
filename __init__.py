bl_info = {
     "name": "Skunk Tools",
     "author": "Tokeli Zabelin",
     "version": (2, 4, 2),
     "blender": (2, 7, 9),
     "location": "3D VIEW > Left Toolbar > Tools",
     "description": "A small collection of tools for SL creation.",
     "wiki_url": "",
     "tracker_url": "https://github.com/Tokeli/skunktools/issues",
     "category": "Object"}

avastar_loaded = False
if "bpy" not in locals():
    import bpy
    #from . import backups
    from . import skunktools
    try:
        import avastar
        skunktools.avastar_loaded = True
    except ImportError:
        print("Avastar not loaded, some SkunkTools functions not enabled.")
else:
    import imp
    imp.reload(skunktools)
    #imp.reload(backups)
    try:
        import avastar
        skunktools.avastar_loaded = True
    except ImportError:
        print("Avastar not loaded, some SkunkTools functions not enabled.")
        
         
def register():  
    bpy.utils.register_module(__name__)
    print("Registering outer module!!!")
    skunktools.register()
    
def unregister():
    bpy.utils.unregister_module(__name__)
    skunktools.unregister()
    