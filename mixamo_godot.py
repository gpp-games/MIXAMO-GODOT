# Open Blender in Terminal,
# Save .blend in Working-Directory first!
import bpy
import os
import fnmatch
import io_scene_godot

context = bpy.context
ops = bpy.ops
dat = bpy.data

# Options: Change the flags in Main()
EXPORT_ESCN = True
SAVE_INDIVIDUAL_BLENDS = True # Don't touch this. Has to be True right now.
SAVE_AS_ANIMATION_LIB = False
ADD_ROOT_MOTION = True

# Script Variables:
filepath = bpy.data.filepath
ESCN_OUT_DIR_NAME =  'escn_out'

# Armature and it'sTransforms
ARMATURE_NAME = 'Armature'
armature = None
init_arma_scale = (0, 0, 0)
init_arma_location = (0, 0, 0)
init_arma_rotation = (0, 0, 0)

RM_BONE_NAME = 'RootMotion'
RM_BONE_SIZE = 0.3
HIP_BONE_NAME = 'Hips'

### Script Functions ###
def importFBX(filePath, filename):
    bpy.ops.import_scene.fbx( filepath = filePath + '/' + filename)

def getArmatureAndTransforms():
    armature = bpy.data.objects[ARMATURE_NAME]
    init_arma_scale = (bpy.context.object.scale[0], bpy.context.object.scale[1], bpy.context.object.scale[2])
    init_arma_location = (bpy.context.object.location[0], bpy.context.object.location[1], bpy.context.object.location[2])
    init_arma_rotation = (bpy.context.object.rotation_euler[0], bpy.context.object.rotation_euler[1], bpy.context.object.rotation_euler[2])

def selectAllPoseBones(armature, select = True): # Toggle-Select
    for bone in armature.pose.bones:
        armature.pose.bones[bone.name].bone.select = select

def selectPoseBone(armature, bone_name): # Deselect all Pose-Bones first!
    armature.pose.bones[bone_name].bone.select = True

def selectArmature(armature):
    bpy.ops.object.select_all(action = 'DESELECT')
    armature.select_set(True)

def scale_keyframes(scalar):
    area_type = bpy.context.area.type
    bpy.context.area.type = 'GRAPH_EDITOR'
    bpy.context.space_data.dopesheet.filter_text = "location"
    bpy.context.space_data.pivot_point = 'CURSOR'
    bpy.context.scene.frame_current = 0
    bpy.context.space_data.cursor_position_y = 0
    bpy.ops.graph.select_all(action = 'SELECT')
    bpy.ops.transform.resize(value=(1, scalar, 1), orient_type='GLOBAL',
                            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                            orient_matrix_type='GLOBAL', constraint_axis=(False, True, False),
                            mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH',
                            proportional_size=1, use_proportional_connected=False,
                            use_proportional_projected=False)
    bpy.context.area.type = area_type

def saveBlendfile(filePath, filename):
    bpy.ops.wm.save_mainfile(filepath = filePath + "/" + filename + ".blend")

