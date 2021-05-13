bl_info = {
    "name": "3D Presentation Plug-in",
    "author": "Matyas Sojka",
    "version": (1, 0),
    "blender": (2, 91, 2),
    "location": "View3D > Sidebar > Components + Presentation + Slideshow",
    "description": "Create animated 3D presentations and present them in Blender.",
    "warning": "",
    "doc_url": "https://gitlab.fit.cvut.cz/sojkamat/blender-presentation-plug-in",
    "category": "3D View",
}

import bpy, os, platform, glob, random, json
from math import radians, sin, cos, tan, pi, pow, ceil
from bpy.app.handlers import persistent

        

# -----------------------------------------------------------------------------------------------------
#                                               PROPERTIES
# -----------------------------------------------------------------------------------------------------

class PresMenuProperties(bpy.types.PropertyGroup):
    script_file = os.path.realpath(__file__)
    script_dir = os.path.dirname(script_file)
    
    # chosen slides, ready to import   
    # slide_list = [[filepath, parent_collection, camera_name], ...]
    slide_list = []
    
    # chosen images, ready to import 
    # image_list = [filepath1, filepath2, ...]
    image_list = []
    
    # camera objects for interpolation
    camera_objects = []
    
    # loops = {end_frame1: start_frame1, end_frame2: start_frame2, ...}
    loops = {}
    
    # structure for marker movement
    # marker_timers = {TIMER strip: [marker1, marker2, ...], ...}
    marker_timers = {}
    
    # structure for checking nla changes
    # nla_strips = {name: [start, end], ...}
    nla_strips = {}
    
    # structure for type count (template creation) 
    assigned_types = {'H1':0, 'H2':0, 'OL':0, 'UL':0, 'IMAGE':0, 'NUMBER':0}

    # enter fullscreen for slideshow or not
    fullscreen: bpy.props.BoolProperty(name="Enter fullscreen mode", default=True)
    # already used override or not
    overriden: bpy.props.BoolProperty(name="Flag for overriding", default=False)
    # show objects with unassigned type in UI
    show_unassigned: bpy.props.BoolProperty(name="Show UNASSIGNED objects", default=True)
    # does component has more collections
    more_collections: bpy.props.BoolProperty(name="Flag for component with more collections", default=False)
    # interpolate camera inbetween components or not
    interpolate_camera: bpy.props.BoolProperty(name="Interpolate camera", default=True)
    # path to the JSON file
    json_path: bpy.props.StringProperty(name="JSON File", default="//", subtype='FILE_PATH')
    # path to this .blend file
    this_file: bpy.props.StringProperty(name="Path to this .blend file", default="//", subtype='FILE_PATH')
    # time of the camera transition
    transition_time: bpy.props.FloatProperty(name="Transition time  [s]", default=2, subtype='TIME', unit='TIME', step=20, min=0.2, max=3600)
    # number of images chosen, but not imported
    image_chosen: bpy.props.IntProperty(name="Number of images chosen, but not imported", default=0, min=0, max=999)
    # number of components chosen, but not imported
    slides_chosen: bpy.props.IntProperty(name="Number of components chosen, but not imported", default=0, min=0, max=999)
    # number of images imported
    image_count: bpy.props.IntProperty(name="Current number of images imported", default=0, min=0, max=999)
    # number of components imported
    slide_count: bpy.props.IntProperty(name="Current number of components imported", default=0, min=0, max=999)
    # are there any components imported
    already_imported: bpy.props.BoolProperty(name="Flag for importing components", default=False)
    # image or component relative postition
    slide_position: bpy.props.EnumProperty(name="Arrange in", 
                items = [("x_axis", "x-axis", "Arrange next to each other in the x-axis", "FORWARD", 0),
                        ("y_axis", "y-axis", "Arrange behind each other in the y-axis", "TRANSFORM_ORIGINS", 1),
                        ("z_axis", "z-axis", "Arrange under each other in the z-axis", "SORT_ASC", 2),
                        ("circle", "circle", "Arrange in a circle, or n-polygon", "SEQ_CHROMA_SCOPE", 3)])
    # object type for template creation
    object_type: bpy.props.EnumProperty(name="Object type", 
                items = [("H1", "H1", "Heading 1"),
                        ("H2", "H2", "Heading 2"),
                        ("OL", "OL", "Ordered List"),
                        ("UL", "UL", "Unordered List"),
                        ("IMAGE", "IMAGE", "Image file (.jpg, .png, ...)"),
                        ("NUMBER", "NUMBER", "Component number out of the total number of components, for ex. 5/24"),
                        ("UNASSIGNED", "UNASSIGNED", "Unassign type to turn the object into background")])
    
    
    
# -----------------------------------------------------------------------------------------------------
#                                                 UI
# -----------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------
#    COMPONENTS UI
# -------------------------------------------------------------------

class SlidePanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Components'
     
        
class SLIDE_PARENT_PT_panel(SlidePanel, bpy.types.Panel):
    bl_label = "Component & Template Generating"
    bl_idname = "SLIDE_PARENT_PT_panel"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        

class IMAGE_PT_panel(SlidePanel, bpy.types.Panel):
    bl_label = "Image Slides"
    bl_parent_id = "SLIDE_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'IMAGE_PLANE')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        row.label(text="Use to generate a component from images.")
        row = layout.row()
        row.prop(pres_tool, "slide_position")
        row = layout.row()
        row.prop(pres_tool, "interpolate_camera")
        if pres_tool.interpolate_camera:
            row.prop(pres_tool, "transition_time")
        row = layout.row()
        row = layout.row()
        row = layout.row()
        row.operator("presentation.choose_image", text="Choose Images")
        row = layout.row()
        
        if pres_tool.image_chosen != 0:
            row.label(text=str(pres_tool.image_chosen) + " Images chosen, but not imported")
            row = layout.row()
            row.label(text="Choose all images first, then import them.")
            row = layout.row()
            row.operator("presentation.add_image", text="Import Images")
            row = layout.row()
        
        
class TEMPLATE_PT_panel(SlidePanel, bpy.types.Panel):
    bl_label = "Template Creation"
    bl_parent_id = "SLIDE_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'CON_SIZELIKE')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        row.label(text="Use to create a template for a component.")
        row = layout.row()
        row.prop(pres_tool, "object_type")
        row = layout.row()
        row.prop(pres_tool, "show_unassigned")
        row = layout.row()
        row.operator("presentation.assign_object_type", text="Assign Type to Selected")
        row = layout.row()
        if len(bpy.data.objects.values()) == 0:
            row.label(text="Add some objects to the scene first")
            row = layout.row()
        else:
            row.label(text="OBJECT")
            row.label(text=" ")
            row.label(text="TYPE")
            row = layout.row()
        
        for obj in bpy.context.scene.objects:
            if obj.type == 'GPENCIL':
                icon = 'OUTLINER_OB_GREASEPENCIL'
            elif obj.type == 'LIGHT_PROBE':
                icon = 'OUTLINER_OB_LIGHTPROBE'
            else:
                icon = 'OUTLINER_OB_' + obj.type
                
            try:
                if pres_tool.show_unassigned is False and obj["OBJECT TYPE"] == "UNASSIGNED":
                    continue
                row.label(text=obj.name + ":", icon=icon)
                if obj.select_get():
                    row.label(text="(selected)")
                else:
                     row.label(text=" ")
                row.label(text=obj["OBJECT TYPE"])
                row = layout.row()
            except:
                if pres_tool.show_unassigned is True:
                    row.label(text="UNASSIGNED")
                    row = layout.row()
        
        if len(bpy.data.objects.values()) != 0:
            row = layout.row()
            row = layout.row()
            row.label(text="If your template is finished, generate the JSON file.")
            row = layout.row()
            row.label(text="UNASSIGNED objects will be considered background.")
            row = layout.row()
            row.operator("presentation.generate_json_file", text="Generate JSON File")       
                

class GENERATING_PT_panel(SlidePanel, bpy.types.Panel):
    bl_label = "Component from Template"
    bl_parent_id = "SLIDE_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'MOD_EXPLODE')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        row.label(text="Use to generate a component from this template file.")
        row = layout.row()
        row.prop(pres_tool, "json_path")
        row = layout.row()
        row.label(text="This blender file will be filled with the JSON data.")
        row = layout.row()
        row.operator("presentation.component_from_template", text="Create Component(s)")   
    

# -------------------------------------------------------------------
#    PRESENTATION UI
# -------------------------------------------------------------------

class PresentationPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Presentation'
 
 
class PRESENTATION_PARENT_PT_panel(PresentationPanel, bpy.types.Panel):
    bl_label = "Presentation Setup"
    bl_idname = "PRESENTATION_PARENT_PT_panel"
   
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        
class IMPORT_SETTINGS_PT_panel(PresentationPanel, bpy.types.Panel):
    bl_label = "Component Import"
    bl_parent_id = "PRESENTATION_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'LINKED')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool

        row = layout.row()
        row.label(text="Use to create a presentation from components.")
        row = layout.row()
        if  len(pres_tool.slide_list) == 0:
            row.prop(pres_tool, "slide_position")
            row = layout.row()
            row = layout.row()
            row.prop(pres_tool, "interpolate_camera")
            if pres_tool.interpolate_camera:
                row.prop(pres_tool, "transition_time")
            row = layout.row()
            row = layout.row()
            row = layout.row()
            row.label(text="Set Arrangement and Interpolation BEFORE choosing Components.")
        else:
            row.label(text="Can't change import settings anymore.")
            row = layout.row()
        row = layout.row()
        row.operator("presentation.choose_slide", text="Choose Component(s)")
        row = layout.row()
        
        if pres_tool.slides_chosen != 0:
            row.label(text=str(pres_tool.slides_chosen) + " Component(s) chosen, but not imported")
            row = layout.row()
            row.operator("presentation.add_slide", text="Import Component(s)")
            row = layout.row()
        row.label(text=str(pres_tool.slide_count) + " Components imported")
        row = layout.row()

  
