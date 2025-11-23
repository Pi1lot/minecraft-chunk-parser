import amulet
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
from collections import Counter
import numpy as np
import csv
import argparse
from tqdm import tqdm
import os
import sys

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
# Safe block/biome translation
# ---------------------------
def safe_block_name(block, translator):
    real = translator.from_universal(block)
    if isinstance(real, tuple):
        real = real[0]
    if real is None:
        return getattr(block, "namespaced_name", str(block))
    return getattr(real, "namespaced_name", str(real))

def safe_biome_name(biome, translator):
    real = translator.from_universal(biome)
    if isinstance(real, tuple):
        real = real[0]
    if real is None:
        return getattr(biome, "namespaced_name", str(biome))
    return getattr(real, "namespaced_name", str(real))

# ---------------------------
# Main function
# ---------------------------
def main(world_path, output_csv, max_radius):
    dimension = "minecraft:overworld"

    print(f"INFO - Loading world: {world_path}")
    level = amulet.load_level(world_path)

    platform = level.level_wrapper.platform
    version = level.level_wrapper.version
    print(f"INFO - Platform: {platform}, Version: {version}")

    translator = level.translation_manager.get_version(platform, version)
    block_translator = translator.block
    biome_translator = translator.biome

    chunk_data = []
    all_blocks = set()

    coords = list(spiral_chunks(max_radius))
    print(f"INFO - Total chunks to process: {len(coords)}")

    # Iterate chunks with progress bar
    for chunk_x, chunk_z in tqdm(coords, desc="Processing chunks", ncols=100):
        try:
            chunk = level.get_chunk(chunk_x, chunk_z, dimension)
        except (ChunkDoesNotExist, ChunkLoadError):
            continue

        block_counter = Counter()
        biome_counter = Counter()
        subchunks = sorted(chunk.blocks.sub_chunks)

        if not subchunks:
            block_counter["minecraft:air"] = 16*16*384
            dominant_biome = "unknown"
        else:
            for sy in range(min(subchunks), max(subchunks)+1):
                if sy in chunk.blocks.sub_chunks:
                    arr = chunk.blocks.get_sub_chunk(sy)
                else:
                    arr = np.zeros((16,16,16), dtype=int)
                palette = chunk.block_palette

                # ---------- PRE-TRANSLATION ----------
                translated_palette = {i: safe_block_name(b, block_translator) for i, b in enumerate(palette)}

                # ---------- VECTORIZE COUNT ----------
                flat_arr = arr.flatten()
                unique, counts = np.unique(flat_arr, return_counts=True)
                for idx, cnt in zip(unique, counts):
                    name = translated_palette[idx]
                    block_counter[name] += cnt
                    all_blocks.add(name)

                # ---------- BIOMES ----------
                if chunk.biomes.has_section(sy):
                    biome_arr = chunk.biomes.get_section(sy)
                    biome_palette = chunk.biome_palette
                    # pre-translate biome palette
                    translated_biome_palette = {i: safe_biome_name(b, biome_translator) for i, b in enumerate(biome_palette)}

                    flat_biome = biome_arr.flatten()
                    unique_b, counts_b = np.unique(flat_biome, return_counts=True)
                    for idx, cnt in zip(unique_b, counts_b):
                        name = translated_biome_palette[idx]
                        biome_counter[name] += cnt

            dominant_biome = biome_counter.most_common(1)[0][0] if biome_counter else "unknown"

        chunk_data.append({
            "x": chunk_x,
            "z": chunk_z,
            "biome": dominant_biome,
            "blocks": block_counter
        })

    level.close()

    # Write CSV
    all_blocks = sorted(all_blocks)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["chunk_x", "chunk_z", "dominant_biome"] + all_blocks
        writer.writerow(header)
        for entry in chunk_data:
            row = [entry["x"], entry["z"], entry["biome"]] + [entry["blocks"].get(b,0) for b in all_blocks]
            writer.writerow(row)

    print(f"✔ DONE — CSV written: {output_csv}")

# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minecraft chunk CSV exporter (fast mono-process)")
    parser.add_argument("world", help="Path to Minecraft world folder")
    parser.add_argument("-o", "--output", default="chunks_biomes.csv", help="Output CSV filename")
    parser.add_argument("-r", "--radius", type=int, default=10, help="Radius of chunks to process (spiral)")
    args = parser.parse_args()

    main(args.world, args.output, args.radius)
