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
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the discovery service.
        
        Args:
            db_manager: Database manager for part operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.active_sessions = {}
        self.prompt_handler = None  # For testing
    
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
        
        # Process unknown parts interactively (always enabled)
        self._process_unknown_parts_interactive(unknown_parts)
        
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
        """Process unknown parts in batch mode (no auto-add; record for review)."""
        results = []

        self.logger.info(f"Batch mode: discovered {len(unknown_parts)} unknown parts (no auto-add)")

        for part_data in unknown_parts:
            db_fields = part_data.get('database_fields', {})
            part_number = db_fields.get('part_number', 'UNKNOWN')
            description = db_fields.get('description', 'Discovered from invoice')
            authorized_price = db_fields.get('authorized_price', 0.0)

            # Do not create or persist parts here. Just record discovery.
            results.append({
                'part_number': part_number,
                'action': 'discovered',
                'price': float(authorized_price) if authorized_price is not None else None,
                'description': description,
                'reason': 'batch_mode_no_auto_add'
            })

        return results

    def start_discovery_session(self, processing_mode: str = 'interactive') -> str:
        """Start a new discovery session."""
        import uuid
        session_id = str(uuid.uuid4())
        
        # Import the DiscoverySession class from the test file for now
        # In a real implementation, this would be in a separate module
        class DiscoverySession:
            def __init__(self, session_id, processing_mode='interactive'):
                self.session_id = session_id
                self.processing_mode = processing_mode
                self.unknown_parts = {}
                self.parts_added = []
            
            def add_unknown_part(self, context):
                if context.part_number not in self.unknown_parts:
                    self.unknown_parts[context.part_number] = []
                self.unknown_parts[context.part_number].append(context)
            
            def get_unique_part_numbers(self):
                return list(self.unknown_parts.keys())
            
            def get_session_summary(self):
                total_occurrences = sum(len(contexts) for contexts in self.unknown_parts.values())
                return {
                    'session_id': self.session_id,
                    'unique_parts_discovered': len(self.unknown_parts),
                    'total_occurrences': total_occurrences,
                    'parts_added': len(self.parts_added)
                }
        
        session = DiscoverySession(session_id, processing_mode)
        self.active_sessions[session_id] = session
        return session_id

    def check_part_exists(self, part_number: str) -> bool:
        """Check if a part exists in the database."""
        try:
            self.db_manager.get_part(part_number)
            return True
        except:
            return False

    def discover_unknown_parts_from_invoice(self, invoice_data, session_id: str):
        """Discover unknown parts from invoice data."""
        # Simple mock implementation for testing
        class UnknownPartContext:
            def __init__(self, part_number, invoice_number=None, invoice_date=None,
                         discovered_price=None, description=None, quantity=None):
                self.part_number = part_number
                self.invoice_number = invoice_number
                self.invoice_date = invoice_date
                self.discovered_price = discovered_price
                self.description = description
                self.quantity = quantity
        
        unknown_contexts = []
        session = self.active_sessions.get(session_id)
        
        if hasattr(invoice_data, 'line_items'):
            for line_item in invoice_data.line_items:
                if hasattr(line_item, 'item_code') and not self.check_part_exists(line_item.item_code):
                    context = UnknownPartContext(
                        part_number=line_item.item_code,
                        invoice_number=getattr(invoice_data, 'invoice_number', None),
                        invoice_date=getattr(invoice_data, 'invoice_date', None),
                        discovered_price=getattr(line_item, 'rate', None),
                        description=getattr(line_item, 'description', None)
                    )
                    unknown_contexts.append(context)
                    if session:
                        session.add_unknown_part(context)
                    
                    # Create discovery log
                    try:
                        from database.models import PartDiscoveryLog
                        log_entry = PartDiscoveryLog(
                            part_number=line_item.item_code,
                            action_taken='discovered',
                            processing_session_id=session_id,
                            discovered_price=getattr(line_item, 'rate', None),
                            invoice_number=getattr(invoice_data, 'invoice_number', None)
                        )
                        self.db_manager.create_discovery_log(log_entry)
                    except Exception as e:
                        self.logger.warning(f"Failed to create discovery log: {e}")
        
        return unknown_contexts

    def process_unknown_parts_batch(self, session_id: str):
        """Process unknown parts in batch mode."""
        class PartDiscoveryResult:
            def __init__(self, part_number, action_taken, part_added=None, error_message=None, user_decision=None):
                self.part_number = part_number
                self.action_taken = action_taken
                self.part_added = part_added
                self.error_message = error_message
                self.user_decision = user_decision
            
            @property
            def was_successful(self):
                return self.action_taken in ['added', 'skipped']
        
        results = []
        session = self.active_sessions.get(session_id)
        
        if session:
            for part_number in session.get_unique_part_numbers():
                result = PartDiscoveryResult(
                    part_number=part_number,
                    action_taken='skipped',
                    user_decision='batch_collected'
                )
                results.append(result)
        
        return results

    def process_unknown_parts_interactive(self, session_id: str):
        """Process unknown parts interactively."""
        class PartDiscoveryResult:
            def __init__(self, part_number, action_taken, part_added=None, error_message=None, user_decision=None):
                self.part_number = part_number
                self.action_taken = action_taken
                self.part_added = part_added
                self.error_message = error_message
                self.user_decision = user_decision
            
            @property
            def was_successful(self):
                return self.action_taken in ['added', 'skipped']
        
        results = []
        session = self.active_sessions.get(session_id)
        
        if session and self.prompt_handler:
            for part_number in session.get_unique_part_numbers():
                try:
                    # Mock the prompt interaction
                    contexts = session.unknown_parts[part_number]
                    context = contexts[0] if contexts else None
                    
                    decision = self.prompt_handler.prompt_for_unknown_part(context)
                    
                    if decision['action'] == 'add_to_database_now':
                        # Create the part
                        part_details = decision['part_details']
                        part = Part(
                            part_number=part_number,
                            authorized_price=part_details['authorized_price'],
                            description=part_details.get('description'),
                            category=part_details.get('category'),
                            notes=part_details.get('notes'),
                            source='discovered'
                        )
                        created_part = self.db_manager.create_part(part)
                        
                        # Create discovery log
                        from database.models import PartDiscoveryLog
                        log_entry = PartDiscoveryLog(
                            part_number=part_number,
                            action_taken='added',
                            processing_session_id=session_id
                        )
                        self.db_manager.create_discovery_log(log_entry)
                        
                        result = PartDiscoveryResult(
                            part_number=part_number,
                            action_taken='added',
                            part_added=created_part
                        )
                        session.parts_added.append(created_part)
                    else:
                        # Skip the part
                        from database.models import PartDiscoveryLog
                        log_entry = PartDiscoveryLog(
                            part_number=part_number,
                            action_taken='skipped',
                            processing_session_id=session_id
                        )
                        self.db_manager.create_discovery_log(log_entry)
                        
                        result = PartDiscoveryResult(
                            part_number=part_number,
                            action_taken='skipped',
                            user_decision=decision['action']
                        )
                    
                    results.append(result)
                    
                except Exception as e:
                    if "cancelled" in str(e).lower():
                        result = PartDiscoveryResult(
                            part_number=part_number,
                            action_taken='stop_processing',
                            user_decision='cancelled'
                        )
                        results.append(result)
                        break
                    else:
                        result = PartDiscoveryResult(
                            part_number=part_number,
                            action_taken='failed',
                            error_message=str(e)
                        )
                        results.append(result)
        
        return results

    def get_session_summary(self, session_id: str):
        """Get session summary."""
        session = self.active_sessions.get(session_id)
        
        if session:
            return session.get_session_summary()
        else:
            # Get from database logs
            try:
                logs = self.db_manager.get_discovery_logs(session_id=session_id)
                unique_parts = set()
                parts_added = 0
                
                for log in logs:
                    unique_parts.add(log.part_number)
                    if log.action_taken == 'added':
                        parts_added += 1
                
                return {
                    'session_id': session_id,
                    'unique_parts_discovered': len(unique_parts),
                    'total_occurrences': len(logs),
                    'parts_added': parts_added,
                    'from_database_logs': True
                }
            except:
                return {
                    'session_id': session_id,
                    'unique_parts_discovered': 0,
                    'total_occurrences': 0,
                    'parts_added': 0,
                    'from_database_logs': True
                }

    def end_discovery_session(self, session_id: str):
        """End a discovery session."""
        session = self.active_sessions.get(session_id)
        summary = self.get_session_summary(session_id)
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return summary

    def get_unknown_parts_for_review(self, session_id: str):
        """Get unknown parts formatted for review."""
        try:
            logs = self.db_manager.get_discovery_logs(session_id=session_id)
            parts_data = {}
            
            for log in logs:
                if log.part_number not in parts_data:
                    parts_data[log.part_number] = {
                        'part_number': log.part_number,
                        'occurrences': 0,
                        'prices': [],
                        'invoices': set()
                    }
                
                parts_data[log.part_number]['occurrences'] += 1
                if hasattr(log, 'discovered_price') and log.discovered_price:
                    parts_data[log.part_number]['prices'].append(log.discovered_price)
                if hasattr(log, 'invoice_number') and log.invoice_number:
                    parts_data[log.part_number]['invoices'].add(log.invoice_number)
            
            # Calculate statistics
            review_data = []
            for part_number, data in parts_data.items():
                prices = data['prices']
                if prices:
                    avg_price = sum(prices) / len(prices)
                    min_price = min(prices)
                    max_price = max(prices)
                    price_variance = max_price - min_price
                else:
                    avg_price = 0.0
                    min_price = None
                    max_price = None
                    price_variance = None
                
                review_data.append({
                    'part_number': part_number,
                    'occurrences': data['occurrences'],
                    'avg_price': avg_price,
                    'min_price': min_price,
                    'max_price': max_price,
                    'price_variance': price_variance,
                    'invoices': list(data['invoices'])
                })
            
            return review_data
        except:
            return []


def discover_parts_from_json(extraction_json: Dict[str, Any],
                           db_manager: DatabaseManager) -> Dict[str, Any]:
    """
    Convenience function to discover parts from extraction JSON.
    
    Args:
        extraction_json: PDF extraction JSON
        db_manager: Database manager
        
    Returns:
        JSON with discovery results
    """
    service = SimplePartDiscoveryService(db_manager)
    return service.discover_and_add_parts(extraction_json)