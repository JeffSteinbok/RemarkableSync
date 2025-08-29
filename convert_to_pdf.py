#!/usr/bin/env python3
"""
Convert ReMarkable files to PDF using rmc

This script converts backed up ReMarkable notebooks to PDF files.
"""

import json
import logging
import subprocess
import sys
import shlex
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
import click
from tqdm import tqdm


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def find_notebooks(backup_dir: Path) -> tuple[List[Dict], Dict[str, Dict]]:
    """Find and parse notebook metadata from backup."""
    notebooks = []
    folders = {}
    files_dir = backup_dir / "files"
    
    if not files_dir.exists():
        logging.error(f"Backup files directory not found: {files_dir}")
        return [], {}
    
    # Look for .metadata files which indicate notebooks/documents
    for metadata_file in files_dir.glob("*.metadata"):
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            uuid = metadata_file.stem
            notebook_type = metadata.get('type', 'unknown')
            
            if notebook_type in ['CollectionType', 'DocumentType']:
                item_info = {
                    'uuid': uuid,
                    'name': metadata.get('visibleName', 'Untitled'),
                    'type': notebook_type,
                    'parent': metadata.get('parent', ''),
                    'metadata_file': metadata_file,
                    'content_file': files_dir / f"{uuid}.content",
                    'rm_files': list(files_dir.glob(f"{uuid}/*.rm")),
                    'pagedata_files': list(files_dir.glob(f"{uuid}/*.json"))
                }
                
                if notebook_type == 'CollectionType':
                    # This is a folder
                    folders[uuid] = item_info
                elif notebook_type == 'DocumentType':
                    # This is a notebook - only include if it has content or rm files
                    if item_info['content_file'].exists() or item_info['rm_files']:
                        notebooks.append(item_info)
                    
        except Exception as e:
            logging.warning(f"Failed to parse {metadata_file}: {e}")
    
    return notebooks, folders


def build_folder_path(parent_uuid: str, folders: Dict[str, Dict]) -> List[str]:
    """Build the folder path for an item by traversing up the parent chain."""
    path_components = []
    current_parent = parent_uuid
    
    # Traverse up the parent chain
    while current_parent and current_parent != "trash":
        if current_parent in folders:
            folder_name = folders[current_parent]['name']
            # Create safe folder name
            safe_folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            if safe_folder_name:
                path_components.append(safe_folder_name)
            current_parent = folders[current_parent]['parent']
        else:
            # Parent folder not found, break the chain
            break
    
    # Reverse to get correct order (root -> leaf)
    path_components.reverse()
    return path_components


