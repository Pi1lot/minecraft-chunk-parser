import amulet
from amulet.api.errors import ChunkLoadError, ChunkDoesNotExist
from collections import Counter

# Charger le monde
level = amulet.load_level("map")

# Coordonnées du chunk à lire
chunk_x, chunk_z = 0, 0
dimension = "minecraft:overworld"

try:
    chunk = level.get_chunk(chunk_x, chunk_z, dimension)
except ChunkDoesNotExist:
    print("Chunk does not exist")
    chunk = None
except ChunkLoadError:
    print("Chunk load error")
    chunk = None

if chunk:
    print(f"Informations pour le chunk {chunk_x}, {chunk_z}:")

    block_counter = Counter()
    biome_counter = Counter()

    # Récupérer tous les subchunks (sections) existants
    subchunk_indices = sorted(chunk.blocks.sub_chunks)

    # Si aucun subchunk existant, considérer que tout est air
    if not subchunk_indices:
        print("Chunk vide, rempli d'air")
        block_counter["minecraft:air"] = 16 * 16 * 384  # 16x16x24 sections *16 ?
        average_biome = "plains"
    else:
        # Parcourir chaque section
        for section_y in range(min(subchunk_indices), max(subchunk_indices)+1):
            if section_y in chunk.blocks.sub_chunks:
                arr = chunk.blocks.get_sub_chunk(section_y)
            else:
                # Subchunk manquant → remplir d'air
                import numpy as np
                arr = np.zeros((16, 16, 16), dtype=int)  # 0 correspond souvent à air dans palette

            # Compter les blocs
            for x in range(16):
                for y in range(16):
                    for z in range(16):
                        block_index = arr[x, y, z]
                        block = chunk.block_palette[block_index]
                        block_counter[block.namespaced_name] += 1

            # Biomes
            if chunk.biomes.has_section(section_y):
                biome_arr = chunk.biomes.get_section(section_y)
                for x in range(biome_arr.shape[0]):
                    for y in range(biome_arr.shape[1]):
                        for z in range(biome_arr.shape[2]):
                            biome_index = biome_arr[x, y, z]
                            biome = chunk.biome_palette[biome_index]
                            biome_counter[biome] += 1

        # Biome le plus fréquent
        average_biome = biome_counter.most_common(1)[0][0] if biome_counter else "unknown"

    # Afficher les infos
    print(f"Coordonnées chunk (en blocs): X={chunk_x*16}, Z={chunk_z*16}")
    print(f"Biome moyen : {average_biome}")
    print("Top 10 blocs présents :")
    for block, count in block_counter.most_common(10):
        print(f"  {block}: {count}")

# Fermer le monde
level.close()
