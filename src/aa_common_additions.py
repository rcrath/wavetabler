# aa_common_additions.py
# These functions should be ADDED to aa_common.py to support the fixes

def get_method_suffix():
    """
    Returns the method suffix for filenames.
    FIX #28: Add method tags to identify segmentation method used.
    
    Returns:
        '_a' for autocorrelation
        '_z' for zero-crossing
    """
    global autocorrelation_flag
    return "_a" if autocorrelation_flag else "_z"

def add_suffix_to_filename(filename, suffix):
    """
    Add suffix to filename without duplicating.
    FIX #30: Prevents _chunk_chunk and similar issues.
    
    Args:
        filename: The original filename (with or without extension)
        suffix: The suffix to add (without underscore)
    
    Returns:
        Filename with suffix added (or unchanged if already present)
    
    Examples:
        add_suffix_to_filename("test.wav", "chunk") -> "test_chunk.wav"
        add_suffix_to_filename("test_chunk.wav", "chunk") -> "test_chunk.wav"
        add_suffix_to_filename("test_chunk", "norm") -> "test_chunk_norm"
    """
    base, ext = os.path.splitext(filename)
    
    # Check if suffix already present
    if base.endswith(f"_{suffix}"):
        return filename
    
    # Add new suffix
    return f"{base}_{suffix}{ext}"

def sanitize_filename(filename):
    """
    Sanitize filename by stripping whitespace and removing invalid characters.
    FIX #36: Prevents trailing spaces from breaking os.makedirs()
    
    Args:
        filename: The original filename
    
    Returns:
        Sanitized filename safe for filesystem operations
    """
    # Strip leading/trailing whitespace
    filename = filename.strip()
    
    # Remove problematic characters but keep common safe ones
    # Allows: alphanumeric, spaces, dots, dashes, underscores
    filename = re.sub(r'[^\w\s\-\.]', '', filename)
    
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    
    # Remove any trailing dots (problematic on Windows)
    filename = filename.rstrip('.')
    
    return filename

def find_nearest_zero_crossing(data, sample_index, window=None, threshold=None):
    """
    Find the nearest zero crossing to the given sample index.
    FIX: Zero-crossing alignment for pick mode
    
    Args:
        data: Audio data array
        sample_index: Target sample index
        window: Search window size (default: ZERO_WINDOW from aa_common)
        threshold: Amplitude threshold (default: zero_threshold from aa_common)
    
    Returns:
        Index of nearest zero crossing, or original index if none found
    """
    global zero_threshold, ZERO_WINDOW
    
    if window is None:
        window = ZERO_WINDOW
    if threshold is None:
        threshold = zero_threshold
    
    # Define search window
    start = max(0, sample_index - window)
    end = min(len(data), sample_index + window)
    
    if start >= end:
        return sample_index
    
    # Extract segment
    segment = data[start:end]
    
    # Find zero crossings with low amplitude
    crossings = []
    for i in range(1, len(segment)):
        # Check if sign changes (crosses zero)
        if (segment[i-1] * segment[i]) <= 0:
            # Check if both points are below threshold amplitude
            if abs(segment[i]) < threshold and abs(segment[i-1]) < threshold:
                actual_index = start + i
                crossings.append(actual_index)
    
    if crossings:
        # Return crossing nearest to original index
        nearest = min(crossings, key=lambda x: abs(x - sample_index))
        return nearest
    else:
        # No suitable crossing found within threshold
        # Try again with relaxed threshold
        relaxed_threshold = threshold * 2
        for i in range(1, len(segment)):
            if (segment[i-1] * segment[i]) <= 0:
                if abs(segment[i]) < relaxed_threshold or abs(segment[i-1]) < relaxed_threshold:
                    actual_index = start + i
                    crossings.append(actual_index)
        
        if crossings:
            nearest = min(crossings, key=lambda x: abs(x - sample_index))
            return nearest
        else:
            # Still nothing - return original
            return sample_index