def convert_notebook_to_pdf(notebook: Dict, output_base_dir: Path, folders: Dict[str, Dict]) -> Optional[Path]:
    """Convert a single notebook to PDF using rmc.

    Strategy:
      1. Attempt whole-directory conversion (multi-page) if .rm files exist.
      2. If that fails, fall back to per-page conversion collecting page PDFs.
      3. If no .rm files, create an _info.txt placeholder.
    Returns a representative Path or None.
    """
    # 1. Safe base name
    safe_name = "".join(c for c in notebook['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip() or f"notebook_{notebook['uuid'][:8]}"

    # 2. Resolve output subdirectory based on folder path
    folder_path_components = build_folder_path(notebook['parent'], folders)
    if notebook['parent'] == "trash":
        output_dir = output_base_dir / "trash"
    elif folder_path_components:
        output_dir = output_base_dir.joinpath(*folder_path_components)
    else:
        output_dir = output_base_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    whole_pdf = output_dir / f"{safe_name}.pdf"
    # Helper to convert SVG -> PDF (lazy import so missing deps can be reported nicely)
    def svg_to_pdf(svg_path: Path, pdf_path: Path) -> bool:
        try:
            from svglib.svglib import svg2rlg  # type: ignore
            from reportlab.graphics import renderPDF  # type: ignore
        except ImportError:
            logging.debug("svglib/reportlab not installed; cannot convert SVG to PDF")
            return False
        try:
            drawing = svg2rlg(str(svg_path))
            renderPDF.drawToFile(drawing, str(pdf_path))
            return pdf_path.exists() and pdf_path.stat().st_size > 500
        except Exception as e:  # noqa: BLE001
            logging.debug("SVG->PDF failed %s: %s", svg_path.name, e)
            return False
    rm_files = notebook.get('rm_files', [])

    # 3. Whole document attempt
    if rm_files:
        notebook_dir = rm_files[0].parent
        try:
            with tempfile.TemporaryDirectory() as tmpd:
                svg_whole = Path(tmpd) / f"{safe_name}.svg"
                cmd = ['rmc', '-t', 'svg', '-o', str(svg_whole), str(notebook_dir)]
                logging.debug("Running whole-doc SVG command: %s", ' '.join(shlex.quote(str(c)) for c in cmd))
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
                logging.debug("Whole SVG return code: %s", result.returncode)
                if result.stderr:
                    logging.debug("Whole SVG STDERR: %s", result.stderr.strip()[:500])
                if result.returncode == 0 and svg_whole.exists() and svg_whole.stat().st_size > 200:
                    if svg_to_pdf(svg_whole, whole_pdf):
                        logging.info("Whole convert via SVG OK: %s", notebook['name'])
                        return whole_pdf
                    else:
                        logging.debug("SVG->PDF whole failed for %s", notebook['name'])
                else:
                    logging.debug("Whole SVG generation failed for %s", notebook['name'])
        except subprocess.TimeoutExpired:
            logging.warning("Timeout whole SVG convert: %s", notebook['name'])
        except Exception as e:  # noqa: BLE001
            logging.warning("Error whole SVG convert %s: %s", notebook['name'], e)

    # 4. Per-page attempt
    page_pdfs: List[Path] = []
    for i, rm_file in enumerate(rm_files):
        page_pdf = output_dir / f"{safe_name}_page_{i+1:03d}.pdf"
        try:
            with tempfile.TemporaryDirectory() as tmpd:
                svg_page = Path(tmpd) / f"page_{i+1:03d}.svg"
                page_cmd = ['rmc', '-t', 'svg', '-o', str(svg_page), str(rm_file)]
                logging.debug("Running page SVG command: %s", ' '.join(shlex.quote(str(c)) for c in page_cmd))
                result = subprocess.run(page_cmd, capture_output=True, text=True, timeout=30)
                logging.debug("Return code (page %d SVG): %s", i+1, result.returncode)
                if result.stderr:
                    logging.debug("STDERR (page %d SVG): %s", i+1, result.stderr.strip()[:300])
                if result.returncode == 0 and svg_page.exists() and svg_page.stat().st_size > 200:
                    if svg_to_pdf(svg_page, page_pdf):
                        page_pdfs.append(page_pdf)
                    else:
                        logging.debug("SVG->PDF failed page %d (%s)", i+1, notebook['name'])
                else:
                    logging.debug("SVG gen failed page %d (%s)", i+1, notebook['name'])
        except subprocess.TimeoutExpired:
            logging.debug("Timeout page %d (%s)", i+1, notebook['name'])
        except Exception as e:  # noqa: BLE001
            logging.debug("Error page %d (%s): %s", i+1, notebook['name'], e)

    if page_pdfs:
        logging.info("Converted %d pages for %s", len(page_pdfs), notebook['name'])
        return page_pdfs[0]

    # 5. Placeholder info file
    info_path = output_dir / f"{safe_name}_info.txt"
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write(f"ReMarkable Notebook: {notebook['name']}\n")
        f.write(f"UUID: {notebook['uuid']}\n")
        f.write(f"Type: {notebook['type']}\n")
        f.write(f"Folder: {' / '.join(folder_path_components) if folder_path_components else 'Root'}\n")
        f.write(f"Pages with .rm files: {len(rm_files)}\n")
        if not rm_files:
            f.write("\nNote: No .rm drawing data present. Possibly empty or a folder placeholder.\n")
    logging.info("Created info file for %s", notebook['name'])
    return info_path


def merge_pdfs(pdf_files: List[Path], output_path: Path) -> bool:
    """Merge multiple PDF files into one (if possible)."""
    try:
        # Try to use PyPDF2 if available for merging
        try:
            from PyPDF2 import PdfMerger
            
            merger = PdfMerger()
            for pdf_file in pdf_files:
                if pdf_file.suffix.lower() == '.pdf':
                    merger.append(str(pdf_file))
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            merger.close()
            
            logging.info(f"Merged {len(pdf_files)} PDFs into {output_path}")
            return True
            
        except ImportError:
            logging.warning("PyPDF2 not available for merging PDFs")
            return False
            
    except Exception as e:
        logging.error(f"Failed to merge PDFs: {e}")
        return False


@click.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path), 
              default=Path('./remarkable_backup'),
              help='Directory containing ReMarkable backup files')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Directory to save PDF files (default: backup_dir/pdfs)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--merge-pages', is_flag=True, help='Merge per-page PDFs into a single file when possible')
