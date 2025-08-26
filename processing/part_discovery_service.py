"""
Part Discovery Service - Advanced part discovery and management.

This module provides the PartDiscoveryService class that handles advanced
part discovery workflows, session management, and batch processing.

This is an enhanced version of the SimplePartDiscoveryService with additional
features for complex discovery scenarios and better integration with the
validation engine.

Key Features:
- Session-based discovery management
- Batch and interactive discovery modes
- Integration with validation engine
- Advanced discovery statistics and reporting
- Persistent discovery logging

Usage Examples:

    # Basic discovery service
    from processing.part_discovery_service import PartDiscoveryService
    from database.database import DatabaseManager
    
    db_manager = DatabaseManager("invoices.db")
    service = PartDiscoveryService(db_manager)
    
    # Start discovery session
    session_id = service.start_discovery_session('interactive')
    
    # Process unknown parts
    results = service.process_unknown_parts_interactive(session_id)
    
    # Get session summary
    summary = service.get_session_summary(session_id)
    service.end_discovery_session(session_id)
"""

import logging
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

from database.database import DatabaseManager
from database.models import Part, PartDiscoveryLog
from .part_discovery import SimplePartDiscoveryService


logger = logging.getLogger(__name__)


@dataclass
class PartDiscoveryResult:
    """Result of processing a discovered part."""
    part_number: str
    action_taken: str  # 'added', 'skipped', 'failed', 'cancelled'
    part_added: Optional[Part] = None
    error_message: Optional[str] = None
    user_decision: Optional[str] = None
    
    @property
    def was_successful(self) -> bool:
        """Check if the discovery action was successful."""
        return self.action_taken in ['added', 'skipped']


@dataclass
class UnknownPartContext:
    """Context information for an unknown part."""
    part_number: str
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    discovered_price: Optional[Decimal] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    line_number: Optional[int] = None


