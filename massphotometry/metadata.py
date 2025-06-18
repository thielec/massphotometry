"""
Functions to convert metadata to a unified format.

The metadata is stored in a dictionary with the following structure:
{
    "framerate": value, # float, value before any binning
    "framerate_unit": value, # str, typically "Hz"
    "framebinning": value, # int, number of frames binned together
    "pixelsize": value, # float, value before any binning
    "pixelsize_unit": value, # str, typically "um"
    "pixelbinning": value, # int, number of pixels binned together
    "exposuretime": value, # float, value before any binning
    "exposuretime_unit": value, # str, typically "s"
    "instrument": value, # str, name of the instrument
    "camera": value, # str, name of the camera
}
"""


def empty_metadata() -> dict:
    """
    Returns a dictionary representing the minimal metadata.
    Contains generic values for framerate, pixelsize, and exposuretime.
    """
    out_dict = {
        "framerate": 1,
        "framerate_unit": "1/frame",
        "framebinning": 1,
        "pixelsize": 1.0,
        "pixelsize_unit": "px",
        "pixelbinning": 1,
        "exposuretime": 1.0,
        "exposuretime_unit": "frame",
        "instrument": "unknown",
    }
    return out_dict


def convert_metadata(metadata: dict, include_native: bool = False) -> dict:
    """
    Convert metadata dictionary to a standardized format.

    The standardized format is described in the module docstring.

    Parameters
    ----------
    metadata : dict
        The metadata dictionary to be converted.
    include_native : bool, optional
        Whether to include the original (native) metadata dictionary
        under the key "native_metadata" in the output. Defaults to False.

    Returns
    -------
    dict
        The converted metadata dictionary, conforming to the standardized format.
        Returns an empty metadata structure if the input metadata is empty or
        cannot be converted.
    """
    if not metadata:
        return empty_metadata()

    try:
        if metadata.get("format_version_number") == 3:
            # there are at least two versions of version 3
            if metadata.get("movie/configuration/Devices/AcqCam/Height") is not None:
                image_shape = (
                    metadata["movie/configuration/Devices/AcqCam/Height"],
                    metadata["movie/configuration/Devices/AcqCam/Width"],
                )
                out_dict = {
                    "framerate": metadata[
                        "movie/configuration/Devices/AcqCam/FrameRate"
                    ],
                    "framerate_unit": "Hz",
                    "framebinning": metadata[
                        "movie/configuration/Devices/AcqCam/SoftwareFrameBinning"
                    ],
                    "pixelsize": 1.0,
                    "pixelsize_unit": "px",
                    "image_shape": image_shape,
                    "field_of_view": image_shape,
                    "field_of_view_unit": "px",
                    "pixelbinning": metadata[
                        "movie/configuration/Devices/AcqCam/SoftwarePixelBinning"
                    ],
                    "exposuretime": metadata[
                        "movie/configuration/Devices/AcqCam/ExposureTime"
                    ],
                    "exposuretime_unit": "ms",
                    "instrument": metadata["movie/device_info/InstrumentName"].decode(
                        "utf-8"
                    ),
                    "cammera": metadata[
                        "movie/configuration/Devices/AcqCam/CameraName"
                    ].decode("utf-8"),
                }
            else:
                image_shape = (*metadata["movie/keyframe"].shape[1:],)
                out_dict = {
                    "framerate": metadata["movie/configuration/acq_camera/frame_rate"],
                    "framerate_unit": "Hz",
                    "framebinning": metadata[
                        "movie/configuration/acq_camera/frame_binning"
                    ],
                    "pixelsize": 1.0,
                    "pixelsize_unit": "px",
                    "image_shape": image_shape,
                    "field_of_view": image_shape,
                    "field_of_view_unit": "px",
                    "pixelbinning": metadata[
                        "movie/configuration/acq_camera/pixel_binning"
                    ],
                    "exposuretime": metadata[
                        "movie/configuration/acq_camera/exposure_time"
                    ],
                    "exposuretime_unit": "ms",
                    "instrument": metadata[
                        "movie/device_serials/InstrumentName"
                    ].decode("utf-8"),
                    "cammera": metadata["movie/configuration/acq_camera/model"].decode(
                        "utf-8"
                    ),
                }
        else:
            # try mp version 2
            image_shape = (
                metadata["configuration/Devices/AcqCam/Height"],
                metadata["configuration/Devices/AcqCam/Width"],
            )
            out_dict = {
                "framerate": metadata["configuration/Devices/AcqCam/FrameRate"],
                "framerate_unit": "Hz",
                "framebinning": metadata[
                    "configuration/Engines/AcqMovieEngine/FrameBinning"
                ],
                "pixelsize": 1.0,
                "pixelsize_unit": "px",
                "image_shape": image_shape,
                "field_of_view": image_shape,
                "field_of_view_unit": "px",
                "pixelbinning": metadata[
                    "configuration/Engines/AcqMovieEngine/PixelBinning"
                ],
                "exposuretime": metadata["configuration/Devices/AcqCam/ExposureTime"],
                "exposuretime_unit": "ms",
                "instrument": metadata["device_info/InstrumentName"].decode("utf-8"),
                "cammera": metadata["configuration/Devices/AcqCam/CameraName"].decode(
                    "utf-8"
                ),
            }
        lookup_pixelsize(out_dict)
        out_dict["framerate_effective"] = (
            out_dict["framerate"] / out_dict["framebinning"]
        )
        out_dict["pixelsize_effective"] = (
            out_dict["pixelsize"] * out_dict["pixelbinning"]
        )
        out_dict["exposuretime_effective"] = (
            out_dict["exposuretime"] * out_dict["framebinning"]
        )
        out_dict["field_of_view"] = (
            image_shape[0] * out_dict["pixelsize"],
            image_shape[1] * out_dict["pixelsize"],
        )
        out_dict["field_of_view_unit"] = out_dict["pixelsize_unit"]

        if include_native:
            out_dict["native"] = metadata
    except Exception as e:
        print(f"Error converting metadata: {e}")
        out_dict = empty_metadata()
    return out_dict


def lookup_pixelsize(metadata: dict):
    """
    Returns the pixel size in micrometers for known instruments.
    """
    if metadata.get("instrument") == "Refeyn OneMP":
        metadata["pixelsize"] = 0.0193
        metadata["pixelsize_unit"] = "um"
    elif metadata.get("instrument") == "Refeyn TwoMP":
        metadata["pixelsize"] = 0.0118
        metadata["pixelsize_unit"] = "um"
