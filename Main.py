import random
from amulet.api.chunk import Chunk
from amulet.api.chunk.biomes import BiomesShape
from amulet.api.block import Block
from amulet.api.chunk.biomes import Biomes
from amulet.api.errors import ChunkDoesNotExist 
from math import floor
import time
import amulet
import glob
import opensimplex
import json
from loadbar import LoadBar

# Load level
level = amulet.load_level("D+kHY4hCAAA=")
opensimplex.random_seed()

# Parameters
chunk_height = 60
width = 50
planet_offset = 5000

# Data
blocks = {}
biomes = []

modifications = []

for file_name in glob.glob(r"Biomes\*.biome.json"):
    with open (file_name, "r") as data:
        data_dict = json.load(data)
        flora = []
        features = []

        for feature in data_dict["flora"]:
            for i in range(feature["weight"]):
                flora.append(feature)

        for feature in data_dict["features"]:
            for i in range(feature["weight"]):
                features.append(feature)

        random.shuffle(flora)
        random.shuffle(features)

        data_dict.update({"flora": flora})
        data_dict.update({"features": features})
        biomes.append(data_dict)

print(f"Loaded {len(biomes)} biomes")

def GetId(id) -> int:
    if id in blocks:
        return blocks[f"{id}"]

    namespace = id.split(":")[0]
    identifier = id.split(":")[1]
        
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

def Get3DNoise(x, y, z, offset, scale):
    return opensimplex.noise3(
        (x + 0.1) / 16 * scale + offset, 
        (y + 0.1) / 16 * scale + offset, 
        (z + 0.1) / 16 * scale + offset
    )

def MakeTree(world_x, world_y, world_z, min_height, max_height, log, leaves):
    height = random.randint(min_height, max_height)

    for i in range(height):
        modifications.append((log, world_x, world_y + i, world_z))

    for x in range(-2, 3):
        for z in range(-2, 3):
            if x == 0 and z == 0: continue
            modifications.append((leaves, world_x + x, world_y + height - 2, world_z + z))
            modifications.append((leaves, world_x + x, world_y + height - 1, world_z + z))

    for x in range(-1, 2):
        for z in range(-1, 2):
            if x == 0 and z == 0: continue
            modifications.append((leaves, world_x + x, world_y + height, world_z + z))

def GetBlock(biome, x, y, z, ground_height, flora, feature, feature_2) -> int:
    if y == 0: return GetId("minecraft:bedrock")

    if y == ground_height + 1 and flora > 0:
        index = floor(flora * len(biome["flora"]))
        return GetId(biome["flora"][index]["block"])

    elif y == ground_height + 1 and feature > 0:
        if feature_2 > 0.4:
            index = floor(feature * len(biome["features"]))
            feature = biome["features"][index]
            feature_type = feature["feature_type"]

            if feature_type == "tree":
                MakeTree(x, y, z, 4, 10, feature["log"], feature["leaves"])

    if y == ground_height:
        return GetId(biome["surface_parameters"]["top_material"])

    elif y < ground_height and y > ground_height - 3:
        return GetId(biome["surface_parameters"]["mid_material"])

    elif y < ground_height:
        return GetId(biome["surface_parameters"]["foundation_material"])

    return GetId("minecraft:air")

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
            flora = Get2DNoise(x + offset_x, z + offset_z, 4315, 1)
            feature = Get2DNoise(x + offset_x, z + offset_z, 65434, 10)
            feature2 = Get2DNoise(x + offset_x, z + offset_z, 242, 2)
 
            biome = GetBiome(temperature, rainfall)

            ground_height = 45 + floor(10 * height_noise);

            for y in range(0, 60):
                chunk.blocks[x, y, z] = GetBlock(biome, x + offset_x, y, z + offset_z, ground_height, flora, feature, feature2)
    
    level.put_chunk(chunk, "minecraft:overworld")
    chunk.changed = True

start = time.time()

bar = LoadBar(max=(width * width), title="Chunks")
bar.start()

for x in range(width):
    for z in range(width):
        CreateChunk(x + planet_offset, z + planet_offset)
        bar.update(step=(x * width) + z)

bar.end()

bar = LoadBar(max=len(modifications), title="Modifications")
bar.start()

mod_total = 0

for mod in modifications:
    block_id = mod[0]
    x = mod[1]
    y = mod[2]
    z = mod[3]

    cx = x // 16
    cz = z // 16
    
    try:
        chunk = level.get_chunk(cx, cz, "minecraft:overworld")
        chunk.blocks[x - (cx * 16), y, z - (cz * 16)] = GetId(block_id)

        level.put_chunk(chunk, "minecraft:overworld")
        chunk.changed = True

    except ChunkDoesNotExist:
        pass

    mod_total += 1
    bar.update(step=mod_total)

bar.end()
total_time = time.time() - start

print(str(total_time) + "s taken to generate " + str(width * width) + " chunks!")
print(str(total_time / (width * width) * 1000) + "ms per chunk")
 
# Save the data to the level and close it
level.save()
level.close()