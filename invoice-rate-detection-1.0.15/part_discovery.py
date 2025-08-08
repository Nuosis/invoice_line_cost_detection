"""
Simple Part Discovery Service - JSON-based approach.

This service discovers unknown parts from PDF extraction JSON and provides
interactive prompts to add them to the database.
"""

import json
import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional

from database.database import DatabaseManager
from database.models import Part


logger = logging.getLogger(__name__)


class SimplePartDiscoveryService:
    """
    Simple part discovery service that works directly with PDF extraction JSON.
    
    Input: PDF extraction JSON (same format as validation engine)
    Output: Same JSON with discovered parts added to database
    """
    
    def __init__(self, db_manager: DatabaseManager, interactive_mode: bool = True):
        """
        Initialize the discovery service.
        
        Args:
            db_manager: Database manager for part operations
            interactive_mode: Whether to prompt user for unknown parts
        """
        self.db_manager = db_manager
        self.interactive_mode = interactive_mode
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def discover_and_add_parts(self, extraction_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover unknown parts from extraction JSON and add them to database.
        
        Args:
            extraction_json: PDF extraction JSON with parts array
            
        Returns:
            Original input JSON (unchanged)
        """
        # Find unknown parts
        unknown_parts = self._find_unknown_parts(extraction_json)
        
        if not unknown_parts:
            self.logger.info("No unknown parts found")
            return extraction_json
        
        self.logger.info(f"Found {len(unknown_parts)} unknown parts")
        
        # Process unknown parts (adds them to database)
        if self.interactive_mode:
            self._process_unknown_parts_interactive(unknown_parts)
        else:
            self._process_unknown_parts_batch(unknown_parts)
        
        # Return original input unchanged
        return extraction_json
    
    def _find_unknown_parts(self, extraction_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find parts that don't exist in the database."""
        unknown_parts = []
        parts = extraction_json.get('parts', [])
        
        for part_data in parts:
            part_number = part_data.get('database_fields', {}).get('part_number')
            if not part_number:
                continue
            
            # Check if part exists in database
            try:
                existing_part = self.db_manager.get_part(part_number)
                # Part exists, skip it completely (don't update rates)
                self.logger.debug(f"Part {part_number} already exists in database, skipping")
                continue
            except Exception:
                # Part doesn't exist, add to unknown list
                unknown_parts.append(part_data)
        
        return unknown_parts
    
    def _process_unknown_parts_interactive(self, unknown_parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process unknown parts with user interaction and verification."""
        results = []
        
        print(f"\n🔍 Found {len(unknown_parts)} unknown parts")
        print("=" * 50)
        
        for i, part_data in enumerate(unknown_parts, 1):
            db_fields = part_data.get('database_fields', {})
            line_fields = part_data.get('lineitem_fields', {})
            
            part_number = db_fields.get('part_number', 'UNKNOWN')
            description = db_fields.get('description', 'No description')
            discovered_price = db_fields.get('authorized_price', 0.0)
            
            print(f"\nPart {i}/{len(unknown_parts)}: {part_number}")
            print(f"Description: {description}")
            print(f"Discovered Price: ${discovered_price}")
            print(f"Line: {line_fields.get('raw_text', 'N/A')}")
            
            while True:
                choice = input("\n[A]dd to database, [S]kip this part, [Q]uit discovery: ").strip().upper()
                
                if choice == 'A':
                    # Verify part number
                    verified_part_number = input(f"Confirm part number [{part_number}]: ").strip()
                    if not verified_part_number:
                        verified_part_number = part_number
                    
                    # Verify price
                    while True:
                        price_input = input(f"Confirm authorized price [${discovered_price}]: ").strip()
                        if not price_input:
                            verified_price = Decimal(str(discovered_price))
                            break
                        else:
                            try:
                                # Remove $ if present
                                price_input = price_input.replace('$', '').strip()
                                verified_price = Decimal(price_input)
                                if verified_price < 0:
                                    print("❌ Price cannot be negative. Please try again.")
                                    continue
                                break
                            except Exception:
                                print("❌ Invalid price format. Please enter a valid number (e.g., 15.50)")
                                continue
                    
                    # Add part to database
                    try:
                        part = Part(
                            part_number=verified_part_number,
                            authorized_price=verified_price,
                            description=description,
                            item_type=db_fields.get('item_type'),
                            category=db_fields.get('category'),
                            source='discovered',
                            first_seen_invoice=db_fields.get('first_seen_invoice'),
                            notes=db_fields.get('notes')
                        )
                        
                        self.db_manager.create_part(part)
                        print(f"✅ Added {verified_part_number} to database with price ${verified_price}")
                        
                        results.append({
                            'part_number': verified_part_number,
                            'action': 'added',
                            'verified_price': float(verified_price),
                            'original_price': float(discovered_price)
                        })
                        break
                        
                    except Exception as e:
                        print(f"❌ Failed to add {verified_part_number}: {e}")
                        results.append({
                            'part_number': verified_part_number,
                            'action': 'failed',
                            'error': str(e)
                        })
                        break
                
                elif choice == 'S':
                    print(f"⏭️  Skipped {part_number}")
                    results.append({
                        'part_number': part_number,
                        'action': 'skipped'
                    })
                    break
                
                elif choice == 'Q':
                    print("🛑 Discovery cancelled by user")
                    results.append({
                        'part_number': part_number,
                        'action': 'cancelled'
                    })
                    return results
                
                else:
                    print("Invalid choice. Please enter A, S, or Q.")
        
        return results
    
    def _process_unknown_parts_batch(self, unknown_parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process unknown parts in batch mode (automatically add to database)."""
        results = []
        
        self.logger.info(f"Batch mode: automatically adding {len(unknown_parts)} unknown parts to database")
        
        for part_data in unknown_parts:
            db_fields = part_data.get('database_fields', {})
            part_number = db_fields.get('part_number', 'UNKNOWN')
            description = db_fields.get('description', 'Auto-discovered from invoice')
            authorized_price = db_fields.get('authorized_price', 0.0)
            
            try:
                # Create part with discovered data
                part = Part(
                    part_number=part_number,
                    authorized_price=Decimal(str(authorized_price)) if authorized_price else Decimal('0.0'),
                    description=description,
                    item_type=db_fields.get('item_type'),
                    category=db_fields.get('category'),
                    source='discovered',
                    first_seen_invoice=db_fields.get('first_seen_invoice'),
                    notes=f"Auto-discovered in batch mode from invoice {db_fields.get('first_seen_invoice', 'unknown')}"
                )
                
                self.db_manager.create_part(part)
                self.logger.info(f"Added {part_number} to database with price ${authorized_price}")
                
                results.append({
                    'part_number': part_number,
                    'action': 'added',
                    'price': float(authorized_price),
                    'reason': 'batch_mode_auto_add'
                })
                
            except Exception as e:
                self.logger.error(f"Failed to add {part_number} to database: {e}")
                results.append({
                    'part_number': part_number,
                    'action': 'failed',
                    'error': str(e),
                    'reason': 'batch_mode_error'
                })
        
        return results


def discover_parts_from_json(extraction_json: Dict[str, Any], 
                           db_manager: DatabaseManager,
                           interactive: bool = True) -> Dict[str, Any]:
    """
    Convenience function to discover parts from extraction JSON.
    
    Args:
        extraction_json: PDF extraction JSON
        db_manager: Database manager
        interactive: Whether to use interactive mode
        
    Returns:
        JSON with discovery results
    """
    service = SimplePartDiscoveryService(db_manager, interactive)
    return service.discover_and_add_parts(extraction_json)