class PRESENTATION_SETTINGS_PT_panel(PresentationPanel, bpy.types.Panel):
    bl_label = "Presentation Settings"
    bl_parent_id = "PRESENTATION_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'TOOL_SETTINGS')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        if pres_tool.slide_count == 0:
            row.label(text="-- Choose and Import Components first --")
            row = layout.row()
        else:
            row.label(text=str(pres_tool.slide_count) + " Components imported")
            row = layout.row()
        if pres_tool.slide_count != 0:
            try:
                if bpy.data.workspaces["Presentation"] is not None:
                    if bpy.context.window.workspace != bpy.data.workspaces["Presentation"]:
                        row.label(text="! Before using Override, left-click into 3D Viewport !")
                        row = layout.row()
                        row.operator("presentation.override_slides", text="Override")
                        row = layout.row()
                    else:
                        row.label(text="To call Override switch other wokspace")
                        row = layout.row()
                        if pres_tool.overriden is True:
                            row.label(text="Filter NLA Strips by TIMERS Collection", icon ="FILTER")
                            row = layout.row()
            except:
                row.label(text="! Before using Override, left-click into 3D Viewport !")
                row = layout.row()
                row.operator("presentation.override_slides", text="Override")
                row = layout.row()
        if pres_tool.overriden:
            row.operator("presentation.delete_slide", text="Delete Component(s)")
            row = layout.row()
            row.operator("presentation.recalculate_cameras", text="Recalculate cameras")
            row = layout.row()


class PRESENTATION_RESET_PT_panel(PresentationPanel, bpy.types.Panel):
    bl_label = "Reset Presentation"
    bl_parent_id = "PRESENTATION_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'CANCEL')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        row.label(text="Use this to reset the component count.")
        row = layout.row()
        row.operator("presentation.reset", text="Reset Presentation")


# -------------------------------------------------------------------
#    SLIDESHOW UI
# -------------------------------------------------------------------      

class PresenterPanel:
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Slideshow'
 
 
class PRESENTING_PARENT_PT_panel(PresenterPanel, bpy.types.Panel):
    bl_label = "Slideshow"
    bl_idname = "PRESENTING_PARENT_PT_panel"
   
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        
class PRESENTATION_START_PT_panel(PresentationPanel, bpy.types.Panel):
    bl_label = "Presentation Start"
    bl_parent_id = "PRESENTING_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'IMAGE_BACKGROUND')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        row.label(text="Use 'Window --> New Main Window' for multiple screens.")
        row = layout.row()
        row.prop(pres_tool, "fullscreen")
        row = layout.row()
        row.operator("presentation.start", text="START Presentation")
        row = layout.row()
        row.operator("presentation.end", text="END Presentation")
        row = layout.row()
        
        
class NAVIGATION_PT_panel(PresentationPanel, bpy.types.Panel):
    bl_label = "Presentation Navigation"
    bl_parent_id = "PRESENTING_PARENT_PT_panel"
    
    def draw_header(self, context):
        layout = self.layout
        layout.label(icon= 'ARROW_LEFTRIGHT')
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        pres_tool = scene.my_pres_tool
        
        row = layout.row()
        row = layout.row(align=True)
        cf = layout.column_flow(columns=4, align=True)
        cf.scale_y = 2.0
        cf.operator("wm.jumptostart", text="", icon='REW')
        cf.operator("wm.rotatecamdown", text="", icon='PLAY_REVERSE')
        cf.operator("wm.rotatecamup", text="", icon='PLAY')
        cf.operator("wm.jumptoend", text="", icon='FF')



# -----------------------------------------------------------------------------------------------------
#                                               FUNCTIONS
# -----------------------------------------------------------------------------------------------------

def getCorrectTypeName(type):
    pres_tool = bpy.context.scene.my_pres_tool
    
    if type in ["NUMBER", "UNASSIGNED"]:
        return type

    cnt = pres_tool.assigned_types[type]
            
    if cnt == 0:
        pres_tool.assigned_types[type] += 1
        return type
    else:
        pres_tool.assigned_types[type] += 1
        return type+"."+str(cnt+1)

#------------------------------------------------------------

def check_marker_loops():
    pres_tool = bpy.context.scene.my_pres_tool
    pres_tool.loops.clear()
    last_loop_start = -1
    markers = bpy.context.scene.timeline_markers
    
    m_list = []
    for m in markers:
        m_list.append((m.frame, m.name))
    m_list.sort()
    
    for m in m_list:
        if m[1] == "LOOP_START":
            last_loop_start = m[0]
            continue
        if m[1] == "LOOP_END":
            pres_tool.loops[m[0]] = last_loop_start
            continue
    return

#------------------------------------------------------------

# https://blender.stackexchange.com/questions/146685/how-to-obtain-the-parent-of-a-collection-using-python
# functions to get the parent collection
def get_parent_collection_names(collection, parent_names):
  for parent_collection in bpy.data.collections:
    if collection.name in parent_collection.children.keys():
      parent_names.append(parent_collection.name)
      get_parent_collection_names(parent_collection, parent_names)
      return

def get_parent_collection(obj):
  parent_collection = obj.users_collection[0]
  parent_names      = []
  parent_names.append(parent_collection.name)
  get_parent_collection_names(parent_collection, parent_names)
  parent_names.reverse()
  return parent_names[0]
        
#------------------------------------------------------------

# change timing of a component        
def change_timimg(file, time, interpolation_time, cnt, this_file):
    total_x = time
    bpy.ops.wm.open_mainfile(filepath= file)
    more_collections = False
        
    #get collection to link ("Component")
    try:
        if bpy.data.collections["Component"] is not None:
            parent_collection = "Component"
    except:
        #no collection -> create Component collection
        if len(bpy.data.collections.values()) == 0:
            collection = bpy.data.collections.new(name="Component")
            bpy.context.scene.collection.children.link(collection)
            for obj in bpy.data.objects:
                collection.objects.link(obj)
                bpy.context.scene.collection.objects.unlink(obj)
            parent_collection = "Component"
        #one collection -> rename it to Component
        elif len(bpy.data.collections.values()) == 1:
            bpy.data.collections[0].name = "Component"
            parent_collection = "Component"
        #more collections -> take the one with a camera + warning
        else:
            if len(bpy.data.cameras.values()) != 0:
                cam_obj = None
                for obj in bpy.data.objects:
                    if obj.type == 'CAMERA':
                        cam_obj = obj
                        break
                more_collections = True
                parent_collection = get_parent_collection(cam_obj)
                bpy.data.collections[parent_collection].name = "Component"
                parent_collection = "Component"
    
    cam = None
    cam_found = False
    cam_multiple = False
    
    #check for multiple or no cameras            
    for obj in bpy.data.collections["Component"].objects:
        if obj.type == 'CAMERA':
            if cam_found is False:
                cam = obj
                cam_found = True
            else:
                cam_multiple = True
                break
    
    if cam_multiple is True or cam is None:
        return -1
    
    #rename the camera
    new_cam_name = getCorrectCameraName(cnt)
    cam.name = new_cam_name
    cam.data.name = new_cam_name
        
    max_x = 0
    min_x = bpy.context.scene.frame_end
            
    #check keyframes    
    for action in bpy.data.actions:
        for fcurve in action.fcurves:
            for point in fcurve.keyframe_points:
                if point.co.x > max_x:
                    max_x = point.co.x
                if point.co.x < min_x:
                    min_x = point.co.x
                    
    #no keyframes -> create them               
    if max_x == 0:
        cam.keyframe_insert(data_path="location", index=0, frame=1)
        cam.keyframe_insert(data_path="location", index=0, frame=2)
        min_x = 1
        max_x = 2
    
    #convert object keyframes to nla strips and move them
    for obj in bpy.context.scene.objects:
        if obj.animation_data is not None:
            action = obj.animation_data.action
            if action is not None:
                track = obj.animation_data.nla_tracks.new()
                frame = total_x - min_x
                if time != 1:
                    frame += interpolation_time
                strip = track.strips.new(action.name, action.frame_range[0] + frame, action)
                strip.use_sync_length = True
                obj.animation_data.action = None
    
    #convert material keyframes to nla strips and move them
    for mat in bpy.data.materials:
        if mat.node_tree is not None:
            if mat.node_tree.animation_data is not None:
                action = mat.node_tree.animation_data.action
                if action is not None:
                    track = mat.node_tree.animation_data.nla_tracks.new()
                    frame = total_x - min_x
                    if time != 1:
                        frame += interpolation_time
                    strip = track.strips.new(action.name, action.frame_range[0] + frame, action)
                    strip.use_sync_length = True
                    mat.node_tree.animation_data.action = None
     
    l = file.split("\\")
    dir = ("\\").join(l[:-1])
    name = l[-1]
    
    p = this_file.split("\\")
    this_dir = ("\\").join(p[:-1])
    this_fullname = p[-1].split(".")
    this_name = this_fullname[0]
     
    #create folder for timed components    
    if not os.path.exists(bpy.path.abspath(os.path.join(this_dir, this_name))):
        os.makedirs(bpy.path.abspath(os.path.join(this_dir, this_name)))

    #check for markers at start and end
    start_marker = False
    end_marker = False
    markers = bpy.context.scene.timeline_markers
    for m in markers:
        if m.frame == min_x:
            start_marker = True
        if m.frame == max_x:
            end_marker = True
    if start_marker is not True:
        bpy.context.scene.timeline_markers.new(name="HH_" + str(min_x), frame=min_x)
    if end_marker is not True:
        bpy.context.scene.timeline_markers.new(name="HH_" + str(max_x), frame=max_x)
    
    #move and sort markers by frame    
    m_list = []
    markers = bpy.context.scene.timeline_markers
    for m in markers:
        m.frame -= int(min_x)
        m.frame += int(total_x)
        if total_x != 1:
            m.frame += int(interpolation_time)
        m_list.append([int(m.frame), m.name])
    m_list.sort()
    
    #create a text file with them
    m_name = os.path.join(this_dir, this_name, "markers.txt")
    with open(m_name, "a") as f:
        f.write(name + ":")
        for m in m_list:
            if m[1] == "LOOP_START":
                f.write("LS-")
            if m[1] == "LOOP_END":
                f.write("LE-")
            f.write(str(m[0]) + ";")
        f.write("\n")
         
    #calculate total time shift
    diff = max_x - min_x           
    total_x += diff
    if time != 1:
        total_x += interpolation_time
                    
    bpy.context.scene.frame_start = total_x - diff            
    bpy.context.scene.frame_end = total_x
    
    #create empty for better timing change
    create_slide_empty(parent_collection, name)
        
    fname = os.path.join(this_dir, this_name, name)
    bpy.context.scene.my_pres_tool.slide_list.append([fname, parent_collection, new_cam_name])
                        
    #save as new file in ./timed
    bpy.ops.wm.save_as_mainfile(filepath=fname, copy=True)

    
    return total_x, more_collections
  
