"""DWG to DXF conversion utilities.

Uses ODA File Converter for DWG to DXF conversion when available,
with fallback options for different environments.
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# Common ODA File Converter paths
ODA_PATHS = [
    # macOS
    "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
    "/usr/local/bin/ODAFileConverter",
    # Linux
    "/usr/bin/ODAFileConverter",
    "/opt/ODAFileConverter/ODAFileConverter",
    # Windows (common locations)
    "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
    "C:\\Program Files (x86)\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
]


def find_oda_converter() -> Optional[str]:
    """Find ODA File Converter executable."""
    # Check environment variable first
    env_path = os.environ.get("ODA_FILE_CONVERTER")
    if env_path and os.path.isfile(env_path):
        return env_path

    # Check common paths
    for path in ODA_PATHS:
        if os.path.isfile(path):
            return path

    # Try to find in PATH
    try:
        result = subprocess.run(
            ["which", "ODAFileConverter"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def convert_dwg_to_dxf(
    dwg_path: str | Path,
    output_dir: Optional[str | Path] = None,
    dxf_version: str = "ACAD2018",
) -> Optional[Path]:
    """
    Convert a DWG file to DXF format.

    Args:
        dwg_path: Path to the input DWG file
        output_dir: Directory for output DXF file (default: same as input)
        dxf_version: Target DXF version (default: ACAD2018)

    Returns:
        Path to the converted DXF file, or None if conversion failed

    Raises:
        FileNotFoundError: If input file doesn't exist
        RuntimeError: If ODA File Converter is not available
    """
    dwg_path = Path(dwg_path)

    if not dwg_path.exists():
        raise FileNotFoundError(f"DWG file not found: {dwg_path}")

    if not dwg_path.suffix.lower() == ".dwg":
        raise ValueError(f"Expected .dwg file, got: {dwg_path.suffix}")

    # Find converter
    converter_path = find_oda_converter()
    if not converter_path:
        raise RuntimeError(
            "ODA File Converter not found. Please install from: "
            "https://www.opendesign.com/guestfiles/oda_file_converter"
        )

    # Set up output directory
    if output_dir is None:
        output_dir = dwg_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary input directory (ODA works with directories)
    with tempfile.TemporaryDirectory() as temp_input:
        # Copy DWG to temp input
        temp_dwg = Path(temp_input) / dwg_path.name
        shutil.copy2(dwg_path, temp_dwg)

        # Create temp output directory
        with tempfile.TemporaryDirectory() as temp_output:
            # Run ODA File Converter
            # Format: ODAFileConverter <input_dir> <output_dir> <output_version> <output_type>
            cmd = [
                converter_path,
                temp_input,
                temp_output,
                dxf_version,
                "DXF",
                "0",  # Recurse: 0 = no
                "1",  # Audit: 1 = yes
            ]

            logger.info(f"Running ODA converter: {' '.join(cmd)}")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,  # 2 minute timeout
                )

                if result.returncode != 0:
                    logger.error(f"ODA converter error: {result.stderr}")
                    return None

            except subprocess.TimeoutExpired:
                logger.error("ODA converter timed out")
                return None
            except Exception as e:
                logger.error(f"ODA converter failed: {e}")
                return None

            # Find output DXF file
            dxf_name = dwg_path.stem + ".dxf"
            temp_dxf = Path(temp_output) / dxf_name

            if not temp_dxf.exists():
                # Try case-insensitive search
                for f in Path(temp_output).iterdir():
                    if f.suffix.lower() == ".dxf":
                        temp_dxf = f
                        break

            if not temp_dxf.exists():
                logger.error(f"DXF output not found in {temp_output}")
                return None

            # Copy to final output location
            final_dxf = output_dir / dxf_name
            shutil.copy2(temp_dxf, final_dxf)

            logger.info(f"Converted {dwg_path} to {final_dxf}")
            return final_dxf


def is_dwg_file(path: str | Path) -> bool:
    """Check if file is a DWG file."""
    return Path(path).suffix.lower() == ".dwg"


def is_dxf_file(path: str | Path) -> bool:
    """Check if file is a DXF file."""
    return Path(path).suffix.lower() == ".dxf"


def get_supported_versions() -> list[str]:
    """Get list of supported DXF output versions."""
    return [
        "ACAD9",
        "ACAD10",
        "ACAD12",
        "ACAD13",
        "ACAD14",
        "ACAD2000",
        "ACAD2004",
        "ACAD2007",
        "ACAD2010",
        "ACAD2013",
        "ACAD2018",
    ]
