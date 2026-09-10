# PHONOS paper demo

Static listening page for **PHONOS: PHONetic Translation for Online Streaming Applications**.

## Rebuild the sample set

The page uses five source/conversion pairs per direction from the manually reviewed
`accent_new` study pool. The preparation script ranks the available PHONOS outputs by
NISQA MOS, copies the selected WAV files, and writes both the browser manifest and an
audit CSV.

```bash
cd /data/waris/code/warisqr007.github.io/demos/phonos-taslp
python -m pip install soundfile
python prepare_demo.py
```

For local preview:

```bash
python -m http.server 8765
```

Then open `http://localhost:8765/`.