#------------------------------------------------------------ 

#converts all to nla strips
def convert_all_to_nla():
    for obj in bpy.context.scene.objects:
        if obj.animation_data is not None:
            action = obj.animation_data.action
            if action is not None:
                track = obj.animation_data.nla_tracks.new()
                strip = track.strips.new(action.name, action.frame_range[0], action)
                strip.use_sync_length = True
                obj.animation_data.action = None

    #convert material keyframes to nla strips and move them
    for mat in bpy.data.materials:
        if mat.node_tree is not None:
            if mat.node_tree.animation_data is not None:
                action = mat.node_tree.animation_data.action
                if action is not None:
                    track = mat.node_tree.animation_data.nla_tracks.new()
                    strip = track.strips.new(action.name, action.frame_range[0], action)
                    strip.use_sync_length = True
                    mat.node_tree.animation_data.action = None

 #------------------------------------------------------------ 

#creates an empty for time shifts
def create_slide_empty(parent_collection, filename):
    #create empty object with keyframes from 1 to frame_end
    empty = bpy.data.objects.new("COMPONENT TIMER", None)
    bpy.context.scene.collection.objects.link(empty)
    bpy.data.collections[parent_collection].objects.link(empty)
    bpy.context.scene.collection.objects.unlink(empty)
    empty.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_start)
    empty.keyframe_insert(data_path="location", frame=bpy.context.scene.frame_end)
    
    #create NLA strip with "unique" name
    action = empty.animation_data.action
    rng = random.random()
    action.name = filename + " TIMER STRIP" + str(rng)
    track = empty.animation_data.nla_tracks.new()
    strip = track.strips.new(action.name, action.frame_range[0], action)
    strip.use_sync_length = True
    empty.animation_data.action = None
    
    #add drivers to all NLA strips
    for obj in bpy.context.scene.objects:
        if obj.name == "COMPONENT TIMER":
            continue
        try:
            for strip in obj.animation_data.nla_tracks["NlaTrack"].strips:
                #frame start
                driver = obj.driver_add('animation_data.nla_tracks["NlaTrack"].strips["'+strip.name+'"].frame_start')
                driver.driver.type = 'SCRIPTED'
                tmp = driver.driver.expression
                driver.driver.expression = "delta + " + tmp + " - " + str(bpy.context.scene.frame_start)
                var = driver.driver.variables.new()
                var.name = 'delta'
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id = bpy.data.objects.get('COMPONENT TIMER')
                target.data_path = 'animation_data.nla_tracks["NlaTrack"].strips["' + filename + ' TIMER STRIP'+str(rng)+'"].frame_start'
                
                #frame end
                driver = obj.driver_add('animation_data.nla_tracks["NlaTrack"].strips["'+strip.name+'"].frame_end')
                driver.driver.type = 'SCRIPTED'
                tmp = driver.driver.expression
                driver.driver.expression = "delta + " + tmp + " - " + str(bpy.context.scene.frame_start)
                var = driver.driver.variables.new()
                var.name = 'delta'
                var.type = 'SINGLE_PROP'
                target = var.targets[0]
                target.id = bpy.data.objects.get('COMPONENT TIMER')
                target.data_path = 'animation_data.nla_tracks["NlaTrack"].strips["' + filename + ' TIMER STRIP'+str(rng)+'"].frame_start'
                
        except:
            continue
        
    return

 #------------------------------------------------------------ 

 # return camera name acorrding to cnt       
def getCorrectCameraName(cnt):
    if cnt == 0:
        return '=> CAMERA'
    elif cnt > 0 and cnt < 10:
        return '=> CAMERA.00' + str(cnt)
    elif cnt >= 10 and cnt < 100:
        return '=> CAMERA.0' + str(cnt)
    elif cnt >= 100:
        return '=> CAMERA.' + str(cnt)
    else:
        return 'INCORRECT CAMERA INDEX'

 #------------------------------------------------------------

# setup camera transition inbetween components
def create_camera_change(i, max_frame, min_frame, n_tmp):
    pres_tool = bpy.context.scene.my_pres_tool
    
    if i == 0:
        if n_tmp != 0:
            #setup camera for slide after already imported
            n = i + n_tmp
            marker = bpy.context.scene.timeline_markers.new(name="SLIDE " + str(n) + " START", frame=min_frame)
            cam_name = getCorrectCameraName(n)
            marker.camera = bpy.context.scene.objects.get(cam_name)
            pres_tool.camera_objects.append(marker.camera)
        else:
            #setup camera for first slide
            marker = bpy.context.scene.timeline_markers.new(name="SLIDE 0 START", frame=1)
            marker.camera = bpy.context.scene.objects.get("=> CAMERA")
            pres_tool.camera_objects.append(marker.camera)
            
    if n_tmp != 0:
        i += n_tmp
        
    if i != pres_tool.slide_count-1:
        #set camera interpolation time
        if pres_tool.interpolate_camera is True:
            interpolation_time = bpy.context.scene.render.fps * pres_tool.transition_time
        else:
            interpolation_time = 1

        # create markers  
        marker_frame = max_frame + interpolation_time
        marker = bpy.context.scene.timeline_markers.new(name="SLIDE " + str(i) + " START", frame=marker_frame)
        cam_name = getCorrectCameraName(i)
        cam_next_name = getCorrectCameraName(i+1)
        marker.camera = bpy.context.scene.objects.get(cam_next_name)
        pres_tool.camera_objects.append(marker.camera)
        # create camera constraints
        const_loc = bpy.data.objects[cam_name].constraints.new('COPY_LOCATION')
        const_rot = bpy.data.objects[cam_name].constraints.new('COPY_ROTATION')
        const_scl = bpy.data.objects[cam_name].constraints.new('COPY_SCALE')
        const_loc.target = bpy.data.objects[cam_next_name]
        const_rot.target = bpy.data.objects[cam_next_name]
        const_scl.target = bpy.data.objects[cam_next_name]
        const_loc.influence = 0
        const_rot.influence = 0
        const_scl.influence = 0
        bpy.data.objects[cam_name].keyframe_insert(data_path='constraints["Copy Location"].influence', frame=max_frame)
        bpy.data.objects[cam_name].keyframe_insert(data_path='constraints["Copy Rotation"].influence', frame=max_frame)
        bpy.data.objects[cam_name].keyframe_insert(data_path='constraints["Copy Scale"].influence', frame=max_frame)
        const_loc.influence = 1
        const_rot.influence = 1
        const_scl.influence = 1
        marker_frame = max_frame + interpolation_time
        bpy.data.objects[cam_name].keyframe_insert(data_path='constraints["Copy Location"].influence', frame=marker_frame)
        bpy.data.objects[cam_name].keyframe_insert(data_path='constraints["Copy Rotation"].influence', frame=marker_frame)
        bpy.data.objects[cam_name].keyframe_insert(data_path='constraints["Copy Scale"].influence', frame=marker_frame)
    
    return

#------------------------------------------------------------

# scale image to fit the camera
def normalizeImageDimensions(img_obj, max_y, i):
    #set width to 1
    orig_dim = img_obj.dimensions
    coef = 1/orig_dim[0]
    y_dim = orig_dim[1]*coef
    #set heigth to 1
    if y_dim > 1:
        coef_y = 1/y_dim
        img_obj.dimensions = orig_dim[0]*coef*coef_y, orig_dim[1]*coef*coef_y, orig_dim[2]
        if i == 0:
            max_y = orig_dim[1]*coef*coef_y
        if orig_dim[1]*coef > max_y:
            max_y = orig_dim[1]*coef*coef_y
    else:
        img_obj.dimensions = orig_dim[0]*coef, orig_dim[1]*coef, orig_dim[2]
        if i == 0:
            max_y = orig_dim[1]*coef
        if orig_dim[1]*coef > max_y:
            max_y = orig_dim[1]*coef      
    return max_y 


# -----------------------------------------------------------------------------------------------------
#                                             HANDLERS
# -----------------------------------------------------------------------------------------------------
        
# called every time the frame changes
def presentation_handler(scene):
    frame_current = bpy.context.scene.frame_current
    markers = bpy.context.scene.timeline_markers
    pres_tool = bpy.context.scene.my_pres_tool
    
    check_marker_loops()
    
    for m in markers:
        if m.frame == frame_current:
            if m.name == "LOOP_START":
                bpy.ops.screen.animation_cancel()
                bpy.context.scene.frame_current = m.frame
            elif m.name == "LOOP_END":
                loop_start = pres_tool.loops[m.frame]
                bpy.context.scene.frame_current = loop_start+1
            else:
                bpy.ops.screen.animation_cancel()
                bpy.context.scene.frame_current = m.frame


#------------------------------------------------------------

