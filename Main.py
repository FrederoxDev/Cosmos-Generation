from asyncio import constants
from math import floor
import time
from amulet.api.chunk import Chunk
from amulet.api.block import Block
from amulet.utils.world_utils import block_coords_to_chunk_coords
from amulet.api.errors import ChunkDoesNotExist
import amulet
import glob
import opensimplex
import json
from loadbar import LoadBar

# Load level
level = amulet.load_level("PhQFY+iUAAA=")
opensimplex.random_seed()

# Parameters
chunk_height = 60
width = 100

# Data
blocks = {}
biomes = []

for file_name in glob.glob(r"Biomes\*.biome.json"):
    with open (file_name, "r") as data:
        biomes.append(json.load(data))

print(f"Loaded {len(biomes)} biomes")

def GetId(identifier, namespace = "minecraft") -> int:
    if f"{namespace}:{identifier}" in blocks:
        return blocks[f"{namespace}:{identifier}"]
    
    block = Block(namespace, identifier, {})
    universal = level.translation_manager.get_version("bedrock", (1, 19, 0)).block.to_universal(block)[0]
    id = level.block_palette.get_add_block(universal)

    blocks.update({f"{namespace}:{identifier}": id})
    return id

def Get2DNoise(x, z, offset, scale):
    return opensimplex.noise2(
        (x + 0.1) / 16 * scale + offset, 
        (z + 0.1) / 16 * scale + offset
    )

def GetBlock(biome, y, ground_height) -> int:
    if y == 0: return GetId("bedrock")

    if y == ground_height:
        return GetId(biome["surface_parameters"]["top_material"])

    elif y < ground_height and y > ground_height - 3:
        return GetId(biome["surface_parameters"]["mid_material"])

    elif y < ground_height:
        return GetId(biome["surface_parameters"]["foundation_material"])

    return GetId("air")

def GetBiome(temperature, rainfall):
    closestDist = -1
    closest = None

    for biome in biomes:
        temp = max(biome["climate"]["temperature"], temperature) - min(biome["climate"]["temperature"], temperature)
        rain = max(biome["climate"]["rainfall"], rainfall) - min(biome["climate"]["rainfall"], rainfall);

        if (temp + rain > closestDist):
            closestDist = temp + rain
            closest = biome

    return closest

def CreateChunk(cx, cz) -> None:
    chunk = Chunk(cx, cz)

    for x in range(0, 16):
        for z in range(0, 16):
            offset_x = cx * 16
            offset_z = cz * 16

            height_noise = (Get2DNoise(x + offset_x, z + offset_z, 0, 0.5) + Get2DNoise(x + offset_x, z + offset_z, 1234, 0.25))

            temperature = Get2DNoise(x + offset_x, z + offset_z, 3214, 0.2)
            rainfall = Get2DNoise(x + offset_x, z + offset_z, 43155, 0.2)

            biome = GetBiome(temperature, rainfall)

            ground_height = 45 + floor(10 * height_noise);

            for y in range(0, 60):
                chunk.blocks[x, y, z] = GetBlock(biome, y, ground_height)
    
    level.put_chunk(chunk, "minecraft:overworld")
    chunk.changed = True

start = time.time()

bar = LoadBar(max=(width * width), title="Chunks")
bar.start()

for x in range(width):
    for z in range(width):
        CreateChunk(x, z)
        bar.update(step=(x * width) + z)

bar.end()

total_time = time.time() - start

print(str(total_time) + "s taken to generate " + str(width * width) + " chunks!")
print(str(total_time / (width * width) * 1000) + "ms per chunk")
 
# Save the data to the level and close it
level.save()
level.close()
