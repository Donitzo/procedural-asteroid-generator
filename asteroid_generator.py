# ============================================================================================================
# Procedural Asteroid Generator
#
# This script procedurally generates animated asteroids in Blender,
# complete with style, shape, props, and texture variation.
#
# GitHub Repository: https://github.com/donitzo/procedural-asteroid-generator
# Author: Donitz
# License: MIT
# Version: 1.0.3
# ============================================================================================================

# ============================================================================================================
# Attribution
# ============================================================================================================

# FilterForge filters used to create textures:
#  - [Filter 9445](https://www.filterforge.com/filters/9445.html)
#  - [Filter 235](https://www.filterforge.com/filters/235.html)
#  - [Filter 3215](https://www.filterforge.com/filters/3215.html)
#  - [Filter 7402](https://www.filterforge.com/filters/7402.html)
#  - [Filter 13302](https://www.filterforge.com/filters/13302.html)
#
# Triplanar normal calculation adapted from:
#  - [Blender StackExchange post by Nathan](https://blender.stackexchange.com/questions/270490/how-to-fix-box-projected-normal-maps)

# ============================================================================================================
# Quick start
# ============================================================================================================

# This project can either:
#   - Generate a grid of procedurally created asteroid meshes.
#   - Render animated spritesheets and APNGs (if `CREATE_ASTEROIDS_ONLY` is set to `False`).
#
# Note: APNG uses RGBA for compatibility. Palette indexing is only applied to the spritesheet.
#
# The project also creates a `preview_timestamp.html` file for easy viewing of generated asteroids.
# You can open it in any browser. The seed can be copied from existing asteroids to regenerate either the style or shape.
#
# Requirements:
#   - Blender 4.0 or newer
#   - `Pillow` (Python Imaging Library) installed for image handling
#   - `Extra Mesh Objects` Extension installed in Blender
#
# To install Pillow inside Blender's Python environment (on Windows):
# ```console
# "C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\bin\python.exe" -m pip install Pillow --target="C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\lib\site-packages"
# ```
#
# To run the script:
#   1. Open the `asteroid_generator.xxx.blend` file in Blender.
#   2. Open the `Text Editor` and the script named `asteroid_generator.py`.
#   4. Adjust the configuration parameters as needed (see section below).
#   5. Click `Run Script` or press Alt+P to start generation.
#   6. Wait for the script to finish. Check the system console for progress or errors.
#   7. When done, open `preview.html` (in the output folder) to view all generated asteroids in a browser.

# ============================================================================================================
# Prop setup
# ============================================================================================================

# Props must be organized under a Blender collection called `Props`.
# Each **child collection** inside `Props` represents a **prop type**,
# and should contain one or more objects that will be randomly selected.
# Each asteroid can only select props from within one **prop type**, or none.
#
# Each prop object name can include metadata in square brackets at the end of its name:
#   - `angle`: Max rotation variation in degrees from the surface normal.
#   - `scale`: Multiplier for random scale variation (centered around 1.0).
#   - `height`: Maximum upward offset from the asteroid surface.
#
# Example prop name:
#   `Antenna [angle=25,scale=0.1,height=0.2]`

# ============================================================================================================
# Material setup
# ============================================================================================================

# Textures are loaded dynamically based on PNG files in `TEXTURE_PATH` using filenames of the form:
#   `name_diffuse.png`
#   `name_normal.png`
#   `name_emission.png [optional]`
#
# Example `rock` material:
#   `rock_diffuse.png`
#   `rock_normal.png`
#   `rock_emission.png`
#
# If edited, the base material (named `Asteroid`) can contain the following named nodes:
#   - Image Texture node: `Diffuse`
#   - Image Texture node: `Normal`
#   - Image Texture node: `Emission`
#   - Value node: `Triplanar Scale`
#   - Value node: `Roughness`
#   - RGB node: `Tint`

import bpy
import math
import numpy as np
import os
import random
import re
import warnings

from datetime import datetime
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree
from PIL import Image, ImageFilter

# ============================================================================================================
# Configuration parameters
# ============================================================================================================