##############################
### MAIN Function #########
########################
def Main():
    if filepath is '':
        print('Save .blend in working directory first!')
    else:
        # For file in Working-Dir,
        for filename in os.listdir(os.path.dirname(filepath)):
            # if is FBX-File:
            if filename.endswith(".fbx"):
                # Import and Prepare
                importFBX(os.path.dirname(filepath), filename)
                armature = bpy.data.objects[ARMATURE_NAME]
                init_arma_scale = (context.object.scale[0], context.object.scale[1],
                                    context.object.scale[2])

                # Optimize for Godot
                selectArmature(armature)
                ops.object.transform_apply(location=True, rotation=True, scale=True)
                ops.object.mode_set(mode = 'POSE', toggle = False)
                selectAllPoseBones(armature, False)
                armature.pose.bones[HIP_BONE_NAME].bone.select = True
                # Rename Action
                dat.actions[0].name = str(os.path.splitext(filename)[0])
                scale_keyframes(init_arma_scale[0])

                # Add Root Motion
                if ADD_ROOT_MOTION == True:
                    loc_fcurves = { 0 : 'x', 1 : 'z' }
                    rm_bone = None
                    context.area.type = 'VIEW_3D'
                    context.scene.tool_settings.transform_pivot_point = 'CURSOR'

                    # Add the RootMotion-Bone:
                    ops.object.mode_set(mode = 'OBJECT', toggle = False)
                    selectArmature(armature)
                    ops.object.mode_set(mode = 'EDIT', toggle = False)
                    ops.armature.bone_primitive_add(name = RM_BONE_NAME)

                    # Push down the RootMotion bone to .3 scale and store in variable
                    for bone in armature.data.edit_bones:
                        if fnmatch.fnmatchcase(bone.name, RM_BONE_NAME):
                            print(bone)
                            rm_bone = bone
                            bone.head = (0.0, 0.0, 0.0)
                            bone.tail = (0.0, 0.0, 0.3)

                    # Parent the Hip- to RootMotion-Bone
                    for bone in armature.data.edit_bones:
                        if fnmatch.fnmatchcase(bone.name, HIP_BONE_NAME):
                            bone.parent = rm_bone

                    # Copy the X and Y Location F-Curves from Hip-Bone,
                    # on RootMotion-Bone add a Location-Keyframe on Frame 1 and paste the F-Curves:
                    for loc in loc_fcurves:
                        ops.object.mode_set(mode = 'POSE', toggle = False)
                        selectAllPoseBones(armature, False)
                        selectPoseBone(armature, HIP_BONE_NAME)
                        context.area.type = 'GRAPH_EDITOR'
                        context.space_data.pivot_point = 'CURSOR'
                        context.scene.frame_current = 1
                        context.space_data.cursor_position_y = 0
                        context.space_data.dopesheet.filter_text = loc_fcurves[loc] + " location"
                        ops.graph.select_all(action = 'SELECT')
                        ops.graph.copy()
                        selectAllPoseBones(armature, False)
                        selectPoseBone(armature, RM_BONE_NAME)
                        ops.anim.keyframe_insert_menu(type='Location')
                        context.space_data.dopesheet.filter_text = loc_fcurves[loc] + " location"
                        ops.graph.paste()

                    # Delete the Y-Location F-Curve from the RootMotion-Bone:
                    context.space_data.dopesheet.filter_text = "y location"
                    ops.graph.select_all(action = 'SELECT')
                    ops.graph.delete()

                    # Delete X and Z Location from the Hip-Bone
                    selectAllPoseBones(armature, False)
                    selectPoseBone(armature, HIP_BONE_NAME)
                    for loc in loc_fcurves:
                        context.space_data.dopesheet.filter_text = loc_fcurves[loc] + " location"
                        ops.graph.delete()



                # Save Armatures/Animations as individual Blendfiles
                if SAVE_INDIVIDUAL_BLENDS == True:
                    saveBlendfile(os.path.dirname(filepath), str(os.path.splitext(filename)[0]))
                    print("saved .blend!")

                # Export to Godot
                if EXPORT_ESCN == True:
                    if not os.path.isdir(str(os.path.dirname(filepath)) + '/' + ESCN_OUT_DIR_NAME):
                        os.mkdir(str(os.path.dirname(filepath)) + '/' + ESCN_OUT_DIR_NAME)
                        prj_godot = open(str(os.path.dirname(filepath))
                                            + '/' + ESCN_OUT_DIR_NAME + '/' + 'project.godot', 'w')
                    io_scene_godot.export(str(os.path.dirname(filepath))
                                            + '/' + ESCN_OUT_DIR_NAME + '/'
                                            + str(os.path.splitext(filename)[0]) + '.escn')

                # Delete all Objects
                ops.object.mode_set(mode = 'OBJECT', toggle = False)
                ops.object.select_all(action = 'SELECT')
                ops.object.delete()
                # Remove all Armatures
                for arma in dat.armatures:
                    dat.armatures.remove(arma)
                # Remove all Actions
                for a in dat.actions:
                    dat.actions.remove(a)


Main()