@click.option('--limit', type=int, help='Limit number of notebooks processed (for testing)')
def main(backup_dir: Path, output_dir: Optional[Path], verbose: bool, merge_pages: bool, limit: Optional[int]):
    """Convert ReMarkable backup files to PDF using rmc"""
    
    setup_logging(verbose)
    
    if not backup_dir.exists():
        print(f"[ERROR] Backup directory not found: {backup_dir}")
        sys.exit(1)
    
    # Set default output directory
    if not output_dir:
        output_dir = backup_dir / "pdfs"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("ReMarkable to PDF Converter")
    print("=" * 40)
    print(f"Backup directory: {backup_dir}")
    print(f"Output directory: {output_dir}")
    
    # Find notebooks and folders
    notebooks, folders = find_notebooks(backup_dir)
    
    if not notebooks:
        print("[WARNING] No notebooks found in backup directory")
        print("Make sure you've run the backup tool first")
        sys.exit(0)
    
    print(f"\nFound {len(notebooks)} notebooks and {len(folders)} folders to convert:")
    for nb in notebooks[:5]:  # Show first 5
        rm_count = len(nb['rm_files'])
        # Show folder path
        folder_path = build_folder_path(nb['parent'], folders)
        folder_str = ' / '.join(folder_path) if folder_path else 'Root'
        if nb['parent'] == "trash":
            folder_str = 'Trash'
        print(f"  - {nb['name']} ({nb['type']}, {rm_count} pages) in [{folder_str}]")
    if len(notebooks) > 5:
        print(f"  ... and {len(notebooks)-5} more")
    
    # Optionally limit for testing
    if limit is not None:
        notebooks = notebooks[:limit]

    # Convert notebooks
    successful_conversions = 0
    failed_conversions = 0
    
    print(f"\nConverting notebooks to PDF with folder structure...")
    with tqdm(notebooks, desc="Converting") as pbar:
        for notebook in pbar:
            pbar.set_postfix_str(notebook['name'][:30])
            
            result = convert_notebook_to_pdf(notebook, output_dir, folders)
            if result:
                successful_conversions += 1
            else:
                failed_conversions += 1
    
    # Summary
    print(f"\n[SUMMARY] PDF Conversion Results:")
    print(f"Successfully converted: {successful_conversions}")
    print(f"Failed conversions: {failed_conversions}")
    print(f"Total notebooks: {len(notebooks)}")
    
    if successful_conversions > 0:
        print(f"\nPDF files saved to: {output_dir}")
        print("Files are organized in folders matching your ReMarkable structure")
        
        # List some of the created files and show directory structure
        pdf_files = list(output_dir.rglob("*.pdf"))  # Use rglob to find PDFs in all subdirectories
        txt_files = list(output_dir.rglob("*.txt"))  # Use rglob to find txt files in all subdirectories
        
        if pdf_files:
            print(f"Created {len(pdf_files)} PDF files")
        if txt_files:
            print(f"Created {len(txt_files)} info files")
            
        # Show a sample of the directory structure
        directories = [d for d in output_dir.rglob("*") if d.is_dir()]
        if directories:
            print(f"\nCreated {len(directories)} folders:")
            for directory in directories[:10]:  # Show first 10 folders
                relative_path = directory.relative_to(output_dir)
                print(f"  - {relative_path}")
            if len(directories) > 10:
                print(f"  ... and {len(directories)-10} more")
    
    if failed_conversions > 0:
        print(f"\n[NOTE] {failed_conversions} notebooks couldn't be converted")
        print("This is normal for empty notebooks or folders")


if __name__ == "__main__":
    main()