def calculate_adaptive_tolerance_percentage(segment_lengths, base_tolerance=5.0):
    """
    Calculate adaptive tolerance based on variance in segment lengths.
    FIX #22: More variance requires wider tolerance.
    
    Args:
        segment_lengths: Dictionary or list of segment lengths
        base_tolerance: Base tolerance percentage (default: 5%)
    
    Returns:
        Adaptive tolerance percentage (capped at 20%)
    """
    if isinstance(segment_lengths, dict):
        lengths = list(segment_lengths.values())
    else:
        lengths = list(segment_lengths)
    
    if not lengths:
        return base_tolerance
    
    # Calculate coefficient of variation
    std_dev = np.std(lengths)
    mean_length = np.mean(lengths)
    
    if mean_length == 0:
        return base_tolerance
    
    cv = std_dev / mean_length
    
    # Increase tolerance proportionally to variation
    # cv > 0.05 (5% std dev) triggers increase
    if cv > 0.05:
        adaptive_tolerance = base_tolerance * (1 + cv * 10)
    else:
        adaptive_tolerance = base_tolerance
    
    # Cap maximum tolerance at 20%
    return min(adaptive_tolerance, 20.0)

def validate_segment_distribution(segment_sizes, lower_bound, upper_bound):
    """
    Validate that segment distribution is reasonable.
    FIX #22: Helps diagnose autocorrelation issues.
    
    Args:
        segment_sizes: List of (filename, size) tuples
        lower_bound: Lower tolerance bound
        upper_bound: Upper tolerance bound
    
    Returns:
        (is_valid, warning_message) tuple
    """
    total = len(segment_sizes)
    
    if total == 0:
        return False, "❌ No segments found at all!"
    
    # Count segments within tolerance
    within_tolerance = sum(1 for _, size in segment_sizes 
                          if lower_bound <= size <= upper_bound)
    
    within_percent = (within_tolerance / total) * 100
    
    # Determine validity
    if within_percent < 10:
        msg = (f"❌ Only {within_percent:.1f}% of segments within tolerance!\n"
               f"   Try: widening tolerance, using other method, or checking input audio")
        return False, msg
    elif within_percent < 30:
        msg = f"⚠️  Warning: Only {within_percent:.1f}% of segments within tolerance"
        return True, msg
    else:
        return True, None

def get_timestamped_filename(base, suffix, extension=".wav"):
    """
    Generate a timestamped filename with method tag.
    FIX #28: Include method tag in output filenames.
    
    Args:
        base: Base filename (without extension)
        suffix: Descriptive suffix (e.g., "chunk", "pick", "full")
        extension: File extension (default: ".wav")
    
    Returns:
        Formatted filename like "base_z_20260205_143022_chunk.wav"
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    method_tag = get_method_suffix()
    
    # Sanitize base to prevent issues
    base = sanitize_filename(base)
    
    return f"{base}{method_tag}_{timestamp}_{suffix}{extension}"

# Add these to initialize_settings() in aa_common.py:
def initialize_settings_enhanced():
    """
    Enhanced version of initialize_settings() with additional options.
    Replace the existing initialize_settings() with this version.
    """
    global global_settings
    
    global_settings = {
        # Existing settings
        'zero_crossing_method': 1,
        'percent_tolerance': 5,
        'discard_atk_choice': 'N',
        'discard_dev_choice': 'N',
        'discard_good_choice': 'N',
        'cleanup_choice': 'Y',
        'accept_current_settings': False,
        
        # NEW: Enhanced settings for fixes
        'percent_tolerance_autocorr': 10,  # FIX #22: Wider tolerance for autocorr
        'autocorr_prominence': 0.5,        # FIX #26: Configurable prominence
        'use_adaptive_tolerance': True,     # FIX #22: Enable adaptive tolerance
        'add_method_tags': True,            # FIX #28: Add _z or _a tags
        'preserve_suffixes': True,          # FIX #31: Keep _norm, _dev, _atk
        'skip_correct_length_interp': True, # Skip interpolating already-correct files
        'align_to_zero_cross': True,        # Align pick mode to zero crossings
    }
    
    return global_settings
