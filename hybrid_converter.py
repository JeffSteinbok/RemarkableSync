#!/usr/bin/env python3
"""
Hybrid ReMarkable PDF Converter

Uses the cor                    notebook_info['v3_files'] = []

                # Parse parent information for folder hierarchy
                notebook_info['parent'] = metadata.get('parent', '')

                for rm_file in notebook_info['rm_files']:t tools for each file version:
- rmrl for v5 files
- rmc for v6 files
- (placeholder) v4 files detected and reported separately
"""

import json
import logging
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional
import click
from tqdm import tqdm

# Suppress warnings
warnings.filterwarnings("ignore")

def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Suppress verbose debug messages from svglib that clutter the output
    logging.getLogger('svglib.svglib').setLevel(logging.WARNING)
    logging.getLogger('reportlab').setLevel(logging.WARNING)

def find_notebooks(backup_dir: Path) -> List[Dict]:
    """Find and parse notebook metadata from backup.

    For each notebook we classify contained .rm files by version header.
    Currently supported conversions:
      - version=5 via rmrl
      - version=6 via rmc
    Detected-but-unsupported (placeholders only):
      - version=4 (historic format, attempted with rmrl fallback)
      - version=3 (older / experimental?)
    """
    notebooks: List[Dict] = []
    files_dir = backup_dir / "files"

    if not files_dir.exists():
        logging.error(f"Backup files directory not found: {files_dir}")
        return []

    for metadata_file in files_dir.glob("*.metadata"):
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            uuid = metadata_file.stem
            notebook_type = metadata.get('type', 'unknown')

            if notebook_type in ['CollectionType', 'DocumentType']:
                notebook_info: Dict = {
                    'uuid': uuid,
                    'name': metadata.get('visibleName', 'Untitled'),
                    'type': notebook_type,
                    'parent': metadata.get('parent', ''),
                    'metadata_file': metadata_file,
                    'rm_files': list(files_dir.glob(f"{uuid}/*.rm")),
                    'pdf_files': list(files_dir.glob(f"{uuid}/*.pdf")),
                }

                # Analyze file versions
                notebook_info['v5_files'] = []
                notebook_info['v6_files'] = []
                notebook_info['v4_files'] = []
                notebook_info['v3_files'] = []

                for rm_file in notebook_info['rm_files']:
                    try:
                        with open(rm_file, 'rb') as f:
                            header = f.read(50).decode('ascii', errors='ignore')
                            if 'version=6' in header:
                                notebook_info['v6_files'].append(rm_file)
                            elif 'version=5' in header:
                                notebook_info['v5_files'].append(rm_file)
                            elif 'version=4' in header:
                                notebook_info['v4_files'].append(rm_file)
                            elif 'version=3' in header:
                                notebook_info['v3_files'].append(rm_file)
                    except Exception:
                        pass

                # Include folders (CollectionType) and documents with content
                if (notebook_type == 'CollectionType' or 
                    notebook_info['v5_files'] or
                    notebook_info['v6_files'] or
                    notebook_info['v4_files'] or
                    notebook_info['v3_files'] or
                    notebook_info['pdf_files']):
                    notebooks.append(notebook_info)

        except Exception as e:  # noqa: BLE001
            logging.warning(f"Failed to parse {metadata_file}: {e}")

    return notebooks

def svg_to_pdf(svg_file: Path, pdf_file: Path) -> bool:
    """Convert SVG to PDF using svglib."""
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPDF
        
        # Convert SVG to ReportLab drawing
        drawing = svg2rlg(str(svg_file))
        
        # Render to PDF
        renderPDF.drawToFile(drawing, str(pdf_file))
        
        return pdf_file.exists() and pdf_file.stat().st_size > 0
        
    except Exception as e:
        logging.debug(f"SVG to PDF conversion failed: {e}")
        return False

def merge_pdfs(pdf_files: List[Path], output_file: Path) -> bool:
    """Merge multiple PDF files into a single PDF."""
    try:
        from PyPDF2 import PdfWriter, PdfReader
        
        writer = PdfWriter()
        
        for pdf_file in pdf_files:
            if pdf_file.exists():
                reader = PdfReader(str(pdf_file))
                for page in reader.pages:
                    writer.add_page(page)
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'wb') as f:
            writer.write(f)
        
        return output_file.exists() and output_file.stat().st_size > 0
        
    except Exception as e:
        logging.debug(f"PDF merge failed: {e}")
        return False

