"""
Hybrid ReMarkable PDF Converter - Internal Module

This is a helper module providing core conversion functionality.
Do not run directly - use the main RemarkableSync entry point instead.

Entry Point:
    RemarkableSync.py convert [OPTIONS]

This module provides:
- Automatic file version detection by reading .rm file headers
- Batch conversion with progress tracking
- Folder structure preservation matching ReMarkable organization
- PDF merging to create single documents from multi-page notebooks
- Support for v5 format files (rmrl) and v6 format files (rmc)
- Detection and reporting for v4/v3 files (limited support)
"""

import json
import logging
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Dict, List, Optional

# Import modular converter classes
from .converters import V4Converter, V5Converter, V6Converter
from .template_renderer import TemplateRenderer

# Suppress warnings from third-party libraries to reduce output noise
warnings.filterwarnings("ignore")


def setup_logging(verbose: bool = False):
    """Configure logging with appropriate levels and formatting.

    Sets up logging with timestamp formatting and suppresses verbose
    output from third-party libraries (svglib, reportlab) that can
    clutter the console during PDF conversion.

    Args:
        verbose: Enable DEBUG level logging if True, INFO level if False
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Suppress verbose debug messages from svglib that clutter the output
    logging.getLogger("svglib.svglib").setLevel(logging.WARNING)
    logging.getLogger("reportlab").setLevel(logging.WARNING)


# Initialize converter instances as module-level objects for reuse
v4_converter = V4Converter()
v5_converter = V5Converter()
v6_converter = V6Converter()


def find_notebooks(backup_dir: Path) -> List[Dict]:
    """Find and parse notebook metadata from backup directory.

    Scans the backup directory for .metadata files and analyzes associated
    .rm files to classify them by version for appropriate conversion tools.

    File Version Detection:
    - Reads the first 8 bytes of each .rm file to detect format version
    - version=5: Uses rmrl library (legacy format)
    - version=6: Uses rmc library (current format)
    - version=4: Detected but limited support (attempts rmrl fallback)
    - version=3: Detected but no conversion support

    Args:
        backup_dir: Path to the ReMarkable backup directory

    Returns:
        List of dictionaries containing notebook information:
        - uuid: Unique identifier for the notebook
        - name: Display name of the notebook
        - type: DocumentType or CollectionType (folder)
        - parent: UUID of parent folder (empty if root level)
        - metadata_file: Path to the .metadata file
        - rm_files: List of all .rm files for this notebook
        - v5_files, v6_files, v4_files, v3_files: Files categorized by version
        - pdf_files: Any existing PDF files in the notebook directory
    """
    notebooks: List[Dict] = []
    files_dir = backup_dir / "Notebooks"

    if not files_dir.exists():
        logging.error(f"Backup files directory not found: {files_dir}")
        return []

    for metadata_file in files_dir.glob("*.metadata"):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            uuid = metadata_file.stem
            notebook_type = metadata.get("type", "unknown")

            if notebook_type in ["CollectionType", "DocumentType"]:
                notebook_info: Dict = {
                    "uuid": uuid,
                    "name": metadata.get("visibleName", "Untitled"),
                    "type": notebook_type,
                    "parent": metadata.get("parent", ""),
                    "metadata_file": metadata_file,
                    "rm_files": list(files_dir.glob(f"{uuid}/*.rm")),
                    "pdf_files": list(files_dir.glob(f"{uuid}/*.pdf")),
                }

                # Analyze file versions
                notebook_info["v5_files"] = []
                notebook_info["v6_files"] = []
                notebook_info["v4_files"] = []
                notebook_info["v3_files"] = []

                for rm_file in notebook_info["rm_files"]:
                    try:
                        # Read file header to determine version format
                        # Each .rm file starts with a version identifier in ASCII
                        with open(rm_file, "rb") as f:
                            header = f.read(50).decode("ascii", errors="ignore")
                            # Classify files by version for appropriate conversion tool
                            if "version=6" in header:
                                notebook_info["v6_files"].append(rm_file)
                            elif "version=5" in header:
                                notebook_info["v5_files"].append(rm_file)
                            elif "version=4" in header:
                                notebook_info["v4_files"].append(rm_file)
                            elif "version=3" in header:
                                notebook_info["v3_files"].append(rm_file)
                    except Exception:
                        # Ignore files that can't be read or don't have valid headers
                        pass

                # Include in conversion list if it's a folder or has convertible content
                # - CollectionType: Folders (included for directory structure)
                # - Documents with any version of .rm files or existing PDFs
                if (
                    notebook_type == "CollectionType"
                    or notebook_info["v5_files"]
                    or notebook_info["v6_files"]
                    or notebook_info["v4_files"]
                    or notebook_info["v3_files"]
                    or notebook_info["pdf_files"]
                ):
                    notebooks.append(notebook_info)

        except Exception as e:  # noqa: BLE001
            logging.warning(f"Failed to parse {metadata_file}: {e}")

    return notebooks


def svg_to_pdf(svg_file: Path, pdf_file: Path) -> bool:
    """Convert SVG to PDF using modular converter utilities.

    This is a wrapper function that maintains backward compatibility
    while using the new modular converter architecture.

    Args:
        svg_file: Path to input SVG file
        pdf_file: Path to output PDF file

    Returns:
        bool: True if conversion successful, False otherwise
    """
    # Use any converter instance for the utility method since it's in the base class
    return v6_converter.svg_to_pdf(svg_file, pdf_file)


def merge_pdf_with_template(
    content_pdf: Path, template_pdf: Optional[Path], output_pdf: Path
) -> bool:
    """Merge a content PDF with a template background PDF.

    Args:
        content_pdf: Path to PDF with notebook content
        template_pdf: Path to PDF with template background (None for no template)
        output_pdf: Path where merged PDF should be saved

    Returns:
        bool: True if merge successful, False otherwise
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter

        if not content_pdf.exists():
            return False

        content_reader = PdfReader(str(content_pdf))
        writer = PdfWriter()

        # If we have a template, merge it with the content
        if template_pdf and template_pdf.exists():
            template_reader = PdfReader(str(template_pdf))
            if len(template_reader.pages) > 0:
                # For each content page, start with a fresh copy of the template
                for content_page in content_reader.pages:
                    # Get a fresh copy of the template page (always use first template page)
                    template_copy = PdfReader(str(template_pdf)).pages[0]

                    # Merge content on top of template
                    template_copy.merge_page(content_page)
                    writer.add_page(template_copy)
            else:
                # No template pages, just copy content
                for page in content_reader.pages:
                    writer.add_page(page)
        else:
            # No template, just copy content
            for page in content_reader.pages:
                writer.add_page(page)

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        with open(output_pdf, "wb") as f:
            writer.write(f)

        return output_pdf.exists() and output_pdf.stat().st_size > 0

    except Exception as e:
        logging.debug(f"PDF template merge failed: {e}")
        return False


