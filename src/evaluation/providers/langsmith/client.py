# src\evaluation\providers\langsmith\client.py


from langsmith import Client

from src.logging_exception.logging.logger import logger


class LangSmithClient:
    """
    Wrapper around the LangSmith SDK.

    Responsible only for creating and exposing the
    LangSmith client instance.
    """

    def __init__(self):

        logger.info("Initializing LangSmith client.")

        self.client = Client()

    def get_client(self) -> Client:
        """
        Return initialized LangSmith client.
        """

        return self.client