# Folder where spritesheets and APNGs will be saved.
OUTPUT_PATH = bpy.path.abspath('//generated_asteroids')
# Folder where the asteroid texture sets (diffuse, normal, etc.) are located.
TEXTURE_PATH = bpy.path.abspath('//textures')
# Folder where the palette .png images are located.
PALETTE_PATH = bpy.path.abspath('//palettes')
# The name of the frames directory.
FRAMES_DIRECTORY = 'frames'

# Fixed seed for asteroid style (materials, props and colors). Use None for random.
STYLE_SEED = None
# Fixed seed for asteroid shape (mesh geometry and prop placement). Use None for random.
SHAPE_SEED = None
# Fixed seed for asteroid spin. Use None for random.
SPIN_SEED = None
# Spin axis override. Example: (1.0, 0.0, 0.0)
SPIN_AXIS = None

# Maximum resolution of each asteroid frame (used for spritesheets).
RESOLUTION_MAX = 512
# Scale the rendering to force all sprites to be of RESOLUTION_MAX (slows down rendering significantly).
SCALE_TO_FIT = False
# Extra margin around each asteroid in the spritesheet, in pixels.
MARGIN_PIXELS = 8
# Total number of frames in the asteroid animation loop.
FRAME_COUNT = 64
# Frames per second for the animated asteroid (used in APNG export).
FRAMES_PER_SECOND = 24
# Whether to apply anti-aliasing in output renders.
USE_ANTIALIASING = True
# Alpha clip threshold used to trim translucent borders. Use None to disable.
ALPHA_CLIP = 127
# The name of the .png palette image in the palettes directory (without extension). Use None to disable.
PALETTE_NAME = None
# Size of the median filter applied to the images. Use None to disable.
MEDIAN_FILTER_SIZE = None
# The number of 1-pixel edges to trim before outlining. Use None to disable.
TRIM_PIXEL_EDGES = None
# List of colors to apply as 1-pixel outlines around each asteroid.
# Example: [(0, 0, 0, 255), (255, 255, 255, 255)]  # First pass black, second pass white.
PIXEL_OUTLINE_COLORS = []

# If True, generate only the asteroid objects in a grid without rendering.
# If False, animate and render each asteroid as its own spritesheet and APNG.
CREATE_ASTEROIDS_ONLY = False
# Number of asteroids to generate.
ASTEROID_COUNT = 8
# Spacing between asteroids in the grid layout.
ASTEROID_SPACING = 5
# Number of columns in the asteroid layout grid.
ASTEROID_COLUMNS = 16
# Minimum base scale of an asteroid.
ASTEROID_SCALE_MIN = 0.25
# Maximum base scale of an asteroid.
ASTEROID_SCALE_MAX = 2.0
# Amount of non-uniform axis variation for each asteroid (e.g., stretched or squashed shapes).
ASTEROID_AXIS_SCALE_VARIATION = 0.5
# If True, restrict asteroid rotation to only the Z-axis.
ONLY_Z_ROTATION = False

# Chance [0.0 - 1.0] that an asteroid gets props attached.
PROP_CHANCE = 0.5
# Chance [0.0 - 1.0] that the prop is assigned the asteroid material.
PROP_MATCH_ASTEROID_MATERIAL_CHANCE = 0.33
# Minimum number of props on a single asteroid (if props are added).
PROP_COUNT_MIN = 1
# Maximum number of props on a single asteroid.
PROP_COUNT_MAX = 32
# Minimum random scale multiplier for props.
PROP_SCALE_MIN = 0.2
# Maximum random scale multiplier for props.
PROP_SCALE_MAX = 1.0
# If True, scale props proportionally to the asteroid's base size (in addition to the prop scale).
SCALE_PROPS_BY_ASTEROID = True

# Minimum surface roughness value for asteroid materials.
ROUGHNESS_MIN = 0.2
# Maximum surface roughness value for asteroid materials.
ROUGHNESS_MAX = 1.0
# Minimum scale value for triplanar texturing.
TRIPLANAR_SCALE_MIN = 0.3
# Maximum scale value for triplanar texturing.
TRIPLANAR_SCALE_MAX = 1.0
# Maximum deviation for color tint on the asteroid (e.g., +-0.3 per color channel).
TINT_MAX_VARIATION = 0.3

