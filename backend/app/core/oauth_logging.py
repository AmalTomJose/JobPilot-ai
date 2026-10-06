"""Keep one-time OAuth codes and state out of Uvicorn access logs."""
import logging


class OAuthAccessFilter(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, tuple) and len(record.args) >= 3:
            args = list(record.args)
            if isinstance(args[2], str) and args[2].split('?', 1)[0] == '/email/gmail/callback':
                args[2] = '/email/gmail/callback'
                record.args = tuple(args)
        return True


def install_oauth_log_filter():
    logger = logging.getLogger('uvicorn.access')
    if not any(isinstance(item, OAuthAccessFilter) for item in logger.filters):
        logger.addFilter(OAuthAccessFilter())