def merge_pdfs(pdf_files: List[Path], output_file: Path) -> bool:
    """Merge multiple PDF files into a single PDF document.

    Takes a list of individual page PDFs and combines them into
    a single multi-page PDF document, maintaining page order.

    Args:
        pdf_files: List of PDF file paths to merge (in order)
        output_file: Path where merged PDF should be saved

    Returns:
        bool: True if merge successful, False otherwise

    Note:
        Uses PyPDF2 for PDF manipulation. Creates parent directories
        if they don't exist.
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter

        writer = PdfWriter()

        for pdf_file in pdf_files:
            if pdf_file.exists():
                reader = PdfReader(str(pdf_file))
                for page in reader.pages:
                    writer.add_page(page)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "wb") as f:
            writer.write(f)

        return output_file.exists() and output_file.stat().st_size > 0

    except Exception as e:
        logging.debug(f"PDF merge failed: {e}")
        return False


def organize_notebooks_by_structure(notebooks: List[Dict], backup_dir: Path) -> Dict:
    """Organize notebooks into their folder structure for conversion.

    Analyzes the parent-child relationships between notebooks and folders
    to recreate the ReMarkable folder structure in the output directory.
    This ensures PDFs are organized the same way as on the device.

    Args:
        notebooks: List of notebook dictionaries from find_notebooks()
        backup_dir: Path to backup directory (used for hierarchy resolution)

    Returns:
        Dictionary with:
        - 'documents': List of document notebooks to convert
        - 'structure': Dict mapping folder paths to lists of notebooks

    Note:
        Folder hierarchy is determined by following parent UUIDs up
        to the root level, creating folder paths like "Work/Projects/Notes"
    """
    # Build folder structure
    folder_structure = {}
    documents_to_convert = []

    for item in notebooks:
        if item["type"] == "DocumentType":
            # This is a notebook to convert
            hierarchy = get_folder_hierarchy(item, backup_dir)
            folder_path = "/".join(hierarchy) if hierarchy else ""

            item["folder_path"] = folder_path
            documents_to_convert.append(item)

            # Ensure folder exists in structure
            if folder_path not in folder_structure:
                folder_structure[folder_path] = []
            folder_structure[folder_path].append(item)

    return {"folder_structure": folder_structure, "documents_to_convert": documents_to_convert}


def get_folder_hierarchy(notebook: Dict, backup_dir: Path) -> List[str]:
    """Get the folder hierarchy for a notebook by following parent UUIDs."""
    hierarchy = []
    current_uuid = notebook.get("parent")
    files_dir = backup_dir / "files"

    while current_uuid and current_uuid != "":
        try:
            metadata_file = files_dir / f"{current_uuid}.metadata"
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                folder_name = metadata.get("visibleName", "Unknown")
                # Create safe folder name
                safe_folder = "".join(
                    c for c in folder_name if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                if safe_folder:
                    hierarchy.insert(0, safe_folder)  # Insert at beginning to build path
                current_uuid = metadata.get("parent")
            else:
                break
        except Exception as e:
            logging.debug(f"Failed to read parent metadata for {current_uuid}: {e}")
            break

    return hierarchy


def convert_v6_file_with_rmc(rm_file: Path, output_file: Path) -> bool:
    """Convert v6 format .rm file to PDF using modular V6Converter.

    This is a wrapper function that maintains backward compatibility
    while using the new modular converter architecture.

    Args:
        rm_file: Path to the v6 format .rm file
        output_file: Path where PDF should be saved

    Returns:
        bool: True if conversion successful, False otherwise
    """
    return v6_converter.convert_to_pdf(rm_file, output_file)


def convert_v5_file_with_rmrl(rm_file: Path, output_file: Path) -> bool:
    """Convert v5 format .rm file to PDF using modular V5Converter.

    This is a wrapper function that maintains backward compatibility
    while using the new modular converter architecture.

    Args:
        rm_file: Path to the v5 format .rm file
        output_file: Path where PDF should be saved

    Returns:
        bool: True if conversion successful, False otherwise
    """
    return v5_converter.convert_to_pdf(rm_file, output_file)


def convert_v4_file_with_rmrl(rm_file: Path, output_file: Path) -> bool:
    """Convert v4 format .rm file to PDF using modular V4Converter.

    This is a wrapper function that maintains backward compatibility
    while using the new modular converter architecture.

    Args:
        rm_file: Path to the v4 format .rm file
        output_file: Path where PDF should be saved

    Returns:
        bool: True if conversion successful, False otherwise

    Note:
        v4 format support is limited and may fail for many files.
    """
    return v4_converter.convert_to_pdf(rm_file, output_file)


def copy_existing_pdf(pdf_file: Path, output_file: Path) -> bool:
    """Copy existing PDF file using base converter utility.

    This is a wrapper function that maintains backward compatibility
    while using the modular converter architecture.

    Args:
        pdf_file: Path to the source PDF file
        output_file: Path where PDF should be copied

    Returns:
        bool: True if copy successful, False otherwise
    """
    # Use any converter instance for the utility method since it's in the base class
    return v6_converter.copy_existing_pdf(pdf_file, output_file)


def get_page_templates(content_file: Path) -> Dict[str, str]:
    """Extract template names for each page from .content file.

    Args:
        content_file: Path to the .content JSON file

    Returns:
        Dictionary mapping page IDs to template names
    """
    page_templates = {}

    if not content_file or not content_file.exists():
        return page_templates

    try:
        with open(content_file, "r", encoding="utf-8") as f:
            content_data = json.load(f)

        # Extract pages from cPages structure
        c_pages = content_data.get("cPages", {})
        pages = c_pages.get("pages", [])

        for page in pages:
            page_id = page.get("id")
            template_info = page.get("template", {})
            template_name = template_info.get("value", "Blank")

            if page_id:
                page_templates[page_id] = template_name

    except Exception as e:
        logging.debug(f"Failed to extract page templates from {content_file}: {e}")

    return page_templates


def convert_notebook(
    notebook: Dict,
    output_dir: Path,
    backup_dir: Path,
    template_renderer: Optional[TemplateRenderer] = None,
) -> Dict:
    """Convert a notebook using appropriate tools for each file type.

    Creates a single PDF per notebook with all pages merged together.
    Organizes output in folder hierarchy matching backup structure.
    """
    # Create safe filename
    safe_name = "".join(c for c in notebook["name"] if c.isalnum() or c in (" ", "-", "_")).rstrip()
    if not safe_name:
        safe_name = f"notebook_{notebook['uuid'][:8]}"

    # Use pre-computed folder path from organization
    folder_path = notebook.get("folder_path", "")

    # Create output directory with folder structure
    output_notebook_dir = output_dir
    if folder_path:
        for folder in folder_path.split("/"):
            output_notebook_dir = output_notebook_dir / folder
    output_notebook_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "name": notebook["name"],
        "folder_path": str(output_notebook_dir.relative_to(output_dir)) if folder_path else "",
        "v5_converted": 0,
        "v6_converted": 0,
        "v4_converted": 0,
        "pdfs_copied": 0,
        "v4_detected": len(notebook.get("v4_files", [])),
        "v3_detected": len(notebook.get("v3_files", [])),
        "total_files": 0,
        "output_files": [],
    }

    # Collect all PDF pages to merge
    temp_pdfs = []

    # Create temporary directories in OS standard temp location
    temp_dir = Path(tempfile.mkdtemp(prefix="remarkable_pages_"))
    template_temp_dir = None
    if template_renderer:
        template_temp_dir = Path(tempfile.mkdtemp(prefix="remarkable_templates_"))

    try:
        # Resolve ordered pages using .content file if present (v5 ordering)
        metadata_file = notebook.get("metadata_file")
        content_path = metadata_file.with_suffix(".content") if metadata_file else None

        # Extract page templates from content file
        page_templates = {}
        if template_renderer and content_path:
            page_templates = get_page_templates(content_path)

        ordered_v5_pages: List[Path] = []
        if content_path and content_path.exists():
            try:
                with open(content_path, "r", encoding="utf-8") as cf:
                    content_json = json.load(cf)
                page_ids = content_json.get("pages", [])
                base_dir = content_path.parent / content_path.stem
                for pid in page_ids:
                    candidate = base_dir / f"{pid}.rm"
                    if candidate.exists():
                        ordered_v5_pages.append(candidate)
                    else:
                        # fallback: find rm page anywhere under files matching page id
                        alt = list((content_path.parent).glob(f"{pid}.rm"))
                        if alt:
                            ordered_v5_pages.append(alt[0])
            except Exception as e:
                logging.debug("Failed reading content ordering for %s: %s", notebook["name"], e)

        # Fallback to unsorted list if ordering extraction failed
        if not ordered_v5_pages:
            ordered_v5_pages = notebook["v5_files"]

        # Convert v5 files in determined order
        for i, rm_file in enumerate(ordered_v5_pages):
            temp_pdf_content = temp_dir / f"v5_page_{i+1:03d}_content.pdf"
            if convert_v5_file_with_rmrl(rm_file, temp_pdf_content):
                # Apply template if available
                if template_renderer and template_temp_dir:
                    page_id = rm_file.stem
                    template_name = page_templates.get(page_id, "Blank")

                    if template_name and template_name != "Blank":
                        temp_template_pdf = template_temp_dir / f"template_{i+1:03d}.pdf"
                        temp_pdf_final = temp_dir / f"v5_page_{i+1:03d}.pdf"

                        if template_renderer.render_template_to_pdf(
                            template_name, temp_template_pdf
                        ):
                            if merge_pdf_with_template(
                                temp_pdf_content, temp_template_pdf, temp_pdf_final
                            ):
                                temp_pdfs.append(temp_pdf_final)
                                results["v5_converted"] += 1
                            else:
                                temp_pdfs.append(temp_pdf_content)
                                results["v5_converted"] += 1
                        else:
                            temp_pdfs.append(temp_pdf_content)
                            results["v5_converted"] += 1
                    else:
                        temp_pdfs.append(temp_pdf_content)
                        results["v5_converted"] += 1
                else:
                    temp_pdfs.append(temp_pdf_content)
                    results["v5_converted"] += 1

        # Convert v6 files
        for i, rm_file in enumerate(notebook["v6_files"]):
            temp_pdf_content = temp_dir / f"v6_page_{i+1:03d}_content.pdf"
            if convert_v6_file_with_rmc(rm_file, temp_pdf_content):
                # Apply template if available
                if template_renderer and template_temp_dir:
                    page_id = rm_file.stem
                    template_name = page_templates.get(page_id, "Blank")

                    if template_name and template_name != "Blank":
                        temp_template_pdf = template_temp_dir / f"template_{i+1:03d}.pdf"
                        temp_pdf_final = temp_dir / f"v6_page_{i+1:03d}.pdf"

                        if template_renderer.render_template_to_pdf(
                            template_name, temp_template_pdf
                        ):
                            if merge_pdf_with_template(
                                temp_pdf_content, temp_template_pdf, temp_pdf_final
                            ):
                                temp_pdfs.append(temp_pdf_final)
                                results["v6_converted"] += 1
                            else:
                                temp_pdfs.append(temp_pdf_content)
                                results["v6_converted"] += 1
                        else:
                            temp_pdfs.append(temp_pdf_content)
                            results["v6_converted"] += 1
                    else:
                        temp_pdfs.append(temp_pdf_content)
                        results["v6_converted"] += 1
                else:
                    temp_pdfs.append(temp_pdf_content)
                    results["v6_converted"] += 1

        # Convert v4 files (best-effort; may not succeed)
        for i, rm_file in enumerate(notebook.get("v4_files", [])):
            temp_pdf = temp_dir / f"v4_page_{i+1:03d}.pdf"
            if convert_v4_file_with_rmrl(rm_file, temp_pdf):
                temp_pdfs.append(temp_pdf)
                results["v4_converted"] += 1

        # Copy existing PDFs
        for i, pdf_file in enumerate(notebook["pdf_files"]):
            temp_pdf = temp_dir / f"existing_{i+1:03d}.pdf"
            if copy_existing_pdf(pdf_file, temp_pdf):
                temp_pdfs.append(temp_pdf)
                results["pdfs_copied"] += 1

        # Create merged PDF if we have any pages
        if temp_pdfs:
            final_pdf = output_notebook_dir / f"{safe_name}.pdf"
            if merge_pdfs(temp_pdfs, final_pdf):
                results["output_files"].append(final_pdf)
                logging.info(
                    f"✓ {notebook['name']}: Merged {len(temp_pdfs)} pages into {final_pdf.name}"
                )
            else:
                logging.warning(f"✗ {notebook['name']}: Failed to merge {len(temp_pdfs)} pages")

        results["total_files"] = (
            len(notebook["v5_files"])
            + len(notebook["v6_files"])
            + len(notebook.get("v4_files", []))
            + len(notebook.get("v3_files", []))
            + len(notebook["pdf_files"])
        )

        # Unsupported versions note
        if results["v4_detected"] or results["v3_detected"]:
            unsupported_info = output_notebook_dir / f"{safe_name}_unsupported.txt"
            try:
                with open(unsupported_info, "w", encoding="utf-8") as f:
                    f.write(f"Notebook: {notebook['name']}\n")
                    f.write(f"UUID: {notebook['uuid']}\n\n")
                    f.write("Detected unsupported .rm versions:\n")
                    if results["v4_detected"]:
                        f.write(
                            f"  - v4 pages: {results['v4_detected']} (no converter implemented yet)\n"
                        )
                    if results["v3_detected"]:
                        f.write(f"  - v3 pages: {results['v3_detected']} (legacy format)\n")
                    f.write(
                        "\nSuggestion: Keep these files; future tooling or an older firmware converter may be needed.\n"
                    )
                results["output_files"].append(unsupported_info)
            except Exception as e:
                logging.debug("Could not write unsupported info for %s: %s", notebook["name"], e)

    finally:
        # Clean up temporary directories in OS temp location
        try:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if template_temp_dir and template_temp_dir.exists():
                shutil.rmtree(template_temp_dir, ignore_errors=True)
        except Exception as e:
            logging.debug(f"Cleanup error: {e}")

    return results