# Convenient way to handle templates
#TEMPLATE = 'pixel-art-dusty-space'
#TEMPLATE = 'pixel-art-2bit-demichrome-32x'
#TEMPLATE = 'pixel-art-steam-lords-32x'
#TEMPLATE = 'pixel-art-sweetie-16-32x'
TEMPLATE = 'realistic'

if TEMPLATE.startswith('pixel-art-'):
    RESOLUTION_MAX = 256
    MARGIN_PIXELS = 2
    TRIM_PIXEL_EDGES = 1
    USE_ANTIALIASING = False
    ALPHA_CLIP = 127
if TEMPLATE.startswith('pixel-art-2bit-demichrome-32x'):
    PALETTE_NAME = '2bit-demichrome-32x'
    PIXEL_OUTLINE_COLORS = [(50, 60, 90, 255)]
elif TEMPLATE.startswith('pixel-art-steam-lords-32x'):
    PALETTE_NAME = 'steam-lords-32x'
elif TEMPLATE.startswith('pixel-art-sweetie-16-32x'):
    RESOLUTION_MAX = 40
    SCALE_TO_FIT = True
    PALETTE_NAME = 'sweetie-16-32x'
    PIXEL_OUTLINE_COLORS = [(0, 0, 0, 255)]
elif TEMPLATE.startswith('pixel-art-dusty-space'):
    PALETTE_NAME = 'dusty-space'
    PIXEL_OUTLINE_COLORS = [(0, 0, 0, 255), (255, 255, 255, 255)]
elif TEMPLATE.startswith('realistic'):
    pass

# The timestamp is used for file naming
now = datetime.now()
timestamp = now.strftime('%Y%m%dT%H%M%S') + now.strftime('%f')[:3]
os.makedirs(os.path.join(OUTPUT_PATH, f'output_{timestamp}'))

# Load color palette from an image
if not PALETTE_NAME is None:
    image = Image.open(os.path.join(PALETTE_PATH, f'{PALETTE_NAME}.png')).convert('RGB')

    unique_colors = list({image.getpixel((x, y)) for y in range(image.height) for x in range(image.width)})
    if len(unique_colors) > 255:
        raise ValueError('Palette image contains more than 256 unique colors')

    # RGB palette
    palette_rgb = [channel for color in unique_colors for channel in color]
    palette_rgb_image = Image.new('P', (1, 1))
    palette_rgb_image.putpalette(palette_rgb)

    # Get the first unused color for alpha
    # (apparently, the alpha color must be unique in indexed images)
    for i in range(256):
        color = (i, i, i)
        if not color in unique_colors:
            transparency_color = list(color)
            break

    # Create palette with transparency color
    palette_rgb_with_transparency = [
        channel
        for i in range(0, len(palette_rgb), 3)
        for channel in (palette_rgb[i], palette_rgb[i + 1], palette_rgb[i + 2])
    ] + transparency_color
    transparency_index = len(unique_colors)

# Index an image with the loaded color palette. Adds a transparency color.
def index_image(image_rgba, return_rgba=False):
    if PALETTE_NAME is None:
        return image_rgba

    # Quantize the image with the RGB palette
    indexed = image_rgba.convert('RGB').quantize(palette=palette_rgb_image, dither=Image.NONE)

    # Replace transparent pixels with the transparency index
    alpha = np.array(image_rgba.getchannel('A'))
    data_l = np.array(indexed)
    data_l[alpha <= 127] = transparency_index

    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        indexed = Image.fromarray(data_l, mode='P')

    # Set the palette with transparency index
    indexed.putpalette(palette_rgb_with_transparency)
    indexed.im.putpalettealpha(transparency_index, 0)

    if not return_rgba:
        return indexed

    # Convert to RGBA and force full transparency where needed
    data_rgba = np.array(indexed.convert('RGBA')).copy()
    data_rgba[data_l == transparency_index] = [0, 0, 0, 0]

    return Image.fromarray(data_rgba)

