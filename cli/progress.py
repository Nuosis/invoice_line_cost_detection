"""
Progress indicator utilities for the CLI interface.

This module provides progress bars, spinners, and status indicators
for long-running operations in the CLI application.
"""

import time
import threading
from typing import Optional, Callable, Any, Iterator
from contextlib import contextmanager

import click


class ProgressBar:
    """
    A wrapper around Click's progress bar with additional features.
    """
    
    def __init__(self, length: Optional[int] = None, label: str = "Processing",
                 show_eta: bool = True, show_percent: bool = True,
                 show_pos: bool = True, item_show_func: Optional[Callable] = None):
        """
        Initialize progress bar.
        
        Args:
            length: Total number of items to process
            label: Label to display with progress bar
            show_eta: Whether to show estimated time remaining
            show_percent: Whether to show percentage complete
            show_pos: Whether to show current position
            item_show_func: Function to format current item display
        """
        self.length = length
        self.label = label
        self.show_eta = show_eta
        self.show_percent = show_percent
        self.show_pos = show_pos
        self.item_show_func = item_show_func
        self._bar = None
    
    def __enter__(self):
        """Enter context manager."""
        self._bar = click.progressbar(
            length=self.length,
            label=self.label,
            show_eta=self.show_eta,
            show_percent=self.show_percent,
            show_pos=self.show_pos,
            item_show_func=self.item_show_func
        )
        return self._bar.__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self._bar:
            return self._bar.__exit__(exc_type, exc_val, exc_tb)


class Spinner:
    """
    A simple spinner for operations without known duration.
    """
    
    def __init__(self, message: str = "Processing", spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
        """
        Initialize spinner.
        
        Args:
            message: Message to display with spinner
            spinner_chars: Characters to cycle through for spinner animation
        """
        self.message = message
        self.spinner_chars = spinner_chars
        self._stop_event = threading.Event()
        self._thread = None
        self._current_char_index = 0
    
    def _spin(self):
        """Internal method to animate the spinner."""
        while not self._stop_event.is_set():
            char = self.spinner_chars[self._current_char_index]
            click.echo(f"\r{char} {self.message}", nl=False)
            self._current_char_index = (self._current_char_index + 1) % len(self.spinner_chars)
            time.sleep(0.1)
    
    def start(self):
        """Start the spinner animation."""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._spin)
            self._thread.daemon = True
            self._thread.start()
    
    def stop(self, final_message: Optional[str] = None):
        """
        Stop the spinner animation.
        
        Args:
            final_message: Optional final message to display
        """
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=0.5)
        
        # Clear the spinner line
        click.echo("\r" + " " * (len(self.message) + 10), nl=False)
        click.echo("\r", nl=False)
        
        if final_message:
            click.echo(final_message)
    
    def __enter__(self):
        """Enter context manager."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if exc_type is None:
            self.stop("✓ Complete")
        else:
            self.stop("✗ Failed")


@contextmanager
def progress_bar(length: Optional[int] = None, label: str = "Processing",
                 show_eta: bool = True, show_percent: bool = True,
                 show_pos: bool = True, item_show_func: Optional[Callable] = None):
    """
    Context manager for progress bar.
    
    Args:
        length: Total number of items to process
        label: Label to display with progress bar
        show_eta: Whether to show estimated time remaining
        show_percent: Whether to show percentage complete
        show_pos: Whether to show current position
        item_show_func: Function to format current item display
        
    Yields:
        Progress bar object
    """
    with ProgressBar(length, label, show_eta, show_percent, show_pos, item_show_func) as bar:
        yield bar


@contextmanager
def spinner(message: str = "Processing", spinner_chars: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
    """
    Context manager for spinner.
    
    Args:
        message: Message to display with spinner
        spinner_chars: Characters to cycle through for spinner animation
        
    Yields:
        Spinner object
    """
    with Spinner(message, spinner_chars) as spin:
        yield spin


def show_file_progress(files: list, label: str = "Processing files") -> Iterator[tuple]:
    """
    Show progress for file processing operations.
    
    Args:
        files: List of files to process
        label: Label to display with progress bar
        
    Yields:
        Tuple of (index, file, progress_bar)
    """
    def show_current_file(item):
        if item and hasattr(item, 'name'):
            return f"Current: {item.name}"
        return str(item) if item else ""
    
    with progress_bar(
        length=len(files),
        label=label,
        item_show_func=show_current_file
    ) as bar:
        for i, file in enumerate(files):
            bar.current_item = file
            yield i, file, bar
            bar.update(1)


def show_batch_progress(batches: list, label: str = "Processing batches") -> Iterator[tuple]:
    """
    Show progress for batch processing operations.
    
    Args:
        batches: List of batches to process
        label: Label to display with progress bar
        
    Yields:
        Tuple of (index, batch, progress_bar)
    """
    def show_current_batch(item):
        if isinstance(item, dict) and 'name' in item:
            return f"Batch: {item['name']}"
        return f"Batch {item}" if item else ""
    
    with progress_bar(
        length=len(batches),
        label=label,
        show_eta=True,
        item_show_func=show_current_batch
    ) as bar:
        for i, batch in enumerate(batches):
            bar.current_item = batch
            yield i, batch, bar
            bar.update(1)


def show_import_progress(records: list, label: str = "Importing records") -> Iterator[tuple]:
    """
    Show progress for data import operations.
    
    Args:
        records: List of records to import
        label: Label to display with progress bar
        
    Yields:
        Tuple of (index, record, progress_bar)
    """
    def show_import_rate(item):
        # Calculate and show import rate
        if hasattr(show_import_rate, 'start_time'):
            elapsed = time.time() - show_import_rate.start_time
            if elapsed > 0:
                rate = (getattr(show_import_rate, 'processed', 0)) / elapsed
                return f"Rate: {rate:.1f} records/sec"
        return ""
    
    show_import_rate.start_time = time.time()
    show_import_rate.processed = 0
    
    with progress_bar(
        length=len(records),
        label=label,
        show_eta=True,
        item_show_func=show_import_rate
    ) as bar:
        for i, record in enumerate(records):
            show_import_rate.processed = i + 1
            yield i, record, bar
            bar.update(1)


class ProgressTracker:
    """
    A comprehensive progress tracker for complex operations.
    """
    
    def __init__(self, total_items: int = 0, label: str = "Processing"):
        """
        Initialize progress tracker.
        
        Args:
            total_items: Total number of items to process
            label: Label to display with progress
        """
        self.total_items = total_items
        self.label = label
        self.processed_items = 0
        self.start_time = time.time()
        self.current_operation = ""
    
    def update(self, increment: int = 1, operation: str = None):
        """
        Update progress.
        
        Args:
            increment: Number of items processed
            operation: Current operation description
        """
        self.processed_items += increment
        if operation:
            self.current_operation = operation
    
    def set_total(self, total: int):
        """Set the total number of items."""
        self.total_items = total
    
    def get_progress_percentage(self) -> float:
        """Get current progress as percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    def get_eta(self) -> str:
        """Get estimated time of arrival."""
        if self.processed_items == 0:
            return "Calculating..."
        
        elapsed = self.get_elapsed_time()
        rate = self.processed_items / elapsed
        
        if rate == 0:
            return "Unknown"
        
        remaining_items = self.total_items - self.processed_items
        remaining_seconds = remaining_items / rate
        
        return estimate_time_remaining(self.processed_items, self.total_items, self.start_time)
    
    def format_status(self) -> str:
        """Format current status for display."""
        percentage = self.get_progress_percentage()
        elapsed = self.get_elapsed_time()
        
        status = f"{self.label}: {self.processed_items}/{self.total_items} ({percentage:.1f}%)"
        
        if self.current_operation:
            status += f" - {self.current_operation}"
        
        if elapsed > 1:  # Only show time info after 1 second
            status += f" - Elapsed: {elapsed:.1f}s"
            if self.total_items > 0 and self.processed_items > 0:
                eta = self.get_eta()
                status += f" - ETA: {eta}"
        
        return status


