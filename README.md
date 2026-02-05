# Procedural Asteroid Generator

![Example Asteroid](https://github.com/Donitzo/procedural-asteroid-generator/blob/main/images/example_asteroid.png)
([More samples](https://donitz.itch.io/procedural-asteroid-generator))

This script procedurally generates animated asteroids in Blender,
complete with style, shape, props, and texture variation using triplanar shading.

![Example](https://github.com/Donitzo/procedural-asteroid-generator/blob/main/images/blender_asteroids.png)

## Attribution

### FilterForge filters used to create textures:

  - [Filter 9445](https://www.filterforge.com/filters/9445.html)
  - [Filter 235](https://www.filterforge.com/filters/235.html)
  - [Filter 3215](https://www.filterforge.com/filters/3215.html)
  - [Filter 7402](https://www.filterforge.com/filters/7402.html)
  - [Filter 13302](https://www.filterforge.com/filters/13302.html)

### Triplanar normal calculation adapted from:

  - [Blender StackExchange post by Nathan](https://blender.stackexchange.com/questions/270490/how-to-fix-box-projected-normal-maps)

### Palettes

Palettes are from [lospec](https://lospec.com/), except for `dusty-space`, which was created by me for a game.

## Quick start

The project can either:
  - Generate a grid of procedurally created asteroid meshes.
  - Render animated spritesheets and APNGs (if `CREATE_ASTEROIDS_ONLY` is set to `False`).

Note: APNG uses RGBA for compatibility. Palette indexing is only applied to the spritesheet.

The project also creates a `preview_timestamp.html` file for easy viewing of generated asteroids.
You can open it in any browser. The seed can be copied from existing asteroids to regenerate either the style or shape.

### Requirements:
  - Blender 4.0 or newer
  - `Pillow` (Python Imaging Library) installed for image handling
  - `Extra Mesh Objects` Extension installed in Blender

To install Pillow inside Blender's Python environment (on Windows):

Download Pillow into a new directory:
```console
"C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\bin\python.exe" -m pip install Pillow --target="C:\temporary_pillow_directory"
```
Then manually copy the `PIL` and `pillow-x.x.x.dist-info` directories from `C:\temporary_pillow_directory` to `C:\Program Files\Blender Foundation\Blender 4.x\4.x\python\lib\site-packages`. This requires administrative privileges.

To run the script:
  1. Open the `asteroid_generator.xxx.blend` file in Blender.
  2. Open the `Text Editor` and the script named `asteroid_generator.py`.
  4. Adjust the configuration parameters as needed.
  5. Click `Run Script` or press Alt+P to start generation.
  6. Wait for the script to finish. Check the system console for progress or errors.
  7. When done, open `preview.html` (in the output folder) to view all generated asteroids in a browser.

![Configuration](https://github.com/Donitzo/procedural-asteroid-generator/blob/main/images/blender_config.png)

## Prop setup

Props must be organized under a Blender collection called `Props`.
Each **child collection** inside `Props` represents a **prop type**,
and should contain one or more objects that will be randomly selected.
Each asteroid can only select props from within one **prop type**, or none.

Each prop object name can include metadata in square brackets at the end of its name:
  - `angle`: Max rotation variation in degrees from the surface normal.
  - `scale`: Multiplier for random scale variation (centered around 1.0).
  - `height`: Maximum upward offset from the asteroid surface.

Example prop name: `Antenna [angle=25,scale=0.1,height=0.2]`

## Material setup

Textures are loaded dynamically based on PNG files in `TEXTURE_PATH` using filenames of the form:
  - `name_diffuse.png`
  - `name_normal.png`
  - `name_emission.png [optional]`

Example `rock` material:
  - `rock_diffuse.png`
  - `rock_normal.png`
  - `rock_emission.png`

If edited, the base material (named `Asteroid`) can contain the following named nodes:
  - Image Texture node: `Diffuse`
  - Image Texture node: `Normal`
  - Image Texture node: `Emission`
  - Value node: `Triplanar Scale`
  - Value node: `Roughness`
  - RGB node: `Tint`

## Feedback & Bug Reports

If you find any bugs or have feedback, please [open an issue](https://github.com/Donitzo/procedural-asteroid-generator/issues) in the GitHub repository.
