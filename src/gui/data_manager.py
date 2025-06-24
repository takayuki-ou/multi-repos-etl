"""
Data Management for the Streamlit GUI.
Handles interactions with settings and database.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from src.config.settings import Settings
from src.db.database import Database

logger = logging.getLogger(__name__)


def _parse_datetime_string(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Parses a datetime string (typically from DB) into a datetime object.
    Assumes format like 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SSZ'.
    """
    if not datetime_str:
        return None
    try:
        # Handle formats like '2023-10-19 08:30:00' or '2023-10-19T08:30:00Z'
        # SQLite often stores datetimes without timezone info by default.
        # GitHub API provides ISO 8601 format e.g. "2011-01-26T19:01:12Z"
        if 'T' in datetime_str and 'Z' in datetime_str:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        else: # Assuming 'YYYY-MM-DD HH:MM:SS' or similar from DB
            return datetime.strptime(datetime_str.split(".")[0], "%Y-%m-%d %H:%M:%S") # Handle potential millis
    except ValueError:
        logger.warning(f"Could not parse datetime string: {datetime_str}", exc_info=True)
        return None


class DataManager:
    def __init__(self):
        try:
            self.settings = Settings()
            db_config = {'db_path': self.settings.sqlite_db_path}
            self.db = Database(db_config)
            # Ensure tables exist
            self.db.create_tables()
            logger.info("DataManager initialized successfully.")
        except ValueError as ve:
            logger.error(f"Configuration error during DataManager initialization: {ve}")
            raise  # Re-raise to be caught by the GUI for user feedback
        except Exception as e:
            logger.error(f"Unexpected error during DataManager initialization: {e}", exc_info=True)
            raise # Re-raise for GUI

    def get_repositories(self) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches the list of repositories.
        Returns a tuple: (data, error_message).
        """
        try:
            repos = self.db.get_repository_list()
            if repos is None: # Should not happen with current db.get_repository_list which returns [] on error
                return None, "Failed to retrieve repositories: unknown database error."
            return repos, None
        except Exception as e:
            logger.error(f"Error getting repositories: {e}", exc_info=True)
            return None, f"Database error while fetching repositories: {e}"

    def get_pull_requests(self, repository_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches pull requests for a given repository ID.
        Returns a tuple: (data, error_message).
        """
        try:
            prs_raw = self.db.get_pull_requests_for_repository(repository_id)
            if prs_raw is None: # Should not happen
                return None, f"Failed to retrieve pull requests for repository ID {repository_id}: unknown database error."

            parsed_prs = []
            for pr_data in prs_raw:
                pr_data['created_at_dt'] = _parse_datetime_string(pr_data.get('created_at'))
                pr_data['updated_at_dt'] = _parse_datetime_string(pr_data.get('updated_at'))
                # Keep original strings as well, GUI might want to display them
                parsed_prs.append(pr_data)
            return parsed_prs, None
        except Exception as e:
            logger.error(f"Error getting pull requests for repo ID {repository_id}: {e}", exc_info=True)
            return None, f"Database error while fetching pull requests: {e}"

    def get_review_comments(self, pr_db_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches review comments for a given pull request database ID.
        Returns a tuple: (data, error_message).
        """
        try:
            comments_raw = self.db.get_review_comments_for_pr(pr_db_id)
            if comments_raw is None: # Should not happen
                return None, f"Failed to retrieve comments for PR ID {pr_db_id}: unknown database error."

            parsed_comments = []
            for comment_data in comments_raw:
                comment_data['created_at_dt'] = _parse_datetime_string(comment_data.get('created_at'))
                # updated_at for comments if available and needed
                # comment_data['updated_at_dt'] = _parse_datetime_string(comment_data.get('updated_at'))
                parsed_comments.append(comment_data)
            return parsed_comments, None
        except Exception as e:
            logger.error(f"Error getting review comments for PR ID {pr_db_id}: {e}", exc_info=True)
            return None, f"Database error while fetching review comments: {e}"

if __name__ == '__main__':
    # Basic test for DataManager
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing DataManager...")
    try:
        dm = DataManager()
        repos, error = dm.get_repositories()
        if error:
            logger.error(f"Test error fetching repos: {error}")
        elif repos:
            logger.info(f"Successfully fetched {len(repos)} repositories.")
            if repos:
                repo_id_to_test = repos[0]['id']
                logger.info(f"Testing with repo ID: {repo_id_to_test}")
                prs, pr_error = dm.get_pull_requests(repo_id_to_test)
                if pr_error:
                    logger.error(f"Test error fetching PRs: {pr_error}")
                elif prs:
                    logger.info(f"Successfully fetched {len(prs)} PRs for repo {repo_id_to_test}.")
                    if prs:
                        pr_db_id_to_test = prs[0]['id'] # Assuming 'id' is the DB PK
                        comments, comment_error = dm.get_review_comments(pr_db_id_to_test)
                        if comment_error:
                            logger.error(f"Test error fetching comments: {comment_error}")
                        elif comments:
                            logger.info(f"Successfully fetched {len(comments)} comments for PR {pr_db_id_to_test}.")
                        else:
                            logger.info(f"No comments found for PR {pr_db_id_to_test} (or an issue if there should be some).")
                else:
                    logger.info(f"No PRs found for repo {repo_id_to_test} (or an issue if there should be some).")

        else:
            logger.info("No repositories found (or an issue if there should be some).")

    except Exception as e:
        logger.error(f"Error during DataManager test: {e}", exc_info=True)
