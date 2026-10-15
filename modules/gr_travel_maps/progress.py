"""Request-local progress; the same generators serve JSON and streaming clients."""
from __future__ import annotations


def event(phase, message, **details):
    return {'type': 'progress', 'phase': phase, 'message': message, **details}


def finish(steps):
    """Run without a progress consumer, preserving the generator's return value."""
    try:
        while True:
            next(steps)
    except StopIteration as completed:
        return completed.value
    finally:
        steps.close()
