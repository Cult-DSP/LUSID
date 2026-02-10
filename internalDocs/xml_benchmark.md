# LUSID XML Parser Benchmark

**Generated:** 2026-02-10 12:53  
**File:** `/Users/lucian/projects/sonoPleth/processedData/currentMetaData.xml`  
**File Size:** 25.1 MB  
**Runs:** 5 (averaged)

## Results

| Metric          | lxml (old) | xml.etree.ElementTree (new) | Ratio                 |
| --------------- | ---------- | --------------------------- | --------------------- |
| Parse Time      | 1252.5 ms  | 547.3 ms                    | etree is 2.29x faster |
| Peak Memory     | 31.9 MB    | 175.2 MB                    | 5.49x                 |
| Frames          | 5348       | 5348                        | —                     |
| Audio Objects   | 56         | 56                          | —                     |
| Direct Speakers | 9          | 9                           | —                     |
| LFE             | True       | True                        | —                     |

## Output Parity

✅ Equivalent

## Analysis

### lxml (current pipeline)

- Uses `lxml.etree` with XPath and explicit namespace maps
- Requires external C library dependency (`lxml`)
- Pipeline: lxml parse → intermediate Python dicts → `adm_to_lusid_scene()`
- Two-step process: sonoPleth parses XML, LUSID converts dicts to scene

### xml.etree.ElementTree (new prototype)

- Uses Python stdlib `xml.etree.ElementTree` only
- **Zero external dependencies** — LUSID is fully self-contained
- Pipeline: stdlib parse → LUSID scene directly (single step)
- Handles EBU namespaces via `{ns}tag` prefix convention

### Recommendation

The `xml.etree.ElementTree` approach is recommended because:

1. **No external dependencies** — LUSID stays stdlib-only
2. **Single-step pipeline** — XML → LUSID scene in one function call
3. **Equivalent output** — scenes match the lxml pipeline exactly
4. **Adequate performance** — parsing time is acceptable for the workload
5. **Cross-platform** — no C library compilation needed

### Notes

- The `lxml` pipeline includes dict conversion overhead (two-step process)
- The `etree` pipeline does everything in a single pass
- Memory measurements include the full scene construction
- Both pipelines are I/O-bound for large XML files; parse time differences
  are mostly from the XML library's C vs Python implementation
- **Memory trade-off:** etree uses ~5.5x more peak memory (175 MB vs 32 MB for a 25 MB XML file). This is because `xml.etree.ElementTree` loads the full DOM tree in Python objects, while `lxml` uses a more compact C-backed representation. For typical ADM files (<100 MB), this is not a concern. For very large files, consider streaming with `iterparse()`.
