"""
Interactive Part Discovery Service for the Invoice Rate Detection System.

This module provides the core service for discovering unknown parts during invoice
processing and managing the interactive workflow for adding them to the database.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

from database.models import Part, PartDiscoveryLog, DatabaseError, ValidationError
from database.database import DatabaseManager
from processing.models import LineItem, InvoiceData
from processing.part_discovery_models import UnknownPartContext
from processing.part_discovery_prompts import PartDiscoveryPrompt
from cli.exceptions import UserCancelledError


logger = logging.getLogger(__name__)


@dataclass
class PartDiscoveryResult:
    """
    Result of a part discovery operation.
    
    Attributes:
        part_number: The part number that was processed
        action_taken: Action taken ('added', 'skipped', 'stop_processing', 'skip_all')
        part_added: The Part object if it was added to the database
        user_decision: User's decision during interactive discovery
        discovery_context: Original discovery context
        error_message: Error message if the operation failed
    """
    part_number: str
    action_taken: str
    part_added: Optional[Part] = None
    user_decision: Optional[str] = None
    discovery_context: Optional[UnknownPartContext] = None
    error_message: Optional[str] = None
    
    @property
    def was_successful(self) -> bool:
        """Check if the discovery operation was successful."""
        return self.action_taken in ['added', 'skipped'] and not self.error_message


@dataclass
class DiscoverySession:
    """
    Manages a discovery session for tracking unknown parts across multiple invoices.
    
    Attributes:
        session_id: Unique session identifier
        unknown_parts: Collection of unknown parts discovered
        user_decisions: User decisions made during the session
        parts_added: Parts successfully added to the database
        processing_mode: Mode of processing ('interactive', 'batch_collect', 'auto_add')
        start_time: When the session started
    """
    session_id: str
    unknown_parts: Dict[str, List[UnknownPartContext]] = field(default_factory=dict)
    user_decisions: Dict[str, str] = field(default_factory=dict)
    parts_added: List[Part] = field(default_factory=list)
    processing_mode: str = 'interactive'
    start_time: datetime = field(default_factory=datetime.now)
    
    def add_unknown_part(self, context: UnknownPartContext) -> None:
        """Add an unknown part context to the session."""
        if context.part_number not in self.unknown_parts:
            self.unknown_parts[context.part_number] = []
        self.unknown_parts[context.part_number].append(context)
    
    def get_unique_part_numbers(self) -> Set[str]:
        """Get set of unique part numbers discovered in this session."""
        return set(self.unknown_parts.keys())
    
    def get_part_contexts(self, part_number: str) -> List[UnknownPartContext]:
        """Get all contexts for a specific part number."""
        return self.unknown_parts.get(part_number, [])
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the session."""
        return {
            'session_id': self.session_id,
            'unique_parts_discovered': len(self.unknown_parts),
            'total_occurrences': sum(len(contexts) for contexts in self.unknown_parts.values()),
            'parts_added': len(self.parts_added),
            'processing_mode': self.processing_mode,
            'duration_minutes': (datetime.now() - self.start_time).total_seconds() / 60
        }