# called every time the scene or nla or anything changes
@persistent
def nla_handler(scene):
    pres_tool = bpy.context.scene.my_pres_tool
    for obj in bpy.context.scene.objects:
        if "COMPONENT TIMER" in obj.name:
            nla_name = obj.animation_data.nla_tracks[0].strips[0].name
            nla_start = obj.animation_data.nla_tracks[0].strips[0].frame_start
            nla_end = obj.animation_data.nla_tracks[0].strips[0].frame_end
            nla_len = nla_end - nla_start
            if nla_name != '':
                #strip moved -> update strips, markers and drivers
                if pres_tool.nla_strips[nla_name][0] != nla_start:
                    
                    #strip snapping while overlaping
                    #problem when strips contain one another after -> strip is scaled and unusable
                    """
                    if len(bpy.context.selected_nla_strips) == 1:
                        #snap
                        restart = True
                        forward = True
                        back    = True
                        while restart:
                            restart = False
                            for strip in pres_tool.nla_strips:
                                if strip == nla_name:
                                    continue
                                if pres_tool.nla_strips[strip][0] <= nla_start <= pres_tool.nla_strips[strip][1] and pres_tool.nla_strips[strip][0] <= nla_end <= pres_tool.nla_strips[strip][1] and forward == True:
                                    print("====== MIDDLE ======")
                                    nla_start = pres_tool.nla_strips[strip][1] + 1
                                    nla_end = nla_start + nla_len
                                    obj.animation_data.nla_tracks[0].strips[0].frame_start = nla_start
                                    obj.animation_data.nla_tracks[0].strips[0].frame_end = nla_end
                                    back = False
                                    restart = True
                                elif pres_tool.nla_strips[strip][0] <= nla_start <= pres_tool.nla_strips[strip][1] and forward == True:
                                    print("====== START ======")
                                    nla_start = pres_tool.nla_strips[strip][1] + 1
                                    nla_end = nla_start + nla_len
                                    obj.animation_data.nla_tracks[0].strips[0].frame_start = nla_start
                                    obj.animation_data.nla_tracks[0].strips[0].frame_end = nla_end
                                    back = False
                                    restart = True
                                elif pres_tool.nla_strips[strip][0] <= nla_end <= pres_tool.nla_strips[strip][1] and back == True:
                                    print("====== END ======")
                                    nla_end = pres_tool.nla_strips[strip][0] - 1
                                    nla_start = nla_end - nla_len
                                    obj.animation_data.nla_tracks[0].strips[0].frame_start = nla_start
                                    obj.animation_data.nla_tracks[0].strips[0].frame_end = nla_end
                                    forward = False
                                    restart = True
                    """
                                    
                    #move markers
                    for m in bpy.context.scene.timeline_markers:
                        if m in pres_tool.marker_timers[nla_name]:
                            diff = nla_start - pres_tool.nla_strips[nla_name][0]
                            m.frame += diff
                    check_marker_loops()
                            
                    #update strips list
                    pres_tool.nla_strips[nla_name][0] = nla_start
                    pres_tool.nla_strips[nla_name][1] = nla_end
                    tmp_dict = dict(sorted(pres_tool.nla_strips.items(), key=lambda item: item[1][0]))
                    pres_tool.nla_strips = tmp_dict
                    
                    #update drivers (move other strips)
                    for o in bpy.context.scene.objects:
                        try:
                            for driver in o.animation_data.drivers:
                                driver.driver.expression += ""
                        except:
                            continue
                        
                    #update interpolation cameras
                    cam_strips = set()
                    for i, cam in enumerate(pres_tool.camera_objects):
                        if i == len(pres_tool.camera_objects)-1:
                            break
                        try:
                            #list of nla ranges [start, end]
                            nla_list = list(pres_tool.nla_strips.values())
                            cam.animation_data.nla_tracks[1].strips[0].frame_start = nla_list[i][1]
                            cam.animation_data.nla_tracks[1].strips[0].frame_end = nla_list[i+1][0]
                            cam_strips.add(cam.animation_data.nla_tracks[1].strips[0])
                        except:
                            #list of nla ranges [start, end]
                            nla_list = list(pres_tool.nla_strips.values())
                            cam.animation_data.nla_tracks[0].strips[0].frame_start = nla_list[i][1]
                            cam.animation_data.nla_tracks[0].strips[0].frame_end = nla_list[i+1][0]
                            cam_strips.add(cam.animation_data.nla_tracks[0].strips[0])
                            
                    #fix strip keyframe scale (changed while moving strip for some reason)
                    for area in bpy.context.screen.areas:
                        if area.type == "OUTLINER":
                            #unhide all collections
                            override = bpy.context.copy()
                            override['area'] = area
                            bpy.ops.outliner.unhide_all(override)
                    for area in bpy.context.screen.areas:
                        if area.type == "NLA_EDITOR":
                            for space in area.spaces:
                                if space.type == "NLA_EDITOR":
                                    override = bpy.context.copy()
                                    override['area'] = area
                                    #remove all filters
                                    filter = space.dopesheet.filter_collection
                                    space.dopesheet.filter_collection = None
                                    #unhide hidden collections - doesnt wotk (??)
                                    """
                                    hidden_collections = set()
                                    for collection in bpy.context.scene.collection.children:
                                        print(collection)
                                        if collection.hide_viewport == True:
                                            print("-- HIDEN --")
                                            hidden_collections.add(collection)
                                            collection.hide_viewport = False
                                            """
                                    #select all strips
                                    for i in bpy.data.objects:
                                        if i.animation_data is None:
                                            continue
                                        for j in i.animation_data.nla_tracks:
                                            for k in j.strips:
                                                if k not in cam_strips:
                                                    k.select = True
                                    # clear scale                
                                    bpy.ops.nla.clear_scale(override)
                                    bpy.ops.nla.select_all(override, action='DESELECT')
                                    space.dopesheet.filter_collection = filter
                                    #for collection in hidden_collections:
                                        #collection.hide_viewport = True
                                    break


# -----------------------------------------------------------------------------------------------------
#                                            OPERATORS
# -----------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------
#    COMPONENT OPERATORS
# -------------------------------------------------------------------

class AssignObjectType(bpy.types.Operator):
    """Assign selected type to currentely selected objects"""
    bl_idname = 'presentation.assign_object_type'
    bl_label = 'Assign type to selected objects'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        pres_tool.assigned_types = {'H1':0, 'H2':0, 'OL':0, 'UL':0, 'IMAGE':0, 'NUMBER':0}
        
        # check current types
        for obj in bpy.data.objects:
            try:
                if '.' in obj["OBJECT TYPE"]:
                    type_list = obj["OBJECT TYPE"].split('.')
                    type = type_list[0]
                    pres_tool.assigned_types[type] += 1
                else:
                    pres_tool.assigned_types[obj["OBJECT TYPE"]] += 1
            except:
                continue
        
        # assign type to selected
        for obj in bpy.context.selected_objects:
            if pres_tool.object_type in ['H1','H2','OL','UL','NUMBER'] and obj.type != 'FONT':
                self.report({'WARNING'}, "Object " + obj.name + " is not a Text Object!")
                continue
            if pres_tool.object_type == 'IMAGE' and obj.type != 'MESH':
                self.report({'WARNING'}, "Object " + obj.name + " is not a Mesh Object!")
                continue

            obj["OBJECT TYPE"] = getCorrectTypeName(pres_tool.object_type)
            
        return{'FINISHED'}


#------------------------------------------------------------  
    
    
class GenerateJsonFile(bpy.types.Operator):
    """Generate JSON file from this template"""
    bl_idname = 'presentation.generate_json_file'
    bl_label = 'Generate JSON'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        if not bpy.data.is_saved:
            self.report({'WARNING'}, "Save this .blend file first.")
            return {'CANCELLED'}
        
        pres_tool.this_file = bpy.data.filepath
        
        # prepare the json structure
        future_json = {}
        for obj in bpy.data.objects:
            try:
                if obj["OBJECT TYPE"] is not None:
                    if 'H1' in obj["OBJECT TYPE"]:
                        future_json[obj["OBJECT TYPE"]] = "Heading 1"
                    if 'H2' in obj["OBJECT TYPE"]:
                        future_json[obj["OBJECT TYPE"]] = "Heading 2"
                    if 'OL' in obj["OBJECT TYPE"]:
                        future_json[obj["OBJECT TYPE"]] = ["Item 1", "Item 2", "Item 3"]
                    if 'UL' in obj["OBJECT TYPE"]:
                        future_json[obj["OBJECT TYPE"]] = ["Item 1", "Item 2", "Item 3"]
                    if 'IMAGE' in obj["OBJECT TYPE"]:
                        future_json[obj["OBJECT TYPE"]] = "C:\\Path\\To\\The\\Image\\File.jpg"
            except:
                continue
        
        # create the json structure
        json_content = json.dumps(future_json, indent=8, sort_keys=True)
        
        p = bpy.context.scene.my_pres_tool.this_file.split("\\")
        this_dir = ("\\").join(p[:-1])
        this_fullname = p[-1].split(".")
        this_name = this_fullname[0]
        
        self.report({'INFO'}, "Generating " + os.path.join(this_dir, this_name) + ".json")

        # create the json file
        with open(os.path.join(this_dir, this_name)+".json", "w+") as f:
            f.write("{\n\t\"Filename\":\n\t")
            f.write(json_content)
            f.write("\n}")
            f.close()
              
        return{'FINISHED'}
        
        
#------------------------------------------------------------  


