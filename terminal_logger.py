import sys
import os
from datetime import datetime

class TerminalLogger:
    """
    Simple terminal logging class that captures all terminal output to log files.
    """
    
    def __init__(self, log_name: str = "terminal_output"):
        """
        Initialize the terminal logger.
        
        Args:
            log_name: Base name for the log file
        """
        self.log_name = log_name
        self.log_dir = "logs"
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.log_file = None
        self.tee_stdout = None
        self.tee_stderr = None
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Generate timestamp for unique log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"{log_name}_{timestamp}.txt"
        self.log_path = os.path.join(self.log_dir, self.log_filename)
        
        # Start logging
        self.start_logging()
        
    def start_logging(self):
        """Start capturing all terminal output to the log file."""
        try:
            # Open log file
            self.log_file = open(self.log_path, 'w', encoding='utf-8')
            
            # Create Tee objects for stdout and stderr
            self.tee_stdout = Tee(self.original_stdout, self.log_file)
            self.tee_stderr = Tee(self.original_stderr, self.log_file)
            
            # Redirect stdout and stderr
            sys.stdout = self.tee_stdout
            sys.stderr = self.tee_stderr
            
            # Log the start of the session
            print(f"=== TERMINAL LOGGING STARTED ===")
            print(f"Log file: {self.log_path}")
            print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            
        except Exception as e:
            print(f"Error starting logging: {e}")
            # Fallback to original stdout
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
    
    def stop_logging(self):
        """Stop logging and restore original stdout/stderr."""
        try:
            if self.log_file:
                print(f"\n=== LOGGING ENDED ===")
                print(f"Log saved to: {self.log_path}")
                print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 50)
                
                # Restore original stdout and stderr
                sys.stdout = self.original_stdout
                sys.stderr = self.original_stderr
                
                # Close log file
                self.log_file.close()
                self.log_file = None
                
        except Exception as e:
            print(f"Error stopping logging: {e}")
    
    def get_log_path(self) -> str:
        """Get the path to the current log file."""
        return self.log_path
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures logging is stopped."""
        self.stop_logging()


class Tee:
    """
    Tee class that writes to both terminal and log file.
    """
    
    def __init__(self, terminal_stream, log_file):
        self.terminal = terminal_stream
        self.log_file = log_file
    
    def write(self, message):
        """Write message to both terminal and log file."""
        try:
            self.terminal.write(message)
            self.log_file.write(message)
            self.log_file.flush()  # Ensure immediate write to file
        except Exception as e:
            # If logging fails, still write to terminal
            self.terminal.write(message)
            self.terminal.write(f"\n[LOGGING ERROR: {e}]\n")
    
    def flush(self):
        """Flush both streams."""
        try:
            self.terminal.flush()
            self.log_file.flush()
        except Exception:
            self.terminal.flush()


# Example usage
if __name__ == "__main__":
    # Start logging
    logger = TerminalLogger("test_session")
    
    try:
        print("This output will be captured in the log file")
        print("So will this line")
        print("And any errors too!")
        
        # Simulate some work
        for i in range(3):
            print(f"Processing step {i+1}...")
            
    finally:
        # Stop logging
        logger.stop_logging()
        print("Logging stopped - this won't be captured") 