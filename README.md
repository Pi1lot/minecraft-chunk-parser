# Minecraft Chunk Parser

A Python tool for extracting block counts, biome information, and chunk coordinates from Minecraft 1.21+ worlds.
It exports chunk data into a wide-format CSV file suitable for data analysis, machine learning, or world-generation studies.

This project uses the [Amulet world manipulation](https://www.amuletmc.com/) library and automatically translates universal block and biome IDs using a dynamic cache for performance.
