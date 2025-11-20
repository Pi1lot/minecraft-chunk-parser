import amulet
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
from collections import Counter
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
        if (x == z) or (x < 0 and x == -z) or (x > 0 and x == 1-z):
            dx, dz = -dz, dx
        x += dx
        z += dz

# -----------------------
# Lecture du monde
# -----------------------
level = amulet.load_level("map")
dimension = "minecraft:overworld"

output_csv = "analyse_chunks.csv"

with open(output_csv, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["chunk_x", "chunk_z", "dominant_biome", "block", "count"])

    # Spirale autour du chunk (0 ,0), rayon 10 → 21×21 = 441 chunks
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
            # Chunk vide → que de l'air
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

                # -------- biomes --------
                if chunk.biomes.has_section(section_y):
                    biome_arr = chunk.biomes.get_section(section_y)
                    for x in range(4):  # biome grid is usually 4x4x4
                        for y in range(4):
                            for z in range(4):
                                bidx = biome_arr[x, y, z]
                                biome = chunk.biome_palette[bidx]
                                biome_counter[biome] += 1

            dominant_biome = (
                biome_counter.most_common(1)[0][0]
                if biome_counter else "unknown"
            )

        # ---- Écriture CSV ----
        for block, count in block_counter.items():
            writer.writerow([chunk_x, chunk_z, dominant_biome, block, count])

        print(f"✔ Chunk {chunk_x}, {chunk_z} traité")

level.close()
print("Terminé ! Fichier généré :", output_csv)