class CreateComponentFromTemplate(bpy.types.Operator):
    """Use a template and a JSON file to generate a component"""
    bl_idname = 'presentation.component_from_template'
    bl_label = 'Generate Component'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        if not bpy.data.is_saved:
            self.report({'WARNING'}, "Save this .blend file first.")
            return {'CANCELLED'}
        
        pres_tool.this_file = bpy.data.filepath

        # fix the path
        if "//" in pres_tool.json_path:
            tmp = pres_tool.json_path.split("//")
            p = pres_tool.this_file.split("\\")
            this_dir = ("\\").join(p[:-1])
            filename = os.path.join(this_dir, tmp[1])
            pres_tool.json_path = filename

        # try to open the json file
        try:
            f = open(pres_tool.json_path,)
            data = json.load(f)
            f.close()
        except:
            self.report({'ERROR'}, "FILE ERROR. Can't open file " + pres_tool.json_path + ". Make sure it is an existing and valid JSON file. If the problem continues, try moving the JSON file to the same folder as the template.blend file and set the path manually to \"//filename.json\"")
            return {'CANCELLED'}
        
        bpy.ops.wm.save_as_mainfile(filepath=pres_tool.this_file)
        
        unused_keys = set()

        # fill the objects with json data        
        slide_cnt = len(data)
        for n, slide in enumerate(data):
            for key in data[slide]:
                key_found = False
                for obj in bpy.data.objects:
                    try:
                        if bpy.data.objects[obj.name]["OBJECT TYPE"] == key:
                            key_found = True
                            if "H1" in key or "H2" in key:
                                obj.data.body = data[slide][key]
                                break
                            if "OL" in key:
                                for i, line in enumerate(data[slide][key]):
                                    if i == 0:
                                        obj.data.body = str(i+1) + ". " + line
                                    else:
                                        obj.data.body += "\n" + str(i+1) + ". " + line
                                break
                            if "UL" in key:
                                for i, line in enumerate(data[slide][key]):
                                    if i == 0:
                                        obj.data.body = "- " + line
                                    else:
                                        obj.data.body += "\n- " + line
                                break
                            if "IMAGE" in key:
                                img = bpy.data.images.load(filepath = data[slide][key])
                                mat = bpy.data.materials.new(name="New_Mat")
                                mat.use_nodes = True
                                bsdf = mat.node_tree.nodes["Principled BSDF"]
                                texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
                                texImage.image = img
                                mat.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
                                if obj.data.materials:
                                    obj.data.materials[0] = mat
                                else:
                                    obj.data.materials.append(mat)
                                break
                        elif bpy.data.objects[obj.name]["OBJECT TYPE"] == "NUMBER":
                            obj.data.body = str(n+1) + "/" + str(slide_cnt)
                            key_found = True
                    except:
                        continue
            # save it as new file
            dir = bpy.data.filepath.split("\\")
            dir = dir[:-1]
            dir_str = "\\".join(dir)
            slide_str = str(slide) + ".blend"
            self.report({'INFO'}, "Creating file " + os.path.join(dir_str, slide_str))
            bpy.ops.wm.save_as_mainfile(filepath = os.path.join(dir_str, slide_str))
            
        bpy.ops.wm.open_mainfile(filepath=pres_tool.this_file)     
                
        
        return{'FINISHED'}


#------------------------------------------------------------  


class ChooseImage(bpy.types.Operator):
    """Choose Images that will be used to create a Component"""
    bl_idname = 'presentation.choose_image'
    bl_label = 'Select Images'
    
    #selected images
    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement)
    
    #images directory
    directory: bpy.props.StringProperty(
        subtype="DIR_PATH")

    def invoke(self, context, event):
        del event
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        #filter by images
        context.space_data.params.use_filter = True
        context.space_data.params.use_filter_folder = True
        context.space_data.params.use_filter_image = True
        
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        n_tmp = pres_tool.image_chosen
        pres_tool.image_chosen = 0
        
        #check selected files
        for i, file in enumerate(self.files):
            filename = os.path.join(self.directory, file.name)
            if os.path.isfile(filename):
                #image files -> get ready for import
                bpy.context.scene.my_pres_tool.image_list.append(filename)
                pres_tool.image_chosen += 1
            else:
                #file not found
                self.report({'WARNING'}, os.path.split(filename)[1]+' FILE NOT FOUND')
                                 
        pres_tool.image_chosen += n_tmp 
        n_tmp = 0 
        
        return{'FINISHED'}


#------------------------------------------------------------  


class AddImage(bpy.types.Operator):
    """Create a component from the selected images"""
    bl_idname = 'presentation.add_image'
    bl_label = 'Import Selected Images'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        n_tmp = pres_tool.image_count
        pres_tool.image_count = 0
        total = pres_tool.image_chosen
        collection = None
        collection_name = ""
        z_rot = 0
        max_y = 0
        
        #import slides
        for i, file in enumerate(pres_tool.image_list[n_tmp:]):
            filename = file
            if os.path.isfile(filename): 

                #create unique collection for the images
                try:
                    if bpy.data.collections["Component"] is not None:
                        if i == 0:
                            unique_name = False
                            j = 0
                            while not unique_name:
                                j += 1
                                name = "Component." + str(j)
                                try:
                                    if bpy.data.collections[name] is None:
                                        pass
                                except:
                                    unique_name = True
                                    collection = bpy.data.collections.new(name=name)
                                    collection_name = name
                                    bpy.context.scene.collection.children.link(collection)
                                    
                        else:
                            collection = bpy.data.collections[collection_name]
                except:
                    collection = bpy.data.collections.new(name="Component")
                    collection_name = "Component"
                    bpy.context.scene.collection.children.link(collection)
                    
                #import images as planes
                f = filename.split("\\")
                name = f[-1]
                dir = ("\\").join(f[:-1])
                try:
                    bpy.ops.preferences.addon_enable(module="io_import_images_as_planes")
                    bpy.ops.import_image.to_plane(files=[{"name":name, "name":name}], directory=dir, relative=False)
                except:
                    self.report({'ERROR'}, 'Couldnt import image ' + os.path.split(filename)[1])
                    return{'CANCELLED'}
                # image collection
                img_collection = get_parent_collection(bpy.context.active_object)
                if img_collection == "Master Collection":
                    collection.objects.link(bpy.context.active_object)
                    bpy.context.scene.collection.objects.unlink(bpy.context.active_object)
                else:
                    collection.objects.link(bpy.context.active_object)
                    bpy.data.collections[img_collection].objects.unlink(bpy.context.active_object)
                pres_tool.image_count += 1
                pres_tool.image_chosen -= 1

                #arrange images
                if pres_tool.slide_position == "x_axis":
                    #set width to 1
                    if i == 0:
                        max_y = 0
                    max_y = normalizeImageDimensions(bpy.context.object, max_y, i)
                    #set rotation
                    bpy.context.object.rotation_euler[0] = radians(90.0)
                    bpy.context.object.rotation_euler[2] = 0
                    #set location 
                    bpy.context.object.location[0] = i
                    bpy.context.object.location[1] = sin(radians(60.0))
                    bpy.context.object.location[2] = 0
                    z_rot = 60.0
                elif pres_tool.slide_position == "y_axis":
                    #set width to 1
                    if i == 0:
                        max_y = 0
                    max_y = normalizeImageDimensions(bpy.context.object, max_y, i)
                    #set rotation
                    bpy.context.object.rotation_euler[0] = radians(90.0)
                    bpy.context.object.rotation_euler[2] = 0
                    #set location 
                    bpy.context.object.location[0] = 0
                    bpy.context.object.location[1] = (i+1)*sin(radians(60.0))
                    bpy.context.object.location[2] = 0
                    z_rot = 60.0
                elif pres_tool.slide_position == "z_axis":
                    #set width to 1
                    if i == 0:
                        max_y = 0
                    max_y = normalizeImageDimensions(bpy.context.object, max_y, i)
                    #set rotation
                    bpy.context.object.rotation_euler[0] = radians(90.0)
                    bpy.context.object.rotation_euler[2] = radians(-90.0)
                    #set location 
                    bpy.context.object.location[0] = sin(radians(60.0))
                    bpy.context.object.location[1] = 0
                    bpy.context.object.location[2] = -i
                    z_rot = 60.0
                elif pres_tool.slide_position == "circle":
                    n = total
                    z_rot = 360/n                      #z rotation
                    alpha = (n-2)*180/n                #inner angle
                    s = 1                              #polygon side length
                    r1 = s/(2*sin(radians(180.0)/n))   #outer circle radius
                    r2 = s/(2*tan(radians(180.0)/n))   #inner circle radius
                    v = sin(alpha/2)*r1                #triangle height
                    
                    #set rotation
                    bpy.context.object.rotation_euler[0] = radians(90.0)
                    bpy.context.object.rotation_euler[2] = radians(-i*z_rot-90)
                    #set location 
                    if n == 1:
                        bpy.context.object.location[0] = sin(radians(60.0))
                        bpy.context.object.location[1] = 0
                        bpy.context.object.location[2] = 0
                        z_rot = 60.0
                    elif n == 2:
                        bpy.context.object.location[0] = pow(-1,i)*sin(radians(60.0))
                        bpy.context.object.location[1] = 0
                        bpy.context.object.location[2] = 0
                        z_rot = 60.0
                    else:
                        bpy.context.object.location[0] = cos(-i*2*pi/n)*r2
                        bpy.context.object.location[1] = sin(-i*2*pi/n)*r2
                        bpy.context.object.location[2] = 0
                    #set width to 1
                    if i == 0:
                        max_y = 0
                    max_y = normalizeImageDimensions(bpy.context.object, max_y, i)

            else:
                self.report({'ERROR'}, os.path.split(filename)[1]+' FILE NOT FOUND')
         
        pres_tool.image_count += n_tmp
        n_tmp = 0
        
        if pres_tool.slide_position in ["x_axis", "y_axis"]:
            rot = (radians(90.0), 0, 0)
        else:
            rot = (radians(90.0), 0, radians(-90.0))
        #create new camera
        bpy.ops.object.camera_add(enter_editmode=False, align='VIEW', location=(0, 0, 0), rotation=rot)
        #set camera view angle
        bpy.context.object.data.angle = radians(z_rot)
        #set camera as active
        currentCameraObj = bpy.data.objects[bpy.context.active_object.name]
        bpy.context.scene.camera = currentCameraObj
        #set resolution to match the biggest image
        bpy.context.scene.render.resolution_x = 2000
        bpy.context.scene.render.resolution_y = max_y * 2000
        #add it to the collection
        collection = bpy.data.collections[collection_name]
        cam_collection = get_parent_collection(currentCameraObj)
        if cam_collection == "Master Collection":
            collection.objects.link(currentCameraObj)
            bpy.context.scene.collection.objects.unlink(currentCameraObj)
        else:
            collection.objects.link(currentCameraObj)
            bpy.data.collections[cam_collection].objects.unlink(currentCameraObj)

        
        #no interpolation is actully 1 frame interpolation
        if pres_tool.interpolate_camera is False:
            pres_tool.transition_time = 1/bpy.context.scene.render.fps
            
        n = total
        bpy.context.scene.frame_current = 1
        
        if pres_tool.interpolate_camera is False:
            bpy.context.scene.frame_end = n*bpy.context.scene.render.fps*pres_tool.transition_time
        else:
            bpy.context.scene.frame_end = (n-1)*bpy.context.scene.render.fps*pres_tool.transition_time
        
        #set keyframes and markers
        bpy.context.scene.timeline_markers.new("SLIDE_" + str(0), frame=1)
        if pres_tool.slide_position == "x_axis":
            currentCameraObj.keyframe_insert(data_path="location", index=0, frame=1)
            for i in range(1, n):
                #move the camera and set a keyframe + marker
                currentCameraObj.location[0] += 1
                if pres_tool.interpolate_camera is False:
                    f=int((i+1)*bpy.context.scene.render.fps*pres_tool.transition_time)
                else:
                    f=int(i*bpy.context.scene.render.fps*pres_tool.transition_time)
                currentCameraObj.keyframe_insert(data_path="location", index=0, frame=f)
                bpy.context.scene.timeline_markers.new("SLIDE_" + str(i), frame=f)
        elif pres_tool.slide_position == "y_axis":
            currentCameraObj.keyframe_insert(data_path="location", index=1, frame=1)
            for i in range(1, n):
                #move the camera and set a keyframe + marker
                currentCameraObj.location[1] += sin(radians(60.0))
                if pres_tool.interpolate_camera is False:
                    f=int((i+1)*bpy.context.scene.render.fps*pres_tool.transition_time)
                else:
                    f=int(i*bpy.context.scene.render.fps*pres_tool.transition_time)
                currentCameraObj.keyframe_insert(data_path="location", index=1, frame=f)
                bpy.context.scene.timeline_markers.new("SLIDE_" + str(i), frame=f)
        elif pres_tool.slide_position == "z_axis":
            currentCameraObj.keyframe_insert(data_path="location", index=2, frame=1)
            for i in range(1, n):
                #move the camera and set a keyframe + marker
                currentCameraObj.location[2] -= 1
                if pres_tool.interpolate_camera is False:
                    f=int((i+1)*bpy.context.scene.render.fps*pres_tool.transition_time)
                else:
                    f=int(i*bpy.context.scene.render.fps*pres_tool.transition_time)
                currentCameraObj.keyframe_insert(data_path="location", index=2, frame=f)
                bpy.context.scene.timeline_markers.new("SLIDE_" + str(i), frame=f)
        elif pres_tool.slide_position == "circle":
            currentCameraObj.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
            for i in range(1, n):
                currentCameraObj.rotation_euler[2] -= radians(360/n)
                if pres_tool.interpolate_camera is False:
                    f=(i+1)*bpy.context.scene.render.fps*pres_tool.transition_time
                else:
                    f=i*bpy.context.scene.render.fps*pres_tool.transition_time
                currentCameraObj.keyframe_insert(data_path="rotation_euler", index=2, frame=f)
                bpy.context.scene.timeline_markers.new("SLIDE_" + str(i), frame=f)  

        return{'FINISHED'}