class InteractivePartDiscoveryService:
    """
    Service for managing interactive part discovery during invoice processing.
    
    This service handles the discovery of unknown parts, manages user interactions
    for adding parts to the database, and maintains audit trails of all discovery
    activities.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the discovery service.
        
        Args:
            db_manager: Database manager for part operations
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.prompt_handler = PartDiscoveryPrompt()
        self.active_sessions: Dict[str, DiscoverySession] = {}
    
    def start_discovery_session(self, session_id: Optional[str] = None, 
                              processing_mode: str = 'interactive') -> str:
        """
        Start a new discovery session.
        
        Args:
            session_id: Optional custom session ID
            processing_mode: Processing mode ('interactive', 'batch_collect', 'auto_add')
            
        Returns:
            Session ID for the new session
        """
        if not session_id:
            session_id = str(uuid.uuid4())
        
        session = DiscoverySession(
            session_id=session_id,
            processing_mode=processing_mode
        )
        
        self.active_sessions[session_id] = session
        self.logger.info(f"Started discovery session {session_id} in {processing_mode} mode")
        
        return session_id
    
    def discover_unknown_parts_from_invoice(self, invoice_data: InvoiceData, 
                                          session_id: str) -> List[UnknownPartContext]:
        """
        Discover unknown parts from an invoice.
        
        Args:
            invoice_data: Extracted invoice data
            session_id: Discovery session ID
            
        Returns:
            List of unknown part contexts discovered
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"No active discovery session found: {session_id}")
        
        session = self.active_sessions[session_id]
        unknown_contexts = []
        
        # Check each line item for unknown parts
        for line_item in invoice_data.get_valid_line_items():
            if not line_item.item_code:
                continue
            
            try:
                # Check if part exists in database
                existing_part = self.db_manager.get_part(line_item.item_code)
                self.logger.debug(f"Part {line_item.item_code} found in database")
                continue
                
            except Exception:
                # Part not found - create unknown part context
                context = UnknownPartContext(
                    part_number=line_item.item_code,
                    invoice_number=invoice_data.invoice_number,
                    invoice_date=invoice_data.invoice_date,
                    line_item=line_item,
                    discovered_price=line_item.rate,
                    description=line_item.description,
                    quantity=line_item.quantity,
                    wearer_info=f"{line_item.wearer_number} - {line_item.wearer_name}" if line_item.wearer_number else None
                )
                
                unknown_contexts.append(context)
                session.add_unknown_part(context)
                
                # Log the discovery
                self._log_part_discovery(context, session_id, 'discovered')
        
        self.logger.info(f"Discovered {len(unknown_contexts)} unknown parts in invoice {invoice_data.invoice_number}")
        return unknown_contexts
    
    def process_unknown_parts_interactive(self, session_id: str) -> List[PartDiscoveryResult]:
        """
        Process unknown parts with interactive user prompts.
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            List of discovery results
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"No active discovery session found: {session_id}")
        
        session = self.active_sessions[session_id]
        results = []
        
        unique_parts = session.get_unique_part_numbers()
        if not unique_parts:
            self.logger.info("No unknown parts to process")
            return results
        
        self.logger.info(f"Starting interactive processing of {len(unique_parts)} unknown parts")
        
        try:
            for part_number in unique_parts:
                # Skip if user already made a global decision
                if session.user_decisions.get('skip_all_remaining'):
                    result = PartDiscoveryResult(
                        part_number=part_number,
                        action_taken='skipped',
                        user_decision='skip_all_remaining'
                    )
                    results.append(result)
                    continue
                
                # Get all contexts for this part
                contexts = session.get_part_contexts(part_number)
                primary_context = contexts[0]  # Use first context for prompting
                
                # Prepare context for user prompt
                prompt_context = {
                    'invoice_number': primary_context.invoice_number,
                    'line_item': primary_context.description,
                    'price': primary_context.discovered_price,
                    'quantity': primary_context.quantity,
                    'occurrences': len(contexts),
                    'invoices': list(set(c.invoice_number for c in contexts if c.invoice_number))
                }
                
                # Prompt user for decision
                user_decision = self.prompt_handler.prompt_for_unknown_part(
                    primary_context, len(contexts)
                )
                
                # Process user decision
                result = self._process_user_decision(
                    part_number, user_decision, contexts, session
                )
                results.append(result)
                
                # Handle global decisions
                if user_decision['action'] == 'stop_processing':
                    self.logger.info("User requested to stop processing")
                    break
                elif user_decision['action'] == 'skip_all_unknown_parts':
                    session.user_decisions['skip_all_remaining'] = 'true'
                    self.logger.info("User requested to skip all remaining unknown parts")
        
        except UserCancelledError:
            self.logger.info("Interactive discovery cancelled by user")
            result = PartDiscoveryResult(
                part_number="CANCELLED",
                action_taken='stop_processing',
                user_decision='cancelled'
            )
            results.append(result)
        
        return results
    
    def process_unknown_parts_batch(self, session_id: str) -> List[PartDiscoveryResult]:
        """
        Process unknown parts in batch collection mode (no user interaction).
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            List of discovery results
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"No active discovery session found: {session_id}")
        
        session = self.active_sessions[session_id]
        results = []
        
        unique_parts = session.get_unique_part_numbers()
        self.logger.info(f"Batch collecting {len(unique_parts)} unknown parts")
        
        for part_number in unique_parts:
            contexts = session.get_part_contexts(part_number)
            
            # Log as collected for later review
            for context in contexts:
                self._log_part_discovery(context, session_id, 'skipped', 'batch_collected')
            
            result = PartDiscoveryResult(
                part_number=part_number,
                action_taken='skipped',
                user_decision='batch_collected',
                discovery_context=contexts[0] if contexts else None
            )
            results.append(result)
        
        return results
    
    def _process_user_decision(self, part_number: str, user_decision: Dict[str, Any],
                             contexts: List[UnknownPartContext], 
                             session: DiscoverySession) -> PartDiscoveryResult:
        """
        Process a user's decision about an unknown part.
        
        Args:
            part_number: The part number being processed
            user_decision: User's decision from the prompt
            contexts: All contexts for this part
            session: Current discovery session
            
        Returns:
            PartDiscoveryResult with the outcome
        """
        action = user_decision['action']
        
        if action == 'add_to_database_now':
            try:
                # Create part from user input
                part_details = user_decision['part_details']
                part = Part(
                    part_number=part_number,
                    authorized_price=part_details['authorized_price'],
                    description=part_details.get('description'),
                    category=part_details.get('category'),
                    source='discovered',
                    first_seen_invoice=contexts[0].invoice_number,
                    notes=part_details.get('notes')
                )
                
                # Add to database
                created_part = self.db_manager.create_part(part)
                session.parts_added.append(created_part)
                
                # Log the addition
                for context in contexts:
                    self._log_part_discovery(
                        context, session.session_id, 'added', 
                        user_decision=user_decision['action']
                    )
                
                self.logger.info(f"Successfully added part {part_number} to database")
                
                return PartDiscoveryResult(
                    part_number=part_number,
                    action_taken='added',
                    part_added=created_part,
                    user_decision=action,
                    discovery_context=contexts[0]
                )
                
            except (ValidationError, DatabaseError) as e:
                error_msg = f"Failed to add part {part_number}: {e}"
                self.logger.error(error_msg)
                
                return PartDiscoveryResult(
                    part_number=part_number,
                    action_taken='failed',
                    user_decision=action,
                    discovery_context=contexts[0],
                    error_message=error_msg
                )
        
        elif action in ['skip_this_part', 'skip_all_unknown_parts']:
            # Log as skipped
            for context in contexts:
                self._log_part_discovery(
                    context, session.session_id, 'skipped',
                    user_decision=action
                )
            
            return PartDiscoveryResult(
                part_number=part_number,
                action_taken='skipped',
                user_decision=action,
                discovery_context=contexts[0]
            )
        
        else:  # stop_processing
            return PartDiscoveryResult(
                part_number=part_number,
                action_taken='stop_processing',
                user_decision=action,
                discovery_context=contexts[0]
            )
    
    def _log_part_discovery(self, context: UnknownPartContext, session_id: str,
                          action_taken: str, user_decision: Optional[str] = None) -> None:
        """
        Log a part discovery event to the database.
        
        Args:
            context: Unknown part context
            session_id: Discovery session ID
            action_taken: Action taken ('discovered', 'added', 'skipped', etc.)
            user_decision: User's decision if applicable
        """
        try:
            log_entry = PartDiscoveryLog(
                part_number=context.part_number,
                invoice_number=context.invoice_number,
                invoice_date=context.invoice_date,
                discovered_price=context.discovered_price,
                authorized_price=None,  # Will be set if part is added
                action_taken=action_taken,
                user_decision=user_decision,
                processing_session_id=session_id,
                notes=context.description
            )
            
            self.db_manager.create_discovery_log(log_entry)
            self.logger.debug(f"Logged discovery event for {context.part_number}: {action_taken}")
            
        except Exception as e:
            self.logger.error(f"Failed to log discovery event: {e}")
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary of a discovery session.
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            Dictionary containing session summary
        """
        if session_id not in self.active_sessions:
            # Try to get summary from database logs
            return self._get_session_summary_from_logs(session_id)
        
        session = self.active_sessions[session_id]
        return session.get_session_summary()
    
    def _get_session_summary_from_logs(self, session_id: str) -> Dict[str, Any]:
        """Get session summary from database logs for completed sessions."""
        try:
            logs = self.db_manager.get_discovery_logs(session_id=session_id)
            
            unique_parts = set(log.part_number for log in logs)
            parts_added = len([log for log in logs if log.action_taken == 'added'])
            
            return {
                'session_id': session_id,
                'unique_parts_discovered': len(unique_parts),
                'total_occurrences': len(logs),
                'parts_added': parts_added,
                'processing_mode': 'completed',
                'from_database_logs': True
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session summary from logs: {e}")
            return {
                'session_id': session_id,
                'error': str(e)
            }
    
    def end_discovery_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a discovery session and return final summary.
        
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
        except Exception:
            return False
    
    def get_unknown_parts_for_review(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get unknown parts from a session formatted for review.
        
        Args:
            session_id: Discovery session ID
            
        Returns:
            List of unknown parts with analysis data
        """
        try:
            logs = self.db_manager.get_discovery_logs(session_id=session_id)
            unknown_logs = [log for log in logs if log.action_taken == 'discovered']
            
            # Group by part number for analysis
            parts_data = {}
            for log in unknown_logs:
                if log.part_number not in parts_data:
                    parts_data[log.part_number] = {
                        'part_number': log.part_number,
                        'discovered_prices': [],
                        'invoices': [],
                        'descriptions': set(),
                        'occurrences': 0
                    }
                
                if log.discovered_price:
                    parts_data[log.part_number]['discovered_prices'].append(log.discovered_price)
                if log.invoice_number:
                    parts_data[log.part_number]['invoices'].append(log.invoice_number)
                if log.notes:
                    parts_data[log.part_number]['descriptions'].add(log.notes)
                
                parts_data[log.part_number]['occurrences'] += 1
            
            # Convert to review format
            review_data = []
            for part_number, data in parts_data.items():
                prices = [p for p in data['discovered_prices'] if p is not None]
                
                review_item = {
                    'part_number': part_number,
                    'occurrences': data['occurrences'],
                    'unique_invoices': len(set(data['invoices'])),
                    'descriptions': list(data['descriptions'])
                }
                
                if prices:
                    review_item.update({
                        'avg_price': sum(prices) / len(prices),
                        'min_price': min(prices),
                        'max_price': max(prices),
                        'price_variance': max(prices) - min(prices) if len(prices) > 1 else 0
                    })
                
                review_data.append(review_item)
            
            return review_data
            
        except Exception as e:
            self.logger.error(f"Failed to get unknown parts for review: {e}")
            return []