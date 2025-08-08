#!/usr/bin/env python3
"""
Database parts review script for invoice PDFs.

- Extracts text, lines, and parts from an invoice PDF.
- Simulates CLI-based add/update/pass logic for parts management.
- At the end, exports the current parts database to test_validation/expectations/.

Intended for use in validation and regression testing of the parts database workflow.
"""

import argparse
import logging
import sys
from pathlib import Path
import shutil
import csv
import json
from decimal import Decimal

from processing.pdf_processor import extract_text_from_pdf, extract_lines_from_pdf, extract_parts_from_pdf
from database.database import DatabaseManager
from database.models import Part, ValidationError, DatabaseError

def create_logger() -> logging.Logger:
    """Create a simple logger."""
    logger = logging.getLogger('database_parts_review')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def main():
    parser = argparse.ArgumentParser(description="Database parts review for invoice PDF")
    parser.add_argument("--invoicePath", required=True, help="Path to PDF invoice")
    parser.add_argument("--dbPath", help="Path to SQLite database (optional)")
    parser.add_argument("--outputDir", help="Directory to store expectations (default: ./test_validation/expectations/)")
    parser.add_argument("--exportFormat", default="csv", choices=["csv", "json"], help="Export format for parts database")
    args = parser.parse_args()

    logger = create_logger()

    # Validate input
    pdf_path = Path(args.invoicePath)
    if not pdf_path.exists():
        logger.error(f"File not found: {pdf_path}")
        return 1
    if not pdf_path.suffix.lower() == '.pdf':
        logger.error(f"Not a PDF: {pdf_path}")
        return 1

    # Set up database path
    if args.dbPath:
        db_path = Path(args.dbPath)
    else:
        # Use a temp DB in the test_validation directory for isolation
        db_path = Path("test_validation") / f"test_parts_review_{pdf_path.stem}.db"
        if db_path.exists():
            db_path.unlink()

    # Set up output directory
    if args.outputDir:
        output_dir = Path(args.outputDir)
    else:
        output_dir = Path(__file__).parent / "expectations"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract text (for logging/validation)
    extracted_text_path = output_dir / f"{pdf_path.stem}_extracted_text.txt"
    try:
        text = extract_text_from_pdf(str(pdf_path))
        with open(extracted_text_path, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"Extracted text saved to: {extracted_text_path}")
    except Exception as e:
        logger.error(f"Failed to extract text: {e}")
        return 1

    # 2. Extract lines (for validation)
    extracted_lines_path = output_dir / f"{pdf_path.stem}_lines.csv"
    try:
        lines = extract_lines_from_pdf(str(pdf_path))
        if lines:
            with open(extracted_lines_path, "w", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=lines[0].keys())
                writer.writeheader()
                writer.writerows(lines)
            logger.info(f"Extracted lines saved to: {extracted_lines_path}")
    except Exception as e:
        logger.error(f"Failed to extract lines: {e}")
        return 1

    # 3. Extract parts (simulate discovery)
    extracted_parts_path = output_dir / f"{pdf_path.stem}_parts.csv"
    try:
        parts = extract_parts_from_pdf(str(pdf_path))
        if parts:
            with open(extracted_parts_path, "w", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=parts[0].keys())
                writer.writeheader()
                writer.writerows(parts)
            logger.info(f"Extracted parts saved to: {extracted_parts_path}")
    except Exception as e:
        logger.error(f"Failed to extract parts: {e}")
        return 1

    # 4. Simulate add/update/pass logic for each part in extracted_parts_path
    db = DatabaseManager(str(db_path))
    for row in parts:
        part_number = row.get("part_number")
        authorized_price = row.get("authorized_price")
        description = row.get("description")
        item_type = row.get("item_type")
        first_seen_invoice = row.get("first_seen_invoice")
        
        # Skip rows without sufficient identification data
        if not any([part_number, description, item_type]):
            logger.warning(f"Skipping row with insufficient identification data: {row}")
            continue
            
        try:
            part = Part(
                part_number=part_number,
                authorized_price=Decimal(str(authorized_price)) if authorized_price else Decimal("0.0"),
                description=description,
                item_type=item_type,
                first_seen_invoice=first_seen_invoice,
                source="discovered"
            )
            db.create_part(part)
            logger.info(f"Added part: {part.composite_key} (part_number: {part_number})")
        except (DatabaseError, ValidationError) as e:
            if "already exists" in str(e):
                try:
                    # Try to find existing part by components
                    existing = db.find_part_by_components(item_type, description, part_number)
                    
                    if existing:
                        update_kwargs = {
                            "authorized_price": Decimal(str(authorized_price)) if authorized_price else Decimal("0.0"),
                            "description": description,
                            "first_seen_invoice": first_seen_invoice
                        }
                        
                        # Always include item_type in update_kwargs to prevent it from being set to null
                        if item_type:
                            # Use the item_type from the extracted part
                            update_kwargs["item_type"] = item_type
                        else:
                            # Preserve existing item_type if no new one provided
                            update_kwargs["item_type"] = existing.item_type
                        
                        db.update_part(
                            existing.composite_key,
                            **update_kwargs
                        )
                        logger.info(f"Updated part: {existing.composite_key}")
                    else:
                        logger.warning(f"Could not find existing part for update: {part.composite_key}")
                except Exception as ue:
                    logger.error(f"Failed to update part {part.composite_key}: {ue}")
            else:
                logger.error(f"Failed to add part {part.composite_key}: {e}")

    # 5. Export current parts database to expectations
    export_file = output_dir / f"{pdf_path.stem}_parts_db.{args.exportFormat}"
    try:
        all_parts = db.list_parts()
        if args.exportFormat == "csv":
            with open(export_file, "w", newline='', encoding="utf-8") as f:
                fieldnames = [
                    "composite_key", "part_number", "authorized_price", "description",
                    "item_type", "category", "source", "first_seen_invoice",
                    "created_date", "last_updated", "is_active", "notes"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for part in all_parts:
                    writer.writerow(part.to_dict())
        elif args.exportFormat == "json":
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump([part.to_dict() for part in all_parts], f, indent=2, default=str)
        logger.info(f"Exported current parts database to: {export_file}")
    except Exception as e:
        logger.error(f"Failed to export parts database: {e}")
        return 1

    print(f"Database parts review complete. Output: {export_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())