# -------------------------------------------------------------------
#    PRESENTATION OPERATORS
# ------------------------------------------------------------------- 
    

class ChooseSlide(bpy.types.Operator):
    """Choose the .blend Component files that you want to use in the presentation"""
    bl_idname = 'presentation.choose_slide'
    bl_label = 'Select Slide(s)'
    
    #selected files
    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement)
    
    #files directory
    directory: bpy.props.StringProperty(
        subtype="DIR_PATH")

    def invoke(self, context, event):
        del event
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        #filter by .blend files
        context.space_data.params.use_filter = True
        context.space_data.params.use_filter_blender = True
        context.space_data.params.use_filter_blendid = True
        context.space_data.params.use_filter_folder = True
        
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        if pres_tool.slide_count == 0 and pres_tool.slides_chosen == 0:
            time = 1
            total = 1
        else:
            time = bpy.context.scene.frame_end
            total = bpy.context.scene.frame_end
            
        n_tmp = pres_tool.slides_chosen
        pres_tool.slides_chosen = 0
        raise_collection_warning = False
        
        if not bpy.data.is_saved:
            self.report({'WARNING'}, "Save this .blend file first.")
            return {'CANCELLED'}
        pres_tool.this_file = bpy.data.filepath

        #check for markers file and delete it
        p = bpy.data.filepath.split("\\")
        this_dir = ("\\").join(p[:-1])
        this_fullname = p[-1].split(".")
        this_name = this_fullname[0]
        m_name = os.path.join(this_dir, this_name, "markers.txt")
        if os.path.exists(m_name) and n_tmp == 0:
            os.remove(m_name)
        
        #set camera interpolation time
        if pres_tool.interpolate_camera is True:
            interpolation_time = bpy.context.scene.render.fps * pres_tool.transition_time
        else:
            interpolation_time = 1
        
        #check selected files
        for i, file in enumerate(self.files):
            filename = os.path.join(self.directory, file.name)
            if os.path.isfile(filename):
                #blender file -> change timing
                f_name = pres_tool.this_file
                bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
                cnt = pres_tool.slides_chosen + pres_tool.slide_count
                if pres_tool.already_imported is False:
                    cnt += n_tmp
                total, more_collections = change_timimg(filename, time, interpolation_time, cnt, bpy.data.filepath)
                if total == -1:
                    #camera error -> abort
                    bpy.ops.wm.open_mainfile(filepath=f_name)
                    pres_tool = bpy.context.scene.my_pres_tool
                    pres_tool.slides_chosen = 0
                    pres_tool.slide_list = []
                    #todo - reset selected files (???)
                    self.report({'ERROR'}, filename + ': CAMERA ERROR. Make sure each component contains EXACTLY 1 CAMERA.')
                    return{'CANCELLED'}
                if more_collections is True:
                    raise_collection_warning = True
                time = total
                bpy.ops.wm.open_mainfile(filepath=f_name)
                pres_tool = bpy.context.scene.my_pres_tool
                pres_tool.slides_chosen += 1
            else:
                #file not found
                self.report({'ERROR'}, os.path.split(filename)[1]+' FILE NOT FOUND')
                                 
        if raise_collection_warning is True:
            self.report({'WARNING'}, str(filename) + ': UNSURE WHICH COLLECTION TO CHOOSE, CHOOSING THE ONE WITH A CAMERA.')
            self.report({'INFO'}, 'Please name the collection that you want to use as "Component" to avoid this.')
        
        bpy.context.scene.frame_start = 1
        bpy.context.scene.frame_end = total
        pres_tool.slides_chosen += n_tmp 
        n_tmp = 0 
        
        return{'FINISHED'}

#------------------------------------------------------------  


class AddSlide(bpy.types.Operator):
    """Import the selected Component .blend files and create a Presentation"""
    bl_idname = 'presentation.add_slide'
    bl_label = 'Add New Slide(s)'

    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        n_tmp = pres_tool.slide_count
        pres_tool.slide_count = 0
        
        #import slides
        for i, file in enumerate(pres_tool.slide_list[n_tmp:]):
            filename = file[0]
            if os.path.isfile(filename):
                
                #link .blend file collection
                section = "\\Collection\\"
                collection_name = file[1]
                filepath  = filename + section + collection_name
                directory = filename + section
                bpy.ops.wm.link(filepath=filepath, filename=collection_name, directory=directory)
                #rename it
                l = file[0].split("\\")
                fullname = l[-1].split(".")
                just_name = fullname[0]
                bpy.context.active_object.name = just_name
                #set component location
                if pres_tool.slide_position == "x_axis":
                    bpy.context.object.location[0] = (i+n_tmp)*50
                    bpy.context.object.location[1] = 0
                    bpy.context.object.location[2] = 0
                elif pres_tool.slide_position == "y_axis":
                    bpy.context.object.location[0] = 0
                    bpy.context.object.location[1] = (i+n_tmp)*50
                    bpy.context.object.location[2] = 0
                elif pres_tool.slide_position == "z_axis":
                    bpy.context.object.location[0] = 0
                    bpy.context.object.location[1] = 0
                    bpy.context.object.location[2] = -(i+n_tmp)*30
                elif pres_tool.slide_position == "circle":
                    if pres_tool.already_imported is False:
                        n = len(pres_tool.slide_list) 
                        z_rot = 360/n                      #z rotation
                        alpha = (n-2)*180/n                #inner angle
                        s = 50                             #polygon side length
                        r2 = s/(2*tan(radians(180.0)/n))   #inner circle radius
                        #set rotation
                        bpy.context.object.rotation_euler[2] = radians(-i*z_rot-90)
                        #set location 
                        if n == 1:
                            bpy.context.object.location[0] = 0
                            bpy.context.object.location[1] = 0
                            bpy.context.object.location[2] = 0
                        elif n == 2:
                            bpy.context.object.location[0] = pow(-1,i)*25
                            bpy.context.object.location[1] = 0
                            bpy.context.object.location[2] = 0
                        else:
                            bpy.context.object.location[0] = cos(-i*2*pi/n)*r2
                            bpy.context.object.location[1] = sin(-i*2*pi/n)*r2
                            bpy.context.object.location[2] = 0
                    else:
                        bpy.context.object.location[0] = 0
                        bpy.context.object.location[1] = -i*30
                        bpy.context.object.location[2] = 0
                    
                pres_tool.slide_count += 1
                pres_tool.slides_chosen -= 1                            
                
                #append camera as its own object
                section = "\\Object\\"
                camera_name = file[2]
                filepath  = filename + section + camera_name
                directory = filename + section
                try:
                    bpy.ops.wm.append(filepath=filepath, filename=camera_name, directory=directory, link=False, instance_collections=True)
                    #make camera local and parent it to slide
                    bpy.ops.object.make_local(type='SELECT_OBJECT')
                    cam = bpy.data.objects[camera_name]
                    s = bpy.context.active_object #slide
                    cam.parent = s
                except:
                    self.report({'WARNING'}, bpy.context.active_object.name +' doesnt contain a camera, or its name is not "Camera".')

            else:
                #not .blend file
                self.report({'WARNING'}, os.path.split(filename)[1]+' FILE NOT FOUND')
         
        pres_tool.slide_count += n_tmp
        
        #create markers
        filename = pres_tool.slide_list[0][0]
        l = filename.split("\\")
        timed_dir = ("\\").join(l[:-1])
        m_name = os.path.join(timed_dir, "markers.txt")
        with open(m_name, "r") as f:
            for i, line in enumerate(f):
                splited = line.split(":")
                if splited[1].strip() == "":
                    continue
                min_frame = 999999
                max_frame = -1
                last_loop_start = -1
                markers = splited[1].split(";")
                markers = markers[:-1]
                for m in markers:
                    if "LS-" in m:
                        m_frame = m.split("-")
                        m_frame = m_frame[-1]
                        pres_tool.last_loop_start = int(m_frame)
                        bpy.context.scene.timeline_markers.new(name="LOOP_START", frame=int(m_frame))
                        if int(m_frame) > max_frame:
                            max_frame = int(m_frame)
                        if int(m_frame) < min_frame:
                            min_frame = int(m_frame)
                        last_loop_start = int(m_frame)
                    elif "LE-" in m:
                        m_frame = m.split("-")
                        m_frame = m_frame[-1]
                        pres_tool.loops[int(m_frame)] = pres_tool.last_loop_start
                        bpy.context.scene.timeline_markers.new(name="LOOP_END", frame=int(m_frame))
                        if int(m_frame) > max_frame:
                            max_frame = int(m_frame)
                        if int(m_frame) < min_frame:
                            min_frame = int(m_frame)
                        pres_tool.loops[int(m_frame)] = last_loop_start
                    else:
                        bpy.context.scene.timeline_markers.new(name="F_" + m, frame=int(m))
                        if int(m) > max_frame:
                            max_frame = int(m)
                        if int(m) < min_frame:
                            min_frame = int(m)
                        
                #automatic camera change
                create_camera_change(i, max_frame, min_frame, n_tmp)

        #convert camera keyframes to nla strips
        convert_all_to_nla()
        
        #fill the structure for nla changes
        for obj in bpy.context.scene.objects:
            if "COMPONENT TIMER" in obj.name:
                nla_name = obj.animation_data.nla_tracks[0].strips[0].name
                nla_start = obj.animation_data.nla_tracks[0].strips[0].frame_start
                nla_end = obj.animation_data.nla_tracks[0].strips[0].frame_end
                pres_tool.nla_strips[nla_name] = [nla_start, nla_end]
        tmp_dict = dict(sorted(pres_tool.nla_strips.items(), key=lambda item: item[1][0]))
        pres_tool.nla_strips = tmp_dict
            

        if presentation_handler not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(presentation_handler)
                
        if os.path.exists(m_name):
            os.remove(m_name)
            
        pres_tool.already_imported = True
        n_tmp = 0
                    
        return{'FINISHED'}