# Postprocess image
def postprocess_image(image_rgba):
    original_alpha = np.array(image_rgba)[..., 3]

    # Apply median filter
    if MEDIAN_FILTER_SIZE is not None:
        image_rgba = image_rgba.filter(ImageFilter.MedianFilter(MEDIAN_FILTER_SIZE))

    # Replace alpha channel after filtering
    data = np.array(image_rgba)
    data[..., 3] = original_alpha

    # Trim edges
    if not TRIM_PIXEL_EDGES is None:
        for _ in range(TRIM_PIXEL_EDGES):
            p = np.pad(data[..., 3], 1, mode='constant', constant_values=0)
            inner = (
                (p[1:-1, 1:-1] == 255) &
                (p[:-2, 1:-1] == 255) &
                (p[2:, 1:-1] == 255) &
                (p[1:-1, :-2] == 255) &
                (p[1:-1, 2:] == 255)
            )
            data[..., 3] = np.where(inner, data[..., 3], 0)

    # Add outlines
    for color in PIXEL_OUTLINE_COLORS:
        p = np.pad(data[..., 3], pad_width=1, mode='constant', constant_values=0)
        mask_outline = (
            (data[..., 3] < 255) & (
                (p[:-2, 1:-1] == 255) |
                (p[2:, 1:-1] == 255) |
                (p[1:-1, :-2] == 255) |
                (p[1:-1, 2:] == 255)
            )
        )
        data[mask_outline] = color

    return Image.fromarray(data)

# Load prop types and metadata

props_collection = bpy.data.collections.get('Props')

prop_name_pattern = re.compile(r'\[(.*?)\]$')

prop_types = {}

for type_collection in props_collection.children:
    props = []

    prop_types[type_collection.name] = props

    for obj in type_collection.objects:
        angle = 0.0
        scale = 0.0
        height = 0.0

        match = prop_name_pattern.search(obj.name)
        if match:
            params = match.group(1).split(',')
            for param in params:
                if '=' in param:
                    key, value = param.split('=')
                    key = key.strip().lower()
                    try:
                        value = float(value)
                    except ValueError:
                        continue

                    if key == 'angle':
                        angle = value
                    elif key == 'scale':
                        scale = value
                    elif key == 'height':
                        height = value
                    else:
                        print(f'Invalid property "{key}"')

        props.append({
            'object': obj,
            'angle': angle,
            'scale': scale,
            'height': height
        })

# List textures

textures = {}

for file in os.listdir(TEXTURE_PATH):
    if file.endswith('.png'):
        name, kind = file.rsplit('_', 1)
        kind = kind.replace('.png', '').lower()
        if name not in textures:
            textures[name] = { 'name': name }
        textures[name][kind] = os.path.join(TEXTURE_PATH, file)

materials_collection = bpy.data.collections.get('Materials')

# Create the asteroids

apng_paths = []

