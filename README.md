# Minecraft Chunk Parser

A Python tool for extracting block counts, biome information, and chunk coordinates from Minecraft 1.21+ worlds.
It exports chunk data into a wide-format CSV file suitable for data analysis, machine learning, or world-generation studies.

This project uses the [Amulet world manipulation](https://www.amuletmc.com/) library and automatically translates universal block and biome IDs using a dynamic cache for performance.

> [!WARNING]
> Due to the CSV output format, the script needs to store all discovered chunks in RAM before writing them to the file. As a result, this program can become extremely RAM-hungry for radii above 80.

## Features

-   Extract blocks and biomes from Minecraft chunks (16×16×384)
-   Count occurrences of every block type
-   Determine the dominant biome for each chunk
-   Export all data to a clean, analysis-ready CSV file

## Installation

```
pip install amulet-core numpy tqdm
```

### CLI usage

| Flag            | Description                          |
|-----------------|--------------------------------------|
| `world`         | Path to the Minecraft world folder   |
| `-o, --output`  | Output CSV filename                  |
| `-r, --radius`  | Chunk radius (spiral traversal)      |

Example:

    python3 chunk_parser.py ~/minecraft/saves/MyWorld -o chunks.csv -r 40

## Example CSV Output

    chunk_x,chunk_z,dominant_biome,minecraft:stone,minecraft:dirt,minecraft:oak_log,...
    0,0,plains,50120,8250,32,...
    0,1,forest,49800,8120,120,...
    1,0,river,40000,5000,0,...

Each row corresponds to one chunk, and each block type appears as a
separate column.\
The CSV file follows a wide-format structure.