def organize_notebooks_by_structure(notebooks: List[Dict], backup_dir: Path) -> Dict:
    """Organize notebooks into their folder structure for conversion."""
    # Create lookup for all items by UUID
    all_items = {item['uuid']: item for item in notebooks}
    
    # Build folder structure
    folder_structure = {}
    documents_to_convert = []
    
    for item in notebooks:
        if item['type'] == 'DocumentType':
            # This is a notebook to convert
            hierarchy = get_folder_hierarchy(item, backup_dir)
            folder_path = '/'.join(hierarchy) if hierarchy else ''
            
            item['folder_path'] = folder_path
            documents_to_convert.append(item)
            
            # Ensure folder exists in structure
            if folder_path not in folder_structure:
                folder_structure[folder_path] = []
            folder_structure[folder_path].append(item)
    
    return {
        'folder_structure': folder_structure,
        'documents_to_convert': documents_to_convert
    }

def get_folder_hierarchy(notebook: Dict, backup_dir: Path) -> List[str]:
    """Get the folder hierarchy for a notebook by following parent UUIDs."""
    hierarchy = []
    current_uuid = notebook.get('parent')
    files_dir = backup_dir / "files"
    
    while current_uuid and current_uuid != "":
        try:
            metadata_file = files_dir / f"{current_uuid}.metadata"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                folder_name = metadata.get('visibleName', 'Unknown')
                # Create safe folder name
                safe_folder = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).strip()
                if safe_folder:
                    hierarchy.insert(0, safe_folder)  # Insert at beginning to build path
                current_uuid = metadata.get('parent')
            else:
                break
        except Exception as e:
            logging.debug(f"Failed to read parent metadata for {current_uuid}: {e}")
            break
    
    return hierarchy