class DiscoverySession:
    """Manages a part discovery session."""
    
    def __init__(self, session_id: str, processing_mode: str = 'interactive'):
        self.session_id = session_id
        self.processing_mode = processing_mode
        self.unknown_parts: Dict[str, List[UnknownPartContext]] = {}
        self.parts_added: List[Part] = []
        self.created_at = datetime.now()
    
    def add_unknown_part(self, context: UnknownPartContext):
        """Add an unknown part context to the session."""
        if context.part_number not in self.unknown_parts:
            self.unknown_parts[context.part_number] = []
        self.unknown_parts[context.part_number].append(context)
    
    def get_unique_part_numbers(self) -> List[str]:
        """Get list of unique part numbers discovered in this session."""
        return list(self.unknown_parts.keys())
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary statistics for this session."""
        total_occurrences = sum(len(contexts) for contexts in self.unknown_parts.values())
        return {
            'session_id': self.session_id,
            'processing_mode': self.processing_mode,
            'unique_parts_discovered': len(self.unknown_parts),
            'total_occurrences': total_occurrences,
            'parts_added': len(self.parts_added),
            'created_at': self.created_at.isoformat()
        }


class PartDiscoveryService:
    """
    Advanced part discovery service with session management.
    
    This service extends the SimplePartDiscoveryService with additional
    features for complex discovery workflows and better integration
    with the validation engine.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the part discovery service.
        
        Args:
            db_manager: Database manager for parts operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Session management
        self.active_sessions: Dict[str, DiscoverySession] = {}
        
        # Integration with simple discovery service
        self.simple_service = SimplePartDiscoveryService(db_manager)
        
        # Mock prompt handler for testing
        self.prompt_handler = None
    
    def start_discovery_session(self, processing_mode: str = 'interactive') -> str:
        """
        Start a new discovery session.
        
        Args:
            processing_mode: Processing mode ('interactive' or 'batch')
            
        Returns:
            Session ID for the new session
        """
        session_id = str(uuid.uuid4())
        session = DiscoverySession(session_id, processing_mode)
        self.active_sessions[session_id] = session
        
        self.logger.info(f"Started discovery session {session_id} in {processing_mode} mode")
        return session_id
    
    def discover_unknown_parts_from_invoice(self, invoice_data: Any, session_id: str) -> List[UnknownPartContext]:
        """
        Discover unknown parts from invoice data and add to session.
        
        Args:
            invoice_data: Invoice data object with line_items
            session_id: Active discovery session ID
            
        Returns:
            List of unknown part contexts discovered
        """
        unknown_contexts = []
        session = self.active_sessions.get(session_id)
        
        if not session:
            self.logger.warning(f"Session {session_id} not found")
            return unknown_contexts
        
        # Process line items if available
        if hasattr(invoice_data, 'line_items'):
            for line_item in invoice_data.line_items:
                if hasattr(line_item, 'item_code') and not self.check_part_exists(line_item.item_code):
                    context = UnknownPartContext(
                        part_number=line_item.item_code,
                        invoice_number=getattr(invoice_data, 'invoice_number', None),
                        invoice_date=getattr(invoice_data, 'invoice_date', None),
                        discovered_price=getattr(line_item, 'rate', None),
                        description=getattr(line_item, 'description', None),
                        quantity=getattr(line_item, 'quantity', None),
                        line_number=getattr(line_item, 'line_number', None)
                    )
                    unknown_contexts.append(context)
                    session.add_unknown_part(context)
                    
                    # Create discovery log
                    self._create_discovery_log(context, session_id, 'discovered')
        
        self.logger.info(f"Discovered {len(unknown_contexts)} unknown parts in session {session_id}")
        return unknown_contexts
    
    def process_unknown_parts_interactive(self, session_id: str) -> List[PartDiscoveryResult]:
        """
        Process unknown parts interactively with user prompts.
        
        Args:
            session_id: Active discovery session ID
            
        Returns:
            List of discovery results
        """
        results = []
        session = self.active_sessions.get(session_id)
        
        if not session:
            self.logger.warning(f"Session {session_id} not found")
            return results
        
        self.logger.info(f"Processing {len(session.unknown_parts)} unique parts interactively")
        
        for part_number in session.get_unique_part_numbers():
            try:
                contexts = session.unknown_parts[part_number]
                context = contexts[0] if contexts else None
                
                if self.prompt_handler:
                    # Use mock prompt handler for testing
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
                        session.parts_added.append(created_part)
                        
                        # Create discovery log
                        self._create_discovery_log(context, session_id, 'added')
                        
                        result = PartDiscoveryResult(
                            part_number=part_number,
                            action_taken='added',
                            part_added=created_part
                        )
                    else:
                        # Skip the part
                        self._create_discovery_log(context, session_id, 'skipped')
                        
                        result = PartDiscoveryResult(
                            part_number=part_number,
                            action_taken='skipped',
                            user_decision=decision['action']
                        )
                else:
                    # Fallback to simple interactive processing
                    result = PartDiscoveryResult(
                        part_number=part_number,
                        action_taken='skipped',
                        user_decision='no_prompt_handler'
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
    
    def process_unknown_parts_batch(self, session_id: str) -> List[PartDiscoveryResult]:
        """
        Process unknown parts in batch mode (collect for later review).
        
        Args:
            session_id: Active discovery session ID
            
        Returns:
            List of discovery results
        """
        results = []
        session = self.active_sessions.get(session_id)
        
        if not session:
            self.logger.warning(f"Session {session_id} not found")
            return results
        
        self.logger.info(f"Processing {len(session.unknown_parts)} unique parts in batch mode")
        
        for part_number in session.get_unique_part_numbers():
            contexts = session.unknown_parts[part_number]
            context = contexts[0] if contexts else None
            
            # In batch mode, just collect the parts for later review
            self._create_discovery_log(context, session_id, 'collected')
            
            result = PartDiscoveryResult(
                part_number=part_number,
                action_taken='skipped',
                user_decision='batch_collected'
            )
            results.append(result)
        
        return results
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary for a discovery session.
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            Session summary dictionary
        """
        session = self.active_sessions.get(session_id)
        
        if session:
            return session.get_session_summary()
        else:
            # Try to get from database logs
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
            except Exception as e:
                self.logger.warning(f"Failed to get session summary from database: {e}")
                return {
                    'session_id': session_id,
                    'unique_parts_discovered': 0,
                    'total_occurrences': 0,
                    'parts_added': 0,
                    'from_database_logs': True
                }
    
    def end_discovery_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a discovery session and return summary.
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            Final session summary
        """
        summary = self.get_session_summary(session_id)
        
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            self.logger.info(f"Ended discovery session {session_id}")
        
        return summary
    
    def get_unknown_parts_for_review(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get unknown parts formatted for review.
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            List of parts data for review
        """
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
                    parts_data[log.part_number]['prices'].append(float(log.discovered_price))
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
        except Exception as e:
            self.logger.warning(f"Failed to get parts for review: {e}")
            return []
    
    def check_part_exists(self, part_number: str) -> bool:
        """
        Check if a part exists in the database.
        
        Args:
            part_number: Part number to check
            
        Returns:
            True if part exists, False otherwise
        """
        try:
            self.db_manager.get_part(part_number)
            return True
        except:
            return False
    
    def _create_discovery_log(self, context: Optional[UnknownPartContext], session_id: str, action: str):
        """
        Create a discovery log entry.
        
        Args:
            context: Unknown part context
            session_id: Discovery session ID
            action: Action taken ('discovered', 'added', 'skipped', 'collected')
        """
        try:
            if context:
                log_entry = PartDiscoveryLog(
                    part_number=context.part_number,
                    action_taken=action,
                    processing_session_id=session_id,
                    discovered_price=context.discovered_price,
                    invoice_number=context.invoice_number
                )
                self.db_manager.create_discovery_log(log_entry)
        except Exception as e:
            self.logger.warning(f"Failed to create discovery log: {e}")


def create_part_discovery_service(db_manager: DatabaseManager) -> PartDiscoveryService:
    """
    Create a PartDiscoveryService instance with standard configuration.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        Configured PartDiscoveryService instance
    """
    return PartDiscoveryService(db_manager)