class MultiStepProgress:
    """
    Progress indicator for multi-step operations.
    """
    
    def __init__(self, steps: list, overall_label: str = "Overall Progress"):
        """
        Initialize multi-step progress.
        
        Args:
            steps: List of step names
            overall_label: Label for overall progress
        """
        self.steps = steps
        self.overall_label = overall_label
        self.current_step = 0
        self.total_steps = len(steps)
    
    def start_step(self, step_name: str, message: str = None):
        """
        Start a new step.
        
        Args:
            step_name: Name of the step
            message: Optional message to display
        """
        if step_name in self.steps:
            self.current_step = self.steps.index(step_name) + 1
        
        step_msg = f"Step {self.current_step}/{self.total_steps}: {step_name}"
        if message:
            step_msg += f" - {message}"
        
        click.echo(step_msg)
        
        # Show overall progress
        overall_percent = (self.current_step - 1) / self.total_steps * 100
        click.echo(f"{self.overall_label}: {overall_percent:.1f}% complete")
    
    def complete_step(self, success: bool = True, message: str = None):
        """
        Mark current step as complete.
        
        Args:
            success: Whether the step completed successfully
            message: Optional completion message
        """
        status = "✓" if success else "✗"
        step_name = self.steps[self.current_step - 1] if self.current_step > 0 else "Unknown"
        
        completion_msg = f"{status} {step_name}"
        if message:
            completion_msg += f" - {message}"
        
        click.echo(completion_msg)
    
    def finish(self, success: bool = True, message: str = None):
        """
        Finish the multi-step operation.
        
        Args:
            success: Whether all steps completed successfully
            message: Optional final message
        """
        status = "✓" if success else "✗"
        final_msg = f"{status} {self.overall_label} complete"
        if message:
            final_msg += f" - {message}"
        
        click.echo(final_msg)


def estimate_time_remaining(processed: int, total: int, start_time: float) -> str:
    """
    Estimate time remaining for an operation.
    
    Args:
        processed: Number of items processed
        total: Total number of items
        start_time: Start time of the operation
        
    Returns:
        Formatted time remaining string
    """
    if processed == 0:
        return "Calculating..."
    
    elapsed = time.time() - start_time
    rate = processed / elapsed
    
    if rate == 0:
        return "Unknown"
    
    remaining_items = total - processed
    remaining_seconds = remaining_items / rate
    
    if remaining_seconds < 60:
        return f"{remaining_seconds:.0f} seconds"
    elif remaining_seconds < 3600:
        minutes = remaining_seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = remaining_seconds / 3600
        return f"{hours:.1f} hours"


def format_processing_rate(processed: int, elapsed_time: float, unit: str = "items") -> str:
    """
    Format processing rate for display.
    
    Args:
        processed: Number of items processed
        elapsed_time: Elapsed time in seconds
        unit: Unit name for items
        
    Returns:
        Formatted rate string
    """
    if elapsed_time == 0:
        return f"∞ {unit}/sec"
    
    rate = processed / elapsed_time
    
    if rate < 1:
        return f"{rate:.2f} {unit}/sec"
    elif rate < 100:
        return f"{rate:.1f} {unit}/sec"
    else:
        return f"{rate:.0f} {unit}/sec"