def convert_v6_file_with_rmc(rm_file: Path, output_file: Path) -> bool:
    """Convert v6 .rm file to PDF using rmc via SVG intermediate."""
    try:
        # Create temporary SVG file
        svg_file = output_file.with_suffix('.svg')
        
        # Convert to SVG first
        result = subprocess.run([
            'rmc', '-t', 'svg', '-o', str(svg_file), str(rm_file)
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and svg_file.exists():
            # Convert SVG to PDF
            success = svg_to_pdf(svg_file, output_file)
            # Clean up temporary SVG
            try:
                svg_file.unlink()
            except:
                pass
            return success
        else:
            logging.debug(f"rmc SVG failed for {rm_file.name}: {result.stderr}")
            return False
            
    except Exception as e:
        logging.debug(f"rmc error for {rm_file.name}: {e}")
        return False

def convert_v5_file_with_rmrl(rm_file: Path, output_file: Path) -> bool:
    """Convert v5 .rm file to PDF using rmrl via SVG intermediate."""
    try:
        import rmrl
        
        # Create output directory
        output_file.parent.mkdir(parents=True, exist_ok=True)
        if not rm_file.exists():
            logging.debug("v5 source missing: %s (cwd=%s)", rm_file, Path.cwd())
            return False
        logging.debug("v5 source present: %s size=%d", rm_file, rm_file.stat().st_size)
        sibling_sample = [p.name for p in rm_file.parent.glob('*')][:20]
        logging.debug("v5 sibling sample (%d total): %s", len(list(rm_file.parent.glob('*'))), sibling_sample)
        
        # Create temporary SVG file
        svg_file = output_file.with_suffix('.svg')
        
        # Try to render to SVG first (rmrl might support SVG output)
        try:
            svg_data = rmrl.render(str(rm_file), template='svg')
            if svg_data:
                with open(svg_file, 'wb') as f:
                    f.write(svg_data)
                # Convert SVG to PDF
                success = svg_to_pdf(svg_file, output_file)
                # Clean up temporary SVG
                try:
                    svg_file.unlink()
                except:
                    pass
                return success
        except:
            # Fall back to original method if SVG doesn't work
            pdf_data = rmrl.render(str(rm_file))
            if pdf_data:
                with open(output_file, 'wb') as f:
                    f.write(pdf_data)
                return True
            
        return False
            
    except Exception as e:
        logging.debug(f"rmrl error for {rm_file.name}: {e}")
        return False

def convert_v4_file_with_rmrl(rm_file: Path, output_file: Path) -> bool:
    """Best-effort convert v4 .rm file using rmrl (may fail)."""
    try:
        import rmrl  # type: ignore
        output_file.parent.mkdir(parents=True, exist_ok=True)
        if not rm_file.exists():
            logging.debug("v4 source missing: %s (cwd=%s)", rm_file, Path.cwd())
            return False
        logging.debug("v4 source present: %s size=%d", rm_file, rm_file.stat().st_size)
        pdf_data = rmrl.render(str(rm_file))  # Some v4 files may render; if not, exception thrown
        if pdf_data:
            with open(output_file, 'wb') as f:
                f.write(pdf_data)
            return True
        return False
    except Exception:
        logging.debug("v4 render failure for %s", rm_file, exc_info=True)
        return False

def copy_existing_pdf(pdf_file: Path, output_file: Path) -> bool:
    """Copy existing PDF file."""
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pdf_file, 'rb') as src, open(output_file, 'wb') as dst:
            dst.write(src.read())
        return True
    except Exception as e:
        logging.debug(f"PDF copy error for {pdf_file.name}: {e}")
        return False

def convert_notebook(notebook: Dict, output_dir: Path, backup_dir: Path) -> Dict:
    """Convert a notebook using appropriate tools for each file type.
    
    Creates a single PDF per notebook with all pages merged together.
    Organizes output in folder hierarchy matching backup structure.
    """
    # Create safe filename
    safe_name = "".join(c for c in notebook['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_name:
        safe_name = f"notebook_{notebook['uuid'][:8]}"
    
    # Use pre-computed folder path from organization
    folder_path = notebook.get('folder_path', '')
    
    # Create output directory with folder structure
    output_notebook_dir = output_dir
    if folder_path:
        for folder in folder_path.split('/'):
            output_notebook_dir = output_notebook_dir / folder
    output_notebook_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'name': notebook['name'],
        'folder_path': str(output_notebook_dir.relative_to(output_dir)) if folder_path else "",
        'v5_converted': 0,
        'v6_converted': 0,
        'v4_converted': 0,
        'pdfs_copied': 0,
        'v4_detected': len(notebook.get('v4_files', [])),
        'v3_detected': len(notebook.get('v3_files', [])),
        'total_files': 0,
        'output_files': []
    }
    
    # Collect all PDF pages to merge
    temp_pdfs = []
    temp_dir = output_notebook_dir / "temp_pages"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # Resolve ordered pages using .content file if present (v5 ordering)
        content_path = notebook.get('metadata_file').with_suffix('.content') if notebook.get('metadata_file') else None
        ordered_v5_pages: List[Path] = []
        if content_path and content_path.exists():
            try:
                with open(content_path, 'r', encoding='utf-8') as cf:
                    content_json = json.load(cf)
                page_ids = content_json.get('pages', [])
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
                logging.debug("Failed reading content ordering for %s: %s", notebook['name'], e)
        
        # Fallback to unsorted list if ordering extraction failed
        if not ordered_v5_pages:
            ordered_v5_pages = notebook['v5_files']

        # Convert v5 files in determined order
        for i, rm_file in enumerate(ordered_v5_pages):
            temp_pdf = temp_dir / f"v5_page_{i+1:03d}.pdf"
            if convert_v5_file_with_rmrl(rm_file, temp_pdf):
                temp_pdfs.append(temp_pdf)
                results['v5_converted'] += 1
        
        # Convert v6 files  
        for i, rm_file in enumerate(notebook['v6_files']):
            temp_pdf = temp_dir / f"v6_page_{i+1:03d}.pdf"
            if convert_v6_file_with_rmc(rm_file, temp_pdf):
                temp_pdfs.append(temp_pdf)
                results['v6_converted'] += 1
        
        # Convert v4 files (best-effort; may not succeed)
        for i, rm_file in enumerate(notebook.get('v4_files', [])):
            temp_pdf = temp_dir / f"v4_page_{i+1:03d}.pdf"
            if convert_v4_file_with_rmrl(rm_file, temp_pdf):
                temp_pdfs.append(temp_pdf)
                results['v4_converted'] += 1

        # Copy existing PDFs
        for i, pdf_file in enumerate(notebook['pdf_files']):
            temp_pdf = temp_dir / f"existing_{i+1:03d}.pdf"
            if copy_existing_pdf(pdf_file, temp_pdf):
                temp_pdfs.append(temp_pdf)
                results['pdfs_copied'] += 1
        
        # Create merged PDF if we have any pages
        if temp_pdfs:
            final_pdf = output_notebook_dir / f"{safe_name}.pdf"
            if merge_pdfs(temp_pdfs, final_pdf):
                results['output_files'].append(final_pdf)
                logging.info(f"✓ {notebook['name']}: Merged {len(temp_pdfs)} pages into {final_pdf.name}")
            else:
                logging.warning(f"✗ {notebook['name']}: Failed to merge {len(temp_pdfs)} pages")
        
        results['total_files'] = (len(notebook['v5_files']) + len(notebook['v6_files']) +
                                  len(notebook.get('v4_files', [])) + len(notebook.get('v3_files', [])) +
                                  len(notebook['pdf_files']))

        # Unsupported versions note
        if results['v4_detected'] or results['v3_detected']:
            unsupported_info = output_notebook_dir / f"{safe_name}_unsupported.txt"
            try:
                with open(unsupported_info, 'w', encoding='utf-8') as f:
                    f.write(f"Notebook: {notebook['name']}\n")
                    f.write(f"UUID: {notebook['uuid']}\n\n")
                    f.write("Detected unsupported .rm versions:\n")
                    if results['v4_detected']:
                        f.write(f"  - v4 pages: {results['v4_detected']} (no converter implemented yet)\n")
                    if results['v3_detected']:
                        f.write(f"  - v3 pages: {results['v3_detected']} (legacy format)\n")
                    f.write("\nSuggestion: Keep these files; future tooling or an older firmware converter may be needed.\n")
                results['output_files'].append(unsupported_info)
            except Exception as e:
                logging.debug("Could not write unsupported info for %s: %s", notebook['name'], e)
    
    finally:
        # Clean up temporary files
        try:
            for temp_pdf in temp_pdfs:
                if temp_pdf.exists():
                    temp_pdf.unlink()
            if temp_dir.exists():
                temp_dir.rmdir()
        except Exception as e:
            logging.debug(f"Cleanup error: {e}")
    
    return results

@click.command()
@click.option('--backup-dir', '-d', type=click.Path(path_type=Path), 
              default=Path('./remarkable_backup'),
              help='Directory containing ReMarkable backup files')
@click.option('--output-dir', '-o', type=click.Path(path_type=Path),
              help='Directory to save PDF files (default: backup_dir/pdfs_final)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--sample', '-s', type=int, help='Convert only first N notebooks (for testing)')
@click.option('--updated-only', type=click.Path(path_type=Path),
              help='File containing list of updated notebook UUIDs to convert')
def main(backup_dir: Path, output_dir: Optional[Path], verbose: bool, sample: Optional[int], updated_only: Optional[Path]):
    """Hybrid ReMarkable PDF Converter - uses rmrl for v5, rmc for v6"""
    
    setup_logging(verbose)
    
    if not backup_dir.exists():
        print(f"[ERROR] Backup directory not found: {backup_dir}")
        sys.exit(1)
    
    # Set default output directory
    if not output_dir:
        output_dir = backup_dir / "pdfs_final"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("ReMarkable Hybrid PDF Converter")
    print("=" * 40)
    print(f"Backup directory: {backup_dir}")
    print(f"Output directory: {output_dir}")
    print("Uses: rmrl for v5 files, rmc for v6 files")
    
    # Load updated notebooks list if provided
    updated_uuids = None
    if updated_only:
        if not updated_only.exists():
            print(f"[ERROR] Updated notebooks file not found: {updated_only}")
            sys.exit(1)
        
        try:
            with open(updated_only, 'r', encoding='utf-8') as f:
                updated_uuids = set(line.strip() for line in f if line.strip())
            print(f"[SELECTIVE MODE] Converting only {len(updated_uuids)} updated notebooks")
        except OSError as e:
            print(f"[ERROR] Failed to read updated notebooks file: {e}")
            sys.exit(1)
    
    # Find notebooks and organize by folder structure
    all_items = find_notebooks(backup_dir)
    
    if not all_items:
        print("[WARNING] No items found in backup directory")
        sys.exit(0)
    
    # Filter by updated UUIDs if provided
    if updated_uuids:
        all_items = [item for item in all_items if item['uuid'] in updated_uuids]
        if not all_items:
            print("[INFO] No updated notebooks found for conversion")
            sys.exit(0)
    
    # Organize into folder structure
    organization = organize_notebooks_by_structure(all_items, backup_dir)
    notebooks = organization['documents_to_convert']
    
    if not notebooks:
        print("[WARNING] No convertible notebooks found")
        sys.exit(0)
    
    # Apply sample limit if specified
    if sample and sample > 0:
        notebooks = notebooks[:sample]
        print(f"\n[SAMPLE MODE] Converting first {len(notebooks)} notebooks")
    
    print(f"\nFolder structure discovered:")
    for folder_path, items in organization['folder_structure'].items():
        folder_display = folder_path if folder_path else "(root)"
        print(f"  {folder_display}: {len(items)} notebook(s)")
    
    # Analyze what we have
    total_v5 = sum(len(nb['v5_files']) for nb in notebooks)
    total_v6 = sum(len(nb['v6_files']) for nb in notebooks)
    total_v4 = sum(len(nb.get('v4_files', [])) for nb in notebooks)
    total_v3 = sum(len(nb.get('v3_files', [])) for nb in notebooks)
    total_pdfs = sum(len(nb['pdf_files']) for nb in notebooks)
    
    print(f"\nFound {len(notebooks)} notebooks:")
    print(f"- v6 files to convert: {total_v6}")
    print(f"- v5 files to convert: {total_v5}")
    print(f"- v4 files detected (unsupported): {total_v4}")
    print(f"- v3 files detected (unsupported): {total_v3}")
    print(f"- Existing PDFs to copy: {total_pdfs}")
    
    # Convert notebooks
    total_v5_converted = 0
    total_v6_converted = 0
    total_v4_converted = 0
    total_copied = 0
    successful_notebooks = 0
    
    print(f"\nConverting notebooks...")
    with tqdm(notebooks, desc="Converting") as pbar:
        for notebook in pbar:
            pbar.set_postfix_str(notebook['name'][:30])
            
            results = convert_notebook(notebook, output_dir, backup_dir)
            
            if results['output_files']:
                successful_notebooks += 1
                total_v5_converted += results['v5_converted']
                total_v6_converted += results['v6_converted']
                total_v4_converted += results['v4_converted']
                total_copied += results['pdfs_copied']
                
                folder_info = f" -> {results['folder_path']}" if results['folder_path'] else ""
                logging.info(f"✓ {notebook['name']}: {len(results['output_files'])} files created{folder_info}")
            else:
                logging.warning(f"✗ {notebook['name']}: No files converted")
    
    # Summary
    print(f"\n[SUMMARY] Conversion Results:")
    print(f"Successful notebooks: {successful_notebooks}/{len(notebooks)}")
    print(f"v6 files converted: {total_v6_converted}")
    print(f"v5 files converted: {total_v5_converted}")
    print(f"v4 files converted (best-effort): {total_v4_converted}")
    print(f"Existing PDFs copied: {total_copied}")
    print(f"Total output files: {total_v6_converted + total_v5_converted + total_v4_converted + total_copied}")
    if total_v4 or total_v3:
        print(f"Unsupported pages noted (v4: {total_v4}, v3: {total_v3}) -> see *_unsupported.txt markers")
    
    if successful_notebooks > 0:
        print(f"\nPDF files saved to: {output_dir}")
        
        # Show sample files with folder structure
        pdf_files = list(output_dir.rglob("*.pdf"))  # Search recursively
        if pdf_files:
            print(f"\nSample converted files:")
            for pdf in pdf_files[:5]:
                size_mb = pdf.stat().st_size / (1024 * 1024)
                relative_path = pdf.relative_to(output_dir)
                print(f"  - {relative_path} ({size_mb:.1f} MB)")
            if len(pdf_files) > 5:
                print(f"  ... and {len(pdf_files)-5} more")
    
    print(f"\n[SUCCESS] Hybrid conversion completed!")

if __name__ == "__main__":
    main()