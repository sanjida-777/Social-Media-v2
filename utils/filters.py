from datetime import datetime
import time

def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime object to a string using the given format."""
    if value is None:
        return ""
    return value.strftime(format)

def timeago(value):
    """Format a datetime object to a relative time string (e.g., "2 hours ago")."""
    if value is None:
        return ""

    now = datetime.now()
    diff = now - value

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years > 1 else ''} ago"

# Register filters with Flask app
def register_filters(app):
    """Register custom filters with the Flask app."""
    app.jinja_env.filters['strftime'] = format_datetime
    app.jinja_env.filters['timeago'] = timeago
    app.jinja_env.filters['humanize'] = timeago  # Add humanize as an alias for timeago
