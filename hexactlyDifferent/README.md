## hex file compariser (based on unified memory layout)

* requirements collection: see `functional_requirements.md`

## output for unified memory layout

```
# UNIFIED_MEMORY_LAYOUT v1
# SOURCE testFiles/12074798_002_edited.hex
# RANGE 0x00000000 0x0001FDFF SIZE 130560
# FORMAT: 0xAAAAAAAA: <hex bytes>  |<ASCII>|   (CONTENT_STARTS_AT_LINE 5)
0x00000000: 68 4E 00 20 B9 01 00 00 E9 01 00 00 EB 01 0A AA  |hN. ............|
0x00000010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|
...
```

## diff check

```
python3 hexactlyDifferent.py testFiles/expo_ili.hex testFiles/2025-11-12_14-14-07_ili2315.hex -v
INFO: A: records=4008, bytes_mapped=64004, data_range=0x00000000-0x0001F43F
INFO: B: records=4043, bytes_mapped=64548, data_range=0x00000000-0x0001FDFF
INFO: Unified range: 0x00000000 - 0x0001FDFF (size 130560 bytes)
INFO: Wrote unified dump for A to: testFiles/expo_ili.unified.txt
INFO: Wrote unified dump for B to: testFiles/2025-11-12_14-14-07_ili2315.unified.txt
0x0001F060: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF  |................|   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|   ^^^^^^^^^^^^^^^^
0x0001F230: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF  |................|   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  |................|   ^^^^^^^^^^^^^^^^
INFO: Diff: differing_bytes=32, differing_lines=2
```

