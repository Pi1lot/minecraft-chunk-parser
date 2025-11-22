import amulet
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
from collections import Counter
import csv
import numpy as np


# ---------------------------
# Spiral chunk iterator
# ---------------------------
def spiral_chunks(max_radius):
    x = z = 0
    dx, dz = 0, -1
    for _ in range((max_radius * 2 + 1) ** 2):
        yield x, z
        if (x == z) or (x < 0 and x == -z) or (x > 0 and x == 1 - z):
            dx, dz = -dz, dx
        x += dx
        z += dz


# ---------------------------
# Load world
# ---------------------------
WORLD_PATH = r"path_to_your_save_file"
dimension = "minecraft:overworld"

print("INFO - Loading:", WORLD_PATH)
level = amulet.load_level(WORLD_PATH)

# ---------------------------
# REAL translator for Amulet 1.9.32
# ---------------------------
platform = level.level_wrapper.platform
version = level.level_wrapper.version  # MUST be tuple in this version

print("INFO - Platform =", platform)
print("INFO - Version  =", version)

translator = level.translation_manager.get_version(platform, version)
block_translator = translator.block


# ------------------------------------------
# Scan
# ------------------------------------------
chunk_data = []
all_blocks = set()

MAX_RADIUS = 10

for chunk_x, chunk_z in spiral_chunks(MAX_RADIUS):

    try:
        chunk = level.get_chunk(chunk_x, chunk_z, dimension)
    except (ChunkDoesNotExist, ChunkLoadError):
        print(f"✘ Missing chunk {chunk_x},{chunk_z}")
        continue

    print(f"✔ Chunk {chunk_x},{chunk_z}")

    block_counter = Counter()
    biome_counter = Counter()

    subchunks = sorted(chunk.blocks.sub_chunks)

    if not subchunks:
        block_counter["minecraft:air"] = 16 * 16 * 384
        dominant_biome = "unknown"

    else:
        for section_y in range(min(subchunks), max(subchunks) + 1):

            # ---------- blocks ----------
            if section_y in chunk.blocks.sub_chunks:
                arr = chunk.blocks.get_sub_chunk(section_y)
            else:
                arr = np.zeros((16, 16, 16), dtype=int)

            palette = chunk.block_palette

            for x in range(16):
                for y in range(16):
                    for z in range(16):
                        idx = arr[x, y, z]
                        universal_block = palette[idx]

                        # translate universal → real
                        real_block = block_translator.from_universal(universal_block)

                        # If translator gives tuple → take first
                        if isinstance(real_block, tuple):
                            real_block = real_block[0]

                        if real_block is None:
                            name = universal_block.namespaced_name
                        else:
                            name = real_block.namespaced_name

                        block_counter[name] += 1
                        all_blocks.add(name)

            # ---------- biomes ----------
            if chunk.biomes.has_section(section_y):
                biome_arr = chunk.biomes.get_section(section_y)
                for bx in range(biome_arr.shape[0]):
                    for by in range(biome_arr.shape[1]):
                        for bz in range(biome_arr.shape[2]):
                            bidx = biome_arr[bx, by, bz]
                            biome = chunk.biome_palette[bidx]
                            biome_counter[biome] += 1

        dominant_biome = biome_counter.most_common(1)[0][0] if biome_counter else "unknown"

    chunk_data.append({
        "x": chunk_x,
        "z": chunk_z,
        "biome": dominant_biome,
        "blocks": block_counter
    })


# ---------------------------
# Write CSV
# ---------------------------
output_csv = "chunks_final.csv"
all_blocks = sorted(all_blocks)

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    header = ["chunk_x", "chunk_z", "dominant_biome"] + all_blocks
    writer.writerow(header)

    for entry in chunk_data:
        row = [entry["x"], entry["z"], entry["biome"]]
        for b in all_blocks:
            row.append(entry["blocks"].get(b, 0))
        writer.writerow(row)

level.close()

print("✔ DONE — CSV written:", output_csv)