#------------------------------------------------------------    
    
class OverrideSlides(bpy.types.Operator):
    """! CLICK INTO 3D VIEWPORT FIRST ! Use to enable changes in the Presentation."""
    bl_idname = 'presentation.override_slides'
    bl_label = 'Override Slide Hierarchy in Outliner'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool

        if presentation_handler not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(presentation_handler)

        bpy.ops.wm.save_mainfile()
        
        #override hierarchies
        for area in bpy.context.screen.areas:
            if area.type == 'OUTLINER':
                override = bpy.context.copy()
                override['area'] = area
                bpy.ops.outliner.show_one_level(override)
                bpy.ops.outliner.select_all(override, action='SELECT')
                try:
                    bpy.ops.outliner.id_operation(override, type='OVERRIDE_LIBRARY_CREATE_HIERARCHY')
                except:
                    self.report({'WARNING'}, "INVALID CONTEXT.")
                    return{'CANCELLED'}
                bpy.ops.outliner.show_one_level(override, open=False)
                break
        
        # switch to Presentation workspace
        try:
            if bpy.data.workspaces["Presentation"] is not None:
                workspace = bpy.data.workspaces["Presentation"]
                bpy.context.window.workspace = workspace
        except:
            self.report({'WARNING'}, "Workspace \"Presentation\" not found. Use the PRESENTATION_TEMPLATE file for better results.")

        #fill the structure for nla changes and marker movement
        for obj in bpy.context.scene.objects:
            if "COMPONENT TIMER" in obj.name:
                nla_name = obj.animation_data.nla_tracks[0].strips[0].name
                nla_start = obj.animation_data.nla_tracks[0].strips[0].frame_start
                nla_end = obj.animation_data.nla_tracks[0].strips[0].frame_end
                pres_tool.nla_strips[nla_name] = [nla_start, nla_end]
                pres_tool.marker_timers[nla_name] = []
                #fill markers
                for m in bpy.context.scene.timeline_markers:
                    if nla_start <= m.frame <= nla_end:
                        pres_tool.marker_timers[nla_name].append(m)
        #sort nla strips                
        tmp_dict = dict(sorted(pres_tool.nla_strips.items(), key=lambda item: item[1][0]))
        pres_tool.nla_strips = tmp_dict          
                
        #create a collection for original slides
        try:
            if bpy.data.collections["COMPONENTS"] is not None:
                collection = bpy.data.collections["COMPONENTS"]
        except:
            collection = bpy.data.collections.new(name="COMPONENTS")
            bpy.context.scene.collection.children.link(collection)
        for obj in bpy.data.objects:
            if obj.instance_type == 'COLLECTION':
                comp_collection = get_parent_collection(obj)
                if comp_collection == "Master Collection":
                    collection.objects.link(obj)
                    bpy.context.scene.collection.objects.unlink(obj)
                else:
                    if comp_collection == "COMPONENTS":
                        continue
                    else:
                        collection.objects.link(obj)
                        bpy.data.collections[comp_collection].objects.unlink(obj)
                
        #create a collection for override slides
        try:
            if bpy.data.collections["OVERRIDES"] is not None:
                collection = bpy.data.collections["OVERRIDES"]
        except:
            collection = bpy.data.collections.new(name="OVERRIDES")
            bpy.context.scene.collection.children.link(collection)
        for col in bpy.data.collections:
            if col.override_library is not None:
                try:
                    bpy.context.scene.collection.children.unlink(col)
                    collection.children.link(col)
                except:
                    print(col.name, " is child collection, so its moved already")
                
        #create a collection for slide timers
        try:
            if bpy.data.collections["TIMERS"] is not None:
                collection = bpy.data.collections["TIMERS"]
        except:
            collection = bpy.data.collections.new(name="TIMERS")
            bpy.context.scene.collection.children.link(collection)
        for obj in bpy.context.scene.objects:
            if "COMPONENT TIMER" in obj.name and obj.name not in bpy.data.collections["TIMERS"].objects:
                timer = bpy.context.scene.objects.get(obj.name)
                collection.objects.link(obj)
                
                
        #filter NLA strips by timer collection - doesnt work (??)
        for area in bpy.context.screen.areas:
            #for area in screen.areas:
            if area.type == "NLA_EDITOR":
                for space in area.spaces:
                    if space.type == "NLA_EDITOR":
                        space.dopesheet.filter_collection = bpy.data.collections["TIMERS"]
                        break
        
        if presentation_handler not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(presentation_handler)
        
        pres_tool.overriden = True
           
        return{'FINISHED'}

        
#------------------------------------------------------------  


class RecalculateCameras(bpy.types.Operator):
    """Recalcultes camera transitions. Use after any change in the Presentation."""
    bl_idname = 'presentation.recalculate_cameras'
    bl_label = 'Recalculate camera interpolation after component order change.'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        sorted_strips = dict(sorted(pres_tool.nla_strips.items(), key=lambda item: item[1][0]))
        sorted_markers = list(sorted(bpy.context.scene.timeline_markers.items(), key=lambda item: item[1].frame))
        
        #take the camera from end marker and set interpolation constrains to next start marker camera
        prev_camera = None
        const_start = -1
        for i, s in enumerate(sorted_strips):
            start = sorted_strips[s][0]
            end   = sorted_strips[s][1]
            for m in sorted_markers:
                if m[1].frame == start:
                    if m[1].camera is not None:
                        #remove constraints
                        try:
                            constr = m[1].camera.constraints["Copy Location"]
                            m[1].camera.constraints.remove(constr)
                            constr = m[1].camera.constraints["Copy Rotation"]
                            m[1].camera.constraints.remove(constr)
                            constr = m[1].camera.constraints["Copy Scale"]
                            m[1].camera.constraints.remove(constr)
                        except:
                            print(m[1].camera, " DOESNT HAVE CONSTRAINS")
                        #set it as target for previous camera
                        if i != 0:
                            const_loc = prev_camera.constraints.new('COPY_LOCATION')
                            const_rot = prev_camera.constraints.new('COPY_ROTATION')
                            const_scl = prev_camera.constraints.new('COPY_SCALE')
                            const_loc.target = m[1].camera
                            const_rot.target = m[1].camera
                            const_scl.target = m[1].camera
                            const_loc.influence = 0
                            const_rot.influence = 0
                            const_scl.influence = 0
                            prev_camera.keyframe_insert(data_path='constraints["Copy Location"].influence', frame=const_start)
                            prev_camera.keyframe_insert(data_path='constraints["Copy Rotation"].influence', frame=const_start)
                            prev_camera.keyframe_insert(data_path='constraints["Copy Scale"].influence', frame=const_start)
                            const_loc.influence = 1
                            const_rot.influence = 1
                            const_scl.influence = 1
                            prev_camera.keyframe_insert(data_path='constraints["Copy Location"].influence', frame=m[1].frame)
                            prev_camera.keyframe_insert(data_path='constraints["Copy Rotation"].influence', frame=m[1].frame)
                            prev_camera.keyframe_insert(data_path='constraints["Copy Scale"].influence', frame=m[1].frame)
                        prev_camera = m[1].camera
                elif m[1].frame == end:
                    #if its not the last one -> remember it next round
                    if i != len(sorted_strips)-1:
                        const_start = m[1].frame
                        
        convert_all_to_nla()
        
        return{'FINISHED'}