for asteroid_index in range(ASTEROID_COUNT):
    print('Creating asteroid %i out of %i' % (asteroid_index + 1, ASTEROID_COUNT))

    # Deselect objects
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection

    # Delete old asteroids
    if not CREATE_ASTEROIDS_ONLY or asteroid_index == 0:
        for obj in bpy.data.objects:
            if obj.name.startswith("Asteroid") and obj.parent is None:
                for obj2 in [obj] + list(obj.children_recursive):
                    obj2.select_set(True)

        bpy.context.view_layer.objects.active = None
        bpy.ops.object.delete()

    # Randomize the asteroid style properties
    style_seed = random.SystemRandom().randint(0, 1e8) if STYLE_SEED is None else STYLE_SEED
    random.seed(style_seed)

    triplanar_scale = random.uniform(TRIPLANAR_SCALE_MIN, TRIPLANAR_SCALE_MAX)

    roughness = random.uniform(ROUGHNESS_MIN, ROUGHNESS_MAX)

    color_tint = (
        1.0 - random.uniform(-TINT_MAX_VARIATION, TINT_MAX_VARIATION),
        1.0 - random.uniform(-TINT_MAX_VARIATION, TINT_MAX_VARIATION),
        1.0 - random.uniform(-TINT_MAX_VARIATION, TINT_MAX_VARIATION),
        1.0,
    )

    prop_name = random.choice(list(prop_types.keys())) if random.random() < PROP_CHANCE else ''
    prop_scale = random.uniform(PROP_SCALE_MIN, PROP_SCALE_MAX)
    prop_match_material = random.random() < PROP_MATCH_ASTEROID_MATERIAL_CHANCE

    material_name = random.choice(list(textures.keys()))

    # Randomization for shape
    shape_seed = random.SystemRandom().randint(0, 1e8) if SHAPE_SEED is None else SHAPE_SEED
    random.seed(shape_seed)

    # Select a random scale for the new asteroid
    base_scale = random.uniform(ASTEROID_SCALE_MIN, ASTEROID_SCALE_MAX)

    # Generate the asteroid using the 'Rock Generator' addon included with the 'Extra Mesh Objects' extension
    try:
        bpy.ops.mesh.add_mesh_rock(
            num_of_rocks=1,
            scale_X=(base_scale, (1 + ASTEROID_AXIS_SCALE_VARIATION) * base_scale),
            scale_Y=(base_scale, (1 + ASTEROID_AXIS_SCALE_VARIATION) * base_scale),
            scale_Z=(base_scale, (1 + ASTEROID_AXIS_SCALE_VARIATION) * base_scale),
            deform=7.5,
            rough=3.0,
            detail=3,
            display_detail=2,
            smooth_fac=0.5,
            smooth_it=1,
            use_random_seed=False,
            user_seed = random.randint(0, 1048575)
        )
    except Exception as e:
        if bpy.context.active_object:
            bpy.ops.object.delete()
        print(f"Asteroid generation failed: {e}")
        continue

    # Select the newly created asteroid
    asteroid = bpy.context.active_object
    asteroid.name = f'Asteroid{asteroid_index}'

    # Apply all modifiers
    for modifier in asteroid.modifiers:
        bpy.ops.object.modifier_apply(modifier=modifier.name)

    # Set center of mass and center asteroid
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
    x = asteroid_index % ASTEROID_COLUMNS
    y = asteroid_index // ASTEROID_COLUMNS
    asteroid.location = (x * ASTEROID_SPACING, -y * ASTEROID_SPACING, 0.0)\
        if CREATE_ASTEROIDS_ONLY else (0.0, 0.0, 0.0)

    # Load random textures for the asteroid material
    material = bpy.data.materials.get('Asteroid')
    if CREATE_ASTEROIDS_ONLY:
        material = material.copy()
        material.name = f'Asteroid{asteroid_index}'
    asteroid.data.materials.append(material)

    # Update values in material nodes

    def find_nodes(node_tree, node_type=None, name=None):
        results = []
        for node in node_tree.nodes:
            if node.type == 'GROUP':
                results.extend(find_nodes(node.node_tree, node_type, name))
            else:
                if (node_type is None or node.type == node_type) and (name is None or node.name == name):
                    results.append(node)
        return results

    texture_set = textures[material_name]

    for node in find_nodes(material.node_tree, node_type='TEX_IMAGE'):
        if node.name == 'Diffuse':
            node.image = bpy.data.images.load(texture_set['diffuse'], check_existing=True)\
                if 'diffuse' in texture_set else None
        elif node.name == 'Normal':
            node.image = bpy.data.images.load(texture_set['normal'], check_existing=True)\
                if 'normal' in texture_set else None
            if node.image:
                node.image.colorspace_settings.name = 'Non-Color'
        elif node.name == 'Emission':
            node.image = bpy.data.images.load(texture_set['emission'], check_existing=True)\
                if 'emission' in texture_set else None

    for node in find_nodes(material.node_tree, node_type='VALUE'):
        if node.name == 'Triplanar Scale':
            node.outputs[0].default_value = triplanar_scale
        elif node.name == 'Roughness':
            node.outputs[0].default_value = roughness

    for node in find_nodes(material.node_tree, node_type='RGB'):
        if node.name == 'Tint':
            node.outputs[0].default_value = color_tint

    # Create props

    prop_count = 0 if not prop_name in prop_types else random.randint(PROP_COUNT_MIN, PROP_COUNT_MAX)

    if prop_count > 0:
        # Create a graph for raycasting
        depsgraph = bpy.context.evaluated_depsgraph_get()
        bvhtree = BVHTree.FromObject(asteroid.evaluated_get(depsgraph), depsgraph)

        for i in range(prop_count):
            # Generate a random spherical direction
            while True:
                direction = Vector((
                    random.uniform(-1, 1),
                    random.uniform(-1, 1),
                    random.uniform(-1, 1)
                ))
                if direction.length_squared > 1e-5 and direction.length_squared <= 1.0:
                    break
            direction = direction.normalized()

            # Perform the raycast
            location, normal, index, dist = bvhtree.ray_cast(direction * 1000.0, -direction)

            # If the asteroid was hit
            if not location is None:
                # Select a random prop
                prop_info = random.choice(prop_types[prop_name])

                # Duplicate the prop
                prop = prop_info['object'].copy()
                prop.data = prop_info['object'].data.copy()
                bpy.context.collection.objects.link(prop)

                # Use the asteroid material for the prop
                if prop_match_material:
                    prop.data.materials.clear()
                    prop.data.materials.append(material)

                # Randomize scale
                scale = prop_scale * (1 + random.uniform(-prop_info['scale'], prop_info['scale']))
                if SCALE_PROPS_BY_ASTEROID:
                    scale *= base_scale
                prop.scale = (scale, scale, scale)

                # Create a random axis perpendicular to the normal
                tangent = normal.cross(Vector((0, 0, 1)))
                if tangent.length < 1e-5:
                    tangent = normal.cross(Vector((1, 0, 0)))
                tangent.normalize()

                # Rotate the normal
                max_angle_rad = math.radians(prop_info['angle'])
                angle_variation = random.uniform(-max_angle_rad, max_angle_rad)
                rotation = Quaternion(tangent, angle_variation)
                up = Vector((0, 0, 1))
                prop.rotation_mode = 'QUATERNION'
                prop.rotation_quaternion = up.rotation_difference(rotation @ normal)

                # Apply height offset along normal
                height_offset = prop_info['height'] * random.random()
                prop.location = location + (normal * height_offset)

                # Parent to asteroid
                prop.parent = asteroid

    if CREATE_ASTEROIDS_ONLY:
        continue

    # Sandomization for spin
    spin_seed = random.SystemRandom().randint(0, 1e6) if SPIN_SEED is None else SPIN_SEED
    random.seed(spin_seed)

    # Create a random rotation axis
    if ONLY_Z_ROTATION:
        axis = Vector((0.0, 0.0, -1.0))
    elif not SPIN_AXIS is None:
        axis = Vector(SPIN_AXIS).normalized()
    else:
        axis = Vector((random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(-1, 1))).normalized()

    # Create keyframes rotating the asteroid a full 360 degrees
    asteroid.rotation_mode = 'QUATERNION'
    for i in range(FRAME_COUNT):
        angle = math.radians((i / FRAME_COUNT) * 360)
        asteroid.rotation_quaternion = Quaternion(axis, angle)
        asteroid.keyframe_insert(data_path='rotation_quaternion', frame=i)
        bpy.context.scene.frame_set(i)

    for curve in asteroid.animation_data.action.fcurves:
        for kp in curve.keyframe_points:
            kp.interpolation = 'LINEAR'
        curve.modifiers.new(type='CYCLES')

    target_size = RESOLUTION_MAX - MARGIN_PIXELS * 2
    size_test = SCALE_TO_FIT
    asteroid_scale = 1.0
    attempts = 0

    while True:
        attempts += 1
        if attempts > 128:
            raise RuntimeError('Unable to scale asteroid to fit inside camera.')

        # Render the animation
        scene = bpy.context.scene
        scene.render.image_settings.file_format = 'PNG'
        scene.render.resolution_x = RESOLUTION_MAX
        scene.render.resolution_y = RESOLUTION_MAX
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = True
        scene.frame_start = 0
        scene.frame_end = FRAME_COUNT - 1
        bpy.context.scene.display.render_aa = '8' if USE_ANTIALIASING else 'OFF'

        frames_path = os.path.join(OUTPUT_PATH, FRAMES_DIRECTORY)
        os.makedirs(frames_path, exist_ok=True)
        scene.render.filepath = bpy.path.abspath(os.path.join(frames_path, 'frame_'))
        bpy.ops.render.render(animation=True)

        # Load frames into memory

        frames = []
        max_side = 0
        touching_edge = False

        for i in range(FRAME_COUNT):
            # Load frame
            path = os.path.join(OUTPUT_PATH, FRAMES_DIRECTORY, f'frame_{i:04d}.png')
            image = Image.open(bpy.path.abspath(path)).convert('RGBA')

            width, height = image.size
            data = np.array(image)

            # Check if touching edge
            for y in range(height):
                if data[y, width - 1][3] > 0 or data[y, 0][3] > 0:
                    touching_edge = True
            for x in range(width):
                if data[height - 1, x][3] > 0 or data[0, x][3] > 0:
                    touching_edge = True

            # Alpha clip
            if not ALPHA_CLIP is None:
                data[..., 3] = np.where(data[..., 3] <= ALPHA_CLIP, 0, 255)
                image = Image.fromarray(data)

            # Calculate maximum size
            for y in range(height):
                for x in range(width):
                    if data[y, x][3] > 0:
                        max_side = max(max_side, abs(x - RESOLUTION_MAX / 2), abs(y - RESOLUTION_MAX / 2))

            frames.append(image)

        # If size test, scale asteroid to exactly match the required resolution
        if size_test:
            if max_side * 2 < target_size / 2:
                asteroid_scale *= 2
                print(f'Asteroid is smaller than half the frame. Growing...')
            elif touching_edge:
                asteroid_scale *= 0.75
                print(f'Asteroid is larger than frame. Shrinking...')
            else:
                asteroid_scale *= target_size / (max_side * 2)
                size_test = False
                print(f'Final asteroid scaling factor: {asteroid_scale:.3}')
            asteroid.scale = [asteroid_scale, asteroid_scale, asteroid_scale]
        else:
            sprite_size = RESOLUTION_MAX if SCALE_TO_FIT else int((max_side + MARGIN_PIXELS) * 2)
            break

    # Create placeholder spritesheet
    spritesheet = Image.new('RGBA', (sprite_size * FRAME_COUNT, sprite_size), (0, 0, 0, 0))

    # Crop frames and populate spritesheet

    cropped_frames = []

    x_offset = (sprite_size - RESOLUTION_MAX) // 2
    y_offset = (sprite_size - RESOLUTION_MAX) // 2

    for i, image in enumerate(frames):
        cropped_frame = Image.new('RGBA', (sprite_size, sprite_size), (0, 0, 0, 0))
        cropped_frame.paste(image, (x_offset, y_offset), image)
        cropped_frame = postprocess_image(cropped_frame)
        cropped_frames.append(cropped_frame)
        spritesheet.paste(cropped_frame, (i * sprite_size, 0), cropped_frame)

    # Save spritesheet
    spritesheet_path = os.path.join(OUTPUT_PATH,
        f'output_{timestamp}/spritesheet_style_{style_seed}_shape_{shape_seed}_spin_{spin_seed}.png')

    index_image(spritesheet).save(spritesheet_path)

    # Save animated APNG image
    apng_path = f'output_{timestamp}/animation_style_{style_seed}_shape_{shape_seed}_spin_{spin_seed}.png'
    apng_paths.append(apng_path)
    apng_abs_path = os.path.join(OUTPUT_PATH, apng_path)

    indexed_frames = [index_image(frame, True) for frame in cropped_frames]
    indexed_frames[0].save(apng_abs_path, save_all=True, append_images=indexed_frames[1:],
        duration=1000 // FRAMES_PER_SECOND, loop=0, disposal=1)

if not CREATE_ASTEROIDS_ONLY:
    # Create HTML collage
    html_path = os.path.join(OUTPUT_PATH, f'preview_{timestamp}.html')

    with open(html_path, 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Asteroid Collage</title>
    <style>
body {
    background: black url('background.png') repeat;
    margin: 0;
}
img {
    cursor: pointer;
    display: inline-block;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
    margin: 8px;
    min-width: 256px;
    min-height: 256px;
    object-fit: contain;
}
    </style>
</head>
<body>
''')
        for path in apng_paths:
            f.write(f'    <a href="{path}" target="_blank"><img class="sprite" src="{path}" alt="{path}"></a>\n')
        f.write('''
</body>
</html>
''')

# Reset
bpy.context.scene.render.film_transparent = False
random.seed(None)

print('Done creating asteroids')
