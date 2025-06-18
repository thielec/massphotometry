import os
from pathlib import Path
import numpy as np
import h5py
import hdf5plugin  # required for reading compressed data
from .metadata import convert_metadata as mp_convert_metadata


def _hdf5_to_dict(h5file: h5py.File) -> dict:
    """
    Converts an HDF5 file to a flattened dictionary.

    Iterates over all Groups and datasets in the HDF5 file.
    Flattening the dictionary (e.g., group/subgroup/dataset becomes "group/subgroup/dataset")
    avoids side-effects when copying the object and simplifies access.

    Parameters
    ----------
    h5file : h5py.File
        The HDF5 file object to convert.

    Returns
    -------
    dict
        A dictionary containing the flattened HDF5 file data.
        Keys are the full paths to the datasets.
    """
    # Iterate over all Groups and entries in the hdf5 file and output them as a flattend dictionary
    # Flattening the dictionary avoids sideeffect when copying the object.
    d = {}

    def helper(name, obj):
        try:
            if isinstance(obj, h5py.Dataset):
                d[name] = obj[()]
            elif isinstance(obj, h5py.Group):
                for key, val in obj.items():
                    helper(name + "/" + key, val)
        except Exception as e:
            print(f"Error accessing {name}: {e}")

    for key, val in h5file.items():
        helper(key, val)
    return d


def decode_compresed_movie(frames: np.ndarray, metadata: dict) -> np.ndarray:
    """
    Decodes a movie compressed with frame-wise differences.

    In this compression scheme, the first frame is stored as is (or as a keyframe).
    Subsequent frames are stored as the difference to the previous frame.
    This function reconstructs the full movie by cumulative summation.
    A check against a final keyframe (if present in metadata) ensures decompression integrity.

    Parameters
    ----------
    frames : np.ndarray
        The compressed movie data. Expected to be an array where `frames[0]`
        is a keyframe and `frames[i]` for `i > 0` are difference frames.
    metadata : dict
        The metadata associated with the movie. This function looks for
        `metadata["movie/keyframe"]` to verify decompression if available.
        This entry is removed from the metadata dict if used for verification.

    Returns
    -------
    np.ndarray
        The decompressed movie data, with the same dtype as the input `frames`
        if decompression is successful and verified.

    Raises
    ------
    ValueError
        If decompression fails when comparing the reconstructed last frame
        to the keyframe provided in `metadata["movie/keyframe"]`.
    """
    # get the compression parameters
    maxint = np.iinfo(frames.dtype).max

    unwraped = frames.astype(float) - (frames > maxint // 2) * (float(maxint) + 1)
    unwraped[0] = frames[0]
    unwraped = np.cumsum(unwraped, axis=0)
    # check if correct by comparing the last frame to the keyframe
    if np.allclose(unwraped[-1], metadata["movie/keyframe"][-1]):
        metadata.pop("movie/keyframe")
        return unwraped.astype(frames.dtype)
    else:
        raise ValueError("Decompression failed.")


def read_mp(
    filepath: str | os.PathLike, convert_metadata: bool = False
) -> tuple[np.ndarray, dict]:
    """
    Reads an MP (mass photometry) file and returns its data and metadata.

    This function handles opening HDF5-based .mp files, extracting movie frames
    (decompressing if necessary), and associated metadata.

    Parameters
    ----------
    filepath : str or os.PathLike
        The path to the .mp movie file.
    convert_metadata : bool, optional
        If True, converts the raw metadata extracted from the file into a
        standardized format using `massphotometry.metadata.convert_metadata`.
        Default is False, in which case raw metadata is returned.

    Returns
    -------
    tuple[np.ndarray, dict]
        A tuple containing:
        - movie_data (np.ndarray): The movie data as a NumPy array.
          Shape is typically (n_frames, height, width).
        - metadata (dict): The metadata. If `convert_metadata` is True,
          this is the standardized metadata; otherwise, it's the raw
          metadata extracted from the file.

    Raises
    ------
    FileNotFoundError
        If the specified `filepath` does not exist.
    ValueError
        If the file is not a valid HDF5 file, if essential datasets like
        'movie/frames' are missing, or if movie decompression fails.
    Exception
        Other exceptions may be raised by underlying libraries (h5py) for
        file access or corruption issues.
    """
    with h5py.File(filepath, "r") as file:
        metadata = _hdf5_to_dict(file)

    frames = metadata.pop("movie/frame", None)  # for metadata["mp_version_number"] == 3
    if frames is None:
        frames = metadata.pop("frame", None)  # for metadata["mp_version_number"] == 2
    if frames is None:
        raise ValueError(f"No entry for frames found: {filepath}")

    try:
        if np.divide(*np.std(frames[:2], axis=(1, 2))) < 0.5:
            # Check the ratio of the std of the first two frames.
            # The first frame is uncompressed and has the normal std.
            # If the second frame is compressed, it has a much higher std due to uint overflow.
            frames = decode_compresed_movie(frames, metadata)
    except Exception as exc:
        print(f"Compression check failed: {exc}")
    if convert_metadata:
        metadata = mp_convert_metadata(metadata)

    return frames, metadata
