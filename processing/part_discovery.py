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
        seen_composite_keys = set()  # Track parts we've already processed
        parts = extraction_json.get('parts', [])
        
        for part_data in parts:
            db_fields = part_data.get('database_fields', {})
            part_number = db_fields.get('part_number')
            if not part_number:
                continue
            
            # Get all components for composite key check (excluding price)
            item_type = db_fields.get('item_type')
            description = db_fields.get('description')
            
            # Generate composite key for this part (item_type|description|part_number)
            from database.models import Part
            composite_key = Part.generate_identifier_from_components(item_type, description, part_number)
            
            # Skip if we've already processed this exact composite key in this session
            if composite_key in seen_composite_keys:
                self.logger.debug(f"Duplicate part {part_number} (composite: {composite_key}) already processed in this session, skipping")
                continue
            
            # Check if part exists in database using composite key components
            try:
                existing_part = self.db_manager.find_part_by_components(item_type, description, part_number)
                if existing_part:
                    # Part exists in database, skip it completely
                    self.logger.debug(f"Part {part_number} (composite: {existing_part.composite_key}) already exists in database, skipping")
                    seen_composite_keys.add(composite_key)  # Mark as seen to avoid duplicates
                    continue
                else:
                    # Part doesn't exist in database, add to unknown list
                    self.logger.debug(f"Part {part_number} (composite: {composite_key}) is unknown, adding to discovery list")
                    unknown_parts.append(part_data)
                    seen_composite_keys.add(composite_key)  # Mark as seen to avoid duplicates
            except Exception as e:
                # If there's an error checking, assume part doesn't exist and add to unknown list
                self.logger.debug(f"Error checking part {part_number}: {e}, treating as unknown")
                if composite_key not in seen_composite_keys:
                    unknown_parts.append(part_data)
                    seen_composite_keys.add(composite_key)
        
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
                choice = input("\n[A]dd to database, [P]art details, [C]hange rate, [S]kip this part, [Q]uit discovery: ").strip().upper()
                
                if choice == 'A':
                    # Add part directly to database without confirmation
                    try:
                        part = Part(
                            part_number=part_number,
                            authorized_price=Decimal(str(discovered_price)),
                            description=description,
                            item_type=db_fields.get('item_type'),
                            category=db_fields.get('category'),
                            source='discovered',
                            first_seen_invoice=db_fields.get('first_seen_invoice'),
                            notes=db_fields.get('notes')
                        )
                        
                        self.db_manager.create_part(part)
                        print(f"✅ Added {part_number} to database with price ${discovered_price}")
                        
                        results.append({
                            'part_number': part_number,
                            'action': 'added',
                            'verified_price': float(discovered_price),
                            'original_price': float(discovered_price)
                        })
                        break
                        
                    except Exception as e:
                        print(f"❌ Failed to add {part_number}: {e}")
                        results.append({
                            'part_number': part_number,
                            'action': 'failed',
                            'error': str(e)
                        })
                        break
                
                elif choice == 'P':
                    # Adjust part details (number, price, etc.)
                    print("Adjust part details:")
                    
                    # Verify part number
                    verified_part_number = input(f"Part number [{part_number}]: ").strip()
                    if not verified_part_number:
                        verified_part_number = part_number
                    
                    # Verify price
                    while True:
                        price_input = input(f"Authorized price [${discovered_price}]: ").strip()
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
                    
                    # Update the current part data
                    part_number = verified_part_number
                    discovered_price = float(verified_price)
                    print(f"✅ Part details updated: {part_number} @ ${discovered_price}")
                    
                    # Continue the loop to show updated options
                    continue
                
                elif choice == 'C':
                    # Change rate option
                    print(f"Current discovered price: ${discovered_price}")
                    while True:
                        new_price_input = input("Enter new authorized price: $").strip()
                        try:
                            # Remove $ if present
                            new_price_input = new_price_input.replace('$', '').strip()
                            new_price = Decimal(new_price_input)
                            if new_price < 0:
                                print("❌ Price cannot be negative. Please try again.")
                                continue
                            
                            # Update the discovered price for this part
                            discovered_price = float(new_price)
                            print(f"✅ Price updated to ${new_price}")
                            break
                            
                        except Exception:
                            print("❌ Invalid price format. Please enter a valid number (e.g., 15.50)")
                            continue
                    
                    # Continue the loop to show updated options
                    continue
                
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
                    print("Invalid choice. Please enter A, P, C, S, or Q.")
        
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