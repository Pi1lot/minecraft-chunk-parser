#!/usr/bin/env python3
import amulet
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
from collections import Counter
import numpy as np
import csv
from tqdm import tqdm
import argparse

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
# Helpers: normalize key for a universal block/biome
# ---------------------------
def universal_key(obj):
    """Return a stable key (string) for a universal block/biome object."""
    # prefer namespaced_name when present, otherwise fallback to str()
    return getattr(obj, "namespaced_name", None) or str(obj)

# ---------------------------
# Dynamic caches (global for the run)
# ---------------------------
BLOCK_CACHE = {}  # universal_key -> translated_name
BIOME_CACHE = {}  # universal_key -> translated_name

def translate_block_from_palette(idx, palette, translator):
    """
    Given an index in a chunk.palette, translate via translator only when needed.
    Caches by universal_key of the palette element (not by index).
    """
    uni = palette[idx]
    key = universal_key(uni)
    if key in BLOCK_CACHE:
        return BLOCK_CACHE[key]
    # translate and cache
    real = translator.from_universal(uni)
    if isinstance(real, tuple):
        real = real[0]
    name = getattr(real, "namespaced_name", None) or getattr(uni, "namespaced_name", None) or str(uni)
    BLOCK_CACHE[key] = name
    return name

def translate_biome_from_palette(idx, palette, translator):
    uni = palette[idx]
    key = universal_key(uni)
    if key in BIOME_CACHE:
        return BIOME_CACHE[key]
    real = translator.from_universal(uni)
    if isinstance(real, tuple):
        real = real[0]
    name = getattr(real, "namespaced_name", None) or getattr(uni, "namespaced_name", None) or str(uni)
    BIOME_CACHE[key] = name
    return name

# ---------------------------
# Main
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

    coords = list(spiral_chunks(max_radius))
    print(f"INFO - Total chunks to process: {len(coords)}")

    empty_subchunk = np.zeros(16*16*16, dtype=int)  # reusable empty subchunk

    chunk_data = []
    all_blocks = set()

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
            # Collect flattened arrays for the present subchunks (reuse empty_subchunk when missing)
            all_blocks_arr = []
            all_biomes_arr = []

            min_sy = min(subchunks)
            max_sy = max(subchunks)
            for sy in range(min_sy, max_sy + 1):
                if sy in chunk.blocks.sub_chunks:
                    arr = chunk.blocks.get_sub_chunk(sy).flatten()
                else:
                    arr = empty_subchunk
                all_blocks_arr.append(arr)

                if chunk.biomes.has_section(sy):
                    b_arr = chunk.biomes.get_section(sy).flatten()
                    all_biomes_arr.append(b_arr)

            # Vectorized count for blocks (single np.unique per chunk)
            if all_blocks_arr:
                flat_blocks = np.concatenate(all_blocks_arr)
                unique_idx, counts = np.unique(flat_blocks, return_counts=True)
                # Translate only the universal palette entries we need (and cache by universal key)
                palette = chunk.block_palette
                for idx, cnt in zip(unique_idx, counts):
                    name = translate_block_from_palette(int(idx), palette, block_translator)
                    block_counter[name] += int(cnt)
                    all_blocks.add(name)

            # Vectorized count for biomes (single np.unique per chunk)
            if all_biomes_arr:
                flat_biomes = np.concatenate(all_biomes_arr)
                unique_b, counts_b = np.unique(flat_biomes, return_counts=True)
                palette_b = chunk.biome_palette
                for idx, cnt in zip(unique_b, counts_b):
                    bname = translate_biome_from_palette(int(idx), palette_b, biome_translator)
                    biome_counter[bname] += int(cnt)

            dominant_biome = biome_counter.most_common(1)[0][0] if biome_counter else "unknown"

        chunk_data.append({
            "x": chunk_x,
            "z": chunk_z,
            "biome": dominant_biome,
            "blocks": block_counter
        })

    level.close()

    # Write CSV (one row per chunk, wide format)
    all_blocks = sorted(all_blocks)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["chunk_x", "chunk_z", "dominant_biome"] + all_blocks
        writer.writerow(header)
        for entry in chunk_data:
            row = [entry["x"], entry["z"], entry["biome"]] + [entry["blocks"].get(b, 0) for b in all_blocks]
            writer.writerow(row)

    print(f"✔ DONE — CSV written: {output_csv}")
    print(f"INFO - Unique universal block types translated: {len(BLOCK_CACHE)}")
    print(f"INFO - Unique universal biome types translated: {len(BIOME_CACHE)}")

# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minecraft chunk CSV exporter (dynamic-universal-cache + vectorized)")
    parser.add_argument("world", help="Path to Minecraft world folder")
    parser.add_argument("-o", "--output", default="chunks_biomes.csv", help="Output CSV filename")
    parser.add_argument("-r", "--radius", type=int, default=10, help="Radius of chunks to process (spiral)")
    args = parser.parse_args()

    main(args.world, args.output, args.radius)
