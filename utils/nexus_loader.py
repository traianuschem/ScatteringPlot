"""
NeXus/HDF5 loader for 2D SAXS detector data.

Supports:
- .h5  (direct HDF5)
- .h5z (ZIP-compressed HDF5, vendor format)

Expected HDF5 structure (NeXus-compliant):
  /entry/data/data          (1, H, W) or (N,) float64  — intensity
  /entry/data/x axis        (N,)             float64  — qx per pixel, m⁻¹
  /entry/data/y axis        (N,)             float64  — qy per pixel, m⁻¹
  /entry/instrument/detector/pixel_mask  (H, W) int32 — 0=valid, ≠0=masked
  /entry/instrument/monochromator/wavelength  scalar float — wavelength, m
  /entry/instrument/detector/distance         scalar float — sample–det, m
  /entry/data/sample_name                     string (optional)
"""

import zipfile
import tempfile
import shutil
from pathlib import Path
import numpy as np
import logging

logger = logging.getLogger(__name__)

_NM_PER_M = 1e9  # 1 m⁻¹ = 1e-9 nm⁻¹


def _open_h5(fpath: Path):
    """Opens an HDF5 file, returns (h5py.File, tmp_dir | None)."""
    import h5py

    if fpath.suffix.lower() == '.h5z':
        tmp_dir = tempfile.mkdtemp(prefix='scatterforge_2d_')
        try:
            with zipfile.ZipFile(fpath, 'r') as zf:
                zf.extractall(tmp_dir)
            # Find the extracted .h5 file
            h5_files = list(Path(tmp_dir).rglob('*.h5'))
            if not h5_files:
                raise ValueError(f"No .h5 file found inside {fpath.name}")
            extracted = h5_files[0]
            logger.debug(f"Extracted {fpath.name} → {extracted}")
            return h5py.File(extracted, 'r'), tmp_dir
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
    else:
        return h5py.File(fpath, 'r'), None


def _safe_read_scalar(h5, *paths, default=None):
    """Read first found scalar from multiple HDF5 paths."""
    for path in paths:
        try:
            val = h5[path][()]
            if hasattr(val, '__len__'):
                return float(val.flat[0])
            return float(val)
        except (KeyError, TypeError, ValueError):
            continue
    return default


def _safe_read_string(h5, *paths, default=''):
    """Read first found string from multiple HDF5 paths."""
    for path in paths:
        try:
            raw = h5[path][()]
            if isinstance(raw, bytes):
                return raw.decode('utf-8', errors='replace').strip()
            if isinstance(raw, np.ndarray):
                val = raw.flat[0]
                if isinstance(val, bytes):
                    return val.decode('utf-8', errors='replace').strip()
                return str(val).strip()
            return str(raw).strip()
        except (KeyError, TypeError):
            continue
    return default


def read_nexus_2d(fpath) -> dict:
    """
    Read a NeXus-compliant HDF5 SAXS file (.h5 or .h5z).

    Returns a dict with:
      'qx'       np.ndarray  — valid pixels, nm⁻¹
      'qy'       np.ndarray  — valid pixels, nm⁻¹
      'I'        np.ndarray  — valid pixels, intensity
      'metadata' dict        — wavelength_nm, distance_m, sample_name, filepath, n_pixels_total, n_pixels_valid
    """
    fpath = Path(fpath)
    if not fpath.exists():
        raise FileNotFoundError(f"File not found: {fpath}")

    h5f, tmp_dir = _open_h5(fpath)
    try:
        return _parse_nexus(h5f, fpath)
    finally:
        h5f.close()
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _parse_nexus(h5f, fpath: Path) -> dict:
    # ── Intensity ────────────────────────────────────────────────
    data_raw = h5f['/entry/data/data'][()]
    if data_raw.ndim == 3:
        # (1, H, W) → (N,)
        I_flat = data_raw[0].ravel().astype(np.float64)
    elif data_raw.ndim == 2:
        I_flat = data_raw.ravel().astype(np.float64)
    elif data_raw.ndim == 1:
        I_flat = data_raw.astype(np.float64)
    else:
        raise ValueError(f"Unexpected data shape: {data_raw.shape}")

    N = len(I_flat)
    logger.debug(f"Intensity array: {N} pixels")

    # ── q coordinates ────────────────────────────────────────────
    qx_raw = h5f['/entry/data/x axis'][()].ravel().astype(np.float64)
    qy_raw = h5f['/entry/data/y axis'][()].ravel().astype(np.float64)

    if len(qx_raw) != N or len(qy_raw) != N:
        raise ValueError(
            f"Shape mismatch: data has {N} pixels but x axis has {len(qx_raw)} "
            f"and y axis has {len(qy_raw)} elements"
        )

    # Auto-detect unit: if most |q| values > 1e4 assume m⁻¹ → convert to nm⁻¹
    q_magnitude = np.nanmedian(np.abs(qx_raw[qx_raw != 0])) if np.any(qx_raw != 0) else 0
    if q_magnitude > 1e4:
        qx = qx_raw / _NM_PER_M
        qy = qy_raw / _NM_PER_M
        logger.debug(f"Converted q from m⁻¹ to nm⁻¹ (median |qx| was {q_magnitude:.2e} m⁻¹)")
    else:
        qx = qx_raw
        qy = qy_raw

    # ── Pixel mask ───────────────────────────────────────────────
    try:
        mask_raw = h5f['/entry/instrument/detector/pixel_mask'][()].ravel().astype(np.int32)
        if len(mask_raw) == N:
            masked = mask_raw != 0
        else:
            logger.warning(f"Pixel mask size {len(mask_raw)} ≠ data size {N}, ignoring mask")
            masked = np.zeros(N, dtype=bool)
    except KeyError:
        logger.debug("No pixel_mask found, treating all pixels as valid")
        masked = np.zeros(N, dtype=bool)

    # Also mask NaN / Inf in intensity and q arrays
    invalid = (
        masked
        | ~np.isfinite(I_flat)
        | ~np.isfinite(qx)
        | ~np.isfinite(qy)
    )
    valid = ~invalid

    qx_out = qx[valid]
    qy_out = qy[valid]
    I_out = I_flat[valid]

    n_valid = int(valid.sum())
    n_total = N
    logger.debug(f"Valid pixels: {n_valid}/{n_total} ({100*n_valid/max(n_total,1):.1f}%)")

    # ── Metadata ─────────────────────────────────────────────────
    wavelength_m = _safe_read_scalar(
        h5f,
        '/entry/instrument/monochromator/wavelength',
        '/entry/instrument/source/wavelength',
        default=None
    )
    wavelength_nm = wavelength_m * _NM_PER_M if wavelength_m is not None else None

    distance_m = _safe_read_scalar(
        h5f,
        '/entry/instrument/detector/distance',
        '/entry/instrument/detector/detector_distance',
        default=None
    )

    sample_name = _safe_read_string(
        h5f,
        '/entry/data/sample_name',
        '/entry/sample/name',
        '/entry/sample/sample_name',
        default=fpath.stem
    )

    metadata = {
        'filepath': str(fpath),
        'sample_name': sample_name,
        'wavelength_nm': wavelength_nm,
        'distance_m': distance_m,
        'n_pixels_total': n_total,
        'n_pixels_valid': n_valid,
    }

    return {
        'qx': qx_out,
        'qy': qy_out,
        'I': I_out,
        'metadata': metadata,
    }
