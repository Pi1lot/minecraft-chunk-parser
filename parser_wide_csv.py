import amulet
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
from collections import Counter, defaultdict
import csv
import numpy as np

# -----------------------
# Fonction de spirale
# -----------------------
def spiral_chunks(max_radius):
    x = z = 0
    dx, dz = 0, -1
    for _ in range((max_radius*2+1)**2):
        yield x, z
        if (x == z) or (x < 0 and x == -z) or (x > 0 and x == 1 - z):
            dx, dz = -dz, dx
        x += dx
        z += dz

# -----------------------
# Lecture du monde
# -----------------------
level = amulet.load_level("map")
dimension = "minecraft:overworld"

# Stockage temporaire : une entrée par chunk
chunk_data = []

# Set global de tous les types de blocs rencontrés
all_blocks = set()

# Spirale autour du chunk (0,0)
for chunk_x, chunk_z in spiral_chunks(max_radius=10):

    try:
        chunk = level.get_chunk(chunk_x, chunk_z, dimension)
    except (ChunkDoesNotExist, ChunkLoadError):
        print(f"Chunk {chunk_x},{chunk_z} introuvable.")
        continue

    block_counter = Counter()
    biome_counter = Counter()

    subchunk_indices = sorted(chunk.blocks.sub_chunks)

    if not subchunk_indices:
        block_counter["minecraft:air"] = 16 * 16 * 384
        dominant_biome = "unknown"
    else:
        for section_y in range(min(subchunk_indices), max(subchunk_indices)+1):

            # -------- blocs --------
            if section_y in chunk.blocks.sub_chunks:
                arr = chunk.blocks.get_sub_chunk(section_y)
            else:
                arr = np.zeros((16,16,16), dtype=int)

            for x in range(16):
                for y in range(16):
                    for z in range(16):
                        idx = arr[x, y, z]
                        block = chunk.block_palette[idx]
                        block_counter[block.namespaced_name] += 1
                        all_blocks.add(block.namespaced_name)

            # -------- biomes --------
            if chunk.biomes.has_section(section_y):
                biome_arr = chunk.biomes.get_section(section_y)
                for x in range(biome_arr.shape[0]):
                    for y in range(biome_arr.shape[1]):
                        for z in range(biome_arr.shape[2]):
                            bidx = biome_arr[x, y, z]
                            biome = chunk.biome_palette[bidx]
                            biome_counter[biome] += 1

        dominant_biome = biome_counter.most_common(1)[0][0] if biome_counter else "unknown"

    # Stocker le résultat temporairement
    chunk_data.append({
        "x": chunk_x,
        "z": chunk_z,
        "biome": dominant_biome,
        "blocks": block_counter
    })

    print(f"✔ Chunk {chunk_x}, {chunk_z} traité")

# -----------------------
# Export CSV wide
# -----------------------
output_csv = "chunks_final.csv"

all_blocks = sorted(all_blocks)  # stable order

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)

    # Colonnes : coords + biome + tous les blocs
    header = ["chunk_x", "chunk_z", "dominant_biome"] + all_blocks
    writer.writerow(header)

    # Une ligne = un chunk
    for entry in chunk_data:
        row = [
            entry["x"],
            entry["z"],
            entry["biome"]
        ]
        # Ajouter le count pour chaque bloc → 0 si absent
        for b in all_blocks:
            row.append(entry["blocks"].get(b, 0))

        writer.writerow(row)

level.close()

print("Terminé ! Fichier généré :", output_csv)