#------------------------------------------------------------  

class DeleteSlide(bpy.types.Operator):
    """Delete selected Component, its markers and timer."""
    bl_idname = 'presentation.delete_slide'
    bl_label = 'Delete Selected Slide(s)'
    
    @classmethod
    def poll(cls, context):
        comp = []
        for obj in bpy.context.selected_objects:
            if obj.instance_type == 'COLLECTION':
                comp.append(obj)
        if len(comp) != 0:
            return True
        else:
            return False
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        slides = []
        deleted = 0
        
        if len(bpy.context.selected_objects) == 0:
            return{'CANCELLED'} 
        
        for s in bpy.context.selected_objects:
            if s.instance_type == 'COLLECTION':
                timer_strip = ""
                #delete markers
                for strip in pres_tool.marker_timers:
                    if s.name + '.blend TIMER STRIP' in strip:
                        timer_strip = strip
                        for m in pres_tool.marker_timers[strip]:
                            bpy.context.scene.timeline_markers.remove(m)
                pres_tool.marker_timers.pop(timer_strip)
                pres_tool.nla_strips.pop(timer_strip)
                #delete empty timer
                for obj in bpy.context.scene.objects:
                    if "COMPONENT TIMER" in obj.name:
                        nla_name = obj.animation_data.nla_tracks[0].strips[0].name
                        if nla_name == timer_strip:
                            bpy.data.objects.remove(obj)
                #delete component and children from scene
                for child in s.children:
                    child.select_set(True)
                #bpy.data.objects.remove(s, do_unlink=True)
                deleted += 1
            else:
                s.select_set(False)
                
        bpy.ops.object.delete()
        
        if deleted == 0:
            return{'CANCELLED'}
        
        pres_tool.slide_count -= deleted
        if pres_tool.slide_count == 0:
            pres_tool.already_imported = False
                
        return{'FINISHED'}
    
    
#------------------------------------------------------------  

class ResetPresentation(bpy.types.Operator):
    """Sets Component count to zero. Use after accidentaly deleting Components by X or Delete."""
    bl_idname = 'presentation.reset'
    bl_label = 'Are you sure you want to reset your progress?'
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool

        bpy.context.scene.my_pres_tool.slide_count = 0
        bpy.context.scene.my_pres_tool.slide_list = []
        bpy.context.scene.my_pres_tool.image_count = 0
        bpy.context.scene.my_pres_tool.slides_chosen = 0
        bpy.context.scene.my_pres_tool.image_chosen = 0
        bpy.context.scene.my_pres_tool.already_imported = False
        bpy.context.scene.my_pres_tool.overriden = False

        bpy.context.scene.timeline_markers.clear()

        return{'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)



# -------------------------------------------------------------------
#    SLIDESHOW OPERATORS
# ------------------------------------------------------------------- -

class StartPresentation(bpy.types.Operator):
    """"Sets up camera, goes into fullscreen and starts the presentation"""
    bl_label = "Start the Presentation"
    bl_idname = "presentation.start"
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        bpy.ops.screen.animation_cancel()
        bpy.context.scene.frame_current = 1

        if presentation_handler not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(presentation_handler)
            
        workspace = None
        
        # switch to Slideshow workspace
        try:
            if bpy.data.workspaces["Slideshow"] is not None:
                workspace = bpy.data.workspaces["Slideshow"]
                bpy.context.window.workspace = workspace
        except:
            self.report({'WARNING'}, "Workspace \"Slideshow\" not found. Use the PRESENTATION_TEMPLATE file, or create your own \"Slideshow\" Workspace.")
            workspace = bpy.data.workspaces["Layout"]
            bpy.context.window.workspace = workspace

        # set rendered view
        for screen in workspace.screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'RENDERED'
                            space.region_3d.view_perspective = 'CAMERA'
                            #bpy.ops.screen.screen_full_area(use_hide_panels=True)
        if pres_tool.fullscreen:
            bpy.ops.wm.window_fullscreen_toggle()
            
        for camera in bpy.data.cameras:
            camera.passepartout_alpha = 1
            
        return {'FINISHED'}
    

#------------------------------------------------------------  

class EndPresentation(bpy.types.Operator):
    """"Stops the presentation and goes into Presentation layout."""
    bl_label = "Stop the Presentation"
    bl_idname = "presentation.end"
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        bpy.ops.screen.animation_cancel()
        
        # switch to Presentation workspace
        try:
            if bpy.data.workspaces["Presentation"] is not None:
                bpy.context.window.workspace = bpy.data.workspaces["Presentation"]
        except:
            self.report({'WARNING'}, "Workspace \"Presentation\" not found. Swicthing to Layout Workspace.")
            bpy.context.window.workspace = bpy.data.workspaces["Layout"]

        if pres_tool.fullscreen:
            bpy.ops.wm.window_fullscreen_toggle()
                
        return {'FINISHED'}


#------------------------------------------------------------  
        
             
class RotateCameraUp(bpy.types.Operator):
    """Plays animation until next slide"""
    bl_label = "NEXT SLIDE"
    bl_idname = "wm.rotatecamup"  
    
    
    def draw(self, context):
        layout = self.layout
        layout.label(icon= 'PLAY')
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool

        if presentation_handler not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(presentation_handler)
        
        check_marker_loops()

        #check if im in a loop
        for m in bpy.context.scene.my_pres_tool.loops:
            if m > bpy.context.scene.frame_current > bpy.context.scene.my_pres_tool.loops[m]:
                #break the loop
                bpy.context.scene.frame_current = m+1
                bpy.ops.screen.animation_play()
        bpy.ops.screen.animation_play()
        
        return {'FINISHED'}

#------------------------------------------------------------  

class RotateCameraDown(bpy.types.Operator):
    """Plays animation until previous slide"""
    bl_label = "PREVIOUS SLIDE"
    bl_idname = "wm.rotatecamdown"  
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool

        if presentation_handler not in bpy.app.handlers.frame_change_pre:
            bpy.app.handlers.frame_change_pre.append(presentation_handler)

        check_marker_loops()

        #check if im in a loop
        for m in pres_tool.loops:
            if bpy.context.scene.frame_current > pres_tool.loops[m] and bpy.context.scene.frame_current < m:
                #break the loop
                bpy.context.scene.frame_current = pres_tool.loops[m] - 1
                bpy.ops.screen.animation_play(reverse=True)
        bpy.ops.screen.animation_play(reverse=True)
        
        return {'FINISHED'}

#------------------------------------------------------------      
    
class JumpToStart(bpy.types.Operator):
    """Jumps to presentation start (first frame)"""
    bl_label = "JUMP TO START"
    bl_idname = "wm.jumptostart"  
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        bpy.ops.screen.animation_cancel()
        bpy.context.scene.frame_current = bpy.context.scene.frame_start
        
        return {'FINISHED'}

#------------------------------------------------------------  
    
class JumpToEnd(bpy.types.Operator):
    """Jumps to presentation end (last frame)"""
    bl_label = "JUMP TO END"
    bl_idname = "wm.jumptoend" 
    
    def execute(self, context):
        pres_tool = bpy.context.scene.my_pres_tool
        
        bpy.ops.screen.animation_cancel()
        bpy.context.scene.frame_current = bpy.context.scene.frame_end
        
        return {'FINISHED'}



# -----------------------------------------------------------------------------------------------------
#                                               REGISTER
# -----------------------------------------------------------------------------------------------------


addon_keymaps = []
my_classes =    [
                PresMenuProperties, 
                SLIDE_PARENT_PT_panel, 
                IMAGE_PT_panel, 
                TEMPLATE_PT_panel, 
                GENERATING_PT_panel, 
                PRESENTATION_PARENT_PT_panel, 
                IMPORT_SETTINGS_PT_panel, 
                PRESENTATION_SETTINGS_PT_panel,
                PRESENTATION_RESET_PT_panel, 
                PRESENTING_PARENT_PT_panel, 
                PRESENTATION_START_PT_panel, 
                NAVIGATION_PT_panel,
                AssignObjectType, 
                GenerateJsonFile, 
                CreateComponentFromTemplate, 
                ChooseSlide, 
                ChooseImage, 
                OverrideSlides, 
                RecalculateCameras, 
                AddSlide, 
                AddImage, 
                DeleteSlide, 
                ResetPresentation, 
                StartPresentation,
                EndPresentation, 
                RotateCameraUp, 
                RotateCameraDown, 
                JumpToStart, 
                JumpToEnd
                ]


def register():
    for cls in my_classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.my_pres_tool = bpy.props.PointerProperty(type=PresMenuProperties)
    
    #append handler
    bpy.app.handlers.frame_change_pre.append(presentation_handler)
    bpy.app.handlers.depsgraph_update_pre.append(nla_handler)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        #create new keymap shortcuts
        kmi = km.keymap_items.new("wm.rotatecamup", type='PAGE_UP', value='PRESS')
        kmi = km.keymap_items.new("wm.rotatecamdown", type='PAGE_DOWN', value='PRESS')
        kmi = km.keymap_items.new("wm.jumptostart", type='HOME', value='PRESS')
        kmi = km.keymap_items.new("wm.jumptoend", type='END', value='PRESS')
        kmi = km.keymap_items.new("presentation.start", type='F5', value='PRESS')
        kmi = km.keymap_items.new("presentation.end", type='F6', value='PRESS')
        addon_keymaps.append((km, kmi))
   
   
def unregister():
    for cls in my_classes:
        bpy.utils.unregister_class(cls)
        
    #append handler
    try:
        bpy.app.handlers.depsgraph_update_pre.remove(nla_handler)
        bpy.app.handlers.frame_change_pre.remove(presentation_handler)
    except:
        print("Couldnt unregister the handlers.")
    
    for km,kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()    
   
    del bpy.types.Scene.my_pres_tool
   
   
if __name__ == "__main__":
    register()
    
